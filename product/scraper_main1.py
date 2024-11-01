import os
import requests
import re  # For price formatting
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from django.conf import settings
from django.utils.text import slugify
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from decimal import Decimal, InvalidOperation
from product.models import ProductModel, ProductImage, ProductSpec, Brand, Category


def scraper_enter(brand_name, category_name, url, check_duplicates=False):
    print(f"Starting scraping for {brand_name} at URL: {url}")
    print(f"Starting scraping for {category_name}")
    print(f"Check duplicates: {check_duplicates}")

    # Create output directories
    images_directory = os.path.join(settings.MEDIA_ROOT, 'product_model_images')
    os.makedirs(images_directory, exist_ok=True)

    # Get brand and category instances
    try:
        brand = Brand.objects.get(name__iexact=brand_name)
    except Brand.DoesNotExist:
        print(f"Brand '{brand_name}' does not exist in the database.")
        return

    try:
        category = Category.objects.get(name__iexact=category_name)
    except Category.DoesNotExist:
        print(f"Category '{category_name}' does not exist in the database.")
        return

    if brand.name.lower() == 'lg':
        scraper_lg(brand, category, url, images_directory)
    else:
        print(f"Scraping for {brand.name} is not yet supported.")
        return


def scraper_lg(brand, category, url, image_directory):
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('--disable-dev-shm-usage')  # Avoid /dev/shm partition being too small
    options.add_argument('--no-sandbox')             # Required for some environments
    options.add_argument('--disable-cache')          # Prevent cache issues
    options.add_argument('--incognito')              # Start with a fresh profile
    options.add_argument('--disable-gpu')            # Disable GPU for better stability in some environments

    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    print("Start loading Page")
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiBox-root')]"))
    )

    # Scroll and click "Load More" if necessary
    while True:
        try:
            load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More')]")
            if len(load_more_buttons) == 0:
                break
            load_more_buttons[0].click()
            print("Clicked 'Load More' button.")
            time.sleep(2)
        except Exception as e:
            print("Error clicking 'Load More':", e)
            break

    product_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiGrid-item') and contains(@class, 'css-1rs68s8')]")
    print(f"Found {len(product_elements)} products on the page.")

    for element in product_elements:
        try:
            model_number = element.find_element(By.XPATH, ".//span[contains(@class, 'MuiTypography-caption')]").text

            link = element.find_element(By.XPATH, ".//a[@class='css-11xg6yi']").get_attribute('href')

            try:
                msrp = element.find_element(By.XPATH, ".//span[@class='MuiTypography-root MuiTypography-caption css-y2b2df']").text
                msrp_decimal = float(re.sub(r'[^\d.]', '', msrp)) if msrp else 0
            except:
                msrp_decimal = 0

            try:
                discount_price = element.find_element(By.XPATH, ".//h6[@class='MuiTypography-root MuiTypography-subtitle1 MuiTypography-alignRight css-krsbao']").text
                discount_price_decimal = float(re.sub(r'[^\d.]', '', discount_price)) if discount_price else 0
            except:
                discount_price_decimal = 0

            if msrp_decimal == 0:
                msrp_decimal = discount_price_decimal

            # Save product to database
            product, created = ProductModel.objects.update_or_create(
                model_number=model_number,
                defaults={
                    'brand': brand,
                    'category': category,
                    'description': "",  # Update description later from the detailed page
                    'msrp': msrp_decimal,
                    'discount_price': discount_price_decimal,
                    'link': link
                }
            )

            print(f"Extracted and saved product: {model_number}")

            # Open the product page to scrape additional details
            open_lg_sub_page(model_number, link, image_directory)

        except Exception as e:
            print(f"Error extracting product information: {e}")

    driver.quit()
    print("Scraping completed.")


def open_lg_sub_page(model_number, url, image_directory):
    # Set up Selenium WebDriver with headless mode
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-cache')
    options.add_argument('--incognito')
    options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        time.sleep(2)  # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiBox-root')]"))
        )

        # Close pop-up if present
        close_popup_if_present(driver)
        # Click the "All Specs" button to reveal the full specifications
        click_all_specs_button(driver)
        
        # Scrape descriptions and specifications
        descriptions = scrape_descriptions(driver)
        specifications = scrape_spec(driver)

        # Update product description in the database
        ProductModel.objects.filter(model_number=model_number).update(description="; ".join(descriptions))

        # Save specifications to the database
        for spec_name, spec_value in specifications.items():
            spec, _ = ProductSpec.objects.get_or_create(spec=spec_name)
            ProductSpec.objects.create(
                product_model_id=model_number,
                spec=spec,
                value=spec_value
            )

        # Scrape and save images
        image_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'image-gallery')]//img")
        for index, image_element in enumerate(image_elements):
            img_url = image_element.get_attribute("src")
            if model_number.lower() in img_url.lower():
                image_file_name = f"{model_number}_{index + 1}.jpg"
                image_path = os.path.join(image_directory, image_file_name)
                img_data = requests.get(img_url).content
                with open(image_path, 'wb') as handler:
                    handler.write(img_data)
                ProductImage.objects.create(
                    product_model_id=model_number,
                    image=image_path
                )

    except Exception as e:
        print(f"Error processing product page for model {model_number}: {e}")
    finally:
        driver.quit()


def close_popup_if_present(driver):
    try:
        close_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "closeIconContainer"))
        )
        close_button.click()
        print("Popup closed using the close button.")
    except Exception as e:
        print("No popup found or close button not clickable, continuing with scraping.")


def handle_blocking_element(driver):
    try:
        blocking_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "transcend-consent-manager"))
        )
        driver.execute_script("arguments[0].style.display = 'none';", blocking_element)
        print("Blocking element removed.")
    except Exception as e:
        print("No blocking element found or removed.")


def click_all_specs_button(driver):
    try:
        handle_blocking_element(driver)
        all_specs_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "simple-tab-3"))
        )
        actions = ActionChains(driver)
        actions.move_to_element(all_specs_button).click().perform()
        time.sleep(2)
        print("Clicked the 'All Specs' button.")
    except Exception as e:
        print(f"Error locating or clicking 'All Specs' button: {e}")


def scrape_spec(driver):
    try:
        spec_elements = driver.find_elements(By.XPATH, "//div[@class='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-3 css-1pmmlk2']")
        specifications = {}
        for spec in spec_elements:
            title_element = spec.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-body3')]")
            title = title_element.text
            value_element = spec.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-body2')]")
            value = value_element.text
            specifications[title] = value
        return specifications
    except Exception as e:
        print(f"Error scraping specifications: {e}")
        return {}


def scrape_descriptions(driver):
    try:
        ul_element = driver.find_element(By.XPATH, "//ul[contains(@class, 'css-1he9hsx')]")
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        descriptions = [li.text for li in li_elements]
        return descriptions
    except Exception as e:
        print(f"Error scraping descriptions: {e}")
        return []

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
from product.models import ProductModel, ProductImage, ProductSpec, Brand, Category, Spec, product_image_upload_path
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import hashlib

def scraper_enter(brand_name, category_name, url):
    print(f"Starting scraping for {brand_name} at URL: {url}")
    print(f"Starting scraping for {category_name}")

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
        scraper_lg(brand, category, url)
    else:
        print(f"Scraping for {brand.name} is not yet supported.")
        return

def scraper_lg(brand, category, url):
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
            open_lg_sub_page(product, link)

        except Exception as e:
            print(f"Error extracting product information: {e}")

    driver.quit()
    print("Scraping completed.")

def open_lg_sub_page(product, url):
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
        
        # Scrape descriptions and save to database
        descriptions = scrape_descriptions(driver)
        if descriptions:
            product.description = "; ".join(descriptions)
            product.save()
            print(f"Descriptions saved database for model {product.model_number}.")

        # Scrape and Save specifications to the database
        specifications = scrape_spec(driver)
        if specifications:
            for spec_name, spec_value in specifications.items():
                spec, _ = Spec.objects.get_or_create(name=spec_name)
                ProductSpec.objects.update_or_create(
                    product_model=product,
                    spec=spec,
                    defaults={'value': spec_value}
                )
            print(f"Specs saved to database for model {product.model_number}.")

        # Scrape and save images
        image_elements = driver.find_elements(By.XPATH, "//img[@class='thumbnail-item MuiBox-root css-12v44gy']")
        print(f"Found {len(image_elements)} images for model {product.model_number}.")

        fs = FileSystemStorage()  # Use Django's FileSystemStorage for safe handling

        for image_element in image_elements:
            img_url = image_element.get_attribute("src")

            response = requests.get(img_url)
            img_data = response.content
            image_hash = hashlib.md5(img_data).hexdigest()

                # Check if an image with the same hash already exists
            duplicate = ProductImage.objects.filter(product_model=product, hash=image_hash).exists()
            if duplicate:
                print(f"Duplicate image found for model {product.model_number}, skipping upload.")
                continue

                # Create a unique filename
            image_file_name = f"{product.model_number}_{image_hash}.jpg"
            image_path = product_image_upload_path(product.model_number, image_file_name)

                # Use FileSystemStorage to save the image
            image_file = ContentFile(img_data)
            saved_path = fs.save(image_path, image_file)

            # Save the image in the database, including the hash
            ProductImage.objects.create(
                product_model=product,
                image=saved_path,
                hash=image_hash
            )
            print(f"Save image {image_file_name}.")

    except Exception as e:
        print(f"Error processing product page for model {product.model_number}: {e}")
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
        # Handle any blocking elements before proceeding
        handle_blocking_element(driver)
        
        retries = 3
        for attempt in range(retries):
            try:
                # Locate either a <button> or an <a> tag containing the text "All Specs"
                all_specs_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[h6[text()='All Specs']]"))
                )
                
                # Scroll smoothly to the element and click it
                actions = ActionChains(driver)
                actions.move_to_element(all_specs_element).click().perform()
                
                time.sleep(2)  # Allow time for the "All Specs" content to load
                print("Clicked the 'All Specs' element.")

                return  # Exit the function if click is successful

            except Exception as inner_e:
                print(f"Attempt {attempt + 1} to click 'All Specs' element failed: {inner_e}")
                time.sleep(2)  # Short wait before retrying
                click_other_button(driver)

    except Exception as e:
        print(f"Error locating or clicking 'All Specs' element: {e}")

def click_other_button(driver):
    try:
        # Handle any blocking elements before proceeding
        handle_blocking_element(driver)
        
        retries = 3
        for attempt in range(retries):
            try:
                # Locate either a <button> or an <a> tag containing the text "All Specs"
                other_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//h6[@class='MuiTypography-root MuiTypography-buttonMedium css-1q3fipq'/ancestor::button"))
                )
                
                # Scroll smoothly to the element and click it
                actions = ActionChains(driver)
                actions.move_to_element(other_element).click().perform()
                
                time.sleep(2)  # Allow time for the "All Specs" content to load
                print("Clicked other element.")

                return  # Exit the function if click is successful

            except Exception as inner_e:
                print(f"Attempt {attempt + 1} to click other element failed: {inner_e}")
                time.sleep(2)  # Short wait before retrying

    except Exception as e:
        print(f"Error locating or clicking other element: {e}")

def scrape_spec(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-3 css-1pmmlk2']"))
        )

        spec_elements = driver.find_elements(By.XPATH, "//div[@class='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-3 css-1pmmlk2']")
        specifications = {}
        for spec in spec_elements:
            title_element = spec.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-body3')]")
            title = title_element.text
            if not title.strip():
                continue
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
        descriptions = [li.text for li in li_elements if "extra 1-year limited warranty" not in li.text.lower()]
        return descriptions
    except Exception as e:
        print(f"Error scraping descriptions: {e}")
        return []

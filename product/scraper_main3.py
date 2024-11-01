import os
import csv
import requests
import re  # For price formatting
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from django.conf import settings
from django.utils.text import slugify
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from decimal import Decimal, InvalidOperation

# Function to read existing model numbers from CSV---读取已经抓取过的产品型号csv文件，把文件内存在的 Model Number作为列表输出
def read_existing_model_numbers(product_data_file):
    if not os.path.exists(product_data_file):
        return set()
    model_numbers = set()
    with open(product_data_file, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            model_numbers.add(row['Product Model Number'])
    return model_numbers

# Common function to save product data to CSV---通用功能，把抓去的产品信息保存到csv文件里。产品信息products作为list输入
def save_products_to_csv(products, product_data_file, existing_model_numbers):
    with open(product_data_file, mode='a', newline='', encoding='utf-8') as data_file:
        fieldnames = ['Product Model Number', 'Brand','Category','Description', 'MSRP', 'Discount Price', 'Link']
        writer = csv.DictWriter(data_file, fieldnames=fieldnames)

        if data_file.tell() == 0:
            writer.writeheader()

        for product in products:
            if product['Product Model Number'] not in existing_model_numbers:
                writer.writerow({
                    'Product Model Number': product['Product Model Number'],
                    'Brand': product['Brand'],
                    'Category': product['Category'],
                    'Description': product['Description'],
                    'MSRP': product['MSRP'],
                    'Discount Price': product['Discount Price'],
                    'Link' : product['Link']
                })

def scraper_enter(brand,category, url,check_duplicates=False):
    print(f"Starting scraping for {brand} at URL: {url}")
    print(f"Starting scraping for {category}")
    print(f"Check duplicates: {check_duplicates}")

    # Create output directories
    output_directory = os.path.join(os.getcwd(), 'scraping_output')
    os.makedirs(output_directory, exist_ok=True)
    images_directory = os.path.join(settings.MEDIA_ROOT, 'product_model_images')
    os.makedirs(images_directory, exist_ok=True)

    product_data_file = os.path.join(output_directory, "product_model_data.csv")
    image_data_file = os.path.join(output_directory, "product_model_image.csv")
    product_spec_file = os.path.join(output_directory, "product_spec_data.csv")

    existing_model_numbers = set()
    if check_duplicates:
        existing_model_numbers = read_existing_model_numbers(product_data_file)

    if brand.lower() == 'lg':
        scraper_lg(brand, category, url, existing_model_numbers, output_directory, images_directory, product_data_file, image_data_file, product_spec_file)
    else:
        print(f"Scraping for {brand} is not yet supported.")
        return
    
def scraper_lg(brand, category, url, existing_model_numbers, output_directory, image_directory, product_data_file, image_data_file, product_spec_file):
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

    products = []

    # Extract product information for LG
    product_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiGrid-item') and contains(@class, 'css-1rs68s8')]")
    print(f"Found {len(product_elements)} products on the page.")

    for element in product_elements:
        try:
            model_number = element.find_element(By.XPATH, ".//span[contains(@class, 'MuiTypography-caption')]").text
            if model_number in existing_model_numbers:
                print(f"Skipping duplicate model: {model_number}")
                continue

            link = element.find_element(By.XPATH, ".//a[@class='css-11xg6yi']").get_attribute('href')  # Extract the product link

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

            if msrp_decimal is 0:
                msrp_decimal = discount_price_decimal

            products.append({
                'Brand': brand,
                'Category': category,
                'Product Model Number': model_number,
                'Description': "",
                'MSRP': msrp_decimal,
                'Discount Price': discount_price_decimal,
                'Link': link
            })

            print(f"Extracted product: {model_number}")

        except Exception as e:
            print(f"Error extracting product information: {e}")

    driver.quit()

    save_products_to_csv(products, product_data_file, existing_model_numbers)

    for product in products:
        model_number = product['Product Model Number']
        url = product['Link']
        open_lg_sub_page(model_number, url,existing_model_numbers, output_directory, image_directory, product_data_file, image_data_file, product_spec_file)

    print("scraping completed.")

def open_lg_sub_page(model_number, url,existing_model_numbers, output_directory, image_directory, product_data_file, image_data_file, product_spec_file):
    # Set up Selenium WebDriver with headless mode disabled (so you can see it in action)
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('--disable-dev-shm-usage')  # Avoid /dev/shm partition being too small
    options.add_argument('--no-sandbox')             # Required for some environments
    options.add_argument('--disable-cache')          # Prevent cache issues
    options.add_argument('--incognito')              # Start with a fresh profile
    options.add_argument('--disable-gpu')            # Disable GPU for better stability in some environments
    
    # Start the WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Open the provided URL (model page)
        driver.get(url)
        time.sleep(2)  # Wait for the page to load
        WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiBox-root')]"))
            )
        # Keep the browser open for 5 more seconds to confirm
        
        # Check if the popup appears and close it if it does
        close_popup_if_present(driver)
        # Click the "All Specs" button to reveal the full specifications
        click_all_specs_button(driver)
        
        # Scrape the list of features
        descriptions = scrape_descriptions(driver)

        print(descriptions)

        #spec = scrape_spec(driver)


    finally:
        # Close the browser after testing
        driver.quit()


def close_popup_if_present(driver):
    try:
        # Use WebDriverWait to check if the popup close button is present within 5 seconds
        close_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "closeIconContainer"))
        )
        close_button.click()
        print("Popup closed using the close button.")
    except Exception as e:
        # If no popup is found within 5 seconds, we proceed without an issue
        print("No popup found or close button not clickable, continuing with scraping.")

def handle_blocking_element(driver):
    try:
        # Check if the blocking element (e.g., consent manager) is present
        blocking_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "transcend-consent-manager"))
        )
        driver.execute_script("arguments[0].style.display = 'none';", blocking_element)
        print("Blocking element removed.")
    except Exception as e:
        # If no blocking element is found, continue with normal flow
        print("No blocking element found or removed.")

def click_all_specs_button(driver):
    try:
        # First, handle any blocking elements (e.g., consent manager)
        handle_blocking_element(driver)
        
        # Locate the "All Specs" button using the ID attribute
        all_specs_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "simple-tab-3"))
        )
        
        actions = ActionChains(driver)
        actions.move_to_element(all_specs_button).perform()  # Scrolls to the button
       
        # Click the button to reveal the specs
        all_specs_button.click()
        time.sleep(10)
        print("Clicked the 'All Specs' button.")
    except Exception as e:
        print(f"Error locating or clicking 'All Specs' button: {e}")

def scrape_spec(driver):
    try:
        # Locate all divs containing specifications
        spec_elements = driver.find_elements(By.XPATH, "//div[@class='MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-sm-6 MuiGrid-grid-md-3 css-1pmmlk2']")
        
        specifications = {}
        
        for spec in spec_elements:
            # Find the specification title (e.g., "Dry Modes")
            title_element = spec.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-body3')]")
            title = title_element.text

            # Find the corresponding value (e.g., "Damp, 120min, Energy Saver...")
            value_element = spec.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-body2')]")
            value = value_element.text

            # Store the result in a dictionary
            specifications[title] = value
        
        # Print extracted specifications
        print("Extracted Specifications:")
        for title, value in specifications.items():
            print(f"{title}: {value}")
        
        return specifications

    except Exception as e:
        print(f"Error scraping specifications: {e}")
        return {}
    
def scrape_descriptions(driver):
    try:
        # Locate the <ul> element containing the list items
        ul_element = driver.find_element(By.XPATH, "//ul[contains(@class, 'css-1he9hsx')]")
        
        # Extract all <li> elements inside the <ul>
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        
        # Extract the text content from each <li> element
        descriptions = [li.text for li in li_elements]
        
        return descriptions
    
    except Exception as e:
        print(f"Error scraping descriptions: {e}")
        return []



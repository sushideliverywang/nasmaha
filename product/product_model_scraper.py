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
        fieldnames = ['Product Model Number', 'Brand','Category','Description', 'MSRP', 'Lowest Price', 'Link']
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
                    'Lowest Price': product['Lowest Price'],
                    'Link' : product['Link']
                })

# Common function to save image data and download images
def save_images_to_csv(products, image_data_file):
    with open(image_data_file, mode='a', newline='', encoding='utf-8') as image_file:
        fieldnames = ['Product Model Number', 'Image File Name']
        writer = csv.DictWriter(image_file, fieldnames=fieldnames)

        if image_file.tell() == 0:
            writer.writeheader()

        for product in products:
            model_number = product['Product Model Number']
            brand = slugify(product['Brand'])
            category = slugify(product['Category'])
            
            # Create the image folder structure: product_model_images/brand/category/model_number/
            images_directory = os.path.join('media/product_model_images', brand, category, slugify(model_number))
            os.makedirs(images_directory, exist_ok=True)  # Create the directories if they don't exist

            # Define the image file name
            image_file_name = f"{model_number}.jpg"
            
            # Write to CSV
            writer.writerow({'Product Model Number': model_number, 'Image File Name': image_file_name})

            # Download the image
            try:
                img_data = requests.get(product['Image URL']).content
                image_path = os.path.join(images_directory, image_file_name)
                with open(image_path, 'wb') as handler:
                    handler.write(img_data)
                print(f"Downloaded image for {model_number}")
            except Exception as e:
                print(f"Error downloading image for {model_number}: {e}")

# Parsing function for LG website
def parse_lg(driver, existing_model_numbers):
    products = []

    # Extract product information for LG
    product_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiGrid-item') and contains(@class, 'css-1rs68s8')]")
    print(f"Found {len(product_elements)} products on the page.")

    for product in product_elements:
        try:
            model_number = product.find_element(By.XPATH, ".//span[contains(@class, 'MuiTypography-caption')]").text
            if model_number in existing_model_numbers:
                print(f"Skipping duplicate model: {model_number}")
                continue

            description = product.find_element(By.XPATH, ".//h6[@id='product-title']").text
            link = product.find_element(By.XPATH, ".//a[@class='css-11xg6yi']").get_attribute('href')  # Extract the product link

            try:
                msrp = product.find_element(By.XPATH, ".//span[@class='MuiTypography-root MuiTypography-caption css-y2b2df']").text
                msrp_decimal = float(re.sub(r'[^\d.]', '', msrp)) if msrp else 0
            except:
                msrp_decimal = 0

            try:
                lowest_price = product.find_element(By.XPATH, ".//h6[@class='MuiTypography-root MuiTypography-subtitle1 MuiTypography-alignRight css-krsbao']").text
                lowest_price_decimal = float(re.sub(r'[^\d.]', '', lowest_price)) if lowest_price else 0
            except:
                lowest_price_decimal = 0

            if msrp_decimal is 0:
                msrp_decimal = lowest_price_decimal

            image_url = product.find_element(By.XPATH, ".//img").get_attribute('src')
            products.append({
                'Product Model Number': model_number,
                'Description': description,
                'MSRP': msrp_decimal,
                'Lowest Price': lowest_price_decimal,
                'Image URL': image_url,
                'Link': link
            })

            print(f"Extracted product: {model_number}")

        except Exception as e:
            print(f"Error extracting product information: {e}")

    return products

# Main scraping function that accepts a brand and URL
def scrape_website(brand, category, url, output_directory, check_duplicates=False):
    print(f"Starting scraping for {brand} at URL: {url}")
    print(f"Starting scraping for {category}")
    print(f"Output directory: {output_directory}")
    print(f"Check duplicates: {check_duplicates}")

    # Set up Selenium WebDriver with headless mode
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(service=service, options=options)

    # Create output directories
    os.makedirs(output_directory, exist_ok=True)
    images_directory = os.path.join(settings.MEDIA_ROOT, 'product_model_images')
    os.makedirs(images_directory, exist_ok=True)

    product_data_file = os.path.join(output_directory, "product_model_data.csv")
    image_data_file = os.path.join(output_directory, "product_model_image.csv")

    # Read existing model numbers if checking for duplicates
    existing_model_numbers = set()
    if check_duplicates:
        existing_model_numbers = read_existing_model_numbers(product_data_file)

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

    # Choose the correct parsing function based on the brand
    if brand.lower() == 'lg':
        products = parse_lg(driver, existing_model_numbers)
    else:
        print(f"Scraping for {brand} is not yet supported.")
        driver.quit()
        return
    
    for product in products:
        product['Category'] = category  # Add the selected category to each product
        product['Brand'] = brand  # Add the selected brand to each product
        # Set MSRP and Lowest Price to 0 if they are null
        product['MSRP'] = product['MSRP'] if product['MSRP'] is not None else 0
        product['Lowest Price'] = product['Lowest Price'] if product['Lowest Price'] is not None else 0

    # Save products and images
    save_products_to_csv(products, product_data_file, existing_model_numbers)
    save_images_to_csv(products, image_data_file)

    driver.quit()
    print(f"{brand.upper()} scraping completed.")


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

def scrape_specifications(driver):
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

def scrape_list_items(driver):
    try:
        # Locate the <ul> element containing the list items
        ul_element = driver.find_element(By.XPATH, "//ul[contains(@class, 'css-1he9hsx')]")
        
        # Extract all <li> elements inside the <ul>
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        
        # Extract the text content from each <li> element
        features = [li.text for li in li_elements]
        
        print("Extracted features:")
        for feature in features:
            print(f"- {feature}")
        
        return features
    
    except Exception as e:
        print(f"Error scraping list items: {e}")
        return []

def scrape_and_download_images(driver, product_model, images_directory):
    try:
        # Locate all <img> elements with the class 'thumbnail-item'
        img_elements = driver.find_elements(By.XPATH, "//img[@class='thumbnail-item MuiBox-root css-12v44gy']")
        
        image_urls = []
        
        for idx, img_element in enumerate(img_elements):
            # Extract the image URL from the 'src' attribute
            img_url = img_element.get_attribute('src')
            
            # Only download the image if the URL contains the product model number
            if product_model.lower() in img_url.lower():
                image_urls.append(img_url)
                
                # Create a filename for the image
                image_file_name = f"{product_model}_image_{idx + 1}.jpg"
                image_path = os.path.join(images_directory, image_file_name)

                # Download the image
                try:
                    img_data = requests.get(img_url).content
                    with open(image_path, 'wb') as handler:
                        handler.write(img_data)
                    print(f"Downloaded image {image_file_name} for model {product_model}")
                except Exception as e:
                    print(f"Error downloading image {image_file_name}: {e}")
            else:
                print(f"Skipping image {img_url} as it doesn't contain the model number {product_model}")
        
        return image_urls
    
    except Exception as e:
        print(f"Error scraping images: {e}")
        return []

def open_and_process_page(url, product_model, images_directory):
    # Set up Selenium WebDriver with headless mode disabled (so you can see it in action)
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.headless = False  # Disable headless mode so you can see the browser

    # Start the WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Open the provided URL (model page)
        driver.get(url)
        time.sleep(2)  # Wait for the page to load

        # Check if the popup appears and close it if it does
        close_popup_if_present(driver)
        # Click the "All Specs" button to reveal the full specifications
        click_all_specs_button(driver)
        
        # Scrape the list of features
        features = scrape_list_items(driver)
        
        specifications = scrape_specifications(driver)
        
        # Scrape and download images
        image_urls = scrape_and_download_images(driver, product_model, images_directory)
        
        # Keep the browser open for 5 more seconds to confirm
        time.sleep(5)

    finally:
        # Close the browser after testing
        driver.quit()


    
def scrape_product_price(driver):
    
    try:
        try:
            msrp = driver.find_element(By.XPATH, ".//span[@class='MuiTypography-root MuiTypography-caption css-14jem7i']").text
            msrp_decimal = float(re.sub(r'[^\d.]', '', msrp)) if msrp else 0
        except:
            msrp_decimal = 0

        try:
            discount_price = driver.find_element(By.XPATH, ".//h6[@class='MuiTypography-root MuiTypography-subtitle1 css-1x0i2qf']").text
            discount_price_decimal = float(re.sub(r'[^\d.]', '', discount_price)) if discount_price else 0
        except:
            discount_price_decimal = 0

        if msrp_decimal is 0:
            msrp_decimal = discount_price_decimal

        return msrp_decimal,discount_price_decimal
    
    except Exception as e:
        print(f"Error extracting product price: {e}")
    
    
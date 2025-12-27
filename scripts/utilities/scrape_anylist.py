#!/usr/bin/env python3
"""
AnyList Recipe URL Scraper
Extracts source URLs from all recipes in your AnyList account
"""

import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import EMAIL, PASSWORD

# Configuration
ANYLIST_URL = "https://www.anylist.com/web"
OUTPUT_FILE = "anylist_recipes.csv"
SCROLL_PAUSE_TIME = 2  # seconds to wait after scrolling
PAGE_LOAD_WAIT = 3  # seconds to wait for pages to load

def setup_driver():
    """Set up and return Chrome WebDriver"""
    print("Setting up Chrome driver...")
    chrome_options = Options()
    # Remove headless mode so you can see what's happening
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login(driver):
    """Log into AnyList"""
    print(f"Logging in as {EMAIL}...")
    driver.get(ANYLIST_URL)
    
    # Wait for login page to load and enter credentials
    wait = WebDriverWait(driver, 10)
    
    # Find and fill email field
    email_field = wait.until(EC.presence_of_element_located((By.ID, "sign_in_email")))
    email_field.send_keys(EMAIL)
    
    # Find and fill password field
    password_field = driver.find_element(By.ID, "sign_in_pw")
    password_field.send_keys(PASSWORD)
    
    # Click sign in button
    sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    sign_in_button.click()
    
    # Wait for main page to load
    time.sleep(PAGE_LOAD_WAIT)
    print("Logged in successfully!")

def navigate_to_all_recipes(driver):
    """Navigate to the All Recipes view"""
    print("Navigating to All Recipes...")
    
    # Wait a bit for any popups to appear
    time.sleep(3)
    
    print("If you see any popups, close them now, then press Enter to continue...")
    input()
    
    # Click on Recipes in sidebar
    wait = WebDriverWait(driver, 10)
    recipes_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Recipes')]")))
    recipes_link.click()
    time.sleep(2)
    
    # Look for "All" or "All Recipes" option - may need to adjust this selector
    # You might need to update this xpath based on the actual HTML structure
    try:
        all_recipes = driver.find_element(By.XPATH, "//div[contains(text(), 'All') or contains(text(), 'all')]")
        all_recipes.click()
        time.sleep(2)
    except:
        print("Already on All Recipes or couldn't find All option")
    
    print("On All Recipes view")

def scroll_to_load_all_recipes(driver):
    """Scroll through the recipe list to load all recipes"""
    print("Scrolling to load all recipes...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    recipes_loaded = 0
    
    while True:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Calculate new scroll height and compare with last height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Count visible recipes (adjust selector as needed)
        current_count = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'recipe') or contains(text(), 'from ')]"))
        if current_count > recipes_loaded:
            recipes_loaded = current_count
            print(f"  Loaded {recipes_loaded} recipes so far...")
        
        if new_height == last_height:
            print(f"Finished scrolling. Total recipes visible: {recipes_loaded}")
            break
            
        last_height = new_height

def get_recipe_links(driver):
    """Extract all recipe links from the list view"""
    print("Extracting recipe links from list...")
    
    # Find only recipe cells that have images (not category headers)
    # Look for elements with both ALTableCell class AND an image child
    recipe_elements = driver.find_elements(By.XPATH, 
        "//div[contains(@class, 'ALTableCell')]//div[contains(@class, 'ALTableCellImage')]/ancestor::div[contains(@class, 'ALTableCell')]")
    
    print(f"Found {len(recipe_elements)} recipe elements")
    
    # Collect recipe info
    recipes = []
    for idx, element in enumerate(recipe_elements):
        try:
            # Get the full text of the recipe cell
            full_text = element.text
            # Title is typically the first line
            lines = full_text.split('\n')
            title = lines[0] if lines else f"Recipe {idx+1}"
            
            recipes.append({
                'title': title.strip(),
                'element': element,
                'index': idx
            })
        except Exception as e:
            print(f"Error processing recipe {idx}: {e}")
    
    print(f"Collected {len(recipes)} recipe entries")
    return recipes

def extract_source_url(driver):
    """Extract the source URL from the current recipe detail page"""
    try:
        wait = WebDriverWait(driver, 5)
        # Look for the "from [source]" link with external link icon
        source_link = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(text(), 'from ') or contains(@href, 'http')]")
        ))
        
        url = source_link.get_attribute('href')
        return url
    except Exception as e:
        print(f"  Could not find source URL: {e}")
        return None

def scrape_all_recipes(driver, recipe_list):
    """Visit each recipe and extract source URL"""
    print(f"\nStarting to scrape {len(recipe_list)} recipes...")
    results = []
    
    for idx, recipe_info in enumerate(recipe_list):
        print(f"\n[{idx+1}/{len(recipe_list)}] Processing: {recipe_info['title']}")
        
        try:
            # Click the recipe element
            recipe_info['element'].click()
            time.sleep(PAGE_LOAD_WAIT)
            
            # Extract source URL
            source_url = extract_source_url(driver)
            
            results.append({
                'title': recipe_info['title'],
                'source_url': source_url if source_url else 'No URL found'
            })
            
            print(f"  ✓ URL: {source_url}")
            
            # Navigate back to list
            driver.back()
            time.sleep(2)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'title': recipe_info['title'],
                'source_url': f'Error: {str(e)}'
            })
            # Try to get back to list view
            try:
                driver.back()
                time.sleep(2)
            except:
                pass
    
    return results

def save_results(results):
    """Save results to CSV file"""
    print(f"\nSaving {len(results)} results to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'source_url'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✓ Results saved to {OUTPUT_FILE}")

def main():
    """Main execution function"""
    driver = None
    
    try:
        driver = setup_driver()
        login(driver)
        navigate_to_all_recipes(driver)
        scroll_to_load_all_recipes(driver)
        recipe_list = get_recipe_links(driver)
        results = scrape_all_recipes(driver, recipe_list)
        save_results(results)
        
        print("\n" + "="*50)
        print("SCRAPING COMPLETE!")
        print(f"Total recipes processed: {len(results)}")
        print(f"Results saved to: {OUTPUT_FILE}")
        print("="*50)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()

if __name__ == "__main__":
    main()

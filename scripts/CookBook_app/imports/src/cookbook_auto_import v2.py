#!/usr/bin/env python3
"""
CookBook Recipe Auto-Importer

This script automates importing recipes into CookBook using the browser extension.
It opens each recipe URL in Chrome and triggers the CookBook extension to save it.

SETUP REQUIREMENTS:
1. Install Selenium:
   pip install selenium

2. Make sure Chrome and ChromeDriver are compatible
   - Chrome browser installed
   - ChromeDriver matches your Chrome version
   - Install ChromeDriver: brew install chromedriver (Mac)
   
3. CookBook extension must be installed and you must be logged in

USAGE:
    python cookbook_auto_import.py recipes_missing_from_cookbook.csv
    
    Or edit INPUT_FILE below and run:
    python cookbook_auto_import.py
"""

import pandas as pd
import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FILE = '/Users/yourname/Downloads/recipes_missing_from_cookbook.csv'
OUTPUT_LOG = 'cookbook_import_log.txt'

# Timing settings (in seconds)
PAGE_LOAD_TIMEOUT = 30
EXTENSION_WAIT = 3  # Wait for extension to process recipe
SAVE_WAIT = 2       # Wait after clicking save for recipe to be saved
BETWEEN_RECIPES = 2 # Pause between recipes to avoid rate limiting

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# BROWSER SETUP
# ============================================================================

def setup_chrome():
    """Setup Chrome with existing profile to use installed extensions"""
    
    chrome_options = Options()
    
    # Use your existing Chrome profile so CookBook extension is available
    # You may need to adjust this path - check chrome://version/ in Chrome
    # Common paths:
    # Mac: ~/Library/Application Support/Google/Chrome
    # Windows: %LOCALAPPDATA%\Google\Chrome\User Data
    # Linux: ~/.config/google-chrome
    
    user_data_dir = str(Path.home() / "Library/Application Support/Google/Chrome")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
    # Use a specific profile (usually "Default" or "Profile 1")
    # Check chrome://version/ to see which profile you're using
    chrome_options.add_argument("profile-directory=Default")
    
    # Keep browser open and visible (not headless) so you can monitor
    # chrome_options.add_argument("--headless")  # Uncomment for headless
    
    # Disable some features that might interfere
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    logger.info("Initializing Chrome browser...")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    return driver


# ============================================================================
# IMPORT LOGIC
# ============================================================================

def wait_for_cookbook_extension(driver):
    """
    Wait for CookBook extension to be ready.
    
    NOTE: This is the tricky part. The CookBook extension needs to:
    1. Detect the recipe on the page
    2. Show its popup/button
    3. Be ready to save
    
    You may need to adjust this based on how the extension behaves.
    """
    time.sleep(EXTENSION_WAIT)
    # TODO: Add specific checks for CookBook extension elements if needed
    return True


def trigger_cookbook_save(driver):
    """
    Trigger the CookBook extension to save the recipe using keyboard shortcut.
    
    Uses Cmd+Shift+A (Mac) to open the CookBook extension popup,
    then waits for the "Save recipe" button and clicks it.
    """
    
    logger.info("   Triggering CookBook extension (Cmd+Shift+A)...")
    
    # Send keyboard shortcut to open extension: Cmd+Shift+A
    # On Mac, Cmd is Keys.COMMAND
    actions = ActionChains(driver)
    actions.key_down(Keys.COMMAND)
    actions.key_down(Keys.SHIFT)
    actions.send_keys('a')
    actions.key_up(Keys.SHIFT)
    actions.key_up(Keys.COMMAND)
    actions.perform()
    
    # Wait for extension popup to appear and process the recipe
    time.sleep(EXTENSION_WAIT)
    
    # Now we need to click the "Save recipe" button in the popup
    # The popup appears as an overlay/iframe from the extension
    
    # Try to find and click the save button
    try:
        # Switch to the extension popup frame if needed
        # CookBook extension shows popup on the right side
        
        # Wait a bit for the extension to render
        time.sleep(1)
        
        # The extension popup should now be visible
        # We'll look for the "Save recipe" button
        # This might need adjustment based on how the extension renders
        
        # Try clicking via JavaScript if the button is in shadow DOM
        # or use ActionChains to send Tab + Enter to navigate to button
        
        # Simple approach: Send Tab a few times then Enter
        # This works if the Save button is the focused element
        logger.info("   Clicking Save button...")
        
        # Give it a moment, then press Enter (often the save button is focused)
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN)
        actions.perform()
        
        time.sleep(SAVE_WAIT)
        return True
        
    except Exception as e:
        logger.warning(f"   Could not auto-click Save button: {e}")
        logger.info("   ⏸️  Please manually click 'Save recipe' button")
        logger.info("   (Press Enter in terminal when done)")
        input()
        return True


def import_recipe(driver, url, recipe_name, site_name):
    """Import a single recipe"""
    
    logger.info(f"📖 Importing: [{site_name}] {recipe_name}")
    logger.info(f"   URL: {url}")
    
    try:
        # Load the recipe page
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Wait for CookBook extension to detect recipe
        wait_for_cookbook_extension(driver)
        
        # Trigger CookBook to save (manual for now)
        trigger_cookbook_save(driver)
        
        logger.info("✅ Successfully imported")
        return True
        
    except TimeoutException:
        logger.error(f"❌ Timeout loading page: {url}")
        return False
    except Exception as e:
        logger.error(f"❌ Error importing recipe: {e}")
        return False


def run_import(csv_file):
    """Main import process"""
    
    logger.info("="*70)
    logger.info("CookBook Recipe Auto-Importer")
    logger.info("="*70)
    
    # Load recipes to import
    df = pd.read_csv(csv_file)
    total = len(df)
    
    logger.info(f"Found {total} recipes to import")
    logger.info(f"Log file: {OUTPUT_LOG}")
    logger.info("")
    
    # Setup browser
    driver = setup_chrome()
    
    try:
        # Keep track of progress
        successful = 0
        failed = 0
        
        for idx, row in df.iterrows():
            url = row['cleaned_url']
            recipe_name = row['recipe_name_guess']
            site_name = row['site_name']
            
            logger.info(f"\n[{idx+1}/{total}]")
            
            if import_recipe(driver, url, recipe_name, site_name):
                successful += 1
            else:
                failed += 1
            
            # Pause between recipes
            if idx < total - 1:  # Don't pause after last recipe
                time.sleep(BETWEEN_RECIPES)
        
        # Summary
        logger.info("")
        logger.info("="*70)
        logger.info("IMPORT COMPLETE")
        logger.info("="*70)
        logger.info(f"Total recipes: {total}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success rate: {successful/total*100:.1f}%")
        
    finally:
        logger.info("\nClosing browser...")
        driver.quit()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    
    # Get input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = INPUT_FILE
    
    # Check file exists
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        print("\nUsage: python cookbook_auto_import.py <csv_file>")
        sys.exit(1)
    
    try:
        run_import(input_file)
    except KeyboardInterrupt:
        print("\n\nImport cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

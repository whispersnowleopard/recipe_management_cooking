#!/usr/bin/env python3
"""
Recipe URL Cleaner and Name Extractor

This script takes an Excel file containing recipe URLs and:
1. Cleans the URLs by removing tracking parameters (UTM codes, etc.)
2. Removes trailing slashes and query strings
3. Removes duplicate URLs (keeps first occurrence)
4. Extracts a human-readable site name from the domain
5. Extracts a human-readable recipe name from the URL slug
6. Outputs cleaned data to Excel and CSV formats

USAGE:
    python clean_recipe_urls.py input_file.xlsx

    Or edit the INPUT_FILE variable below and run:
    python clean_recipe_urls.py

REQUIREMENTS:
    pip install pandas openpyxl

The script will create these output files:
- recipe_urls_cleaned.xlsx - Full comparison (source, original, cleaned, site, name)
- recipe_urls_cleaned_simple.xlsx - Just cleaned URLs, sites, and names
- CSV versions of both files
"""

import pandas as pd
from urllib.parse import urlparse, urlunparse
import re
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Input file path - edit this or pass as command line argument
INPUT_FILE = '/mnt/user-data/uploads/recipe_urls.xlsx'

# Output directory
OUTPUT_DIR = '/mnt/user-data/outputs'

# ============================================================================
# FUNCTIONS
# ============================================================================

def clean_url(url):
    """
    Clean up URL by removing tracking parameters and unnecessary components.
    
    Removes:
    - Query parameters (everything after ?)
    - URL fragments (everything after #)
    - Trailing slashes (except for root paths)
    
    Args:
        url (str): Original URL
        
    Returns:
        str: Cleaned URL
    """
    if pd.isna(url) or not isinstance(url, str):
        return url
    
    # Parse the URL into components
    parsed = urlparse(url)
    
    # Rebuild without query parameters or fragments
    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  # params
        '',  # query - removing all query parameters
        ''   # fragment
    ))
    
    # Remove trailing slashes from path (except for root)
    if cleaned.endswith('/') and len(parsed.path) > 1:
        cleaned = cleaned.rstrip('/')
    
    return cleaned


def extract_recipe_name(url):
    """
    Extract a human-readable recipe name from the URL path.
    
    The last segment of the URL path (called the "slug" in web development)
    typically contains the recipe name in a URL-friendly format.
    This function converts it back to human-readable form.
    
    Args:
        url (str): URL to extract name from
        
    Returns:
        str: Extracted recipe name in Title Case
    """
    if pd.isna(url) or not isinstance(url, str):
        return ""
    
    parsed = urlparse(url)
    path = parsed.path
    
    # Remove common file extensions
    path = re.sub(r'\.(html?|php|aspx?)$', '', path, flags=re.IGNORECASE)
    
    # Split path and get all non-empty parts
    parts = [p for p in path.split('/') if p]
    if not parts:
        return ""
    
    # Use the last part as the recipe name (this is the "slug")
    slug = parts[-1]
    
    # Remove leading numbers with hyphens (like "12345-recipe-name" -> "recipe-name")
    slug = re.sub(r'^[\d\-]+', '', slug)
    
    # Remove trailing numbers with hyphens (like "recipe-name-12345" -> "recipe-name")
    slug = re.sub(r'[\-\d]+$', '', slug)
    
    # Replace hyphens and underscores with spaces
    name = slug.replace('-', ' ').replace('_', ' ')
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    # Title case for readability
    name = name.title()
    
    # Fix common issues with possessives (S -> 's)
    name = re.sub(r'\bS\b', "'s", name)
    
    return name


def extract_site_name(url):
    """
    Extract a readable site name from the domain.
    
    Args:
        url (str): URL to extract site name from
        
    Returns:
        str: Formatted site name
    """
    if pd.isna(url) or not isinstance(url, str):
        return ""
    
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    
    # Remove www. prefix
    domain = domain.replace('www.', '')
    
    # Get the main part (before .com, .net, etc.)
    site_name = domain.split('.')[0]
    
    # Dictionary of known cooking/recipe sites with their proper names
    known_sites = {
        'allrecipes': 'AllRecipes',
        'bbcgoodfood': 'BBC Good Food',
        'betterhomesandgardens': 'Better Homes And Gardens',
        'bonappetit': 'Bon Appétit',
        'budgetbytes': 'Budget Bytes',
        'cookieandkate': 'Cookie And Kate',
        'cookingchanneltv': 'Cooking Channel',
        'cookinglight': 'Cooking Light',
        'countryliving': 'Country Living',
        'delish': 'Delish',
        'eater': 'Eater',
        'eatingwell': 'Eating Well',
        'epicurious': 'Epicurious',
        'food52': 'Food52',
        'foodandwine': 'Food And Wine',
        'foodnetwork': 'Food Network',
        'halfbakedharvest': 'Half Baked Harvest',
        'marthastewart': 'Martha Stewart',
        'minimalistbaker': 'Minimalist Baker',
        'myrecipes': 'My Recipes',
        'nytimes': 'NY Times',
        'pinchofyum': 'Pinch Of Yum',
        'realsimple': 'Real Simple',
        'recipetineats': 'Recipe Tin Eats',
        'seriouseats': 'Serious Eats',
        'simplyrecipes': 'Simply Recipes',
        'skinnytaste': 'Skinny Taste',
        'smittenkitchen': 'Smitten Kitchen',
        'southernliving': 'Southern Living',
        'tasteofhome': 'Taste Of Home',
        'tasty': 'Tasty',
        'thekitchn': 'The Kitchn',
        'thepioneerwoman': 'The Pioneer Woman',
        'thespruceeats': 'The Spruce Eats',
        'yummly': 'Yummly',
        'latimes': 'LA Times',
        'washingtonpost': 'Washington Post',
        'theatlantic': 'The Atlantic',
        'slate': 'Slate',
        'sfgate': 'SF Gate',
    }
    
    # Check if we know this site
    site_lower = site_name.lower()
    if site_lower in known_sites:
        return known_sites[site_lower]
    
    # Fallback: Try to intelligently split compound words
    words = []
    
    # Split on numbers
    parts = re.split(r'(\d+)', site_name)
    
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            words.append(part)
        else:
            # Try to find known word boundaries
            common_words = ['food', 'cook', 'kitchen', 'recipe', 'eat', 'taste', 'home', 'living', 'the', 'my']
            
            remaining = part.lower()
            part_words = []
            
            while remaining:
                found = False
                for word in common_words:
                    if remaining.startswith(word):
                        part_words.append(word.capitalize())
                        remaining = remaining[len(word):]
                        found = True
                        break
                
                if not found:
                    # Just capitalize what's left and move on
                    part_words.append(remaining.capitalize())
                    break
            
            words.extend(part_words)
    
    if words:
        return ' '.join(words)
    
    # Ultimate fallback: just capitalize
    return site_name.capitalize()


def process_recipe_urls(input_file, output_dir):
    """
    Main processing function that reads, cleans, and exports recipe URLs.
    
    Args:
        input_file (str): Path to input Excel file
        output_dir (str): Directory for output files
    """
    print(f"Reading input file: {input_file}")
    df = pd.read_excel(input_file)
    
    print(f"Processing {len(df)} URLs...")
    
    # Apply cleaning and name extraction
    df['cleaned_url'] = df['recipe urls'].apply(clean_url)
    df['site_name'] = df['cleaned_url'].apply(extract_site_name)
    df['recipe_name_guess'] = df['cleaned_url'].apply(extract_recipe_name)
    
    # Calculate statistics before deduplication
    urls_cleaned = (df['recipe urls'] != df['cleaned_url']).sum()
    urls_unchanged = (df['recipe urls'] == df['cleaned_url']).sum()
    names_extracted = (df['recipe_name_guess'] != '').sum()
    total_before_dedup = len(df)
    
    # Remove duplicates based on cleaned_url, keeping first occurrence
    df_deduped = df.drop_duplicates(subset='cleaned_url', keep='first')
    duplicates_removed = total_before_dedup - len(df_deduped)
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create full comparison output
    output_df = pd.DataFrame({
        'source': df_deduped['source'],
        'original_url': df_deduped['recipe urls'],
        'cleaned_url': df_deduped['cleaned_url'],
        'site_name': df_deduped['site_name'],
        'recipe_name_guess': df_deduped['recipe_name_guess']
    })
    
    # Create simple output (just URLs, sites, and names)
    simple_df = pd.DataFrame({
        'url': df_deduped['cleaned_url'],
        'site': df_deduped['site_name'],
        'recipe_name': df_deduped['recipe_name_guess']
    })
    
    # Save Excel files
    full_excel = f"{output_dir}/recipe_urls_cleaned.xlsx"
    simple_excel = f"{output_dir}/recipe_urls_cleaned_simple.xlsx"
    output_df.to_excel(full_excel, index=False)
    simple_df.to_excel(simple_excel, index=False)
    
    # Save CSV files
    full_csv = f"{output_dir}/recipe_urls_cleaned.csv"
    simple_csv = f"{output_dir}/recipe_urls_cleaned_simple.csv"
    output_df.to_csv(full_csv, index=False)
    simple_df.to_csv(simple_csv, index=False)
    
    # Print summary
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"Total URLs in input: {total_before_dedup}")
    print(f"URLs cleaned: {urls_cleaned}")
    print(f"URLs unchanged: {urls_unchanged}")
    print(f"Duplicate URLs removed: {duplicates_removed}")
    print(f"Unique URLs in output: {len(df_deduped)}")
    print(f"Recipe names extracted: {names_extracted}")
    print("\nOutput files created:")
    print(f"  • {full_excel}")
    print(f"  • {simple_excel}")
    print(f"  • {full_csv}")
    print(f"  • {simple_csv}")
    print("="*70)
    
    # Show some examples
    print("\nExample results (first 10):")
    print("-"*70)
    for i in range(min(10, len(df_deduped))):
        if df_deduped['recipe_name_guess'].iloc[i]:
            print(f"\n[{df_deduped['site_name'].iloc[i]}]")
            print(f"{df_deduped['cleaned_url'].iloc[i]}")
            print(f"  → {df_deduped['recipe_name_guess'].iloc[i]}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = INPUT_FILE
    
    # Run the processing
    try:
        process_recipe_urls(input_file, OUTPUT_DIR)
    except FileNotFoundError:
        print(f"Error: Could not find input file: {input_file}")
        print("\nUsage: python clean_recipe_urls.py <input_file.xlsx>")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

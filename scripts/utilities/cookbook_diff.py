#!/usr/bin/env python3
"""
CookBook Recipe URL Diff Tool

This script compares your CookBook exported recipes against your cleaned URL list
and identifies which URLs are NOT yet in your CookBook collection.

USAGE:
    python cookbook_diff.py
    
REQUIREMENTS:
    pip install pandas openpyxl

Outputs:
- recipes_missing_from_cookbook.xlsx - URLs not yet in CookBook
- recipes_missing_from_cookbook.csv - CSV version
- recipes_already_in_cookbook.xlsx - URLs already imported
"""

import pandas as pd
from urllib.parse import urlparse
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

COOKBOOK_RECIPES = '/mnt/user-data/outputs/cookbook_recipes.xlsx'
URL_LIST = '/mnt/user-data/outputs/recipe_urls_cleaned.xlsx'
OUTPUT_DIR = '/mnt/user-data/outputs'

# ============================================================================
# MAIN
# ============================================================================

def normalize_url(url):
    """
    Normalize URL for comparison - handles trailing slashes, case, www prefix
    """
    if pd.isna(url) or not isinstance(url, str):
        return None
    parsed = urlparse(url.strip())
    domain = parsed.netloc.replace('www.', '').lower()
    path = parsed.path.rstrip('/').lower()
    return f"{domain}{path}"


def find_missing_recipes():
    """Find recipes in URL list that aren't in CookBook yet"""
    
    print("Loading data...")
    cookbook_df = pd.read_excel(COOKBOOK_RECIPES)
    urls_df = pd.read_excel(URL_LIST)
    
    print(f"CookBook recipes: {len(cookbook_df)}")
    print(f"URL list: {len(urls_df)}")
    
    # Normalize URLs for better matching (handles trailing slashes, case differences)
    print("\nNormalizing URLs for accurate matching...")
    cookbook_df['url_normalized'] = cookbook_df['source_url'].apply(normalize_url)
    urls_df['url_normalized'] = urls_df['cleaned_url'].apply(normalize_url)
    
    cookbook_normalized = set(cookbook_df['url_normalized'].dropna())
    list_normalized = set(urls_df['url_normalized'].dropna())
    
    print(f"Unique normalized URLs in CookBook: {len(cookbook_normalized)}")
    print(f"Unique normalized URLs in URL list: {len(list_normalized)}")
    
    # Find which normalized URLs are missing or present
    missing_normalized = list_normalized - cookbook_normalized
    already_imported_normalized = list_normalized & cookbook_normalized
    
    # Map back to original URLs
    missing_url_set = set(urls_df[urls_df['url_normalized'].isin(missing_normalized)]['cleaned_url'])
    already_imported_set = set(urls_df[urls_df['url_normalized'].isin(already_imported_normalized)]['cleaned_url'])
    
    print(f"\nURLs NOT yet in CookBook: {len(missing_url_set)}")
    print(f"URLs already in CookBook: {len(already_imported_set)}")
    
    # Create DataFrames for missing and already imported
    missing_df = urls_df[urls_df['cleaned_url'].isin(missing_url_set)].copy()
    already_df = urls_df[urls_df['cleaned_url'].isin(already_imported_set)].copy()
    
    # Sort by site name, then recipe name
    missing_df = missing_df.sort_values(['site_name', 'recipe_name_guess']).reset_index(drop=True)
    already_df = already_df.sort_values(['site_name', 'recipe_name_guess']).reset_index(drop=True)
    
    # Save outputs
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Missing recipes
    missing_excel = f"{OUTPUT_DIR}/recipes_missing_from_cookbook.xlsx"
    missing_csv = f"{OUTPUT_DIR}/recipes_missing_from_cookbook.csv"
    missing_df.to_excel(missing_excel, index=False)
    missing_df.to_csv(missing_csv, index=False)
    
    # Already imported recipes
    already_excel = f"{OUTPUT_DIR}/recipes_already_in_cookbook.xlsx"
    already_csv = f"{OUTPUT_DIR}/recipes_already_in_cookbook.csv"
    already_df.to_excel(already_excel, index=False)
    already_df.to_csv(already_csv, index=False)
    
    # Print summary
    print("\n" + "="*70)
    print("COMPARISON COMPLETE")
    print("="*70)
    print(f"Total URLs in your list: {len(urls_df)}")
    print(f"Already in CookBook: {len(already_df)} ({len(already_df)/len(urls_df)*100:.1f}%)")
    print(f"Missing from CookBook: {len(missing_df)} ({len(missing_df)/len(urls_df)*100:.1f}%)")
    print("\nOutput files created:")
    print(f"  • {missing_excel}")
    print(f"  • {missing_csv}")
    print(f"  • {already_excel}")
    print(f"  • {already_csv}")
    print("="*70)
    
    # Show site breakdown for missing recipes
    if not missing_df.empty:
        print("\nMissing recipes by site (top 15):")
        print("-"*70)
        site_counts = missing_df['site_name'].value_counts().head(15)
        for site, count in site_counts.items():
            print(f"  {site}: {count}")
    
    # Show sample of missing recipes
    if not missing_df.empty:
        print("\nSample of missing recipes (first 15):")
        print("-"*70)
        for idx, row in missing_df.head(15).iterrows():
            print(f"\n[{row['site_name']}] {row['recipe_name_guess']}")
            print(f"  {row['cleaned_url']}")
    
    # Show what was already imported
    if not already_df.empty:
        print("\n" + "="*70)
        print(f"Sample of recipes already in CookBook (first 10):")
        print("-"*70)
        for idx, row in already_df.head(10).iterrows():
            print(f"  [{row['site_name']}] {row['recipe_name_guess']}")


if __name__ == "__main__":
    try:
        find_missing_recipes()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

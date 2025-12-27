#!/usr/bin/env python3
"""
CookBook YAML to Excel Converter

This script converts exported CookBook recipe files (YAML format) into 
a structured Excel workbook or CSV file.

USAGE:
    python cookbook_yaml_to_excel.py <path_to_yaml_folder_or_zip>
    
    Or edit the INPUT_PATH variable below and run:
    python cookbook_yaml_to_excel.py

REQUIREMENTS:
    pip install pandas openpyxl pyyaml

The script creates:
- cookbook_recipes.xlsx - Full spreadsheet with all recipe data
- cookbook_recipes.csv - CSV version
- cookbook_recipes_simple.xlsx - Simplified version with key fields only
"""

import yaml
import pandas as pd
from pathlib import Path
import sys
import zipfile
import tempfile
import shutil

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_PATH = '/mnt/user-data/uploads/CookBook-Recipes-YAML-20251105T1029274450800.zip'
OUTPUT_DIR = '/mnt/user-data/outputs'

# ============================================================================
# FUNCTIONS
# ============================================================================

def extract_nutrition_value(nutrition_str, key):
    """Extract a specific nutrition value from the nutrition string"""
    if not nutrition_str:
        return None
    
    # Look for the pattern "key: value"
    import re
    pattern = rf'{key}:\s*([0-9.]+)'
    match = re.search(pattern, nutrition_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_duration(duration_str):
    """Convert ISO 8601 duration (PT15M) to minutes"""
    if not duration_str or not isinstance(duration_str, str):
        return None
    
    import re
    # PT15M -> 15 minutes
    # PT1H30M -> 90 minutes
    hours = 0
    minutes = 0
    
    hour_match = re.search(r'(\d+)H', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))
    
    min_match = re.search(r'(\d+)M', duration_str)
    if min_match:
        minutes = int(min_match.group(1))
    
    total_minutes = (hours * 60) + minutes
    return total_minutes if total_minutes > 0 else None


def clean_source_url(url):
    """Remove tracking parameters from URL"""
    if not url or not isinstance(url, str):
        return url
    
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  # params
        '',  # query
        ''   # fragment
    ))
    return cleaned


def parse_recipe_file(yaml_path):
    """Parse a single YAML recipe file"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        recipe = yaml.safe_load(f)
    
    # Extract and flatten the data
    data = {
        'name': recipe.get('name', ''),
        'description': recipe.get('description', ''),
        'servings': recipe.get('servings', ''),
        'source_url': clean_source_url(recipe.get('source', '')),
        'source_url_original': recipe.get('source', ''),
        'prep_time_min': parse_duration(recipe.get('prep_time')),
        'cook_time_min': parse_duration(recipe.get('cook_time')),
        'total_time_min': None,  # Will calculate if both prep and cook exist
        'video_url': recipe.get('video', ''),
        'notes': recipe.get('notes', ''),
        'on_favorites': recipe.get('on_favorites', 'no'),
        'favorite': recipe.get('favorite', 'no'),
        'cook_count': recipe.get('cook_count', 0),
        'tags': ', '.join(recipe.get('tags', [])) if recipe.get('tags') else '',
        'keywords': recipe.get('keywords', ''),
    }
    
    # Calculate total time
    if data['prep_time_min'] and data['cook_time_min']:
        data['total_time_min'] = data['prep_time_min'] + data['cook_time_min']
    elif data['prep_time_min']:
        data['total_time_min'] = data['prep_time_min']
    elif data['cook_time_min']:
        data['total_time_min'] = data['cook_time_min']
    
    # Parse nutrition
    nutrition_str = recipe.get('nutrition', '')
    data['calories'] = extract_nutrition_value(nutrition_str, 'Calories')
    data['fat_g'] = extract_nutrition_value(nutrition_str, 'Fat')
    data['saturated_fat_g'] = extract_nutrition_value(nutrition_str, 'Saturated fat')
    data['carbs_g'] = extract_nutrition_value(nutrition_str, 'Carbs')
    data['sugar_g'] = extract_nutrition_value(nutrition_str, 'Sugar')
    data['fiber_g'] = extract_nutrition_value(nutrition_str, 'Fiber')
    data['protein_g'] = extract_nutrition_value(nutrition_str, 'Protein')
    data['sodium_mg'] = extract_nutrition_value(nutrition_str, 'Sodium')
    data['cholesterol_mg'] = extract_nutrition_value(nutrition_str, 'Cholesterol')
    
    # Join ingredients and directions as text
    ingredients = recipe.get('ingredients', [])
    if ingredients:
        data['ingredients'] = '\n'.join(str(i) for i in ingredients)
    else:
        data['ingredients'] = ''
    
    directions = recipe.get('directions', [])
    if directions:
        # Filter out empty strings and join
        directions_clean = [str(d) for d in directions if str(d).strip()]
        data['directions'] = '\n'.join(directions_clean)
    else:
        data['directions'] = ''
    
    # Count ingredients and steps
    data['ingredient_count'] = len([i for i in ingredients if str(i).strip() and not str(i).strip().endswith(':')])
    data['step_count'] = len([d for d in directions if str(d).strip()])
    
    return data


def find_yaml_files(input_path):
    """Find YAML files from a folder or zip file"""
    path = Path(input_path)
    
    # If it's a directory, just glob for YAML files
    if path.is_dir():
        return list(path.glob('*.yml')) + list(path.glob('*.yaml'))
    
    # If it's a zip file, extract to temp directory
    elif path.suffix.lower() == '.zip':
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        yaml_files = list(Path(temp_dir).glob('*.yml')) + list(Path(temp_dir).glob('*.yaml'))
        return yaml_files
    
    else:
        raise ValueError(f"Input must be a directory or zip file, got: {input_path}")


def convert_cookbook_yaml_to_excel(input_path, output_dir):
    """Main conversion function"""
    
    print(f"Finding YAML files in: {input_path}")
    yaml_files = find_yaml_files(input_path)
    print(f"Found {len(yaml_files)} recipe files\n")
    
    if not yaml_files:
        print("No YAML files found!")
        return
    
    print("Parsing recipes...")
    recipes_data = []
    errors = []
    
    for i, yaml_file in enumerate(yaml_files, 1):
        try:
            recipe_data = parse_recipe_file(yaml_file)
            recipes_data.append(recipe_data)
            if i % 50 == 0:
                print(f"  Processed {i}/{len(yaml_files)} recipes...")
        except Exception as e:
            errors.append((yaml_file.name, str(e)))
            print(f"  ERROR parsing {yaml_file.name}: {e}")
    
    print(f"\nSuccessfully parsed {len(recipes_data)} recipes")
    if errors:
        print(f"Errors: {len(errors)}")
        for filename, error in errors[:5]:  # Show first 5 errors
            print(f"  - {filename}: {error}")
    
    # Create DataFrame
    df = pd.DataFrame(recipes_data)
    
    # Sort by name
    df = df.sort_values('name').reset_index(drop=True)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Full version - all columns
    full_excel = f"{output_dir}/cookbook_recipes.xlsx"
    full_csv = f"{output_dir}/cookbook_recipes.csv"
    
    df.to_excel(full_excel, index=False)
    df.to_csv(full_csv, index=False)
    
    # Simplified version - key fields only
    simple_cols = [
        'name', 'description', 'servings', 'source_url',
        'prep_time_min', 'cook_time_min', 'total_time_min',
        'tags', 'calories', 'protein_g', 'carbs_g', 'fat_g',
        'ingredient_count', 'step_count', 'cook_count'
    ]
    df_simple = df[simple_cols]
    simple_excel = f"{output_dir}/cookbook_recipes_simple.xlsx"
    df_simple.to_excel(simple_excel, index=False)
    
    # Print summary
    print("\n" + "="*70)
    print("CONVERSION COMPLETE")
    print("="*70)
    print(f"Total recipes: {len(df)}")
    print(f"Average prep time: {df['prep_time_min'].mean():.1f} minutes") if df['prep_time_min'].notna().any() else None
    print(f"Average cook time: {df['cook_time_min'].mean():.1f} minutes") if df['cook_time_min'].notna().any() else None
    print(f"Average calories: {df['calories'].mean():.0f}") if df['calories'].notna().any() else None
    print(f"Recipes with tags: {(df['tags'] != '').sum()}")
    print(f"Recipes cooked: {(df['cook_count'] > 0).sum()}")
    print("\nOutput files created:")
    print(f"  • {full_excel}")
    print(f"  • {full_csv}")
    print(f"  • {simple_excel}")
    print("="*70)
    
    # Show sample recipes
    print("\nSample recipes (first 5):")
    print("-"*70)
    for idx, row in df.head(5).iterrows():
        print(f"\n{row['name']}")
        if row['tags']:
            print(f"  Tags: {row['tags']}")
        if row['total_time_min']:
            print(f"  Time: {row['total_time_min']} min")
        if row['calories']:
            print(f"  Calories: {row['calories']:.0f}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = INPUT_PATH
    
    # Run the conversion
    try:
        convert_cookbook_yaml_to_excel(input_path, OUTPUT_DIR)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

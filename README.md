# Recipe Management Scripts

A collection of Python scripts for extracting, converting, and managing recipes from various sources into the [CookBook app](https://www.cooklang.org/) YAML format.

## Overview

This toolkit handles the complete workflow of recipe management:
- Extract recipes from PDF cookbooks (including OCR for scanned PDFs)
- Convert recipes from various formats (text, CSV, web scraping)
- Import recipes into CookBook app
- Export and manage CookBook recipe collections

## Repository Structure

```
.
├── scripts/
│   ├── pdf_processing/          # PDF recipe extraction
│   ├── import_export/           # Format conversion & import
│   └── utilities/               # Helper tools
├── samples/
│   ├── reference/               # Format examples
│   ├── yaml_examples/           # Sample recipe outputs
│   └── image_examples/          # Sample extracted images
└── README.md
```

## Scripts

### PDF Processing

**recipe_parse_export_v3_13_forceocr.py**
- Main PDF parser with forced OCR capability
- Extracts recipes from PDF cookbooks (tested extensively with "The Woks of Life" cookbook)
- Outputs: YAML files, CSV export, extracted images
- Handles both text-based and scanned PDFs

**Diagnostic Tools:**
- `check_page_extraction.py` - Verify PDF text extraction quality
- `check_pdf_text_layer.py` - Check if PDF has embedded text layer
- `find_pdf_page_width.py` - Get PDF page dimensions for layout analysis

### Import/Export

**recipe_import_universal_v1.1.py**
- Universal recipe importer supporting multiple input formats
- Converts various recipe formats to CookBook YAML
- Handles text files, CSV, and structured data

**cookbook_auto_import v2.py**
- Automated bulk import into CookBook app via plugin
- Processes multiple recipes in batch
- Requires CookBook app with Python plugin enabled

**cookbook_yaml_to_excel.py**
- Export CookBook YAML recipes to CSV/Excel format
- Useful for analysis, backup, or migration

### Utilities

**cookbook_diff.py**
- Compare recipes already in CookBook vs recipe files
- Identifies which recipes still need to be imported
- Prevents duplicate imports

**clean_recipe_urls.py**
- Clean and standardize recipe source URLs
- Removes tracking parameters and normalizes formats

**scrape_anylist.py + config.py**
- Web scraper for AnyList recipe format
- Requires configuration in `config.py`

## Requirements

```bash
# Core dependencies
pip install PyPDF2 pytesseract Pillow pandas pyyaml --break-system-packages

# For OCR functionality
brew install tesseract  # macOS
# or
apt-get install tesseract-ocr  # Linux
```

## Usage Examples

### Extract recipes from PDF cookbook

```bash
python recipe_parse_export_v3_13_forceocr.py cookbook.pdf
```

Outputs:
- Individual YAML files per recipe
- Combined CSV export
- Extracted recipe images

### Import recipes into CookBook app

```bash
python cookbook_auto_import\ v2.py /path/to/yaml/files
```

### Check what's not yet imported

```bash
python cookbook_diff.py
```

### Convert CookBook recipes to Excel

```bash
python cookbook_yaml_to_excel.py
```

## Sample Files

The `samples/` directory contains:
- **BulkImportExampleCSVFormat.csv** - Reference format for bulk imports
- **yaml_examples/** - Sample recipes showing simple, medium, and complex structures
- **image_examples/** - Examples of images extracted from PDFs

## CookBook YAML Format

Recipes are stored in YAML format compatible with the CookBook app:

```yaml
title: Recipe Name
source: Source URL or Book
servings: 4
ingredients:
  - 2 cups flour
  - 1 tsp salt
instructions:
  - Mix dry ingredients
  - Add wet ingredients
  - Bake at 350°F
notes: Optional cooking notes
tags:
  - dinner
  - vegetarian
```

## Notes

- PDF processing works best with well-formatted recipe books
- OCR is slower but handles scanned PDFs
- CookBook import scripts require the CookBook app installed
- All scripts tested on macOS; should work on Linux with minor adjustments

## Development

Originally developed through iterative testing with ChatGPT (PDF processing) and Claude (organization/utilities). The messy iterations and abandoned attempts have been cleaned up - this repo contains only the working, tested scripts.

## License

Personal use scripts - use at your own risk. No warranty provided.

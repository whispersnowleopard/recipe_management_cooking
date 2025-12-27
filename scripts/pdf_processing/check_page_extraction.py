import pdfplumber
from recipe_parse_export_v3_2 import extract_columns_from_page, clean_utf8_text

pdf = pdfplumber.open("TheWoksofLife-Top25Recipes_compressed.pdf")
page = pdf.pages[6]  # first recipe
left, right = extract_columns_from_page(page)
left = clean_utf8_text(left)
right = clean_utf8_text(right)

print("=== LEFT COLUMN (Ingredients) ===")
print(left[:1000])
print("\n=== RIGHT COLUMN (Title + Intro + Directions) ===")
print(right[:1000])
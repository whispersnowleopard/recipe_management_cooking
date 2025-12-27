#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recipe_parse_export_v3_13_forceocr.py
------------------------------------------------------------
Specialized parser for “The Woks of Life – Top 25 Recipes” PDF.

Extracts structured recipe data into YAML and CookBook CSV formats.
Adds auto or forced OCR fallback, cleans UTF-8 artifacts, strips
footers, and handles bullet characters gracefully.

🔧 PREREQUISITES
------------------------------------------------------------
Install these once (macOS example):

    brew install tesseract
    pip install pdfplumber pytesseract Pillow PyYAML pandas

⚙️ USAGE
------------------------------------------------------------
Example:
    python3 recipe_parse_export_v3_13_forceocr.py \
        --input "TheWoksofLife-Top25Recipes_compressed.pdf" \
        --outdir ./out_v3_13 \
        --ocr-debug

Optional flags:
    --force-ocr      → Run OCR on *every* recipe page
    --ocr-debug      → Show garble scores and OCR usage info

🧠 CONFIG
------------------------------------------------------------
    START_PAGE = 6
    LEFT_COLUMN_XMAX = 280
    RIGHT_COLUMN_XMIN = 280
    PAGE_WIDTH_EXPECTED = 768
    GARBLED_THRESHOLD = 0.25
    SOURCE_URL = "https://thewoksoflife.com"

🪪 NOTES
------------------------------------------------------------
• OCR fallback replaces unreadable characters with “[unk]”.
• Bullet points “•” or “-” are stripped from ingredients.
• “THE WOKS OF LIFE | TOP 25 RECIPES [page]” footer is removed from all text.
• Title cleanup trims leaked words like “It’s” or “As …”.
"""

# ------------------------------------------------------------
# Imports & Config
# ------------------------------------------------------------

import os, re, sys
from collections import defaultdict
import pdfplumber
import pandas as pd
import yaml
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

# --- Config constants ---
START_PAGE = 6
LEFT_COLUMN_XMAX = 280
RIGHT_COLUMN_XMIN = 280
PAGE_WIDTH_EXPECTED = 768
GARBLED_THRESHOLD = 0.25
SOURCE_URL = "https://thewoksoflife.com"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\\-_\\s]", "", value)
    value = value.strip().lower().replace(" ", "-")
    return re.sub(r"-+", "-", value)

def clean_utf8_text(txt: str) -> str:
    """Fix UTF-8 artifacts, normalize to ASCII where possible."""
    fixes = {
        "â€™": "’", "â€œ": "“", "â€": "”", "â€“": "-", "â€”": "–",
        "Â½": "½", "Â¼": "¼", "Â¾": "¾", "Âº": "º", "Â°": "°",
        "Ã©": "é", "Ã¨": "è", "Ã¢": "â", "Ã®": "î", "Ã´": "ô",
        "Ã¶": "ö", "Ã¼": "ü", "Ã": "à", "Â": "",
        "‚Ä¢": "•", "‚Äôs": "’s", "‚Äì": "-", "¬Ω": "1/2",
        "‚Öî": "1/3", "¬æ": "3/4", "¬º": "1/8"
    }
    for bad, good in fixes.items():
        txt = txt.replace(bad, good)
    txt = ''.join(ch if 32 <= ord(ch) <= 126 or ch in "\n\r\t–—’•" else "[unk]" for ch in txt)
    txt = re.sub(r'\s{2,}', ' ', txt)
    return txt.strip()

def text_garble_score(txt: str) -> float:
    """Estimate corruption level of extracted text."""
    if not txt.strip():
        return 1.0
    weird = sum(ch not in "\n\r\t" and (ord(ch) > 126 or ord(ch) < 9) for ch in txt)
    return weird / max(1, len(txt))

# ------------------------------------------------------------
# PDF text extraction with OCR fallback
# ------------------------------------------------------------

def extract_columns_from_page(page):
    words = page.extract_words()
    if not words:
        return "", ""
    left_words = [w for w in words if w["x0"] < LEFT_COLUMN_XMAX]
    right_words = [w for w in words if w["x0"] >= RIGHT_COLUMN_XMIN]
    def join_column(ws):
        lines = defaultdict(list)
        for w in ws:
            key = round(w["top"], 0)
            lines[key].append(w["text"])
        ordered = [" ".join(lines[y]) for y in sorted(lines)]
        return "\n".join(ordered)
    return join_column(left_words), join_column(right_words)

def extract_text_from_pdf(path, ocr_debug=False, force_ocr=False):
    results = []
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f"[Info] PDF opened: {total_pages} pages total.")
        for i in range(START_PAGE, total_pages):
            if (i - START_PAGE) % 2 == 1:
                continue
            page = pdf.pages[i]
            left, right = extract_columns_from_page(page)
            combined = clean_utf8_text(left + right)
            garble_score = text_garble_score(combined)

            if ocr_debug:
                print(f"[Debug] Page {i+1}: garble_score={garble_score:.2f}")

            if pytesseract and (force_ocr or garble_score > GARBLED_THRESHOLD):
                try:
                    img = page.to_image(resolution=200).original
                    ocr_txt = pytesseract.image_to_string(img)
                    left, right = split_ocr_text(ocr_txt)
                    if ocr_debug:
                        print(f"[OCR] Page {i+1}: OCR used (force={force_ocr}, score={garble_score:.2f})")
                except Exception as e:
                    print(f"[Warn] OCR failed on page {i+1}: {e}")

            left, right = clean_utf8_text(left), clean_utf8_text(right)
            results.append((i + 1, left, right))
    print(f"[Info] Extracted {len(results)} recipe pages.")
    return results

def split_ocr_text(txt: str):
    """Naive fallback split if OCR output isn’t column-aware."""
    lines = txt.splitlines()
    mid = len(lines)//2
    return "\n".join(lines[:mid]), "\n".join(lines[mid:])

# ------------------------------------------------------------
# Recipe parsing
# ------------------------------------------------------------

def parse_recipe_text(left_text, right_text, page_num):
    recipe = {
        "title": "",
        "course": "",
        "description": "",
        "source": SOURCE_URL,
        "prep_time": "",
        "cook_time": "",
        "total_time": "",
        "servings": "",
        "yield": "",
        "ingredients": [],
        "directions": "",
        "tags": [],
        "rating": "",
        "photo_url": "",
        "calories": "",
        "fat": "",
        "cholesterol": "",
        "sodium": "",
        "sugar": "",
        "carbohydrate": "",
        "fiber": "",
        "protein": "",
        "cost": "",
        "created_at": "",
        "updated_at": "",
    }

    # --- Servings ---
    m = re.search(r"(SERVES|MAKES)\s+([0-9½¼¾]+)", left_text, re.I)
    if m:
        recipe["servings"] = m.group(2).strip()

    # --- Title ---
    lines = [ln.strip() for ln in right_text.splitlines() if ln.strip()]
    title_lines = []
    for ln in lines:
        if re.search(r"[a-z]", ln):
            break
        if re.match(r"^[#\d:\-\sA-Z]+$", ln):
            title_lines.append(ln)
    title_joined = " ".join(title_lines).strip()
    title_joined = re.sub(r"^#?\s*\d*[:\-]?\s*", "", title_joined)
    title_joined = re.sub(r"\b(It|As|Despite)\b.*", "", title_joined).strip()
    recipe["title"] = title_joined or "Untitled Recipe"

    # --- Remove footer ---
    right_text = re.sub(r"THE WOKS OF LIFE\s*\|.*", "", right_text, flags=re.I)

    # --- Description + Directions ---
    desc_lines, dir_lines = [], []
    step_triggers = re.compile(
        r"^(In a|Add|Heat|Pour|Mix|Whisk|Combine|Cook|Meanwhile|Stir|Serve|Transfer|Preheat)",
        re.I,
    )
    in_directions = False
    for ln in lines:
        if ln in title_lines:
            continue
        if step_triggers.match(ln):
            in_directions = True
        if in_directions:
            dir_lines.append(ln)
        else:
            desc_lines.append(ln)

    # Remove footers from description/directions
    def strip_footer(txt):
        return re.sub(r"THE WOKS OF LIFE\s*\|.*", "", txt, flags=re.I).strip()
    recipe["description"] = strip_footer(" ".join(desc_lines))
    recipe["directions"] = strip_footer(" ".join(dir_lines))

    # --- Ingredients ---
    left_text = re.sub(r"(\w)-\s+(\w)", r"\1\2", left_text)
    left_lines = [ln.strip("• \t") for ln in left_text.splitlines()]
    ing_lines = []
    for ln in left_lines:
        if not ln or re.match(r"^(SERVES|MAKES|YIELD)", ln, re.I):
            continue
        ln = re.sub(r"^\[unk\]\s*", "", ln)  # remove stray [unk] bullets
        if ing_lines and not re.search(r"[0-9/]", ln) and len(ln.split()) < 3:
            ing_lines[-1] += " " + ln
        else:
            ing_lines.append(ln)
    recipe["ingredients"] = ing_lines

    # --- Tags ---
    txt = (recipe["title"] + " " + recipe["description"] + " " + recipe["directions"]).lower()
    tags = []
    if "thai" in txt or "curry" in txt:
        tags.append("thai")
    if "chinese" in txt or "soy" in txt or "lo mein" in txt:
        tags.append("chinese")
    if "quick" in txt or "minute" in txt or "easy" in txt:
        tags.append("quick")
    if "vegetarian" in txt or "tofu" in txt:
        tags.append("vegetarian")
    recipe["tags"] = sorted(set(tags))

    recipe["title"] += f" (Page {page_num})"
    return recipe

# ------------------------------------------------------------
# Exports
# ------------------------------------------------------------

def export_yaml(recipe, outdir, index):
    fname = slugify(recipe["title"]) or f"recipe-{index+1}"
    path = os.path.join(outdir, f"{fname}.yml")
    data = {
        "title": recipe["title"],
        "description": recipe["description"],
        "source": recipe["source"],
        "prep_time": recipe["prep_time"],
        "cook_time": recipe["cook_time"],
        "total_time": recipe["total_time"],
        "servings": recipe["servings"],
        "yield": recipe["yield"],
        "ingredients": recipe["ingredients"],
        "directions": recipe["directions"],
        "tags": recipe["tags"],
        "nutrition": {
            "calories": recipe["calories"],
            "fat": recipe["fat"],
            "cholesterol": recipe["cholesterol"],
            "sodium": recipe["sodium"],
            "sugar": recipe["sugar"],
            "carbohydrate": recipe["carbohydrate"],
            "fiber": recipe["fiber"],
            "protein": recipe["protein"],
        },
        "photos": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path

def export_csv(recipes, outdir):
    csv_path = os.path.join(outdir, "recipes_export.csv")
    cols = [
        "Title","Course","Description","Source","Prep Time","Cook Time","Total Time",
        "Servings","Yield","Ingredients","Directions","Tags","Rating","Photo Url",
        "Calories","Fat","Cholesterol","Sodium","Sugar","Carbohydrate","Fiber",
        "Protein","Cost","Created At","Updated At"
    ]
    rows = []
    for r in recipes:
        rows.append({
            "Title": r["title"], "Course": r["course"], "Description": r["description"],
            "Source": r["source"], "Prep Time": r["prep_time"], "Cook Time": r["cook_time"],
            "Total Time": r["total_time"], "Servings": r["servings"], "Yield": r["yield"],
            "Ingredients": "\n".join(r["ingredients"]), "Directions": r["directions"],
            "Tags": ";".join(r["tags"]), "Rating": r["rating"], "Photo Url": r["photo_url"],
            "Calories": r["calories"], "Fat": r["fat"], "Cholesterol": r["cholesterol"],
            "Sodium": r["sodium"], "Sugar": r["sugar"], "Carbohydrate": r["carbohydrate"],
            "Fiber": r["fiber"], "Protein": r["protein"], "Cost": r["cost"],
            "Created At": r["created_at"], "Updated At": r["updated_at"],
        })
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parse Woks of Life PDF recipes into CookBook-compatible CSV/YAML.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", default="./out")
    parser.add_argument("--ocr-debug", action="store_true")
    parser.add_argument("--force-ocr", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    pages = extract_text_from_pdf(args.input, ocr_debug=args.ocr_debug, force_ocr=args.force_ocr)
    recipes = []
    for idx, (page_num, left, right) in enumerate(pages):
        recipe = parse_recipe_text(left, right, page_num)
        recipes.append(recipe)
        print(f"[{idx+1}/{len(pages)}] Page {page_num}: Parsed {recipe['title']} ✅")
        export_yaml(recipe, args.outdir, idx)
    csv_path = export_csv(recipes, args.outdir)
    print(f"\n[Done] Export complete:\n - YAML: {len(recipes)} files\n - CSV: {csv_path}")

if __name__ == "__main__":
    main()
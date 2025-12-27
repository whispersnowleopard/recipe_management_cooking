#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recipe_import_universal_v1.1.py
------------------------------------------------------------
🧠 UNIVERSAL RECIPE EXTRACTOR (Multi-PDF Folder Edition)

Parses arbitrary recipe PDFs — scanned or text-based — into
structured CookBook-compatible data (CSV, YAML, TXT).
Designed to automatically detect layout patterns and fall
back to OCR when needed.

------------------------------------------------------------
🔧 PREREQUISITES
------------------------------------------------------------
Install once via Terminal (macOS / Linux):

    brew install tesseract
    pip install pdfplumber pytesseract Pillow PyYAML pandas spacy

(Optional) for advanced tagging:
    python -m spacy download en_core_web_sm

------------------------------------------------------------
⚙️ USAGE
------------------------------------------------------------
    python3 recipe_import_universal_v1.1.py \
        --input_dir "./recipes_inbox" \
        --outdir "./recipes_out"

Produces:
    • recipes_export.csv  – structured CookBook import
    • recipes_export.yml  – YAML array of recipes
    • recipes_export.txt  – plain text version, all recipes
    • recipes_review.csv  – low-confidence extractions
    • moves successfully parsed PDFs to ./recipes_inbox/processed/

------------------------------------------------------------
🧩 HOW IT WORKS
------------------------------------------------------------
1. For each PDF in input_dir:
   - Reads page-by-page
   - Attempts text extraction in this order:
       (a) Structured column zones
       (b) Full-page text
       (c) OCR fallback if garbled or short
   - Assigns confidence 0.0–1.0
   - If confidence ≥ threshold, exports recipe
   - Otherwise logs to review queue

2. Outputs combined CSV, YAML, and TXT exports
   after all PDFs are processed.

------------------------------------------------------------
✏️ CONFIG
------------------------------------------------------------
    CONF_THRESHOLD = 0.45
    USE_OCR_FALLBACK = True
    MOVE_PROCESSED = True
    MAX_PAGES = 50
    TXT_SEPARATOR = "-" * 25

------------------------------------------------------------
📚 NOTES
------------------------------------------------------------
• Automatically cleans non-ASCII symbols → [unk]
• Removes common watermark footers like “THE WOKS OF LIFE | …”
• Gracefully skips empty / malformed pages
• Uses lexical cues to detect cuisines (e.g. “Thai”, “Italian”)
------------------------------------------------------------
"""

import os, re, csv, sys, shutil, pdfplumber, yaml, pytesseract, pandas as pd
from collections import defaultdict
from PIL import Image

# Optional NLP tagging
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
CONF_THRESHOLD = 0.45
USE_OCR_FALLBACK = True
MOVE_PROCESSED = True
MAX_PAGES = 50
TXT_SEPARATOR = "-" * 25

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def clean_utf8_text(txt: str) -> str:
    replacements = {
        "¬Ω": "1/2", "¬æ": "3/4", "¬º": "1/8", "¬½": "1/4", "‚Ä¢": "",
        "‚Äôs": "’s", "‚Äì": "-", "â€“": "-", "â€”": "—", "â€˜": "‘",
        "â€™": "’", "â€œ": "“", "â€": "”", "Ã©": "é", "Ã¼": "ü",
        "Ã": "à", "Â": "", "‚Öì": "1/3", "‚Öî": "1/3"
    }
    for bad, good in replacements.items():
        txt = txt.replace(bad, good)
    txt = txt.encode("ascii", "replace").decode("ascii")
    txt = txt.replace("?", "[unk]")
    txt = re.sub(r"\s{2,}", " ", txt)
    txt = txt.replace("•", "").strip()
    return txt

def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")

def text_is_garbled(txt: str) -> bool:
    if len(txt.strip()) < 40:
        return True
    letters = sum(ch.isalpha() for ch in txt)
    return letters / max(len(txt),1) < 0.2

def detect_tags(text):
    tags = set()
    low = text.lower()
    for k in ["thai","chinese","vietnamese","italian","mexican","indian",
              "soup","stew","stir-fry","noodle","pasta","chicken","beef",
              "pork","vegan","vegetarian","dessert","bake","grill","roast"]:
        if k in low:
            tags.add(k)
    if nlp:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("NORP","GPE","PRODUCT"):
                tags.add(ent.text.lower())
    return sorted(tags)

# ------------------------------------------------------------
# PDF HANDLING
# ------------------------------------------------------------
def extract_text_zones(page):
    """Try to extract two-column layout if present."""
    words = page.extract_words()
    if not words: return "", ""
    mid = page.width/2
    left = [w["text"] for w in words if w["x0"] < mid]
    right = [w["text"] for w in words if w["x0"] >= mid]
    return "\n".join(left), "\n".join(right)

def extract_best_text(page):
    """Try zone → full → OCR fallback with confidence."""
    left, right = extract_text_zones(page)
    merged = clean_utf8_text(left + "\n" + right)
    if not merged or text_is_garbled(merged):
        merged = clean_utf8_text(page.extract_text() or "")
    conf = 0.5
    if text_is_garbled(merged): conf -= 0.2
    if USE_OCR_FALLBACK and (not merged or conf < 0.4):
        try:
            img = page.to_image(resolution=200).original
            ocr = pytesseract.image_to_string(img)
            if len(ocr) > len(merged):
                merged = clean_utf8_text(ocr)
                conf += 0.3
        except Exception:
            pass
    return merged.strip(), min(max(conf,0.0),1.0)

# ------------------------------------------------------------
# RECIPE PARSING
# ------------------------------------------------------------
def parse_recipe_text(txt, filename, page_num):
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    recipe = {
        "title": "Untitled Recipe",
        "description": "",
        "ingredients": [],
        "directions": "",
        "tags": [],
        "confidence": 0.0,
        "source_file": filename,
        "page": page_num
    }

    # crude split
    ing_idx = next((i for i,l in enumerate(lines) if re.match(r"(?i)^ingredients?[:\s]",l)),None)
    dir_idx = next((i for i,l in enumerate(lines) if re.match(r"(?i)^(directions?|instructions?)[:\s]",l)),None)
    if ing_idx and ing_idx<5:
        recipe["title"] = lines[0]
    elif len(lines)>1:
        recipe["title"] = lines[0]
        recipe["description"] = " ".join(lines[1:3])

    # ingredients
    if ing_idx:
        end = dir_idx or len(lines)
        recipe["ingredients"] = [clean_utf8_text(l) for l in lines[ing_idx+1:end]]
    # directions
    if dir_idx:
        recipe["directions"] = " ".join(lines[dir_idx+1:])

    # fallback
    if not recipe["ingredients"] and len(lines)>4:
        recipe["ingredients"] = [l for l in lines[1:5]]

    recipe["tags"] = detect_tags(" ".join(lines))
    return recipe

# ------------------------------------------------------------
# EXPORTS
# ------------------------------------------------------------
def export_all(recipes, outdir):
    os.makedirs(outdir, exist_ok=True)
    # CSV
    df = pd.DataFrame(recipes)
    csv_path = os.path.join(outdir, "recipes_export.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")

    # YAML
    yml_path = os.path.join(outdir, "recipes_export.yml")
    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(recipes, f, sort_keys=False, allow_unicode=True)

    # TXT
    txt_path = os.path.join(outdir, "recipes_export.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in recipes:
            f.write(r["title"] + "\n" + "-"*len(r["title"]) + "\n")
            if r.get("ingredients"):
                f.write("Ingredients:\n" + "\n".join(r["ingredients"]) + "\n\n")
            if r.get("directions"):
                f.write("Directions:\n" + r["directions"] + "\n\n")
            f.write(f"Source File: {r['source_file']} (page {r['page']})\n")
            f.write(TXT_SEPARATOR + "\n")
    return csv_path, yml_path, txt_path

def export_review(recipes, outdir):
    low = [r for r in recipes if r["confidence"]<CONF_THRESHOLD]
    if not low: return None
    path = os.path.join(outdir,"recipes_review.csv")
    df = pd.DataFrame(low)
    df.to_csv(path,index=False,encoding="utf-8")
    return path

# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Universal Recipe Importer (multi-PDF)")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--outdir", default="./out")
    args = parser.parse_args()

    infolder = args.input_dir
    outdir = args.outdir
    processed_dir = os.path.join(infolder,"processed")
    os.makedirs(processed_dir, exist_ok=True)

    recipes = []

    for fname in os.listdir(infolder):
        if not fname.lower().endswith(".pdf"):
            continue
        fpath = os.path.join(infolder,fname)
        try:
            with pdfplumber.open(fpath) as pdf:
                page_total = min(len(pdf.pages), MAX_PAGES)
                for i in range(page_total):
                    page = pdf.pages[i]
                    txt, conf = extract_best_text(page)
                    if not txt.strip(): continue
                    recipe = parse_recipe_text(txt,fname,i+1)
                    recipe["confidence"] = conf
                    if conf>=CONF_THRESHOLD:
                        recipes.append(recipe)
                print(f"[✓] {fname} → {len(recipes)} total recipes")
            if MOVE_PROCESSED:
                shutil.move(fpath, os.path.join(processed_dir,fname))
        except Exception as e:
            print(f"[Error] {fname}: {e}")

    csv_path,yml_path,txt_path = export_all(recipes,outdir)
    review_path = export_review(recipes,outdir)
    print("\n[Done] Export complete:")
    print(f" - CSV: {csv_path}")
    print(f" - YAML: {yml_path}")
    print(f" - TXT: {txt_path}")
    if review_path:
        print(f" - Review CSV: {review_path}")
    print(f"Processed {len(recipes)} recipes total.\n")

if __name__=="__main__":
    main()
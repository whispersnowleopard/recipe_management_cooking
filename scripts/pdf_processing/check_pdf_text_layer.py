import pdfplumber
path = "TheWoksofLife-Top25Recipes_compressed.pdf"
pdf = pdfplumber.open(path)
page = pdf.pages[6]  # zero-based, so this should be the first recipe page
print("Page width:", page.width)
print("Extracted words sample:")
print(page.extract_words()[:20])
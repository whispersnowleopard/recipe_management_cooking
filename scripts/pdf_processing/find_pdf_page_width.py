import pdfplumber
pdf = pdfplumber.open("TheWoksofLife-Top25Recipes_compressed.pdf")
print(pdf.pages[6].width)
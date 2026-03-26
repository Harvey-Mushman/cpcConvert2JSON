import pdfplumber
from pathlib import Path

pdf_folder = Path("./certificates")
files = sorted(pdf_folder.glob("*.pdf"))

if not files:
    print("No PDF files found in ./certificates")
    exit()

print("Which PDF to check?")
print("  0 - Check ALL files")
for i, f in enumerate(files, start=1):
    print(f"  {i} - {f.name}")

choice = input("Enter number: ").strip()

if choice == "0":
    targets = files
elif choice.isdigit() and 1 <= int(choice) <= len(files):
    targets = [files[int(choice) - 1]]
else:
    print("Invalid choice. Exiting.")
    exit()

for pdf_file in targets:
    print(f"\n{pdf_file.name}")
    print("-" * 50)
    with pdfplumber.open(pdf_file) as pdf:
        total = len(pdf.pages)
        text_pages = 0
        image_pages = 0
        mixed_pages = 0
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            has_text = len(text.strip()) > 0
            has_images = len(page.images) > 0
            if has_text and has_images:
                status = "TEXT + IMAGE (mixed)"
                mixed_pages += 1
            elif has_text:
                status = "TEXT searchable"
                text_pages += 1
            elif has_images:
                status = "SCANNED IMAGE only"
                image_pages += 1
            else:
                status = "EMPTY"
            print(f"  Page {i:02d}/{total}: {status}")

    print(f"\n  Summary: {text_pages} text | {image_pages} scanned | {mixed_pages} mixed | {total} total")
    if image_pages > 0 or mixed_pages > 0:
        print(f"  WARNING: scanned pages cannot be converted without OCR software.")

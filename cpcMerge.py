import json
from pathlib import Path

page_output_folder = Path("./page_output")
json_output_folder = Path("./json_output")
json_output_folder.mkdir(exist_ok=True)

cert_folder = Path("./certificates")
all_folders = sorted([f for f in page_output_folder.iterdir() if f.is_dir()])
if not all_folders:
    print("No page_output folders found. Run cpcConvert.py first.")
    exit()

# Determine which page_output folders have a matching file in certificates/
cert_files = set()
if cert_folder.exists():
    for f in cert_folder.iterdir():
        if f.is_file() and f.suffix.lower() in (".pdf", ".xls", ".xlsx"):
            cert_files.add(f.stem)

new_folders = [f for f in all_folders if f.name in cert_files]
prior_folders = [f for f in all_folders if f.name not in cert_files]

# Build the menu
print("Which CPC to merge?")
print(f"\n  0 - Merge ALL ({len(all_folders)} folders)")
idx = 1

if new_folders:
    print(f"\n  --- New (in certificates/) ---")
    new_start = idx
    for f in new_folders:
        print(f"  {idx} - {f.name}")
        idx += 1

if prior_folders:
    print(f"\n  --- Prior runs (not in certificates/) ---")
    prior_start = idx
    for f in prior_folders:
        print(f"  {idx} - {f.name}")
        idx += 1

total = idx - 1
choice = input("\nEnter number: ").strip()
if choice == "0":
    folders = all_folders
elif choice.isdigit() and 1 <= int(choice) <= total:
    # Map choice number back to the correct folder
    c = int(choice)
    combined = new_folders + prior_folders
    folders = [combined[c - 1]]
else:
    print("Invalid choice. Exiting.")
    exit()

LIST_FIELDS = {"production_sites", "storage_locations", "authorized_counties",
               "authorized_representatives", "producers_selling_for_me",
               "producers_i_sell_for", "commodities"}

for pdf_folder in folders:
    print(f"\nMerging: {pdf_folder.name}")

    page_files = sorted(pdf_folder.glob("page_*.json"))
    if not page_files:
        print("  No page files found, skipping.")
        continue

    merged = {}

    for page_file in page_files:
        data = json.loads(page_file.read_text())
        for key, value in data.items():
            if key in LIST_FIELDS:
                # Accumulate list fields across all pages
                if key not in merged:
                    merged[key] = []
                if isinstance(value, list):
                    merged[key].extend(value)
            elif key == "producer" and isinstance(value, dict):
                # Merge producer fields, first value wins
                if "producer" not in merged:
                    merged["producer"] = {}
                for k, v in value.items():
                    if k not in merged["producer"] or not merged["producer"][k]:
                        merged["producer"][k] = v
            else:
                # Scalar fields — first page value wins
                if key not in merged or not merged[key]:
                    merged[key] = value

    output_file = json_output_folder / f"{pdf_folder.name}.json"
    output_file.write_text(json.dumps(merged, indent=2, ensure_ascii=False))

    commodity_count = len(merged.get("commodities", []))
    print(f"  {commodity_count} commodities merged into {output_file.name}")

print("\nMerge complete.")

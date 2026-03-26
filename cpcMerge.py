import json
from pathlib import Path

page_output_folder = Path("./page_output")
json_output_folder = Path("./json_output")
json_output_folder.mkdir(exist_ok=True)

all_folders = sorted([f for f in page_output_folder.iterdir() if f.is_dir()])
if not all_folders:
    print("No page_output folders found. Run cpcConvert.py first.")
    exit()

print("Which CPC to merge?")
print("  0 - Merge ALL")
for i, f in enumerate(all_folders, start=1):
    print(f"  {i} - {f.name}")

choice = input("Enter number: ").strip()
if choice == "0":
    folders = all_folders
elif choice.isdigit() and 1 <= int(choice) <= len(all_folders):
    folders = [all_folders[int(choice) - 1]]
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

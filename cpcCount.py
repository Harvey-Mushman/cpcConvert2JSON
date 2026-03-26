import json
from pathlib import Path

page_output_folder = Path("./page_output")
json_output_folder = Path("./json_output")

# List available folders
folders = sorted([f for f in page_output_folder.iterdir() if f.is_dir()])
if not folders:
    print("No page_output folders found.")
    exit()

print("Which CPC to count?")
for i, f in enumerate(folders, start=1):
    print(f"  {i} - {f.name}")

choice = input("Enter number: ").strip()
if not choice.isdigit() or not (1 <= int(choice) <= len(folders)):
    print("Invalid choice. Exiting.")
    exit()

selected = folders[int(choice) - 1]

# Count per page
print(f"\nPage counts for: {selected.name}")
print("-" * 40)
page_total = 0
for page_file in sorted(selected.glob("page_*.json")):
    data = json.loads(page_file.read_text())
    count = 0
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == "commodities" and isinstance(v, list):
                count = len(v)
                break
    page_total += count
    print(f"  {page_file.name}: {count}")

print(f"  {'─'*30}")
print(f"  Page output total: {page_total}")

# Optionally count merged output
merged_file = json_output_folder / f"{selected.name}.json"
if merged_file.exists():
    answer = input(f"\nAlso count merged json_output file? (y/n): ").strip().lower()
    if answer == "y":
        data = json.loads(merged_file.read_text())
        merged_total = 0
        for k, v in data.items():
            if k.lower() == "commodities" and isinstance(v, list):
                merged_total = len(v)
                break
        print(f"  Merged output total: {merged_total}")
        diff = page_total - merged_total
        if diff == 0:
            print(f"  Match: page output and merged file have the same count.")
        else:
            print(f"  Difference: {diff} commodities missing from merged file!")
else:
    print(f"\n  No merged file found in json_output for this CPC.")

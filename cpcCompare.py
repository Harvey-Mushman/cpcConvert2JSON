import json
from pathlib import Path

json_output_folder = Path("./json_output")

# List available files
files = sorted(json_output_folder.glob("*.json"))
if not files:
    print("No files found in json_output.")
    exit()

print("Select files to compare (enter numbers separated by commas, e.g. 1,3,5):")
for i, f in enumerate(files, start=1):
    print(f"  {i} - {f.name}")

choices = input("Enter numbers: ").strip().split(",")
try:
    selected = [files[int(c.strip()) - 1] for c in choices if c.strip().isdigit()]
except IndexError:
    print("Invalid selection. Exiting.")
    exit()

if len(selected) < 2:
    print("Please select at least 2 files to compare.")
    exit()

def get_keys_flat(obj, prefix=""):
    """Recursively collect all keys from a dict, excluding list contents."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            if isinstance(v, dict):
                keys.update(get_keys_flat(v, full_key))
    return keys

def get_commodity_keys(data):
    """Get keys from the first commodity entry."""
    for k, v in data.items():
        if k.lower() == "commodities" and isinstance(v, list) and v:
            return set(v[0].keys())
    return set()

# Load all selected files
loaded = {}
for f in selected:
    loaded[f.stem] = json.loads(f.read_text())

names = list(loaded.keys())

# Collect keys per file
doc_keys    = {name: get_keys_flat(data) for name, data in loaded.items()}
commod_keys = {name: get_commodity_keys(data) for name, data in loaded.items()}

# Build report
report_file = Path("./label_comparison_report.txt")
lines = []

def r(line=""):
    lines.append(line)
    print(line)

r("=" * 60)
r("LABEL COMPARISON REPORT")
r(f"Files compared:")
for name in names:
    r(f"  - {name}")
r("=" * 60)

for section, key_sets in [("DOCUMENT FIELDS", doc_keys), ("COMMODITY FIELDS", commod_keys)]:
    r(f"\n{'─'*60}")
    r(f"{section}")
    r(f"{'─'*60}")

    all_keys = set()
    for ks in key_sets.values():
        all_keys.update(ks)

    in_all = sorted([k for k in all_keys if all(k in key_sets[n] for n in names)])
    partial = sorted([k for k in all_keys if not all(k in key_sets[n] for n in names)])

    r(f"\n  PRESENT IN ALL {len(names)} FILES ({len(in_all)} labels):")
    for k in in_all:
        r(f"    {k}")

    r(f"\n  PRESENT IN SOME FILES ONLY ({len(partial)} labels):")
    for k in partial:
        present_in = [n for n in names if k in key_sets[n]]
        missing_in = [n for n in names if k not in key_sets[n]]
        r(f"    {k}")
        r(f"      Found in:   {', '.join(present_in)}")
        r(f"      Missing in: {', '.join(missing_in)}")

r(f"\n{'='*60}")

report_file.write_text("\n".join(lines), encoding="utf-8")
print(f"\nReport saved to: {report_file}")

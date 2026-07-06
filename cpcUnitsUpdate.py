import json
import sqlite3
from pathlib import Path

DB_FILE = Path("./cpc.db")
NORMALIZED_FOLDER = Path("./json_normalized")


def load_valid_units():
    """Load unit_name values from the units table. Returns a dict of uppercase → canonical name."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT unit_name FROM units").fetchall()
    conn.close()
    return {row[0].upper(): row[0] for row in rows}


def get_units_list():
    """Return sorted list of (id, unit_name) for display."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT id, unit_name FROM units ORDER BY unit_name").fetchall()
    conn.close()
    return rows


def save_new_unit(unit_name):
    """Insert a new unit into the units table. Returns (id, name).
    If a unit with the same name (case-insensitive) already exists, returns that instead."""
    title_name = unit_name.strip().title()
    conn = sqlite3.connect(DB_FILE)
    existing = conn.execute(
        "SELECT id, unit_name FROM units WHERE UPPER(unit_name) = ?",
        (title_name.upper(),)).fetchone()
    if existing:
        unit_id, canonical = existing
        print(f"  Unit \"{canonical}\" already exists (id={unit_id}), adding alias only.")
    else:
        conn.execute("INSERT INTO units (unit_name) VALUES (?)", (title_name,))
        unit_id = conn.execute("SELECT id FROM units WHERE unit_name = ?",
                               (title_name,)).fetchone()[0]
        canonical = title_name
    conn.execute("INSERT OR IGNORE INTO unit_aliases (alias, unit_id) VALUES (?, ?)",
                 (unit_name.strip().upper(), unit_id))
    conn.commit()
    conn.close()
    return unit_id, canonical


def save_alias(alias, unit_id):
    """Insert a new alias into the unit_aliases table."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR IGNORE INTO unit_aliases (alias, unit_id) VALUES (?, ?)",
                 (alias.upper(), unit_id))
    conn.commit()
    conn.close()


def prompt_unknown_unit(raw_unit):
    """Ask user how to handle an unrecognized unit.
    Returns (unit_id, unit_name) — either existing or newly created."""
    valid = get_units_list()
    display = raw_unit.strip().title()
    print(f"\n  *** UNKNOWN UNIT: \"{raw_unit}\"")
    print(f"  Existing valid units:")
    for i, (uid, name) in enumerate(valid, 1):
        print(f"    {i:3d} - {name}")
    print(f"    {len(valid)+1:3d} - ** Accept \"{display}\" as a NEW valid unit **")

    while True:
        choice = input(f"  Map \"{display}\" to: ").strip()
        if choice.isdigit():
            c = int(choice)
            if 1 <= c <= len(valid):
                uid, name = valid[c - 1]
                return uid, name
            if c == len(valid) + 1:
                uid, title_name = save_new_unit(raw_unit)
                return uid, title_name
        print("  Invalid choice, try again.")


def scan_and_update():
    if not DB_FILE.exists():
        print(f"ERROR: {DB_FILE} not found. Run cpcBuildDB.py first.")
        return

    all_files = sorted(NORMALIZED_FOLDER.glob("*.json"))
    if not all_files:
        print("No JSON files found in json_normalized/. Run cpcNormalize.py first.")
        return

    valid_units = load_valid_units()

    # Scan all normalized files for unknown units and case mismatches
    unknown_units = {}   # raw_value → list of (file, field, index)
    case_fixes = {}      # raw_value → canonical_name (auto-fix, no prompt needed)
    for json_file in all_files:
        data = json.loads(json_file.read_text())
        for idx, comm in enumerate(data.get("commodities", [])):
            for field in ("amount_unit", "production_unit"):
                val = comm.get(field, "").strip()
                if not val:
                    continue
                val_upper = val.upper()
                if val_upper in valid_units:
                    canonical = valid_units[val_upper]
                    if val != canonical:
                        # Case mismatch — auto-fix
                        if val not in case_fixes:
                            case_fixes[val] = canonical
                        if val not in unknown_units:
                            unknown_units[val] = []
                        unknown_units[val].append((json_file, field, idx))
                else:
                    if val not in unknown_units:
                        unknown_units[val] = []
                    unknown_units[val].append((json_file, field, idx))

    # Auto-fix case mismatches silently
    if case_fixes:
        print(f"Auto-fixing {len(case_fixes)} case mismatch(es):")
        for old_val, canonical in sorted(case_fixes.items()):
            print(f"  \"{old_val}\" → \"{canonical}\"")
            for json_file, field, idx in unknown_units.pop(old_val, []):
                data = json.loads(json_file.read_text())
                data["commodities"][idx][field] = canonical
                json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    if not unknown_units:
        print("\nAll units are valid. No updates needed.")
        return

    print(f"\nFound {len(unknown_units)} unknown unit(s):\n")

    # Resolve each truly unknown unit
    resolved = {}  # old_value → new_unit_name
    for raw_unit, locations in unknown_units.items():
        files_affected = {loc[0].name for loc in locations}
        print(f"  \"{raw_unit}\" found in {len(locations)} entries across: {', '.join(sorted(files_affected))}")
        uid, unit_name = prompt_unknown_unit(raw_unit)
        save_alias(raw_unit, uid)
        resolved[raw_unit] = unit_name
        print(f"  Saved: \"{raw_unit}\" → \"{unit_name}\" (id={uid})\n")

    # Update the normalized JSON files
    files_updated = set()
    for old_val, locations in unknown_units.items():
        new_val = resolved[old_val]
        for json_file, field, idx in locations:
            if json_file not in files_updated:
                files_updated.add(json_file)
            data = json.loads(json_file.read_text())
            data["commodities"][idx][field] = new_val
            json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"\nUpdated {len(files_updated)} normalized file(s).")
    print("Units update complete.")


if __name__ == "__main__":
    scan_and_update()

import json
import sqlite3
from pathlib import Path

DB_FILE = Path("./cpc.db")
NORMALIZED_FOLDER = Path("./json_normalized")


def load_unit_lookup():
    """Load unit_name → bit position (id) from the database."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT id, unit_name FROM units").fetchall()
    conn.close()
    return {name: uid for uid, name in rows}


def load_county_lookup():
    """Load county_name (uppercase) → bit position (id) from the database."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT id, county_name FROM counties").fetchall()
    conn.close()
    return {name.upper(): cid for cid, name in rows}


def build_items():
    if not DB_FILE.exists():
        print(f"ERROR: {DB_FILE} not found. Run cpcBuildDB.py first.")
        return

    all_files = sorted(NORMALIZED_FOLDER.glob("*.json"))
    if not all_files:
        print("No JSON files found in json_normalized/. Run cpcNormalize.py first.")
        return

    unit_lookup = load_unit_lookup()
    county_lookup = load_county_lookup()

    # items_key = (commodity_upper, variety_upper) → {commodity, variety, amount_unit_bits, production_unit_bits, county_bits}
    items = {}
    unknown_units = set()
    unknown_counties = set()

    for json_file in all_files:
        data = json.loads(json_file.read_text())

        county_name = data.get("issuing_county", "").strip().upper()
        county_bit = county_lookup.get(county_name)
        if not county_bit:
            if county_name and county_name not in unknown_counties:
                unknown_counties.add(county_name)
                print(f"  WARNING: Unknown county \"{county_name}\" in {json_file.name}")
            county_bit = 0

        for comm in data.get("commodities", []):
            commodity = comm.get("commodity", "").strip()
            variety = comm.get("variety", "").strip()
            amount_unit = comm.get("amount_unit", "").strip()
            production_unit = comm.get("production_unit", "").strip()

            if not commodity:
                continue

            key = (commodity.upper(), variety.upper())

            if key not in items:
                items[key] = {
                    "commodity": commodity,
                    "variety": variety,
                    "amount_unit_bits": 0,
                    "production_unit_bits": 0,
                    "county_bits": 0,
                }

            entry = items[key]

            # Set county bit
            if county_bit:
                entry["county_bits"] |= (1 << county_bit)

            # Set amount_unit bit
            if amount_unit:
                au_bit = unit_lookup.get(amount_unit)
                if au_bit:
                    entry["amount_unit_bits"] |= (1 << au_bit)
                elif amount_unit not in unknown_units:
                    unknown_units.add(amount_unit)
                    print(f"  WARNING: Unknown amount_unit \"{amount_unit}\" — run cpcUnitsUpdate.py first")

            # Set production_unit bit
            if production_unit:
                pu_bit = unit_lookup.get(production_unit)
                if pu_bit:
                    entry["production_unit_bits"] |= (1 << pu_bit)
                elif production_unit not in unknown_units:
                    unknown_units.add(production_unit)
                    print(f"  WARNING: Unknown production_unit \"{production_unit}\" — run cpcUnitsUpdate.py first")

    if unknown_units:
        print(f"\n  {len(unknown_units)} unknown unit(s) found. Run cpcUnitsUpdate.py first, then re-run this script.")
        choice = input("  Continue anyway? (y/n): ").strip().lower()
        if choice != "y":
            print("Aborted.")
            return

    conn = sqlite3.connect(DB_FILE)

    # Ensure active column exists (migrate older databases)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
    if "active" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

    # Load existing items keyed by (commodity_upper, variety_upper) → (id, amount_unit, production_unit, county)
    existing = {}
    for row in conn.execute("SELECT id, commodity, variety, amount_unit, production_unit, county FROM items").fetchall():
        existing[(row[1].upper(), row[2].upper())] = {
            "id": row[0], "amount_unit": row[3], "production_unit": row[4], "county": row[5]
        }

    inserted = 0
    updated = 0
    unchanged = 0
    for key, entry in sorted(items.items()):
        prev = existing.get(key)
        if prev is not None:
            # OR new bits into existing bitmasks — never lose previously recorded data
            new_au = prev["amount_unit"] | entry["amount_unit_bits"]
            new_pu = prev["production_unit"] | entry["production_unit_bits"]
            new_county = prev["county"] | entry["county_bits"]
            if new_au != prev["amount_unit"] or new_pu != prev["production_unit"] or new_county != prev["county"]:
                conn.execute(
                    "UPDATE items SET amount_unit = ?, production_unit = ?, county = ? WHERE id = ?",
                    (new_au, new_pu, new_county, prev["id"])
                )
                updated += 1
            else:
                unchanged += 1
        else:
            conn.execute(
                "INSERT INTO items (commodity, variety, amount_unit, production_unit, county, active) VALUES (?, ?, ?, ?, ?, 1)",
                (entry["commodity"], entry["variety"],
                 entry["amount_unit_bits"], entry["production_unit_bits"],
                 entry["county_bits"])
            )
            inserted += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    conn.close()

    print(f"\nItems table: {inserted} new, {updated} updated, {unchanged} unchanged, {total} total.")
    print("Items update complete.")


if __name__ == "__main__":
    build_items()

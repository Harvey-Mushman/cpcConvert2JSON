import sqlite3
import json
from pathlib import Path

DB_FILE = Path("./cpc.db")
GOLD_STANDARD_FILE = Path("./normalize_configs/GOLD_STANDARD.json")

CA_COUNTIES = [
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras",
    "Colusa", "Contra Costa", "Del Norte", "El Dorado", "Fresno",
    "Glenn", "Humboldt", "Imperial", "Inyo", "Kern",
    "Kings", "Lake", "Lassen", "Los Angeles", "Madera",
    "Marin", "Mariposa", "Mendocino", "Merced", "Modoc",
    "Mono", "Monterey", "Napa", "Nevada", "Orange",
    "Placer", "Plumas", "Riverside", "Sacramento", "San Benito",
    "San Bernardino", "San Diego", "San Francisco", "San Joaquin", "San Luis Obispo",
    "San Mateo", "Santa Barbara", "Santa Clara", "Santa Cruz", "Shasta",
    "Sierra", "Siskiyou", "Solano", "Sonoma", "Stanislaus",
    "Sutter", "Tehama", "Trinity", "Tulare", "Tuolumne",
    "Ventura", "Yolo", "Yuba",
]

def build_database():
    if DB_FILE.exists():
        print(f"Database {DB_FILE} already exists.")
        choice = input("Delete and rebuild? (y/n): ").strip().lower()
        if choice != "y":
            print("Aborted.")
            return
        DB_FILE.unlink()

    gold = json.loads(GOLD_STANDARD_FILE.read_text())
    unit_map = gold.get("unit_map", {})

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # ── UNITS TABLE ──────────────────────────────────────────
    c.execute("""CREATE TABLE units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT UNIQUE NOT NULL
    )""")

    unique_units = sorted(set(unit_map.values()))
    for i, name in enumerate(unique_units, 1):
        c.execute("INSERT INTO units (id, unit_name) VALUES (?, ?)", (i, name))

    print(f"Units: {len(unique_units)} inserted")
    for i, name in enumerate(unique_units, 1):
        print(f"  bit {i:3d} = {name}")

    # ── UNIT ALIASES TABLE ───────────────────────────────────
    c.execute("""CREATE TABLE unit_aliases (
        alias TEXT PRIMARY KEY,
        unit_id INTEGER NOT NULL,
        FOREIGN KEY (unit_id) REFERENCES units(id)
    )""")

    alias_count = 0
    for alias, normalized in unit_map.items():
        unit_id = c.execute(
            "SELECT id FROM units WHERE unit_name = ?", (normalized,)
        ).fetchone()[0]
        c.execute("INSERT OR IGNORE INTO unit_aliases (alias, unit_id) VALUES (?, ?)",
                  (alias, unit_id))
        alias_count += 1

    print(f"Unit aliases: {alias_count} inserted")

    # ── COUNTIES TABLE ───────────────────────────────────────
    c.execute("""CREATE TABLE counties (
        id INTEGER PRIMARY KEY,
        county_name TEXT UNIQUE NOT NULL
    )""")

    for i, name in enumerate(CA_COUNTIES, 1):
        c.execute("INSERT INTO counties (id, county_name) VALUES (?, ?)", (i, name))

    print(f"Counties: {len(CA_COUNTIES)} inserted")

    # ── ITEMS TABLE (empty, populated later) ─────────────────
    c.execute("""CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commodity TEXT NOT NULL,
        variety TEXT NOT NULL DEFAULT '',
        amount_unit INTEGER NOT NULL DEFAULT 0,
        production_unit INTEGER NOT NULL DEFAULT 0,
        county INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(commodity, variety)
    )""")

    print("Items table: created (empty)")

    conn.commit()
    conn.close()
    print(f"\nDatabase built: {DB_FILE}")


if __name__ == "__main__":
    build_database()

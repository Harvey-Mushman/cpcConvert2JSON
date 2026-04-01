import json
import re
from pathlib import Path

# ── CONFIGURATION ────────────────────────────────────────────
JSON_OUTPUT_FOLDER = Path("./json_output")
NORMALIZED_FOLDER = Path("./json_normalized")
NORMALIZE_CONFIGS_FOLDER = Path("./normalize_configs")
GOLD_STANDARD_FILE = NORMALIZE_CONFIGS_FOLDER / "GOLD_STANDARD.json"
NORMALIZED_FOLDER.mkdir(exist_ok=True)

# Month names are universal — the only hardcoded map
MONTH_MAP = {
    "JAN": "Jan", "JANUARY": "Jan",
    "FEB": "Feb", "FEBRUARY": "Feb",
    "MAR": "Mar", "MARCH": "Mar",
    "APR": "Apr", "APRIL": "Apr",
    "MAY": "May",
    "JUN": "Jun", "JUNE": "Jun",
    "JUL": "Jul", "JULY": "Jul",
    "AUG": "Aug", "AUGUST": "Aug",
    "SEP": "Sep", "SEPT": "Sep", "SEPTEMBER": "Sep",
    "OCT": "Oct", "OCTOBER": "Oct",
    "NOV": "Nov", "NOVEMBER": "Nov",
    "DEC": "Dec", "DECEMBER": "Dec",
}


# ── CONFIG LOADING ───────────────────────────────────────────

def load_gold_standard():
    """Load the gold standard config."""
    if not GOLD_STANDARD_FILE.exists():
        print(f"ERROR: {GOLD_STANDARD_FILE} not found.")
        exit()
    return json.loads(GOLD_STANDARD_FILE.read_text())


def load_county_config(county, gold):
    """Load county-specific config and merge with gold standard.
    County config overrides gold standard for any keys it defines."""
    path = NORMALIZE_CONFIGS_FOLDER / f"{county}.json"
    if not path.exists():
        return None, None

    county_cfg = json.loads(path.read_text())

    # Start with a copy of gold standard, then overlay county-specific values
    merged = json.loads(json.dumps(gold))  # deep copy
    for key, value in county_cfg.items():
        if key == "notes":
            merged["notes"] = value
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            # Merge dicts (county additions extend gold standard)
            merged[key].update(value)
        elif isinstance(value, list) and len(value) > 0:
            # County list overrides gold standard list
            merged[key] = value
        elif not isinstance(value, (dict, list)):
            merged[key] = value
        elif isinstance(value, dict) and len(value) > 0:
            merged[key] = value

    return merged, path.name


# ── NORMALIZATION FUNCTIONS ──────────────────────────────────

def normalize_unit(raw_unit, unit_map):
    """Normalize a unit string using the config unit_map."""
    if not raw_unit:
        return ""
    clean = raw_unit.strip().rstrip(".").strip().upper()
    return unit_map.get(clean, raw_unit.strip().rstrip(".").strip())


def clean_number(s):
    """Clean a numeric string: remove commas, trailing .0."""
    if not s:
        return ""
    s = s.strip().replace(",", "")
    if "." in s:
        try:
            f = float(s)
            if f == int(f):
                return str(int(f))
            else:
                return str(f)
        except ValueError:
            pass
    return s


def split_amount_and_unit(value, unit_map):
    """Split '15 Trees' into ('15', 'Tree') using config unit_map.
    Also handles compound patterns like '4 x 300 ft rows' and '1.00 Row by 50 feet'."""
    if not value or not value.strip():
        return "", ""

    value = value.strip()

    # Handle "N x M ft rows" patterns
    m = re.match(r'^([\d,.]+)\s*(?:x|X)\s*([\d,.]+)\s+(?:ft|feet)\s+rows?', value, re.IGNORECASE)
    if m:
        return f"{clean_number(m.group(1))} x {clean_number(m.group(2))}", "Row Ft"

    # Handle "N Row by M feet"
    m = re.match(r'^([\d,.]+)\s+[Rr]ow\s+by\s+([\d,.]+)\s+(?:ft|feet)', value, re.IGNORECASE)
    if m:
        return f"{clean_number(m.group(1))} x {clean_number(m.group(2))}", "Row Ft"

    # Handle "N-M GAL POTS"
    m = re.match(r'^([\d,-]+)\s+(GAL)\s+(POTS?)', value, re.IGNORECASE)
    if m:
        return m.group(1), "Gal Pot"

    # Standard: "NUMBER UNIT"
    m = re.match(r'^([\d,.]+)\s+(.+)$', value)
    if m:
        num = clean_number(m.group(1))
        unit_text = m.group(2).strip()
        return num, normalize_unit(unit_text, unit_map)

    # Just a number
    if re.match(r'^[\d,.]+$', value):
        return clean_number(value), ""

    return value, ""


def normalize_month(text):
    """Convert month text to 3-letter proper case."""
    if not text:
        return ""
    return MONTH_MAP.get(text.upper().strip(), "")


def normalize_harvest_season(season, config):
    """Normalize harvest season using config aliases."""
    if not season or not season.strip():
        return ""

    season = season.strip()
    aliases = config.get("harvest_season_aliases", {})

    # Check aliases first
    upper_clean = season.upper().replace(" ", "")
    for alias_key, alias_val in aliases.items():
        if upper_clean == alias_key.replace(" ", ""):
            return alias_val

    # Replace en-dash, em-dash, forward slash with hyphen
    season = season.replace("\u2013", "-").replace("\u2014", "-").replace("/", "-")

    # Remove spaces around hyphen
    season = re.sub(r'\s*-\s*', '-', season)

    # Split on hyphen
    parts = season.split("-")
    if len(parts) == 2:
        start = normalize_month(parts[0].strip())
        end = normalize_month(parts[1].strip())
        if start and end:
            return f"{start}-{end}"

    # Single month
    single = normalize_month(season)
    if single:
        return single

    return season


def split_city_state_zip(combined):
    """Split 'VALLEY CENTER, CA 92082' into (city, state, zip)."""
    if not combined:
        return "", "", ""

    combined = combined.strip().rstrip("-").strip()

    m = re.match(r'^(.+?),\s*([A-Z]{2})\s*([\d-]*)\s*$', combined)
    if m:
        return m.group(1).strip(), m.group(2), m.group(3).strip().rstrip("-")

    return combined, "", ""


def parse_address_city_state_zip(address, config):
    """Try to split city/state/zip from end of an address string using config street suffixes."""
    if not address:
        return address, "", "", ""

    suffixes = config.get("street_suffixes", [])
    if not suffixes:
        return address, "", "", ""

    # PO Box pattern first
    m = re.match(
        r'^((?:PO|P\.O\.)\s+Box\s+\d+)\s+(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\s*$',
        address, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4)

    # Build street suffix regex from config
    suffix_pattern = '|'.join(re.escape(s) for s in suffixes)
    m = re.match(
        r'^(.+\b(?:' + suffix_pattern + r')\.?)\s+'
        r'(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\s*$',
        address, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4)

    return address, "", "", ""


def normalize_county_name(name):
    """Remove parenthetical county codes and title-case."""
    if not name:
        return ""
    clean = re.sub(r'\s*\(\d+\)\s*$', '', name.strip())
    return clean.title()


def is_empty_value(value, skip_list):
    """Check if a value should be treated as empty based on config skip list."""
    if not value:
        return True
    return value.strip().upper() in [s.upper() for s in skip_list]


# ── PRODUCER NORMALIZATION ───────────────────────────────────

def normalize_producer(producer, config):
    """Normalize producer fields using config."""
    if not producer:
        return {}

    field_map = config.get("producer_field_map", {})
    result = {}

    # Apply field mapping from config
    for src_key, value in producer.items():
        target_key = field_map.get(src_key, src_key)
        result[target_key] = value

    # Split city_state_zip if present
    if "city_state_zip" in result:
        city, state, zip_code = split_city_state_zip(result.pop("city_state_zip"))
        result.setdefault("city", city)
        result.setdefault("state", state)
        result.setdefault("zip_code", zip_code)

    # If city still empty, try parsing from address using config street suffixes
    if not result.get("city") and result.get("address"):
        addr, city, state, zip_code = parse_address_city_state_zip(result["address"], config)
        if city:
            result["address"] = addr
            result["city"] = city
            result["state"] = state
            result["zip_code"] = zip_code

    # Clean zip trailing dashes
    if "zip_code" in result:
        result["zip_code"] = result["zip_code"].rstrip("-").strip()

    # Ensure all standard fields present from config
    for field in config.get("standard_producer_fields", []):
        result.setdefault(field, "")

    return result


# ── COMMODITY NORMALIZATION ──────────────────────────────────

def normalize_commodity(comm, config):
    """Normalize a single commodity entry using config."""
    result = {}
    unit_map = config.get("unit_map", {})
    skip_list = config.get("empty_value_skip_list", [])

    # Apply field mapping from config
    field_map = config.get("commodity_field_map", {})
    for src_key, value in comm.items():
        target_key = field_map.get(src_key, src_key)
        result[target_key] = value

    # Split amount_grown into amount_grown + amount_unit if combined
    if "amount_unit" not in result and "amount_grown" in result:
        amt, unit = split_amount_and_unit(result["amount_grown"], unit_map)
        result["amount_grown"] = amt
        result["amount_unit"] = unit
    elif "amount_unit" in result:
        result["amount_grown"] = clean_number(result["amount_grown"])
        result["amount_unit"] = normalize_unit(result["amount_unit"], unit_map)

    # Split est_production into est_production + production_unit if combined
    if "production_unit" not in result and "est_production" in result:
        prod, unit = split_amount_and_unit(result["est_production"], unit_map)
        result["est_production"] = prod
        result["production_unit"] = unit
    elif "production_unit" in result:
        result["est_production"] = clean_number(result["est_production"])
        result["production_unit"] = normalize_unit(result["production_unit"], unit_map)

    # Normalize harvest season using config
    result["harvest_season"] = normalize_harvest_season(
        result.get("harvest_season", ""), config)

    # Clean season_altering_device and months_in_storage using config skip list
    sad = result.get("season_altering_device", "")
    result["season_altering_device"] = "" if is_empty_value(sad, skip_list) else sad.strip()

    mis = result.get("months_in_storage", "")
    result["months_in_storage"] = "" if is_empty_value(mis, skip_list) else mis.strip()

    # Ensure all standard fields present from config
    for field in config.get("standard_commodity_fields", []):
        result.setdefault(field, "")

    return result


# ── FULL FILE NORMALIZATION ──────────────────────────────────

def normalize_file(data, config):
    """Normalize a full CPC JSON structure using config."""
    result = {}

    # Certificate fields from config
    cert_map = config.get("certificate_field_map", {})
    for field in config.get("standard_certificate_fields", []):
        src_field = None
        for src, tgt in cert_map.items():
            if tgt == field:
                src_field = src
                break
        if src_field and src_field in data:
            result[field] = data[src_field]
        elif field in data:
            result[field] = data[field]
        else:
            result[field] = ""

    # Producer
    result["producer"] = normalize_producer(data.get("producer", {}), config)

    # Production sites
    result["production_sites"] = data.get("production_sites", [])

    # Storage locations
    result["storage_locations"] = data.get("storage_locations", [])

    # Authorized counties — normalize names
    raw_counties = data.get("authorized_counties", [])
    result["authorized_counties"] = [normalize_county_name(c) for c in raw_counties if c]

    # Authorized representatives — check config for source field names
    rep_source_fields = config.get("authorized_rep_source_fields", ["authorized_representatives"])
    reps = []
    for src_field in rep_source_fields:
        if src_field in data and data[src_field]:
            reps = data[src_field]
            break

    # Normalize reps to list of strings
    rep_dict_fmt = config.get("authorized_rep_dict_format", {})
    first_key = rep_dict_fmt.get("first_name_key", "first_name")
    last_key = rep_dict_fmt.get("last_name_key", "last_name")
    normalized_reps = []
    for r in reps:
        if isinstance(r, dict):
            name = f"{r.get(first_key, '')} {r.get(last_key, '')}".strip()
            if name:
                normalized_reps.append(name)
        elif isinstance(r, str) and r.strip():
            normalized_reps.append(r.strip())
    result["authorized_representatives"] = normalized_reps

    # Second certificates / sell-for
    result["producers_i_sell_for"] = data.get("producers_i_sell_for", [])
    result["producers_selling_for_me"] = data.get("producers_selling_for_me", [])

    # Commodities
    raw_commodities = data.get("commodities", [])
    result["commodities"] = [normalize_commodity(c, config) for c in raw_commodities]

    return result


# ── MAIN ─────────────────────────────────────────────────────

gold = load_gold_standard()

all_files = sorted(JSON_OUTPUT_FOLDER.glob("*.json"))
if not all_files:
    print("No JSON files found in json_output/. Run cpcConvert.py and cpcMerge.py first.")
    exit()

print("Which CPC to normalize?")
print("  0 - Normalize ALL")
for i, f in enumerate(all_files, start=1):
    print(f"  {i} - {f.name}")

choice = input("Enter number: ").strip()
if choice == "0":
    files = all_files
elif choice.isdigit() and 1 <= int(choice) <= len(all_files):
    files = [all_files[int(choice) - 1]]
else:
    print("Invalid choice. Exiting.")
    exit()

for json_file in files:
    print(f"\nNormalizing: {json_file.name}")
    data = json.loads(json_file.read_text())

    county = data.get("issuing_county", "UNKNOWN").upper()
    config, config_name = load_county_config(county, gold)
    if config is None:
        print(f"  ERROR: No normalize config found for county '{county}'.")
        print(f"         Create normalize_configs/{county}.json before normalizing.")
        continue
    print(f"  County: {county}, Config: {config_name}")

    normalized = normalize_file(data, config)

    out_file = NORMALIZED_FOLDER / json_file.name
    out_file.write_text(json.dumps(normalized, indent=2, ensure_ascii=False))

    commodity_count = len(normalized.get("commodities", []))
    print(f"  {commodity_count} commodities -> {out_file.name}")

print("\nNormalization complete.")

import json
from pathlib import Path

# ─────────────────────────────────────────────
# STANDARD OUTPUT SCHEMA (target format)
# ─────────────────────────────────────────────
EMPTY_STANDARD = {
    "certificate_number": "",
    "issuing_county": "",
    "issuing_date": "",
    "expiration_date": "",
    "amended_date": "",
    "county_fee": "",
    "certified_copies_made": "",
    "producer": {
        "name": "",
        "farm_name": "",
        "dba": "",
        "address": "",
        "city": "",
        "state": "",
        "zip_code": "",
        "phone_cell": "",
        "phone_business": "",
        "fax": "",
        "email": ""
    },
    "production_sites": [],
    "storage_locations": [],
    "authorized_counties": [],
    "authorized_representatives": [],
    "producers_authorized_to_sell_for": [],
    "issuing_commissioner": {
        "agency": "",
        "signatory_name": "",
        "title": ""
    },
    "commodities": []
}

# ─────────────────────────────────────────────
# GENERIC FIELD MAP
# Maps known AI variation names → standard name
# Add new variations here as new counties are processed
# ─────────────────────────────────────────────
FIELD_MAP = {
    # Certificate number
    "cert_number": "certificate_number",
    "certificate_no": "certificate_number",
    "certificate_id": "certificate_number",

    # Dates
    "issuance_date": "issuing_date",
    "date_issued": "issuing_date",
    "issue_date": "issuing_date",

    # Fee
    "account_fee": "county_fee",
    "fee": "county_fee",

    # Copies
    "copies_made": "certified_copies_made",
    "number_of_copies": "certified_copies_made",
}

# ─────────────────────────────────────────────
# COUNTY-SPECIFIC OVERRIDES
# Add a new county key as you process more CPCs
# ─────────────────────────────────────────────
COUNTY_OVERRIDES = {
    "KERN": {
        # No extra overrides needed beyond FIELD_MAP so far
        # Add here if Kern uses unique field names not covered above
    },
    "TULARE": {
        # Fill in after processing first Tulare CPC
    },
    "LOS ANGELES": {
        # Fill in after processing first LA CPC
    }
}

# ─────────────────────────────────────────────
# HELPER: find a value by searching multiple
# possible locations in the raw JSON
# ─────────────────────────────────────────────
def find_value(data, *keys):
    """Search for a value across multiple keys and nested sections."""
    # Search top-level first
    for key in keys:
        if key in data and data[key]:
            return data[key]
    # Search one level deep in any dict values
    for section in data.values():
        if isinstance(section, dict):
            for key in keys:
                if key in section and section[key]:
                    return section[key]
    return ""

def find_list(data, *keys):
    """Search for a list value across multiple keys and nested sections."""
    for key in keys:
        if key in data and isinstance(data[key], list) and data[key]:
            return data[key]
    for section in data.values():
        if isinstance(section, dict):
            for key in keys:
                if key in section and isinstance(section[key], list) and section[key]:
                    return section[key]
    return []

def find_producer(data):
    """Build producer block from wherever the fields appear."""
    producer = EMPTY_STANDARD["producer"].copy()

    # Look for a nested producer block first
    for key in ["producer", "producer_info", "certified_producer_info"]:
        if key in data and isinstance(data[key], dict):
            src = data[key]
            producer["name"]          = src.get("name") or src.get("contact") or src.get("certified_producer_contact") or ""
            producer["farm_name"]     = src.get("farm_name") or src.get("business_name") or src.get("certified_producer_name") or ""
            producer["dba"]           = src.get("dba") or ""
            producer["address"]       = src.get("address") or ""
            producer["city"]          = src.get("city") or ""
            producer["state"]         = src.get("state") or ""
            producer["zip_code"]      = src.get("zip_code") or src.get("zip") or ""
            producer["phone_cell"]    = src.get("phone_cell") or src.get("cell_phone") or src.get("mobile") or ""
            producer["phone_business"]= src.get("phone_business") or src.get("business_phone") or src.get("phone") or ""
            producer["fax"]           = src.get("fax") or src.get("phone_additional") or ""
            producer["email"]         = src.get("email") or ""
            return producer

    # Fall back to searching all sections
    producer["name"]           = find_value(data, "name", "certified_producer_contact", "contact", "producer_contact")
    producer["farm_name"]      = find_value(data, "farm_name", "certified_producer_name", "business_name", "operator_name")
    producer["dba"]            = find_value(data, "dba")
    producer["address"]        = find_value(data, "address")
    producer["city"]           = find_value(data, "city")
    producer["zip_code"]       = find_value(data, "zip_code", "zip")
    producer["phone_cell"]     = find_value(data, "phone_cell", "cell_phone", "mobile")
    producer["phone_business"] = find_value(data, "phone_business", "business_phone", "phone")
    producer["fax"]            = find_value(data, "fax", "phone_additional")
    producer["email"]          = find_value(data, "email")
    return producer

# ─────────────────────────────────────────────
# MAIN NORMALIZE FUNCTION
# ─────────────────────────────────────────────
def normalize(data):
    # Detect issuing county
    issuing_county = find_value(data, "issuing_county").upper().strip()

    # Build combined field map: generic + county-specific
    field_map = {**FIELD_MAP}
    if issuing_county in COUNTY_OVERRIDES:
        field_map.update(COUNTY_OVERRIDES[issuing_county])

    out = json.loads(json.dumps(EMPTY_STANDARD))  # deep copy

    out["certificate_number"]   = find_value(data, "certificate_number", "cert_number", "certificate_no")
    out["issuing_county"]       = issuing_county
    out["issuing_date"]         = find_value(data, "issuing_date", "issuance_date", "issue_date", "date_issued")
    out["expiration_date"]      = find_value(data, "expiration_date")
    out["amended_date"]         = find_value(data, "amended_date")
    out["county_fee"]           = find_value(data, "county_fee", "account_fee", "fee")
    out["certified_copies_made"]= find_value(data, "certified_copies_made", "copies_made", "number_of_copies")
    out["producer"]             = find_producer(data)
    out["production_sites"]     = find_list(data, "production_sites")
    out["storage_locations"]    = find_list(data, "storage_locations")
    out["authorized_counties"]  = find_list(data, "authorized_counties")
    out["authorized_representatives"]       = find_list(data, "authorized_representatives")
    out["producers_authorized_to_sell_for"] = find_list(data, "producers_authorized_to_sell_for", "authorized_to_sell_for")
    out["issuing_commissioner"]             = find_value(data, "issuing_commissioner") or {"agency": "", "signatory_name": "", "title": ""}
    out["commodities"]                      = find_list(data, "commodities")

    return out

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
input_folder = Path("./json_output")
final_folder = Path("./json_final")
final_folder.mkdir(exist_ok=True)

files = sorted(input_folder.glob("*.json"))
if not files:
    print("No JSON files found in ./json_output. Run cpcMerge.py first.")
    exit()

print("Which file to normalize?")
print("  0 - Normalize ALL files")
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

for json_file in targets:
    print(f"Normalizing: {json_file.name}")
    data = json.loads(json_file.read_text())
    normalized = normalize(data)

    out_file = final_folder / json_file.name
    out_file.write_text(json.dumps(normalized, indent=2))

    county = normalized["issuing_county"] or "UNKNOWN"
    commodities = len(normalized["commodities"])
    print(f"  County: {county} | Commodities: {commodities} | Saved to json_final/{json_file.name}")

print("\nNormalization complete.")

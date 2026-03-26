---
name: CPC Converter Project Status
description: Architecture, field naming conventions, confirmed fixes, and pending work for the CPC PDF-to-JSON converter
type: project
---

# CPC PDF-to-JSON Converter

## What it does
Converts California Certified Producer's Certificates (CPCs) from PDF to structured JSON. Two scripts:
- `cpcConvert.py` — extracts each PDF page to individual JSON files in `page_output/<name>/page_NNN.json`
- `cpcMerge.py` — merges all page JSONs into a single `json_output/<name>.json`

County-specific parsing rules live in `county_configs/<COUNTY>_<revision>.json`.

## Confirmed working counties (as of 2026-03-25)
- **Orange** (51-049 Rev 10/24) — fully working including page-break storage locations and second-cert sell-for fields
- **Kern** (51-049M Rev 09/2020) — working; certificate header uses de-interleaving (kern_dual_column); one CIDFont glyph misread in CERTIFICATE NO is unavoidable without OCR
- **LA** (51-049 Rev 10/24) — config correct, not yet tested with second-cert samples
- **San Diego** (51-049M Rev 01/15) — text-based extraction; config correct, not yet tested with second-cert samples

## Standard schema field names — SELL-FOR direction is critical
| Field | Meaning |
|---|---|
| `producers_i_sell_for` | CPC holder is authorized to SELL FOR these other producers |
| `producers_selling_for_me` | These other CPC holders are authorized to SELL the holder's products |
| `authorized_representatives` | Named individuals authorized to operate at the holder's market stall (San Diego only so far) |

**Why:** State law allows up to 2 in each direction. The direction is a legal distinction. "authorized_representatives" was the wrong name — it was ambiguous about direction.

## Key architectural decisions

### Page-break table continuation (solved 2026-03-25)
Three-layer detection in `extract_page_table_based`:
1. **Positional table_patterns** (config-driven): for tables whose continuation starts with raw data rows (no header). Orange County uses `^[A-Z]{1,2}$` pattern to catch storage location IDs (A, B, etc.) with positional column mapping and `skip_rows: 0`.
2. **Column-header matching** (`find_continuation_config`): for continuations that repeat column headers in row 0. Returns `force_header_row_0=True`.
3. **Table-name matching** (`find_continuation_config`): for continuations that repeat the section title in row 0. Returns `force_header_row_0=False`.
4. **Rescue from page-repeat table**: if pdfplumber merges the "Certified Producer:" header with continuation rows, the tail after row 0 is checked for continuation data.

### header_row: 0 pattern (solved 2026-03-25)
Orange/LA/UNKNOWN county sell-for tables have the section title AND all column headers in row 0. `find_header_row` incorrectly treats the first data row as the header. Fix: `"header_row": 0` in the table config forces correct behavior.

Applies to: any table where the first cell of row 0 IS the table name and the remaining cells of row 0 are column headers.

### Kern dual-column header (solved 2026-03-24)
`certificate_header_type: "kern_dual_column"` triggers char-level de-interleaving. Uses `_deinterleave_by_text` (for CERTIFICATE NO) and `_deinterleave_by_position` (for ISSUING DATE). Clean right-column rows are used as references.

## Pending / not yet tested
- LA, Kern, San Diego: second-certificate scenarios (producers_i_sell_for / producers_selling_for_me with real data)
- LA, Kern, San Diego: page-break table continuations — need samples
- Remaining CPCs: Tenerelli Farms, Urban Greens Direct (LA), McKay Smith Farms
- Murray Family Farms: run cpcMerge.py (585 commodities already extracted)

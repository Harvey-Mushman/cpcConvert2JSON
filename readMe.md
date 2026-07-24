These Python programs are designed to convert text-searchable Certified Producer Certificates (CPC) files (PDF, MS WOrd or MS Excell) into JSON files that can be imported into CFMiX.com database.  The process uses configuration files that are setup using AI to parse the input file based on the county of orgin and the form number withing the target file.  Once the configuration file is created for one county form, all other source files from the same county that carry the same form number are processed identically.

The first time a county form is realized to not already exist on file, the program notifies the user.  This notification suggests the output file(s) that are generated must be reviewed very carefilly by the user to confirm the AI interperted the source file correctly.  The config file often needs to be tweaked before it can be use to correctly process any CPC's.

All of these Python programs must run within a virtual enviroment -- run the following command in the Terminal:

c:\Users\hm\Documents\CFMiX\cpcConvert2json\.venv\Scripts\Activate.ps1

the prompt will change to show the following :

(.venv) PS C:\Users\hm\Documents\CFMiX\cpcConvert2json> 

Now the processing of CPC's can start... But note the support files at the bottom of this document as well since they ight have an effect on the desired results.

Step #1
python cpcConvert.py — extract from PDFs/XLS
  The product is written into /page_output/page_001.json ~ lastPage

Step #2
python cpcMerge.py — merge pages into per-CPC files
  The product of this step is written into /json_output/sourceFilename.json

Step #3
python cpcNormalize.py — apply normalization rules
  The product of this step is written into /json_normalized/sourceFilename.json

The input folder is ./certificates/ this folder contains the original CPC text-searchable PDF, XLS files.  All the fils in this folder will be presented to the user in a menu list.  From that list the User can select to process All or select any one for processing.

The cpcConvert.py program is the first step in the process.  It calls on the county_config files for processing the input files.  If a new county is presented of the form is not the same as the form(s) on file, the subrouting to create a new config file is called on.  This is where AI parses the input file to understand the design of the form.  Once parsed, the AI writes out a new config file which needs to be verified for correctness.  

The result of running the cpcConvert program is output into the page_output folder, where each page of the CPC is regenerated in a folder that is named based on the source cpc filename.  (Example: Source Filename Weiser19.pdf the folder name is Weiser19)  Then within the folder each page of the source PDF becomes filename page_001.json through the last page number.

The next step is cpcMerge.py, this program assembled all of the individual pages of the cpc after the convert program transformed the original pdf files into JSON.  This routine was required because the AI process that is build in the cpcConvert program ran out of memory on several of the multiple page cpc's.  So the convert program generates one output page for each PDF input page and this routing merges all of them back into one document that only has one JSON commodity object.

The third and final step is normailzation, in this process the cpcNormalize.py program converts all of the merged output files into a standard format that can be imported into another systems database.  The normalizer references normalizer_config JSON configuration file for each county which describes the data points that need to be altered to conform to the standard format.  The "Gold_Standard.config" file has rules that are applied to all counties.

Known Warning Messages, symtoms and solutions

Sympton reads:
Page 2/9: extracting...
    WARNING: Unknown table '4' — not in county config. Form may have changed. Review county_configs/LOS ANGELES.json

Explnation:

The table name '4' means pdfPlumber extracted a table whose first cell is literally just the number "4". This is almost certainly a commodity data row (site number 4) that pdfPlumber split into a separate table — it happens when a page break falls mid-table, and the continuation on the next page doesn't have the column headers repeated.

The code tried to match it as a known table name in the LA config, couldn't find "4", then tried page-break continuation detection (line 1311), and that also didn't match. So it falls through to the generic "unknown table" handler.

Two things to check:

1. Is the data being lost? The fallback handler (lines 1321-1329) still tries to parse it, but without knowing it's a commodity table it may not map the columns correctly.

2. The config filename — it says LOS ANGELES.json rather than LOS ANGELES_51-049_Rev_10-24.json. Is this a different CPC that didn't match the form revision, causing it to generate a new generic config?

This condition was correted. the page started with a headless table which was caused by the prior page table runnoverby one additional site location row.


Sympton reads (Ventura provides XLS format files):
FILE: Cuyama Orchards.xls
WARNING *** OLE2 inconsistency: SSCS size is 0 but SSAT size is non-zero
  Format: xls_access_export
  Config: VENTURA_ACCESS_EXPORT.json
WARNING *** OLE2 inconsistency: SSCS size is 0 but SSAT size is non-zero
  Extracted 35 commodities from Access export
  TOTAL: 35 commodities

Explnation:

That warning is not from your code — it's from the xlrd library that reads .xls files. It's a low-level warning about the internal structure of the Excel file (the OLE2 container format has a minor inconsistency in how small-stream sizes are declared).

It's harmless. The file is being read correctly — 35 commodities were extracted successfully. Ventura County's Access database exports just produce slightly non-standard .xls files, which is common with older Microsoft Access exports.

You can safely ignore it. Would you like me to suppress the warning in the code so it doesn't clutter the output?

Sympton: cpcConfig reading Fresno CPC: the commodities table has a header but theactual data is not contained in rows and columns.  Rather the data has character spacing and new-line to form rows and columns.  This condition meant the config file for Fresno has both table definations and character spacing where each column starts and stops.  The text that apears to word-wrap within a column also had to be understood by AI before the rows were able to be idenitified correctly.  

Additionally, Fresno's way to describe "Amount" is unique to their county.  The description reads "1.5R X 160 FT" which combined the value with teh unit, assuming "1.5R" stands for 1.5 Rows.  Assuming a standard based on how most other counties defined this data point, Amount would read "1.5 x 160 Row Ft" there by seperating the value of "1.5 x 160" from the unit of measure "Row Ft".  To properly handle this condition a seperate RegX description was designed and build into the normalizer.py program.


**************************************************************
**************************************************************
                 Support Files:
**************************************************************
**************************************************************

/cpcConvert2json/cpc.db

This SQLite file is the start of a database for cpc's. the tables within the database include the following:

Counties: list of all 58 California Counties along with their respective County Number.

Items: this is a list of all items converted from PDF/XLS input cpc files.  The valid unit of measure for Amount and Production are stored in unique decimal bit values which reference the unit descriptions found in the 

*******************************

python cpcCount.py

This file allows the User to confirm the pages that were converted as well as merged back into one JSON file.  the routine counts commidities on each indivual page_output file and then offers the option to count the total commidities once the cpcMerge.py program reassembles the page_output files back into one JSON file.

*******************************

python cpcItemsUpdate.py

This program is used to update the cpc.db Items database which was created by the cpcBuildDB.py file.

*******************************

python cpcPdfCheck.py

This program presents a menu of files within the certificates root folder.  THe user can then select All or a single file to text for compatibility, where all files MUST be "text-searchable".

*******************************

python cpcUnitsUpdate.py

This program is used to modify the Units table that is part of the "cpc.db" database.  It exhamins the normilized output files nad reads all the units of measure, then compairs those to the units stored in the database and lists any missing units.  If all units are present in the database, a message is presented that says "All units are valid.  No updates are needed".  If units are not found, the User has the option to add a new unit to the database.

*******************************
*******************************


cpcConvert.py reads from:

PDF files (via pdfplumber)
XLS/XLSX files (via xlrd / openpyxl)
JSON config files (from ./county_configs/)
The Anthropic API (to auto-generate a county config when one doesn't exist)

And it writes to:

JSON page files (into ./page_output/)
A log file (conversion_log.txt)
County config JSON (when generating a new one)

**************************************************************
**************************************************************
          Pipeline & Database Summary by Claude, Summary
**************************************************************
**************************************************************

NOTE: To view the database and tables, use the DB Browser (SQLite) tool, a Windows installed application.

The CPC programs form a pipeline that converts county-issued Certified Producer Certificates into normalized JSON, then registers the commodities and units into a SQLite database (cpc.db).

Processing Pipeline (run in order):

  cpcPdfCheck.py   — Pre-flight check. Verifies PDFs are text-searchable. No database, no file output.

  cpcConvert.py    — Extracts raw data from PDF/XLS/XLSX into per-page JSON files (page_output/). No database interaction. Uses county_configs/ for parsing rules; calls the Anthropic API to generate a new config when a county/form is seen for the first time.

  cpcMerge.py      — Reassembles the per-page JSON files into one JSON per certificate (json_output/). No database interaction. Pure JSON-to-JSON merge.

  cpcNormalize.py  — Standardizes field names, units, commodity names, and formatting (json_normalized/). Reads cpc.db to load the unit alias table so raw unit strings (e.g. "TREES", "SQ FT") resolve to canonical names (e.g. "Tree", "Sq Ft"). Does not write to the database.

  cpcUnitsUpdate.py — Scans normalized JSON for unit strings not yet in the database. Prompts the user to map unknowns to existing units or create new ones. Reads and writes the units and unit_aliases tables. Also patches the normalized JSON files in place with corrected unit names.

  cpcItemsUpdate.py — Scans normalized JSON and registers every unique commodity+variety pair into the items table. Reads units and counties tables to convert names into bit positions. For each item, stores which units and which counties have been observed as bitmasks (amount_unit, production_unit, county columns). Inserts new items; OR-merges bitmasks into existing items so no prior data is lost.

  cpcCount.py      — Diagnostic utility. Counts commodities per page and per merged file. No database, no file writes.

  cpcBuildDB.py    — One-time setup. Creates cpc.db from scratch with four tables (see below). Seeds units and unit_aliases from GOLD_STANDARD.json, seeds counties with all 58 California counties, and creates an empty items table.

Database Tables (cpc.db):

  units          — Canonical unit names (id, unit_name). The id doubles as a bit position for bitmask storage in the items table.

  unit_aliases   — Maps raw/variant unit strings to their canonical unit id (alias, unit_id). Used by cpcNormalize.py for lookup and by cpcUnitsUpdate.py for registration.

  counties       — All 58 California counties (id, county_name). The id doubles as a bit position for the county bitmask in items.

  items          — One row per unique commodity+variety. Columns amount_unit, production_unit, and county are bitmasks where each set bit references an id from the units or counties table. The active column flags whether the item is in use.

File Storage Locations:

  ./certificates/        — Source CPC files (PDF, XLS, XLSX)
  ./county_configs/      — Per-county extraction configs (JSON, some AI-generated)
  ./page_output/         — Per-page extracted JSON (one folder per certificate)
  ./json_output/         — Merged per-certificate JSON
  ./normalize_configs/   — Normalization rules (GOLD_STANDARD.json + per-county overrides)
  ./json_normalized/     — Final normalized JSON, ready for import or items registration
  ./cpc.db               — SQLite database (units, aliases, counties, items)
  ./conversion_log.txt   — Extraction log from cpcConvert.py

  **************************************************************
  **************************************************************
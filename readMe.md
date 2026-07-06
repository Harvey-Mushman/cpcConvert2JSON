These Python programs are designed to convert text-searchable Certified Producer Certificates (CPC) files (PDF, MS WOrd or MS Excell) into JSON files that can be imported into CFMiX.com database.  The process uses configuration files that are setup using AI to parse the inpot file based on the county of orgin and the form number withing the target file.  Once the configuration file is created for one county form, all other source files from the same county that carry the same form number are processed identically.

The first time a county form is realized to not already exist on file, the program notifies the user.  This notification suggests the output file(s) that are generated must be reviewed very carefilly by the user to confirm the AI interperted the source file correctly.  The config file often needs to be tweaked before it can be use to correctly process any CPC's.

All of these Python programs must run within a virtual enviroment -- run the following command in the Terminal:

c:\Users\hm\Documents\CFMiX\cpcConvert2json\.venv\Scripts\Activate.ps1

the prompt will change to show the following :

(.venv) PS C:\Users\hm\Documents\CFMiX\cpcConvert2json> 

Now the processing of CPC's can start...

python cpcConvert.py — extract from PDFs/XLS
python cpcMerge.py — merge pages into per-CPC files
python cpcNormalize.py — apply normalization rules

The input folder is ./certificates/ this folder contains the original CPC text-searchable PDF, XLS files.

The cpcConvert.py program is the first step in the process.  It calls on the county_config files for processing the input files.  If a new county is presented of the form is not hte same as the form(s) on file, the subrouting to create a new config file is called on.  This is where AI parses the input file to understand the design of hte form.  Once parsed, the AI writes out a new config file which needs to be verified for correctness.  

The result of running the cpcConvert program is output into the page_output folder, where each page of the CPC is regenerated in a folder that is named based on the source cpc filename.  (Example: Source Filename Weiser19.pdf the folder name is Weiser19)  Then within the folder each page of the source PDF becomes filename page_001.json through the last page number.

The next stem is cpcMerge.py, this program assembled all of the individual pages of hte cpc after the convert program transformed the original pdf files into JSON.  This routine was required because the OCR process that is build in the cpcConvert program ran out of memory on several of the multiple page cpc's.  So the convert program generates one output page for each PDF input page and this routing merges all of them back into one document that only has one JSON commodity object.

The third and final step is normailzation, in this process the cpcNormalize.py program converts all of the merged output files into a standard format that can be imported into another systems database.  The normalizer references the configuration file for each county which describes the data points that need to be altered to confirm to the standard format.  The "Gold_Standard.config" file has rules that are applied to all counties.

Known Warning Messages, symtoms and solutions

Sympton reads:
Page 2/9: extracting...
    WARNING: Unknown table '4' — not in county config. Form may have changed. Review county_configs/LOS ANGELES.json

Explnation:

The table name '4' means pdfplumber extracted a table whose first cell is literally just the number "4". This is almost certainly a commodity data row (site number 4) that pdfplumber split into a separate table — it happens when a page break falls mid-table, and the continuation on the next page doesn't have the column headers repeated.

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

####
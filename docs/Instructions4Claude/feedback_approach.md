---
name: User approach preferences for CPC converter
description: How the user wants problems approached — especially around PDF extraction
type: feedback
---

Do not give up on pdfplumber extraction when data appears unreadable. The data is always in the PDF in some form. Investigate the actual character/table structure before concluding something is impossible.

**Why:** User rejected the suggestion to fall back to OCR for Kern County's garbled certificate header. The interleaving was solvable with character-level analysis.

**How to apply:** When pdfplumber returns garbled or missing data, run diagnostics (dump chars, table rows, y-coordinates) to understand the PDF structure before proposing workarounds. Only accept a limitation after exhausting all pdfplumber approaches.

---

Blank fields still matter — include them in output as empty strings, not as absent keys.

**Why:** User explicitly called this out for Kern County's `amended_date` field. An empty amended_date is meaningful (certificate was not amended).

**How to apply:** Use `if v is not None` not `if v` when filtering output fields.

---

Add diagnostic logging to the log file (not console) so the user can see exactly what tables are being processed per page.

**Why:** The storage location page-break bug was diagnosed in one step once the table names were logged. Without it we were guessing.

**How to apply:** Always log table names found per page to the log file. Log skipped tables, unknown tables, and continuation matches.

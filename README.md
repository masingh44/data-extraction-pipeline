# Balochistan Incident Pipeline v6

## Overview
Extracts structured incident data from SATP Balochistan timeline PDFs into 118-column CSVs.

## Usage

### Full pipeline (PDF → CSV)
```bash
python3 pipeline.py --pdf MAR_25.pdf --out BAL_MAR2025 --month March --year 2025
```

### Extractor only
```bash
python3 extractor.py input.pdf output.csv [Month] [Year]
# Example:
python3 extractor.py MAR_25.pdf BAL_MAR2025_Full.csv March 2025
```

### Standardize existing CSV
```bash
python3 pipeline.py input.csv [output.csv]
```

## Files
- `schema.py` — Column definitions, district list, area-to-district mappings, allowed values
- `extractor.py` — PDF parser + all field extractors (incident_type, casualties, districts, etc.)
- `standardize.py` — Enforces schema: column order, null normalization, allowed value checks
- `audit.py` — Smart field-level audit against original_description text
- `pipeline.py` — Orchestrator: extract → sanity check → standardize → audit
- `codebook.py` — Column documentation (optional)

## Key Changes from v5

### District Extraction (completely rewritten)
- Multi-signal position-based algorithm
- Filters out "resident of X District" (victim origin ≠ event location)
- 80+ area-to-district mappings (Mundi→Kech, Mashkel→Washuk, etc.)
- Aggregate statistical reports → district = "No"
- Bolan/Kachhi area-specific override

### Schema Alignment
- 118 columns matching BAL_JAN2025/BAL_FEB2025 gold CSVs
- Removed: named_individuals, incident_summary, group_statement_key_claim
- Default values aligned: sf_captured→0, hostages_taken→0, sf_counter_op→No, etc.

### Classifier Improvements
- Annual/aggregate reports detected BEFORE suicide bombing check
- Group-joining events recognized as Aggregate report
- Improved death squad perpetrator detection
- SF perpetrator detection improved for ED/IBO entries
- Protest entries get perpetrator_group = "-"

### Named Victims Builder
- Auto-generates structured strings: "Name (disappeared)", "Name (killed)", etc.
- Uses disappeared_names for ED entries
- Extracts named individuals from targeted killings, armed assaults

### Other Fixes
- disappearance_circumstances: improved raid/airport/clinic detection
- family_member_previously_targeted: reduced false positives
- target_organization: broader coverage, Protest→Civilian
- civilian_killed: better counting for targeted killings
- weapons fields: cleaned up vague entries

## Accuracy (tested on Jan/Feb 2025 PDFs)
- Row count: 100% match (75 Jan, 109 Feb)
- District: 0 errors Jan, 3 errors Feb (user judgment edge cases)
- Feb overall: 99.0% cell-level accuracy (157/17,462 cell diffs)

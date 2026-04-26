"""
standardize.py — Enforces the schema on a Balochistan incidents CSV.

Fixes:
  1. Column order and presence (adds missing columns, removes extra ones)
  2. Null value normalization (Yes/No/- consistency)
  3. Allowed value enforcement (flags values not in schema)
  4. Named_victims noise removal (irrelevant info that isn't a victim)
  5. Column rules from schema.py
  6. Numeric column type enforcement

Usage:
  python3 standardize.py input.csv [output.csv]
  If output.csv not given, writes input_standardized.csv
"""

import csv, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import (COLUMNS, ALLOWED_VALUES, NON_ATTACK_TYPES, NUMERIC_COLUMNS,
                    COLUMN_RULES, NAMED_VICTIMS_NOISE, BOOLEAN_COLUMNS,
                    NULL_NOT_APPLICABLE, NULL_NOT_REPORTED)

# ── NULL NORMALIZATION MAP ────────────────────────────────────────────────────
# Maps various null-like values to the standard form
NULL_VARIANTS_TO_NA = {
    'n/a', 'na', 'none', 'not applicable', 'not relevant', 'n.a.', 'null',
}
NULL_VARIANTS_TO_NO = {
    'unknown', 'not reported', 'not available', 'not mentioned',
    'not stated', 'unspecified',
}

# Boolean columns imported from schema_v6

def normalize_null(val, col):
    """Normalize null/empty values to standard form."""
    v = str(val).strip()
    if v == '':
        # Empty: use '-' for non-boolean, 'No' for boolean
        return NULL_NOT_REPORTED if col in BOOLEAN_COLUMNS else NULL_NOT_APPLICABLE
    if v.lower() in NULL_VARIANTS_TO_NA:
        return NULL_NOT_APPLICABLE
    if v.lower() in NULL_VARIANTS_TO_NO:
        return NULL_NOT_REPORTED
    return v

def normalize_boolean(val):
    """Normalize boolean-like values to Yes/No."""
    v = str(val).strip().lower()
    if v in ('yes', 'true', '1', 'y'): return 'Yes'
    if v in ('no', 'false', '0', 'n', '-', ''): return 'No'
    return val  # return as-is if not recognizable

def normalize_numeric(val):
    """Normalize numeric columns: integer or '-'."""
    v = str(val).strip()
    if v in ('', '-', 'No', 'N/A', 'na', 'none'): return '-'
    try:
        return str(int(float(v)))
    except:
        return v  # leave as-is if not convertible

def is_noise_victim(val):
    """Return True if named_victims value is just noise with no real victim."""
    v = str(val).strip().lower()
    if v in ('no', '-', '', 'no named victims'):
        return False  # already clean
    for pattern in NAMED_VICTIMS_NOISE:
        if re.match(pattern, v, re.IGNORECASE):
            return True
    # Check if it ONLY contains source/official attributions but no actual victim
    # Pattern: contains only "(source)" or "(official source)" type entries
    entries = [e.strip() for e in val.split(';')]
    victim_entries = []
    for e in entries:
        # Check if entry has a victim status keyword
        if re.search(r'\b(killed|disappeared|injured|wounded|executed|victim|dead|found)\b', 
                    e, re.IGNORECASE):
            victim_entries.append(e)
        # Or if it's a named individual without source tag
        elif re.search(r'\b(spokesperson|source|official|commentator|reporter)\b', 
                       e, re.IGNORECASE):
            pass  # skip source-only entries
        elif len(e) > 5 and not re.search(r'unnamed|unknown', e, re.IGNORECASE):
            victim_entries.append(e)
    return len(victim_entries) == 0

def standardize_row(row, report):
    """Standardize a single row. Modifies in place. Appends issues to report."""
    
    # ── Boolean columns
    for col in BOOLEAN_COLUMNS:
        if col in row:
            orig = row[col]
            row[col] = normalize_boolean(orig)
            if row[col] != orig and orig not in ('', '-'):
                report.append((row.get('incident_id','?'), col,
                               f"Boolean normalized: '{orig}' → '{row[col]}'"))

    # ── Numeric columns
    for col in NUMERIC_COLUMNS:
        if col in row:
            orig = row[col]
            row[col] = normalize_numeric(orig)

    # ── Null normalization for all columns
    for col in COLUMNS:
        if col in row:
            v = str(row[col]).strip()
            if v == '':
                row[col] = normalize_null(v, col)

    # ── Allowed values check
    for col, allowed in ALLOWED_VALUES.items():
        if col not in row: continue
        val = str(row[col]).strip()
        # Multi-value columns (semicolon separated) - check each part
        if ';' in val:
            parts = [p.strip() for p in val.split(';')]
            for p in parts:
                if p and p not in allowed and p not in ('-', 'No'):
                    report.append((row.get('incident_id','?'), col,
                                  f"Non-standard value: '{p}' (in '{val}')"))
        else:
            if val and val not in allowed and val not in ('-', 'No', ''):
                report.append((row.get('incident_id','?'), col,
                               f"Non-standard value: '{val}'"))

    # ── Column rules from schema
    for condition_fn, field, fix_val, description in COLUMN_RULES:
        try:
            if condition_fn(row):
                old_val = row.get(field, '')
                row[field] = fix_val
                report.append((row.get('incident_id','?'), field,
                               f"RULE: {description} (was: '{old_val}' → '{fix_val}')"))
        except Exception as e:
            pass

    # ── Named victims noise removal
    if 'named_victims' in row:
        val = str(row['named_victims']).strip()
        if val not in ('No', '-', '') and is_noise_victim(val):
            report.append((row.get('incident_id','?'), 'named_victims',
                          f"NOISE REMOVED: '{val[:60]}...' → 'No'"))
            row['named_victims'] = 'No'

    return row

def standardize_csv(input_path, output_path=None):
    """Main standardization function."""
    
    if output_path is None:
        base = input_path.rsplit('.', 1)[0]
        output_path = base + '_standardized.csv'

    # Load
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_cols = list(reader.fieldnames)
        for r in reader:
            rows.append(dict(r))

    print(f"\n{'='*70}")
    print(f"STANDARDIZING: {input_path.split('/')[-1]}")
    print(f"{'='*70}")
    print(f"Input rows: {len(rows)}")
    print(f"Input columns: {len(existing_cols)}")

    # Check column presence
    missing_cols = [c for c in COLUMNS if c not in existing_cols]
    extra_cols   = [c for c in existing_cols if c not in COLUMNS]
    if missing_cols:
        print(f"\nMISSING COLUMNS (will be added with '-'):")
        for c in missing_cols:
            print(f"  + {c}")
    if extra_cols:
        print(f"\nEXTRA COLUMNS (will be removed):")
        for c in extra_cols:
            print(f"  - {c}")

    # Add missing columns with default null value
    for row in rows:
        for col in missing_cols:
            from schema import BOOLEAN_COLUMNS as BC
            row[col] = NULL_NOT_REPORTED if col in BC else NULL_NOT_APPLICABLE

    # Standardize each row
    report = []
    for row in rows:
        standardize_row(row, report)

    # Reorder columns to canonical order (drop extra columns)
    standardized_rows = []
    for row in rows:
        standardized_rows.append({col: row.get(col, NULL_NOT_APPLICABLE) for col in COLUMNS})

    # Write output
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(standardized_rows)

    # Report
    print(f"\nOutput columns: {len(COLUMNS)} (canonical order)")
    print(f"Output rows: {len(standardized_rows)}")
    
    if report:
        print(f"\nSTANDARDIZATION CHANGES ({len(report)}):")
        print(f"{'Row':<8} {'Field':<35} Change")
        print("-"*100)
        for row_id, field, change in report[:50]:  # show first 50
            print(f"{row_id:<8} {field:<35} {change}")
        if len(report) > 50:
            print(f"  ... and {len(report)-50} more changes")
    else:
        print("\n✓ No standardization changes needed.")

    print(f"\n✓ Written: {output_path}")
    return output_path, report

if __name__ == '__main__':
    inp = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if not inp:
        print("Usage: python3 standardize.py input.csv [output.csv]")
        sys.exit(1)
    standardize_csv(inp, out)


"""
pipeline.py — Full processing pipeline for Balochistan incident CSVs.

TWO MODES:
  1. From PDF (full pipeline):
     python3 pipeline.py --pdf FEB_25.pdf --out BAL_FEB2025 --month February --year 2025
     Runs: extract → standardize → sanity check → audit → report

  2. From existing CSV (standardize + audit only):
     python3 pipeline.py input.csv [output.csv]
"""

import csv, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from standardize import standardize_csv
from audit import run_audit

MONTH_MAP = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
}

# ── SANITY CHECK ─────────────────────────────────────────────────────────────

def sanity_check(csv_path, pdf_path=None, month_name=None):
    """
    Compare extracted CSV row count against PDF header count.
    Uses header-count method (your insight): 
    number of 'Month - N' occurrences = exact entry count.
    """
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    csv_count = len(rows)

    # Count PDF entries using header-count method
    pdf_count = None
    pdf_by_day = {}
    if pdf_path and month_name:
        try:
            import pdfplumber, re
            from collections import Counter
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ''.join(page.extract_text()+'\n' for page in pdf.pages)
            HDRX = re.compile(rf'{month_name}\s*-\s*(\d+)', re.IGNORECASE)
            pdf_by_day = Counter(int(m.group(1)) for m in HDRX.finditer(full_text))
            pdf_count = sum(pdf_by_day.values())
        except Exception as e:
            print(f"  (Could not count PDF headers: {e})")

    from collections import Counter
    csv_by_day = Counter(int(r['date'].split('-')[2]) for r in rows)

    print(f"\n{'─'*55}")
    print(f"SANITY CHECK (header-count method)")
    print(f"  PDF total (header count): {pdf_count if pdf_count else 'N/A'}  ← ground truth")
    print(f"  CSV total (extracted):    {csv_count}")

    problems = []
    if pdf_count and pdf_by_day:
        for day in sorted(pdf_by_day.keys()):
            exp = pdf_by_day[day]
            got = csv_by_day.get(day, 0)
            if got != exp:
                problems.append((day, exp, got))

        if not problems:
            print(f"  Match:          ✓ EXACT — all {pdf_count} entries captured per day")
        else:
            print(f"  Match:          ✗ {len(problems)} day(s) off:")
            for day, exp, got in problems:
                print(f"    Feb {day}: expected {exp}, got {got} — check PDF for this date")

    return csv_count, pdf_count

# ── PIPELINE MODES ────────────────────────────────────────────────────────────

def run_from_pdf(pdf_path, out_prefix, month_name, year):
    """Full pipeline: PDF → Full CSV → Standardize → Sanity → Audit."""
    from extractor import extract

    full_path = out_prefix + '_Full.csv'
    std_path  = out_prefix + '_Full_std.csv'
    final_path = out_prefix + '_Full_pipeline.csv'
    report_path = out_prefix + '_Full_audit_report.txt'

    print(f"\n{'#'*65}")
    print(f"# PIPELINE (PDF mode): {pdf_path.split('/')[-1]}")
    print(f"{'#'*65}")

    # Step 1: Extract
    print(f"\n[STEP 1/3] EXTRACTING...")
    extract(pdf_path, full_path, month_name, year)

    # Step 2: Sanity check
    print(f"\n[STEP 2/3] SANITY CHECK...")
    csv_count, pdf_count = sanity_check(full_path, pdf_path, month_name)

    if pdf_count and (csv_count / pdf_count) < 0.95:
        print(f"\n  ⚠ Entry count below 95% — review parser before proceeding.")

    # Step 3: Standardize + Audit
    print(f"\n[STEP 3/3] STANDARDIZE + AUDIT...")
    standardize_csv(full_path, std_path)
    issues = run_audit(std_path)

    shutil.copy(std_path, final_path)
    try: os.remove(std_path)
    except: pass

    # Save report
    _save_report(report_path, issues)

    _print_summary(full_path, final_path, report_path, csv_count, pdf_count, issues)
    return final_path

def run_from_csv(input_path, output_path=None):
    """CSV-only pipeline: Standardize → Audit."""
    base = input_path.rsplit('.', 1)[0]
    std_path   = base + '_std.csv'
    final_path = output_path or (base + '_pipeline.csv')
    report_path = base + '_audit_report.txt'

    print(f"\n{'#'*65}")
    print(f"# PIPELINE (CSV mode): {input_path.split('/')[-1]}")
    print(f"{'#'*65}")

    print(f"\n[STEP 1/2] STANDARDIZING...")
    std_out, std_report = standardize_csv(input_path, std_path)

    print(f"\n[STEP 2/2] AUDITING...")
    issues = run_audit(std_path)

    shutil.copy(std_path, final_path)
    try: os.remove(std_path)
    except: pass

    _save_report(report_path, issues)

    rows = sum(1 for _ in open(final_path)) - 1
    _print_summary(input_path, final_path, report_path, rows, None, issues)
    return final_path

def _save_report(report_path, issues):
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("AUDIT FLAGS\n" + "="*50 + "\n\n")
        if issues:
            for issue in issues:
                f.write(f"Row {issue['row']} | {issue['field']}: "
                       f"current='{issue['current']}' hint='{issue['hint']}'\n"
                       f"  → {issue['reason']}\n\n")
        else:
            f.write("No issues found.\n")

def _print_summary(inp, out, report, csv_count, pdf_count, issues):
    from collections import Counter
    print(f"\n{'─'*65}")
    print(f"PIPELINE COMPLETE")
    print(f"  Input:          {inp.split('/')[-1]}")
    print(f"  Output:         {out.split('/')[-1]}")
    print(f"  Audit report:   {report.split('/')[-1]}")
    if pdf_count:
        pct = csv_count/pdf_count*100
        status = '✓' if csv_count==pdf_count else f'⚠ {csv_count}/{pdf_count} ({pct:.0f}%)'
        print(f"  Entry count:    {status}")
    print(f"  Audit flags:    {len(issues) if issues else 0}")

    if issues:
        fc = Counter(i['field'] for i in issues)
        print(f"\n  Top flagged fields:")
        for field, count in fc.most_common(5):
            bar = '█' * min(count, 20)
            print(f"    {field:<35} {count:3d}  {bar}")

    verdict = "✓ CLEAN" if (not issues or len(issues) <= 5) else f"⚠ {len(issues)} FLAGS — REVIEW NEEDED"
    print(f"\n  Status: {verdict}")
    print(f"{'─'*65}\n")

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    args = sys.argv[1:]

    if '--pdf' in args:
        # PDF mode
        pdf_idx  = args.index('--pdf') + 1
        out_idx  = args.index('--out') + 1 if '--out' in args else None
        mon_idx  = args.index('--month') + 1 if '--month' in args else None
        yr_idx   = args.index('--year') + 1 if '--year' in args else None

        pdf_path   = args[pdf_idx]
        out_prefix = args[out_idx] if out_idx else pdf_path.rsplit('.', 1)[0]
        month_name = args[mon_idx] if mon_idx else 'February'
        year       = int(args[yr_idx]) if yr_idx else 2025

        run_from_pdf(pdf_path, out_prefix, month_name, year)

    elif len(args) >= 1 and args[0].endswith('.csv'):
        inp = args[0]
        out = args[1] if len(args) > 1 else None
        run_from_csv(inp, out)

    else:
        print("Usage:")
        print("  From PDF:  python3 pipeline.py --pdf FEB_25.pdf --out BAL_FEB2025 --month February --year 2025")
        print("  From CSV:  python3 pipeline.py input.csv [output.csv]")
        sys.exit(1)

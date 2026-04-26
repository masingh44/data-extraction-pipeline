#!/usr/bin/env python3
"""
verify.py — Post-pipeline verification for Balochistan incident CSVs.

Re-reads each row's original_description and cross-checks critical fields
against what the text actually says. Produces a flagged report sorted by
confidence, so you can fix the most likely errors first.

Usage:
  python3 verify.py BAL_FEB2025_Full_pipeline.csv
  python3 verify.py BAL_FEB2025_Full_pipeline.csv --fix   # auto-fix high-confidence issues
  python3 verify.py BAL_FEB2025_Full_pipeline.csv --html   # produce HTML report

Checks (columns 6–48: district → economic_sector_targeted):
  1. incident_type vs text patterns
  2. attack_method consistency with incident_type and text
  3. target_organization vs text context
  4. perpetrator_group vs text (claim statements, SF actions)
  5. named_victims completeness (names in text but missing from field)
  6. disappeared_names / num_disappeared consistency
  7. disappearance_circumstances vs text
  8. sf_killed / sf_injured vs text numbers
  9. civilian_killed / civilian_injured vs text numbers
  10. militant_killed vs text
  11. death_squad / informant flags vs text
  12. property_damaged consistency
"""

import csv, re, sys, os
from collections import Counter, defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def has(text, *patterns):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)

WORD_NUMS = {
    'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,
    'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'thirteen':13,
    'fourteen':14,'fifteen':15,'sixteen':16,'seventeen':17,'eighteen':18,
    'nineteen':19,'twenty':20,
}

def to_num(text):
    m = re.search(r'\b(\d+)\b', text)
    if m: return int(m.group(1))
    t = text.lower()
    for w, n in sorted(WORD_NUMS.items(), key=lambda x: -len(x[0])):
        if re.search(rf'\b{w}\b', t): return n
    return 0

_NUM = r'(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)'
SF_UNITS = r'(?:soldiers?|Frontier\s+Corps.*?personnel|FC\s+personnel|Army\s+personnel|personnel|troops?|policem[ae]n|police\s+personnel|levies\s+personnel|constables?)'

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION CHECKS — each returns list of Flag dicts
# ═══════════════════════════════════════════════════════════════════════════════

class Flag:
    """A single verification flag."""
    def __init__(self, row_id, field, current, expected, reason, confidence='Medium'):
        self.row_id = row_id
        self.field = field
        self.current = str(current)[:80]
        self.expected = str(expected)[:80]
        self.reason = reason
        self.confidence = confidence  # High, Medium, Low

def check_incident_type(row):
    flags = []
    text = row.get('original_description','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    # META-ENTRY CHECK (feedback): statements/announcements misclassified as attacks
    first_50 = text[:200].lower()
    if has(first_50, r'announced|confirmed|stated\s+in\s+(?:a\s+)?briefing',
                      r'released\s+a\s+statement', r'according\s+to\s+(?:the\s+)?(?:report|ispr)',
                      r'according\s+to\s+\w{3,30}\s*spokesperson',
                      r'press\s+(?:release|conference)', r'on\s+the\s+floor\s+of'):
        if itype not in ('Aggregate report', 'Surrender', 'Protest/sit-in'):
            if not has(text[:200], r'killed|shot\s+dead|ambushed|opened\s+fire|bomb\s+(?:attack|blast)'):
                flags.append(Flag(rid, 'incident_type', itype, 'Aggregate report?',
                    'Entry appears to be a statement/announcement, not an incident', 'High'))

    # IED without explosive language (expanded regex per feedback)
    if itype == 'IED':
        if not has(text, r'\bIED\b', r'improvised\s+explosive', r'roadside\s+explosion',
                        r'remote.controlled\s+(?:bomb|device|explosive)', r'bomb\s+(?:struck|detonated|exploded|blast)',
                        r'car\s+rigged', r'explosion\s+(?:occurred|took)', r'blast\s+(?:caused|occurred)',
                        r'\b(?:bomb|mine|explosive\s+device)\b.*?\b(?:targeted|blast|exploded|detonated|went\s+off)\b',
                        r'anti.personnel\s+mine'):
            flags.append(Flag(rid, 'incident_type', itype, '?',
                'Type=IED but no explosive/blast/IED language found in text', 'High'))

    # Targeted killing but text describes an armed assault on a group
    if itype == 'Targeted killing':
        if has(text, r'(?:\d+|at\s+least\s+\w+)\s+soldiers?\s+(?:were\s+)?killed',
                     r'ambushed\s+(?:a\s+)?(?:convoy|patrol|military)',
                     r'attacked\s+(?:a\s+)?(?:military|army|security)'):
            flags.append(Flag(rid, 'incident_type', itype, 'Armed assault?',
                'Type=Targeted killing but text describes a military engagement', 'Medium'))

    # ED but text describes a killing
    if itype == 'Enforced disappearance':
        if has(text, r'(?:was\s+)?(?:shot\s+dead|killed|executed|body\s+(?:found|recovered))'):
            if not has(text, r'enforced\s+disappear|forcibly\s+disappear'):
                flags.append(Flag(rid, 'incident_type', itype, 'Targeted killing/EJK?',
                    'Type=ED but text describes a killing without disappearance language', 'High'))

    return flags


def check_attack_method(row):
    flags = []
    text = row.get('original_description','')
    method = row.get('attack_method','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    NON_ATTACK = {'Enforced disappearance','Aggregate report','Surrender',
                  'IBO','Protest/sit-in','Prisoner release','Armed robbery'}

    # Non-attack type should have method = '-'
    if itype in NON_ATTACK and method not in ('-',''):
        flags.append(Flag(rid, 'attack_method', method, '-',
            f'Non-attack type ({itype}) should have attack_method=-', 'High'))

    # Attack type but method is '-'
    if itype not in NON_ATTACK and method == '-':
        if has(text, r'opened\s+fire|shot|sniper|grenade|rocket|IED|bomb|ambush'):
            flags.append(Flag(rid, 'attack_method', '-', '?',
                f'Attack type ({itype}) has method=- but text describes weapons', 'Medium'))

    # IED in method but no IED in text
    if 'IED' in method:
        if not has(text, r'\bIED\b', r'improvised\s+explosive', r'bomb', r'blast', r'explosion'):
            flags.append(Flag(rid, 'attack_method', method, 'Small arms?',
                'Method contains IED but no explosive language in text', 'High'))

    return flags


def check_perpetrator(row):
    flags = []
    text = row.get('original_description','')
    perp = row.get('perpetrator_group','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    # SF as perpetrator on non-ED/EJK/IBO
    sf_types = {'Enforced disappearance','Extrajudicial killing','IBO'}
    if 'Security Forces' in perp and itype not in sf_types:
        if not has(text, r'security\s+forces?\s+(?:opened\s+fire|attacked|targeted|shot|fired)',
                        r'SF\s+(?:opened\s+fire|attacked|targeted)'):
            flags.append(Flag(rid, 'perpetrator_group', perp, '?',
                'SF as perpetrator on non-ED/EJK/IBO entry — verify SF acted against victim', 'Medium'))

    # ED but perpetrator is Unidentified when text says SF
    if itype in ('Enforced disappearance','Extrajudicial killing') and perp == 'Unidentified':
        if has(text, r'[Ss]ecurity\s+[Ff]orces', r'\bSFs?\b', r'intelligence\s+agenc',
                     r'plainclothes', r'Frontier\s+Corps'):
            flags.append(Flag(rid, 'perpetrator_group', 'Unidentified', 'Security Forces?',
                'ED/EJK with Unidentified perpetrator but text mentions SF/intelligence', 'High'))

    # Text has group claim but perpetrator is Unidentified
    if perp == 'Unidentified':
        for grp, pat in [('BLA', r'\bBLA\b.*claim'), ('BLF', r'\bBLF\b.*claim'),
                         ('BRG', r'\bBRG\b.*claim'), ('UBA', r'\bUBA\b.*claim'),
                         ('TTP', r'\bTTP\b.*claim')]:
            if has(text, pat):
                flags.append(Flag(rid, 'perpetrator_group', 'Unidentified', grp,
                    f'Text contains {grp} claim statement but perpetrator=Unidentified', 'High'))

    return flags


def check_named_victims(row):
    flags = []
    text = row.get('original_description','')
    nv = row.get('named_victims','No')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    if itype in ('Aggregate report','Surrender'):
        return flags

    # Count names in text vs names in named_victims
    name_indicators = len(re.findall(
        r'identified\s+as\s+[A-Z]|(?:son|daughter)\s+of\s+[A-Z]|\bs/o\s+[A-Z]|'
        r'(?:Naik|Lance\s+Naik|Soldier|Lieutenant|Colonel|DSP|SSP)\s+[A-Z]',
        text))

    if name_indicators >= 1 and nv == 'No':
        flags.append(Flag(rid, 'named_victims', 'No', f'{name_indicators} name(s) in text',
            'Text contains named individuals but named_victims=No', 'Medium'))

    # Check for names in text that are NOT in named_victims
    if nv != 'No' and name_indicators > 0:
        # Count semicolons as rough name count
        nv_count = nv.count(';') + 1
        if name_indicators > nv_count + 1:
            flags.append(Flag(rid, 'named_victims', f'{nv_count} names', f'{name_indicators} in text',
                'More names found in text than in named_victims field', 'Low'))

    return flags


def check_disappeared(row):
    flags = []
    text = row.get('original_description','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    if itype != 'Enforced disappearance':
        return flags

    # num_disappeared vs disappeared_names count
    num_d = row.get('num_disappeared','No')
    d_names = row.get('disappeared_names','No')

    if d_names not in ('No','-','') and num_d not in ('No','-',''):
        name_count = len([n for n in d_names.split(';') if n.strip()])
        try:
            expected = int(num_d)
            if name_count != expected and expected > 0:
                flags.append(Flag(rid, 'num_disappeared', num_d, f'{name_count} (from names)',
                    f'num_disappeared={num_d} but {name_count} names listed', 'Medium'))
        except ValueError:
            pass

    # Disappeared names missing but text has "identified as"
    if d_names in ('No','-',''):
        if has(text, r'identified\s+as\s+[A-Z]', r'\bs/o\s+[A-Z]', r'son\s+of\s+[A-Z]'):
            flags.append(Flag(rid, 'disappeared_names', 'No', 'Names in text',
                'ED entry has no disappeared_names but text contains identifiable names', 'High'))

    # disappearance_circumstances check
    circ = row.get('disappearance_circumstances','-')
    if circ in ('-',''):
        if has(text, r'raid.*home|home.*raid|stormed.*home|from\s+(?:his|their)\s+home'):
            flags.append(Flag(rid, 'disappearance_circumstances', circ, 'Raid on home',
                'Text describes home raid but circumstances not filled', 'Medium'))
        elif has(text, r'checkpoint|check\s*post'):
            flags.append(Flag(rid, 'disappearance_circumstances', circ, 'At checkpoint',
                'Text mentions checkpoint but circumstances not filled', 'Medium'))

    return flags


def check_casualties(row):
    flags = []
    text = row.get('original_description','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    if itype in ('Aggregate report','Enforced disappearance','Surrender','Protest/sit-in'):
        return flags

    # ── SF killed ────────────────────────────────────────────────────────
    sf_k = int(row.get('sf_killed','0')) if str(row.get('sf_killed','0')).isdigit() else 0
    # Extract from text
    text_sf_k = 0
    patterns_sfk = [
        rf'({_NUM})\s+{SF_UNITS}\s+(?:were\s+|was\s+)?killed',
        rf'killing\s+({_NUM})\s+{SF_UNITS}',
        rf'killed\s+({_NUM})\s+(?:Pakistani\s+)?{SF_UNITS}',
        rf'death\s+toll.*?increased\s+to\s+({_NUM})',
        rf'eliminating\s+all\s+({_NUM})\s+personnel',
    ]
    for p in patterns_sfk:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g:
                    n = to_num(g)
                    if n > text_sf_k: text_sf_k = n

    if text_sf_k > 0 and sf_k == 0:
        flags.append(Flag(rid, 'sf_killed', '0', str(text_sf_k),
            f'Text mentions {text_sf_k} SF killed but sf_killed=0', 'High'))
    elif text_sf_k > 0 and sf_k > 0 and abs(text_sf_k - sf_k) > 1:
        flags.append(Flag(rid, 'sf_killed', str(sf_k), str(text_sf_k),
            f'sf_killed={sf_k} but text suggests {text_sf_k}', 'Medium'))

    # ── Civilian killed ──────────────────────────────────────────────────
    civ_k = int(row.get('civilian_killed','0')) if str(row.get('civilian_killed','0')).isdigit() else 0
    text_civ_k = 0
    # Count from text patterns
    civ_pats = [
        rf'({_NUM})\s+(?:civilians?|workers?|persons?|people|coal\s+mine\s+workers?)\s+(?:were\s+)?(?:shot\s+)?(?:killed|dead)',
        rf'({_NUM})\s+(?:people\s+of\s+\w+\s+ethnicity)\s+(?:were\s+)?(?:shot\s+dead|killed)',
    ]
    for p in civ_pats:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g:
                    n = to_num(g)
                    if n > text_civ_k: text_civ_k = n

    if itype == 'Targeted killing' and civ_k == 0:
        if has(text, r'shot\s+dead|was\s+killed|gunned\s+down') and not has(text, r'soldier|military|police|levies'):
            flags.append(Flag(rid, 'civilian_killed', '0', '≥1',
                'Targeted killing with "shot dead" in text but civilian_killed=0', 'High'))
    if text_civ_k > 0 and civ_k == 0:
        flags.append(Flag(rid, 'civilian_killed', '0', str(text_civ_k),
            f'Text mentions {text_civ_k} civilians killed but civilian_killed=0', 'Medium'))

    # ── Group claim vs official ──────────────────────────────────────────
    grp_claim = row.get('group_claimed_sf_killed','-')
    if grp_claim not in ('-','0','No',''):
        try:
            grp_n = int(grp_claim)
            if grp_n > 0 and sf_k > 0 and grp_n > sf_k * 1.5:
                if row.get('conflicting_claims','') != 'Yes':
                    flags.append(Flag(rid, 'conflicting_claims', 'No', 'Yes',
                        f'Group claims {grp_n} but official={sf_k}; conflicting_claims should be Yes', 'High'))
        except ValueError:
            pass

    return flags


def check_target_organization(row):
    flags = []
    text = row.get('original_description','')
    tgt_org = row.get('target_organization','')
    itype = row.get('incident_type','')
    rid = row.get('incident_id','?')

    if itype in ('Aggregate report','Surrender','Protest/sit-in'):
        return flags

    # target_org is empty/dash but text has clear target
    if tgt_org in ('-','','No'):
        if has(text, r'military\s+(?:camp|post|convoy)|army|FC\b|frontier\s+corps|security\s+forces?\s+(?:camp|post|convoy)'):
            flags.append(Flag(rid, 'target_organization', '-', 'Army/FC?',
                'target_organization empty but text mentions military/SF target', 'Medium'))
        elif has(text, r'police\s+(?:checkpoint|station|training)'):
            flags.append(Flag(rid, 'target_organization', '-', 'Police?',
                'target_organization empty but text mentions police target', 'Medium'))
        elif itype == 'Targeted killing':
            flags.append(Flag(rid, 'target_organization', '-', 'Civilian?',
                'Targeted killing with empty target_organization — likely Civilian', 'Low'))

    return flags


def check_property(row):
    flags = []
    text = row.get('original_description','')
    prop = row.get('property_damaged','No')
    rid = row.get('incident_id','?')

    if prop == 'No':
        if has(text, r'(?:set\s+(?:fire|ablaze)|destroyed|burned|damaged)\s+(?:the\s+)?(?:vehicle|building|machinery|post|station|checkpoint|office)',
                     r'vehicle\s+was\s+(?:completely\s+)?destroyed',
                     r'completely\s+destroyed\s+the\s+(?:targeted\s+)?vehicle'):
            flags.append(Flag(rid, 'property_damaged', 'No', 'Yes',
                'Text describes property destruction but property_damaged=No', 'Medium'))

    return flags


def check_cross_field(row):
    """Cross-field consistency checks (feedback issues #4, #5, audit section)."""
    flags = []
    rid = row.get('incident_id','?')

    # Issue #4: claimed=Yes + perpetrator=Unidentified should be impossible
    claimed = row.get('claimed_responsibility','No')
    perp = row.get('perpetrator_group','Unidentified')
    if claimed == 'Yes' and perp == 'Unidentified':
        flags.append(Flag(rid, 'perpetrator_group', 'Unidentified', '?',
            'claimed_responsibility=Yes but perpetrator_group=Unidentified — impossible combination', 'High'))

    # Audit feedback: sf_injured == civilian_injured mirroring (same people counted twice)
    sf_i = row.get('sf_injured','0')
    civ_i = row.get('civilian_injured','0')
    if sf_i.isdigit() and civ_i.isdigit():
        if int(sf_i) > 0 and int(civ_i) > 0 and sf_i == civ_i:
            flags.append(Flag(rid, 'civilian_injured', civ_i, '0?',
                f'sf_injured={sf_i} and civilian_injured={civ_i} are identical — possible double-count', 'Medium'))

    # Audit feedback: death_squad_targeted=Yes but perpetrator=Death Squad (contradictory)
    ds_tgt = row.get('death_squad_targeted','No')
    if ds_tgt == 'Yes' and 'Death squad' in perp:
        flags.append(Flag(rid, 'death_squad_targeted', 'Yes', 'No?',
            'death_squad_targeted=Yes but perpetrator IS the death squad — contradictory', 'High'))

    # Group claim >> sf_killed without conflicting_claims=Yes
    grp_claim = row.get('group_claimed_sf_killed','-')
    sf_k = row.get('sf_killed','0')
    conflict = row.get('conflicting_claims','No')
    if grp_claim not in ('-','0','No','') and sf_k.isdigit():
        try:
            grp_n = int(grp_claim)
            sf_n = int(sf_k)
            if grp_n > 0 and sf_n >= 0 and grp_n > sf_n * 1.5:
                if conflict != 'Yes':
                    flags.append(Flag(rid, 'conflicting_claims', 'No', 'Yes',
                        f'Group claims {grp_n} SF killed vs official {sf_n} — should set conflicting_claims=Yes', 'High'))
        except ValueError:
            pass

    return flags


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

ALL_CHECKS = [
    check_incident_type,
    check_attack_method,
    check_perpetrator,
    check_named_victims,
    check_disappeared,
    check_casualties,
    check_target_organization,
    check_property,
    check_cross_field,
]

def run_verification(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    all_flags = []
    for row in rows:
        for check_fn in ALL_CHECKS:
            try:
                flags = check_fn(row)
                all_flags.extend(flags)
            except Exception as e:
                pass

    return rows, all_flags


def print_report(csv_path, rows, flags):
    # Sort: High confidence first, then by row
    priority = {'High': 0, 'Medium': 1, 'Low': 2}
    flags.sort(key=lambda f: (priority.get(f.confidence, 9), f.row_id))

    print(f"\n{'═'*90}")
    print(f"VERIFICATION REPORT: {os.path.basename(csv_path)}")
    print(f"{'═'*90}")
    print(f"  Rows checked:  {len(rows)}")
    print(f"  Total flags:   {len(flags)}")

    # Summary by confidence
    by_conf = Counter(f.confidence for f in flags)
    print(f"\n  🔴 High confidence:   {by_conf.get('High',0)}")
    print(f"  🟡 Medium confidence: {by_conf.get('Medium',0)}")
    print(f"  ⚪ Low confidence:    {by_conf.get('Low',0)}")

    # Summary by field
    by_field = Counter(f.field for f in flags)
    print(f"\n  Flags by field:")
    for field, count in by_field.most_common(15):
        bar = '█' * min(count, 30)
        print(f"    {field:<35} {count:3d}  {bar}")

    if not flags:
        print(f"\n  ✓ No issues found. CSV looks clean.")
        return

    # Detail: High confidence first
    for conf_level in ['High', 'Medium', 'Low']:
        level_flags = [f for f in flags if f.confidence == conf_level]
        if not level_flags:
            continue

        icon = {'High': '🔴', 'Medium': '🟡', 'Low': '⚪'}[conf_level]
        print(f"\n{'─'*90}")
        print(f"{icon} {conf_level.upper()} CONFIDENCE FLAGS ({len(level_flags)})")
        print(f"{'─'*90}")
        print(f"{'Row':<18} {'Field':<30} {'Current':<22} {'Expected':<22} Reason")
        print(f"{'-'*18} {'-'*30} {'-'*22} {'-'*22} {'-'*40}")

        for f in level_flags:
            print(f"{f.row_id:<18} {f.field:<30} {f.current:<22} {f.expected:<22} {f.reason}")

    print(f"\n{'═'*90}")
    print(f"  ACTION: Review 🔴 HIGH flags first — these are most likely real errors.")
    print(f"  Then check 🟡 MEDIUM flags. ⚪ LOW flags are informational.")
    print(f"{'═'*90}\n")


def generate_html_report(csv_path, rows, flags):
    """Generate an HTML report for browser viewing."""
    priority = {'High': 0, 'Medium': 1, 'Low': 2}
    flags.sort(key=lambda f: (priority.get(f.confidence, 9), f.row_id))

    by_conf = Counter(f.confidence for f in flags)
    by_field = Counter(f.field for f in flags)

    base = os.path.basename(csv_path).rsplit('.', 1)[0]
    html_path = csv_path.rsplit('.', 1)[0] + '_verification.html'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Verification: {base}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2rem; background: #f8f9fa; color: #333; }}
  h1 {{ color: #1a1a2e; }}
  .summary {{ display: flex; gap: 1.5rem; margin: 1rem 0; }}
  .stat {{ background: white; padding: 1rem 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .stat .num {{ font-size: 2rem; font-weight: 700; }}
  .high {{ color: #dc3545; }} .medium {{ color: #ffc107; }} .low {{ color: #6c757d; }}
  table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin: 1rem 0; }}
  th {{ background: #1a1a2e; color: white; padding: 0.7rem; text-align: left; font-size: 0.85rem; }}
  td {{ padding: 0.6rem 0.7rem; border-bottom: 1px solid #eee; font-size: 0.85rem; }}
  tr:hover {{ background: #f0f4ff; }}
  .conf-high {{ background: #fff5f5; }} .conf-medium {{ background: #fffbeb; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
  .badge-high {{ background: #dc3545; color: white; }}
  .badge-medium {{ background: #ffc107; color: #333; }}
  .badge-low {{ background: #e9ecef; color: #666; }}
  .field-bar {{ display: flex; gap: 0.5rem; align-items: center; margin: 0.3rem 0; }}
  .bar {{ height: 8px; background: #4361ee; border-radius: 4px; }}
</style></head><body>
<h1>Verification Report — {base}</h1>
<div class="summary">
  <div class="stat"><div class="num">{len(rows)}</div>Rows</div>
  <div class="stat"><div class="num">{len(flags)}</div>Flags</div>
  <div class="stat"><div class="num high">{by_conf.get('High',0)}</div>High</div>
  <div class="stat"><div class="num medium">{by_conf.get('Medium',0)}</div>Medium</div>
  <div class="stat"><div class="num low">{by_conf.get('Low',0)}</div>Low</div>
</div>

<h2>Flags by Field</h2>
<div style="max-width:600px">"""

    max_count = max(by_field.values()) if by_field else 1
    for field, count in by_field.most_common(15):
        pct = count / max_count * 100
        html += f'<div class="field-bar"><span style="width:200px">{field}</span><div class="bar" style="width:{pct}%"></div><span>{count}</span></div>\n'

    html += "</div>\n<h2>All Flags</h2>\n<table>\n"
    html += "<tr><th>Confidence</th><th>Row</th><th>Field</th><th>Current</th><th>Expected</th><th>Reason</th></tr>\n"

    for f in flags:
        cls = f'conf-{f.confidence.lower()}'
        badge = f'badge-{f.confidence.lower()}'
        html += f'<tr class="{cls}"><td><span class="badge {badge}">{f.confidence}</span></td>'
        html += f'<td>{f.row_id}</td><td><b>{f.field}</b></td>'
        html += f'<td>{f.current}</td><td>{f.expected}</td><td>{f.reason}</td></tr>\n'

    html += "</table>\n</body></html>"

    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return html_path


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_html = '--html' in sys.argv

    if not args:
        print("Usage: python3 verify.py pipeline_output.csv [--html]")
        print("  --html  Generate HTML report for browser viewing")
        sys.exit(1)

    csv_path = args[0]
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)

    rows, flags = run_verification(csv_path)
    print_report(csv_path, rows, flags)

    if do_html:
        html_path = generate_html_report(csv_path, rows, flags)
        print(f"  HTML report: {html_path}")

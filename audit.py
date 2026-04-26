"""
audit.py — Smart field-level audit for Balochistan incidents CSVs.
Reads original_description and compares against field values.
Far more precise than checking fields in isolation.

Usage:
  python3 audit.py input.csv [--fix]
  --fix: apply auto-fixable corrections and write input_audited.csv

TO ADD A NEW AUDIT RULE:
  Add a function to the RULES list at the bottom of this file.
  Each function signature: rule(row) -> list of (field, current, hint, reason)
  Return empty list if no issues found.
"""

import csv, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import (COLUMNS, NON_ATTACK_TYPES, BOOLEAN_COLUMNS,
                    NULL_NOT_APPLICABLE, NULL_NOT_REPORTED)

# ── PATTERN LIBRARIES (extend these as new patterns are discovered) ───────────

SF_KILLED_PATTERNS = [
    (r'(\d+)\s+(?:soldiers?|personnel|troops?|FC\s+personnel|Army\s+personnel|policem[ae]n|police\s+personnel|Levies\s+personnel|constables?|Rangers?)\s+(?:were\s+|was\s+)?killed', 1),
    (r'killing\s+(\d+)\s+(?:soldiers?|personnel|troops?)', 1),
    (r'killed\s+(\d+)\s+(?:Pakistani\s+)?(?:soldiers?|personnel|troops?)', 1),
    (r'death\s+toll.*?increased\s+to\s+(\d+)', 1),
    (r'(\d+)\s+(?:soldiers?|personnel)\s+killed\s+on\s+the\s+spot', 1),
    (r'eliminating\s+all\s+(\d+)\s+personnel\s+on\s+board', 1),
    (r'resulting\s+in\s+the\s+death\s+of\s+(\d+)', 1),
    (r'(?:at\s+least\s+)?(\d+)\s+(?:soldiers?|personnel|troops?)\s+(?:and\s+.{1,80}?\s+)?(?:were\s+|was\s+)?killed', 1),
    (r'one\s+(?:soldier|FC\s+personnel|policem[ae]n|Levies\s+personnel)\s+(?:was\s+)?killed', 0),
    (r'two\s+(?:soldiers?|FC\s+personnel|policem[ae]n)\s+(?:were\s+)?killed', 0),
    (r'three\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed', 0),
    (r'four\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed', 0),
    (r'five\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed', 0),
    (r'six\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed', 0),
    (r'seven\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed', 0),
    (r'killed\s+two\s+Security\s+Forces?\s*(?:\(SFs?\)\s*)?personnel', 0),
]

SF_INJURED_PATTERNS = [
    (r'(\d+)\s+(?:others?|soldiers?|personnel|policem[ae]n)\s+(?:were\s+)?(?:sustained\s+)?injur', 1),
    (r'injuring\s+(?:at\s+least\s+)?(\d+)', 1),
    (r'(\d+)\s+(?:others?|personnel)\s+sustained\s+injur', 1),
    (r'one\s+(?:soldier|personnel|policem[ae]n)\s+sustained\s+injur', 0),
    (r'two\s+(?:soldiers?|personnel)\s+sustained\s+injur', 0),
    (r'three\s+(?:soldiers?|personnel)\s+sustained\s+injur', 0),
    (r'four\s+(?:soldiers?|personnel)\s+sustained\s+injur', 0),
]

CIV_KILLED_PATTERNS = [
    (r'(\d+)\s+civilians?\s+(?:were\s+)?killed', 1),
    (r'(\d+)\s+(?:workers?|miners?|passengers?|persons?|people)\s+(?:were\s+)?killed', 1),
    (r'eleven\s+coal\s+mine\s+workers?\s+(?:were\s+)?killed', 0),
    (r'shot\s+(?:him|her)\s+dead', 0),
    (r'killing\s+(?:him|her)\s+on\s+the\s+spot', 0),
    (r'one\s+(?:worker|miner|passenger|civilian|teenager|youth|man|woman|girl|boy|person)\s+(?:was\s+)?killed', 0),
    (r'two\s+(?:members?|persons?|civilians?|passengers?|brothers?)\s+(?:were\s+)?(?:shot\s+)?dead', 0),
    (r'found\s+(?:dead|deceased)', 0),
    (r'body\s+(?:was\s+)?(?:found|recovered|discovered)', 0),
]

ACTUAL_IED_PATTERNS = [
    r'improvised\s+explosive\s+device', r'\bIED\b', r'roadside\s+explosion',
    r'remote.controlled\s+(?:bomb|device|IED)', r'motorcycle\s+planted\s+with',
    r'car\s+rigged\s+with\s+explosives', r'blast\s+(?:caused|occurred|when)',
    r'bomb\s+(?:struck|detonated|exploded)', r'explosion\s+(?:occurred|took\s+place)',
]

NAME_PATTERNS = [
    r'\bidentified as\b', r'\bs/o\b', r'\bson of\b', r'\bdaughter of\b', r'\bd/o\b',
    r'\bNaik\s+[A-Z]', r'\bLance Naik\s+[A-Z]', r'\bSepoy\s+[A-Z]',
    r'\bCaptain\s+[A-Z]', r'\bLieutenant\s+[A-Z]', r'\bColonel\s+[A-Z]',
    r'\bSubedar\s+[A-Z]', r'\bDSP\s+[A-Z]', r'\bSSP\s+[A-Z]',
    r'age\s+\d+', r'aged\s+\d+', r'\(\d{2}\)',
]

def word_to_num(text):
    mapping = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,
               'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'thirteen':13,
               'fourteen':14,'fifteen':15,'sixteen':16,'seventeen':17,'eighteen':18}
    t = text.lower()
    for w, n in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if re.search(r'\b' + w + r'\b', t):
            return n
    m = re.search(r'(\d+)', text)
    return int(m.group(1)) if m else 0

def extract_number(patterns, text):
    """Returns best number estimate from text using pattern list."""
    max_n = 0
    for pattern, has_group in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if has_group:
                try: n = word_to_num(m.group(1))
                except: n = word_to_num(m.group(0))
            else:
                n = word_to_num(m.group(0))
            if n > max_n:
                max_n = n
    return max_n

def has_name_in_text(text):
    return any(re.search(p, text, re.IGNORECASE) for p in NAME_PATTERNS)

# ── INDIVIDUAL AUDIT RULES ────────────────────────────────────────────────────
# Each returns list of (field, current, hint, reason). Empty = no issue.
# ADD NEW RULES HERE — each is a standalone function.

def rule_ied_type_no_ied_in_text(row):
    issues = []
    if row['incident_type'] == 'IED':
        text = row.get('original_description','')
        if not any(re.search(p, text, re.IGNORECASE) for p in ACTUAL_IED_PATTERNS):
            issues.append(('incident_type', 'IED', '?',
                'Type=IED but no IED/explosive/blast language in original_description'))
    return issues

def rule_attack_method_ied_no_ied_in_text(row):
    issues = []
    text = row.get('original_description','')
    method = row.get('attack_method','')
    if 'IED' in method and row['incident_type'] not in ['IED','Suicide bombing']:
        if not any(re.search(p, text, re.IGNORECASE) for p in ACTUAL_IED_PATTERNS):
            clean = re.sub(r'(?:;\s*)?IED(?:;\s*)?', '', method).strip('; ')
            issues.append(('attack_method', method, clean or 'Small arms',
                'attack_method contains IED but no IED/explosive found in text'))
    return issues

def rule_drone_is_helicopter_response(row):
    issues = []
    if 'Drone' in row.get('attack_method',''):
        text = row.get('original_description','')
        if re.search(r'helicopter|aerial\s+shelling|air\s+support|gunship', text, re.IGNORECASE):
            clean = re.sub(r'(?:;\s*)?Drone(?:;\s*)?', '', row['attack_method']).strip('; ')
            issues.append(('attack_method', row['attack_method'], clean,
                'Drone likely refers to helicopter RESPONSE by SF, not attack method'))
    return issues

def rule_non_attack_has_method(row):
    issues = []
    if row['incident_type'] in NON_ATTACK_TYPES:
        if row.get('attack_method','') not in ['-','','No']:
            issues.append(('attack_method', row['attack_method'], '-',
                f"Non-attack type ({row['incident_type']}) must have attack_method=-"))
    return issues

def rule_target_political_figure_unverified(row):
    issues = []
    text = row.get('original_description','')
    if 'Political figure' in row.get('target_type',''):
        if not re.search(
            r'(?:MPA|MNA|minister|commissioner|DC\b|AC\b|senator|mayor)\s+(?:killed|injured|targeted|attacked|shot|wounded)',
            text, re.IGNORECASE):
            issues.append(('target_type', row['target_type'], '?',
                'target_type=Political figure but no official confirmed attacked in text'))
    return issues

def rule_target_railway_unverified(row):
    issues = []
    if 'Railway' in row.get('target_type',''):
        text = row.get('original_description','')
        if not re.search(
            r'(?:railway|train|rail\s+track|jaffar\s+express)\s+(?:was\s+)?(?:attacked|targeted|struck|blown|derailed)',
            text, re.IGNORECASE):
            issues.append(('target_type', row['target_type'], '?',
                'target_type=Railway but railway not confirmed as attack target'))
    return issues

def rule_target_media_unverified(row):
    issues = []
    if 'Media/journalist' in row.get('target_type',''):
        text = row.get('original_description','')
        if not re.search(
            r'journalist\s+(?:killed|attacked|targeted|shot|abducted)',
            text, re.IGNORECASE):
            issues.append(('target_type', row['target_type'], '?',
                'target_type=Media/journalist but journalist not confirmed as attack target'))
    return issues

def rule_sf_killed_undercounted(row):
    issues = []
    if row['incident_type'] in ['Aggregate report']: return []
    curr = int(row['sf_killed']) if str(row['sf_killed']).isdigit() else 0
    text = row.get('original_description','')
    detected = extract_number(SF_KILLED_PATTERNS, text)
    if detected > curr:
        issues.append(('sf_killed', str(curr), f'≥{detected} (from text)',
            f'Text suggests {detected}+ SF killed but field shows {curr}'))
    return issues

def rule_sf_injured_undercounted(row):
    issues = []
    if row['incident_type'] in ['Aggregate report']: return []
    curr = int(row['sf_injured']) if str(row['sf_injured']).isdigit() else 0
    text = row.get('original_description','')
    detected = extract_number(SF_INJURED_PATTERNS, text)
    if detected > curr:
        issues.append(('sf_injured', str(curr), f'≥{detected} (from text)',
            f'Text suggests {detected}+ SF injured but field shows {curr}'))
    return issues

def rule_civilian_killed_undercounted(row):
    issues = []
    if row['incident_type'] in ['Aggregate report','Enforced disappearance']: return []
    curr = int(row['civilian_killed']) if str(row['civilian_killed']).isdigit() else 0
    text = row.get('original_description','')
    detected = extract_number(CIV_KILLED_PATTERNS, text)
    if detected > curr:
        issues.append(('civilian_killed', str(curr), f'≥{detected} (from text)',
            f'Text suggests {detected}+ civilian killed but field shows {curr}'))
    return issues

def rule_named_victims_missing(row):
    # Suppressed: named_victims is a manual enrichment field, not auto-extracted.
    # Flagging it creates noise (42 flags/month). Enable for manual review passes.
    return []

def rule_ed_missing_names(row):
    issues = []
    if row.get('is_enforced_disappearance') == 'Yes':
        if row.get('disappeared_names','') in ['-','No','']:
            text = row.get('original_description','')
            if has_name_in_text(text):
                issues.append(('disappeared_names', row.get('disappeared_names',''),
                    '? (name in text)', 'ED entry has names in text but disappeared_names empty'))
    return issues

def rule_ed_missing_count(row):
    issues = []
    if row.get('is_enforced_disappearance') == 'Yes':
        curr = str(row.get('num_disappeared','-'))
        if curr in ['-','0','']:
            text = row.get('original_description','')
            if re.search(
                r'(\d+|one|two|three|four|five|six)\s+(?:Baloch\s+)?(?:men|women|persons?|youth|individuals?|brothers?|sons?|civilians?)',
                text, re.IGNORECASE):
                issues.append(('num_disappeared', curr, '?',
                    'ED entry but num_disappeared not filled; count mentioned in text'))
    return issues

def rule_sf_as_perpetrator_on_attack(row):
    issues = []
    attack_types = {'Armed assault','IED','Sniper','Targeted killing',
                   'Roadblock','Area seizure','Arson','Suicide bombing'}
    if row.get('perpetrator_group','') == 'Security Forces' and row['incident_type'] in attack_types:
        if row['incident_type'] not in ['Extrajudicial killing']:
            text = row.get('original_description','')
            if not re.search(
                r'security\s+forces?\s+(?:opened\s+fire\s+on|attacked|targeted|shot|fired\s+on)',
                text, re.IGNORECASE):
                issues.append(('perpetrator_group', 'Security Forces', '?',
                    'SF as perpetrator on attack entry; verify SF are not the victim here'))
    return issues

def rule_claimed_yes_zero_casualties(row):
    issues = []
    curr_k = int(row['sf_killed']) if str(row['sf_killed']).isdigit() else 0
    skip_types = {'Arson','Roadblock','Area seizure','IBO','Aggregate report',
                  'Surrender','Protest/sit-in','Enforced disappearance','Sniper'}
    if (row.get('claimed_responsibility') == 'Yes' 
        and curr_k == 0 
        and row['incident_type'] not in skip_types):
        text = row.get('original_description','')
        if re.search(r'killed|casualties|human\s+(?:and\s+material\s+)?loss', text, re.IGNORECASE):
            if not re.search(r'exact\s+number.*?not\s+known|no\s+casualties\s+(?:were\s+)?reported',
                           text, re.IGNORECASE):
                issues.append(('sf_killed', '0', '?',
                    'claimed=Yes + casualties mentioned in text but sf_killed=0'))
    return issues

def rule_group_claim_without_conflicting(row):
    """If group claims more than 1.5x official sf_killed, conflicting_claims should be Yes."""
    issues = []
    try:
        sf_k = int(row['sf_killed'])
        grp = int(row['group_claimed_sf_killed']) if str(row.get('group_claimed_sf_killed','-')).isdigit() else 0
        if grp > 0 and sf_k > 0 and grp > sf_k * 1.5:
            if row.get('conflicting_claims','') != 'Yes':
                issues.append(('conflicting_claims', row.get('conflicting_claims','No'), 'Yes',
                    f'Group claims {grp} SF killed vs official {sf_k}; conflicting_claims should be Yes'))
        elif grp > 0 and sf_k == 0:
            if row.get('conflicting_claims','') != 'Yes':
                issues.append(('conflicting_claims', row.get('conflicting_claims','No'), 'Yes',
                    f'Group claims {grp} SF killed but official count is 0'))
    except: pass
    return issues


def rule_death_squad_flag_vs_casualties(row):
    """If death_squad_targeted=Yes but death_squad_killed=0 and text says killed."""
    issues = []
    if row.get('death_squad_targeted') == 'Yes':
        ds_k = int(row.get('death_squad_killed','0')) if str(row.get('death_squad_killed','0')).isdigit() else 0
        if ds_k == 0:
            text = row.get('original_description','')
            if re.search(r'(?:killed|shot\s+dead|executed)', text, re.IGNORECASE):
                issues.append(('death_squad_killed', '0', '≥1',
                    'death_squad_targeted=Yes and text mentions killing but death_squad_killed=0'))
    return issues


def rule_informant_flag_vs_casualties(row):
    """If alleged_informant_killed=Yes but informant_killed=0."""
    issues = []
    if row.get('alleged_informant_killed') == 'Yes':
        inf_k = int(row.get('informant_killed','0')) if str(row.get('informant_killed','0')).isdigit() else 0
        if inf_k == 0:
            issues.append(('informant_killed', '0', '≥1',
                'alleged_informant_killed=Yes but informant_killed=0'))
    return issues


def rule_sf_counter_op_consistency(row):
    """sf_counter_op=Yes must have sf_counter_op_type filled, and vice versa."""
    issues = []
    is_cop = row.get('sf_counter_op', '-')
    cop_type = row.get('sf_counter_op_type', '-')
    if is_cop == 'Yes' and cop_type in ('-', '', 'No'):
        issues.append(('sf_counter_op_type', cop_type, '?',
            'sf_counter_op=Yes but sf_counter_op_type is empty'))
    if cop_type not in ('-', '', 'No') and is_cop != 'Yes':
        issues.append(('sf_counter_op', is_cop, 'Yes',
            f'sf_counter_op_type={cop_type} but sf_counter_op is not Yes'))
    return issues

# ── RULES REGISTRY ────────────────────────────────────────────────────────────
# ADD NEW RULES TO THIS LIST. Order determines execution order.
RULES = [
    rule_ied_type_no_ied_in_text,
    rule_attack_method_ied_no_ied_in_text,
    rule_drone_is_helicopter_response,
    rule_non_attack_has_method,
    rule_target_political_figure_unverified,
    rule_target_railway_unverified,
    rule_target_media_unverified,
    rule_sf_killed_undercounted,
    rule_sf_injured_undercounted,
    rule_civilian_killed_undercounted,
    rule_named_victims_missing,
    rule_ed_missing_names,
    rule_ed_missing_count,
    rule_sf_as_perpetrator_on_attack,
    rule_claimed_yes_zero_casualties,
    rule_group_claim_without_conflicting,
    rule_death_squad_flag_vs_casualties,
    rule_informant_flag_vs_casualties,
    rule_sf_counter_op_consistency,
]

# ── MAIN ─────────────────────────────────────────────────────────────────────
def run_audit(input_path, fix=False):
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for r in reader:
            rows.append(dict(r))

    all_issues = []
    for row in rows:
        for rule_fn in RULES:
            try:
                issues = rule_fn(row)
                for field, curr, hint, reason in issues:
                    all_issues.append({
                        'row': row.get('incident_id','?')[-3:],
                        'date': row.get('date',''),
                        'type': row.get('incident_type',''),
                        'field': field,
                        'current': curr,
                        'hint': hint,
                        'reason': reason,
                        'row_obj': row,
                    })
            except Exception as e:
                pass

    from collections import Counter
    field_counts = Counter(i['field'] for i in all_issues)

    print(f"\n{'='*80}")
    print(f"AUDIT RESULTS: {input_path.split('/')[-1]}")
    print(f"{'='*80}")
    print(f"Rows: {len(rows)} | Rules: {len(RULES)} | Flags: {len(all_issues)}")

    if not all_issues:
        print("\n✓ No issues found.")
        return

    print(f"\nFlags by field:")
    for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
        print(f"  {field:<40} {count}")

    print(f"\n{'Row':<5} {'Date':<12} {'Type':<22} {'Field':<32} {'Current':<22} {'Hint':<22} Reason")
    print("-"*170)
    for issue in all_issues:
        print(f"{issue['row']:<5} {issue['date']:<12} {issue['type']:<22} "
              f"{issue['field']:<32} {str(issue['current'])[:21]:<22} "
              f"{str(issue['hint'])[:21]:<22} {issue['reason']}")

    if fix:
        # Auto-fix only high-confidence single-value fixes (non-attack method clear)
        fixed = 0
        for issue in all_issues:
            if issue['field'] == 'attack_method' and issue['hint'] == '-':
                issue['row_obj']['attack_method'] = '-'
                fixed += 1
        
        output_path = input_path.rsplit('.', 1)[0] + '_audited.csv'
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n✓ Auto-fixed {fixed} issues → {output_path}")

    return all_issues

if __name__ == '__main__':
    fix_mode = '--fix' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print("Usage: python3 audit.py input.csv [--fix]")
        sys.exit(1)
    run_audit(args[0], fix=fix_mode)


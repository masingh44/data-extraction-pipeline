"""
extractor.py — PDF to structured CSV extractor for SATP Balochistan incident timelines.

IMPROVEMENTS OVER v1:
  1. Hard IED gate — incident_type can never be IED without explicit explosive language
  2. Sentence-level extraction — main action extracted from first/primary sentence only
  3. Reliable word-number casualty mapping — all word forms covered
  4. Entry split detection — flags potentially merged entries before classifying
  5. named_victims left as 'No' by default (filled in verification step)
  6. Negative perpetrator rules — SF never assigned as perpetrator on attack entries
  7. target_type from primary sentence only, not full text scan

Usage:
  python3 extractor.py FEB_25.pdf BAL_FEB2025_Full.csv
  python3 extractor.py MAR_25.pdf BAL_MAR2025_Full.csv --month March --year 2025
"""

import re, csv, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import COLUMNS, DISTRICTS, DISTRICT_ALIASES, AREA_TO_DISTRICT

# ══════════════════════════════════════════════════════════════════════════════
# PDF PARSER
# ══════════════════════════════════════════════════════════════════════════════

NOISE_PATTERNS = [
    r'SATP https?://\S+',
    r'\d+\s+von\s+\d+\s+\d{2}\.\d{2}\.\d{4},?\s*\d+:\d+',
    r'Balochistan:\s*Timeline.*?Collapse All\.\.\.',
    r'•\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
    r'Date\s+Incidents',
    r'\*Data\s+till.*',
    r'Source:\s*Compiled.*',
]

def clean_text(text):
    for p in NOISE_PATTERNS:
        text = re.sub(p, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

INDIVIDUAL_NOISE = [
    r'SATP https?://\S+',
    r'\d+\s+von\s+\d+\s+\d{2}\.\d{2}\.\d{4},?\s*\d+:\d+',
    r'Balochistan:\s*Timeline\s*\(Terrorist\s*Activities\)-\d+',
    r'•\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
    r'Date\s+Incidents\s+Collapse\s+All\.\.\.',
    r'Collapse\s+All\.\.\.',
]

def _clean_entry(text):
    for p in INDIVIDUAL_NOISE:
        text = re.sub(p, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def parse_pdf(pdf_path, month_name):
    """
    Header-count based parser — 110/110 accuracy.

    Algorithm:
      1. Count all "Month - N" headers  → ground truth entry count per day
      2. For each header find surrounding Read less... boundaries
      3. Special case: first entry (no RL before it) uses start-of-file
      4. Returns entries + expected_by_day dict for validation
    """
    try:
        import pdfplumber
    except ImportError:
        import subprocess
        subprocess.run(['pip', 'install', 'pdfplumber', '--break-system-packages', '-q'])
        import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ''.join(page.extract_text() + '\n' for page in pdf.pages)

    HDRX = re.compile(rf'{month_name}\s*-\s*(\d+)\s*\n?', re.IGNORECASE)
    RLX  = re.compile(r'Read\s+less\.\.\.', re.IGNORECASE)

    hdrs = [(m.start(), m.end(), int(m.group(1))) for m in HDRX.finditer(full_text)]
    rls  = [(m.start(), m.end()) for m in RLX.finditer(full_text)]

    from collections import Counter
    expected_by_day = Counter(h[2] for h in hdrs)

    entries = []
    for h_start, h_end, day in hdrs:
        rl_before = next((rl for rl in reversed(rls) if rl[1] < h_start), None)
        rl_after  = next((rl for rl in rls if rl[0] > h_start), None)

        # First entry has no rl_before — use start of file
        entry_start = rl_before[1] if rl_before else 0
        entry_end   = rl_after[0]  if rl_after  else len(full_text)

        segment = full_text[entry_start:entry_end]
        text    = _clean_entry(HDRX.sub(' ', segment, count=1))

        if len(text) < 80:
            continue

        entries.append({'day': day, 'text': text, 'is_merged': False})

    # ── Post-parse deduplication ─────────────────────────────────────────
    # Issue 3: Detect text-bleed between adjacent entries.
    # Strategy: Jaccard overlap check + exact prefix match. Flag but don't
    # auto-split on "Read less..." as it causes false splits.
    deduped = []
    for i, e in enumerate(entries):
        is_dupe = False
        for j in range(max(0, i-3), i):
            prev_text = entries[j]['text']
            # Jaccard token overlap > 70% on first 200 chars = likely duplicate
            tokens_a = set(e['text'][:200].split())
            tokens_b = set(prev_text[:200].split())
            if tokens_a and tokens_b:
                overlap = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
                if overlap > 0.7:
                    is_dupe = True
                    break
            # Exact prefix match
            if e['text'][:100] == prev_text[:100]:
                is_dupe = True
                break
        
        if not is_dupe and len(e['text']) > 80:
            deduped.append(e)
    
    if len(deduped) < len(entries):
        removed = len(entries) - len(deduped)
        print(f"  ⚠ Removed {removed} duplicate(s) from parser output")
    entries = deduped

    return entries, expected_by_day


# ══════════════════════════════════════════════════════════════════════════════
# TEXT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def has(text, *patterns):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)

def primary_sentence(text):
    """Return first 1-2 sentences — the main action of the entry."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    if not sentences:
        return text
    # Take first 2 sentences max — enough for type/target/perpetrator
    return ' '.join(sentences[:2])

WORD_NUMS = {
    'one':1, 'two':2, 'three':3, 'four':4, 'five':5,
    'six':6, 'seven':7, 'eight':8, 'nine':9, 'ten':10,
    'eleven':11, 'twelve':12, 'thirteen':13, 'fourteen':14,
    'fifteen':15, 'sixteen':16, 'seventeen':17, 'eighteen':18,
    'nineteen':19, 'twenty':20,
}

def to_num(text):
    """Convert digit or word number to int. Returns 0 if not found."""
    # Try digit first
    m = re.search(r'\b(\d+)\b', text)
    if m:
        return int(m.group(1))
    # Try word number
    t = text.lower()
    for w, n in sorted(WORD_NUMS.items(), key=lambda x: -len(x[0])):
        if re.search(rf'\b{w}\b', t):
            return n
    return 0

def extract_num(pattern, text):
    """Search text for pattern, return number from match (digit or word)."""
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return 0
    return to_num(m.group(0))

# ══════════════════════════════════════════════════════════════════════════════
# HARD GATE: IED LANGUAGE CHECK
# ══════════════════════════════════════════════════════════════════════════════

IED_LANGUAGE = [
    r'\bIED\b', r'improvised\s+explosive\s+device',
    r'roadside\s+explosion', r'remote.controlled\s+(?:bomb|device|IED)',
    r'car\s+rigged\s+with\s+explosives', r'motorcycle\s+planted\s+with',
    r'bomb\s+(?:struck|detonated|exploded|planted|blast)',
    r'blast\s+(?:caused|occurred|when|from)',
    r'explosion\s+(?:occurred|took\s+place|hit)',
    r'explosive\s+device', r'planted.*\s+IED',
]

def has_ied_language(text):
    """Hard gate: returns True only if text explicitly describes an explosive device."""
    return any(re.search(p, text, re.IGNORECASE) for p in IED_LANGUAGE)

# ══════════════════════════════════════════════════════════════════════════════
# INCIDENT TYPE CLASSIFIER  (fix: hard IED gate, sentence-level)
# ══════════════════════════════════════════════════════════════════════════════

def classify_type(text, primary):
    """
    Classify incident type.
    
    PRIORITY ORDER (critical — feedback issue #1):
      0. Meta-entry / statement classifier (FIRST — before any attack classification)
      1. Aggregate reports, group-joining
      2. Fidayee/suicide
      3. Enforced disappearance
      4. Protest, Surrender, IBO
      5. Extrajudicial killing
      6. IED (hard gate)
      7. Attack types
    """
    # ── PASS 0: Meta-entry classifier (MUST run first) ────────────────────
    # SATP entries that are announcements/statements/briefings/policy — NOT incidents.
    # STRICT: Only trigger when the PRIMARY sentence is purely about a statement,
    # NOT when it reports an attack with attribution ("According to ISPR, X were killed").
    
    _meta_triggers = (
        # Organization released a statement/report (not confirming casualties)
        r'released\s+(?:its|their|the)\s+(?:annual|monthly|quarterly|bi.?annual)\s+report',
        # Paank / human rights reports with aggregate statistics
        r'(?:Paank|BNM|BHRO|human\s+rights)\s+[\w\s]*?reported\s+(?:that\s+)?\d+\s+(?:extra.?judicial|enforced|killings|disappearances)',
        # Press release / directive
        r'press\s+(?:release|conference)\s+(?:held|issued)',
        r'on\s+the\s+floor\s+of\s+(?:the\s+)?(?:National\s+Assembly|Senate|Parliament)',
        r'directive\s+(?:issued|released)',
        # Statistical summaries (with high specificity)
        r'collective(?:ly)?\s+carried\s+out\s+\d+\s+attacks',
        r'annual\s+report.*?titled',
        # Policy/compensation
        r'(?:Government|Provincial)\s+has\s+provided\s+(?:financial|compensation)',
        r'documents?\s+from\s+the\s+Provincial',
        # Armed camp relocation (not an attack)
        r'(?:armed\s+camp|headquarters|base)\s+[\w\s]*?(?:has\s+been\s+)?relocated',
    )
    
    if has(primary, *_meta_triggers):
        # Double-check: is there an actual attack/violence described?
        if not has(primary, r'killed|shot\s+dead|ambushed|opened\s+fire|bomb\s+(?:attack|blast)|IED|explosion|injured|attacked|targeted'):
            return 'Aggregate report'

    # ── High-confidence matches (order matters) ──────────────────────────────

    # Aggregate/summary report — statistical content
    if has(primary, r'annual\s+report|monthly\s+report|paank.*reported.*(?:killings|disappearances)',
                    r'collective.*carried\s+out\s+\d+|total.*\d+\s+attacks',
                    r'over\s+\d+\s+(?:attacks|deaths|killings)\s+in\s+(?:balochistan|\d{4})',
                    r'stated\s+in\s+its\s+annual\s+report'):
        return 'Aggregate report'

    if has(primary, r'announced.*joined|pledging\s+allegiance|joining.*ranks|joined.*ranks',
                    r'announced\s+that.*has\s+joined'):
        return 'Aggregate report'

    # Fidayee/suicide — always from Majeed Brigade
    if has(text, r'fidayee|person.borne\s+ied|suicide\s+attack'):
        return 'Suicide bombing'

    # Enforced disappearance — check BEFORE body recovery
    # GUARD: If primary sentence describes a violent act (shot dead, killed, opened fire)
    # or a protest, "enforced disappear" is likely an accusation/demand, not the event itself.
    _ed_is_incidental = has(primary,
        r'shot\s+dead|shot\s+and\s+killed|killed\s+(?:one|two|three|him|her|a\s+)',
        r'opened\s+fire\s+on|gunned\s+down|executed',
        r'accusing\s+him\s+of|accusing\s+them\s+of|allegation\s+of',
        r'protest|sit.in|demonstration|took\s+to\s+the\s+streets|demanding\s+an\s+end')
    if not _ed_is_incidental and has(primary,
                    r'enforced.disappear|forcibly\s+disappear|enforced\s+disappearance',
                    r"'enforced\s+disappeared'"):
        # BUT if body was found → EJK
        if has(text, r'body\s+(?:was\s+)?(?:found|recovered|discovered)|found\s+dead|dead\s+body'):
            return 'Extrajudicial killing'
        # BUT if they survived an assassination attempt → Armed assault
        if has(text, r'survived\s+an\s+assassination|survived\s+the\s+attack|no\s+casualties'):
            return 'Armed assault'
        return 'Enforced disappearance'

    # Protest
    if has(primary, r'protest|sit.in|demonstration|took\s+to\s+the\s+streets',
                    r'rallied|marched|held\s+a\s+(?:sit|protest)'):
        return 'Protest/sit-in'

    # Surrender
    if has(primary, r'\bsurrender\b|shun\s+the\s+path\s+of\s+violence|renounced\s+violence',
                    r'announced\s+to\s+(?:shun|abandon|quit)'):
        return 'Surrender'

    # IBO — SF-initiated intelligence operation
    if has(primary, r'intelligence.based\s+operation|\bibo\b|stealthily\s+surrounded',
                    r'thwarted.*infiltr|neutrali[sz]ed.*terrorist.*operation',
                    r'foiled.*attempt.*by\s+recovering|recovered.*cache.*weapons'):
        # Only IBO if SF is the actor, not if a militant group claimed it
        if not has(primary, r'bla\s+claimed|blf\s+claimed|brg\s+claimed|uba\s+claimed'):
            return 'IBO'

    # Aggregate/summary report (group-joining already handled above)
    if has(primary, r'documents\s+from\s+the\s+Provincial|Government\s+has\s+provided\s+financial'):
        return 'Aggregate report'

    # Train attack
    if has(primary, r'jaffar\s+express|train.*hijack|hijacked.*train|passenger\s+train.*attack'):
        return 'Train attack'

    # Extrajudicial killing — body found after disappearance
    if has(primary, r'dead\s+body.*found|body.*found.*(?:dead|bullet)|bullet.riddled.*body',
                    r'body.*recovered.*(?:torture|dump)|found.*dead.*previously\s+disappear'):
        return 'Extrajudicial killing'

    # Sniper — ONLY if primary sentence says sniper and no other attack follows
    if has(primary, r'sniper\s+rifle|sniper\s+fire|sniper\s+tactical\s+team|sniper\s+shot'):
        if not has(primary, r'also\s+launched|then\s+launched|followed\s+by|grenade\s+attack\s+on',
                            r'ied\s+attack|bomb\s+attack'):
            return 'Sniper'

    # ── IED — HARD GATE (Fix 1) ───────────────────────────────────────────────
    if has_ied_language(text):
        # Arson check — if primary action is fire-setting with no IED in primary sentence
        if has(primary, r'set\s+(?:fire|ablaze)|torching|set.*on\s+fire') and not has_ied_language(primary):
            return 'Arson'
        return 'IED'

    # ── Without IED language ──────────────────────────────────────────────────

    # Armed robbery — weapon/property confiscation without combat
    if has(primary, r'confiscated\s+(?:by|from)|rifle.*confiscated|weapon.*confiscated',
                    r'confiscated\s+(?:a\s+)?(?:rifle|weapon|arm)'):
        if not has(primary, r'attacked|killed|opened\s+fire|ambushed|shot'):
            return 'Armed robbery'

    # Enforced disappearance from detention — "detained" with no release
    if has(primary, r'allegedly\s+detained|detained\s+(?:by|four|three|two|five)',
                    r'taken\s+into\s+custody.*undisclosed'):
        if not has(text, r'released|freed|let\s+go'):
            return 'Enforced disappearance'

    # Arson — fire without IED
    if has(primary, r'set\s+(?:fire|ablaze)|set.*on\s+fire|torching|burned.*machinery|arson',
                    r'completely\s+destroyed.*fire|fire.*completely\s+destroyed'):
        return 'Arson'

    # Roadblock — highway interception
    # BUT if there were SF casualties or a major attack, it's Armed assault
    if has(primary, r'blocked.*highway|set\s+up.*roadblock|intercepted.*(?:bus|vehicle|convoy).*highway',
                    r'road\s+block|snapcheck|snap\s+check'):
        if has(text, r'(?:soldiers?|personnel|troops?)\s+(?:were\s+|was\s+)?killed',
                     r'killed\s+(?:\d+|one|two|three|four|five|six|seven)\s+(?:soldiers?|personnel)',
                     r'rocket\s+attack|launched.*(?:rocket|RPG|grenade\s+launcher)'):
            return 'Armed assault'
        return 'Roadblock'

    # Targeted killing — named individual shot dead
    if has(primary, r'shot\s+dead|targeted\s+(?:killing|attack|shooting)',
                    r'(?:killed|shot).*identified\s+as',
                    r'identified\s+as.*(?:killed|shot\s+dead)'):
        return 'Targeted killing'

    # Armed assault — catch-all for attacks with weapons
    if has(primary, r'attacked|ambushed|opened\s+fire|targeted.*(?:camp|post|checkpoint|convoy|vehicle)',
                    r'assault|launched.*attack|carried\s+out.*attack|fired.*(?:rockets?|grenades?)',
                    r'struck.*with|used.*weapons'):
        return 'Armed assault'

    # Extrajudicial killing fallback
    if has(text, r'extrajudicial\s+killing|killed.*in\s+(?:custody|detention)'):
        return 'Extrajudicial killing'

    # Default — Armed assault rather than IED when ambiguous
    return 'Armed assault'

# ══════════════════════════════════════════════════════════════════════════════
# ATTACK METHOD  (from full text, after type is known)
# ══════════════════════════════════════════════════════════════════════════════

NON_ATTACK_TYPES = {
    'Enforced disappearance', 'Aggregate report', 'Surrender',
    'IBO', 'Protest/sit-in', 'Prisoner release', 'Armed robbery',
}

def classify_method(itype, text):
    if itype in NON_ATTACK_TYPES:
        return '-'

    methods = []

    # Specific IED types — most specific first
    if has(text, r'person.borne\s+ied|suicide\s+bomb|fidayee.*attack\s+on'):
        methods.append('Person-borne IED')
    if has(text, r'\bvbied\b|vehicle.borne\s+ied|car\s+rigged\s+with|alto\s+car\s+rigged'):
        methods.append('VBIED')
    if has(text, r'motorcycle.*planted.*ied|motorcycle.*ied|motorcycle.*explosive'):
        methods.append('Motorcycle IED')
    if has(text, r'remote.controlled\s+(?:ied|bomb|device)'):
        methods.append('Remote-controlled IED')
    # Generic IED only if no specific type already found
    if has_ied_language(text) and not methods:
        methods.append('IED')

    # Sniper
    if has(text, r'sniper\s+rifle|sniper\s+fire|sniper\s+tactical\s+team'):
        methods.append('Sniper')

    # Rocket/grenade variants — specific first
    if has(text, r'grenade\s+launcher\s+rounds?|used\s+grenade\s+launchers?|launched\s+grenade\s+launcher'):
        methods.append('Grenade launcher')
    elif has(text, r'\bhurled\s+a\s+(?:hand\s+)?grenade\b|\bhand\s+grenade\b|\bgrenade\s+attack\b',
                  r'threw.*grenade|grenade.*threw') and not has(text, r'grenade\s+launcher'):
        methods.append('Grenade')

    if has(text, r'a-1\s+(?:shell|grenade)|rocket\s+launcher|fired.*rockets?|multiple\s+rockets?',
                r'rockets?\s+at\s+(?:a\s+)?(?:camp|post|convoy|checkpost)'):
        methods.append('Rocket')
    elif has(text, r'\brpg\b'):
        methods.append('RPG')

    if has(text, r'mortar'):
        methods.append('Mortar')
    if has(text, r'unguided\s+bombs?'):
        methods.append('Rocket/Mortar')

    # Heavy weapons — only if no specific weapon named
    if has(text, r'heavy\s+(?:and\s+modern\s+)?weapons?|modern\s+weapons?|advanced\s+weaponry'):
        if not any(m in methods for m in ['Rocket','RPG','Grenade launcher','Mortar']):
            methods.append('Heavy weapons')

    # Arson
    if has(text, r'set\s+(?:fire|ablaze)|arson|torching|set.*on\s+fire') and itype == 'Arson':
        methods.append('Arson')

    # Small arms — any shooting that isn't covered above
    # FIX: Do NOT add small arms if the ONLY attack language is IED-related
    non_ied_attack = has(text, r'opened\s+fire|automatic\s+weapons?|shot\s+dead|gunfire',
                                r'fired\s+on|shooting|rounds?\s+of\s+fire|small\s+arms')
    ied_only = has_ied_language(text) and not non_ied_attack
    if non_ied_attack and not ied_only:
        if 'Small arms' not in methods:
            methods.append('Small arms')

    # Fallbacks
    if not methods:
        if itype == 'Arson':    return 'Arson'
        if itype == 'Sniper':   return 'Sniper'
        if itype == 'IED':      return 'IED'
        if itype == 'Targeted killing': return 'Small arms'
        return 'Small arms'

    return '; '.join(methods)

# ══════════════════════════════════════════════════════════════════════════════
# TARGET TYPE  (from primary sentence only — Fix 4)
# ══════════════════════════════════════════════════════════════════════════════

def get_target_type(primary, full_text):
    """Extract target from primary sentence first; fall back to full text for specifics."""
    targets = []
    t = primary  # classify from primary sentence mainly

    # Convoy types
    if has(t, r'military\s+supply\s+convoy'):
        targets.append('Military supply convoy')
    elif has(t, r'(?:military|SF|security\s+forces?)\s+convoy|convoy\s+of\s+(?:\d+\s+)?(?:vehicles|trucks)'):
        targets.append('Military convoy')
    if has(t, r'military\s+supply\s+(?:vehicle|truck|van)'):
        targets.append('Military supply vehicle')

    # Coast guard
    if has(t, r'coast\s+guard\s+(?:camp|post)'):
        targets.append('Coast Guard post')

    # Levies — check before generic police/military
    if has(t, r'levies\s+(?:checkpost|checkpoint|post|thana|station)'):
        targets.append('Levies checkpoint')
    elif has(t, r'levies\s+personnel\b'):
        targets.append('Levies personnel')

    # Police
    if has(t, r'police\s+(?:checkpoint|check.post)\b'):
        targets.append('Police checkpoint')
    elif has(t, r'police\s+training\s+college|\bptc\b'):
        targets.append('Police facility')
    elif has(t, r'police\s+(?:station|thana)\b'):
        targets.append('Police station')
    elif has(t, r'police\s+personnel\b'):
        targets.append('Police personnel')

    # Military structures — most specific first
    if has(t, r'military\s+(?:checkpost|checkpoint)\b'):
        targets.append('Military checkpoint')
    elif has(t, r'military\s+post\b'):
        targets.append('Military post')
    elif has(t, r'military\s+(?:camp|base|headquarters)\b|army.s\s+main\s+camp|central\s+camp\s+of\s+army'):
        targets.append('Military camp/post')

    # Military patrol — only if explicitly described as patrol
    if has(t, r'(?:army|military|SF)\s+patrol\s+team|patrol.*ambushed|ambushed.*patrol'):
        targets.append('Military patrol')

    # Individual military person
    if has(t, r'(?:soldier|naik|lance\s+naik|officer)\s+(?:was\s+)?(?:targeted|killed|shot)',
              r'targeted\s+(?:a\s+)?(?:soldier|naik)'):
        targets.append('Military personnel')

    # CPEC / FWO / energy
    if has(t, r'fwo|frontier\s+works\s+organization\b'):
        targets.append('FWO')
    elif has(t, r'cpec|china.pakistan\s+economic\s+corridor'):
        targets.append('CPEC infrastructure')
    if has(t, r'ogdcl|oil\s+and\s+gas\s+development'):
        targets.append('Energy/pipeline')

    # Construction
    if has(t, r'construction\s+(?:site|company|project)\b'):
        targets.append('Construction site')
    elif has(t, r'construction\s+(?:truck|vehicle|machinery)\b'):
        targets.append('Construction vehicle')

    # Mining
    if has(t, r'coal\s+mine\s+workers?|mining\s+workers?'):
        targets.append('Mining workers')
    elif has(t, r'transporting.*(?:copper|minerals?|chromite)'):
        targets.append('Mineral transport vehicle')

    # Government buildings
    if has(t, r'dc\s+complex|deputy\s+commissioner.s.*complex'):
        targets.append('Government building')
        if has(t, r'deputy\s+commissioner\s+was\s+inside|targeting.*dc\b'):
            targets.append('Political figure')
    elif has(t, r'nadra\s+office|government\s+(?:building|office)|municipal\s+committee'):
        targets.append('Government building')

    # Bank
    if has(t, r'\bbank\s+branch\b|\blooted.*bank\b'):
        targets.append('Bank')

    # MPA/political figure — only if they are the direct target
    if has(t, r'\bmpa\b.*(?:intercepted|held|targeted|attacked)',
              r'intercepted.*\bmpa\b|targeted.*minister\b'):
        targets.append('Political figure')

    # Death squad / alleged informant — targets, not perpetrators
    if has(t, r'death\s+squad.*member.*(?:killed|shot|targeted)',
              r'(?:killed|shot|targeted).*death\s+squad\s+member'):
        targets.append('Death squad/militia')
    if has(t, r'alleged.*(?:agent|informant|spy).*(?:killed|executed)',
              r'(?:killed|executed).*alleged.*(?:agent|informant)'):
        targets.append('Alleged informant')

    # Civilian targets
    if has(t, r'passenger\s+bus|civilian\s+bus|boarded.*bus'):
        targets.append('Civilian vehicle')
    elif has(t, r'residence\s+of|attacked.*(?:home|house)\b'):
        targets.append('Civilian residence')

    if not targets:
        return 'No'
    return '; '.join(dict.fromkeys(targets))  # deduplicate, preserve order

# ══════════════════════════════════════════════════════════════════════════════
# TARGET ORGANIZATION  (only from confirmed target, not full text)
# ══════════════════════════════════════════════════════════════════════════════

def get_target_org(primary, target_type):
    """Derive target_org from target_type + primary sentence. No full-text fishing."""
    if target_type in ('No', '-', ''):
        return '-'

    t = target_type.lower() + ' ' + primary.lower()
    orgs = []

    if 'fc' in target_type.lower() or 'frontier corps' in t: orgs.append('FC')
    if any(x in target_type.lower() for x in ['military','army','army']): orgs.append('Army')
    if 'police' in target_type.lower(): orgs.append('Police')
    if 'levies' in target_type.lower(): orgs.append('Levies')
    if 'coast guard' in target_type.lower(): orgs.append('Coast Guard')
    if 'ogdcl' in target_type.lower() or 'energy' in target_type.lower(): orgs.append('OGDCL')
    if 'fwo' in target_type.lower(): orgs.append('FWO')
    if 'cpec' in target_type.lower() and not orgs: orgs.append('Army')

    # Resolve FC vs Army from primary sentence
    if 'Army' in orgs and 'FC' not in orgs:
        if has(primary, r'\bFC\b|frontier\s+corps'):
            orgs = ['FC' if x == 'Army' else x for x in orgs]
            if 'FC' not in orgs: orgs.insert(0, 'FC')

    if not orgs:
        return '-'
    return '; '.join(dict.fromkeys(orgs))


def get_target_org_for_ed(text, itype):
    """
    For ED and EJK entries, target_org reflects who the victim was.
    Rule: civilian victims = 'Civilian' (as per Jan 2025 canonical file)
    This is different from combat entries where target_org = the SF branch targeted.
    """
    if itype not in ('Enforced disappearance', 'Extrajudicial killing'):
        return get_target_org(text[:200], itype)
    # Always Civilian for ED/EJK — the victim is a civilian
    return 'Civilian'

# ══════════════════════════════════════════════════════════════════════════════
# PERPETRATOR  (Fix: never assign SF as perpetrator on attack entries)
# ══════════════════════════════════════════════════════════════════════════════

def get_perpetrator(text, primary, itype):
    perps = []

    # Militant groups — from claim statements (LOOSENED per feedback issue #4)
    # Accept: "GROUP claimed/said/stated/announced", "spokesperson of/for GROUP",
    # "GROUP cadres/fighters", and named spokespersons
    if has(text, r'\bBLA\b.*(?:claimed|said|stated|cadres|spokesperson|fighters|launched|attacked)',
                 r'(?:claimed|said|stated).*\bBLA\b',
                 r'Baloch\s+Liberation\s+Army.*(?:claimed|cadres|launched|attacked|fighters)',
                 r'BLA\s+[\'"]?spokesperson[\'"]?',
                 r'Jeeyand\s+Baloch\s+(?:said|claimed|stated)'):
        perps.append('BLA')
    if has(text, r'BLA.Azad|BLA\s+Azad\s+(?:faction|claimed)'):
        perps = ['BLA-Azad' if p == 'BLA' else p for p in perps]
        if 'BLA-Azad' not in perps: perps.append('BLA-Azad')

    if has(text, r'\bBLF\b.*(?:claimed|said|stated|cadres|spokesperson|fighters|launched|attacked)',
                 r'(?:claimed|said|stated).*\bBLF\b',
                 r'Balochistan\s+Liberation\s+Front.*(?:claimed|cadres|launched|attacked|fighters)',
                 r'BLF\s+[\'"]?spokesperson[\'"]?',
                 r'(?:Major\s+)?G[ow]hram\s+Baloch\s+(?:said|claimed|stated)'):
        perps.append('BLF')

    if has(text, r'\bBRG\b.*(?:claimed|said|stated|cadres|spokesperson)',
                 r'Baloch\s+Republican\s+Guard.*(?:claimed|cadres|attacked)',
                 r'Dostain\s+Baloch\s+(?:said|claimed|stated)'):
        perps.append('BRG')
    if has(text, r'\bBRA\b.*claimed|Baloch\s+Republican\s+Army.*claimed'):
        perps.append('BRA')
    if has(text, r'\bUBA\b.*(?:claimed|said|stated)',
                 r'United\s+Baloch\s+Army.*(?:claimed|said|attacked)'):
        perps.append('UBA')
    if has(text, r'\bBRAS\b.*(?:claimed|said|stated)',
                 r'Balochistan\s+Ra[aj]i\s+A[aj]oi.*(?:claimed|said)'):
        perps.append('BRAS')
    if has(text, r'\bTTP\b.*(?:claimed|said|stated|announced|terrorists)',
                 r'Tehreek.e.Taliban.*(?:claimed|said|announced)',
                 r'TTP\s+(?:terrorists|claimed|fighters)'):
        perps.append('TTP')
    if has(text, r'\bISKP\b|\bIS.KP\b|Islamic\s+State.*Khorasan'):
        perps.append('ISKP')

    # Majeed Brigade / Fateh Squad / STOS → BLA sub-units
    if has(text, r'Majeed\s+Brigade|Fateh\s+Squad|STOS.*BLA',
                 r'Special\s+Tactical\s+Operations\s+Squad'):
        if 'BLA' not in perps: perps.append('BLA')

    # Security Forces as PERPETRATOR — for ED/EJK/IBO, never for attack entries
    sf_as_perp_types = {'Enforced disappearance', 'Extrajudicial killing', 'IBO'}
    if itype in sf_as_perp_types:
        # Broad detection: any mention of SF doing the disappearing/operation
        if has(text, r'[Ss]ecurity\s+[Ff]orces?\s*(?:\(SFs?\))?\s*[\'"]?\s*(?:allegedly|reportedly|enforced|forcibly|conducted|carried|detained|abducted|took|raided|foiled|recovered|killed|neutrali)',
                     r'(?:allegedly|reportedly)\s+(?:enforced\s+)?disappeared\s+by\s+[Ss]ecurity\s+[Ff]orces',
                     r'at\s+the\s+hands\s+of\s+[Ss]ecurity\s+[Ff]orces',
                     r'by\s+[Ss]ecurity\s+[Ff]orces?\b',
                     r'SFs?\)?[\'"]?\s+(?:allegedly|reportedly|personnel|enforced|conducted|foiled|recovered)',
                     r'SFs?\)\s+[\'"]?enforced\s+disappeared',
                     r'[Ss]ecurity\s+[Ff]orces\s+allegedly\s+detained',
                     r'[Ff]rontier\s+[Cc]orps\s*\(FC\)\s*personnel\s+(?:at\s+a\s+)?checkpoint.*?detained',
                     r'intelligence\s+(?:agencies|personnel|officers)\s+(?:allegedly|reportedly|took|abducted)',
                     r'taken\s+by\s+(?:intelligence|plainclothes)\s+(?:personnel|officers|agents)'):
            if has(text, r'intelligence\s+agenc|plainclothes'):
                perps.append('Security Forces/intelligence agencies')
            else:
                perps.append('Security Forces')

    # Death squad — when described as perpetrating the attack (shot, killed, fired upon)
    if itype not in sf_as_perp_types:
        if has(text, r'(?:by\s+)?["\']?[Dd]eath\s+[Ss]quads?["\']?\s*(?:\([^)]*\))?\s*members?\s*(?:.*?)(?:shot|killed|attacked|fired|opened\s+fire)',
                     r'shot\s+dead\s+(?:allegedly\s+)?by\s+["\']?death\s+squad',
                     r'state.backed.*militia.*(?:shot|killed|attacked|fired)',
                     r'fired\s+upon\s+by\s+["\']?[Dd]eath\s+[Ss]quads?',
                     r'["\']?[Dd]eath\s+[Ss]quads?["\']?\s*\([^)]*\)\s*members?\s+',
                     r'by\s+["\']?[Dd]eath\s+[Ss]quads?["\']?',
                     r'(?:local|state).*sources\s+alleged.*carried\s+out\s+by.*?["\']?[Dd]eath\s+[Ss]quads?',
                     r'["\']?[Dd]eath\s+[Ss]quads?["\']?.*(?:members?|armed\s+men).*(?:shot|killed|opened\s+fire)'):
            if not perps:
                perps.append('Death squad (state-backed militia)')
        # Also check: "allegedly by death squad" pattern  
        if has(primary, r'allegedly\s+by\s+["\']?death\s+squad',
                        r'reportedly.*fired\s+upon\s+by\s+["\']?[Dd]eath\s+[Ss]quad',
                        r'by\s+["\']?[Dd]eath\s+[Ss]quads?["\']?\s*\('):
            if not perps:
                perps.append('Death squad (state-backed militia)')

    # Death squad as VICTIM (not perpetrator) — when a death squad member was killed
    # In this case perpetrator should remain Unidentified (unless a group claimed it)
    if not perps and has(text, r'death\s+squad.*member.*(?:was\s+)?killed',
                                r'death\s+squad.*member.*shot\s+dead'):
        if not has(text, r'no\s+(?:one|group)\s+claimed'):
            pass  # leave as Unidentified — the death squad member is the victim

    if not perps:
        if itype == 'Protest/sit-in':
            perps.append('-')
        else:
            perps.append('Unidentified')

    return '; '.join(dict.fromkeys(perps))

# ══════════════════════════════════════════════════════════════════════════════
# CASUALTY EXTRACTION  (Fix 2: comprehensive word-number coverage)
# ══════════════════════════════════════════════════════════════════════════════

# Build pattern that matches both digit and word numbers
_NUM = r'(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)'

SF_UNITS = r'(?:soldiers?|Frontier\s+Corps\s*\(FC\)\s*,?\s*personnel|FC\s+personnel|Army\s+personnel|personnel|troops?|policem[ae]n|police\s+personnel|levies\s+personnel|constables?|rangers?|security\s+forces?\s*(?:\(SFs?\)\s*)?personnel)'

CIV_UNITS = r'(?:civilians?|workers?|miners?|labou?rers?|passengers?|persons?|people\s+of\s+Punjabi|coal\s+mine\s+workers?)'

def _is_group_claim_context(text, match_pos):
    """Check if a casualty number at match_pos is inside a group-claim context.
    Returns True if the number comes from BLA/BLF/BRG/TTP/BRAS claim, not official source."""
    # Look at 300 chars before the match for attribution
    prefix = text[max(0, match_pos - 300):match_pos]
    # Group claim patterns
    if re.search(r'(?:BLA|BLF|BRG|TTP|UBA|BRAS|Jeeyand\s+Baloch|Gwahram\s+Baloch|Dostain\s+Baloch)'
                 r'[\w\s,]*?(?:said|claimed|stated|announced|added)',
                 prefix, re.IGNORECASE):
        return True
    if re.search(r'(?:claiming|claimed)\s+that', prefix, re.IGNORECASE):
        return True
    if re.search(r'(?:according\s+to|in\s+a\s+(?:media\s+)?statement)\s*,?\s*(?:BLA|BLF|BRG|TTP)',
                 prefix, re.IGNORECASE):
        return True
    if re.search(r"spokesperson['\"s]?\s+(?:said|claimed|stated)", prefix, re.IGNORECASE):
        return True
    return False


def extract_sf_killed(text):
    """Extract SF killed — ONLY from verified/neutral sources, NOT from group claims.
    Group-claim numbers go to group_claimed_sf_killed instead."""
    patterns = [
        rf'({_NUM})\s+{SF_UNITS}\s+(?:were\s+|was\s+)?killed',
        rf'killing\s+({_NUM})\s+{SF_UNITS}',
        rf'killed\s+({_NUM})\s+(?:Pakistani\s+)?{SF_UNITS}',
        rf'({_NUM})\s+{SF_UNITS}\s+killed\s+on\s+the\s+spot',
        rf'(?:resulting\s+in\s+)?(?:the\s+)?death(?:s)?\s+of\s+({_NUM})\s+(?:Pakistani\s+)?{SF_UNITS}',
        rf'eliminating\s+all\s+({_NUM})\s+personnel',
        rf'death\s+toll.*?increased\s+to\s+({_NUM})',
        rf'({_NUM})\s+(?:were|was)\s+killed\s+(?:on\s+the\s+spot|instantly|in\s+the\s+(?:attack|blast|ambush))',
        rf'(?:at\s+least\s+)?({_NUM})\s+{SF_UNITS}\s+(?:and\s+.{{1,80}}?\s+)?(?:were\s+|was\s+)?killed',
        rf'killed\s+({_NUM})\s+Security\s+Forces?\s*(?:\(SFs?\)\s*)?\s*personnel',
    ]
    best_verified = 0
    best_claimed = 0
    
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            for g in (m.groups() if m.lastindex else []):
                if g:
                    n = to_num(g)
                    if _is_group_claim_context(text, m.start()):
                        if n > best_claimed:
                            best_claimed = n
                    else:
                        if n > best_verified:
                            best_verified = n
    
    return str(best_verified), str(best_claimed) if best_claimed > 0 else '-'

def extract_sf_injured(text):
    patterns = [
        rf'({_NUM})\s+(?:others?|{SF_UNITS})\s+sustained\s+injur',
        rf'({_NUM})\s+(?:others?|{SF_UNITS})\s+suffered\s+injur',
        rf'injuring\s+(?:at\s+least\s+)?({_NUM})',
        rf'({_NUM})\s+(?:others?|{SF_UNITS})\s+(?:were\s+|was\s+)?(?:sustained\s+|suffered\s+)?injur',
        rf'injuries?\s+to\s+(?:at\s+least\s+)?({_NUM})',
        rf'({_NUM})\s+others?\s+wounded',
        # "N other personnel including ..., suffered/sustained injuries"
        rf'({_NUM})\s+other\s+{SF_UNITS}\s+(?:including\s+.{{1,80}}?,?\s+)?(?:sustained|suffered)\s+injur',
        # "was seriously injured" (singular)
        rf'(?:a\s+)?{SF_UNITS}\s+was\s+(?:seriously\s+)?injured',
    ]
    best = 0
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            if m.lastindex:
                for g in m.groups():
                    if g:
                        n = to_num(g)
                        if n > best:
                            best = n
            else:
                # Pattern matched without capture group (singular case)
                if best < 1:
                    best = 1
    return str(best)

def extract_civ_killed(text, itype):
    if itype in {'Aggregate report', 'Enforced disappearance'}:
        return '0'
    patterns = [
        rf'({_NUM})\s+{CIV_UNITS}\s+(?:were\s+)?(?:shot\s+)?(?:killed|dead)',
        rf'killing\s+({_NUM})\s+{CIV_UNITS}',
        rf'({_NUM})\s+{CIV_UNITS}\s+killed\s+on\s+the\s+spot',
        rf'shot\s+(?:him|her|them)\s+dead',
        rf'killing\s+(?:him|her)\s+on\s+the\s+spot',
        rf'(?:found|discovered)\s+(?:shot\s+)?dead',
        # EJK: body found/recovered after disappearance
        rf'(?:dead\s+)?body\s+(?:was\s+)?(?:found|recovered|discovered)',
        rf'bullet.riddled.*body',
    ]
    best = 0
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            groups = [g for g in (m.groups() if m.lastindex else []) if g]
            if groups:
                n = to_num(groups[0])
            else:
                n = 1  # pattern matched without group = single death
            if n > best:
                best = n

    # For targeted killings/EJK/armed assault: named individual "was shot dead/killed"
    if itype in ('Targeted killing', 'Extrajudicial killing', 'Armed assault', 'Roadblock', 'Protest/sit-in') and best == 0:
        if has(text, r'was\s+shot\s+dead|was\s+killed|shot\s+dead\s+by',
                     r'opened\s+fire.*?killing\s+(?:him|her|a\s+man|a\s+woman|one)',
                     r'gunned\s+(?:him|her)\s+down',
                     r'shot\s+dead\s+one\s+(?:man|person|woman)',
                     r'killed\s+a\s+man|killed\s+one\s+(?:man|person)',
                     r'body.*(?:found|recovered|discovered)'):
            best = 1
        # "N people/persons/members shot dead"
        m2 = re.search(rf'({_NUM})\s+(?:members?|brothers?|embroiderers?|men|women|youths?|people|persons?)\s+(?:of\s+\w+\s+ethnicity\s+)?(?:were\s+)?(?:shot\s+dead|killed|dead)', text, re.IGNORECASE)
        if m2:
            n2 = to_num(m2.group(1))
            if n2 > best:
                best = n2
        # "shot dead N people/persons after ..."
        m3 = re.search(rf'shot\s+(?:dead\s+)?({_NUM})\s+(?:passengers?|persons?|people|men)', text, re.IGNORECASE)
        if m3:
            n3 = to_num(m3.group(1))
            if n3 > best:
                best = n3

    # Guard: if incident involves ONLY SF casualties (no civilian context), don't double-count
    if itype in ('Armed assault', 'Sniper', 'IED') and best > 0:
        if has(text, r'soldier|military|Army|FC\b|frontier\s+corps|security\s+forces.*killed'):
            if not has(text, r'civilian|worker|mine|resident|passenger|embroiderer|young\s+(?:man|woman)|body.*found'):
                best = 0

    return str(best)

def extract_civ_injured(text):
    patterns = [
        rf'({_NUM})\s+(?:others?|civilians?)\s+(?:were\s+)?(?:sustained\s+)?injur',
        rf'({_NUM})\s+others?\s+(?:were\s+)?(?:also\s+)?injur',
    ]
    best = 0
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g:
                    n = to_num(g)
                    if n > best: best = n
    return str(best)

def extract_militant_killed(text, itype):
    patterns = [
        rf'({_NUM})\s+(?:terrorists?|militants?|cadres?|khwarij)\s+(?:were\s+)?(?:killed|neutrali[sz]ed|sent\s+to\s+hell)',
        rf'neutrali[sz]ed\s+({_NUM})\s+(?:terrorists?|militants?)',
        rf'({_NUM})\s+(?:terrorists?|militants?)\s+(?:were\s+)?killed\s+in',
    ]
    best = 0
    # Last bullet = fighter killed himself
    if has(text, r'last\s+bullet|took\s+his\s+own\s+life|killed\s+himself'):
        best = 1
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g:
                    n = to_num(g)
                    if n > best: best = n
    return str(best)

def extract_group_claim(text):
    """Extract militant group's own claim of SF killed (often inflated)."""
    patterns = [
        rf'(?:claiming|claimed|claims)\s+(?:that\s+)?({_NUM})\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed',
        rf'(?:claiming|claimed)\s+({_NUM})\s+(?:enemy|Pakistani)\s+(?:soldiers?|personnel|army\s+personnel)\s+(?:were\s+)?killed',
        rf'group\s+said.*?({_NUM})\s+(?:soldiers?|personnel)\s+(?:were\s+)?killed',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g: return str(to_num(g))
    return '-'


def extract_death_squad_casualties(text, itype):
    """Extract death squad/militia member killed and injured counts.
    
    CRITICAL FIX (feedback issue #5):
    Distinguish WHO is doing the killing from WHO is being killed.
    - "death squad member was killed" → ds_k++ (member is the VICTIM)
    - "killed by death squad" → this is civilian_killed, NOT ds_k
    
    Rule: death_squad_killed counts death squad members who DIED.
    The perpetrator in these cases is usually BLA/BLF (targeting collaborators).
    """
    ds_k, ds_i = 0, 0
    if itype in {'Aggregate report', 'Enforced disappearance', 'Surrender', 'Protest/sit-in'}:
        return '0', '0'

    # Death squad member killed (they are the VICTIM, killed BY insurgents)
    # Pattern: "Name, associated with death squad, was killed/shot dead"
    # Pattern: "BLA killed one death squad member"
    # Pattern: "death squad operative/member was shot dead"
    victim_patterns = [
        r'(?:death\s+squad|state.backed\s+militia)\s*(?:\([^)]*\))?\s*(?:member|operative|leader).*?(?:was\s+)?(?:killed|shot\s+dead|executed)',
        r'(?:associated\s+with|linked\s+to|affiliated\s+with)\s+(?:Government|state).backed\s+militia.*?(?:was\s+)?(?:killed|shot)',
        r'(?:BLA|BLF|BRG).*?(?:killed|shot\s+dead|executed).*?(?:death\s+squad|state.backed|collaborator)',
        r'operative\s+of\s+a\s+["\']?death\s+squad["\']?.*?(?:killed|shot)',
        r'(?:killed|shot\s+dead)\s+one\s+["\']?death\s+squad["\']?',
    ]
    
    # Anti-pattern: "killed BY death squad" → victim is a civilian, NOT a death squad member
    killed_by_ds = has(text,
        r'(?:killed|shot\s+dead|fired\s+upon|attacked)\s+(?:by|allegedly\s+by)\s+["\']?death\s+squad',
        r'["\']?death\s+squad["\']?\s*(?:\([^)]*\))?\s*members?\s+(?:shot|killed|opened\s+fire|attacked)',
        r'reportedly\s+(?:being\s+)?fired\s+upon\s+by\s+["\']?[Dd]eath\s+[Ss]quad')
    
    if not killed_by_ds:
        for p in victim_patterns:
            if has(text, p):
                ds_k = max(ds_k, 1)
                m = re.search(rf'({_NUM})\s+(?:death\s+squad|militia)\s+(?:members?\s+)?(?:were\s+)?(?:killed|shot)', text, re.IGNORECASE)
                if m:
                    ds_k = max(ds_k, to_num(m.group(1)))
                break

    # Death squad member injured (same subject-as-victim logic)
    if not killed_by_ds:
        if has(text, r'(?:death\s+squad|militia)\s+(?:member|operative).*injur'):
            ds_i = max(ds_i, 1)

    return str(ds_k), str(ds_i)


def _has_informant_killing(text):
    """
    Proximity-window detection: find accusation anchor, then check
    300 chars in BOTH directions for killing language.
    Avoids false positives from "state agents" or "MI 309" in long texts.
    """
    # Accusation anchor patterns (specific enough to avoid generic "agents")
    anchors = [
        r'(?:alleged|accused).{0,50}(?:agent|informant|spy|informer)',
        r'agent\s+and\s+informer',
        r'ISI\s+(?:agent|informant)',
        r'allegation\s+of\s+being\s+.{0,50}(?:agent|informant|ISI)',
        r'working.{0,30}for\s+(?:Military\s+Intelligence)',
        r'ISI\s+informant',
        r'alleging\s+him\s+as\s+.{0,50}(?:agent|informant|informer)',
    ]
    for ap in anchors:
        for m in re.finditer(ap, text, re.IGNORECASE):
            start = max(0, m.start() - 300)
            end   = min(len(text), m.end() + 300)
            snippet = text[start:end]
            if re.search(r'\b(?:killed|executed|shot\s+dead)\b', snippet, re.IGNORECASE):
                return True
    return False


def extract_informant_casualties(text, itype):
    """Extract alleged informant/agent killed and injured counts."""
    inf_k, inf_i = 0, 0
    if itype in {'Aggregate report', 'Enforced disappearance', 'Surrender', 'Protest/sit-in'}:
        return '0', '0'
    if _has_informant_killing(text):
        inf_k = 1
    return str(inf_k), str(inf_i)


def detect_death_squad_flag(text, itype):
    """Detect if incident involves targeting a death squad/militia member."""
    if itype in {'Aggregate report', 'Enforced disappearance', 'Surrender', 'Protest/sit-in'}:
        return 'No'
    if has(text, r'death\s+squad', r'state.backed\s+militia',
                 r'Government.backed\s+militia', r'armed\s+group\s+of.*?death'):
        return 'Yes'
    return 'No'


def detect_informant_flag(text, itype):
    """Detect if incident involves killing/execution of an alleged informant."""
    if itype in {'Aggregate report', 'Enforced disappearance', 'Surrender', 'Protest/sit-in'}:
        return 'No'
    if _has_informant_killing(text):
        return 'Yes'
    return 'No'


def detect_sf_counter_op(text, itype):
    """Detect and classify SF counter-operation type. Returns (is_counter_op, op_type)."""
    if itype == 'IBO':
        return 'Yes', 'IBO'
    if has(text, r'thwarted\s+infiltration|infiltrat.*thwarted|trying\s+to\s+infiltrate',
                 r'Pakistan.Afghanistan\s+[Bb]order.*(?:killed|engaged|neutrali)'):
        return 'Yes', 'Border interception'
    if has(text, r'clearance\s+operation|sanitization\s+operation|follow.up.*operation',
                 r'sanitization\s+operation'):
        return 'Yes', 'Clearance/sanitization'
    if has(text, r'cordon.*search|house.to.house\s+search'):
        return 'Yes', 'Cordon and search'
    return '-', '-'

# ══════════════════════════════════════════════════════════════════════════════
# HELPER EXTRACTORS
# ══════════════════════════════════════════════════════════════════════════════

def get_district(text, itype=None):
    """
    Extract the single district where the event occurred.
    
    ALGORITHM:
      1. Check aggregate report → 'No' for statistical summaries
      2. Collect ALL location signals with positions (explicit districts, provincial capital, areas)
      3. Filter out victim-origin mentions
      4. Pick earliest event-location signal
      5. Apply Bolan/Kachhi area-specific override
    """
    # Statistical aggregate reports have no specific location
    if itype == 'Aggregate report':
        if has(text, r'annual\s+report|collectively\s+carried\s+out|monthly\s+report',
                     r'total.*\d+\s+attacks|over\s+\d+\s+(?:attacks|deaths)',
                     r'documents\s+from\s+the\s+Provincial|Government\s+has\s+provided\s+financial',
                     r'insurgent\s+groups\s+collectively'):
            return 'No'

    # ── Collect all location signals ──────────────────────────────────────
    candidates = []  # list of (position, district, is_victim_origin)
    
    # Signal 1: Explicit "X District" mentions
    for m in re.finditer(r'(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+District', text):
        name = m.group(1).strip()
        canonical = DISTRICT_ALIASES.get(name, name)
        if canonical in DISTRICTS:
            pos = m.start()
            # Check if victim-origin
            prefix = text[max(0, pos-120):pos]
            is_vo = bool(
                re.search(r'(?:resident|hailed|native)\s+(?:of|from)\s+(?:\w+\s+){0,4}(?:in\s+)?$', prefix, re.IGNORECASE)
                or (re.search(r'from\s+(?:the\s+)?(?:\w+\s+){0,5}$', prefix, re.IGNORECASE) 
                    and re.search(r'(?:resident|hailed|working|employed|student)', prefix, re.IGNORECASE))
                or re.search(r'(?:resident|hailed|native)\s+of\b', prefix, re.IGNORECASE)
            )
            candidates.append((pos, canonical, is_vo))
    
    # Signal 2: "X, the provincial capital" or "provincial capital of Balochistan" → Quetta
    for m in re.finditer(r'(?:of|in|at|from)\s+(\w+),?\s+the\s+provincial\s+capital', text, re.IGNORECASE):
        candidates.append((m.start(), 'Quetta', False))
    m_pc = re.search(r'provincial\s+capital\s+of\s+Balochistan', text, re.IGNORECASE)
    if m_pc:
        candidates.append((m_pc.start(), 'Quetta', False))
    
    # Signal 3: "International Airport in Quetta" or similar
    m_ap = re.search(r'Airport\s+in\s+Quetta|inside.*?(?:Airport|Press\s+Club).*?Quetta', text, re.IGNORECASE)
    if m_ap:
        candidates.append((m_ap.start(), 'Quetta', False))
    
    # ── Pick best candidate ───────────────────────────────────────────────
    # Prefer first non-victim-origin candidate
    event_candidates = [(p, d) for p, d, vo in candidates if not vo]
    if event_candidates:
        event_candidates.sort(key=lambda x: x[0])
        result = event_candidates[0][1]
        
        # Apply Bolan/Kachhi area override: Dahadar/Dhadar = Kachhi even when text says "Bolan District"
        if result == 'Bolan' and has(text, r'\bDahadar\b|\bDhadar\b|\bNational\s+Highway\s*\(NH.65\)'):
            result = 'Kachhi'
        
        return result
    
    # If only victim-origin districts found, try area-to-district lookup
    area_matches = []
    for area, district in AREA_TO_DISTRICT.items():
        m = re.search(rf'\b{re.escape(area)}\b', text)
        if m:
            prefix = text[max(0, m.start()-60):m.start()]
            if not re.search(r'(?:resident|hailed|native)\s+(?:of|from)', prefix, re.IGNORECASE):
                area_matches.append((m.start(), district))
    
    if area_matches:
        area_matches.sort(key=lambda x: x[0])
        return area_matches[0][1]
    
    # Fallback: use victim-origin if that's all we have
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    # Last resort: any district name in text
    for d in DISTRICTS:
        if re.search(rf'\b{re.escape(d)}\b', text, re.IGNORECASE):
            return d

    return 'No'



def normalize_time_of_day(text):
    """Extract time of day from text and map to standard periods."""
    # Check for explicit time mentions first
    m = re.search(r'(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?)', text, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        ampm = m.group(3).lower().replace('.', '')
        if 'pm' in ampm and hour != 12:
            hour += 12
        if 'am' in ampm and hour == 12:
            hour = 0
        if 5 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 21:
            return 'Evening'
        else:
            return 'Night'

    # Check for descriptive time references
    if has(text, r'at\s+(?:dawn|daybreak)|early\s+morning|in\s+the\s+morning'):
        return 'Morning'
    if has(text, r'at\s+noon|in\s+the\s+afternoon|afternoon'):
        return 'Afternoon'
    if has(text, r'at\s+(?:dusk|sunset|evening)|in\s+the\s+evening|evening'):
        return 'Evening'
    if has(text, r'at\s+(?:night|midnight)|in\s+the\s+night|late\s+(?:at\s+)?night|night\s+of',
              r'in\s+the\s+early\s+hours|wee\s+hours|midnight\s+raid|2\s+a\.?m\.?'):
        return 'Night'

    return 'No'

def get_source(text):
    sources = []
    if has(text, r'The\s+Balochistan\s+Post'): sources.append('The Balochistan Post')
    if has(text, r'\bDawn\b'): sources.append('Dawn')
    if has(text, r'Khorasan\s+Diary'): sources.append('The Khorasan Diary')
    if has(text, r'ARY\s+News'): sources.append('ARY News')
    if has(text, r'Geo\s+News'): sources.append('Geo News')
    if has(text, r'Urdu\s+Point'): sources.append('Urdu Point')
    if has(text, r'Express\s+Tribune'): sources.append('Express Tribune')
    if has(text, r'Balochistan\s+Times'): sources.append('Balochistan Times')
    if has(text, r'Zrumbesh'): sources.append('Zrumbesh')
    return '; '.join(sources) if sources else 'No'

def get_spokesperson(text):
    if has(text, r'Jeeyand\s+Baloch'): return 'Jeeyand Baloch'
    if has(text, r'Major\s+G(?:wa?|o)h?ram\s+Baloch|Gwahram\s+Baloch|Gohram\s+Baloch'):
        return 'Major Gwahram Baloch'
    if has(text, r'Dostain\s+Baloch'): return 'Dostain Baloch'
    if has(text, r'Azad\s+Baloch\s+(?:said|stated|spokesperson)'): return 'Azad Baloch'
    return 'No'

def get_data_quality(text, itype, sources):
    if has(text, r'\bISPR\b|Inter.Services\s+Public\s+Relations'): return 'High'
    if itype in {'Enforced disappearance', 'Extrajudicial killing'}: return 'Low'
    if sources.count(';') >= 1: return 'High'
    return 'Medium'

def get_disappearance_info(text, itype):
    """Extract disappearance count, names, identifiers, and circumstances."""
    if itype != 'Enforced disappearance':
        return '-', '-', '-', '-'

    # ── ISSUE 8 FIX: Strip location-prefixes that get mistaken for names ──
    # Remove "Nawabshah district's", "Naseer Abad district's", "from Quetta" etc
    # from the text BEFORE name extraction to avoid capturing district names as person names
    clean_text = re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:[Dd]istrict|[Tt]ehsil|[Tt]own|[Cc]ity)(?:\'s|s)?\s+', '', text)

    # Extract names — multiple pattern strategies
    names = []
    
    # ISSUE 7 FIX: Track full patronymic names to avoid splitting.
    # "Name s/o Parent" is ONE person. Store the first-name part to prevent
    # it being added again by a later pattern.
    seen_first_names = set()
    
    # Pattern 1: "identified as Name [s/o Parent]" — keep full patronymic as one entry
    for m in re.finditer(
        r'identified\s+as\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?(?:,?\s+s/o\s+[A-Z][a-zA-Z\s]+)?)',
        clean_text):
        name = m.group(1).strip().rstrip(',.')
        if len(name) > 3 and name not in names:
            names.append(name)
            # Track first name portion to avoid re-adding
            first = name.split()[0]
            seen_first_names.add(first)

    # Pattern 2: "Name s/o Parent" (direct patronymic) — keep as ONE person
    for m in re.finditer(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+s/o\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z\s]*)?)',
        clean_text):
        first_name = m.group(1).strip().rstrip(',.')
        full_name = f"{first_name} s/o {m.group(2).strip().rstrip(',.')}".strip()
        skip = {'Security', 'The', 'According', 'Deputy', 'Assistant'}
        if first_name.split()[0] in skip:
            continue
        if len(first_name) > 2 and first_name not in seen_first_names:
            # Check if a longer version with this first name already exists
            already = any(first_name in n for n in names)
            if not already:
                names.append(first_name)
                seen_first_names.add(first_name)

    # Pattern 3: "Name (son of Parent)" — parenthetical patronymic
    for m in re.finditer(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+\(son\s+of\s+[A-Z]',
        clean_text):
        name = m.group(1).strip()
        if len(name) > 2 and name not in names and name.split()[0] not in seen_first_names and name not in ('Security', 'The'):
            names.append(name)
            seen_first_names.add(name.split()[0])

    # Pattern 4: "Name and Name, sons of Parent" or "Name, Name, and Name"
    for m in re.finditer(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+and\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?),?\s+sons?\s+of',
        clean_text):
        for g in m.groups():
            name = g.strip().rstrip(',.')
            if len(name) > 2 and name not in names and name.split()[0] not in seen_first_names and name not in ('Security', 'The'):
                names.append(name)
                seen_first_names.add(name.split()[0])

    # Pattern 5: "disappeared' one/a Name" — single-victim ED (with or without quotes)
    for m in re.finditer(
        r"disappeared['\"]?\s+(?:one\s+)?(?:a\s+)?(?:Baloch\s+)?(?:man|woman|youth|teenager|boy|girl|person|officer)?\s*,?\s*(?:identified\s+as\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})",
        clean_text):
        name = m.group(1).strip().rstrip(',.')
        skip = {'Security','Forces','Balochistan','The','According','Family','Local',
                'Baloch','District','Post','Read','However','Later','No','From',
                'During','Their','His','Her','One','Two','Three','Four','Five',
                'Province','Reportedly','Allegedly'}
        parts = name.split()
        if parts and parts[0] not in skip and parts[0] not in seen_first_names and len(name) > 3 and name not in names:
            names.append(name)
            seen_first_names.add(parts[0])

    # Pattern 5b: "disappeared ... Name, son of Parent" (name before 'son of')
    for m in re.finditer(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?),?\s+son\s+of\s+[A-Z]',
        clean_text):
        name = m.group(1).strip().rstrip(',.')
        skip = {'Security','The','According','Deputy','Assistant','Additional','Levies','Police','Army'}
        if name.split()[0] not in skip and name.split()[0] not in seen_first_names and len(name) > 2 and name not in names:
            names.append(name)
            seen_first_names.add(name.split()[0])

    # Pattern 5c: "Name and his/her father/brother, Name" 
    for m in re.finditer(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+and\s+(?:his|her|their)\s+(?:father|mother|brother|sister|relative),?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)',
        clean_text):
        for g in m.groups():
            name = g.strip().rstrip(',.')
            if len(name) > 2 and name not in names and name.split()[0] not in seen_first_names:
                names.append(name)
                seen_first_names.add(name.split()[0])

    # Pattern 6: Comma-separated list after "identified as" — "Sajid, Faisal, Ahmed Raza, ..."
    m_list = re.search(
        r'identified\s+as\s+([A-Z][a-zA-Z]+(?:(?:\s+[A-Z][a-zA-Z]+)*(?:,\s*(?:and\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)+))',
        clean_text)
    if m_list:
        name_str = m_list.group(1)
        parts = re.split(r',\s*(?:and\s+)?', name_str)
        for p in parts:
            p = p.strip().rstrip(',.')
            if len(p) > 2 and p not in names and p.split()[0] not in seen_first_names:
                names.append(p)
                seen_first_names.add(p.split()[0])

    # Count
    count = 'No'
    m2 = re.search(
        rf'({_NUM})\s+(?:Baloch\s+)?(?:men|women|persons?|youth|individuals?|brothers?|civilians?|sons?)\s+(?:were\s+)?(?:enforced|forcibly)',
        text, re.IGNORECASE)
    if m2:
        count = str(to_num(m2.group(1)))
    # Also catch "enforced disappeared' N brothers/persons"
    m3 = re.search(
        rf"disappeared['\"]\s+({_NUM})\s+(?:brothers?|persons?|civilians?|sons?|men|youth)",
        text, re.IGNORECASE)
    if m3 and count == 'No':
        count = str(to_num(m3.group(1)))
    # Also catch "At least N persons were 'enforced disappeared'"
    m4 = re.search(
        rf'(?:at\s+least\s+)?({_NUM})\s+persons?\s+(?:were\s+)?(?:\'|")enforced\s+disappeared',
        text, re.IGNORECASE)
    if m4 and count == 'No':
        count = str(to_num(m4.group(1)))
    if count == 'No' and names:
        count = str(len(names))

    disapp_names = '; '.join(names) if names else 'No'
    disapp_ids = '-'

    # Circumstances — matches user's gold CSV taxonomy
    circumstances = '-'
    if has(text, r'raid.*(?:house|home)|stormed.*home|raided.*house|night.*raid.*home',
                 r'raids?\s+on\s+their\s+(?:house|home)',
                 r'conducted\s+raids?\s+in\s+',
                 r'during\s+(?:a\s+)?(?:raid|operation)\s+in\s+',
                 r'from\s+(?:the\s+)?(?:Killi|killi)\s+\w+\s+area',
                 r'from\s+(?:his|their|her)\s+(?:home|house|residence)'):
        if has(text, r'night|midnight|late.night|early\s+hours|11\s*(?:pm|p\.m)'):
            circumstances = 'Raid on home (nighttime)'
        else:
            circumstances = 'Raid on home'
    elif has(text, r'airport|immigration|customs|border\s+crossing'):
        circumstances = 'At airport/border crossing'
    elif has(text, r'travelling|traveling|en\s+route|returning.*home|on.*way.*(?:to|from)',
                   r'while\s+en\s+route|while\s+(?:he|they)\s+(?:was|were)\s+(?:travel|return)'):
        circumstances = 'While travelling'
    elif has(text, r'checkpoint.*(?:detained|taken|abducted)|(?:detained|taken|abducted).*checkpoint',
                   r'fc.*checkpoint|military.*checkpoint|police.*checkpoint'):
        circumstances = 'At military/police checkpoint'
    elif has(text, r'(?:clinic|hospital|shop|workplace|petrol.*pump|hotel|office|hostel|school)\b.*?(?:disappear|taken|detained|abducted)',
                   r'(?:disappear|taken|detained|abducted).*?(?:clinic|hospital|shop|workplace|petrol.*pump|hotel|hostel)'):
        circumstances = 'From shop/workplace'
    elif has(text, r'plainclothes|plain.*clothes|civilian.*cloth'):
        circumstances = 'Plainclothes agents'
    elif has(text, r'intelligence.*(?:agencies|personnel).*(?:inside|at).*(?:Airport|airport)'):
        circumstances = 'At airport/border crossing'

    return count, disapp_names, disapp_ids, circumstances


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 ENRICHMENT EXTRACTORS
# ══════════════════════════════════════════════════════════════════════════════

def get_town_area(text):
    """Extract sub-district locality / town / area name from text."""
    skip_words = {'The', 'Security', 'Balochistan', 'Baloch', 'Pakistani', 'According',
                  'District', 'Province', 'Forces', 'National', 'China', 'February',
                  'January', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December', 'Read', 'However',
                  'Meanwhile', 'Earlier', 'Following', 'During', 'Despite', 'After',
                  'Frontier', 'Balochistan'}

    patterns = [
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\s+area\s+of\s+(?:[A-Z][a-z]+\s+)?(?:tehsil|District)',
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+town\s*\(',
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+),?\s+the\s+(?:provincial|district)\s+capital',
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+town\s+(?:of|in)\s+[A-Z]',
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s+area\s+of\s+[A-Z]',
        r'(?:in|at|near)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s+(?:Bypass|Cross|Chowk|Bazaar)\s+(?:in|of|area)',
        r'(?:in|at|from)\s+(?:the\s+)?([A-Z][a-zA-Z]+),?\s+a\s+(?:coastal|small|remote)\s+town',
        r'(?:in|at|from)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+tehsil\s+(?:\(revenue\s+unit\)\s+)?(?:in|of)\s+[A-Z]',
        r'(?:in|at|from)\s+(?:the\s+)?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:area|locality|region)\s+of\s+[A-Z]',
        r'on\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:Road|Street)\s+in\s+[A-Z]',
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            name = m.group(1).strip()
            if name.split()[0] not in skip_words and len(name) > 2:
                return name
    return '-'


def get_incident_summary(text):
    """Return first 1-2 sentences as incident summary."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    if not sentences:
        return text[:300]
    summary = ' '.join(sentences[:2])
    if len(summary) > 500:
        summary = summary[:497] + '...'
    return summary


def get_official_source(text):
    """Detect official/government sources cited in text."""
    sources = []
    if has(text, r'\bISPR\b|Inter.Services\s+Public\s+Relations'):
        sources.append('ISPR')
    if has(text, r'Deputy\s+Commissioner\s+[A-Z]|Deputy\s+Commissioner\s+of\s+[A-Z]'):
        sources.append('Deputy Commissioner')
    if has(text, r'Additional\s+Deputy\s+Commissioner|ADC\s+[A-Z]'):
        sources.append('ADC')
    if has(text, r'SSP\s+[A-Z]|Senior\s+Superintendent\s+of\s+Police'):
        sources.append('SSP')
    if has(text, r'DSP\s+[A-Z]|Deputy\s+Superintendent\s+of\s+Police'):
        sources.append('DSP')
    if has(text, r'Inspector\s+General\s+of\s+Police|IGP'):
        sources.append('IGP Office')
    if not sources and has(text,
            r'(?:Police|police)\s+(?:official|officer|spokesman|spokesperson)\s+(?:said|stated|confirmed|added)',
            r'(?:said|stated|confirmed)\s+(?:the\s+)?(?:Police|police)',
            r'unnamed\s+(?:Police|District)\s+official',
            r'Police\s+(?:said|confirmed|stated)\s+(?:the|that)'):
        sources.append('Police official')
    return '; '.join(sources) if sources else '-'


def get_economic_sector(text, target_type):
    """Derive economic sector from text and target_type."""
    tt = (target_type or '').lower()
    if has(text, r'\bogdcl\b|oil\s+and\s+gas|gas\s+exploration|energy\s+company'):
        return 'Energy/oil and gas'
    if 'energy' in tt or 'pipeline' in tt or 'ogdcl' in tt:
        return 'Energy/oil and gas'
    if has(text, r'copper\s+project|saindak|mining|mineral.*transport|transporting.*mineral|chromite|coal\s+mine'):
        return 'Mining/minerals'
    if 'mineral' in tt or 'mining' in tt:
        return 'Mining/minerals'
    if has(text, r'\bbank\s+branch\b|looted.*bank|strong\s+room'):
        return 'Banking'
    if 'bank' in tt:
        return 'Banking'
    if has(text, r'railway|train\s+attack|rail\s+track|jaffar\s+express'):
        return 'Railways/transport'
    if has(text, r'construction\s+(?:site|company|project)|road\s+construction|fwo|frontier\s+works'):
        return 'Construction'
    if 'construction' in tt or 'fwo' in tt:
        return 'Construction'
    if has(text, r'cpec|china.pakistan\s+economic\s+corridor'):
        return 'CPEC infrastructure'
    if has(text, r'telecom|surveillance.*camera|mobile\s+tower'):
        return 'Telecommunications'
    return '-'


def get_victim_profession(text, itype):
    """Extract victim's profession/role from text."""
    if itype in {'Aggregate report', 'Surrender', 'Protest/sit-in', 'IBO'}:
        return '-'
    if has(text, r'journalist|reporter|correspondent|media\s+person'):
        return 'journalist'
    if has(text, r'Levies\s+Force\s+personnel|Levies\s+officer') and itype in ('Targeted killing', 'Extrajudicial killing', 'Enforced disappearance'):
        return 'levies'
    if has(text, r'Policem[ae]n|Police\s+personnel|Police\s+department|Class\s+IV\s+employee.*Police') and itype in ('Targeted killing', 'Extrajudicial killing'):
        return 'police'
    if has(text, r'coal\s+mine\s+workers?|miners?'):
        return 'labourer'
    if has(text, r'embroiderer'):
        return 'labourer'
    if has(text, r'OGDCL.*(?:worker|employee)|(?:worker|employee).*OGDCL|employee.*oil\s+and\s+gas'):
        return 'energy worker'
    if has(text, r'school\s+principal|teacher|educator|professor|M\.Phil\.\s+Scholar') and itype in ('Targeted killing', 'Armed assault'):
        return 'educator'
    if has(text, r'shopkeeper|trader|businessman'):
        return 'trader/businessman'
    if has(text, r'(?:NADRA|govt|government)\s+employee|Assistant\s+Commissioner|Assistant\s+Superintendent') and itype in ('Targeted killing', 'Enforced disappearance', 'IED'):
        return 'govt employee'
    if has(text, r'singer|artist|musician') and itype == 'Enforced disappearance':
        return 'artist/musician'
    if has(text, r'petrol\s+pump.*employee|employee.*petrol\s+pump'):
        return 'petrol pump worker'
    if has(text, r'religious\s+scholar|Maulana\s+[A-Z]|Maulvi\s+[A-Z]') and itype == 'Targeted killing':
        return 'religious scholar'
    if has(text, r'social\s+media\s+activist|blogger|founder.*page') and itype == 'Enforced disappearance':
        return 'activist/blogger'
    if has(text, r'retired\s+Army|Lieutenant\s+Colonel') and itype in ('Targeted killing', 'Armed assault'):
        return 'retired military'
    return '-'


def get_target_org_smart(text, primary, itype, tgt_type, tgt_org_basic):
    """
    Always derive target_organization from context.
    Falls back to existing logic but fills Civilian/Army/Police when obvious.
    """
    # If basic extraction already found something, use it
    if tgt_org_basic not in ('-', '', 'No'):
        return tgt_org_basic

    # ED/EJK victims are civilians
    if itype in ('Enforced disappearance', 'Extrajudicial killing'):
        return 'Civilian'

    # Targeted killing — determine who was killed
    if itype == 'Targeted killing':
        if has(text, r'death\s+squad.*member|operative.*death\s+squad'):
            return 'Death Squad'
        if has(text, r'Policem[ae]n|Police\s+personnel|Police\s+department|Assistant\s+Superintendent.*Prison'):
            return 'Police'
        if has(text, r'Levies\s+(?:Force\s+)?personnel'):
            return 'Levies'
        if has(text, r'soldier|military|Army\s+personnel'):
            return 'Army'
        return 'Civilian'

    # Armed assault — determine target from text
    if itype in ('Armed assault', 'Sniper'):
        if has(primary, r'military\s+(?:camp|post|convoy|checkpoint|supply)|army|Army'):
            return 'Army'
        if has(primary, r'\bFC\b|[Ff]rontier\s+[Cc]orps|[Cc]oast\s+[Gg]uard'):
            return 'FC'
        if has(primary, r'[Ss]ecurity\s+[Ff]orces|SF\s+(?:checkpoint|post|camp|personnel)'):
            return 'Army'
        if has(primary, r'[Pp]olice\s+(?:checkpoint|station|training|personnel)'):
            return 'Police'
        if has(primary, r'[Ll]evies\s+(?:checkpoint|checkpost|personnel|post)'):
            return 'Levies'
        if has(primary, r'residence|house|civilian|school|singer|shop|market|embroiderer|young\s+man|opened\s+fire.*?killing\s+(?:him|her|a\s+man|a\s+woman|one|two)'):
            return 'Civilian'
        # If text mentions SF/military anywhere, it's likely an army target
        if has(text, r'military|army|soldier|SF|security\s+forces|FC\b|frontier\s+corps'):
            return 'Army'
        # If it mentions a person being shot/killed, likely civilian
        if has(text, r'(?:shot\s+dead|killed|opened\s+fire\s+on).*?(?:man|woman|person|youth|resident|body)'):
            return 'Civilian'

    # IED — usually targets SF
    if itype == 'IED':
        if has(text, r'military|army|convoy|SF|security\s+forces'):
            return 'Army'
        if has(text, r'coal\s+mine|civilian|workers?|passengers?'):
            return 'Civilian'

    # Arson — usually targets property/construction
    if itype == 'Arson':
        if has(text, r'NADRA\s+office|government\s+(?:building|office)|municipal'):
            return 'Government'
        if has(text, r'construction|machinery'):
            return 'Civilian'
        if has(text, r'levies\s+(?:checkpost|station|post)'):
            return 'Levies'

    # Roadblock
    if itype == 'Roadblock':
        return 'Civilian'

    # IBO — militants are the target
    if itype == 'IBO':
        return 'Militants'

    # Protest — civilians protesting
    if itype == 'Protest/sit-in':
        return 'Civilian'

    return tgt_org_basic if tgt_org_basic not in ('-', '') else '-'


def get_weapons_seized(text):
    """Extract weapons/equipment seized by attackers."""
    if not has(text, r'seiz|confiscat|took\s+away.*(?:weapon|arm|rifle|equipment)'):
        return '-'
    items = []
    m = re.search(r'(\d+)\s+AK.47s?', text, re.IGNORECASE)
    if m: items.append(m.group(0).strip())
    m = re.search(r'([\d,]+)\s+rounds?\s+(?:of\s+)?ammunition', text, re.IGNORECASE)
    if m: items.append(m.group(0).strip())
    m = re.search(r'(\d+)\s+(?:Levies\s+)?vehicles?', text, re.IGNORECASE)
    if m and has(text, r'seiz.*vehicle|vehicle.*seiz|took.*vehicle'):
        items.append(m.group(0).strip())
    m = re.search(r'(\d+)\s+(?:motor\s*bikes?|motorcycles?)', text, re.IGNORECASE)
    if m and has(text, r'seiz|confiscat|took\s+away'):
        items.append(m.group(0).strip())
    m = re.search(r'(\d+)\s+official\s+weapons?', text, re.IGNORECASE)
    if m: items.append(m.group(0).strip())
    if has(text, r'walkie.talkies?') and has(text, r'seiz|confiscat'):
        items.append('walkie-talkies')
    if not items and has(text, r'seiz(?:ed|ing)\s+(?:all\s+)?(?:weapons|arms)|confiscat(?:ed|ing)\s+(?:all\s+)?(?:weapons|arms)'):
        items.append('Weapons seized')
    if not items and has(text, r'rifle.*confiscated|confiscated.*rifle|weapon.*confiscated'):
        items.append('Weapons seized')
    return '; '.join(items) if items else '-'


def get_weapons_recovered(text):
    """Extract weapons recovered by security forces."""
    if has(text, r'(?:SFs?|security\s+forces?|ISPR)\s+(?:also\s+)?recovered',
                  r'recovered\s+(?:a\s+)?(?:large\s+)?(?:cache|quantity)\s+of\s+(?:weapons|arms|ammunition|explosives)',
                  r'hideout.*recovered.*(?:arms|weapons|ammo)'):
        return 'Yes'
    return '-'


def get_hostages_taken(text):
    """Count hostages taken during incident."""
    if has(text, r'took.*hostage|taken\s+hostage|held\s+hostage|personnel\s+hostage'):
        m = re.search(r'took\s+(?:the\s+)?(\d+)\s+(?:staff|personnel|persons?)\s+hostage', text, re.IGNORECASE)
        if m:
            return m.group(1)
        if has(text, r'took\s+(?:the\s+)?(?:staff|personnel)\s+hostage'):
            return '1'
    return '0'


def get_victim_previous_disappearance(text):
    """Detect if victim was previously disappeared — broad detection."""
    if has(text, r'previously\s+(?:forcibly\s+)?disappear|previously\s+abduct',
                 r'had\s+(?:previously|earlier)\s+been\s+(?:disappear|abduct)',
                 r'forcibly\s+disappeared\s+by\s+Security\s+Forces\s+on\s+[A-Z]',
                 r'was\s+(?:forcibly\s+)?disappeared\s+by\s+Security\s+Forces',
                 r'detained\s+by\s+(?:FC|Frontier\s+Corps).*?found\s+(?:dead|injured)',
                 r'was\s+(?:earlier|previously)\s+(?:forcibly\s+)?disappeared',
                 r'abducted\s+on\s+[A-Z].*?(?:found|released|missing)',
                 r'(?:enforced|forcibly)\s+disappeared.*?(?:body|found\s+dead|recovered)'):
        return 'Yes'
    return 'No'


def get_family_member_previously_targeted(text):
    """Detect if a family member of the victim was previously disappeared/killed/targeted.
    STRICT: Only match when text explicitly references a PRIOR incident against a family member."""
    if has(text, r'brother.*(?:was\s+)?(?:a\s+)?victim\s+of\s+(?:enforced\s+)?disappearance',
                 r'another\s+brother.*(?:was\s+)?(?:similarly\s+)?disappeared',
                 r'brother.*(?:was\s+)?(?:extra.?judicial|killed).*(?:in\s+\w+\s+\d{4}|previously|earlier)',
                 r'brother.*previously\s+disappeared',
                 r'brother.*remains?\s+missing\s+till\s+date',
                 r'brother.*was\s+(?:forcibly\s+)?disappeared\s+(?:three|two|four|five)\s+years?\s+ago',
                 r'(?:his|her)\s+brother.*?(?:was\s+)?(?:a\s+)?victim\s+of\s+enforced',
                 r'(?:his|her)\s+residence\s+was\s+(?:previously\s+)?targeted\s+in\s+a\s+bomb'):
        return 'Yes'
    return 'No'


def build_named_victims(text, itype, disapp_names):
    """
    Build structured named_victims string from text.
    Format: "Name (status); Name2 (role; status)"
    
    For ED entries: uses already-extracted disappeared_names
    For other entries: extracts named individuals and their outcomes
    """
    if itype in {'Aggregate report', 'Surrender', 'Protest/sit-in'}:
        # Check for specific named individuals even in these types
        pass  # fall through to general extraction
    
    victims = []
    
    # ── ED entries: tag each disappeared name ──────────────────────────────
    if itype == 'Enforced disappearance' and disapp_names != 'No':
        names = [n.strip() for n in disapp_names.split(';') if n.strip()]
        for name in names:
            # Strip s/o Parent patronymic for clean display
            clean = re.sub(r'\s+s/o\s+.*$', '', name).strip()
            clean = re.sub(r',\s*$', '', clean).strip()
            # Check if later released
            if clean and has(text, rf'(?:{re.escape(clean)}|{re.escape(name)}).*?released'):
                victims.append(f'{clean} (taken, later released)')
            elif clean:
                victims.append(f'{clean} (disappeared)')
        if victims:
            return '; '.join(victims)
    
    # ── EJK entries: body found ───────────────────────────────────────────
    if itype == 'Extrajudicial killing':
        # Extract name from "identified as Name" or "Name s/o Parent"
        for m in re.finditer(r'identified\s+as\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)', text):
            name = m.group(1).strip()
            if len(name) > 2 and name not in ('Security', 'The', 'According'):
                victims.append(f'{name} (killed)')
        for m in re.finditer(r'([A-Z][a-zA-Z]+),?\s+son\s+of\s+[A-Z]', text):
            name = m.group(1).strip()
            skip = {'Security','The','According','Deputy','Assistant','Additional','Levies','Police','Army'}
            if name not in skip and len(name) > 2:
                found = False
                for v in victims:
                    if name in v: found = True
                if not found:
                    victims.append(f'{name} (killed)')
        if victims:
            return '; '.join(victims)
    
    # ── Targeted killing: extract the named person killed ─────────────────
    if itype == 'Targeted killing':
        names_found = []
        # "identified as Name" pattern
        for m in re.finditer(r'identified\s+as\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})', text):
            name = m.group(1).strip().rstrip(',.')
            if len(name) > 2 and name.split()[0] not in ('Security','The','According','However'):
                names_found.append(name)
        # "Name s/o Parent" pattern  
        for m in re.finditer(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+s/o\s+[A-Z]', text):
            name = m.group(1).strip()
            skip = {'Security','The','According','Deputy','Assistant','Levies','Police','Army','Additional'}
            if name.split()[0] not in skip and name not in names_found:
                names_found.append(name)
        # "Name, son of Parent" pattern
        for m in re.finditer(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?),?\s+(?:son|daughter)\s+of\s+[A-Z]', text):
            name = m.group(1).strip()
            skip = {'Security','The','According','Deputy','Assistant','Levies','Police','Army','Additional'}
            if name.split()[0] not in skip and name not in names_found:
                names_found.append(name)
        
        for name in names_found:
            # Determine status
            if has(text, r'shot\s+dead|was\s+killed|gunned.*down|opened\s+fire.*killing'):
                victims.append(f'{name} (killed)')
            elif has(text, r'sustained\s+injur|was\s+injured'):
                victims.append(f'{name} (injured)')
            else:
                victims.append(f'{name} (killed)')
        
        if victims:
            return '; '.join(victims)
    
    # ── Armed assault with named casualties ───────────────────────────────
    if itype in ('Armed assault', 'Sniper', 'IED', 'Suicide bombing'):
        names_found = []
        # Named soldiers/personnel
        for m in re.finditer(r'(?:Naik|Lance\s+Naik|Soldier|Sepoy|Captain|Lieutenant|Colonel)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)', text):
            name = m.group(0).strip()
            if name not in names_found:
                names_found.append(name)
        # Named individuals "identified as"
        for m in re.finditer(r'identified\s+as\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})', text):
            name = m.group(1).strip().rstrip(',.')
            if len(name) > 2 and name.split()[0] not in ('Security','The','According','However'):
                if name not in names_found:
                    names_found.append(name)
        
        for name in names_found:
            if has(text, r'killed|dead|martyred'):
                victims.append(f'{name} (killed)')
            elif has(text, r'injured|wounded'):
                victims.append(f'{name} (injured)')
            else:
                victims.append(name)
        
        if victims:
            return '; '.join(victims)
    
    return 'No'


def build_row(entry, row_num, month_name, year, month_num):
    day   = entry['day']
    text  = entry['text']
    primary = primary_sentence(text)

    date_str    = f"{year}-{month_num:02d}-{day:02d}"
    incident_id = f"BAL-{year}-{month_num:02d}-{row_num:03d}"

    itype    = classify_type(text, primary)
    method   = classify_method(itype, text)
    tgt_type = get_target_type(primary, text)
    tgt_org  = get_target_org(primary, tgt_type)
    perp     = get_perpetrator(text, primary, itype)
    spk      = get_spokesperson(text)
    source   = get_source(text)

    # ── Phase 2 enrichments ──────────────────────────────────────────────
    town     = get_town_area(text)
    summary  = get_incident_summary(text)
    off_src  = get_official_source(text)
    econ_sec = get_economic_sector(text, tgt_type)
    vic_prof = get_victim_profession(text, itype)
    weap_seized = get_weapons_seized(text)
    weap_recov  = get_weapons_recovered(text)
    hostages    = get_hostages_taken(text)

    # ── Phase 3 enrichments ──────────────────────────────────────────────
    vpd          = get_victim_previous_disappearance(text)
    family_tgt   = get_family_member_previously_targeted(text)
    tgt_org_smart = get_target_org_smart(text, primary, itype, tgt_type, tgt_org)

    # Claimed responsibility — broadened detection
    claimed = 'No'
    if has(text, r'claimed\s+responsibility|claiming\s+responsibility'):
        claimed = 'Yes'
    # Broader: spokesperson statement = implicit claim
    elif has(text, r'(?:BLA|BLF|BRG|BRA|UBA|TTP|BRAS|ISKP|BLA.Azad)\s+claimed',
                   r'claimed\s+(?:the|that|this)\s+(?:attack|operation|ambush)',
                   r'In\s+a\s+(?:media\s+)?statement.*?(?:BLA|BLF|BRG|TTP|BRA|UBA)',
                   r"spokesperson.*(?:said|stated|claimed)\s+(?:the|that|this|BLA|BLF)",
                   r'(?:BLA|BLF|BRG|TTP)\s+said\s+(?:the|that|its?)\s+(?:cadres|fighters|unit)',
                   r'cadres\s+on\s+.*?killed\s+.*?accusing\s+him'):
        claimed = 'Yes'
    # Explicit denial overrides
    if has(text, r'no\s+group\s+has\s+(?:so\s+far\s+)?claimed|no\s+one\s+claimed'):
        claimed = 'No'

    # Casualties
    is_non_combat = itype in {'Enforced disappearance','Aggregate report',
                              'Surrender','Protest/sit-in','Prisoner release'}
    if is_non_combat:
        sf_k, grp_claim_from_sfk = '0', '-'
    else:
        sf_k, grp_claim_from_sfk = extract_sf_killed(text)
    sf_i  = '0' if is_non_combat else extract_sf_injured(text)
    civ_k = extract_civ_killed(text, itype)
    civ_i = extract_civ_injured(text)
    mil_k = extract_militant_killed(text, itype)
    
    # Group claim: use dedicated extractor OR claim extracted from sf_killed separation
    grp_claim = extract_group_claim(text)
    if grp_claim == '-' and grp_claim_from_sfk != '-':
        grp_claim = grp_claim_from_sfk
    elif grp_claim != '-' and grp_claim_from_sfk != '-':
        # Take the higher of the two
        try:
            if int(grp_claim_from_sfk) > int(grp_claim):
                grp_claim = grp_claim_from_sfk
        except ValueError:
            pass
    
    conflict = 'No'
    if grp_claim != '-' and sf_k.isdigit() and grp_claim.isdigit():
        grp_n = int(grp_claim)
        sf_n = int(sf_k)
        if grp_n > 0 and sf_n > 0 and grp_n > sf_n * 1.5:
            conflict = 'Yes'
        elif grp_n > 0 and sf_n == 0:
            conflict = 'Yes'

    # ED fields
    is_ed  = 'Yes' if itype == 'Enforced disappearance' else 'No'
    is_ejk = 'Yes' if itype == 'Extrajudicial killing' else 'No'
    num_d, disapp_names, disapp_ids, disapp_circ = get_disappearance_info(text, itype)

    # Victim previous disappearance — use broadened detector
    prev_disapp = vpd

    # Boolean flags
    cpec         = 'Yes' if has(text, r'\bcpec\b|china.pakistan\s+economic\s+corridor') else 'No'
    prop_damaged = 'Yes' if has(text, r'destroyed|damaged|set\s+(?:fire|ablaze)|seized\s+weapons|looted') else 'No'
    govt_docs    = 'Yes' if has(text, r'records.*destroyed|nadra.*records|govt.*documents') else 'No'
    is_coord     = 'Yes' if has(text, r'coordinated\s+attack|two\s+separate\s+(?:attacks|roadblocks)',
                                      r'simultaneous|three\s+coordinated') else 'No'
    is_complex   = 'Yes' if has(text, r'first\s+attack.*second\s+attack|followed\s+by.*ambush',
                                      r'initial\s+assault.*then|two\s+phases') else 'No'
    is_agg       = 'Yes' if itype == 'Aggregate report' else 'No'
    surrender_ev = 'Yes' if itype == 'Surrender' else 'No'
    protest      = 'Yes' if itype == 'Protest/sit-in' else 'No'

    # Intelligence wing
    intel_wing = '-'
    if has(text, r'\bZIRAB\b'): intel_wing = 'ZIRAB'
    elif has(text, r'\bQAHR\b'): intel_wing = 'QAHR'

    # Media channel
    media_ch = '-'
    if has(text, r'\bHakkal\b'): media_ch = 'Hakkal'
    elif has(text, r'\bAashob\b'): media_ch = 'Aashob'

    # Perpetrator unit
    perp_unit = '-'
    if has(text, r'Majeed\s+Brigade'): perp_unit = 'Majeed Brigade'
    elif has(text, r'\bSTOS\b'): perp_unit = 'STOS'
    elif has(text, r'Sniper\s+Tactical\s+Team'): perp_unit = 'Sniper Tactical Team'
    elif has(text, r'\bQAHR\b'): perp_unit = 'QAHR'
    elif has(text, r'Fateh\s+Squad'): perp_unit = 'Fateh Squad'

    # Duration of control
    dur = '-'
    m_dur = re.search(rf'(?:lasted|controlled.*?for|remained.*?for)\s+(?:about\s+)?({_NUM})\s+hours?',
                      text, re.IGNORECASE)
    if m_dur: dur = str(to_num(m_dur.group(1)))

    # Cash looted
    cash = '-'
    m_cash = re.search(r'looted\s+(?:over\s+)?(PKR\s+[\d.]+\s+(?:million|billion))', text, re.IGNORECASE)
    if m_cash: cash = m_cash.group(1)

    # Civilian treatment
    civ_treat = '-'
    if has(text, r'released.*Baloch\s+identity|spared.*Baloch\s+identity'): 
        civ_treat = 'Released due to Baloch identity'
    elif has(text, r'warned.*released|released.*warning|warned.*leave'): 
        civ_treat = 'Released after warning'
    elif has(text, r'released\s+unharmed\b'):
        civ_treat = 'Released unharmed'

    dq = get_data_quality(text, itype, source)

    # ── New extractions: death squad, informant, time, sf counter-op ──────
    ds_k, ds_i = extract_death_squad_casualties(text, itype)
    inf_k, inf_i = extract_informant_casualties(text, itype)
    ds_flag = detect_death_squad_flag(text, itype)
    inf_flag = detect_informant_flag(text, itype)
    time_of_day = normalize_time_of_day(text)
    sf_cop, sf_cop_type = detect_sf_counter_op(text, itype)

    # ── Build row ──────────────────────────────────────────────────────────
    row = {col: '-' for col in COLUMNS}

    # Boolean defaults → 'No'
    for col in ['is_coordinated','is_complex_attack','is_aggregate_report',
                'claimed_responsibility','group_joining_event','inter_militant_conflict',
                'baloch_national_court_sentence','conflicting_claims',
                'victim_previous_disappearance','family_member_previously_targeted',
                'is_enforced_disappearance',
                'is_extrajudicial_killing','is_drone_strike_victim','paank_reported',
                'is_curfew_imposed','is_punitive_demolition','property_damaged',
                'is_cpec_related','infrastructure_disruption','govt_documents_destroyed',
                'alleged_informant_killed','death_squad_targeted',
                'sf_counter_op',
                'surrender_event','protest_or_sit_in',
                'prisoner_exchange_event']:
        row[col] = 'No'

    # Numeric defaults → '0'
    for col in ['sf_killed','sf_injured','sf_captured','civilian_killed','civilian_injured',
                'militant_killed','militant_injured','foreign_national_killed',
                'death_squad_killed','death_squad_injured',
                'informant_killed','informant_injured',
                'hostages_taken','sf_neutralized_count']:
        row[col] = '0'
    
    # 'No' defaults for specific non-boolean fields (matching gold CSVs)
    for col in ['named_victims', 'num_disappeared',
                'disappeared_names', 'time_of_day',
                'perpetrator_spokesperson']:
        row[col] = 'No'

    row.update({
        'incident_id':             incident_id,
        'date':                    date_str,
        'month':                   month_name,
        'year':                    str(year),
        'source':                  source,
        'source_count':            str(len(source.split(';'))),
        'original_description':    text,
        'district':                get_district(text, itype),
        'incident_type':           itype,
        'attack_method':           method,
        'target_type':             tgt_type,
        'target_organization':     tgt_org_smart,
        'perpetrator_group':       perp,
        'perpetrator_unit':        perp_unit,
        'perpetrator_spokesperson': spk if spk != 'No' else 'No',
        'claimed_responsibility':  claimed,
        'intelligence_wing_cited': intel_wing,
        'media_channel':           media_ch,
        'time_of_day':             time_of_day if time_of_day != '-' else 'No',
        'sf_killed':               sf_k,
        'sf_injured':              sf_i,
        'civilian_killed':         civ_k,
        'civilian_injured':        civ_i,
        'militant_killed':         mil_k,
        'death_squad_killed':      ds_k,
        'death_squad_injured':     ds_i,
        'informant_killed':        inf_k,
        'informant_injured':       inf_i,
        'group_claimed_sf_killed': grp_claim,
        'conflicting_claims':      conflict,
        'named_victims':           build_named_victims(text, itype, disapp_names),
        'victim_profession':       vic_prof,
        'victim_previous_disappearance': prev_disapp,
        'family_member_previously_targeted': family_tgt,
        'is_enforced_disappearance': is_ed,
        'num_disappeared':         num_d,
        'disappearance_circumstances': disapp_circ if disapp_circ != '-' else ('No' if itype == 'Enforced disappearance' else '-'),
        'disappeared_names':       disapp_names,
        'disappeared_identifiers': disapp_ids,
        'is_extrajudicial_killing': is_ejk,
        'is_cpec_related':         cpec,
        'property_damaged':        prop_damaged,
        'govt_documents_destroyed': govt_docs,
        'is_coordinated':          is_coord,
        'is_complex_attack':       is_complex,
        'is_aggregate_report':     is_agg,
        'alleged_informant_killed': inf_flag,
        'death_squad_targeted':    ds_flag,
        'sf_counter_op':           sf_cop if sf_cop != '-' else 'No',
        'sf_counter_op_type':      sf_cop_type,
        'surrender_event':         surrender_ev,
        'protest_or_sit_in':       protest,
        'duration_militant_control_hours': dur,
        'cash_looted':             cash,
        'civilian_treatment_policy': civ_treat,
        'data_quality':            dq,
        'town_area':               town,
        'official_source':         off_src,
        'economic_sector_targeted': econ_sec,
        'weapons_seized_by_attackers': weap_seized,
        'weapons_recovered_by_sf': weap_recov,
        'hostages_taken':          hostages,
    })

    if entry.get('is_merged'):
        row['data_quality'] = 'Low'


    # Specific property type damaged
    ptypes = []
    if has(text, r'military\s+convoy|army\s+convoy'): ptypes.append('Military convoy')
    if has(text, r'military\s+vehicle|army\s+vehicle|FC\s+vehicle'): ptypes.append('Military vehicle')
    if has(text, r'military\s+(?:camp|post|base).*(?:destroy|damage|burn)'): ptypes.append('Military post/camp')
    if has(text, r'levies\s+(?:station|thana).*(?:fire|ablaze|destroy)'): ptypes.append('Levies station')
    if has(text, r'levies\s+(?:checkpoint|post).*(?:fire|ablaze|seize)'): ptypes.append('Levies checkpoint')
    if has(text, r'police\s+(?:checkpoint|station).*(?:fire|ablaze|seize)'): ptypes.append('Police checkpoint')
    if has(text, r'nadra\s+office|nadra.*records'): ptypes.append('NADRA office')
    if has(text, r'bank\s+branch|looted.*bank'): ptypes.append('Bank branch')
    if has(text, r'municipal\s+(?:office|committee)'): ptypes.append('Municipal office')
    if has(text, r'ogdcl.*vehicle|company.*vehicle.*ogdcl'): ptypes.append('Energy infrastructure vehicle')
    if has(text, r'mineral.*transport|transporting.*mineral'): ptypes.append('Mineral transport vehicle')
    if has(text, r'passenger\s+bus|civilian\s+bus'): ptypes.append('Passenger bus')
    if has(text, r'fwo.*(?:site|vehicle)|frontier\s+works.*vehicle'): ptypes.append('FWO machinery/vehicle')
    if has(text, r'tractor|excavator|heavy.*machinery|machinery.*(?:fire|ablaze|destroy)'): ptypes.append('Construction machinery')
    if has(text, r'death\s+squad.*camp|militia.*camp.*(?:fire|attack)'): ptypes.append('Militia/death squad camp')
    if has(text, r'weapons.*seized|arms.*seized|seized.*(?:weapons|arms)'): ptypes.append('Weapons seized')
    if has(text, r'(?:hideout|cache).*(?:arms|ammo|weapon|explos)'): ptypes.append('Militant hideouts/cache')
    if has(text, r'surveillance.*camera|camera.*destroy'): ptypes.append('Surveillance equipment')
    if has(text, r'construction.*truck|truck.*(?:road\s+construction|company)'): ptypes.append('Construction vehicle')
    if has(text, r'construction\s+site|site.*set.*(?:fire|ablaze)|set.*ablaze.*site'): ptypes.append('Construction site')
    if has(text, r'police\s+station.*(?:fire|ablaze|attack)|attacked.*police\s+station'): ptypes.append('Police station')
    if has(text, r'ancestral\s+home.*demol|demol.*home|home.*demol'): ptypes.append('Civilian residence (demolished)')
    if has(text, r'trucks?.*(?:mineral|stone|precious)|mineral.*truck'): ptypes.append('Mineral transport vehicle')
    if has(text, r'levies.*checkpost|checkpost.*levies|levies.*post.*(?:fire|destroy|ablaze)'): ptypes.append('Levies checkpoint')
    row['property_type_damaged'] = '; '.join(ptypes) if ptypes else '-'

    return row

# ══════════════════════════════════════════════════════════════════════════════
# MONTH CONFIG
# ══════════════════════════════════════════════════════════════════════════════

MONTH_MAP = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
}

def extract(pdf_path, output_path, month_name='February', year=2025):
    month_num = MONTH_MAP[month_name.lower()]
    entries, expected_by_day = parse_pdf(pdf_path, month_name)

    merged_count = 0  # merged detection now handled by sanity check
    print(f"\n{'='*60}")
    print(f"EXTRACTOR: {pdf_path.split('/')[-1]}")
    print(f"{'='*60}")
    print(f"  Entries parsed:   {len(entries)}")
    if merged_count:
        print(f"  Merged flags:     {merged_count} (verify these against PDF)")

    rows = [build_row(e, i, month_name, year, month_num)
            for i, e in enumerate(entries, 1)]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Quick stats
    from collections import Counter
    types = Counter(r['incident_type'] for r in rows)
    print(f"  Output rows:      {len(rows)}")
    print(f"  Output:           {output_path.split('/')[-1]}")
    print(f"\n  Type breakdown:")
    for t,c in types.most_common():
        print(f"    {t:<30} {c}")

    sk = sum(int(r['sf_killed']) for r in rows if r['sf_killed'].isdigit())
    ck = sum(int(r['civilian_killed']) for r in rows if r['civilian_killed'].isdigit())
    dk = sum(int(r['death_squad_killed']) for r in rows if r['death_squad_killed'].isdigit())
    ik = sum(int(r['informant_killed']) for r in rows if r['informant_killed'].isdigit())
    ed = sum(1 for r in rows if r['is_enforced_disappearance']=='Yes')
    ds = sum(1 for r in rows if r['death_squad_targeted']=='Yes')
    ai = sum(1 for r in rows if r['alleged_informant_killed']=='Yes')
    print(f"\n  SF killed:              {sk}")
    print(f"  Civilian killed:        {ck}")
    print(f"  Death squad killed:     {dk} (across {ds} incidents)")
    print(f"  Informant killed:       {ik} (across {ai} incidents)")
    print(f"  ED entries:             {ed}")
    print(f"{'='*60}\n")

    return rows

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 extractor.py input.pdf output.csv [Month] [Year]")
        sys.exit(1)

    pdf_path    = sys.argv[1]
    output_path = sys.argv[2]
    month_name  = sys.argv[3] if len(sys.argv) > 3 else 'February'
    year        = int(sys.argv[4]) if len(sys.argv) > 4 else 2025

    extract(pdf_path, output_path, month_name, year)


# ── STANDALONE SANITY CHECK ───────────────────────────────────────────────────

def sanity_check_pdf(pdf_path, csv_path, month_name):
    """
    Compare extracted CSV against PDF header count.
    This is the source-of-truth validation using your insight:
    count of 'Month - N' headers = exact entry count.
    """
    import csv as csv_mod
    from collections import Counter

    # Count from PDF
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ''.join(page.extract_text()+'\n' for page in pdf.pages)
        HDRX = re.compile(rf'{month_name}\s*-\s*(\d+)', re.IGNORECASE)
        pdf_by_day = Counter(int(m.group(1)) for m in HDRX.finditer(full_text))
        pdf_total  = sum(pdf_by_day.values())
    except Exception as e:
        print(f"  Could not read PDF: {e}")
        return

    # Count from CSV
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for r in csv_mod.DictReader(f):
            rows.append(r)
    csv_by_day = Counter(int(r['date'].split('-')[2]) for r in rows)
    csv_total  = len(rows)

    print(f"\n{'='*60}")
    print(f"SANITY CHECK (header-count method)")
    print(f"{'='*60}")
    print(f"  PDF total (header count): {pdf_total}  ← ground truth")
    print(f"  CSV total (extracted):    {csv_total}")

    problems = []
    print(f"\n  {'Day':<8} {'PDF':>5} {'CSV':>5}  Status")
    print(f"  {'-'*35}")
    for day in sorted(pdf_by_day.keys()):
        exp = pdf_by_day[day]
        got = csv_by_day.get(day, 0)
        status = '✓' if got == exp else f'✗ missing {exp-got}'
        if got != exp:
            problems.append((day, exp, got))
        print(f"  Feb {day:<4} {exp:>5} {got:>5}  {status}")

    print(f"\n  {'TOTAL':<8} {pdf_total:>5} {csv_total:>5}  "
          f"{'✓ EXACT MATCH' if not problems else f'✗ {len(problems)} day(s) off'}")

    if problems:
        print(f"\n  Days with issues:")
        for day, exp, got in problems:
            print(f"    Feb {day}: expected {exp}, got {got} — check PDF for this date")
    else:
        print(f"\n  ✓ Safe to proceed to verification step.")

    print(f"{'='*60}")
    return problems


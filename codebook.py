"""
codebook.py — Master codebook for the Balochistan Incidents Dataset.

Every column is defined here with:
  - description: what the field captures
  - type: categorical / numeric / text / boolean / date
  - values: dict of {value: meaning} for categorical/boolean fields
  - null_meaning: what '-' or 'No' means for this specific field
  - example: a real example value
  - notes: caveats, rules, edge cases

This file serves THREE purposes:
  1. Human reference — look up any column to understand it
  2. Standardization — values dict is the canonical allowed-values list
  3. Documentation — export to readable formats (see bottom of file)

TO ADD A NEW COLUMN: add its entry to CODEBOOK dict below.
TO ADD A NEW VALUE:  add to the 'values' dict for that column.
"""

CODEBOOK = {

    # ══════════════════════════════════════════════════════════════
    # G1 — CORE IDENTIFIERS
    # ══════════════════════════════════════════════════════════════

    'incident_id': {
        'group': 'G1 — Core identifiers',
        'description': 'Unique identifier for each incident entry.',
        'type': 'text',
        'format': 'BAL-YYYY-MM-NNN where NNN is sequential within the month',
        'example': 'BAL-2025-01-004',
        'null_meaning': None,
        'values': {},
        'notes': 'Each row in the source PDF gets one ID. Multiple entries on the same date get sequential numbers.',
    },
    'date': {
        'group': 'G1 — Core identifiers',
        'description': 'Date of the incident in ISO format.',
        'type': 'date',
        'format': 'YYYY-MM-DD',
        'example': '2025-01-04',
        'null_meaning': None,
        'values': {},
        'notes': 'Some entries in SATP report incidents with delayed confirmation — date is the incident date not the report date.',
    },
    'month': {
        'group': 'G1 — Core identifiers',
        'description': 'Full month name of the incident.',
        'type': 'categorical',
        'example': 'January',
        'null_meaning': None,
        'values': {
            'January': 'January', 'February': 'February', 'March': 'March',
            'April': 'April', 'May': 'May', 'June': 'June', 'July': 'July',
            'August': 'August', 'September': 'September', 'October': 'October',
            'November': 'November', 'December': 'December',
        },
        'notes': '',
    },
    'year': {
        'group': 'G1 — Core identifiers',
        'description': 'Year of the incident.',
        'type': 'numeric',
        'example': '2025',
        'null_meaning': None,
        'values': {},
        'notes': '',
    },
    'source': {
        'group': 'G1 — Core identifiers',
        'description': 'News outlets or media sources cited in the SATP entry, semicolon-separated.',
        'type': 'text',
        'example': 'Dawn; The Balochistan Post',
        'null_meaning': 'No',
        'values': {},
        'notes': 'Not all sources are equal in reliability. Dawn and Geo News are considered higher quality than single-source Balochistan Post entries.',
    },
    'source_count': {
        'group': 'G1 — Core identifiers',
        'description': 'Number of distinct sources cited for this entry.',
        'type': 'numeric',
        'example': '2',
        'null_meaning': '-',
        'values': {},
        'notes': 'Higher source count generally means higher data_quality.',
    },
    'original_description': {
        'group': 'G1 — Core identifiers',
        'description': 'Full verbatim text of the SATP entry as extracted from the PDF. Preserved exactly.',
        'type': 'text',
        'example': 'The Baloch Liberation Army (BLA) cadres on January 30 executed one Muhammad Shakir...',
        'null_meaning': None,
        'values': {},
        'notes': 'This is the primary source for all other field values. Never edit this field.',
    },

    # ══════════════════════════════════════════════════════════════
    # G2 — LOCATION
    # ══════════════════════════════════════════════════════════════

    'district': {
        'group': 'G2 — Location',
        'description': 'District of Balochistan where the incident occurred.',
        'type': 'text',
        'example': 'Kech',
        'null_meaning': 'No',
        'values': {},
        'notes': 'Use the district name only, without the word "District". E.g. "Kech" not "Kech District".',
    },
    'tehsil': {
        'group': 'G2 — Location',
        'description': 'Sub-district (tehsil/revenue unit) of the incident.',
        'type': 'text',
        'example': 'Zamuran',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'town_area': {
        'group': 'G2 — Location',
        'description': 'Town, bazaar, or locality name within the tehsil.',
        'type': 'text',
        'example': 'Turbat town',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
    'location_description': {
        'group': 'G2 — Location',
        'description': 'Specific location phrase as described in the source.',
        'type': 'text',
        'example': 'in the Behman area, about eight kilometers from Turbat city',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
    'highway_route': {
        'group': 'G2 — Location',
        'description': 'Named highway or route mentioned, if relevant to the incident.',
        'type': 'text',
        'example': 'M-8 Highway',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'lat_lon_approx': {
        'group': 'G2 — Location',
        'description': 'Approximate GPS coordinates if derivable from location description.',
        'type': 'text',
        'example': '26.0, 63.0',
        'null_meaning': 'No',
        'values': {},
        'notes': 'Currently not populated. Reserved for future geocoding.',
    },

    # ══════════════════════════════════════════════════════════════
    # G3 — INCIDENT CHARACTERISTICS
    # ══════════════════════════════════════════════════════════════

    'incident_type': {
        'group': 'G3 — Incident characteristics',
        'description': 'Primary classification of the incident.',
        'type': 'categorical',
        'example': 'Armed assault',
        'null_meaning': None,
        'values': {
            'IED': 'Improvised explosive device attack — bomb, mine, or remotely detonated explosive used as primary method',
            'Armed assault': 'Attack using firearms, rockets, grenades or heavy weapons without an IED as primary method',
            'Sniper': 'Attack where a sniper rifle was the primary or stated weapon; Sniper Tactical Team operations',
            'Suicide bombing': 'Attack by a Fidayee (self-sacrifice) bomber; person-borne IED or vehicle-borne IED in a suicide mission',
            'Area seizure': 'Militants temporarily seized control of a town, tehsil headquarters, or highway area',
            'Roadblock': 'Militants set up a checkpoint or snap-check on a highway to stop, search, or execute passengers',
            'Arson': 'Primary act was setting fire to vehicles, buildings, machinery, or infrastructure',
            'Targeted killing': 'Deliberate killing of a specific named individual accused of collaborating with SF or being an informant',
            'Extrajudicial killing': 'Body found killed by SF or state-linked actors; killed in custody; fake encounter; drone strike on civilians',
            'Enforced disappearance': 'Person taken by SF or intelligence agencies and whereabouts unknown; family has no information',
            'IBO': 'Intelligence-Based Operation by Security Forces; SF-initiated operation killing/capturing militants',
            'Surrender': 'Militant(s) surrendered to authorities voluntarily and renounced violence',
            'Protest/sit-in': 'Protest or sit-in demanding recovery of disappeared persons, or condemning SF actions',
            'Train attack': 'Attack specifically targeting a train, railway track, or train passengers (e.g. Jaffar Express)',
            'Prisoner capture': 'SF personnel captured alive by militants',
            'Prisoner release': 'SF or civilian hostages/prisoners released by militants',
            'Aggregate report': 'Entry is a summary report, annual statistics, or monthly data compilation — not a single incident',
            'Punitive demolition': 'SF demolished a home or structure as collective punishment',
        },
        'notes': 'CRITICAL: Shooting ≠ IED. Survived assassination ≠ Enforced disappearance. Execution ≠ Enforced disappearance. Body recovery = Extrajudicial killing. SF operation = IBO. News report = Aggregate report.',
    },

    'attack_method': {
        'group': 'G3 — Incident characteristics',
        'description': 'Weapon or technique used in the attack. Use semicolons for multiple methods.',
        'type': 'categorical',
        'example': 'Remote-controlled IED',
        'null_meaning': '-',
        'values': {
            '-': 'Not applicable — entry type does not involve an attack (ED, aggregate, IBO, surrender, protest)',
            'Remote-controlled IED': 'IED detonated remotely (wire, radio, phone); includes car bombs remotely triggered',
            'VBIED': 'Vehicle-borne IED — car/truck loaded with explosives driven to target (not suicide)',
            'Motorcycle IED': 'IED attached to or planted on a motorcycle',
            'Person-borne IED': 'Suicide bomber carrying explosive vest/belt; Fidayee attack',
            'IED': 'Improvised explosive device where specific type is not stated',
            'Sniper': 'Sniper rifle; long-range precision shot; Sniper Tactical Team operations',
            'RPG': 'Rocket-propelled grenade launcher',
            'Rocket': 'Rocket launcher, A-1 shell, or unguided rocket/mortar rounds',
            'Grenade': 'Hand grenade thrown at target',
            'Grenade launcher': 'Grenade launcher (not RPG); under-barrel or standalone launcher',
            'Mortar': 'Mortar rounds fired at target',
            'Rocket/Mortar': 'Unguided bombs or rounds where specific type unclear',
            'Small arms': 'Pistols, rifles, AK-47, automatic weapons — gunfire',
            'Heavy weapons': 'Machine guns, anti-aircraft guns, or unspecified heavy weapons',
            'Arson': 'Fire used as the attack method; vehicles/buildings set ablaze',
            'Drone': 'Drone used as attack method — only use if MILITANTS used a drone (e.g. QAHR unit)',
            'A-1 shell': 'A-1 type artillery shell/rocket round used by BLF',
        },
        'notes': 'NEVER put IED for a shooting incident. Helicopter response ≠ attack method. Multiple methods separated by semicolons.',
    },

    'target_type': {
        'group': 'G3 — Incident characteristics',
        'description': 'What was physically attacked or threatened.',
        'type': 'text',
        'example': 'Military convoy',
        'null_meaning': 'No',
        'values': {
            'Military convoy': 'Moving column of military/SF vehicles on a road',
            'Military vehicle': 'Single military vehicle (not in convoy)',
            'Military supply convoy': 'Convoy transporting supplies/goods to a military base',
            'Military supply vehicle': 'Single vehicle carrying military supplies',
            'Military camp/post': 'Permanent military base, fort, or established camp',
            'Military post': 'Smaller military outpost or forward position',
            'Military checkpoint': 'Temporary or permanent checkpoint manned by SF',
            'Military patrol': 'SF personnel on foot or vehicle patrol',
            'Military personnel': 'Individual SF soldier(s) targeted specifically',
            'Military outpost': 'Small guard post or sentry position',
            'Police station': 'Permanent police station building',
            'Police checkpoint': 'Police checkpoint on road or at location',
            'Police personnel': 'Individual police officer(s) targeted',
            'Levies station': 'Levies Force post or station building',
            'Levies checkpoint': 'Levies Force checkpoint',
            'Levies personnel': 'Individual Levies Force member(s) targeted',
            'Coast Guard post': 'Pakistan Coast Guard post or camp',
            'Railway': 'Railway track, station, or train — confirmed as the attack target',
            'Energy/pipeline': 'Oil/gas pipeline, well, OGDCL infrastructure',
            'CPEC infrastructure': 'China-Pakistan Economic Corridor project infrastructure',
            'Construction site': 'Active construction/road building site',
            'Construction vehicle': 'Truck, excavator, or machinery at construction site',
            'FWO': 'Frontier Works Organization site or vehicle',
            'Telecom tower': 'Mobile/communication tower',
            'Government building': 'Government office, NADRA, municipal committee, registry',
            'Government vehicle': 'Government official\'s vehicle',
            'Bank': 'Bank branch or cash storage',
            'Civilian': 'Individual civilian(s) with no official role',
            'Civilian vehicle': 'Passenger car, bus, or private vehicle',
            'Mineral transport vehicle': 'Truck/vehicle transporting chromite, coal, or other minerals',
            'Mining workers': 'Coal mine or mineral sector workers',
            'Death squad/militia': 'State-backed local militia member (death squad operative)',
            'Alleged informant': 'Person accused by militants of being an intelligence informant',
            'Political figure': 'Elected official (MPA, MNA, senator) or senior government appointee — ONLY if they are the confirmed target',
            'Civilian residence': 'Private home or residence',
            'Security Forces post': 'Generic SF post (when specific branch not identifiable)',
            'Highway': 'The highway itself blocked or targeted (roadblock incidents)',
            'Religious scholar': 'Maulana, mufti, or religious figure',
            'Government official': 'Government employee or officer (non-elected)',
            'Artist/musician': 'Balochi singer, poet, or cultural figure',
            'Academic/educator': 'Teacher, lecturer, principal, or student',
            'Worker': 'Generic laborer or informal sector worker',
            'Religious minority': 'Hindu, Sikh, or other minority community member',
        },
        'notes': 'What was PHYSICALLY struck. Source attribution is not a target. Geographical reference is not a target. Perpetrator organization is not a target.',
    },

    'target_organization': {
        'group': 'G3 — Incident characteristics',
        'description': 'Organization whose personnel or property was attacked.',
        'type': 'text',
        'example': 'FC; Army',
        'null_meaning': 'No',
        'values': {
            'FC': 'Frontier Corps — paramilitary border force',
            'Army': 'Pakistan Army',
            'Police': 'Regular Police',
            'Levies': 'Levies Force — tribal paramilitary',
            'CTD': 'Counter Terrorism Department',
            'Coast Guard': 'Pakistan Coast Guard',
            'Navy': 'Pakistan Navy',
            'Air Force': 'Pakistan Air Force',
            'FWO': 'Frontier Works Organization — military construction body',
            'OGDCL': 'Oil and Gas Development Corporation Limited',
            'Railways': 'Pakistan Railways',
            '-': 'Target organization not applicable (civilian target, death squad, etc.)',
        },
        'notes': 'Remove Army from entries where Army is not the target — e.g. OGDCL attacks, civilian killings, mineral transport. Use semicolons for multiple organizations.',
    },

    'time_of_day': {
        'group': 'G3 — Incident characteristics',
        'description': 'Approximate time of day when the incident occurred.',
        'type': 'categorical',
        'example': 'Night',
        'null_meaning': 'No',
        'values': {
            'Morning': 'Dawn to noon (00:00–12:00)',
            'Afternoon': 'Noon to 5pm (12:00–17:00)',
            'Evening': '5pm to 8pm (17:00–20:00)',
            'Night': '8pm to dawn (20:00–00:00)',
            'No': 'Time not mentioned in source',
        },
        'notes': 'Specific times (e.g. 5:45 PM) should be converted to the category. Original time can be noted in incident_summary if important.',
    },

    'is_coordinated': {
        'group': 'G3 — Incident characteristics',
        'description': 'Whether the attack was explicitly described as coordinated across multiple fronts, directions, or units simultaneously.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Explicitly coordinated — simultaneous attacks, multiple directions, or multiple units acting together', 'No': 'Single-vector attack or coordination not mentioned'},
        'notes': '',
    },
    'is_complex_attack': {
        'group': 'G3 — Incident characteristics',
        'description': 'Whether the attack had multiple distinct phases (e.g. IED then ambush, initial attack then ambush of reinforcements).',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Two or more distinct attack phases in one operation', 'No': 'Single-phase attack'},
        'notes': '',
    },
    'is_aggregate_report': {
        'group': 'G3 — Incident characteristics',
        'description': 'Whether this entry is a summary/statistical report rather than a single incident.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Entry is a monthly/annual report, press conference data, or compiled statistics', 'No': 'Single incident entry'},
        'notes': 'Must match incident_type=Aggregate report.',
    },

    # ══════════════════════════════════════════════════════════════
    # G4 — PERPETRATORS
    # ══════════════════════════════════════════════════════════════

    'perpetrator_group': {
        'group': 'G4 — Perpetrators',
        'description': 'Militant group(s) that carried out or claimed the incident.',
        'type': 'categorical',
        'example': 'BLA',
        'null_meaning': 'Unidentified',
        'values': {
            'BLA': 'Baloch Liberation Army — largest and most active Baloch insurgent group',
            'BLF': 'Balochistan Liberation Front — second-largest; active in Kech and Awaran',
            'BRG': 'Baloch Republican Guards — smaller group; spokesperson Dostain Baloch',
            'BRA': 'Baloch Republican Army',
            'BRAS': 'Baloch Raji Aajoi Sangar — coalition of pro-independence groups',
            'TTP': 'Tehreek-e-Taliban Pakistan — Pakistani Taliban; active in Zhob, Qila Abdullah',
            'ISKP': 'Islamic State Khorasan Province — declared war on BLA/BLF May 2025',
            'UBA': 'United Baloch Army — smaller group; reappeared Feb 2025 after 4-month absence',
            'BLA-Azad': 'BLA Azad faction — split from main BLA in 2018; active in Kalat/Harnai area',
            'Security Forces': 'Pakistan Security Forces — used ONLY when SF are the perpetrator (EJK, enforced disappearance)',
            'Security Forces/intelligence agencies': 'SF or intelligence agencies (ISI, MI, CTD) as perpetrator',
            'Death squad (state-backed militia)': 'State-backed local militia (e.g. Shafiq Mengal group, Kamran Umar group)',
            'Unidentified': 'No group identified or claimed responsibility',
            'Unidentified (banned outfit)': 'SF operation against unnamed banned outfit',
        },
        'notes': 'For multi-group entries use semicolons: BLA; BLF. SF as perpetrator ONLY for EJK, enforced disappearance, or punitive demolition entries.',
    },

    'perpetrator_unit': {
        'group': 'G4 — Perpetrators',
        'description': 'Specific unit or squad within the perpetrator group.',
        'type': 'text',
        'example': 'Majeed Brigade',
        'null_meaning': '-',
        'values': {
            'Majeed Brigade': 'BLA elite suicide/fidayee unit; led major operations',
            'STOS': 'BLA Special Tactical Operations Squad — carries out precision attacks',
            'Fateh Squad': 'BLA Fateh Squad — special operations',
            'Sniper Tactical Team': 'BLF dedicated sniper unit',
            'QAHR': 'BLA QAHR drone unit (Qazi Aero Hive Rangers) — announced Feb 2026; drone capability',
            'Saddo Operational Battalion': 'BLA operational battalion',
            '-': 'No specific unit mentioned or not applicable',
        },
        'notes': '',
    },

    'claimed_responsibility': {
        'group': 'G4 — Perpetrators',
        'description': 'Whether a group formally claimed responsibility for the incident.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Named spokesperson or group issued a formal statement claiming the incident',
            'No': 'No claim made OR source explicitly states no group claimed responsibility',
        },
        'notes': 'If PDF says "no group has so far claimed responsibility" → No, even if BLA/BLF appear elsewhere in the text.',
    },

    'perpetrator_spokesperson': {
        'group': 'G4 — Perpetrators',
        'description': 'Named spokesperson who issued the claim.',
        'type': 'text',
        'example': 'Jeeyand Baloch',
        'null_meaning': 'No',
        'values': {
            'Jeeyand Baloch': 'BLA spokesperson — most frequent in dataset',
            'Major Gwahram Baloch': 'BLF spokesperson (also spelled Gohram, Gwhram)',
            'Dostain Baloch': 'BRG spokesperson',
            'Azad Baloch': 'BLA spokesperson (secondary)',
            'Mazar Baloch': 'BLA spokesperson (secondary)',
        },
        'notes': '',
    },

    'intelligence_wing_cited': {
        'group': 'G4 — Perpetrators',
        'description': 'Militant intelligence wing cited as providing targeting intelligence.',
        'type': 'text',
        'example': 'ZIRAB',
        'null_meaning': '-',
        'values': {
            'ZIRAB': 'BLA intelligence wing — provides targeting intel for BLA operations',
            'QAHR': 'BLA QAHR unit (also drone unit) — cited for drone-based intelligence',
            'BLF intelligence': 'BLF organizational intelligence (unnamed in most entries)',
            '-': 'No intelligence wing cited',
        },
        'notes': '',
    },

    'media_channel': {
        'group': 'G4 — Perpetrators',
        'description': 'Militant media channel through which the claim was released.',
        'type': 'text',
        'example': 'Hakkal',
        'null_meaning': '-',
        'values': {
            'Hakkal': 'BLA media channel',
            'Aashob': 'BLF media cell (Aashob Media Cell)',
            'Al-Azaim': 'ISKP media channel',
            '-': 'No specific media channel cited',
        },
        'notes': '',
    },

    'group_joining_event': {
        'group': 'G4 — Perpetrators',
        'description': 'Whether this entry describes groups or individuals joining a militant organization.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'A group or individual announced joining (e.g. Baloch groups joining TTP)',
            'No': 'Not a joining/recruitment event',
        },
        'notes': '',
    },

    'inter_militant_conflict': {
        'group': 'G4 — Perpetrators',
        'description': 'Whether this entry describes conflict between different militant groups.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'ISKP vs BLA/BLF conflict, or inter-group fighting',
            'No': 'No inter-militant conflict',
        },
        'notes': 'Key example: ISKP declared war on BLA/BLF May 25 2025.',
    },

    'baloch_national_court_sentence': {
        'group': 'G4 — Perpetrators',
        'description': 'Whether BLA\'s internal judicial body ("Baloch National Court") issued a death sentence for the victim.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'BLA/BNM internal court sentenced the victim before execution',
            'No': 'No mention of Baloch National Court',
        },
        'notes': 'Distinct from general targeted killings — the BNC implies a formal internal judicial process.',
    },

    # ══════════════════════════════════════════════════════════════
    # G5 — CASUALTIES
    # ══════════════════════════════════════════════════════════════

    'sf_killed': {
        'group': 'G5 — Casualties',
        'description': 'Number of Security Forces personnel confirmed killed (official/media figure).',
        'type': 'numeric',
        'example': '3',
        'null_meaning': '0',
        'values': {},
        'notes': 'Use OFFICIAL confirmed count. Group claims go in group_claimed_sf_killed. If exact number unknown, use 0.',
    },
    'sf_injured': {
        'group': 'G5 — Casualties',
        'description': 'Number of Security Forces personnel confirmed injured.',
        'type': 'numeric',
        'example': '4',
        'null_meaning': '0',
        'values': {},
        'notes': '',
    },
    'sf_captured': {
        'group': 'G5 — Casualties',
        'description': 'Number of SF personnel captured alive by militants.',
        'type': 'numeric',
        'example': '1',
        'null_meaning': '-',
        'values': {},
        'notes': 'Use - for no capture. Value 0 is not used for this field.',
    },
    'sf_captured_names': {
        'group': 'G5 — Casualties',
        'description': 'Names and ranks of captured SF personnel.',
        'type': 'text',
        'example': 'Sepoy Zafarullah (FC)',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'civilian_killed': {
        'group': 'G5 — Casualties',
        'description': 'Number of civilians killed.',
        'type': 'numeric',
        'example': '2',
        'null_meaning': '0',
        'values': {},
        'notes': 'Includes OGDCL workers, miners, labourers, journalists, and all non-SF, non-militant victims.',
    },
    'civilian_injured': {
        'group': 'G5 — Casualties',
        'description': 'Number of civilians injured.',
        'type': 'numeric',
        'example': '3',
        'null_meaning': '0',
        'values': {},
        'notes': '',
    },
    'militant_killed': {
        'group': 'G5 — Casualties',
        'description': 'Number of militants killed (by SF or in combat).',
        'type': 'numeric',
        'example': '4',
        'null_meaning': '0',
        'values': {},
        'notes': 'Includes militants killed in IBO, crossfire, or SF clearance operations.',
    },
    'militant_injured': {
        'group': 'G5 — Casualties',
        'description': 'Number of militants injured.',
        'type': 'numeric',
        'example': '2',
        'null_meaning': '0',
        'values': {},
        'notes': '',
    },
    'foreign_national_killed': {
        'group': 'G5 — Casualties',
        'description': 'Number of foreign nationals killed.',
        'type': 'numeric',
        'example': '1',
        'null_meaning': '0',
        'values': {},
        'notes': 'Includes Afghan nationals, Chinese workers, etc.',
    },
    'hostages_taken': {
        'group': 'G5 — Casualties',
        'description': 'Number of persons taken hostage during the incident.',
        'type': 'numeric',
        'example': '5',
        'null_meaning': '-',
        'values': {},
        'notes': 'Use - for no hostage-taking; value 0 not used',
    },
    'group_claimed_sf_killed': {
        'group': 'G5 — Casualties',
        'description': 'Number of SF killed as claimed by the militant group (may differ from official figure).',
        'type': 'numeric',
        'example': '47',
        'null_meaning': '-',
        'values': {},
        'notes': 'Always compare with sf_killed (official). If group_claimed_sf_killed > sf_killed * 2, set conflicting_claims=Yes.',
    },
    'conflicting_claims': {
        'group': 'G5 — Casualties',
        'description': 'Whether official and militant group casualty figures conflict significantly.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Official count and group claim differ significantly (typically >2x)',
            'No': 'Counts are consistent or only one figure available',
        },
        'notes': '',
    },
    'casualty_notes': {
        'group': 'G5 — Casualties',
        'description': 'Free text note on casualty discrepancy, context, or where "exact number not known".',
        'type': 'text',
        'example': 'Official: 3 SF killed; BLA STOS claims 11 killed, 28 injured',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
    'named_victims': {
        'group': 'G5 — Casualties',
        'description': 'Every named person in the entry with their status and role. Semicolon-separated.',
        'type': 'text',
        'example': 'Naik Shiraz (Army intelligence; killed); Ahmed Raza System Operator (Army intelligence; killed)',
        'null_meaning': 'No',
        'values': {},
        'notes': 'Include: SF victims with rank, civilians with s/o parentage, disappeared persons, death squad members killed, informant executees, fidayee attackers. Also note official sources but mark as (official source) not victim. Do NOT include pure spokespersons with no victim role.',
    },
    'victim_profession': {
        'group': 'G5 — Casualties',
        'description': 'Profession of the primary civilian victim, if stated.',
        'type': 'text',
        'example': 'journalist',
        'null_meaning': '-',
        'values': {
            'journalist': 'Reporter, correspondent, or journalist',
            'poet/writer': 'Poet, author, or writer',
            'student': 'Student at school, college, or university',
            'lecturer/academic': 'University or college lecturer',
            'contractor': 'Construction or project contractor',
            'fisherman': 'Fisherman or fishing community member',
            'trader/businessman': 'Shopkeeper, trader, or businessman',
            'labourer': 'Manual labourer or construction worker',
            'police': 'Police officer',
            'levies': 'Levies Force member',
            'CTD': 'Counter Terrorism Department officer',
            'PPL/OGDCL employee': 'Oil and gas sector employee',
            'govt employee': 'Government employee',
            '-': 'Not mentioned or not applicable',
        },
        'notes': '',
    },
    'victim_political_affiliation': {
        'group': 'G5 — Casualties',
        'description': 'Political or civil society affiliation of victim, if stated.',
        'type': 'text',
        'example': 'BYC',
        'null_meaning': '-',
        'values': {
            'BSO': 'Baloch Students Organization',
            'BYC': 'Baloch Yakjehti Committee',
            'BNM': 'Baloch National Movement',
            'NDP': 'National Democratic Party',
            'JUI-F': 'Jamiat Ulema-e-Islam (Fazl)',
            'PTM': 'Pashtun Tahafuz Movement',
            'VBMP': 'Voice for Baloch Missing Persons',
            '-': 'Not mentioned',
        },
        'notes': '',
    },
    'victim_previous_disappearance': {
        'group': 'G5 — Casualties',
        'description': 'Whether the victim had previously been subjected to enforced disappearance.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Victim was previously disappeared and released before this incident',
            'No': 'No previous disappearance mentioned',
        },
        'notes': 'Key for tracking repeat targeting patterns.',
    },

    # ══════════════════════════════════════════════════════════════
    # G6 — ENFORCED DISAPPEARANCES & EXTRAJUDICIAL
    # ══════════════════════════════════════════════════════════════

    'is_enforced_disappearance': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether this entry is an enforced disappearance.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Person was taken by SF/intelligence agencies and whereabouts are unknown',
            'No': 'Not an enforced disappearance',
        },
        'notes': 'Must match incident_type Enforced disappearance.',
    },
    'num_disappeared': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Number of persons disappeared in this incident.',
        'type': 'numeric',
        'example': '4',
        'null_meaning': '-',
        'values': {},
        'notes': 'Use dash when is_enforced_disappearance is No',
    },
    'disappeared_names': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Full names of disappeared persons, with parentage where stated. Semicolon-separated.',
        'type': 'text',
        'example': 'Sher Jan Ishaq; Farooq Ishaq; Ramzan Baloch',
        'null_meaning': '-',
        'values': {},
        'notes': 'Include s/o (son of) and d/o (daughter of) if stated in source. Must be present whenever is_enforced_disappearance=Yes and names exist in text.',
    },
    'disappeared_identifiers': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Occupation, organization, or other identifying information about disappeared persons.',
        'type': 'text',
        'example': 'student; journalist; OGDCL employee',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'disappearance_circumstances': {
        'group': 'G6 — Enforced disappearances',
        'description': 'How the disappearance occurred.',
        'type': 'text',
        'example': 'Plainclothes agents',
        'null_meaning': '-',
        'values': {
            'Plainclothes agents': 'Taken by men in civilian clothing, often identifying as FIA/police',
            'Raid on home': 'SF raided the victim\'s home',
            'While travelling': 'Stopped and taken while on road/travelling',
            'From shop/workplace': 'Taken from their place of work',
            'At military checkpoint': 'Taken at a SF/FC checkpoint',
            'At international airport': 'Taken at airport upon arrival',
            'From public gathering': 'Taken from a public event, wedding, ceremony',
            '-': 'Circumstances not specified',
        },
        'notes': '',
    },
    'is_extrajudicial_killing': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether the entry describes an extrajudicial killing by state actors.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Body found with signs of torture after disappearance; fake encounter; killed in custody; drone strike on civilians',
            'No': 'Not an EJK',
        },
        'notes': '',
    },
    'is_drone_strike_victim': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether victim was killed in a drone strike by SF.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Killed in SF drone strike', 'No': 'Not a drone strike'},
        'notes': '',
    },
    'paank_reported': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether Paank (BNM human rights dept) reported or documented this incident.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Paank cited in entry', 'No': 'Paank not cited'},
        'notes': '',
    },
    'is_curfew_imposed': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether SF imposed a curfew following the incident.',
        'type': 'boolean',
        'example': 'No',
        'null_meaning': 'No',
        'values': {'Yes': 'Curfew imposed', 'No': 'No curfew'},
        'notes': '',
    },
    'is_punitive_demolition': {
        'group': 'G6 — Enforced disappearances',
        'description': 'Whether SF demolished a home or structure as collective punishment.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Home/structure demolished by SF', 'No': 'No punitive demolition'},
        'notes': 'Key example: Feb 10 2026 — SF demolished BLA chief\'s ancestral home in Nushki.',
    },

    # ══════════════════════════════════════════════════════════════
    # G7 — PROPERTY / ECONOMIC
    # ══════════════════════════════════════════════════════════════

    'property_damaged': {
        'group': 'G7 — Property/economic',
        'description': 'Whether property was damaged or destroyed.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Property damaged/destroyed', 'No': 'No property damage'},
        'notes': '',
    },
    'property_type_damaged': {
        'group': 'G7 — Property/economic',
        'description': 'Type of property damaged.',
        'type': 'text',
        'example': 'Vehicle; Building/post',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
    'economic_sector_targeted': {
        'group': 'G7 — Property/economic',
        'description': 'Economic sector targeted if attack had economic dimension.',
        'type': 'text',
        'example': 'Energy/oil and gas',
        'null_meaning': '-',
        'values': {
            'Energy/oil and gas': 'OGDCL, PPL, gas pipeline, oil wells',
            'Mining/minerals': 'Coal, chromite, copper, gold mines or mineral transport',
            'Railways/transport': 'Train, railway track, transport infrastructure',
            'Banking': 'Bank branch, cash looting',
            'Telecommunications': 'Mobile towers, communication infrastructure',
            'CPEC/FDI': 'China-Pakistan Economic Corridor projects and Chinese investment',
            'Construction': 'Road construction, FWO projects',
            '-': 'No specific economic sector targeted',
        },
        'notes': '',
    },
    'is_cpec_related': {
        'group': 'G7 — Property/economic',
        'description': 'Whether the incident targeted CPEC infrastructure or a Chinese-linked project.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'CPEC or Chinese project explicitly mentioned as target or context', 'No': 'No CPEC connection'},
        'notes': '',
    },
    'weapons_seized_by_attackers': {
        'group': 'G7 — Property/economic',
        'description': 'Weapons or military equipment seized from SF by militants.',
        'type': 'text',
        'example': '20 AK-47s; 4,000 rounds; 10 motorcycles',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'weapons_recovered_by_sf': {
        'group': 'G7 — Property/economic',
        'description': 'Whether SF recovered weapons/ammunition during an IBO or clearance operation.',
        'type': 'text',
        'example': 'Yes',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'cash_looted': {
        'group': 'G7 — Property/economic',
        'description': 'Cash amount looted if mentioned.',
        'type': 'text',
        'example': 'PKR 90 million',
        'null_meaning': '-',
        'values': {},
        'notes': 'Zehri area seizure Jan 8 2025: PKR 90 million looted from bank strong room.',
    },
    'infrastructure_disruption': {
        'group': 'G7 — Property/economic',
        'description': 'Whether the incident disrupted infrastructure services (roads, trains, utilities).',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Service suspended, route closed, or highway blocked', 'No': 'No disruption'},
        'notes': '',
    },
    'govt_documents_destroyed': {
        'group': 'G7 — Property/economic',
        'description': 'Whether government records or documents were destroyed.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Records ransacked or burned', 'No': 'No document destruction'},
        'notes': 'Key examples: Zehri area seizure (Levies records burned), NADRA office destroyed Panjgur Feb 14.',
    },

    # ══════════════════════════════════════════════════════════════
    # G8 — AREA SEIZURE TACTICS
    # ══════════════════════════════════════════════════════════════

    'duration_militant_control_hours': {
        'group': 'G8 — Area seizure tactics',
        'description': 'How many hours militants controlled an area.',
        'type': 'numeric',
        'example': '8',
        'null_meaning': '-',
        'values': {},
        'notes': 'Dash means not applicable - not an area seizure entry',
    },
    'entry_vehicles_count': {
        'group': 'G8 — Area seizure tactics',
        'description': 'Number of vehicles used in the area seizure entry.',
        'type': 'text',
        'example': '5 vehicles + 20 motorcycles',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'entry_direction': {
        'group': 'G8 — Area seizure tactics',
        'description': 'Direction or route from which militants entered the seized area.',
        'type': 'categorical',
        'example': 'From mountains',
        'null_meaning': '-',
        'values': {
            'From mountains': 'Militants descended from nearby mountains/hills',
            'From highway': 'Entered from the main highway or road',
            'Urban infiltration': 'Entered through the town/bazaar from inside',
            '-': 'Not applicable or not described',
        },
        'notes': '',
    },
    'public_address_method': {
        'group': 'G8 — Area seizure tactics',
        'description': 'How militants communicated with the local population during seizure.',
        'type': 'categorical',
        'example': 'Loudspeaker at mosque',
        'null_meaning': '-',
        'values': {
            'Loudspeaker at mosque': 'Used mosque loudspeaker to announce control',
            'Direct address to residents': 'Spoke directly to gathered residents',
            'Media statement': 'Issued statement to media from seized area',
            '-': 'Not applicable or not described',
        },
        'notes': '',
    },
    'civilian_treatment_policy': {
        'group': 'G8 — Area seizure tactics',
        'description': 'How militants treated civilians during the area seizure or roadblock.',
        'type': 'text',
        'example': 'Released due to Baloch identity',
        'null_meaning': '-',
        'values': {
            'Released due to Baloch identity': 'Non-SF civilians released specifically because they identified as Baloch',
            'Released unharmed': 'Civilians released without harm (no identity check mentioned)',
            'Released after warning': 'Released but warned against future collaboration',
            'Civilians allowed to pass safely': 'Civilians not stopped or harmed',
            'Released after warning; non-Baloch executed': 'Baloch released; non-Baloch passengers executed',
            '-': 'Not applicable',
        },
        'notes': 'The Baloch identity release policy is a key ideological marker in BLA/BLF operations.',
    },

    # ══════════════════════════════════════════════════════════════
    # G9 — PRISONER
    # ══════════════════════════════════════════════════════════════

    'prisoner_exchange_event': {
        'group': 'G9 — Prisoner',
        'description': 'Whether this entry involves a prisoner exchange or release demand.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Prisoner exchange event or deadline issued', 'No': 'Not a prisoner exchange event'},
        'notes': '',
    },
    'prisoners_released_count': {
        'group': 'G9 — Prisoner',
        'description': 'Number of prisoners released.',
        'type': 'numeric',
        'example': '2',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'prisoner_release_reason': {
        'group': 'G9 — Prisoner',
        'description': 'Reason given for prisoner release.',
        'type': 'text',
        'example': 'Humanitarian grounds',
        'null_meaning': '-',
        'values': {
            'Humanitarian grounds': 'Released citing humanitarian reasons',
            'Baloch identity': 'Released because prisoner identified as Baloch',
            'Deadline': 'Released before/after a stated deadline',
            'Prisoner exchange': 'Part of formal prisoner exchange deal',
            '-': 'Not applicable',
        },
        'notes': '',
    },
    'captivity_duration_days': {
        'group': 'G9 — Prisoner',
        'description': 'Number of days prisoner was held before release.',
        'type': 'numeric',
        'example': '15',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },

    # ══════════════════════════════════════════════════════════════
    # G10 — FIDAYEE BIOGRAPHY
    # ══════════════════════════════════════════════════════════════

    'fidayee_name': {
        'group': 'G10 — Fidayee biography',
        'description': 'Real name of the suicide bomber/fidayee attacker.',
        'type': 'text',
        'example': 'Sangat Bahar Ali',
        'null_meaning': '-',
        'values': {},
        'notes': 'dash for all non-suicide bombing entries',
    },
    'fidayee_codename': {
        'group': 'G10 — Fidayee biography',
        'description': 'Operational codename given by the group.',
        'type': 'text',
        'example': 'Droshum',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_dob': {
        'group': 'G10 — Fidayee biography',
        'description': 'Date of birth of the fidayee.',
        'type': 'date',
        'example': 'September 13, 2006',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_gender': {
        'group': 'G10 — Fidayee biography',
        'description': 'Gender of the fidayee.',
        'type': 'categorical',
        'example': 'Female',
        'null_meaning': '-',
        'values': {
            'Male': 'Male fidayee attacker',
            'Female': 'Female fidayee attacker',
            '-': 'Not a fidayee entry',
        },
        'notes': 'Female fidayee: Hawa Baloch (Feb 2026) — notable documented case.',
    },
    'fidayee_hometown': {
        'group': 'G10 — Fidayee biography',
        'description': 'Hometown or area of origin of the fidayee.',
        'type': 'text',
        'example': 'Qohda Murad Muhammad Bazar, Dasht Hochat, Turbat',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_year_joined_movement': {
        'group': 'G10 — Fidayee biography',
        'description': 'Year the fidayee joined the Baloch national movement.',
        'type': 'numeric',
        'example': '2017',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_fronts_served': {
        'group': 'G10 — Fidayee biography',
        'description': 'Operational fronts the fidayee served on before volunteering.',
        'type': 'text',
        'example': 'urban; mountain',
        'null_meaning': '-',
        'values': {
            'urban': 'Served on urban front',
            'mountain': 'Served on mountain front',
            '-': 'Not applicable',
        },
        'notes': '',
    },
    'fidayee_year_volunteered_fidayee': {
        'group': 'G10 — Fidayee biography',
        'description': 'Year the fighter specifically volunteered for fidayee/suicide mission.',
        'type': 'numeric',
        'example': '2022',
        'null_meaning': '-',
        'values': {},
        'notes': 'Distinct from year_joined_movement — this is when they volunteered for the specific suicide mission.',
    },
    'fidayee_family_background': {
        'group': 'G10 — Fidayee biography',
        'description': 'Family history relevant to the fidayee (father\'s fate, political household).',
        'type': 'text',
        'example': 'Politically active household; fifth among siblings; father Nako Nabi Bakhsh killed 2021',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_education': {
        'group': 'G10 — Fidayee biography',
        'description': 'Educational background of the fidayee.',
        'type': 'text',
        'example': 'Government Girls High School Kohad',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'fidayee_final_message_recorded': {
        'group': 'G10 — Fidayee biography',
        'description': 'Whether the fidayee recorded a final message or farewell.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': '-',
        'values': {
            'Yes': 'Final video/audio message recorded before mission',
            'No': 'No final message mentioned',
            '-': 'Not a fidayee entry',
        },
        'notes': '',
    },

    # ══════════════════════════════════════════════════════════════
    # G11 — INFORMANT EXECUTION DETAIL
    # ══════════════════════════════════════════════════════════════

    'informant_detained_date': {
        'group': 'G11 — Informant execution',
        'description': 'Date the alleged informant was apprehended by the militant group.',
        'type': 'text',
        'example': 'January 8',
        'null_meaning': '-',
        'values': {},
        'notes': 'Typically weeks before execution after interrogation.',
    },
    'informant_handler_named': {
        'group': 'G11 — Informant execution',
        'description': 'Name and rank of the ISI/MI handler named by the informant during interrogation.',
        'type': 'text',
        'example': 'Major Mujtaba',
        'null_meaning': '-',
        'values': {},
        'notes': 'Key Jan 2025 example: Muhammad Shakir confessed working under "Major Mujtaba".',
    },
    'informant_alleged_methods': {
        'group': 'G11 — Informant execution',
        'description': 'Methods the informant allegedly used to spy.',
        'type': 'text',
        'example': 'tracking device/chip; fake social media accounts; surveillance/monitoring; extortion; informing',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'informant_network_size': {
        'group': 'G11 — Informant execution',
        'description': 'Size of the intelligence network the informant was part of.',
        'type': 'numeric',
        'example': '5',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'informant_network_members_named': {
        'group': 'G11 — Informant execution',
        'description': 'Named members of the informant\'s intelligence network.',
        'type': 'text',
        'example': 'ex-Army Colonel Umar; MI officer Shahid; Subedar Ghulam Hussain; Subedar Jamil',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'informant_victims_named': {
        'group': 'G11 — Informant execution',
        'description': 'Named individuals whose disappearance or death the informant allegedly facilitated.',
        'type': 'text',
        'example': 'Agha Akhtar Shah in Killi Pandarani; Faraz Zehri (petrol station worker Kalat)',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'informant_occupation': {
        'group': 'G11 — Informant execution',
        'description': 'Civilian occupation of the informant (which provided their intelligence access).',
        'type': 'text',
        'example': 'Telecommunications supervisor',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },

    # ══════════════════════════════════════════════════════════════
    # G12 — AGGREGATE REPORT FIELDS
    # ══════════════════════════════════════════════════════════════

    'reporting_organization': {
        'group': 'G12 — Aggregate report',
        'description': 'Organization that produced the aggregate report.',
        'type': 'text',
        'example': 'BLA',
        'null_meaning': '-',
        'values': {
            'BLA': 'BLA annual/periodic report (Dhak series)',
            'BLF': 'BLF report',
            'Paank/BNM': 'Paank — BNM human rights department',
            'BYC': 'Baloch Yakjehti Committee',
            'HRCB': 'Human Rights Council of Balochistan',
            'Government (ACS/Home Dept)': 'Provincial government — Additional Chief Secretary or Home Department',
            'Government (ACS/CTD)': 'Government counter-terrorism figures',
            '-': 'Not an aggregate report entry',
        },
        'notes': '',
    },
    'report_period_covered': {
        'group': 'G12 — Aggregate report',
        'description': 'Time period covered by the aggregate report.',
        'type': 'text',
        'example': 'Annual 2024',
        'null_meaning': '-',
        'values': {},
        'notes': 'Format: Annual YYYY or Monthly (Month YYYY)',
    },
    'aggregate_attacks_reported': {
        'group': 'G12 — Aggregate report',
        'description': 'Total attacks reported in the aggregate entry.',
        'type': 'numeric',
        'example': '938',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'aggregate_disappeared_reported': {
        'group': 'G12 — Aggregate report',
        'description': 'Total enforced disappearances reported.',
        'type': 'numeric',
        'example': '22',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'aggregate_killed_reported': {
        'group': 'G12 — Aggregate report',
        'description': 'Total deaths reported in the aggregate.',
        'type': 'numeric',
        'example': '1002',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'aggregate_sf_killed_reported': {
        'group': 'G12 — Aggregate report',
        'description': 'Total SF killed as reported in the aggregate.',
        'type': 'numeric',
        'example': '545',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'aggregate_sf_operations_reported': {
        'group': 'G12 — Aggregate report',
        'description': 'Total SF operations (IBOs, clearance ops) reported.',
        'type': 'numeric',
        'example': '78000',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },

    # ══════════════════════════════════════════════════════════════
    # G13 — NETWORK / QUALITATIVE / METADATA
    # ══════════════════════════════════════════════════════════════

    'named_individuals': {
        'group': 'G13 — Network/qualitative',
        'description': 'All named persons in the entry with role tags, for network analysis.',
        'type': 'text',
        'example': 'Jeeyand Baloch (spokesperson); Naik Shiraz (SF-killed); Yasir Dashti (official-source)',
        'null_meaning': 'No',
        'values': {},
        'notes': 'Role tags: perpetrator / victim / SF / official / informant / fidayee / political / spokesperson',
    },
    'alleged_informant_killed': {
        'group': 'G13 — Network/qualitative',
        'description': 'Whether this entry describes a militant execution of an alleged SF informant.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'BLA/BLF executed someone on allegation of being ISI/MI agent or informant',
            'No': 'Not an informant execution',
        },
        'notes': '',
    },
    'death_squad_targeted': {
        'group': 'G13 — Network/qualitative',
        'description': 'Whether this entry involves targeting of state-backed militia (death squad) members.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {
            'Yes': 'Death squad/state militia member was the target or a key actor',
            'No': 'No death squad involvement',
        },
        'notes': '',
    },
    'sf_counter_op': {
        'group': 'G13 — Network/qualitative',
        'description': 'Type of SF counter-operation if entry describes SF action.',
        'type': 'text',
        'example': 'IBO',
        'null_meaning': '-',
        'values': {
            'IBO': 'Intelligence-Based Operation',
            'Border interception': 'SF intercepted militants trying to cross Pakistan-Afghanistan border',
            'Clearance/sanitization': 'SF clearance or sanitization operation after an attack',
            'Azm-e-Istehkam': 'Operation Azm-e-Istehkam — national counter-terrorism campaign',
            'Radd-ul-Fitna': 'Operation Radd-ul-Fitna — specific counter-insurgency operation',
            '-': 'Not a SF counter-operation entry',
        },
        'notes': '',
    },
    'sf_neutralized_count': {
        'group': 'G13 — Network/qualitative',
        'description': 'Number of militants neutralized (killed) by SF in IBO or clearance operations.',
        'type': 'numeric',
        'example': '27',
        'null_meaning': '-',
        'values': {},
        'notes': 'Use only for SF-initiated operations. Militants killed in combat go in militant_killed.',
    },
    'official_source': {
        'group': 'G13 — Network/qualitative',
        'description': 'Official government/military source cited in the entry.',
        'type': 'text',
        'example': 'ISPR',
        'null_meaning': 'No',
        'values': {
            'ISPR': 'Inter-Services Public Relations — Pakistan Army media wing',
            'Deputy Commissioner': 'District DC cited as official source',
            'IGP Office': 'Inspector General of Police office',
            'SSP': 'Senior Superintendent of Police',
            'Police official (DSP/SSP)': 'Police official at DSP or SSP level',
            'Police official': 'Unnamed police official cited',
            'No': 'No official source cited',
        },
        'notes': '',
    },
    'surrender_event': {
        'group': 'G13 — Network/qualitative',
        'description': 'Whether this entry describes militants surrendering.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Militant(s) surrendered to authorities', 'No': 'Not a surrender event'},
        'notes': '',
    },
    'protest_or_sit_in': {
        'group': 'G13 — Network/qualitative',
        'description': 'Whether this entry involves a protest or sit-in.',
        'type': 'boolean',
        'example': 'Yes',
        'null_meaning': 'No',
        'values': {'Yes': 'Protest or sit-in described', 'No': 'No protest'},
        'notes': '',
    },
    'incident_summary': {
        'group': 'G13 — Network/qualitative',
        'description': '1-2 sentence paraphrase of the incident in plain English.',
        'type': 'text',
        'example': 'BLA Majeed Brigade fidayee Sangat Bahar Ali carried out a suicide attack on an FC convoy near Turbat, killing at least 11 SF.',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
    'group_statement_key_claim': {
        'group': 'G13 — Network/qualitative',
        'description': 'Core assertion from the militant group\'s official statement.',
        'type': 'text',
        'example': 'Our land will always remain insecure for the occupying state',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'strategic_significance': {
        'group': 'G13 — Network/qualitative',
        'description': 'Free text note on why this incident is strategically significant (new capability, escalation, first of a type).',
        'type': 'text',
        'example': 'Largest BLA-Azad operation since 2018 rift; 18 FC killed in Mangochar',
        'null_meaning': '-',
        'values': {},
        'notes': '',
    },
    'data_quality': {
        'group': 'G13 — Network/qualitative',
        'description': 'Reliability assessment of this entry\'s data.',
        'type': 'categorical',
        'example': 'High',
        'null_meaning': None,
        'values': {
            'High': 'Multiple sources confirmed; or ISPR/Dawn cited; named officials quoted',
            'Medium': 'Single quality source (Balochistan Post, Khorasan Diary) with no contradictions',
            'Low': 'Single-source ED entry; unconfirmed; "exact number not known"; no official confirmation',
        },
        'notes': 'All ED entries default to Low. ISPR-sourced IBO entries default to High.',
    },

    # ══════════════════════════════════════════════════════════════
    # OPERATION FIELDS (part of G3 but documented separately)
    # ══════════════════════════════════════════════════════════════

    'operation_name': {
        'group': 'G3 — Incident characteristics',
        'description': 'Named military operation if this entry is part of one.',
        'type': 'text',
        'example': 'Operation Herof',
        'null_meaning': '-',
        'values': {
            'Operation Herof': 'BLA multi-city offensive; Herof I (Aug 2024) and Herof II (Jan-Feb 2026)',
            'Operation Baam': 'BLA operation',
            'Operation Radd-ul-Fitna': 'SF counter-operation concluded Feb 5 2026',
            'Operation ZirPahazag': 'BLA operation targeting intelligence offices',
            'Operation Darra-e-Bolan': 'BLA Majeed Brigade operation Mach military HQ',
            'Operation Azm-e-Istehkam': 'National SF counter-terrorism campaign',
            '-': 'Not part of a named operation',
        },
        'notes': '',
    },
    'operation_phase_number': {
        'group': 'G3 — Incident characteristics',
        'description': 'Phase number within a multi-phase operation.',
        'type': 'text',
        'example': '2',
        'null_meaning': '-',
        'values': {'1': 'Phase 1', '2': 'Phase 2', '-': 'Not applicable'},
        'notes': '',
    },
    'operation_start_date': {'group': 'G3 — Incident characteristics', 'description': 'Start date of operation.', 'type': 'date', 'example': 'January 31', 'null_meaning': '-', 'values': {}, 'notes': ''},
    'operation_end_date': {'group': 'G3 — Incident characteristics', 'description': 'End date of operation.', 'type': 'date', 'example': 'February 6', 'null_meaning': '-', 'values': {}, 'notes': ''},
    'operation_duration_hours': {'group': 'G3 — Incident characteristics', 'description': 'Duration of operation in hours.', 'type': 'numeric', 'example': '144', 'null_meaning': '-', 'values': {}, 'notes': ''},
    'operation_cities_targeted': {'group': 'G3 — Incident characteristics', 'description': 'Cities or locations targeted in the operation.', 'type': 'text', 'example': '14 locations across Balochistan', 'null_meaning': '-', 'values': {}, 'notes': ''},
    'operation_stated_objective': {'group': 'G3 — Incident characteristics', 'description': 'Stated objective of the operation.', 'type': 'text', 'example': 'Test military coordination and readiness', 'null_meaning': '-', 'values': {}, 'notes': ''},
    'operation_claimed_outcome': {'group': 'G3 — Incident characteristics', 'description': 'Group\'s claimed outcome of the operation.', 'type': 'text', 'example': 'Group claims objectives achieved; 362 SF killed (BLA claim)', 'null_meaning': '-', 'values': {}, 'notes': ''},

    'num_attackers': {
        'group': 'G4 — Perpetrators',
        'description': 'Number of attackers mentioned in the source.',
        'type': 'text',
        'example': '80',
        'null_meaning': 'No',
        'values': {},
        'notes': '',
    },
}

# ── EXPORT FUNCTIONS ──────────────────────────────────────────────────────────

def export_markdown(output_path='codebook.md'):
    """Export codebook as a readable Markdown file."""
    lines = ['# Balochistan Incidents Dataset — Codebook\n\n']
    lines.append('This document describes every column in the dataset: what it means, what values it can contain, and how to interpret it.\n\n')
    lines.append('**Null value conventions:**\n')
    lines.append('- `-` = field not applicable to this incident type\n')
    lines.append('- `No` = field is applicable but information was not reported in the source\n\n')
    lines.append('---\n\n')

    # Group columns
    from collections import defaultdict
    groups = defaultdict(list)
    for col, meta in CODEBOOK.items():
        groups[meta['group']].append((col, meta))

    for group_name, cols in sorted(groups.items()):
        lines.append(f'## {group_name}\n\n')
        for col, meta in cols:
            lines.append(f'### `{col}`\n\n')
            lines.append(f'**Description:** {meta["description"]}\n\n')
            lines.append(f'**Type:** {meta["type"]}')
            if meta.get('format'):
                lines.append(f' | **Format:** {meta["format"]}')
            lines.append('\n\n')
            if meta.get('example'):
                lines.append(f'**Example:** `{meta["example"]}`\n\n')
            if meta.get('null_meaning'):
                lines.append(f'**When empty/null:** {meta["null_meaning"]}\n\n')
            if meta.get('values'):
                lines.append('**Allowed values:**\n\n')
                lines.append('| Value | Meaning |\n|---|---|\n')
                for val, meaning in meta['values'].items():
                    safe_meaning = meaning.replace('|','\\|')
                    lines.append(f'| `{val}` | {safe_meaning} |\n')
                lines.append('\n')
            if meta.get('notes'):
                lines.append(f'> **Note:** {meta["notes"]}\n\n')
            lines.append('---\n\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"✓ Markdown codebook written: {output_path}")

def export_csv_reference(output_path='codebook_reference.csv'):
    """Export codebook as a flat CSV for quick lookup."""
    import csv as csvlib
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csvlib.writer(f)
        writer.writerow(['column', 'group', 'type', 'description', 'example',
                         'null_meaning', 'allowed_values', 'notes'])
        for col, meta in CODEBOOK.items():
            allowed = '; '.join([f"{k}={v[:50]}" for k, v in meta.get('values', {}).items()])
            writer.writerow([
                col,
                meta.get('group', ''),
                meta.get('type', ''),
                meta.get('description', ''),
                meta.get('example', ''),
                meta.get('null_meaning', ''),
                allowed[:500],
                meta.get('notes', ''),
            ])
    print(f"✓ CSV reference codebook written: {output_path}")

def get_allowed_values():
    """Return dict of col -> list of allowed values. Used by schema.py and standardize.py."""
    result = {}
    for col, meta in CODEBOOK.items():
        if meta.get('values'):
            result[col] = list(meta['values'].keys())
    return result

if __name__ == '__main__':
    import sys
    if '--csv' in sys.argv:
        export_csv_reference('/mnt/user-data/outputs/codebook_reference.csv')
    else:
        export_markdown('/mnt/user-data/outputs/codebook.md')
        export_csv_reference('/mnt/user-data/outputs/codebook_reference.csv')
    print("Done.")


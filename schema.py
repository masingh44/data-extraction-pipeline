"""
schema_v6.py — Single source of truth for the Balochistan Incidents CSV schema.
Matches the column order and defaults of the Jan/Feb 2025 gold-standard CSVs.
"""

# ── COLUMN ORDER ─────────────────────────────────────────────────────────────
# Matches BAL_JAN2025_v5_1.csv / BAL_FEB2025_FinalV5_3.csv exactly (118 cols)

COLUMNS = [
    # G1 — Core identifiers
    'incident_id', 'date', 'month', 'year', 'original_description',
    # G2 — Location
    'district', 'town_area',
    # G3 — Incident characteristics
    'incident_type', 'attack_method', 'target_type', 'target_organization',
    'time_of_day',
    # G4 — Perpetrators (immediate)
    'perpetrator_group', 'claimed_responsibility',
    # G5 — Victims
    'named_victims', 'victim_profession',
    'victim_previous_disappearance', 'family_member_previously_targeted',
    # G6 — Enforced disappearances
    'is_enforced_disappearance', 'num_disappeared', 'disappeared_names',
    'disappearance_circumstances',
    # G7 — Casualties
    'sf_killed', 'sf_injured', 'sf_captured', 'sf_captured_names',
    'civilian_killed', 'civilian_injured',
    'militant_killed', 'militant_injured',
    'death_squad_killed', 'death_squad_injured',
    'informant_killed', 'informant_injured',
    'foreign_national_killed', 'hostages_taken',
    'group_claimed_sf_killed',
    # G8 — Flags
    'alleged_informant_killed', 'death_squad_targeted', 'num_attackers',
    'is_extrajudicial_killing', 'is_drone_strike_victim', 'paank_reported',
    'is_curfew_imposed', 'is_punitive_demolition',
    # G9 — Property / economic
    'property_damaged', 'property_type_damaged', 'economic_sector_targeted',
    'is_cpec_related', 'weapons_seized_by_attackers', 'weapons_recovered_by_sf',
    'cash_looted', 'infrastructure_disruption', 'govt_documents_destroyed',
    # G10 — Area seizure tactics
    'duration_militant_control_hours', 'entry_vehicles_count', 'entry_direction',
    'public_address_method', 'civilian_treatment_policy',
    # G11 — Prisoner
    'prisoner_exchange_event', 'prisoners_released_count',
    'prisoner_release_reason', 'captivity_duration_days',
    # G12 — Fidayee biography
    'fidayee_name', 'fidayee_codename', 'fidayee_dob', 'fidayee_gender',
    'fidayee_hometown', 'fidayee_year_joined_movement', 'fidayee_fronts_served',
    'fidayee_year_volunteered_fidayee', 'fidayee_family_background',
    'fidayee_education', 'fidayee_final_message_recorded',
    # G13 — Informant detail
    'informant_detained_date', 'informant_handler_named',
    'informant_alleged_methods', 'informant_network_size',
    'informant_network_members_named', 'informant_victims_named',
    'informant_occupation',
    # G14 — Aggregate report
    'reporting_organization', 'report_period_covered',
    'aggregate_attacks_reported', 'aggregate_disappeared_reported',
    'aggregate_killed_reported', 'aggregate_sf_killed_reported',
    'aggregate_sf_operations_reported',
    # G15 — Network / qualitative / metadata
    'sf_counter_op', 'sf_counter_op_type', 'sf_neutralized_count',
    'official_source',
    'surrender_event', 'protest_or_sit_in', 'data_quality',
    # G16 — Operation details
    'operation_name', 'operation_phase_number',
    'operation_start_date', 'operation_end_date', 'operation_duration_hours',
    'operation_cities_targeted', 'operation_stated_objective',
    'operation_claimed_outcome',
    # G17 — Coordination / group
    'is_coordinated', 'is_complex_attack', 'is_aggregate_report',
    'group_joining_event', 'inter_militant_conflict',
    'baloch_national_court_sentence',
    # G18 — Source / perpetrator detail
    'source', 'source_count',
    'perpetrator_unit', 'perpetrator_spokesperson',
    'intelligence_wing_cited', 'media_channel',
    'conflicting_claims', 'victim_political_affiliation',
    'disappeared_identifiers',
]

# ── DEFAULT VALUE CONVENTIONS ────────────────────────────────────────────────
# These match the gold-standard CSVs exactly.

# Columns that default to '-' (not applicable / not filled)
DASH_DEFAULT_COLS = {
    'sf_captured', 'sf_captured_names', 'hostages_taken',
    'sf_neutralized_count', 'num_attackers',
    'duration_militant_control_hours', 'entry_vehicles_count', 'entry_direction',
    'public_address_method', 'civilian_treatment_policy',
    'prisoner_exchange_event', 'prisoners_released_count',
    'prisoner_release_reason', 'captivity_duration_days',
    'fidayee_name', 'fidayee_codename', 'fidayee_dob', 'fidayee_gender',
    'fidayee_hometown', 'fidayee_year_joined_movement', 'fidayee_fronts_served',
    'fidayee_year_volunteered_fidayee', 'fidayee_family_background',
    'fidayee_education', 'fidayee_final_message_recorded',
    'informant_detained_date', 'informant_handler_named',
    'informant_alleged_methods', 'informant_network_size',
    'informant_network_members_named', 'informant_victims_named',
    'informant_occupation',
    'reporting_organization', 'report_period_covered',
    'aggregate_attacks_reported', 'aggregate_disappeared_reported',
    'aggregate_killed_reported', 'aggregate_sf_killed_reported',
    'aggregate_sf_operations_reported',
    'operation_name', 'operation_phase_number',
    'operation_start_date', 'operation_end_date', 'operation_duration_hours',
    'operation_cities_targeted', 'operation_stated_objective',
    'operation_claimed_outcome',
    'perpetrator_unit', 'intelligence_wing_cited', 'media_channel',
    'group_claimed_sf_killed', 'cash_looted',
    'victim_political_affiliation', 'disappeared_identifiers',
    'economic_sector_targeted', 'weapons_seized_by_attackers',
    'weapons_recovered_by_sf', 'property_type_damaged',
    'sf_counter_op_type',
}

# Columns that default to 'No' (boolean/categorical — not reported)
NO_DEFAULT_COLS = {
    'claimed_responsibility', 'named_victims', 'victim_profession',
    'victim_previous_disappearance', 'family_member_previously_targeted',
    'is_enforced_disappearance', 'num_disappeared', 'disappeared_names',
    'disappearance_circumstances',
    'alleged_informant_killed', 'death_squad_targeted', 'num_attackers',
    'is_extrajudicial_killing', 'is_drone_strike_victim', 'paank_reported',
    'is_curfew_imposed', 'is_punitive_demolition',
    'property_damaged', 'is_cpec_related',
    'infrastructure_disruption', 'govt_documents_destroyed',
    'sf_counter_op', 'surrender_event', 'protest_or_sit_in',
    'is_coordinated', 'is_complex_attack', 'is_aggregate_report',
    'group_joining_event', 'inter_militant_conflict',
    'baloch_national_court_sentence', 'conflicting_claims',
    'official_source', 'town_area', 'time_of_day',
    'perpetrator_spokesperson',
}

# Columns that default to '0' (numeric zero)
ZERO_DEFAULT_COLS = {
    'sf_killed', 'sf_injured', 'civilian_killed', 'civilian_injured',
    'militant_killed', 'militant_injured',
    'death_squad_killed', 'death_squad_injured',
    'informant_killed', 'informant_injured',
    'foreign_national_killed',
}

NULL_NOT_APPLICABLE = '-'
NULL_NOT_REPORTED = 'No'

# ── ALLOWED VALUES ────────────────────────────────────────────────────────────
ALLOWED_VALUES = {
    'incident_type': [
        'IED', 'Armed assault', 'Sniper', 'Suicide bombing',
        'Area seizure', 'Roadblock', 'Arson', 'Targeted killing',
        'Extrajudicial killing', 'Enforced disappearance', 'IBO',
        'Surrender', 'Protest/sit-in', 'Train attack', 'Prisoner capture',
        'Prisoner release', 'Aggregate report', 'Punitive demolition',
        'Armed robbery',
    ],
    'attack_method': [
        '-', 'Remote-controlled IED', 'VBIED', 'Motorcycle IED',
        'Person-borne IED', 'IED', 'Sniper', 'RPG', 'Rocket',
        'Grenade', 'Grenade launcher', 'Mortar', 'Rocket/Mortar',
        'Small arms', 'Heavy weapons', 'Arson', 'Drone', 'A-1 shell',
    ],
    'data_quality': ['High', 'Medium', 'Low'],
    'disappearance_circumstances': [
        '-', 'No', 'Raid on home', 'Raid on home (nighttime)',
        'Raid on home (daytime)', 'Returning Home', 'While travelling',
        'From shop/workplace', 'At military/police checkpoint',
        'Plainclothes agents', 'Plainclothes agents (public area)',
        'At airport/border crossing', 'From public gathering',
        'Raid on shop/business premises',
    ],
    'time_of_day': ['-', 'No', 'Morning', 'Afternoon', 'Evening', 'Night'],
    'perpetrator_group': [
        'BLA', 'BLF', 'BRG', 'BRA', 'BRAS', 'TTP', 'ISKP',
        'UBA', 'BLA-Azad', 'Security Forces', 'Unidentified',
        'Death squad (state-backed militia)',
        'Security Forces/intelligence agencies',
        'Unidentified (banned outfit)',
    ],
    'sf_counter_op_type': [
        '-', 'IBO', 'Border interception', 'Clearance/sanitization',
        'Cordon and search', 'Follow-up operation',
    ],
}

# Boolean Yes/No columns
BOOLEAN_COLUMNS = {
    'is_coordinated', 'is_complex_attack', 'is_aggregate_report',
    'claimed_responsibility', 'group_joining_event', 'inter_militant_conflict',
    'baloch_national_court_sentence', 'conflicting_claims',
    'victim_previous_disappearance', 'family_member_previously_targeted',
    'is_enforced_disappearance', 'is_extrajudicial_killing',
    'is_drone_strike_victim', 'paank_reported',
    'is_curfew_imposed', 'is_punitive_demolition',
    'property_damaged', 'is_cpec_related',
    'infrastructure_disruption', 'govt_documents_destroyed',
    'prisoner_exchange_event', 'alleged_informant_killed',
    'death_squad_targeted', 'sf_counter_op',
    'surrender_event', 'protest_or_sit_in',
}

# Non-attack types: attack_method = '-'
NON_ATTACK_TYPES = {
    'Enforced disappearance', 'Aggregate report', 'Surrender',
    'IBO', 'Protest/sit-in', 'Prisoner release', 'Armed robbery',
}

NUMERIC_COLUMNS = [
    'sf_killed', 'sf_injured', 'civilian_killed', 'civilian_injured',
    'militant_killed', 'militant_injured',
    'death_squad_killed', 'death_squad_injured',
    'informant_killed', 'informant_injured',
    'foreign_national_killed', 'source_count',
]

# ── DISTRICT LIST AND MAPPINGS ───────────────────────────────────────────────
# Complete Balochistan district list (as of 2025) plus user-recognized units

DISTRICTS = {
    'Awaran', 'Barkhan', 'Bolan', 'Chagai', 'Chaman', 'Dera Bugti',
    'Duki', 'Gwadar', 'Harnai', 'Hub', 'Jaffarabad', 'Jhal Magsi',
    'Kachhi', 'Kalat', 'Kech', 'Kharan', 'Khuzdar', 'Kohlu',
    'Lasbela', 'Loralai', 'Mastung', 'Musakhel', 'Naseerabad',
    'Nushki', 'Panjgur', 'Pishin', 'Qila Abdullah', 'Qila Saifullah',
    'Quetta', 'Sherani', 'Sibi', 'Sohbatpur', 'Surab', 'Washuk',
    'Zhob', 'Ziarat',
    # User-recognized sub-district units (used in gold CSVs)
    'Mashkay',
}

# Alias: PDF spelling → canonical name
DISTRICT_ALIASES = {
    'Killa Saifullah': 'Qila Saifullah',
    'Kila Abdullah': 'Qila Abdullah',
    'Killa Abdullah': 'Qila Abdullah',
    'Pishni': 'Gwadar',    # Pasni is in Gwadar District
    'Pasni': 'Gwadar',
    # NOTE: Bolan is NOT aliased to Kachhi — user treats them separately
}

# Sub-area / tehsil / town → parent district (fallback when no explicit "X District" in text)
AREA_TO_DISTRICT = {
    # Gwadar District
    'Pasni': 'Gwadar', 'Jiwani': 'Gwadar', 'Panwan': 'Gwadar',
    'Surbandan': 'Gwadar', 'Pishni': 'Gwadar',
    # Kech District
    'Turbat': 'Kech', 'Tump': 'Kech', 'Buleda': 'Kech',
    'Gwarkop': 'Kech', 'Gowarkop': 'Kech', 'Zamuran': 'Kech',
    'Hironk': 'Kech', 'Mand': 'Kech', 'Absar': 'Kech',
    'Gomazi': 'Kech', 'Mundi': 'Kech',
    'Kushk': 'Kech', 'Koshqalat': 'Kech',
    'Sangani Sar': 'Kech', 'Nasirabad': 'Kech',
    # Bolan District
    'Pir Ghaib': 'Bolan', 'Bibi Nani': 'Bolan',
    'Peergaib': 'Bolan',
    # Kachhi District
    'Dhadar': 'Kachhi', 'Kolpur': 'Kachhi',
    'Dahadar': 'Kachhi',
    # Dera Bugti District
    'Sui': 'Dera Bugti',
    # Khuzdar District
    'Zehri': 'Khuzdar', 'Gresha': 'Khuzdar',
    # Awaran District
    'Kolwah': 'Awaran', 'Jhao': 'Awaran',
    'Buzdad': 'Awaran', 'Rodkan': 'Awaran',
    'Malar Machi': 'Awaran',
    # Mashkay (user-recognized as separate)
    'Mashkay': 'Mashkay', 'Mashky': 'Mashkay',
    'Bandki': 'Mashkay', 'Sherin Gaz': 'Mashkay',
    'Bunduki': 'Mashkay',
    # Kalat District
    'Mangochar': 'Kalat', 'Togho Chhapar': 'Kalat',
    'Pandran': 'Kalat',
    # Harnai District
    'Shahrag': 'Harnai',
    # Panjgur District
    'Paroom': 'Panjgur', 'Parom': 'Panjgur',
    'Pulabad': 'Panjgur', 'Cheedgi': 'Panjgur',
    'Gramkan': 'Panjgur', 'Jaheen': 'Panjgur',
    # Mastung District
    'Kardigap': 'Mastung', 'Splinji': 'Mastung',
    # Quetta District
    'Sariab': 'Quetta', 'Brewery': 'Quetta', 'Gowalmandi': 'Quetta',
    'Isa Nagri': 'Quetta', 'Koila Phatak': 'Quetta',
    'Manu Jan Road': 'Quetta', 'Jail Road': 'Quetta',
    # Qila Abdullah District
    'Gulistan': 'Qila Abdullah',
    # Kharan District
    'Kullan': 'Kharan', 'Roteenko': 'Kharan',
    'Gowash': 'Kharan',
    # Nushki District
    'Hazdah Khol': 'Nushki', 'Zorabad': 'Nushki',
    # Chaman District
    'Chaman': 'Chaman',
    # Washuk District
    'Mashkel': 'Washuk',
    # Hub District
    'Hub': 'Hub', 'Hub Chowki': 'Hub',
    # Naseerabad District
    'Usta Mohammad': 'Naseerabad', 'Usta Muhammad': 'Naseerabad',
    # Barkhan District
    'Radkan': 'Barkhan',
    # Kohlu District
    'Londo Noy Shim': 'Kohlu',
    # Sibi District
    'Karmowad': 'Sibi',
}

NAMED_VICTIMS_NOISE = [
    r'^no\s+named\s+victims?',
    r'^unnamed\s+(?:sf|soldier|civilian|victim)',
    r'^\d+\s+unnamed',
    r'^no\s+casualties',
    r'^\(source\)',
    r'^no\b',
]

COLUMN_RULES = [
    (
        lambda r: r['incident_type'] in NON_ATTACK_TYPES and r['attack_method'] not in ['-', ''],
        'attack_method', '-',
        'Clear attack_method for non-attack entry types'
    ),
    (
        lambda r: r['incident_type'] == 'Aggregate report' and r['is_aggregate_report'] != 'Yes',
        'is_aggregate_report', 'Yes',
        'Set is_aggregate_report=Yes when incident_type=Aggregate report'
    ),
]

method_list = ["HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCSR",
                "LSCAB",
                "MET",
                'TCLP',
                "BEF",
                "SIO2",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP"]

method_list_directories = ["HG",
                "ALPHA",
                "GAMMA",
                "GFPC",
                "LSC",
                "MET",
                'TCLP',
                "BEF",
                "SIO2",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP"]

consumable_type_list = ['Reagent', 
                        'Tracer', 
                        'Standard', 
                        'LCS', 
                        'Equipment Consumable']

aliquot_unit_mapping = {
    'liter': 'L',
    'liters': 'L',
    'litre': 'L',
    'litres': 'L',
    'l': 'L',

    'milliliter': 'mL',
    'milliliters': 'mL',
    'ml': 'mL',

    'gram': 'g',
    'grams': 'g',
    'g': 'g',

    'kilogram': 'kg',
    'kilograms': 'kg',
    'kg': 'kg',

    'microgram': 'µg',
    'micrograms': 'µg',
    'ug': 'µg',
    'µg': 'µg',

    'percent': '%',
    '%': '%',

    'milligram': 'mg',
    'milligrams': 'mg',
    'mg': 'mg',

    'ppm': 'ppm',
    'ppb': 'ppb',

    'nanogram': 'ng',
    'nanograms': 'ng',
    'ng': 'ng',

    'µl': 'µL',
    'microliter': 'µL',
    'microliters': 'µL'
}

prepsheet_columns = {
    "HG": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ISOAM": ['Sample ID', 'Aliquot', 'Aliquot Units', "Am-243\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOTH": ['Sample ID', 'Aliquot', 'Aliquot Units', "Th-229\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber"],
    "ISOU": ['Sample ID', 'Aliquot', 'Aliquot Units', "U-232\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOPU": ['Sample ID', 'Aliquot', 'Aliquot Units', "Pu-238\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber", "Tracer\nRecovery\n(%)"],
    "GAMMA": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "APEX ID", "Gamma\nDET"],
    "GFPC": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "Carrier ID"],
    "LSCPU": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCSR": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCAB": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "MET (AF)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "MET (AQ)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "MET (SM)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "MET (SO)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    'TCLP': ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "BEF": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "SIO2": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    'FLUOR': ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "NH3": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "NO3": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "NO2": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "CRVI": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "CL": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "PH": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Sample\nTemp (°C)', 'Result', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "TSS": ['Sample ID', 'Aliquot', 'Aliquot Units', "Initial\nMass\n(g)", "Intermediate\nMass\n(g)", "Final\nMass\n(g)", "Total\nSolid\n(mg)", "Result", 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "TSP": ['Sample ID', 'Aliquot', 'Aliquot Units', "Initial\nMass\n(g)", "Intermediate\nMass\n(g)", "Final\nMass\n(g)", "Total\nSolid\n(mg)", "Result", 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst']
}

excel_template_field_locations = {
    'BEF.xlsx': {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "CL.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A15"},
    "CRVI.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A12"},
    "FLUOR.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A14"},
    "GFPC.xlsx": {"BatchID": "B3", "Matrix": "C4", "SampleID": "A7"},
    "GAMMA (AF).xlsx": {"BatchID": "B3", "Matrix": "B4", "SampleID": "A9"},
    "GAMMA (SO).xlsx": {"BatchID": "B3", "Matrix": "B4", "SampleID": "A9"},
    "GAMMA (AQ).xlsx": {"BatchID": "B3", "Matrix": "B4", "SampleID": "A9"}, 
    "HG (AQ).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "HG (SO).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "ISOAM.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "ISOPU.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "ISOTH.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "ISOU.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "LSCAB.xlsx": {"BatchID": "B3", "Matrix": "B4", "SampleID": "A8"}, 
    "LSCPU.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"}, 
    "LSCSR.xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"}, 
    "MET (AF).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "MET (AQ).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "MET (SM).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "MET (SO).xlsx": {"BatchID": "B3", "Matrix": "B5", "SampleID": "A8"},
    "NH3.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A12"},
    "NO2.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A12"},
    "NO3.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A13"},
    "PH.xlsx": {"BatchID": "B4", "Matrix": "", "SampleID": "A11"},
    "TCLP.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A15"},
    "TSP.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A7"},
    "TSS.xlsx": {"BatchID": "B3", "Matrix": "", "SampleID": "A6"}
}

wetchem_analyte_key = {
        "HG": "MERCURY", 
        "SIO2": "SILICA",
        "FLUOR": "FLUORIDE",
        "NH3": "AMMONIA",
        "NO3": "NITRATES",
        "NO2": "NITRITES",
        "CRVI": "CHROMIUM",
        "CL": "CHLORIDE",
        "PH": "PH",
        "TSS": "TSS",
        "TSP": "TSP",
        }

matrix_dependent_templates = ['GAMMA', 'MET', 'HG']

mass_units = ['ug', 'mg', 'g', 'kg']

volume_units = ['mL', 'L', 'Sample']

activity_units = ['pCi', 'Bq', 'DPM', 'CPM', 'APS']

rad_isotopes = [
    'AM-238', 'AM-241', 'AM-243',
    'CO-60', 'CS-137', 
    'PU-234', 'PU-236', 'PU-238', 'PU-239', 'PU-240', 'PU-241', 'PU-242', 'PU-243',
    'RA-224', 'RA-226', 'RA-228',
    'SR-90', 'TC-99',
    'TH-228', 'TH-229', 'TH-230', 'TH-232', 'TH-234',
    'U-232', 'U-233', 'U-234', 'U-235', 'U-236', 'U-238',
]

methods_qc = {"HG": ['BLK', 'LCS', 'DUP', 'MS'],
                "ISOAM": ['BLK', 'LCS', 'DUP'],
                "ISOTH": ['BLK', 'LCS', 'DUP'],
                "ISOU": ['BLK', 'LCS', 'DUP'],
                "ISOPU": ['BLK', 'LCS', 'DUP'],
                "GAMMA": ['BLK', 'LCS', 'DUP'],
                "GFPC": ['BLK', 'LCSA', 'LCSB', 'DUP'],
                "LSCPU": ['BLK', 'LCS', 'DUP'],
                "LSCSR": ['BLK', 'LCS', 'DUP'],
                "LSCAB": ['BLK', 'LCS', 'DUP'],
                "MET (AF)": ['BLK', 'LCS', 'LCSDUP'],
                "MET (AQ)": ['BLK', 'LCS', 'MS', 'MSDUP'],
                "MET (SM)": ['BLK', 'LCS', 'LCSDUP'],
                "MET (SO)": ['BLK', 'LCS', 'DUP', 'MS'],
                "TCLP": ['BLK', 'MS'],
                "BEF": ['BLK', 'LCS', 'DUP'],
                "SIO2": ['BLK', 'LCS', 'DUP'],
                "TSP": ['BLK', 'LCS', 'DUP'],
                'FLUOR': ['BLK', 'LCS', 'DUP'],
                "NH3": ['BLK', 'LCS', 'DUP'],
                "NO3": ['LCS', 'DUP'],
                "NO2": ['LCS', 'DUP'],
                "CRVI": ['BLK', 'LCS', 'DUP'],
                "CL": ['BLK', 'LCS', 'DUP'],
                "PH": ['DUP'],
                "TSS": ['BLK', 'LCS', 'DUP'],
                "TSP": ['BLK', 'LCS', 'DUP']}

sample_login_bool_cols = [
                "HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCSR",
                "LSCAB",
                "MET",
                "TCLP",
                "BEF",
                "SIO2",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP",
                "DQO"
            ]

chemistry_categories = {
            'Radiological Chemistry': ["ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCSR",
                "LSCAB"],
            'Elemental Analysis': ["MET",
                "BEF",
                "TCLP"],
            'Wet Chemistry': ["HG", 
                "SIO2",
                "FLUOR",
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP"]
        }

all_qc = ['ICB', 'ICSA', 'ICV', 'CCV', 'CCB', 'CAL', 'BLK', 'LCS-LOW', 'LCS-HIGH', 'LCSA', 'LCSB', 'LCSDUP', 'LCS', 'DUP', 'MSDUP', 'MS']

pdr_result_type_list = ['REG', 'BLK', 'LCS', 'LCS-LOW', 'LCS-HIGH', 'LCSA', 'LCSB', 'LCSDUP', 'DUP', 'MS', 'MSDUP', 'TRACER']

excel_result_type_order = ['BLK', 'LCS', 'LCSDUP', 'LCS-LOW', 'LCS-HIGH', 'LCSA', 'LCSB', 'MS', 'MSDUP', 'DUP', 'REG']

equipment_widgets = [
    'Equipment Type',
    'EquipmentID',
    'Serial Number',
    'Model',
    'Manufacturer',
    'Location',
    'Description',
    'Service Date',
    'Status',
    'Verification Required',
    'Verification Criteria'
]

equipment_verification = [
    'Refrigerator',
    'Oven',
    'Pipette',
    'Hot Block',
    'Thermometer',
    'DI Water System',
    'Analytical Balance',
    'Top-Loading Balance',
    'Micro-Balance',
    'Probe'
]

methods_codes_dict = {
    "HG": {"ANMCode": "CL245.1", "EXCode": "SL999"},
    "ISOAM": {"ANMCode": "A01R-AM", "EXCode": "SL005"},
    "ISOTH": {"ANMCode": "A01R-TH", "EXCode": "SL005"},
    "ISOU": {"ANMCode": "A01R-U", "EXCode": "SL015"},
    "ISOPU": {"ANMCode": "A01R-PU", "EXCode": "SL005"},
    "GAMMA": {"ANMCode": "GA01R", "EXCode": "SL003"},
    "GFPC": {"ANMCode": "E901", "EXCode": "SL018"},
    "LSCPU": {"ANMCode": "A01R-LSC", "EXCode": "SL044"},
    "LSCRa": {"ANMCode": "E904.0", "EXCode": "SL047"},
    "LSCAB": {"ANMCode": "SR486.0", "EXCode": "SL044"},
    "MET (SO)": {"ANMCode": "6020B", "EXCode": "SL035"},
    "MET (AQ)": {"ANMCode": "6020B", "EXCode": "SL036"},
    "MET (SM)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "MET (AF)": {"ANMCode": "6020B", "EXCode": "SL037"},
    'TCLP': {},
    "BEF": {"ANMCode": "E9110", "EXCode": "SL042"},
    "SIO2": {"ANMCode": "N7500", "EXCode": "SL999"},
    "TSP": {"ANMCode": "N0600", "EXCode": "SL053"},
    'FLUOR': {"ANMCode": "SM4500-F-C", "EXCode": "SL040"},
    "NH3": {"ANMCode": "E350.1", "EXCode": "SL039"},
    "NO3": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "NO2": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "CRVI": {"ANMCode": "C335.2", "EXCode": "SL051"},
    "CL": {"ANMCode": "C925.1", "EXCode": "SL050"},
    "PH": {"ANMCode": "SM4500-H", "EXCode": "SL024"},
    "TSS": {"ANMCode": "A2540D", "EXCode": "SL023"}
}

stable_methods = ['HG', 'MET', 'TCLP', 'BEF', 'SIO2', 'TSP', 'FLUOR', 'NH3', 'NO3', 'NO2', 'CRVI', 'CL', 'PH', 'TSS']

rad_methods = ['ISOAM', 'ISOPU', 'ISOTH', 'ISOU', 'GAMMA', 'GFPC', 'LSCPU', 'LSCSR', 'LSCAB']

internal_standards = ['BISMUTH', 'INDIUM', 'TERBIUM', 'SCANDIUM', 'YTTRIUM', 'LITHIUM']

rounding_key = {
    'GAMMA': 2,
    'MET': {'SM': 4, 'AF': 6, 'SO': 3, 'AQ': 3},
    'BEF': 4,
    'ISOAM': 3,
    'ISOPU': 3,
    'ISOTH': 3,
    'ISOU': 3,
    'LSCAB': 3,
    'LSCPU': 3,
    "GFPC": 3,
    'TCLP': 3,
    "SIO2": 3,
    "TSP": 3,
    'FLUOR': 3,
    "NH3": 3,
    "NO3": 3,
    "NO2": 3,
    "CRVI": 3,
    "CL": 3,
    "PH": 3,
    "TSS": 3,
    "HG": 3
}

EDD_columns = {
    'AFIID': 'string', # 'SLDA'
    'LOCID': 'string', # LocationID
    'LOGDATE': 'string', # SampleDate (DD-mmm-YYYY)
    'LOGTIME': 'string', # SampleTime (HHMM)
    'MATRIX': 'string', # Matrix
    'SBD': 'float', # None
    'SED': 'float', # None
    'SACODE': 'string', # Determine if a sample is QC or not. (Either 'QC' or 'NO')
    'SAMPNO': 'int', # None
    'LOGCODE': 'string', # ''
    'SMCODE': 'string', # ''
    'FLDSAMPID': 'string', # SampleID
    'COCID': 'string', # CoCID
    'COOLER': 'string', # ''
    'ABLOT': 'string', # ''
    'EBLOT': 'string', # ''
    'TBLOT': 'string', # ''
    'REMARKS': 'string', # ''
    'SDG': 'string', # SDG
    'LABCODE': 'string', # LabCode
    'ANMCODE': 'string', # ANMCode
    'EXMCODE': 'string', # EXMCode
    'LCHMETH': 'string', # ''
    'RUN_NUMBER': 'int', # Iteration
    'LABSAMPID': 'string', # SampleID
    'EXTDATE': 'string', # PrepDate (DD-mmm-YYYY)
    'EXTTIME': 'string', # PrepTime (HHMM)
    'LCHDATE': 'string', # ''
    'LCHTIME': 'string', # ''
    'LCHLOT': 'string', # ''
    'ANADATE': 'string', # AnalysisDate (DD-mmm-YYYY)
    'ANATIME': 'string', # AnalysisTime (HHMM)
    'ANALOT': 'string', # BatchID
    'LABLOTCTL': 'string', # BatchID
    'CALREFID': 'string', # ''
    'RTTYPE': 'string', # ''
    'BASIS': 'string', # ''
    'PARLABEL': 'string', # Analyte
    'PRCCODE': 'string', # ORG, MET, RN, STD
    'PARVQ': 'string', # Coded value qualifying the analytical results field (TR, ND, =)
    'PARVAL': 'float', # Result
    'PARUN': 'float', # ResultError
    'PRECISION_': 'int', # Number of digits after the decimal point for PARVAL
    'EXPECTED': 'float', # Target result for Spikes, Blanks, LCS
    'EVPREC': 'int', # Number of digits after decimal point for EXPECTED
    'MDL': 'float', # MDL
    'RL': 'float', # Reporting Limit
    'UNITS': 'string', # ResultUnits
    'VQ_1C': 'string', # ''
    'VAL_1C': 'float', # ''
    'FCVALPREC': 'int', # None
    'VQ_CONFIRM': 'string', # ''
    'VAL_CONFIRM': 'float', # None
    'CNFVALPREC': 'int', # None
    'DILUTION': 'float', # DilutionMultiplier/Factor (dont remember, 1 for anything that doesnt have one)
    'PRIME_DQT': 'string', # ''
    'PRIME_FLAG': 'string', # ''
    'LAB_DQT': 'string', # ''
    'LAB_QC_FLAG': 'string', # Flag
    'BEST_RESULT': 'string', # 'Y' yes because we always report the iteration with the best result
    'REASON_CODE': 'string', # ''
    'PERCENT_RECOVERY': 'float', # PercentRecovery
    'RPD': 'float', # RPD
    'UPPER_RPD': 'float', # RPD Upper Limit
    'UPPER_ACCURACY': 'float', # Upper limit for percent recovery
    'LOWER_ACCURACY': 'float', # Lower limit for percent recovery
    'SPIKE_ADDED': 'float', # Aliquot of spike (known value?)
    'SPIKE_ADDED_PREC': 'int', # None
    'VALCODE': 'string', # ''
    'TIC_NAME': 'string', # ''
    'RETENTION_TIME': 'string', # ''
    'LOD': 'float' # LOD
}
method_list = ["HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCRa",
                "LSCAB",
                "MET",
                'TCLP',
                "BEF",
                "SIO2",
                "TSP",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS"]

method_list_directories = ["HG",
                "ALPHA",
                "GAMMA",
                "GFPC",
                "LSC",
                "MET",
                'TCLP',
                "BEF",
                "SIO2",
                "TSP",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS"]

consumable_type_list = ['Reagent', 
                        'Tracer', 
                        'Standard', 
                        'LCS', 
                        'Equipment Consumable']

prepsheet_columns = {
    "HG": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ISOAM": ['Sample ID', 'Aliquot', 'Aliquot Units', "Am-243\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOTH": ['Sample ID', 'Aliquot', 'Aliquot Units', "Th-229\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber"],
    "ISOU": ['Sample ID', 'Aliquot', 'Aliquot Units', "U-232\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOPU": ['Sample ID', 'Aliquot', 'Aliquot Units', "Pu-238\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber", "Tracer\nRecovery\n(%)"],
    "GAMMA": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "APEX ID", "Gamma\nDET"],
    "GFPC": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "Carrier ID"],
    "LSCPU": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCRa": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
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
    "TSS": ['Sample ID', 'Aliquot', 'Aliquot Units', "Initial\nMass\n(g)", "Intermediate\nMass\n(g)", "Final\nMass\n(g)", "Total\nSolid\n(mg)", "Result", 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst']
}

matrix_dependent_templates = ['GAMMA', 'MET']

excel_template_field_locations = {
    "NH3.xlsx": {"BatchID":"B3", "SampleID":"A13"},
    "CRVI.xlsx": {"BatchID":"B3", "SampleID":"A16"},
    "FLUOR.xlsx": {"BatchID":"B3", "SampleID":"A16"},
    "GAMMA (AF).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GAMMA (SO).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GAMMA (AQ).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GFPC.xlsx": {"BatchID":"B1", "SampleID":"A5"},
    "MET (AF).xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "MET (AQ).xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "MET (SM).xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "MET (SO).xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "ISOAM.xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "ISOPU.xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "ISOTH.xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "ISOU.xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "LSCPU.xlsx": {"BatchID":"B3", "SampleID":"A8"},
    "LSCAB.xlsx": {"BatchID":"B2", "SampleID":"A6"},
    "NO3.xlsx": {"BatchID":"B3", "SampleID":"A14"},
    "NO2.xlsx": {"BatchID":"B3", "SampleID":"A14"},
    "PH.xlsx": {"BatchID":"B4", "SampleID":"A13"},
    "TCLP.xlsx": {"BatchID":"B3", "SampleID":"A15"},
    "TSS.xlsx": {"BatchID":"B3", "SampleID":"A7"},
}

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

methods_qc = {"HG": ['BLK', 'LCS', 'DUP'],
                "ISOAM": ['BLK', 'LCS', 'DUP'],
                "ISOTH": ['BLK', 'LCS', 'DUP'],
                "ISOU": ['BLK', 'LCS', 'DUP'],
                "ISOPU": ['BLK', 'LCS', 'DUP'],
                "GAMMA": ['BLK', 'LCS', 'DUP'],
                "GFPC": ['BLK', 'LCSA', 'LCSB', 'DUP'],
                "LSCPU": ['BLK', 'LCS', 'DUP'],
                "LSCRa": ['BLK', 'LCS', 'DUP'],
                "LSCAB": ['BLK', 'LCS', 'DUP'],
                "MET (AF)": ['BLK', 'LCS', 'LCSDUP'],
                "MET (AQ)": ['BLK', 'LCS', 'MS', 'MSDUP'],
                "MET (SM)": ['BLK', 'LCS', 'LCSDUP'],
                "MET (SO)": ['BLK', 'LCS', 'DUP', 'MS'],
                "BEF": ['BLK', 'LCS', 'DUP'],
                "SIO2": ['BLK', 'LCS', 'DUP'],
                "TSP": ['BLK', 'LCS', 'DUP'],
                'FLUOR': ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "NH3": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "NO3": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "NO2": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "CRVI": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "CL": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "PH": ['DUP'],
                "TSS": ['BLK', 'LCS', 'DUP']}

sample_login_bool_cols = [
                "HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCAB",
                "MET",
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
                "LSCAB"],
            'Elemental Analysis': ["MET",
                "BEF"],
            'Wet Chemistry': ["HG", 
                "SIO2",
                "FLUOR",
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",]
        }

all_qc = ['ICB', 'ICSA', 'ICV', 'CCV', 'CCB', 'CAL', 'BLK', 'LCS-LOW', 'LCS-HIGH', 'LCSA', 'LCSB', 'LCSDUP', 'LCS', 'DUP', 'MSDUP', 'MS']

pdr_result_type_list = ['REG', 'BLK', 'LCS', 'LCS-LOW', 'LCS-HIGH', 'LCSA', 'LCSB', 'LCSDUP', 'DUP', 'MS', 'MSDUP']

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
    "ISOAM": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOTH": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOU": {"ANMCode": "A01R", "EXCode": "SL015"},
    "ISOPU": {"ANMCode": "A01R", "EXCode": "SL005"},
    "GAMMA": {"ANMCode": "GA01R", "EXCode": "SL003"},
    "GFPC": {"ANMCode": "E901", "EXCode": "SL018"},
    "LSCPU": {"ANMCode": "A01R", "EXCode": "SL044"},
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

rad_methods = ['ISOAM', 'ISOPU', 'ISOTH', 'ISOU', 'GAMMA', 'GFPC', 'LSCPU', 'LSCRa', 'LSCAB']

method_list = ["FIMS",
                "ISOAm",
                "ISOTh",
                "ISOU",
                "ISOPu",
                "GammaSpec",
                "GAB",
                "LSCPu",
                "LSCRa",
                "LSCTotal",
                "ICPMS (Soil)",
                "ICPMS (Aqueous)",
                "ICPMS (Smear)",
                "ICPMS (Air Filter)",
                'TCLP',
                "Fluorescence",
                "XRD",
                "TSP",
                "Fluoride",
                "Ammonia",
                "Nitrates",
                "Nitrites",
                "Cyanide",
                "Chloride",
                "pH",
                "TSS"]

consumable_type_list = ['Reagent', 
                        'Tracer', 
                        'Standard', 
                        'LCS', 
                        'Equipment Consumable']

prepsheet_columns = {
    "FIMS": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ISOAm": ['Sample ID', 'Aliquot', 'Aliquot Units', "Am-243\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOTh": ['Sample ID', 'Aliquot', 'Aliquot Units', "Th-229\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber"],
    "ISOU": ['Sample ID', 'Aliquot', 'Aliquot Units', "U-232\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst',  "Alpha\nChamber"],
    "ISOPu": ['Sample ID', 'Aliquot', 'Aliquot Units', "Pu-238\n(g)", 'Analysis Date', 'Analysis Time', 'Analyst', "Alpha\nChamber", "Tracer\nRecovery\n(%)"],
    "GammaSpec": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "APEX ID", "Gamma\nDET"],
    "GAB": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "Carrier ID"],
    "LSCPu": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCRa": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCTotal": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ICPMS (Air Filter)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ICPMS (Aqueous)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ICPMS (Smear)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "ICPMS (Soil)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    'TCLP': ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Fluorescence": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "XRD": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Fluoride": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Ammonia": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Nitrates": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Nitrites": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Cyanide": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Chloride": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Result', 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "pH": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Sample\nTemp (°C)', 'Result', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "TSS": ['Sample ID', 'Aliquot', 'Aliquot Units', "Initial\nMass\n(g)", "Intermediate\nMass\n(g)", "Final\nMass\n(g)", "Total\nSolid\n(mg)", "Result", 'Result Units', 'Analysis Date', 'Analysis Time', 'Analyst']
}

mass_units = ['ug', 'mg', 'g', 'kg']

volume_units = ['mL', 'L', 'Sample']

activity_units = ['pCi', 'Bq', 'DPM', 'CPM', 'APS']

rad_isotopes = [
    'Am-237', 'Am-238', 'Am-239', 'Am-240', 'Am-241', 'Am-242', 'Am-243',
    'Pu-234', 'Pu-235', 'Pu-236', 'Pu-237', 'Pu-238', 'Pu-239', 'Pu-240', 
    'Pu-241', 'Pu-242', 'Pu-243', 'Pu-244',
    'Ra-223', 'Ra-224', 'Ra-225', 'Ra-226', 'Ra-227', 'Ra-228',
    'Th-227', 'Th-228', 'Th-229', 'Th-230', 'Th-231', 'Th-232', 'Th-233', 'Th-234',
    'U-232', 'U-233', 'U-234', 'U-235', 'U-236', 'U-237', 'U-238'
]

methods_qc = {"FIMS": ['BLK', 'LCS', 'DUP'],
                "ISOAm": ['BLK', 'LCS', 'DUP'],
                "ISOTh": ['BLK', 'LCS', 'DUP'],
                "ISOU": ['BLK', 'LCS', 'DUP'],
                "ISOPu": ['BLK', 'LCS', 'DUP'],
                "GammaSpec": ['BLK', 'LCS', 'DUP'],
                "GAB": ['BLK', 'LCSA', 'LCSB', 'DUP'],
                "LSCPu": ['BLK', 'LCS', 'DUP'],
                "LSCRa": ['BLK', 'LCS', 'DUP'],
                "LSCTotal": ['BLK', 'LCS', 'DUP'],
                "ICPMS (Air Filter)": ['BLK', 'LCS', 'LCSDUP'],
                "ICPMS (Aqueous)": ['BLK', 'LCS', 'MS', 'MSDUP'],
                "ICPMS (Smear)": ['BLK', 'LCS', 'LCSDUP'],
                "ICPMS (Soil)": ['BLK', 'LCS', 'DUP', 'MS'],
                "Fluorescence": ['BLK', 'LCS', 'DUP'],
                "XRD": ['BLK', 'LCS', 'DUP'],
                "TSP": ['BLK', 'LCS', 'DUP'],
                "Fluoride": ['BLK', 'LCS', 'DUP'],
                "Ammonia": ['BLK', 'LCS1', 'LCS2', 'DUP'],
                "Nitrates": ['BLK', 'LCS', 'DUP'],
                "Nitrites": ['BLK', 'LCS', 'DUP'],
                "Cyanide": ['BLK', 'LCS', 'DUP'],
                "Chloride": ['BLK', 'LCS', 'DUP'],
                "pH": ['BLK', 'LCS', 'DUP'],
                "TSS": ['BLK', 'LCS', 'DUP']}

all_qc = ['ICB', 'ICSA', 'ICV', 'CCV', 'CCB', 'CAL', 'BLK', 'LCS', 'LCS1', 'LCS2', 'LCSA', 'LCSB', 'LCSDUP', 'DUP', 'MS', 'MSDUP']

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
    "FIMS": {"ANMCode": "CL245.1", "EXCode": "SL999"},
    "ISOAm": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOTh": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOU": {"ANMCode": "A01R", "EXCode": "SL015"},
    "ISOPu": {"ANMCode": "A01R", "EXCode": "SL005"},
    "GammaSpec": {"ANMCode": "GA01R", "EXCode": "SL003"},
    "GAB": {"ANMCode": "E901", "EXCode": "SL018"},
    "LSCPu": {"ANMCode": "A01R", "EXCode": "SL044"},
    "LSCRa": {"ANMCode": "E904.0", "EXCode": "SL047"},
    "LSCTotal": {"ANMCode": "SR486.0", "EXCode": "SL044"},
    "ICPMS (Soil)": {"ANMCode": "6020B", "EXCode": "SL035"},
    "ICPMS (Aqueous)": {"ANMCode": "6020B", "EXCode": "SL036"},
    "ICPMS (Smear)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "ICPMS (Air Filter)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "Fluorescence": {"ANMCode": "E9110", "EXCode": "SL042"},
    "XRD": {"ANMCode": "N7500", "EXCode": "SL999"},
    "TSP": {"ANMCode": "N0600", "EXCode": "SL053"},
    "Fluoride": {"ANMCode": "SM4500-F-C", "EXCode": "SL040"},
    "Ammonia": {"ANMCode": "E350.1", "EXCode": "SL039"},
    "Nitrates": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "Nitrites": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "Cyanide": {"ANMCode": "C335.2", "EXCode": "SL051"},
    "Chloride": {"ANMCode": "C925.1", "EXCode": "SL050"},
    "pH": {"ANMCode": "SM4500-H", "EXCode": "SL024"},
    "TSS": {"ANMCode": "A2540D", "EXCode": "SL023"}
}
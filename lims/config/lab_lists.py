method_list = ["FIMS",
                "ISOAm",
                "ISOTh",
                "ISOU",
                "ISOPu",
                "GAMMA",
                "GFPC",
                "LSCPu",
                "LSCRa",
                "LSCTotal",
                "Metals",
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

method_list_directories = ["FIMS",
                "AlphaSpec",
                "GAMMA",
                "GFPC",
                "LSC",
                "Metals",
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
    "GAMMA": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "APEX ID", "Gamma\nDET"],
    "GFPC": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst', "Carrier ID"],
    "LSCPu": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCRa": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "LSCTotal": ['Sample ID', 'Aliquot', 'Aliquot Units', 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Metals (Air Filter)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Metals (Aqueous)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Metals (Smear)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
    "Metals (Soil)": ['Sample ID', 'Aliquot', 'Aliquot Units', "Filtered (y/n)", 'Analysis Date', 'Analysis Time', 'Analyst'],
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

matrix_dependent_templates = 'GAMMA', 'Metals'

excel_template_field_locations = {
    "Ammonia.xlsx": {"BatchID":"B3", "SampleID":"A13"},
    "Cyanide.xlsx": {"BatchID":"B3", "SampleID":"A16"},
    "Fluoride.xlsx": {"BatchID":"B3", "SampleID":"A16"},
    "GAMMA (Air Filter).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GAMMA (Soil).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GAMMA (Aqueous).xlsx": {"BatchID":"B1", "SampleID":"A7"},
    "GFPC.xlsx": {"BatchID":"B1", "SampleID":"A5"},
    "Metals (Aqueous).xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "Metals (Smear).xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "Metals (Soil).xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "Metals (Air Filter).xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "ISOAm.xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "ISOPu.xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "ISOTh.xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "ISOU.xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "LSCPu.xlsx": {"BatchID":"B3", "SampleID":"B8"},
    "LSCTotal.xlsx": {"BatchID":"B2", "SampleID":"A6"},
    "Nitrates.xlsx": {"BatchID":"B3", "SampleID":"A14"},
    "Nitrites.xlsx": {"BatchID":"B3", "SampleID":"A14"},
    "pH.xlsx": {"BatchID":"B4", "SampleID":"A13"},
    "TCLP.xlsx": {"BatchID":"B3", "SampleID":"A16"},
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

methods_qc = {"FIMS": ['BLK', 'LCS', 'DUP'],
                "ISOAm": ['BLK', 'LCS', 'DUP'],
                "ISOTh": ['BLK', 'LCS', 'DUP'],
                "ISOU": ['BLK', 'LCS', 'DUP'],
                "ISOPu": ['BLK', 'LCS', 'DUP'],
                "GAMMA": ['BLK', 'LCS', 'DUP'],
                "GFPC": ['BLK', 'LCSA', 'LCSB', 'DUP'],
                "LSCPu": ['BLK', 'LCS', 'DUP'],
                "LSCRa": ['BLK', 'LCS', 'DUP'],
                "LSCTotal": ['BLK', 'LCS', 'DUP'],
                "Metals (Air Filter)": ['BLK', 'LCS', 'LCSDUP'],
                "Metals (Aqueous)": ['BLK', 'LCS', 'MS', 'MSDUP'],
                "Metals (Smear)": ['BLK', 'LCS', 'LCSDUP'],
                "Metals (Soil)": ['BLK', 'LCS', 'DUP', 'MS'],
                "Fluorescence": ['BLK', 'LCS', 'DUP'],
                "XRD": ['BLK', 'LCS', 'DUP'],
                "TSP": ['BLK', 'LCS', 'DUP'],
                "Fluoride": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "Ammonia": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "Nitrates": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "Nitrites": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "Cyanide": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "Chloride": ['BLK', 'LCS-LOW', 'LCS-HIGH', 'DUP'],
                "pH": ['DUP'],
                "TSS": ['BLK', 'LCS', 'DUP']}

sample_login_bool_cols = [
                "FIMS",
                "ISOAm",
                "ISOTh",
                "ISOU",
                "ISOPu",
                "GAMMA",
                "GFPC",
                "LSCPu",
                "LSCTotal",
                "Metals",
                "Fluorescence",
                "XRD",
                "Fluoride",
                "Ammonia",
                "Nitrates",
                "Nitrites",
                "Cyanide",
                "Chloride",
                "pH",
                "TSS",
                "DQO"
            ]

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
    "FIMS": {"ANMCode": "CL245.1", "EXCode": "SL999"},
    "ISOAm": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOTh": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOU": {"ANMCode": "A01R", "EXCode": "SL015"},
    "ISOPu": {"ANMCode": "A01R", "EXCode": "SL005"},
    "GAMMA": {"ANMCode": "GA01R", "EXCode": "SL003"},
    "GFPC": {"ANMCode": "E901", "EXCode": "SL018"},
    "LSCPu": {"ANMCode": "A01R", "EXCode": "SL044"},
    "LSCRa": {"ANMCode": "E904.0", "EXCode": "SL047"},
    "LSCTotal": {"ANMCode": "SR486.0", "EXCode": "SL044"},
    "Metals (Soil)": {"ANMCode": "6020B", "EXCode": "SL035"},
    "Metals (Aqueous)": {"ANMCode": "6020B", "EXCode": "SL036"},
    "Metals (Smear)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "Metals (Air Filter)": {"ANMCode": "6020B", "EXCode": "SL037"},
    'TCLP': {},
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

stable_methods = ['FIMS', 'Metals', 'TCLP', 'Fluorescence', 'XRD', 'TSP', 'Fluoride', 'Ammonia', 'Nitrates', 'Nitrites', 'Cyanide', 'Chloride', 'pH', 'TSS']

rad_methods = ['ISOAm', 'ISOPu', 'ISOTh', 'ISOU', 'GAMMA', 'GFPC', 'LSCPu', 'LSCRa', 'LSCTotal']

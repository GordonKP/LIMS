import csv
import pandas as pd

# Alpha Spectroscopy ============================================================================================
def parse_alpha_file(file_path):
    data = []
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            row_type = row[0]

            if row_type == 'A':
                a = row

            elif row_type == 'B':
                b = row

            elif row_type == 'C':
                c = row
                row_data = {'A': a, 'B': b, 'C': c}
                data.append(row_data)

        columns = [
            "AlphaBatchID", "Detector", "AnalysisDateTime", "SampleDate", 
            "SampleAliquot", "SampleID", "ActivityUnits", 
            "MassUnits", "TracerAliquotGrams", "FileName", "PercentAbundance", 
            "MDAConfidenceFactor", "MDALLDConstant", "Matrix", 
            "EnergyCalibrationDateTime", "EfficiencyCalibrationDateTime", 
            "BackgroundFile", "TracerRecovery", "AlphaChamber", 
            "ChamberEfficiency", "AcquisitionDateTime", "ElapsedLiveTime", 
            "TracerFWHM", "NuclideName", "NetArea", "BackgroundArea", 
            "Activity", "Uncertainty", "MDC"
        ]
        
        # Initialize a list to store all sample rows
        sample_rows = []

        for sample in data:
            # Create the row by extracting values from the sample dictionary
            sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][9], sample['A'][10], 
            sample['A'][11], sample['A'][12], sample['A'][13], sample['A'][14], sample['A'][15], sample['A'][16], sample['B'][4], sample['B'][5], 
            sample['B'][6], sample['B'][8], sample['B'][10], sample['B'][11], sample['B'][12], sample['B'][13], sample['B'][14], sample['C'][4], sample['C'][5], 
            sample['C'][6], sample['C'][7], sample['C'][8], sample['C'][9]]

            sample_rows.append(sample_data)
        
        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        df.to_csv("ProcessedData//YI02_2024Sep26164858.csv", index=False)


parse_alpha_file("RawData//YI02_2024Sep26164858.res")
# Gamma Spectroscopy ============================================================================================
def parse_gamma_file(file_path):
    data = []
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            row_type = row[0]

            if row_type == 'A':
                a = row

            elif row_type == 'B':
                b = row

            elif row_type == 'C':
                c = row
                row_data = {'A': a, 'B': b, 'C': c}
                data.append(row_data)

        columns = [
            "SampleID", "Detector", "Geometry", "AcquisitionStartDateTime", 
            "AcquisitionEndDateTime", "Livetime", "EnergyDateTime", 
            "EfficiencyDate", 
            
            "SampleDateTime", "SampleSize", "SampleSizeUnits", 
            "ActivityUnits", "ErrorMultiplier", 
            
            "NuclideName", "NuclideDetected", "Activity", 
            "ActivityError", "MDA", "MDAError", 
            "ActivityMDARatio"
        ]

        # Initialize a list to store all sample rows
        sample_rows = []

        for sample in data:
            sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][7], sample['A'][8], 
            sample['B'][2], sample['B'][3], sample['B'][4], sample['B'][5], sample['B'][6], sample['C'][1], sample['C'][2], sample['C'][3], sample['C'][4], sample['C'][5], 
            sample['C'][6], sample['C'][7], ]

            sample_rows.append(sample_data)
        
        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        df.to_csv("ProcessedData//GAMMA_ND28AUG24_DET02.csv", index=False)


parse_gamma_file("RawData//GAMMA_ND28AUG24_DET02.csv")

# GFPC ============================================================================================
def parse_gfpc_file(file_path):
    data = []
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        data = []
        for row in reader:
            data.append(row)

        columns = [
            'SampleID', 'ResultType', 'Procedure', 'AcquisitionDateTime', 'AnalysisDate', 'DetectorSN', 'LiveTime', 'GrossAlphaActivityConcentration',
            'GrossAlphaActivityConcentrationError', 'GrossAlphaMDA', 'GrossAlphaAliquot', 'GrossAlphaEfficiencyfactor', 'GrossBetaActivityConcentration',
            'GrossBetaActivityConcentrationError', 'GrossBetaMDA', 'GrossBetaAliquot', 'GrossBetaEfficiencyfactor', 'AliquotUnits', 'EfficiencyCalibrationDateTime'
        ]

        # Initialize a list to store all sample rows
        sample_rows = []

        for sample in data:
            sample_data = [sample[0], sample[1], sample[2], sample[3], sample[4], sample[5], sample[6], sample[9], sample[11], sample[12], 
                           sample[13], sample[15], sample[21], sample[23], sample[24], sample[25], sample[27], sample[26], sample[28]]

            sample_rows.append(sample_data)
        
        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        df.to_csv("ProcessedData//GAB_XLB2BZ03_20240926134158.CSV", index=False)


parse_gfpc_file("RawData//GAB_XLB2BZ03_20240926134158.CSV")

# ICPMS ============================================================================================
import os
def convert_xlsx_to_csv(file_path):
    # Read the Excel file
    df = pd.read_excel(file_path)

    # Change the file extension from .xlsx to .csv
    csv_file_path = os.path.splitext(file_path)[0] + '.csv'

    # Save it as a CSV file
    df.to_csv(csv_file_path, index=False)

    return csv_file_path

def parse_gfpc_file(file_path):
    data = []

    if os.path.splitext(file_path)[1] == '.xlsx':
        file_path = convert_xlsx_to_csv(file_path)

    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        data = []
        for row in reader:
            data.append(row)

        columns = [
            'SampleID', 'SampleDateTime', 'DilutionFactor', 'Notes', 'FileName', 'ICPMSBatchID', 'FilePath', 'Analyst', 'Instrument', 'SampleWeightVolume', 'FinalWeightVolume',
            'DilutionMultiplier', 'ElementalSymbol', 'Element', 'Mass', 'ISTDRefMass', 'Concentration', 'ConcentrationRSD', 'CPSMean', 'CPSRep1', 'CPSRep2', 'CPSRep3', 
            'CPSRep4', 'CPSRep5', 'CPSRSD', 'Units'
        ]

        # Initialize a list to store all sample rows
        sample_rows = []

        for sample in data:
            sample_data = [sample[0], sample[1], sample[2], sample[3], sample[4], sample[5], sample[6], sample[7], sample[8], sample[9], 
                           sample[10], sample[11], sample[12], sample[13], sample[14], sample[15], sample[16], sample[17], sample[18], sample[19], 
                           sample[20], sample[21], sample[22], sample[23], sample[24], sample[25]]

            sample_rows.append(sample_data)
        
        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        df.to_csv("ProcessedData//24LL0995_ICPMS2_RawDataA.csv", index=False)


parse_gfpc_file("RawData//24LL0995_ICPMS2_RawDataA.xlsx")


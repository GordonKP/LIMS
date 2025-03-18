import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from packages.Prepsheet import GetPrepsheetData
from packages.DQO import MergeDQO
from packages.ResultType import GetResultType
from config.config import CONNECTION_STRING
from config.tables import (
    Base, ICPMSResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class ICPMSProcessor:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def parse_file(self, file_path):
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            data = []

            for row in reader:
                data.append(row)

            columns = ['SampleID', 'AnalysisDateTime', 'DilutionFactor', 'Notes', 'ICPMSFileName', 'ICPMSBatchName', 'ICPMSPath',
                       'Analyst', 'Instrument', 'SampleWeightVolume', 'FinalWeightVolume', 'DilutionMultiplier', 'Analyte', 'ElementName',
                       'Mass', 'ISTDRefMass', 'Result', 'ResultRSD', 'CPSMean', 'CPSRep1', 'CPSRep2', 'CPSRep3', 'CPSRep4', 'CPSRep5', 'CPSRSD', 'ResultUnits']
            
            sample_rows = []

            for row in data[1::]:
                sample_rows.append(row)

            print(sample_rows)
            
        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        df = self.create_df(df)

        processed_file_path = self.create_processed_file(df)

        df['ProcessedDataFilePath'] = processed_file_path

        self.upload_data(df)

        return df
    
    def create_processed_file(self, df):
        from config import file_paths
        method = df['Method'].unique()[0]
        batch_id = df['BatchID'].unique()[0]

        processed_data_parent_dir = file_paths.processed_data_directory

        target_parent_dir = os.path.join(processed_data_parent_dir, method)

        # Ensure directory exists
        os.makedirs(target_parent_dir, exist_ok=True)

        file_path = os.path.join(target_parent_dir, f"{batch_id}.csv")

        df.to_csv(file_path, index=False)

        return file_path
                    
    def create_df(self, df):
        # Convert the sample ID column to all caps where applicable, this is to accurately generate result type.
        df['SampleID'] = df['SampleID'].str.upper()

        df['Instrument'] = 'ICPMS'

        # ResultType 
        df = GetResultType.get_result_types(df)

        # Drop the ElementName column, combine Analyte and Mass
        df = df.drop(columns='ElementName')
        df['Analyte'] = df['Analyte']+'-'+df['Mass']
        df = df.drop(columns='Mass')

        sample_id = df[df['ResultType'] == 'REG'].iloc[0]['SampleID']

        print(sample_id)

        df = MergeDQO.get_icpms_dqo(sample_id, df)

        print(df)

        batch_id = df['BatchID'].unique()[0]

        # Get aliquot
        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # List of numeric columns that should be floats
        float_columns = [
            'SampleWeightVolume', 'FinalWeightVolume', 'DilutionMultiplier', 'DilutionFactor', 'ISTDRefMass', 'Result', 'CPSRSD', 'CPSMean', 
            'ResultRSD', 'Aliquot'
        ]

        datetime_columns = [
           'AnalysisDateTime', 'AnalysisDateTime'
        ]

        import numpy as np

        for col in float_columns:
            print(col)
            if col in df.columns:
                df[col] = df[col].replace('', 0)
                df[col] = df[col].replace('N/A', 0)
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
                     
    def upload_data(self, df):
        try:
            self.init_session()

            rejected_samples = []

            for index, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()

                # Set default iteration and reporting values
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True) 

                record = ICPMSResults(**row_dict)

                rep_columns = [f'CPSRep{i}' for i in range(1, 6)]

                rejected_count = sum(1 for col in rep_columns if row_dict.get(col, '').upper() == 'REJECTED')

                if rejected_count > 2:
                    reject_info = [row_dict['SampleID'], row_dict['ICPMSFileName'], row_dict['ICPMSBatchName'], row_dict['Analyte']]
                    rejected_samples.append(reject_info)
                    
                # Check if record already exists
                existing_record = self.session.query(ICPMSResults).filter(
                    ICPMSResults.SDG == record.SDG,
                    ICPMSResults.BatchID == record.BatchID,
                    ICPMSResults.SampleID == record.SampleID,
                    ICPMSResults.Analyte == record.Analyte,
                    ICPMSResults.Reporting == record.Reporting
                ).first()

                # If the record exists
                if existing_record:
                    # Check for exact match, if so do nothing
                    if existing_record:
                        if self.objects_are_identical(record, existing_record, ignore_fields=["Iteration"]):
                            print("Identical row exists (ignoring Iteration), continuing...")
                            continue  # Skip insertion
                    else:
                        print("Non-identical record exists, adding new iteration...")
                        # Set iteration to existing_record iteration + 1
                        record.Iteration = existing_record.Iteration + 1
        
                        # Set existing_record.Reporting to False
                        existing_record.Reporting = False

                        # Update the existing record in the database
                        self.session.add(existing_record)

                self.session.add(record)
                self.session.commit()

            if rejected_samples:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Rejections Detected")
                text = ""

                for sample_row in rejected_samples:
                    row_str = ", ".join(sample_row)
                    row_text = f"{row_str}\n"
                    text += row_text

                msg.setText(f"{text}\nContains more than two CPS Rep Rejections. Would you like to proceed?")

                # Add Yes and No buttons
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)

                result = msg.exec_()

                if result == QMessageBox.Yes:
                    self.session.commit()
                    print(f"Successfully committed results!")
                else:
                    self.session.rollback()
                    print(f"Results not committed.")

        except Exception as e:
            print(f"An exception occurred: {e}")
            self.session.rollback()
        finally:
            self.session.close()

    def objects_are_identical(self, obj1, obj2, ignore_fields=None):
        from sqlalchemy.inspection import inspect

        if ignore_fields is None:
            ignore_fields = []

        obj1_dict = {c.key: getattr(obj1, c.key) for c in inspect(obj1).mapper.column_attrs if c.key not in ignore_fields}
        obj2_dict = {c.key: getattr(obj2, c.key) for c in inspect(obj2).mapper.column_attrs if c.key not in ignore_fields}

        if obj1_dict != obj2_dict:
            print("\nMISMATCH DETECTED:")
            for key in obj1_dict.keys():
                if obj1_dict[key] != obj2_dict[key]:
                    print(f"  🔹 Column: {key}")
                    print(f"     Record: {obj1_dict[key]}")
                    print(f"     Existing: {obj2_dict[key]}\n")
            return False

        return True  # No mismatches found
         
processor = ICPMSProcessor()

df = processor.parse_file(file_path)
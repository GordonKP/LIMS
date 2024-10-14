import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Date, Float, DateTime, desc, and_
from sqlalchemy.orm import sessionmaker, declarative_base
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
import numpy as np
import re

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

head, tail = os.path.split(file_path)

instrument_type = os.path.basename(head)
file_name =  os.path.splitext(tail)[0]
file_name = f"{file_name}.csv"

destination_path = os.path.join(parentdir, "Processed Data", instrument_type, file_name)

Base = declarative_base()

class GABResults(Base):
    __tablename__ = 'GABResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(50))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True)
    Procedure = Column(String(100))                                     # Procedure
    AcquisitionDateTime = Column(DateTime)                              # Date Received
    AnalysisDateTime = Column(DateTime)                                 # Analysis Date
    DetectorSN = Column(String(50))                                     # Detector Serial Number
    LiveTime = Column(Float)                                            # Live time in seconds
    ActivityConcentration = Column(Float)                     # Alpha Concentration
    ActivityConcentrationError = Column(Float)                # Alpha Concentration error
    MDA = Column(Float)                                       # Alpha Minimum Detectable Amount
    Aliquot = Column(Float)                                   # Alpha Aliquot
    EfficiencyFactor = Column(Float)                          # Alpha Efficiency Factor
    AliquotUnits = Column(String(50))                                   # Aliquot Units
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Activity to MDA ratio
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class DQO(Base):
    __tablename__ = "DQO"

    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))

class GABProcessor:
    def __init__(self):
        self.session = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def upload_to_database(self, df):
        method = 'GAB'
        
        try:
            self.init_session()  # Make sure session initialization is done correctly

            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Check if the record exists in the database
                existing_record = self.session.query(GABResults).filter(
                    and_(
                        GABResults.SampleID == row['SampleID'],
                        GABResults.Method == method,
                        GABResults.Analyte == row['Analyte']
                    )
                ).order_by(desc(GABResults.Iteration)).first()

                error_samples = []

                # Regex pattern for finding the result type
                pattern = r"24LLB\d{4}([A-Za-z]+.*)"

                # Search for the pattern in the sample ID
                match = re.search(pattern, row['SampleID'])

                if match:
                    result_type = match.group(1)
                else:
                    result_type = 'REG'

                if existing_record:
                    print("RECORD EXISTS")
                    # If the record exists, increment Iteration and add new data
                    new_iteration = existing_record.Iteration + 1

                    new_row_data = {column: row[column] for column in df.columns}
                    new_row_data['Iteration'] = new_iteration
                    new_row_data['BatchID'] = existing_record.BatchID  # Carry forward BatchID
                    new_row_data['SDG'] = existing_record.SDG  # Carry forward SDG
                    new_row_data['Reporting'] = True  # Set reporting to True
                    new_row_data['Method'] = method
                    new_row_data['Matrix'] = existing_record.Matrix
                    new_row_data['ResultType'] = result_type

                    # Log data to be inserted
                    print(f"Inserting new record with iteration {new_iteration} for SampleID {row['SampleID']}")

                    # Create a new record instead of updating the existing one
                    new_record = GABResults(**new_row_data)
                    self.session.add(new_record)

                else:
                    # Find the batch id and sdg
                    query = self.session.query(DQO).filter(
                        and_(DQO.Method == method,
                             DQO.SampleID == row['SampleID'])
                    ).first()

                    if not query:
                        error_samples.append(row['SampleID'])
                        continue

                    # If no existing record, update the row data in the database
                    new_row_data = {column: row[column] for column in df.columns}
                    new_row_data['Iteration'] = 1  # Set Iteration to 1 for new records
                    new_row_data['Reporting'] = True
                    new_row_data['SampleID'] = query.SampleID
                    new_row_data['BatchID'] = query.BatchID
                    new_row_data['SDG'] = query.SDG
                    new_row_data['Method'] = method
                    new_row_data['Matrix'] = query.Matrix
                    new_row_data['ResultType'] = result_type

                    # Log the update operation
                    print(f"Adding record for SampleID {row['SampleID']} with Iteration 1")

                    new_record = GABResults(**new_row_data)
                    self.session.add(new_record)

                # Commit after all inserts/updates are executed
                self.session.commit()

            if error_samples:
                error_samples_str = ", ".join(error_samples)

        except Exception as e:
            print(f"Upload failed: {e}")
            self.session.rollback()  # Rollback in

    def parse_gab_file(self, file_path):
        data = []
        # Initialize a list to store all sample rows
        sample_rows = []
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                data.append(row)

            columns = ['SampleID', 'Analyte', 'Procedure', 'AcquisitionDateTime', 'AnalysisDateTime', 'DetectorSN', 'LiveTime', 'ActivityConcentration', 'ActivityConcentrationError', 'MDA', 'Aliquot', 'EfficiencyFactor', 'AliquotUnits', 'EfficiencyCalibrationDateTime']

            for sample in data:
                alpha_sample_data = [sample[0], "GrossAlpha", sample[2], sample[3], sample[4], sample[5], sample[6], sample[9], sample[11], sample[12], 
                            sample[13], sample[15], sample[26], sample[28]]
                
                beta_sample_data = [sample[0], "GrossBeta", sample[2], sample[3], sample[4], sample[5], sample[6], sample[21], sample[23], sample[24], 
                            sample[25], sample[27], sample[26], sample[28]]

                sample_rows.append(alpha_sample_data)
                sample_rows.append(beta_sample_data)

            df = pd.DataFrame(sample_rows, columns=columns)

            float_columns = ['LiveTime', 'ActivityConcentration',
                'ActivityConcentrationError', 'MDA', 'Aliquot', 'EfficiencyFactor', 'ActivityConcentration']

            # Check the DataFrame before any conversion
            print("DataFrame before float conversion:")
            print(df.head())  # Print a small portion of the DataFrame
            print(df.dtypes)  # Print the current data types of each column

            # List of columns you're trying to convert to float
            float_columns = ['LiveTime', 'ActivityConcentration', 'ActivityConcentrationError', 'MDA', 'Aliquot', 'EfficiencyFactor']

            # Debug: Check if the columns exist and their current data
            for col in float_columns:
                if col not in df.columns:
                    print(f"Column {col} does not exist in the DataFrame.")
                else:
                    print(f"Data in column {col} before conversion:")
                    print(df[col].head())  # Print a small portion of the column data

            try:
                # Remove commas and convert to float
                df['LiveTime'] = df['LiveTime'].str.replace(',', '').astype(float)
                df[float_columns] = df[float_columns].apply(pd.to_numeric, errors='coerce')
                df[float_columns] = df[float_columns].replace({pd.NA: None, np.nan: None})
                print("Conversion successful. DataFrame after conversion:")
                print(df.head())  # Check the DataFrame after conversion
            except Exception as e:
                print(f"Error during conversion: {e}")

            df.to_csv(destination_path, index=False)

            return df

processor = GABProcessor()

df = processor.parse_gab_file(file_path)

processor.upload_to_database(df)
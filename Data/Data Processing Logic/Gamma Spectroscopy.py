import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_
from sqlalchemy.orm import sessionmaker, declarative_base
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
import re

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

head, tail = os.path.split(file_path)

instrument_type = os.path.basename(head)
file_name =  os.path.splitext(tail)[0]
file_name = f"{file_name}.csv"

destination_path = os.path.join(parentdir, "Processed Data", instrument_type, file_name)

Base = declarative_base()

class GammaSpecResults(Base):
    __tablename__ = 'GammaSpecResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(20), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(50))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Detector = Column(String(50))                                       # Detector ID
    Geometry = Column(String(50))                                       # Geometry type
    AcquisitionStartDateTime = Column(DateTime)                         # Acquisition Start Date and Time
    AnalysisDateTime = Column(DateTime)                           # Acquisition End Date and Time
    Livetime = Column(Integer)                                          # Livetime in seconds
    EnergyDateTime = Column(DateTime)                                   # Energy Calibration Date and Time
    EfficiencyDateTime = Column(DateTime)                               # Efficiency Calibration Date and Time
    SampleDateTime = Column(DateTime)                                   # Sample Date and Time
    SampleSize = Column(Float)                                          # Size of the sample
    SampleSizeUnits = Column(String(20))                                # Units for sample size
    ActivityUnits = Column(String(10))                                  # Units for activity measurement
    ErrorMultiplier = Column(Integer)                                   # Error multiplier
    Analyte = Column(String(50), primary_key=True)                  # Name of the nuclide
    NuclideDetected = Column(String(3))                                 # Whether the nuclide was detected ("YES" or "NO")
    Activity = Column(Float)                                            # Activity value
    ActivityError = Column(Float)                                       # Activity error
    MDA = Column(Float)                                                 # Minimum detectable activity (MDA)
    MDAError = Column(Float)                                            # MDA error
    ActivityMDARatio = Column(Float)                                    # Activity to MDA ratio
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class DQO(Base):
    __tablename__ = "DQO"

    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))

class GammaSpecProcessor:
    def __init__(self):
        self.session = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def upload_to_database(self, df):
        method = 'GammaSpec'
        
        try:
            self.init_session()  # Make sure session initialization is done correctly

            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Check if the record exists in the database
                existing_record = self.session.query(GammaSpecResults).filter(
                    and_(
                        GammaSpecResults.SampleID == row['SampleID'],
                        GammaSpecResults.Method == method,
                        GammaSpecResults.Analyte == row['Analyte']
                    )
                ).order_by(desc(GammaSpecResults.Iteration)).first()

                error_samples = []

                # Regex pattern for finding the result type
                pattern = r"\d{2}LLB\d{4}([A-Za-z]+.*)"

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
                    new_record = GammaSpecResults(**new_row_data)
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

                    new_record = GammaSpecResults(**new_row_data)
                    self.session.add(new_record)

                # Commit after all inserts/updates are executed
                self.session.commit()

            if error_samples:
                error_samples_str = ", ".join(error_samples)
                QMessageBox.critical(self, "Error, samples not found in DQO, check to make sure the Batch exists.:", f"\n{error_samples_str}")

        except Exception as e:
            print(f"Upload failed: {e}")
            self.session.rollback()  # Rollback in

    def parse_gamma_file(self, file_path):
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
                "AnalysisDateTime", "Livetime", "EnergyDateTime", 
                "EfficiencyDateTime", 
                
                "SampleDateTime", "SampleSize", "SampleSizeUnits", 
                "ActivityUnits", "ErrorMultiplier", 
                
                "Analyte", "NuclideDetected", "Activity", 
                "ActivityError", "MDA", "MDAError", 
                "ActivityMDARatio"
            ]

            # Initialize a list to store all sample rows
            sample_rows = []

            for sample in data:
                sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][7], sample['A'][8], 
                sample['B'][2], sample['B'][3], sample['B'][4], sample['B'][5], sample['B'][6], sample['C'][1], sample['C'][2], sample['C'][3], sample['C'][4], sample['C'][5], 
                sample['C'][6], sample['C'][7]]

                sample_rows.append(sample_data)
            
            df = pd.DataFrame(sample_rows, columns=columns)

            print(df)

            df.to_csv(destination_path, index=False)

            return df

processor = GammaSpecProcessor()

df = processor.parse_gamma_file(file_path)

processor.upload_to_database(df)
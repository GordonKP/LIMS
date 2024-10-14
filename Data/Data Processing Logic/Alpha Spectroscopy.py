import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_, Date, Time
from sqlalchemy.orm import sessionmaker, declarative_base
import re
    
basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

head, tail = os.path.split(file_path)

instrument_type = os.path.basename(head)
file_name =  os.path.splitext(tail)[0]
file_name = f"{file_name}.csv"

destination_path = os.path.join(parentdir, "Processed Data", instrument_type, file_name)

Base = declarative_base()

class AlphaSpecResults(Base):
    __tablename__ = 'AlphaSpecResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    AlphaBatchID = Column(String(10))                                   # Batch identifier
    Detector = Column(String(50))                                       # Detector name or ID
    AnalysisDateTime = Column(DateTime)                                 # Date and time of the analysis
    SampleDate = Column(DateTime)                                       # Date of the sample collection
    SampleAliquot = Column(Float)                                       # Aliquot of the sample
    ActivityUnits = Column(String(10))                                  # Units of activity
    MassUnits = Column(String(10))                                      # Units of mass
    TracerAliquotGrams = Column(Float)                                  # Aliquot grams for the tracer
    FileName = Column(String(255))                                      # File name of the corresponding data file
    PercentAbundance = Column(Float)                                    # Percent abundance
    MDAConfidenceFactor = Column(Float)                                 # Confidence factor for MDA
    MDALLDConstant = Column(Integer)                                    # Constant value for MDA LLD
    EnergyCalibrationDateTime = Column(DateTime)                        # Date and time of energy calibration
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Date and time of efficiency calibration
    BackgroundFile = Column(String(255))                                # Path to the background file
    TracerRecovery = Column(Float)                                      # Tracer recovery value
    AlphaChamber = Column(String(50))                                   # Chamber identifier for alpha analysis
    ChamberEfficiency = Column(Float)                                   # Efficiency of the chamber
    AcquisitionDateTime = Column(DateTime)                              # Acquisition date and time
    ElapsedLiveTime = Column(Float)                                     # Elapsed live time
    TracerFWHM = Column(Float)                                          # Tracer full width at half maximum
    Analyte = Column(String(50), primary_key=True)                  # Name of the nuclide
    NetArea = Column(Float)                                             # Net area
    BackgroundArea = Column(Float)                                      # Background area
    Activity = Column(Float)                                            # Activity value
    Uncertainty = Column(Float)                                         # Uncertainty in the activity measurement
    MDC = Column(Float)                                                 # Minimum detectable concentration
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class SampleLogin(Base):
    __tablename__ = 'SampleLogin'

    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Matrix = Column('Matrix', String(12))
    ISORa = Column('ISORa', Boolean)
    ISOTh = Column('ISOTh', Boolean)
    ISOU = Column('ISOU', Boolean)
    GAB = Column('GAB', Boolean)
    Metals = Column('Metals', Boolean)
    GammaSpec = Column('GammaSpec', Boolean)
    Fluoride = Column('Fluoride', Boolean)
    TSS = Column('TSS', Boolean)
    pH = Column('pH', Boolean)
    NH3 = Column('NH3', Boolean)
    SampleVolume = Column('SampleVolume', Float)
    CPM = Column('CPM', Integer)
    Counts = Column('Counts', Integer)
    FirstPriority = Column('FirstPriority', Boolean)
    TimeBackCorrected = Column('TimeBackCorrected', Boolean)
    DateReceived = Column('DateReceived', Date)
    TimeReceived = Column('TimeReceived', Time(2))
    ReceivedBy = Column('ReceivedBy', String(20))
    LocationID = Column('LocationID', String(50))
    Container = Column('Container', String(4))
    Date = Column('Date', Date)
    Time = Column('Time', Time(2))
    DQO = Column('DQO', Boolean)

class DQO(Base):
    __tablename__ = "DQO"

    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))

class AlphaSpecProcessor:
    def __init__(self):
        self.session = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def upload_to_database(self, df):
        # Find the method
        nuclide_name = df['Analyte'].iloc[0]
        df['MDALLDConstant'] = pd.to_numeric(df['MDALLDConstant'], errors='coerce').fillna(0).astype(int)

        if 'TH' in nuclide_name.upper():
            method = 'ISOTh'
        elif 'RA' in nuclide_name.upper():
            method = 'ISORa'
        elif 'U' in nuclide_name.upper():
            method = 'ISOU'
        else:
            method = ''

        try:
            self.init_session()  # Make sure session initialization is done correctly

            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Check if the record exists in the database
                existing_record = self.session.query(AlphaSpecResults).filter(
                    and_(
                        AlphaSpecResults.SampleID == row['SampleID'],
                        AlphaSpecResults.Method == method,
                        AlphaSpecResults.Analyte == row['Analyte']
                    )
                ).order_by(desc(AlphaSpecResults.Iteration)).first()

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
                    new_record = AlphaSpecResults(**new_row_data)
                    self.session.add(new_record)

                else:
                    print("RECORD DOES NOT EXIST")
                    # Find the batch id and sdg
                    query = self.session.query(DQO).filter(
                        and_(DQO.Method == method,
                             DQO.SampleID == row['SampleID'])
                    ).first()

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

                    new_record = AlphaSpecResults(**new_row_data)
                    self.session.add(new_record)

                # Commit after all inserts/updates are executed
                self.session.commit()

        except Exception as e:
            print(f"Upload failed: {e}")
            self.session.rollback()  # Rollback in

    def parse_alpha_file(self, file_path):
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
                "MDAConfidenceFactor", "MDALLDConstant", 
                "EnergyCalibrationDateTime", "EfficiencyCalibrationDateTime", 
                "BackgroundFile", "TracerRecovery", "AlphaChamber", 
                "ChamberEfficiency", "AcquisitionDateTime", "ElapsedLiveTime", 
                "TracerFWHM", "Analyte", "NetArea", "BackgroundArea", 
                "Activity", "Uncertainty", "MDC"
            ]
            
            # Initialize a list to store all sample rows
            sample_rows = []

            for sample in data:
                # Create the row by extracting values from the sample dictionary
                sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][9], sample['A'][10], 
                sample['A'][11], sample['A'][12], sample['A'][13], sample['A'][14], sample['A'][15], sample['B'][4], sample['B'][5], 
                sample['B'][6], sample['B'][8], sample['B'][10], sample['B'][11], sample['B'][12], sample['B'][13], sample['B'][14], sample['C'][4], sample['C'][5], 
                sample['C'][6], sample['C'][7], sample['C'][8], sample['C'][9]]

                sample_rows.append(sample_data)
            
            df = pd.DataFrame(sample_rows, columns=columns)

            print(df)

            df.to_csv(destination_path, index=False) 

            return df

processor = AlphaSpecProcessor()

df = processor.parse_alpha_file(file_path)

processor.upload_to_database(df)
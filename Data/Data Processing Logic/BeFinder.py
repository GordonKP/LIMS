import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_, Date, Time
from sqlalchemy.orm import sessionmaker, declarative_base
import re
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
    
basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

file_path = r"Data\Raw Data\BeFinder\24LLB0001.xlsx"

head, tail = os.path.split(file_path)

instrument_type = os.path.basename(head)
file_name =  os.path.splitext(tail)[0]
file_name = f"{file_name}.csv"

destination_path = os.path.join(parentdir, "Processed Data", instrument_type, file_name)

Base = declarative_base()

class BeFinderResults(Base):
    __tablename__ = 'BeFinderResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    AnalysisDateTime = Column(DateTime)                                 # Date and time of the analysis
    SampleDate = Column(DateTime)                                       # Date of the sample collection
    FileName = Column(String(255))                                      # File name of the corresponding data file
    AcquisitionDateTime = Column(DateTime)                              # Acquisition date and time
    Counts = Column(Float)                                              # Counts value
    Units = Column(String(10))                                          # Counts Units
    PPB = Column(Float)                                                 # Parts per billion
    MicroGrams = Column(Float)                                          # Micrograms per 100cm^2 
    Recovery = Column(Float)
    RelativeDifference = Column(Float)
    DataValidation = Column(String)
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

class BeFinderProcessor:
    def __init__(self):
        self.session = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def upload_to_database(self, df):
        try:
            self.init_session()  # Make sure session initialization is done correctly
            method = 'BeFinder'

            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Check if the record exists in the database
                existing_record = self.session.query(BeFinderResults).filter(
                    and_(
                        BeFinderResults.SampleID == row['SampleID'],
                        BeFinderResults.Method == method,
                    )
                ).order_by(desc(BeFinderResults.Iteration)).first()

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
                    new_record = BeFinderResults(**new_row_data)
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

                    new_record = BeFinderResults(**new_row_data)
                    self.session.add(new_record)

                # Commit after all inserts/updates are executed
                self.session.commit()

        except Exception as e:
            print(f"Upload failed: {e}")
            self.session.rollback()  # Rollback in

    def get_sdg(self, batch_id):
        try:
            self.init_session()

            sdg = self.session.query(DQO.SDG).filter(
                DQO.BatchID == batch_id
            ).first()

            return sdg
        except Exception as e:
            print(f"Erro fetching SDG: {e}")
            self.session.rollback()

    def get_sample_ids(self, batch_id):
        try:
            self.init_session()

            results = (
                self.session.query(DQO.SampleID)
                .filter(DQO.BatchID == batch_id) 
                .all()  # Fetch all results
            )

            sample_id_list = [result.SampleID for result in results]
            print(sample_id_list)

            return sample_id_list
        except Exception as e:
            print(f"Error fetching Sample IDs: {e}")
            self.session.rollback()

    def parse_befinder_file(self, file_path):
        columns = ['BeFinderID', 'Counts', 'Units']
        
        df = pd.read_excel(file_path, header=None)

        df.columns = columns
        
        pattern = r"\d{2}LLB\d{4}"

        file_name = os.path.basename(file_path)
        file_name = os.path.splitext(file_name)[0]

        print(file_name)

        if re.match(pattern, file_name):
            batch_id = file_name
        else:
            # Error handling
            print("File name is not a valid batch ID.")

        df.insert(0, "BatchID", batch_id)

        # Get the SampleIDs and SDG
        sdg = self.get_sdg(batch_id)

        df.insert(0, "SDG", sdg[0])

        df.insert(1, "SampleID", "")

        sample_id_list = self.get_sample_ids(batch_id)

        cal_list = []

        for i in range(5):
            cal_item = f"{batch_id}CAL{i+1}"
            cal_list.append(cal_item)

        sample_id_list = cal_list + sample_id_list

        print(sample_id_list)

        self.move_item_to_index(sample_id_list, "BLK", 6)
        self.move_item_to_index(sample_id_list, "LCS", 7)
        self.move_item_to_index(sample_id_list, "DUP", 9)

        i = 0

        for index, row in df.iterrows():
            df.loc[index, 'SampleID'] = sample_id_list[i]  # Assign value directly to the DataFrame
            print(sample_id_list[i])  
            i += 1

        df.to_csv(destination_path, index=False) 
        
        self.generate_calibration_data(df)

        self.generate_statistics(df)

        return df
    
    def generate_statistics(self, df):
        df['PPB'] = round((df['Counts']-870.25)/3084.1, 5)
        df['MicroGrams'] = round(df['PPB']/10, 5)
        print(df)
        blk_row = df.loc[6, :]
        lcs_row = df.loc[7, :]
        sample_row = df.loc[8, :]
        dup_row = df.loc[9, :]
        # if ug/100cm <= 0.02, pass, else fail
        # if % recovery is not none:
        #   if % recovery >= 80%, pass
        #       elif % recovery is <= 120%, pass, else fail
        # if relative difference is not none:
        #   if relative difference is < 25%, pass
        #       elif ppb < ((3084.1*LOD)+870.25), pass, else fail
        #   
        # BLK statistics
        if blk_row['MicroGrams'] <= 0.02:
            blk_row['DataValidation'] = "Pass"
        else:
            blk_row['DataValidation'] = "Fail"

        # LCS statistics
        lcs_row['Recovery'] = lcs_row['PPB']/4.901

        dup_row['RelativeDifference'] = round(abs((dup_row['Counts']-sample_row['Counts'])/((dup_row['Counts']+sample_row['Counts'])/2))*100, 2)
        
        print(blk_row, lcs_row, sample_row, dup_row)

    def generate_calibration_data(self, df):
        calibration_df = df.loc[:4, :]

        print(calibration_df)

        calibration_df['PPB'] = [0, 0.05, 2, 10, 40]

        X = calibration_df[['PPB']]
        y = calibration_df[['Counts']]

        model = LinearRegression()

        model.fit(X, y)

        predictions = model.predict(X)

        r2 = round(r2_score(y, predictions), 5)

        print("R^2= ", r2)

        print(calibration_df)

    def move_item_to_index(self, lst, keyword, target_index):
        # Find the index of the record containing the keyword
        for i, item in enumerate(lst):
            if keyword in item:
                # Remove the item from its current position
                item_to_move = lst.pop(i)
                # Insert the item at the target index
                lst.insert(target_index, item_to_move)
                break  # Stop after moving the first matching item

processor = BeFinderProcessor()

df = processor.parse_befinder_file(file_path)

processor.upload_to_database(df)
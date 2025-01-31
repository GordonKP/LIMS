import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_, Date, Time
from sqlalchemy.orm import sessionmaker, declarative_base
import re
import json
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
    
basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

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
    Analyte = Column(String(50))
    FilePath = Column(String(255))                                      # File name of the corresponding data file
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                          # Counts Units
    PPB = Column(Float)                                                 # Parts per billion
    MicroGrams = Column(Float)                                          # Micrograms per 100cm^2 
    AnalysisDateTime = Column(DateTime)
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

            batch_id = df['BatchID'].unique()[0]

            query = self.session.query(DQO).filter(
                        and_(DQO.BatchID == batch_id)
                    ).first()
            
            matrix = query.Matrix

            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Check if the record exists in the database
                existing_record = self.session.query(BeFinderResults).filter(
                    and_(
                        BeFinderResults.SampleID == row['SampleID'],
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
                    existing_record.Reporting = False
                    
                    # If the record exists, increment Iteration and add new data
                    new_iteration = existing_record.Iteration + 1

                    new_row_data = {column: row[column] for column in df.columns}
                    new_row_data['Iteration'] = new_iteration
                    new_row_data['BatchID'] = existing_record.BatchID  # Carry forward BatchID
                    new_row_data['SDG'] = existing_record.SDG  # Carry forward SDG
                    new_row_data['Reporting'] = True  # Set reporting to True
                    new_row_data['Method'] = method
                    new_row_data['Matrix'] = matrix
                    new_row_data['ResultType'] = result_type
                    new_row_data['FilePath'] = destination_path
                    new_row_data['Analyte'] = 'BeFinder'
                    new_row_data['AnalysisDateTime'] = row['AnalysisDateTime']

                    # Log data to be inserted
                    print(f"Inserting new record with iteration {new_iteration} for SampleID {row['SampleID']}")

                    # Create a new record instead of updating the existing one
                    new_record = BeFinderResults(**new_row_data)
                    self.session.add(new_record)

                else:
                    print("RECORD DOES NOT EXIST")

                    # If no existing record, update the row data in the database
                    new_row_data = {column: row[column] for column in df.columns}
                    new_row_data['Iteration'] = 1  # Set Iteration to 1 for new records
                    new_row_data['Reporting'] = True
                    new_row_data['SampleID'] = row['SampleID']
                    new_row_data['BatchID'] = row['BatchID']
                    new_row_data['SDG'] = row['SDG']
                    new_row_data['Method'] = method
                    new_row_data['Matrix'] = matrix
                    new_row_data['ResultType'] = result_type
                    new_row_data['FilePath'] = destination_path
                    new_row_data['Analyte'] = 'BeFinder'
                    new_row_data['AnalysisDateTime'] = row['AnalysisDateTime']

                    # Log the update operation
                    print(f"Adding record for SampleID {row['SampleID']} with Iteration 1")

                    new_record = BeFinderResults(**new_row_data)
                    self.session.add(new_record)

                # Commit after all inserts/updates are executed
                self.session.commit()

        except Exception as e:
            print(f"Upload failed: {e}")
            self.session.rollback()  # Rollback in

    def get_sample_ids(self, batch_id):
        from datetime import datetime
        try:
            prepsheetdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Prepsheets")

            json_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")
            with open(json_path, "r", encoding='utf-8') as file:
                prepsheet_data = json.load(file)

                sample_id_list = prepsheet_data['Samples']['Sample ID']

                analysis_prep = next((item for item in prepsheet_data['Prep Data'] if item["Event Name"] == "Analysis"), None)

                if analysis_prep:
                    prep_date = analysis_prep["Prep Date"]
                    prep_time = analysis_prep["Prep Time"]
                    prep_datetime = datetime.strptime(f"{prep_date} {prep_time}", "%Y-%m-%d %H:%M")
                else:
                    print("No 'Analysis' event found.")

            return sample_id_list, prep_datetime

        except Exception as e:
            print(f"Error fetching Sample IDs: {e}")
            self.session.rollback()

    def parse_befinder_file(self, file_path):
        columns = ['BeFinderID', 'Result', 'ResultUnits']
        
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

        df.insert(1, "SampleID", "")

        sample_id_list, analysis_datetime = self.get_sample_ids(batch_id)

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

        print(df)

        calibration_df = df.loc[:4, :]

        calibration_df['PPB'] = [0, 0.05, 2, 10, 40]

        df = df.loc[5:, :]
        
        df['PPB'] = round((df['Result']-870.25)/3084.1, 5)

        df = pd.concat([calibration_df, df], axis=0, ignore_index=True)

        df = df.assign(AnalysisDateTime=analysis_datetime)

        df = df.drop(columns='BeFinderID')

        df['MicroGrams'] = round(df['PPB']/10, 5)

        print(df)

        qc_sdg = None

        for index, row in df.iterrows():
            try:
                self.init_session()

                query = self.session.query(DQO.SDG).filter(DQO.SampleID == df['SampleID']).first()

                if query:
                    row['SDG'] = query.SDG
                    if ',' in query.SDG:
                        qc_sdg = query.SDG
                else:
                    continue
            except Exception as e:
                print(f"Exception: {e}")
        
        df['SDG'].fillna(qc_sdg, inplace=True)

        df.to_csv(destination_path, index=False) 
        
        self.generate_calibration_data(df)

        return df

    def generate_calibration_data(self, df):
        calibration_df = df.loc[:4, :]

        print(calibration_df)

        calibration_df['PPB'] = [0, 0.05, 2, 10, 40]

        X = calibration_df[['PPB']]
        y = calibration_df[['Result']]

        model = LinearRegression()

        model.fit(X, y)

        predictions = model.predict(X)

        r2 = round(r2_score(y, predictions), 5)

        print("R^2= ", r2)

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
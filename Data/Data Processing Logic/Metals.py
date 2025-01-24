import csv
import pandas as pd
import os
import config
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_, Text, distinct
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

class ICPMSResults(Base):
    __tablename__ = 'ICPMSResults'

    SDG = Column(String(50), primary_key=True)                             # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                         # Leidos Batch ID
    Method = Column(String(20))                                            # Analytical Method
    SampleID = Column(String(50), primary_key=True)                        # Sample identifier
    Matrix = Column(String(50))                                            # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    AnalysisDateTime = Column(DateTime, primary_key=True)                  # Date and Time Acquired
    DilutionFactor = Column(Float)                                         # Dilution Factor
    Notes = Column(Text)                                                   # Misc. Info or Comment
    FileName = Column(String(100))                                         # Data File Name
    CalibrationBatchID = Column(String(100), primary_key=True)             # Batch Name
    FilePath = Column(String(255))                                         # Data Path
    Analyst = Column(String(100))                                          # Operator
    InstrumentName = Column(String(50))                                    # Instrument Name
    SampleWeightVolume = Column(Float)                                     # Sample Weight or Volume
    FinalWeightVolume = Column(Float)                                      # Final Weight or Volume
    DilutionMultiplier = Column(Float)                                     # Dilution Multiplier
    ElementSymbol = Column(String(2))                                      # Analyte
    Analyte = Column(String(50), primary_key=True)                        # Element Full Name
    Mass = Column(Float)                                                   # Mass
    ISTDRefMass = Column(Float, primary_key=True)                          # ISTD Ref Mass
    Concentration = Column(Float)                                          # Concentration
    ConcentrationRSD = Column(Float)                                       # Conc RSD
    CPSMean = Column(Float)                                                # CPS Mean
    CPSRep1 = Column(String(50))                                           # CPS Rep1
    CPSRep2 = Column(String(50))                                           # CPS Rep2
    CPSRep3 = Column(String(50))                                           # CPS Rep3
    CPSRep4 = Column(String(50))                                           # CPS Rep4
    CPSRep5 = Column(String(50))                                           # CPS Rep5
    CPSRSD = Column(Float)                                                 # CPS RSD
    Units = Column(String(50))                                             # Units                             
    Iteration = Column(Integer, primary_key=True)                          # Iteration number
    Reporting = Column(Boolean, primary_key=True)                          # Reporting status (True/False)

class DQO(Base):
    __tablename__ = "DQO"

    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))

class MetalsProcessor:
    def __init__(self):
        self.session = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def show_rejected_message(self, rejected_samples):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Sample or Calibration Rejections")
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
            return True
        else:
            return False

    def upload_to_database(self, df):
        method = 'Metals'
        rejected_samples = []
        
        try:
            self.init_session()  # Make sure session initialization is done correctly
            calibration_samples = []
            columns_to_iterate = [f'CPSRep{i}' for i in range(1, 6)]
            # Iterate through the DataFrame rows
            for index, row in df.iterrows():
                # Find the batch id and sdg
                query = self.session.query(DQO).filter( # Check to see if the row exists in the DQO table
                    and_(DQO.Method == method,
                            DQO.SampleID == row['SampleID'])
                ).first()

                reject_counter = 0
                for column in columns_to_iterate:
                    if pd.notnull(row[column]) and row[column].upper() == 'REJECTED':
                        reject_counter += 1

                if reject_counter > 2:
                    reject_info = [row['SampleID'], row['FileName'], row['CalibrationBatchID'], row['Analyte']]
                    rejected_samples.append(reject_info)

                # Regex pattern for finding the result type
                pattern = r"\d{2}LLB\d{4}([A-Za-z]+.*)"

                # Search for the pattern in the sample ID
                match = re.search(pattern, row['SampleID'])

                if match:
                    result_type = match.group(1)
                else:
                    result_type = 'REG'

                if query:
                    # Check if the record exists in the database
                    existing_record = self.session.query(ICPMSResults).filter(
                        and_(
                            ICPMSResults.SampleID == row['SampleID'],
                            ICPMSResults.Method == method,
                            ICPMSResults.ElementSymbol == row['ElementSymbol']
                        )
                    ).order_by(desc(ICPMSResults.Iteration)).first()

                    if existing_record: # Check to see if the row exists in the results table
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
                        new_record = ICPMSResults(**new_row_data)
                        self.session.add(new_record)

                    else:
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

                        new_record = ICPMSResults(**new_row_data)
                        self.session.add(new_record)
                else:
                    calibration_samples.append(row)

            if rejected_samples:
                continue_to_upload = self.show_rejected_message(rejected_samples)
            
            if continue_to_upload is True:
                pass
            else:
                self.session.rollback()

            self.session.commit()

        except Exception as e:
            print(f"Sample upload failed: {e}")
            self.session.rollback()  # Rollback in

        finally:
            self.session.close()
            if calibration_samples:
                self.process_calibration_data(calibration_samples)

    def process_calibration_data(self, calibration_samples):
        calibration_df = pd.DataFrame(calibration_samples, columns=['SampleID', 'AnalysisDateTime', 'DilutionFactor', 'Notes', 'FileName', 'CalibrationBatchID', 'FilePath', 'Analyst', 'InstrumentName', 'SampleWeightVolume', 
                'FinalWeightVolume', 'DilutionMultiplier', 'ElementSymbol', 'Analyte', 'Mass', 'ISTDRefMass', 'Concentration', 'ConcentrationRSD', 'CPSMean', 
                'CPSRep1', 'CPSRep2', 'CPSRep3', 'CPSRep4', 'CPSRep5', 'CPSRSD', 'Units'])
        
        for index, row in calibration_df.iterrows():
            try:
                self.init_session()
                method = "Metals"
                # Check to see if the calibration data is in the results table
                existing_record = self.session.query(ICPMSResults).filter(
                            and_(
                                ICPMSResults.SampleID == row['SampleID'],
                                ICPMSResults.AnalysisDateTime == row['AnalysisDateTime'],
                                ICPMSResults.FileName == row['FileName'],
                                ICPMSResults.Analyte == row['Analyte'],
                                ICPMSResults.CalibrationBatchID == row['CalibrationBatchID'],
                                ICPMSResults.ISTDRefMass == row['ISTDRefMass']
                            )
                        ).order_by(desc(ICPMSResults.Iteration)).first()
                
                if existing_record:
                    continue
                else:
                    # Query for unique BatchID values filtering by CalibrationBatchID
                    unique_batch_ids = self.session.query(distinct(ICPMSResults.BatchID)).filter(
                        ICPMSResults.CalibrationBatchID == row['CalibrationBatchID']
                    ).all()

                    sample_matrix = self.session.query(ICPMSResults.Matrix).filter(
                        ICPMSResults.CalibrationBatchID == row['CalibrationBatchID']
                    ).first()

                    # This will return a list of tuples, so if you want just the BatchID values, you can unpack them:
                    batch_ids = [batch_id[0] for batch_id in unique_batch_ids]

                    batch_ids_str = ', '.join(batch_ids)

                    # Query for unique BatchID values filtering by CalibrationBatchID
                    unique_sdgs = self.session.query(distinct(ICPMSResults.SDG)).filter(
                        ICPMSResults.CalibrationBatchID == row['CalibrationBatchID']
                    ).all()

                    # This will return a list of tuples, so if you want just the BatchID values, you can unpack them:
                    sdgs = [sdg[0] for sdg in unique_sdgs]

                    sdgs_str = ', '.join(sdgs)

                    # If no existing record, update the row data in the database
                    new_row_data = {column: row[column] for column in calibration_df.columns}
                    new_row_data['Iteration'] = 1  # Set Iteration to 1 for new records
                    new_row_data['Reporting'] = True
                    new_row_data['SampleID'] = row['SampleID']
                    new_row_data['BatchID'] = batch_ids_str
                    new_row_data['SDG'] = sdgs_str
                    new_row_data['Method'] = method
                    new_row_data['Matrix'] = sample_matrix.Matrix
                    new_row_data['ResultType'] = "CAL"

                    # Log the update operation
                    print(f"Adding record for SampleID {row['SampleID']} with Iteration 1")

                    new_record = ICPMSResults(**new_row_data)
                    self.session.add(new_record)

                self.session.commit()

            except Exception as e:
                print(f"Caliration upload failed: {e}")
                self.session.rollback()  # Rollback in
            
            finally:
                self.session.close()

    def parse_icpms_file(self, file_path):
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            data = []
            for row in reader:
                data.append(row)

            columns = [
                'SampleID', 'AnalysisDateTime', 'DilutionFactor', 'Notes', 'FileName', 'CalibrationBatchID', 'FilePath', 'Analyst', 'InstrumentName', 'SampleWeightVolume', 
                'FinalWeightVolume', 'DilutionMultiplier', 'ElementSymbol', 'Analyte', 'Mass', 'ISTDRefMass', 'Concentration', 'ConcentrationRSD', 'CPSMean', 
                'CPSRep1', 'CPSRep2', 'CPSRep3', 'CPSRep4', 'CPSRep5', 'CPSRSD', 'Units'
            ]

            # Initialize a list to store all sample rows
            sample_rows = []

            for sample in data[1::]:
                sample_data = []

                for i in range(26):
                    sample_data.append(sample[i])

                sample_rows.append(sample_data)
            
            df = pd.DataFrame(sample_rows, columns=columns)

            df.replace("N/A", None, inplace=True)

            print(df)

            df.to_csv(destination_path, index=False)

            return df

processor = MetalsProcessor()

df = processor.parse_icpms_file(file_path)

processor.upload_to_database(df)
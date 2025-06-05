import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

from PyQt5.QtWidgets import QMessageBox
from math import log
from lims.config import tables
from lims.config.config import CONNECTION_STRING
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class U235_Tracker:
    def __init__():
        session = None
        engine = None

    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        U235_Tracker.engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(U235_Tracker.engine)
        Session = sessionmaker(bind=U235_Tracker.engine)
        U235_Tracker.session = Session()
        return Session()

    @staticmethod
    def calculate(row):
        # First ensure all values are of the right type
        result = float(row['Result'])
        aliquot = float(row['Aliquot'])
        initial_volume = float(row['InitialVolume'])

        # Need to calculate total activity
        total_activity = result * aliquot

        # The result needs to be converted to Bq
        if "DPM" in str(row['ResultUnits']).upper():
            total_activity = total_activity / 60
        elif "PCI" in str(row['ResultUnits']).upper():
            total_activity = total_activity * 0.037 
        elif "BQ" in str(row['ResultUnits']).upper():
            pass
        else:
            QMessageBox.warning("Units Not Found!", f"Cannot convert units: {row['ResultUnits']}\nPlease ensure result units are in pCi, DPM or Bq.")
            return row

        # Determine decay constant, U235 half-life is a known converted to seconds.
        half_life = 2.22 * 10**16

        decay_constant = log(2) / half_life

        # Calculate number of atoms
        atom_count = total_activity / decay_constant

        # Convert atom count to mass. 
        avogadro_num = 6.022 * 10**23
        molar_mass = 235

        volume_ratio = initial_volume / aliquot

        FGE = (((atom_count / avogadro_num) * molar_mass)*volume_ratio)

        row['FGE'] = FGE

        if row['FGE'] > 0.5:
            row['NMCA'] = 1

        return row

    def upload_fge(df):
        try:
            session = U235_Tracker.init_session()

            unique_samples = df[df['ResultType'] == 'REG']['SampleID'].unique().tolist()
            sdg = df['SDG'].unique().tolist()[0]

            sample_volume_map = {}

            for sample_id in unique_samples:
                sample_volume_query = session.query(tables.SampleLogin.SampleVolume).filter(tables.SampleLogin.SDG == sdg, tables.SampleLogin.SampleID == sample_id).first()

                if sample_volume_query:
                    sample_volume_map[sample_id] = float(sample_volume_query[0])

        except Exception as e:
            if session:
                session.rollback()
            print(f"An exception occurred getting Sample Volumes: {e}")
        finally:
            if session:
                session.close()

        df.insert(0, "InitialVolume", 1)

        df['InitialVolume'] = df['SampleID'].map(sample_volume_map).fillna(df['Aliquot'])

        try:
            session = U235_Tracker.init_session()

            # Insert FGE value
            df.insert(0, "FGE", 0)
            df.insert(0, 'NMCA', 0)

            # Apply a mask to only effect the U-235 samples
            mask = df['Analyte'] == 'U-235'
            df.loc[mask] = df.loc[mask].apply(U235_Tracker.calculate, axis=1)

            for index, row in df.iterrows():
                print(f"SDG: {row['SDG']}, SampleID: {row['SampleID']}, Method: {row['Method']}, FGE: {row['FGE']}, Volume: {row['InitialVolume']}")

            # session.commit()

        except Exception as e:
            print(f"An exception occurred updating NCS: {e}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

df = pd.read_csv(r"\\ServerName\Staff\U235_Test.csv")
U235_Tracker.upload_fge(df)
            
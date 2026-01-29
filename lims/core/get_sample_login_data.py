import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

import lims.config.tables as tables
from sqlalchemy import create_engine
from lims.config.config import CONNECTION_STRING
from sqlalchemy.orm import sessionmaker
from lims.core.popups import Popup

from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
    IntegrityError,
    SQLAlchemyError
)

import pandas as pd

class GetSampleLoginData:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_sample_login_data(self, df):
        sdg_list = df["SDG"].dropna().astype(str).unique().tolist()

        if not sdg_list:
            Popup.debugger(
                "Data Error",
                "No SDGs present when calling get_sample_login_data."
            )
            return None

        try:
            self.init_session()

            query = (
                self.session
                .query(tables.SampleLogin)
                .filter(tables.SampleLogin.SDG.in_(sdg_list))
                .statement
            )

            result_df = pd.read_sql(query, self.engine)

            return result_df

        except OperationalError as e:
            Popup.debugger(
                "Database Connection Error",
                f"Could not connect to the database.\n\n{e}"
            )

        except ProgrammingError as e:
            Popup.debugger(
                "SQL Error",
                f"SQL syntax or schema issue encountered.\n\n{e}"
            )

        except IntegrityError as e:
            Popup.debugger(
                "Database Integrity Error",
                f"Integrity constraint issue encountered.\n\n{e}"
            )

        except SQLAlchemyError as e:
            Popup.debugger(
                "Database Error",
                f"A SQLAlchemy error occurred.\n\n{e}"
            )

        except Exception as e:
            Popup.debugger(
                "Unexpected Error",
                f"An unexpected error occurred.\n\n{e}"
            )

        finally:
            if self.session:
                self.session.close()
                self.session = None

        return None
    
    def fill_sample_date_time(self, df):
        '''
        Populate missing SampleDateTime values in instrument data.

        Requirements
        ----------
        PrepDateTime must exist prior to this function's execution.

        Parameters
        ----------
        df : pandas.DataFrame
            Instrument data containing at minimum the following columns:
            - SDG
            - BatchID
            - SampleID

        Returns
        -------
        pandas.DataFrame
            A copy of the input DataFrame with SampleDateTime created and filled where possible.

        Raises
        ------
        ValueError
            If required columns are missing from the input DataFrame.
        '''

        if "PrepDateTime" not in df.columns:
            Popup.debugger("Columnar Error", "PrepDateTime column does not exist when calling fill_sample_date_time.")
            return None

        sample_login_df = self.get_sample_login_data(df)

        if sample_login_df is None or sample_login_df.empty:
            Popup.debugger("Data Error", "SampleLogin query returned no rows.")
            return None
        
        df = df.copy()
        df["SampleID"] = df["SampleID"].astype(str)
        sample_login_df = sample_login_df.copy()
        sample_login_df["SampleID"] = sample_login_df["SampleID"].astype(str)

        def sample_datetime(row):
            sample_id = row["SampleID"]
            sdg = row["SDG"]

            # If DUP, try parent ID first
            if row.get("ResultType") == "DUP":
                parent_id = sample_id.replace("DUP", "")
                match = sample_login_df.loc[
                    (sample_login_df["SDG"] == sdg) &
                    (sample_login_df["SampleID"] == parent_id)
                ]
                if not match.empty:
                    sd = match.iloc[0]["SampleDate"]
                    st = match.iloc[0]["SampleTime"]
                    row["SampleDateTime"] = pd.to_datetime(f"{sd} {st}", errors="coerce")
                    if pd.isna(row["SampleDateTime"]):
                        row["SampleDateTime"] = row["PrepDateTime"]
                        print(row['SampleDateTime'])
                    return row
                # fall through to normal behavior if parent not found

            # Normal SampleID lookup
            match = sample_login_df.loc[
                (sample_login_df["SDG"] == sdg) &
                (sample_login_df["SampleID"] == sample_id)
            ]

            if not match.empty:
                sd = match.iloc[0]["SampleDate"]
                st = match.iloc[0]["SampleTime"]
                row["SampleDateTime"] = pd.to_datetime(f"{sd} {st}", errors="coerce")
                if pd.isna(row["SampleDateTime"]):
                    row["SampleDateTime"] = row["PrepDateTime"]
            else:
                row["SampleDateTime"] = row["PrepDateTime"]

            print(row['SampleDateTime'])
            return row

        df = df.apply(sample_datetime, axis=1)

        return df
    
    def fill_received_date_time(self, df):
        '''
        Populate missing DateTimeReceived values in instrument data.

        Requirements
        ----------
        PrepDateTime must exist prior to this function's execution.

        Parameters
        ----------
        df : pandas.DataFrame
            Instrument data containing at minimum the following columns:
            - SDG
            - BatchID
            - SampleID

        Returns
        -------
        pandas.DataFrame
            A copy of the input DataFrame with DateTimeReceived created and filled where possible.

        Raises
        ------
        ValueError
            If required columns are missing from the input DataFrame.
        '''

        if "PrepDateTime" not in df.columns:
            Popup.debugger("Columnar Error", "PrepDateTime column does not exist when calling fill_received_date_time.")
            return None

        sample_login_df = self.get_sample_login_data(df)

        if sample_login_df is None or sample_login_df.empty:
            Popup.debugger("Data Error", "SampleLogin query returned no rows.")
            return None
        
        df = df.copy()
        df["SampleID"] = df["SampleID"].astype(str)
        sample_login_df = sample_login_df.copy()
        sample_login_df["SampleID"] = sample_login_df["SampleID"].astype(str)

        def received_datetime(row):
            sample_id = row["SampleID"]
            sdg = row["SDG"]

            # If DUP, try parent ID first
            if row.get("ResultType") == "DUP":
                parent_id = sample_id.replace("DUP", "")
                match = sample_login_df.loc[
                    (sample_login_df["SDG"] == sdg) &
                    (sample_login_df["SampleID"] == parent_id)
                ]
                if not match.empty:
                    sd = match.iloc[0]["DateReceived"]
                    st = match.iloc[0]["TimeReceived"]
                    row["DateTimeReceived"] = pd.to_datetime(f"{sd} {st}", errors="coerce")
                    if pd.isna(row["DateTimeReceived"]):
                        row["DateTimeReceived"] = row["PrepDateTime"]
                    print(row['DateTimeReceived'])
                    return row
                # fall through to normal behavior if parent not found

            # Normal SampleID lookup
            match = sample_login_df.loc[
                (sample_login_df["SDG"] == sdg) &
                (sample_login_df["SampleID"] == sample_id)
            ]

            if not match.empty:
                sd = match.iloc[0]["DateReceived"]
                st = match.iloc[0]["TimeReceived"]
                row["DateTimeReceived"] = pd.to_datetime(f"{sd} {st}", errors="coerce")
                if pd.isna(row["DateTimeReceived"]):
                    row["DateTimeReceived"] = row["PrepDateTime"]
            else:
                row["DateTimeReceived"] = row["PrepDateTime"]

            print(row['DateTimeReceived'])
            return row

        df = df.apply(received_datetime, axis=1)

        return df
    
    def fill_field_id(self, df):
        sample_login_df = self.get_sample_login_data(df)

        if sample_login_df is None or sample_login_df.empty:
            Popup.debugger("Data Error", "SampleLogin query returned no rows.")
            return None
        
        df = df.copy()
        df["SampleID"] = df["SampleID"].astype(str)
        sample_login_df = sample_login_df.copy()
        sample_login_df["SampleID"] = sample_login_df["SampleID"].astype(str)

        def get_field_id(row):
            # Normal SampleID lookup
            sdg = row['SDG']
            sample_id = row['SampleID']
            print(f"'{sdg}' '{sample_id}'")

            match = sample_login_df.loc[
                (sample_login_df["SDG"] == sdg) &
                (sample_login_df["SampleID"] == sample_id)
            ]

            if not match.empty:
                field_id = match.iloc[0]['LocationID']
                row['FieldID'] = field_id

                if pd.isna(row["FieldID"]):
                    row["FieldID"] = sample_id
            else:
                row["FieldID"] = sample_id

            return row

        df = df.apply(get_field_id, axis=1)

        return df

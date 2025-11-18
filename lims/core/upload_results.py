from lims.config.config import CONNECTION_STRING
from lims.config import tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

class UploadResults:
    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()
    
    @staticmethod
    def debugger(title, text):
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    @staticmethod
    def choice(title, text, choices):
        """
        Show a choice dialog with custom buttons.
        
        Args:
            title (str): Window title
            text (str): Message text
            choices (list[str]): Button labels, e.g. ["Overwrite", "Skip", "Cancel"]

        Returns:
            str: The label of the button clicked, or None if closed.
        """
        from PyQt5.QtWidgets import QMessageBox

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))

        buttons = {}

        for choice in choices:
            # Add each button dynamically
            btn = msg.addButton(choice, QMessageBox.AcceptRole)
            buttons[btn] = choice  # map PyQt button → text label

        msg.exec_()

        clicked = msg.clickedButton()
        return buttons.get(clicked, None)

    @staticmethod
    def check_results(df):
        # Need to determine the table that data will be uploaded into
        methods_tables = {"HG": tables.HGResults,
                "ISOAM": tables.ALPHAResults,
                "ISOTH": tables.ALPHAResults,
                "ISOU": tables.ALPHAResults,
                "ISOPU": tables.ALPHAResults,
                "GAMMA": tables.GAMMAResults,
                "GFPC": tables.GFPCResults,
                "LSCPU": tables.LSCResults,
                "LSCSR": tables.LSCResults,
                "LSCAB": tables.LSCResults,
                "MET": tables.METResults,
                "TCLP": tables.METResults,
                "BEF": tables.BEFResults,
                "SIO2": tables.WetChemResults,
                "TSP": tables.WetChemResults,
                'FLUOR': tables.WetChemResults,
                "NH3": tables.WetChemResults,
                "NO3": tables.WetChemResults,
                "NO2": tables.WetChemResults,
                "CRVI": tables.WetChemResults,
                "CL": tables.WetChemResults,
                "PH": tables.WetChemResults,
                "TSS": tables.WetChemResults,
                "TSP": tables.WetChemResults}
        
        method_list = df['Method'].unique().tolist()

        # Determine the method
        if len(method_list) == 1:
            method = method_list[0]
            pass
        else:
            UploadResults.debugger("Error Uploading Data", "More or less than one analytical method detected.")
            return None
        
        # Determine the table
        table = methods_tables[method]
        
        # Upload data by batch
        batch_list = df['SDG'].unique().tolist()

        session = None

        try:
            session = UploadResults.init_session()

            query_results = session.query(table).filter(table.SDG == 'SDG').all()

            query_df = pd.DataFrame([dict(row._mapping) for row in query_results])

        except SQLAlchemyError as e:
            UploadResults.debugger("An error occurred uploading data", "An error occurred trying to query results table to find existing results.")
            query_df = pd.DataFrame()
        finally:
            if session is not None:
                session.close()

        if query_df.empty:
            UploadResults.upload_results(df)
        else:
            UploadResults.compare_results(df, query_df)

        
    @staticmethod
    def upload_results(df):
        return
    
    @staticmethod
    def compare_results(df, query_df):
        '''
        If results were discovered for that SDG, they need to be compared and overwritten or preserved.

        To do this, results need to be checked for primary key violations. 

        An analysis for any given sample is determined to already exist if there is a valid row that contains the same SDG, BatchID, SampleID, and Analyte. 
        
        This row must be set to reporting = True.
        '''

        primary_key_columns = ['SDG', 'BatchID', 'SampleID', 'Analyte', 'Reporting']

        # Build key for comparison in both DataFrames
        df['_pk'] = df[primary_key_columns].astype(str).agg('|'.join, axis=1)
        query_df['_pk'] = query_df[primary_key_columns].astype(str).agg('|'.join, axis=1)

        # Identify matches and non-matches
        existing_df = df[df['_pk'].isin(query_df['_pk'])]
        new_df = df[~df['_pk'].isin(query_df['_pk'])]

        # Clean working column
        df.drop(columns=['_pk'], inplace=True)
        query_df.drop(columns=['_pk'], inplace=True)

        # Upload new results if they exist
        if new_df.empty and existing_df.empty:
            UploadResults.debugger(
                "Error Uploading Data",
                "There are no new or existing matching results in this upload.\n"
                "Please verify that SampleIDs are correct."
            )
            return None

        if not new_df.empty:
            UploadResults.upload_results(new_df)

        # Continue to overwrite/compare logic here...
        



            
        

        return

        

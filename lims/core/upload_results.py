from lims.config.config import CONNECTION_STRING
from lims.config import tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

class UploadResults:
    def init_session(self):
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()
    
    def debugger(self, title, text):
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

    def check_results(self, df):
        print("Made it to check_results")
        self.table = None
        self.sdg = None
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
            self.debugger("Error Uploading Data", "More or less than one analytical method detected.")
            return None
        
        sdg_list = df['SDG'].unique().tolist()

        # Determine the sdg
        if len(sdg_list) == 1:
            self.sdg = sdg_list[0]
            pass
        else:
            self.debugger("Error Uploading Data", "More or less than one SDG detected.")
            return None
        
        # Set default iteration and reporting
        df['Iteration'] = 1
        df['Reporting'] = 1
        
        # Determine the table
        self.table = methods_tables[method]
        
        session = None

        try:
            # Query the proper results table for the SDG
            session = self.init_session()

            query_results = session.query(self.table).filter(self.table.SDG == self.sdg).all()

            query_df = pd.DataFrame([
                {c.name: getattr(row, c.name) for c in self.table.__table__.columns}
                for row in query_results
            ])

        except SQLAlchemyError as e:
            self.debugger("An error occurred uploading data", "An error occurred trying to query results table to find existing results.")
            query_df = pd.DataFrame()
        finally:
            if session is not None:
                session.close()

        if query_df.empty:
            print("No existing results found, moving to upload_results.")
            self.upload_results(df)
        else:
            #  🔥 NEW LOGIC: Check for sample-level overlap
            uploaded_samples = set(df['SampleID'].unique())
            existing_samples = set(query_df['SampleID'].unique())

            overlapping_samples = uploaded_samples & existing_samples

            if not overlapping_samples:
                print("No sample-level overlap. Uploading without prompt.")
                df = self.iteration_increase(df, query_df)
                self.upload_results(df)
                return

            #  Fallback to original prompt logic
            print("Existing data found, moving to choice.")
            choice = self.choice(
                "Existing Data Found",
                (
                    f"Results already exist in {self.table.__tablename__} for this SDG.\n\n"
                    "How would you like to handle the existing results?\n\n"
                    "Replace All - Mark all previous results for this SDG as not reporting "
                    "and upload this file as the new full dataset.\n\n"
                    "Update Matching Only - Only overwrite results that match the samples "
                    "and analytes in this file. All other existing results will remain unchanged.\n\n"
                ),
                ["Replace All", "Update Matching Only", "Cancel"]
            )

            if choice == 'Replace All':
                print("Nuking Results")
                self.nuke_results()
                df = self.iteration_increase(df, query_df)
                self.upload_results(df)
            elif choice == 'Update Matching Only':
                print("comparing results")
                # If there were existing query results, then results need compared.
                df = self.iteration_increase(df, query_df)
                self.compare_results(df, query_df)
            else:
                return None
            
    def iteration_increase(self, df, query_df):
        """
        Increase iteration numbers for uploaded results based on existing data.
        If a row already exists in query_df (via PK match without Reporting),
        its iteration will be incremented by 1.
        Otherwise, it defaults to iteration = 1.
        """

        # Columns that define a unique analysis
        key_cols = ['SDG', 'BatchID', 'SampleID', 'Analyte']

        # Create a lookup dict: PK → highest iteration in existing data
        # (in case your old data has multiple reporting rows)
        query_df['pk'] = query_df[key_cols].astype(str).agg('|'.join, axis=1)
        iteration_lookup = query_df.groupby('pk')['Iteration'].max().to_dict()

        # Build PK in new df
        df['pk'] = df[key_cols].astype(str).agg('|'.join, axis=1)

        # Apply iteration logic
        new_iterations = []
        for pk in df['pk']:
            if pk in iteration_lookup:
                new_iterations.append(iteration_lookup[pk] + 1)
            else:
                new_iterations.append(1)

        df['Iteration'] = new_iterations

        # Cleanup working column
        df.drop(columns=['pk'], inplace=True)

        return df
            
    def nuke_results(self):
        session = self.init_session()

        try:
            # Set all existing results for this SDG to Reporting = 0
            session.query(self.table).filter(self.table.SDG == self.sdg).update(
                {self.table.Reporting: 0},
                synchronize_session=False
            )

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            self.debugger(
                "Error Uploading Data",
                f"An error occurred replacing results for SDG {self.sdg}:\n{e}"
            )
            return None

        finally:
            session.close()
        
    def upload_results(self, df):
        """
        Uploads all rows from df into self.table.
        Assumes all PK validation, iteration logic, and cleanup
        have already been performed before calling this.
        """

        session = self.init_session()

        try:
            valid_columns = set(c.name for c in self.table.__table__.columns)

            rows = []

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # Filter out anything not in the table
                filtered = {k: v for k, v in row_dict.items() if k in valid_columns}

                rows.append(self.table(**filtered))

            # Add and commit
            session.add_all(rows)
            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            self.debugger(
                "Error Uploading Data",
                f"An error occurred inserting results into {self.table.__tablename__}:\n{e}"
            )
            return None

        finally:
            session.close()

        return True
    
    def compare_results(self, df, query_df):
        """
        Update logic when existing results are present and the user selected
        'Update Matching Only'.

        Rules:
        - A 'match' means same SDG, BatchID, SampleID, Analyte (Reporting ignored).
        - Any old matching rows must be set to Reporting = 0.
        - New file rows (df) should then be uploaded as the newest version.
        """

        primary_key_columns = ['SDG', 'BatchID', 'SampleID', 'Analyte']

        # Build PK keys (Reporting excluded for matching)
        df['_pk'] = df[primary_key_columns].astype(str).agg('|'.join, axis=1)
        query_df['_pk'] = query_df[primary_key_columns].astype(str).agg('|'.join, axis=1)

        # Determine which rows match existing data
        matching_pks = set(df['_pk']) & set(query_df['_pk'])

        matching_existing = query_df[query_df['_pk'].isin(matching_pks)]
        matching_new = df[df['_pk'].isin(matching_pks)]
        new_df = df[~df['_pk'].isin(query_df['_pk'])]

        # Cleanup temp PK columns
        df.drop(columns=['_pk'], inplace=True)
        query_df.drop(columns=['_pk'], inplace=True)

        if matching_new.empty and new_df.empty:
            self.debugger(
                "No Matching Data Found",
                "There are no matching or new results to upload.\n"
                "Check SampleID and Analyte values."
            )
            return None

        # Build set of valid column names from the SQL table
        valid_columns = set(c.name for c in self.table.__table__.columns)

        def filter_row(row):
            """Return dict of only valid table columns."""
            rd = row.to_dict()
            return {k: v for k, v in rd.items() if k in valid_columns}

        # Open session
        session = self.init_session()

        try:
            # 1. Set Reporting = 0 for old rows that match PKs
            if not matching_existing.empty:
                for _, row in matching_existing.iterrows():
                    session.query(self.table).filter_by(
                        SDG=row['SDG'],
                        BatchID=row['BatchID'],
                        SampleID=row['SampleID'],
                        Analyte=row['Analyte']
                    ).update({self.table.Reporting: 0})

            # 2. Upload brand-new rows
            if not new_df.empty:
                new_rows = [self.table(**filter_row(row)) for _, row in new_df.iterrows()]
                session.add_all(new_rows)

            # 3. Upload updated versions (the new file’s versions)
            if not matching_new.empty:
                updated_rows = [self.table(**filter_row(row)) for _, row in matching_new.iterrows()]
                session.add_all(updated_rows)

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            self.debugger(
                "Error Updating Results",
                f"An error occurred during update:\n{e}"
            )
            return None

        finally:
            session.close()

        return True
        

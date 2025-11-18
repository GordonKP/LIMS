from lims.config.config import CONNECTION_STRING
from lims.config.tables import Base, DQO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

class data_processing:
    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()
    
    @staticmethod
    def debugger(title, text):
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    @staticmethod
    def process_df(df):
        print("DEBUG: Starting process_df()")

        method_list = df['Method'].unique().tolist()
        print(f"DEBUG: Method list detected: {method_list}")

        if len(method_list) != 1:
            data_processing.debugger(
                "Multiple analytical methods detected",
                "Please ensure there is only one batch ID in the data file."
            )
            print("DEBUG: Exiting early due to multiple methods")
            return None

        method = method_list[0]
        print(f"DEBUG: Using method: {method}")

        sample_ids = df['SampleID'].unique().tolist()
        print(f"DEBUG: Sample IDs detected: {sample_ids}")

        merged = None  # ensure defined even if exception happens

        try:
            session = data_processing.init_session()
            print("DEBUG: Database session initialized")

            results = session.query(DQO).filter(
                DQO.SampleID.in_(sample_ids),
                DQO.Method == method
            ).all()

            print(f"DEBUG: Query returned {len(results)} DQO rows")

            dqos = [
                {
                    "SampleID": r.SampleID,
                    "SDG": r.SDG,
                    "BatchID": r.BatchID,
                    "Matrix": r.Matrix
                }
                for r in results
            ]

            dqos_df = pd.DataFrame(dqos)
            print(f"DEBUG: DQO DataFrame shape: {dqos_df.shape}")

            merged = df.merge(dqos_df, on="SampleID", how="left")
            print(f"DEBUG: Merged DataFrame shape after merge: {merged.shape}")

            for col in ['SDG', 'BatchID', 'Matrix']:
                if col not in merged.columns:
                    print(f"DEBUG: Column missing, creating: {col}")
                    merged[col] = ''
                else:
                    before_nulls = merged[col].isna().sum()
                    merged[col] = merged[col].fillna('')
                    after_nulls = merged[col].isna().sum()
                    print(f"DEBUG: Filled nulls on {col}: {before_nulls} → {after_nulls}")

        except Exception as e:
            print(f"DEBUG: Exception occurred during DQO query/merge: {e}")
            data_processing.debugger("DQO Error", str(e))
            return None

        finally:
            try:
                session.close()
                print("DEBUG: Database session closed")
            except NameError:
                print("DEBUG: No session to close")

        # If merged somehow is still None
        if merged is None:
            print("DEBUG: ERROR - merged is None after DQO section")
            return None

        print(f"DEBUG: Columns in merged now: {list(merged.columns)}")

        # Continue debugging downstream logic
        batch_ids = merged.loc[merged['BatchID'] != '', 'BatchID'].unique().tolist()
        print(f"DEBUG: Batch IDs found: {batch_ids}")

        # Now all samples that did not get a hit need to be handled.
        if len(batch_ids) == 1:
            merged['BatchID'] = merged['BatchID'].fillna(batch_ids[0])
            print("Successfully filled na batch ids.")

        elif 'AnalysisDateTime' in merged.columns.tolist():
            # We can handle missing batches by comparing to the closest datetime if that column exists (preferable)
            merged['AnalysisDateTime'] = pd.to_datetime(merged['AnalysisDateTime'], errors='coerce')

            # Split known vs unknown
            known = merged[merged['BatchID'].notna() & (merged['BatchID'] != '')][['BatchID', 'AnalysisDateTime']]
            unknown = merged[merged['BatchID'].isna() | (merged['BatchID'] == '')].index

            if known.empty:
                data_processing.debugger(
                    "Batch Assignment Error",
                    "No known BatchID values available. Cannot infer missing batches."
                )
                return merged

            # For each unknown, assign closest BatchID based on datetime difference
            for idx in unknown:
                t = merged.at[idx, 'AnalysisDateTime']
                if pd.isna(t):
                    continue  # can't infer without a timestamp

                # Compute time difference
                closest = known.iloc[(known['AnalysisDateTime'] - t).abs().argmin()]
                merged.at[idx, 'BatchID'] = closest['BatchID']
        
        else:
            merged['BatchID'] = merged['BatchID'].fillna(batch_ids[0])

        sdg_list = merged['SDG'].unique().tolist()
        print(sdg_list)
    
        if len(sdg_list) == 1:
            merged['SDG'] = merged['SDG'].fillna(sdg_list[0])
        else:
            data_processing.debugger("Error assigning SDGs", "There is more or less than one SDG in this data.")
            return None
        
        print("Made it past sdg list")
        
        matrix_list = merged['Matrix'].unique().tolist()
        print(matrix_list)

        if len(matrix_list) == 1:
            merged['Matrix'] = merged['Matrix'].fillna(matrix_list[0])
        else:
            data_processing.debugger("Error assigning matrices", "There is more or less than one sample matrix in this data.")
            return None
        
        print("Made it past matrix list")

        
        return merged
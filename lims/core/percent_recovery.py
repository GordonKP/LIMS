from lims.config.config import CONNECTION_STRING
from lims.config.tables import Base, ConsumableManagement
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

class PercentRecovery:
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
    def get_recoveries(df):
        consumable_df = PercentRecovery.query_consumables()

        # Combine concentration and activity columns
        consumable_df["Value"] = (
            consumable_df["Concentration"].fillna(consumable_df["Activity"])
        )

        # Clean whitespace for safety
        consumable_df["Component"] = consumable_df["Component"].str.replace(" ", "")
        df["Analyte"] = df["Analyte"].str.replace(" ", "")

        # Split consumable lists
        consumable_df["Method_list"] = consumable_df["Method"].str.split(",")
        consumable_df["Component_list"] = consumable_df["Component"].str.split(",")

        # Explode only consumables
        cons = consumable_df.explode("Method_list").explode("Component_list")

        # --- CRITICAL FIX: preserve df’s original row index ---
        df = df.copy()
        df["_orig_index"] = df.index

        df["ResultType_norm"] = df["ResultType"].replace({
            "LCSDUP": "LCS",
            "MSDUP": "Standard",
            "MS": "Standard"
        })

        # Merge (may produce multiple rows for each df row)
        merged = df.merge(
            cons,
            left_on=["Method", "Analyte", "ResultType_norm"],
            right_on=["Method_list", "Component_list", "Type"],
            how="left"
        )

        # --- Collapse back to original rows using preserved index ---
        qc_choices = (
            merged.groupby("_orig_index")["LotNumber"]
                .apply(lambda x: sorted(set(v for v in x if pd.notna(v))))
        )

        # Assign back
        df["QC_choices"] = qc_choices

        # Cleanup
        df.drop(columns=["_orig_index", "ResultType_norm"], inplace=True)

        # Create a dictionary for each possible lot number associated with SampleID
        lot_dict = {
            row['SampleID']: {row['QC_choices'], row['Compound']}
            for _, row in df.iterrows()
            if isinstance(row['QC_choices'], list) 
            and any(str(x).strip() != "" for x in row['QC_choices'])
        }
        print("Lot Dict")
        print(lot_dict)

        return df

    @staticmethod
    def query_consumables():
        try:
            session = PercentRecovery.init_session()

            stmt = (
                session.query(ConsumableManagement)
                .filter(ConsumableManagement.Status == 1)
                .statement
            )

            df = pd.read_sql(stmt, session.connection())

            print(df)

            return df

        except Exception as e:
            print(f"DEBUG: Exception occurred during DQO query/merge: {e}")
            PercentRecovery.debugger("Error Fetching Consumables", str(e))
            return None
        finally:
            try:
                session.close()
                print("DEBUG: Database session closed")
            except NameError:
                print("DEBUG: No session to close")
    
    @staticmethod
    def lcs_recovery(self):
        return
    
    @staticmethod
    def ms_recovery(self):
        return
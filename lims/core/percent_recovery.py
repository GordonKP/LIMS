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

        # --- Preserve df's original row index ---
        df = df.copy()
        df["_orig_index"] = df.index

        df["ResultType_norm"] = df["ResultType"].replace({
            "LCSDUP": "LCS",
            "MSDUP": "Standard",
            "MS": "Standard"
        })

        # Merge (may produce multiple rows per df row)
        merged = df.merge(
            cons,
            left_on=["Method", "Analyte", "ResultType_norm"],
            right_on=["Method_list", "Component_list", "Type"],
            how="left"
        )

        # --- Collapse consumable info per original row ---
        qc_choices = (
            merged.groupby("_orig_index")["LotNumber"]
                  .apply(lambda x: sorted(set(v for v in x if pd.notna(v))))
        )

        compounds = (
            merged.groupby("_orig_index")["Compound"]
                  .apply(lambda x: next((v for v in x if pd.notna(v)), None))
        )

        df["QC_choices"] = qc_choices
        df["QC_Aliquot_Units"] = compounds

        # Cleanup
        df.drop(columns=["_orig_index", "ResultType_norm"], inplace=True)

        # Build lot_dict for UI selection
        lot_dict = {
            row['SampleID']: {
                "QC_choices": row['QC_choices'],
                "QC_Aliquot_Units": row['QC_Aliquot_Units']
            }
            for _, row in df.iterrows()
            if isinstance(row['QC_choices'], list)
            and any(str(x).strip() != "" for x in row['QC_choices'])
        }

        print("Lot Dict")
        print(lot_dict)
        print(df)

        dialog = QCSelectionDialog(lot_dict)

        if dialog.exec_():
            qc_results = dialog.get_results()
            print(qc_results)
        else:
            return None
                
        # For each lot, fetch the associated Consumable to get the Analytes and their Activity/Concentration
        for key, value in qc_results.items():
            qc_lot = value["QC_Lot"]

            # Filter cons for QC Lot
            qc_rows = cons[cons["LotNumber"] == qc_lot]

            # Build a mapping dictionary of Component: Value
            analyte_map = dict(zip(qc_rows["Component"], qc_rows["Value"]))

            # Add it back into dictionary under this key
            raw_analytes = qc_rows["Component"].iloc[0]
            raw_values = qc_rows["Value"].iloc[0]

            analytes = [a.strip() for a in raw_analytes.split(',')]
            values = [float(v) for v in raw_values.split(',')]

            qc_results[key]["Map"] = dict(zip(analytes, values))

        print(qc_results)

        def calculate_qc_values(row):
            sample_id = row['SampleID']
            analyte = row['Analyte']

            print(f"\n--- Processing Row ---")
            print(f"SampleID: {sample_id}, Analyte: {analyte}")

            # Case 1: SampleID not in qc_results
            if sample_id not in qc_results:
                print("❌ SampleID not in qc_results. Skipping.")
                return None

            qc_entry = qc_results[sample_id]
            print(f"Found QC entry for {sample_id}: {qc_entry}")

            # Component map
            known_map = qc_entry.get("Map", {})
            print(f"Known analyte map: {known_map}")

            # Find expected QC value
            known_value = known_map.get(analyte)
            if known_value is None:
                print(f"❌ Analyte '{analyte}' not found in Map for sample {sample_id}.")
                return None

            print(f"✔ Known component value for '{analyte}': {known_value}")

            # Aliquot handling
            try:
                aliquot = float(qc_entry["Aliquot"])
                print(f"Aliquot converted to float: {aliquot}")
            except Exception as e:
                print(f"❌ Aliquot conversion failed for sample {sample_id}: {qc_entry['Aliquot']}")
                print("Error:", e)
                return None

            # Final computed QC value
            qc_value = known_value * aliquot
            print(f"🎯 Computed QC_Value: {known_value} * {aliquot} = {qc_value}")

            return qc_value

        df["QC_Value"] = df.apply(calculate_qc_values, axis=1)
        df = df.drop(columns=['QC_choices', 'QC_Aliquot_Units'])

        def calculate_recovery(row):
            result_type = row['ResultType']

            if result_type.startswith(("LCS", "MS")):
                aliquot = float(row['Aliquot'])
                result = float(row['Result'])
                sample_value = result * aliquot
                qc_value = float(row['QC_Value'])
            else:
                percent_recovery = 0.0
            
            if 'LCS' in result_type:
                percent_recovery = round(100 * ((sample_value)/qc_value), 2)

            elif 'MS' in result_type:
                MS_sample_id = row['SampleID']

                if MS_sample_id.endswith("MSDUP"):
                    parent_sample_id = str(row['SampleID'])[:-5]
                elif MS_sample_id.endswith("MS"):
                    parent_sample_id = str(row['SampleID'])[:-2]
                else:
                    PercentRecovery.debugger("Sample ID Error", f"Matrix Spike detected via ResultType, however the SampleID does not follow MS/MSDUP naming conventions.\nSampleID: {MS_sample_id}")
                    percent_recovery = 0.0
                
                batch_id = row['BatchID']
                analyte = row['Analyte']

                parent_row = df[
                    (df['BatchID'] == batch_id) &
                    (df['Analyte'] == analyte) &
                    (df['SampleID'] == parent_sample_id)
                ]

                if len(parent_row) > 1:
                    PercentRecovery.debugger("Error Getting Parent ID", f"More than one parent ID was found for {MS_sample_id}.")
                    percent_recovery = 0.0
                if parent_row.empty:
                    PercentRecovery.debugger("Error Getting Parent ID", f"No parent ID was found for {MS_sample_id}.")
                    percent_recovery = 0.0
                
                parent_result = float(parent_row.iloc[0]['Result'])
                parent_aliquot = float(parent_row.iloc[0]['Aliquot'])
                parent_value = parent_result * parent_aliquot

                percent_recovery = round(100 * ((sample_value - parent_value)/qc_value), 2)

            else:
                percent_recovery = 0.0

            return percent_recovery
        
        df["PercentRecovery"] = df.apply(calculate_recovery, axis=1)
        
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
            print(f"DEBUG: Exception occurred during query: {e}")
            PercentRecovery.debugger("Error Fetching Consumables", str(e))
            return None
        finally:
            try:
                session.close()
                print("DEBUG: Database session closed")
            except NameError:
                print("DEBUG: No session to close")
    
# ================================================================
#                   QC SELECTION POPUP DIALOG
# ================================================================

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QPushButton, QHeaderView
)
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt


class QCSelectionDialog(QDialog):
    def __init__(self, lot_dict, parent=None):
        super().__init__(parent)

        self.setWindowTitle("QC Lot Selection")
        self.resize(900, 500)

        layout = QVBoxLayout(self)

        # --- Table Setup ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Sample ID", "QC Lot", "Aliquot", "Units"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.populate_table(lot_dict)
        layout.addWidget(self.table)

        # OK Button
        btn = QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def populate_table(self, lot_dict):
        self.table.setRowCount(len(lot_dict))

        for row_idx, (sample_id, qc_info) in enumerate(lot_dict.items()):

            # --- Sample ID (read-only) ---
            sample_edit = QLineEdit(sample_id)
            sample_edit.setReadOnly(True)
            self.table.setCellWidget(row_idx, 0, sample_edit)

            # --- QC Lot ComboBox ---
            qc_combo = QComboBox()
            qc_combo.addItems(qc_info["QC_choices"])
            self.table.setCellWidget(row_idx, 1, qc_combo)

            # --- Aliquot (float only QLineEdit) ---
            aliquot_edit = QLineEdit()
            aliquot_edit.setPlaceholderText("Enter aliquot amount")
            aliquot_edit.setValidator(QDoubleValidator(0.0, 999999.99, 10))
            self.table.setCellWidget(row_idx, 2, aliquot_edit)

            # --- Units (read-only) ---
            unit_edit = QLineEdit(qc_info["QC_Aliquot_Units"])
            unit_edit.setReadOnly(True)
            self.table.setCellWidget(row_idx, 3, unit_edit)

    def get_results(self):
        """Return user-selected QC info in a dict."""
        results = {}

        for row in range(self.table.rowCount()):
            sample = self.table.cellWidget(row, 0).text()
            qc_lot = self.table.cellWidget(row, 1).currentText()
            aliquot = self.table.cellWidget(row, 2).text()
            units = self.table.cellWidget(row, 3).text()

            results[sample] = {
                "QC_Lot": qc_lot,
                "Aliquot": aliquot,
                "Units": units
            }

        return results

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

    @staticmethod
    def lcs_recovery(self):
        return
    
    @staticmethod
    def ms_recovery(self):
        return

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
            aliquot_edit.setValidator(QDoubleValidator(0.0, 999999.99, 4))
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

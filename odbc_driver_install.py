import os
import pyodbc
from PyQt5.QtWidgets import QApplication, QMessageBox
import webbrowser


REQUIRED_DRIVER = 'ODBC Driver 17 for SQL Server'

def driver_installed():
    print("Checking installed ODBC drivers...")
    drivers = pyodbc.drivers()
    for driver in drivers:
        if REQUIRED_DRIVER in driver:
            print(f"[✓] Found: {REQUIRED_DRIVER}")
            return True
    print(f"[✗] {REQUIRED_DRIVER} not found.")
    return False

def ensure_driver():
    if driver_installed():
        return True

    # Create a temp QApplication only if one doesn't exist
    app_created = False
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app_created = True

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("ODBC Driver Missing")
    msg.setText(
        "The required ODBC Driver 17 for SQL Server is not installed.\n\n"
        "Please download and install it from Microsoft before running this application."
    )
    msg.setInformativeText("Click 'Download' to open the official installer page.")
    download_btn = msg.addButton("Download", QMessageBox.AcceptRole)
    msg.addButton("Cancel", QMessageBox.RejectRole)

    msg.exec_()

    if msg.clickedButton() == download_btn:
        webbrowser.open("https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")

    if app_created:
        app.quit()

    return False
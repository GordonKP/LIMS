import pandas as pd

class PrepDateTime:
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
    def get_prep_datetime(df: pd.DataFrame, column_name: str = "PrepDateTime"):
        """
        Opens a dialog for the user to select the prep finalization datetime.
        If user cancels, returns None.
        If user confirms, returns df with a populated column (default 'PrepDateTime').
        """
        dialog = PrepDateTimeDialog()

        if dialog.exec_():  # accepted
            prep_dt = dialog.get_datetime()
            if prep_dt is None:
                PrepDateTime.debugger(
                    "Invalid Date/Time",
                    "Please choose a valid prep date and time."
                )
                return None

            # Ensure column exists and is datetime dtype
            df = df.copy()
            df['PrepDateTime'] = pd.to_datetime(prep_dt)

            return df

        # canceled
        return None


# ================================================================
#                   PrepDateTime SELECTION POPUP DIALOG
# ================================================================

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QCalendarWidget, QTimeEdit, QHBoxLayout
)
from PyQt5.QtCore import QTime
from datetime import datetime


class PrepDateTimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Prep Date/Time")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Message
        msg = QLabel("When was the prep for this batch finalized?")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Calendar (date)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        # Time selector
        time_row = QHBoxLayout()
        time_label = QLabel("Time (24-hour):")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setMinimumWidth(120)

        time_row.addWidget(time_label)
        time_row.addWidget(self.time_edit)
        time_row.addStretch(1)
        layout.addLayout(time_row)

        # Buttons
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def get_datetime(self):
        """
        Returns a python datetime combining the selected calendar date + time,
        or None if something is invalid.
        """
        try:
            qdate = self.calendar.selectedDate()
            qtime = self.time_edit.time()

            year = qdate.year()
            month = qdate.month()
            day = qdate.day()

            hour = qtime.hour()
            minute = qtime.minute()

            return datetime(year, month, day, hour, minute, 0)
        except Exception:
            return None

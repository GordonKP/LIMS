from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

class Popup:

    @staticmethod
    def debugger(title, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setWindowModality(Qt.ApplicationModal)
        msg.exec_()

    @staticmethod
    def info(title, text):
        QMessageBox.information(None, str(title), str(text))

    @staticmethod
    def choice(title, text, choices):
        """
        Show a choice dialog with custom buttons.

        choices should be a list of button labels (strings).

        Returns:
            str: text of clicked button, or None.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))
        msg.setWindowModality(Qt.ApplicationModal)

        buttons = {}

        for choice in choices:
            btn = msg.addButton(choice, QMessageBox.ActionRole)
            buttons[btn] = choice

        msg.exec_()
        return buttons.get(msg.clickedButton(), None)

import sys
import os
from lims.config import config, file_paths, lab_lists
from lims.core import consumable_form
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1)
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QDateTime, QEvent, QSettings, QTime, QDate, QTimer, pyqtSignal, QDataStream
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFormLayout, QListWidgetItem, QVBoxLayout, QMenu, QListWidget, QScrollArea, QMessageBox, QHeaderView, QCompleter, QTreeWidget, QTreeWidgetItem, QTableWidget, QTimeEdit, QDateEdit, QTableWidgetItem, QLineEdit, QTextEdit, QSpacerItem, QRadioButton, QComboBox, QGridLayout, QPushButton, QLabel, QCheckBox, QFileDialog, QWidget, QStackedWidget, QFrame, QHBoxLayout, QSizePolicy, QDesktopWidget, QSplitter, QButtonGroup
from PyQt5.QtGui import QTextCursor, QTextBlockFormat, QIcon, QPixmap, QFont, QFontDatabase, QIcon
from sqlalchemy import Table, create_engine, MetaData, between, and_, func, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from datetime import datetime
import re
import traceback
import logging
import statistics
import lims.resources_rc
import lims.core.preload_modules
import lims.config.patterns
from lims.config.tables import (User, SampleLogin, DQO, CoC, LIMSLimits, LIMSActivity, ConsumableManagement, EquipmentManagement,
RADCerts, Verifications)

import subprocess
from lims.core.Version import Version
from lims import __version__ 

import odbc_driver_install

if not odbc_driver_install.ensure_driver():
    sys.exit(1)

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)

Base = declarative_base()

settings = QSettings("Leidos", "LIMS")
settings.setValue("lab_code", "SL")

class DragAndDropLabel(QLabel):
    def __init__(self, file_list_widget, parent=None):
        super().__init__(parent)
        self.file_list_widget = file_list_widget
        self.setAlignment(Qt.AlignCenter)
        self.setText("\n\n Or Drop Files Here \n\n")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                font-size: 12px;
            }
        """)
        self.setFixedHeight(300)
        self.setFixedWidth(300)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
            print(f"Files dropped: {file_paths}")  # Debugging print
            self.add_files(file_paths)

    def add_files(self, file_paths):
        for file_path in file_paths:
            print(f"Adding file: {file_path}")  # Debugging print
            self.file_list_widget.addItem(file_path)

        # Check what the list contains after adding files
        print("Current file list:", self.file_list_widget.get_file_paths())

class BatchBox(QFrame):
    def __init__(self, label_text):
        super().__init__()
        self.initUI(label_text)
        
    def initUI(self, label_text):
        self.setFrameShape(QFrame.Box)
        self.setAcceptDrops(True)
        self.setMinimumSize(150, 200)
        
        self.layout = QVBoxLayout()
        
        self.label = QLabel(label_text)
        self.layout.addWidget(self.label)
        
        self.sample_list = QListWidget()
        self.sample_list.setDragEnabled(True)
        self.sample_list.setAcceptDrops(True)
        self.sample_list.setDragDropMode(QListWidget.InternalMove)
        
        self.layout.addWidget(self.sample_list)
        
        self.setLayout(self.layout)
        
    def populate_samples(self, samples):
        self.sample_list.clear()
        for sample in samples:
            item = QListWidgetItem(sample)
            self.sample_list.addItem(item)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.accept()
        else:
            event.ignore()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.accept()
        else:
            event.ignore()
        
    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.setDropAction(Qt.MoveAction)
            event.accept()
            
            # Extract the dropped item data
            data = event.mimeData()
            source = event.source()
            
            if source and source is not self.sample_list:
                item_data = data.data('application/x-qabstractitemmodeldatalist')
                item_text = self.decode_data(item_data)
                
                # Add the dropped item to the current list
                self.add_sample(item_text)
                
                # Remove the dropped item from the source list after a short delay
                def remove_item():
                    for index in range(source.count()):
                        if source.item(index).text() == item_text:
                            source.takeItem(index)
                            break
                
                QTimer.singleShot(10, remove_item)  # Delay of 10 milliseconds
        else:
            event.ignore()
            
    def add_sample(self, sample):
        item = QListWidgetItem(sample)
        self.sample_list.addItem(item)
        
    def clear_samples(self):
        self.sample_list.clear()

    def decode_data(self, data):
        # This function decodes the QByteArray to retrieve the text of the QListWidgetItem
        text = ""
        stream = QDataStream(data)
        while not stream.atEnd():
            row = stream.readInt32()
            column = stream.readInt32()
            map_items = stream.readInt32()
            for i in range(map_items):
                role = stream.readInt32()
                value = stream.readQVariant()
                if role == Qt.DisplayRole:
                    text = value
        return text
    
class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

    def open_context_menu(self, position):
        menu = QMenu()
        remove_action = menu.addAction("Remove")
        action = menu.exec_(self.mapToGlobal(position))
        if action == remove_action:
            self.remove_selected_items()

    def remove_selected_items(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))

    def get_file_paths(self):
        file_paths = []
        for index in range(self.count()):
            original_path = self.item(index).text()
            safe_path = self.resource_path(original_path)
            file_paths.append(safe_path)
        return file_paths
    
    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller .exe"""
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

class QMultiSelectBox(QWidget):
    buttonClicked = pyqtSignal()
    textChanged = pyqtSignal(str)  # Define a new signal

    def __init__(self, parent=None):
        super(QMultiSelectBox, self).__init__(parent)

        # Initialize the container widget
        self.container_widget = QWidget(self)
        container_layout = QHBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignLeft)

        # Initialize the input field
        self.input_field = QLineEdit(self.container_widget)

        # Initialize the button
        self.button = QPushButton()

        # Connect button click signal to custom slot
        self.button.clicked.connect(self.emit_button_clicked)

        list_icon_path = self.resource_path(os.path.join('images', 'list-ul.svg'))
        list_icon = QIcon(list_icon_path)

        # Set the button icon
        self.button.setIcon(list_icon)

        # Add widgets to container layout
        container_layout.addWidget(self.input_field)
        container_layout.addWidget(self.button)

        # Set the layout to the container widget
        self.container_widget.setLayout(container_layout)

        # Set the layout of the main widget
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container_widget)
        self.setLayout(main_layout)

        main_layout.setContentsMargins(0, 0, 0, 0)

        # Connect the input field's textChanged signal to the custom slot
        self.input_field.textChanged.connect(self.emit_text_changed)

    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    def getCurrentText(self):
        return self.input_field.text()
    
    def setCurrentText(self, text):
        self.input_field.setText(text)
    
    def emit_button_clicked(self):
        # Emit the custom signal when the button is clicked
        self.buttonClicked.emit()

    def emit_text_changed(self, text):
        # Emit the custom signal when the text in the input field changes
        self.textChanged.emit(text)

class UniqueCharacterPopup(QDialog):
    def __init__(self, input_field):
        super().__init__(flags=Qt.WindowStaysOnToPHint)
        self.input_field = input_field

        self.initUI()

        QTimer.singleShot(50, self.ensure_focus_on_input)

    def initUI(self):
        self.setWindowTitle("Unique Characters")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        screen_geometry = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, int(screen_geometry.width() * .015), int(screen_geometry.height() * 0.4))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header_font_path = os.path.join(file_paths.fonts_directory, 'AvenirNextCyr-Regular.ttf')

        # Load the fonts
        header_font_id = QFontDatabase.addApplicationFont(header_font_path)
        header_font_family = QFontDatabase.applicationFontFamilies(header_font_id)[0]
        self.header_font = QFont(header_font_family, 14)

        self.content = QGridLayout()

        self.show_characters()

        self.setLayout(self.content)

        self.center_window()

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def ensure_focus_on_input(self):
        """Ensures the input field gets focus after the popup appears."""
        self.input_field.window().activateWindow()
        self.input_field.moveCursor(QTextCursor.End)
        self.input_field.setFocus()
        QApplication.processEvents()

    def show_characters(self):
        uppercase_greek = [
            'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω'
        ]

        lowercase_greek = [
            'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω'
        ]

        normal_chars = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'α', 'β', 'γ', 'ρ', 'Ρ', 'υ', 'ν'
        ]
        subscript_chars = [
            '₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉', 'ₐ', 'ᵦ', 'ᵧ', 'ᵨ', 'ᵣ', 'ᵤ', 'ᵥ'
        ]

        grid_layout1 = QGridLayout()
        grid_layout2 = QGridLayout()
        grid_layout3 = QGridLayout()

        for index, char in enumerate(uppercase_greek):
            button = QPushButton(char)
            button.setFixedWidth(50)
            button.setFixedHeight(50)
            button.clicked.connect(self.create_insert_callback(char))
            grid_layout1.addWidget(button, index // 10, index % 10)

        for index, char in enumerate(lowercase_greek):
            button = QPushButton(char)
            button.setFixedWidth(50)
            button.setFixedHeight(50)
            button.clicked.connect(self.create_insert_callback(char))
            grid_layout2.addWidget(button, index // 10, index % 10)

        for index, (normal_char, subscript_char) in enumerate(zip(normal_chars, subscript_chars)):
            button = QPushButton(normal_char)
            button.setFixedWidth(50)
            button.setFixedHeight(50)
            button.clicked.connect(self.create_insert_callback(subscript_char))
            grid_layout3.addWidget(button, index // 10, index % 10)

        self.character_grid1 = QWidget()
        self.character_grid1.setLayout(grid_layout1)

        self.character_grid2 = QWidget()
        self.character_grid2.setLayout(grid_layout2)

        self.character_grid3 = QWidget()
        self.character_grid3.setLayout(grid_layout3)

        label1 = QLabel("Uppercase Greek Characters")
        label1.setFont(self.header_font)

        label2 = QLabel("Lowercase Greek Characters")
        label2.setFont(self.header_font)

        label3 = QLabel("Subscript Characters")
        label3.setFont(self.header_font)

        self.content.addWidget(label1, 1, 0, 1, 3, Qt.AlignHCenter)
        self.content.addWidget(self.character_grid1, 2, 0, 1, 3, Qt.AlignHCenter)

        self.content.addWidget(label2, 3, 0, 1, 3, Qt.AlignHCenter)
        self.content.addWidget(self.character_grid2, 4, 0, 1, 3, Qt.AlignHCenter)

        self.content.addWidget(label3, 5, 0, 1, 3, Qt.AlignHCenter)
        self.content.addWidget(self.character_grid3, 6, 0, 1, 3, Qt.AlignHCenter)

    def create_insert_callback(self, char):
        def insert_char():
            cursor = self.input_field.textCursor()
            cursor.insertText(char)

            # Bring the main window back into focus
            self.input_field.window().activateWindow()

            self.input_field.moveCursor(QTextCursor.End)

            # Ensure the input field retains focus
            self.input_field.setFocus()

            # Process any pending events to ensure focus change is applied
            QApplication.processEvents()

        return insert_char

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # Calculate the x and y positions
        x = screen_geometry.left() + self.frameGeometry().width()  # Right edge minus the window's total width (including frame)
        y = screen_geometry.top() + self.frameGeometry().height() # Top edge of the screen
        
        # Move the window to the calculated position
        self.move(x, y)

class FocusableTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def event(self, event):
        if event.type() == QEvent.FocusIn:
            self.focus_in_event(event)
        return super().event(event)
    
    def focus_in_event(self, event):
        super().focusInEvent(event)

class QSubscriptInput(QWidget):
    buttonClicked = pyqtSignal()
    textChanged = pyqtSignal(str)  # Define a new signal

    def __init__(self, parent=None):
        super(QSubscriptInput, self).__init__(parent)

        # Initialize the container widget
        self.container_widget = QWidget(self)
        container_layout = QHBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignLeft)

        # Initialize the input field
        self.input_field = QTextEdit(self.container_widget)

        line_height = self.input_field.fontMetrics().lineSpacing()
        self.input_field.setFixedHeight(line_height + 10)

        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(size_policy)

        self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.input_field.setStyleSheet("padding-bottom: 2px;")

        # Apply block format for vertical centering
        cursor = self.input_field.textCursor()
        block_format = QTextBlockFormat()
        block_format.setAlignment(Qt.AlignLeft)
        cursor.select(QTextCursor.Document)
        cursor.setBlockFormat(block_format)
        self.input_field.setTextCursor(cursor)

        # Initialize the button
        self.button = QPushButton()

        # Connect button click signal to custom slot
        self.button.clicked.connect(self.emit_button_clicked)

        list_icon_path = self.resource_path(os.path.join('images', 'table.svg'))
        list_icon = QIcon(list_icon_path)

        # Set the button icon
        self.button.setIcon(list_icon)

        # Add widgets to container layout
        container_layout.addWidget(self.input_field)
        container_layout.addWidget(self.button)

        # Set the layout to the container widget
        self.container_widget.setLayout(container_layout)

        # Set the layout of the main widget
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container_widget)
        self.setLayout(main_layout)

        main_layout.setContentsMargins(0, 0, 0, 0)

        # Connect the input field's textChanged signal to the custom slot
        self.input_field.textChanged.connect(self.emit_text_changed)

    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
        
    def getCurrentText(self):
        return self.input_field.toPlainText()
    
    def setCurrentText(self, text):
        self.input_field.setText(text)
    
    def emit_button_clicked(self):
        # Check if the popup exists and is visible
        if hasattr(self, 'popup') and self.popup.isVisible():
            # Close the popup if it's already open
            self.popup.close()
        else:
            # Create and show the popup if it's not open
            self.popup = UniqueCharacterPopup(self.input_field)
            self.popup.show()

        # Emit the custom signal when the button is clicked
        self.buttonClicked.emit()

    def emit_text_changed(self):
        # Emit the custom signal when the text in the input field changes
        text = self.getCurrentText()
        self.textChanged.emit(text)

class LoginRegister(QMainWindow):
    def __init__(self):
        super().__init__()

        release = Version.is_update_available(__version__)
        if release:
            reply = QMessageBox.question(self, "Update Available",
                f"A new version ({release['version']}) is available. Update now?",
                QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                import json, tempfile
                # ✅ Save update_info.json to a temp location
                temp_dir = tempfile.gettempdir()
                info_path = os.path.join(temp_dir, "update_info.json")
                print(f"📝 Writing update_info.json to: {info_path}")
                with open(info_path, "w") as f:
                    json.dump(release, f)

                # ✅ Get full path to updater.exe
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                
                updater_path = os.path.join(base_dir, "updater.exe")

                # ✅ Check before launching
                if not os.path.exists(updater_path):
                    QMessageBox.critical(self, "Updater Not Found", f"Updater executable not found at: {updater_path}")
                else:
                    print(f"🚀 Launching updater: {updater_path} {info_path}")
                    subprocess.Popen([updater_path, info_path])
                    sys.exit()

        # Initialize the UI
        self.init_ui()

        # Initialize the layout
        self.layout = QVBoxLayout()

        self.init_fonts()

        # Initialize the banner
        self.init_banner()

        # Create a stacked widget to hold login and register widgets
        self.stacked_widget = QStackedWidget()

        # Add the stacked widget to the layout
        self.layout.addWidget(self.stacked_widget, alignment=Qt.AlignCenter)

        # Initialize login and register widgets
        self.login_widget = QWidget()
        self.register_widget = QWidget()

        # Initialize the login UI
        self.init_login_ui()
        
        # Initialize the register UI
        self.init_register_ui()

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        # Set the initial widget to login widget
        self.stacked_widget.setCurrentWidget(self.login_widget)

        # Initialize a member variable to hold MainMenu instance
        self.main_menu = None

        self.check_login_status()

    def init_ui(self):
        # Create main window title and icon
        self.setWindowTitle("Log In")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.25
        height_percent = 0.5

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of login window
        self.setGeometry(0, 0, self.width, self.height)

        # Center the window on the screen
        self.center_window()

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(config.CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def init_banner(self):
        # Create a QHBoxLayout to hold the banner label and image label
        banner_layout = QHBoxLayout()
        banner_layout.setSpacing(0)

        # Add the banner label
        banner_label = QLabel("LIMS Log In")
        banner_label.setStyleSheet("background-color: #901588; color: white; padding: 5%")
        banner_label.setFixedHeight(50)

        banner_label.setFont(self.bold_font)

        # Add the image label
        image_label = QLabel()
        pixmap = QPixmap(os.path.join(file_paths.images_directory, 'leidos_logo_white.png'))
        image_label.setPixmap(pixmap)
        image_label.setMaximumSize(banner_label.sizeHint())

        # Scale the pixmap to fit within the maximum size of the image label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)

        # Align the image label to the top right and center it horizontally
        image_label.setAlignment(Qt.AlignRight | Qt.AlignHCenter)
        image_label.setStyleSheet("background-color: #901588; color: white; font-size: 24px; padding: 5%")

        # Add the banner label and image label to the banner layout
        banner_layout.addWidget(banner_label)
        banner_layout.addWidget(image_label)

        # Add the banner layout to the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(banner_layout)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create a widget to hold the layout
        banner_widget = QWidget()
        banner_widget.setLayout(self.layout)
        self.setCentralWidget(banner_widget)

    def init_fonts(self):
        """Load and initialize fonts from Qt Resource System."""
        print("🔍 Checking fonts in Qt Resources...")

        # Use the correct resource path
        font_id = QFontDatabase.addApplicationFont(":/AvenirNextCyr-Regular.ttf")
        bold_font_id = QFontDatabase.addApplicationFont(":/AvenirNextCyr-Bold.ttf")

        if font_id == -1 or bold_font_id == -1:
            print("⚠️ Font loading failed, using system default.")
            self.default_font = QFont("Arial", 10)
            self.bold_font = QFont("Arial", 16)
            self.header_font = QFont("Arial", 14)
            return

        font_family = QFontDatabase.applicationFontFamilies(font_id)
        bold_font_family = QFontDatabase.applicationFontFamilies(bold_font_id)

        if not font_family or not bold_font_family:
            print("⚠️ Font family not found, using default fonts.")
            self.default_font = QFont("Arial", 10)
            self.bold_font = QFont("Arial", 16)
            self.header_font = QFont("Arial", 14)
            return

        self.default_font = QFont(font_family[0], 10)
        self.bold_font = QFont(bold_font_family[0], 16)
        self.header_font = QFont(bold_font_family[0], 14)

        self.setFont(self.default_font)
        print(f"✅ Loaded Fonts: Default={self.default_font.family()}, Bold={self.bold_font.family()}")
    
    def init_login_ui(self):
        # Create another QVBoxLayout for the input fields and buttons
        login_layout = QVBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)  # Center the widgets horizontally

        # Add spacing between the banner and the input fields
        login_layout.addSpacing(int(0.1 * self.height))  # Adjust spacing as needed

        # Create username and password labels and inputs
        from PyQt5.QtWidgets import QLineEdit
        self.username_label = QLabel("Username")
        self.username_input = QLineEdit(self)
        self.username_input.returnPressed.connect(self.focus_password_input)

        self.password_label = QLabel("Password")
        self.password_input = QLineEdit(self)

        # Set the echo mode of the password input field to Password
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.verify_credentials)

        # Create login and register buttons
        from PyQt5.QtWidgets import QPushButton
        self.login_button = QPushButton("Log in", self)
        self.login_button.clicked.connect(self.verify_credentials)

        self.register_button = QPushButton("Create an Account", self)
        self.register_button.clicked.connect(self.switch_to_register)

        # Set maximum width of widgets
        widget_width = int(0.35 * self.width)
        self.username_label.setFixedWidth(widget_width)
        self.username_input.setFixedWidth(widget_width)
        self.password_label.setFixedWidth(widget_width)
        self.password_input.setFixedWidth(widget_width)
        self.login_button.setFixedWidth(widget_width)
        self.register_button.setFixedWidth(widget_width)

        # Add widgets to the form layout
        login_layout.addWidget(self.username_label)
        login_layout.addWidget(self.username_input)
        login_layout.addWidget(self.password_label)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(self.login_button)
        login_layout.addWidget(self.register_button)

        # Set the form layout as central widget
        self.login_widget.setLayout(login_layout)
        self.stacked_widget.addWidget(self.login_widget)  # Add login widget to stacked widget
    
    def focus_password_input(self):
        self.password_input.setFocus()

    def init_register_ui(self):
        # Create another QVBoxLayout for the input fields and buttons
        register_layout = QVBoxLayout()
        register_layout.setAlignment(Qt.AlignCenter)  # Center the widgets horizontally

        # Add spacing between the banner and the input fields
        register_layout.addSpacing(int(0.1 * self.height))  # Adjust spacing as needed

        # Create username and password labels and inputs
        from PyQt5.QtWidgets import QLineEdit
        self.register_employee_id_label = QLabel("Employee ID")
        self.register_employee_id_input = QLineEdit(self)
        self.register_employee_id_input.returnPressed.connect(self.focus_register_first_name_input)

        self.register_first_name_label = QLabel("First Name")
        self.register_first_name_input = QLineEdit(self)
        self.register_first_name_input.returnPressed.connect(self.focus_register_last_name_input)

        self.register_last_name_label = QLabel("Last Name")
        self.register_last_name_input = QLineEdit(self)
        self.register_last_name_input.returnPressed.connect(self.focus_register_username_input)
        
        self.register_username_label = QLabel("Username")
        self.register_username_input = QLineEdit(self)
        self.register_username_input.returnPressed.connect(self.focus_register_password_input)

        self.register_password_label = QLabel("Password")
        self.register_password_input = QLineEdit(self)
        self.register_password_input.setEchoMode(QLineEdit.Password)
        self.register_password_input.returnPressed.connect(self.focus_register_confirm_password_input)

        self.register_confirm_password_label = QLabel("Confirm Password")
        self.register_confirm_password_input = QLineEdit(self)
        self.register_confirm_password_input.setEchoMode(QLineEdit.Password)
        self.register_confirm_password_input.returnPressed.connect(self.register_account)

        # Create login and register buttons
        from PyQt5.QtWidgets import QPushButton
        self.register_register_button = QPushButton("Register", self)
        self.register_register_button.clicked.connect(self.register_account)

        self.register_back_to_login_button = QPushButton("Back to Log In", self)
        self.register_back_to_login_button.clicked.connect(self.switch_to_login)

        # Set maximum width of widgets
        widget_width = int(0.35 * self.width)
        self.register_employee_id_label.setFixedWidth(widget_width)
        self.register_employee_id_input.setFixedWidth(widget_width)
        self.register_first_name_label.setFixedWidth(widget_width)
        self.register_first_name_input.setFixedWidth(widget_width)
        self.register_last_name_label.setFixedWidth(widget_width)
        self.register_last_name_input.setFixedWidth(widget_width)
        self.register_username_label.setFixedWidth(widget_width)
        self.register_username_input.setFixedWidth(widget_width)
        self.register_password_label.setFixedWidth(widget_width)
        self.register_password_input.setFixedWidth(widget_width)
        self.register_confirm_password_label.setFixedWidth(widget_width)
        self.register_confirm_password_input.setFixedWidth(widget_width)
        self.register_register_button.setFixedWidth(widget_width)

        # Add widgets to the form layout
        register_layout.addWidget(self.register_employee_id_label)
        register_layout.addWidget(self.register_employee_id_input)
        register_layout.addWidget(self.register_first_name_label)
        register_layout.addWidget(self.register_first_name_input)
        register_layout.addWidget(self.register_last_name_label)
        register_layout.addWidget(self.register_last_name_input)
        register_layout.addWidget(self.register_username_label)
        register_layout.addWidget(self.register_username_input)
        register_layout.addWidget(self.register_password_label)
        register_layout.addWidget(self.register_password_input)
        register_layout.addWidget(self.register_confirm_password_label)
        register_layout.addWidget(self.register_confirm_password_input)
        register_layout.addWidget(self.register_register_button)
        register_layout.addWidget(self.register_back_to_login_button)

        # Set the form layout as central widget
        self.register_widget.setLayout(register_layout)
        self.stacked_widget.addWidget(self.register_widget)  # Add register widget to stacked widget

    def center_window(self):
        # Get the screen geometry
        screen_geometry = QDesktopWidget().screenGeometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Calculate the top-left point of the window to center it
        top_left_point = center_point - self.rect().center()

        # Move the window to the calculated position
        self.move(top_left_point)  
    
    def focus_register_first_name_input(self):
        # Define a slot to set focus to the first name input field
        self.register_first_name_input.setFocus()

    def focus_register_last_name_input(self):
        self.register_last_name_input.setFocus()

    def focus_register_username_input(self):
        self.register_username_input.setFocus()

    def focus_register_password_input(self):
        self.register_password_input.setFocus()

    def focus_register_confirm_password_input(self):
        self.register_confirm_password_input.setFocus()
    
    def verify_credentials(self):
        import bcrypt
        username = self.username_input.text()
        password = self.password_input.text()

        # Initialize the db connection
        self.init_session()

        if not all([username, password]):
            QMessageBox.critical(self, "Error", "Please input username and password!")
            return

        try:
            user = self.session.query(User).filter(User.UserName == username).first()

            if user:
                hashed_password = user.PasswordHash.encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    # Cache the username
                    settings.setValue("username", username)
                    
                    # Update LastLogin column with current time
                    user.LastLogin = datetime.now()
                    self.session.commit()  # Commit the transaction to persist changes to the database

                    # Log the activity
                    try:
                        current_datetime = datetime.now()
                        log_entry = LIMSActivity(
                            User=username,
                            TablesAffected="Users",
                            Action=f"{username} logged in",
                            Notes="",
                            Date=current_datetime.date(),
                            Time=current_datetime.time()
                        )
                        self.session.add(log_entry)
                        self.session.commit()
                    except SQLAlchemyError as log_error:
                        QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                        self.session.rollback()

                    self.show_main_menu()
                else:
                    QMessageBox.critical(self, "Error", "Invalid username or password!")
            else:
                QMessageBox.critical(self, "Error", "Invalid username or password!")
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Error", f"Failed to verify credentials: {str(e)}")
            self.session.rollback()  # Rollback the transaction in case of an error
        finally:
            self.session.close()

    def register_account(self):
        import bcrypt
        employee_id = self.register_employee_id_input.text()
        first_name = self.register_first_name_input.text()
        last_name = self.register_last_name_input.text()
        username = self.register_username_input.text()
        password = self.register_password_input.text()
        confirm_password = self.register_confirm_password_input.text()

        # Initialize the db connection
        self.init_session()

        # Check if any field is blank
        if not all([employee_id, first_name, last_name, username, password, confirm_password]):
            QMessageBox.critical(self, "Error", "Please fill in all fields!")
            return

        # Check if the password field is the same as the confirm password field
        if password != confirm_password:
            QMessageBox.critical(self, "Error", "Passwords do not match!")
            return

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            new_user = User(EmployeeID=employee_id, 
                            FirstName=first_name, 
                            LastName=last_name, 
                            UserName=username, 
                            PasswordHash=hashed_password.decode('utf-8'))
            self.session.add(new_user)  # Add the new user object to the session
            self.session.commit()  # Commit the transaction to persist changes to the database
            QMessageBox.information(self, "Success", "Account registered successfully!")

            # Log the activity
            try:
                current_datetime = datetime.now()
                log_entry = LIMSActivity(
                    User=username,
                    TablesAffected="Users",
                    Action=f"{username} registered",
                    Notes='',
                    Date=current_datetime.date(),
                    Time=current_datetime.time()
                )
                self.session.add(log_entry)
                self.session.commit()
            except SQLAlchemyError as log_error:
                QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                self.session.rollback()
        except SQLAlchemyError as e:
            QMessageBox.critical(self, "Error", f"Failed to register account: {str(e)}")
            self.session.rollback()  # Rollback the transaction in case of an error
        finally:
            self.session.close()
            self.register_employee_id_input.clear()
            self.register_first_name_input.clear()
            self.register_last_name_input.clear()
            self.register_username_input.clear()
            self.register_password_input.clear()
            self.register_confirm_password_input.clear()
            
    def check_login_status(self):
        # Check if user is already logged in
        cached_username = settings.value("username")
        print("Cached Username:", cached_username)

        if cached_username:
            try:
                self.init_session()
                last_login = self.session.query(User.LastLogin).filter(User.UserName == cached_username).scalar()

                if last_login:
                    last_login_qdatetime = QDateTime.fromSecsSinceEpoch(int(last_login.timestamp()))
                    current_datetime = QDateTime.currentDateTime()

                    if last_login_qdatetime.daysTo(current_datetime) == 0 and last_login_qdatetime.secsTo(current_datetime) < 3600:
                        # User logged in within the past hour, skip login screen
                        self.username_input.setText(cached_username)  # Autofill username field
                        self.password_input.setFocus()  # Set focus to password field
                    else:
                        # Clear cached username if last login was more than an hour ago
                        settings.remove("username")
            except SQLAlchemyError as e:
                print(f"Failed to check login status: {str(e)}")
            finally:
                self.session.close()

    def show_main_menu(self):
        QTimer.singleShot(10, self.close_login_window)
        self.main_menu = MainMenu()
        self.main_menu.show()
    
    def close_login_window(self):
        self.close()  # Close the login window after a short delay

    def switch_to_login(self):
        # Switch to the login screen
        self.stacked_widget.setCurrentWidget(self.login_widget)

    def switch_to_register(self):
        # Switch to the register screen
        self.stacked_widget.setCurrentWidget(self.register_widget)

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        # Create a logs directory next to your executable
        log_dir = os.path.join(basedir, "log")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{settings.value('username')}.log")

        # Configure the logger
        logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.DEBUG
        )

        # Optional: Also log to console for dev mode
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

        sys.excepthook = self.handle_exception

        self.init_ui()

        self.layout = QVBoxLayout()

        self.init_fonts()

        self.init_banner()

        self.init_sidebar()

        self.init_stacked_widget()

        # Create a splitter to divide the window horizontally
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)

        # Create the vertical separator (frame) to the right of the sidebar
        separator = QFrame(self)
        separator.setFrameShape(QFrame.VLine)  # Set vertical line frame
        separator.setFrameShadow(QFrame.Sunken)  # Optional: gives a sunken look
        separator.setStyleSheet("background-color: #000000;")  # Set color of the separator
        separator.setContentsMargins(0, 0, 0, 0)
        separator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        separator.setFixedWidth(1)

        splitter.addWidget(separator)

        splitter.addWidget(self.stacked_widget)
        splitter.setSizes([(self.width // 4)*2, 1, (self.width)*2])  # Adjust the initial sizes as needed

        # Wrap the splitter in a widget to add margins
        splitter_wrapper = QWidget()
        splitter_layout = QHBoxLayout()
        splitter_layout.addWidget(splitter)
        splitter_layout.setContentsMargins(5, 0, 5, 5)  # Set left and right margins as needed
        splitter_wrapper.setLayout(splitter_layout)
        splitter_wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create a layout for the main window
        self.layout.addWidget(splitter_wrapper)  # Add the wrapped splitter

        # Set the layout to the central widget
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        self.get_users()

        try:
            self.init_session()
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
        except Exception as e:
            self.session.rollback()
            print("An error occurred: {e}")
        finally:
            self.session.close()

    def handle_exception(exc_type, exc_value, exc_traceback):
        logging.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))

    def get_users(self):
        try:
            self.init_session()

            query = self.session.query(User.UserName)

            self.users = ['Select User']

            for user in query.distinct().all():
                self.users.append(user[0])

        except Exception as e:
            print(f"An error occurred gathering user data: {e}")
            self.session.rollback()
        finally:
            self.session.close()

    def init_ui(self):
        # Create main window title and icon
        self.setWindowTitle("Leidos LIMS")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.85
        height_percent = 0.85

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(config.CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def init_sidebar(self):
        self.sidebar = QTreeWidget()
        
        # Set the size policy of the sidebar to expand vertically
        self.sidebar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set background color for the sidebar
        self.sidebar.setStyleSheet("background-color: #f0f0f0;")  # Change color code as needed

        # Add the desired border directly to the stacked widget
        self.sidebar.setFrameStyle(QFrame.NoFrame) 

        self.sidebar.setMinimumWidth(220)

        # Set header hidden
        self.sidebar.setHeaderHidden(True)

        # Create the top-level items
        sample_log_in_item = QTreeWidgetItem(self.sidebar, ['Sample Login'])
        batching_item = QTreeWidgetItem(self.sidebar, ['Batching'])
        prepsheets_item = QTreeWidgetItem(self.sidebar, ['Prepsheets'])
        process_data_item = QTreeWidgetItem(self.sidebar, ['Process Data'])
        reporting_item = QTreeWidgetItem(self.sidebar, ['Reporting'])
        trending_charts_item = QTreeWidgetItem(self.sidebar, ['Trending Charts'])
        qaqc_item = QTreeWidgetItem(self.sidebar, ['QAQC'])
        consumable_item = QTreeWidgetItem(self.sidebar, ['Consumable Management'])
        equipment_management_item = QTreeWidgetItem(self.sidebar, ['Equipment Management'])
        ai_query_item = QTreeWidgetItem(self.sidebar, ['AI Query'])

        # Add child items to QAQC
        qaqc_item.addChild(QTreeWidgetItem(qaqc_item, ['Limits']))
        qaqc_item.addChild(QTreeWidgetItem(qaqc_item, ['Instrument Verification']))
        qaqc_item.addChild(QTreeWidgetItem(qaqc_item, ['Equipment Verification']))
        qaqc_item.addChild(QTreeWidgetItem(qaqc_item, ['RAD CoA Generator']))
        # consumable_item.addChild(QTreeWidgetItem(consumable_item, ['Edit']))
        consumable_item.addChild(QTreeWidgetItem(consumable_item, ['Log In']))

        # Apply a larger font to all items in the sidebar
        large_font = QFont(self.default_font.family(), 14)
        smaller_font = QFont(self.default_font.family(), 12)

        top_level_items = [
            sample_log_in_item, batching_item, prepsheets_item, process_data_item,
            reporting_item, trending_charts_item, qaqc_item, consumable_item,
            equipment_management_item, ai_query_item
        ]
        for item in top_level_items:
            self.apply_font_recursively(item, large_font, smaller_font)    

        # Map each item to its corresponding index in the stacked widget
        self.page_mapping = {
            'Sample Login': 0,
            'Batching': 1,
            'Prepsheets': 2,
            'Process Data': 3,
            'Reporting': 4,
            'Trending Charts': 5,
            'Limits': 6,
            'Instrument Verification': 7,
            'Equipment Verification': 8,
            'RAD CoA Generator': 9,
            'Edit': 10,
            'Log In': 11,
            'Equipment Management': 12,
            'AI Query': 13,
        }

        # Reconnect with itemSelectionChanged
        self.sidebar.itemSelectionChanged.connect(self.item_clicked)

    def apply_font_recursively(self, item, large_font, smaller_font):
        if not large_font:
            item.setFont(0, smaller_font)
        else:
            item.setFont(0, large_font)
        for i in range(item.childCount()):
            self.apply_font_recursively(item.child(i), None, smaller_font)

    def item_clicked(self):
        item = self.sidebar.currentItem()
        if item:
            if item.childCount() > 0:
                if item.isExpanded():
                    self.sidebar.collapseItem(item)
                else:
                    self.sidebar.expandItem(item)
            else:
                self.switch_page(item)

    def switch_page(self, item):
        page_name = item.text(0)
        index = self.page_mapping.get(page_name)
        
        if index is not None:
            if not self.pages_initialized.get(page_name):
                self.initialize_page(page_name)
            # Re-confirm page index and set
            self.stacked_widget.setCurrentIndex(index)
            assert self.stacked_widget.currentIndex() == index, f"Failed to load page {page_name} at index {index}"

    def init_stacked_widget(self):
        self.stacked_widget = QStackedWidget()

        # Add empty placeholder widgets for each page
        for item in self.page_mapping.keys():
            page_placeholder  = QWidget()
            self.stacked_widget.addWidget(page_placeholder )

        # Track which pages have been initialized
        self.pages_initialized = {item: False for item in self.page_mapping.keys()}

        # Add the stacked widget to the layout
        self.layout.addWidget(self.stacked_widget)

    def initialize_page(self, page_name):
        logging.debug(f"Initializing page: {page_name}")
    
        # Create and initialize the page based on the page_name
        page = QWidget()

        if page_name == 'Sample Login':
            self.init_sample_login_page(page)
        elif page_name == 'Batching':
            self.init_batching_page(page)
        elif page_name == "Prepsheets":
            self.init_prepsheets_page(page)
        elif page_name == "Process Data":
            self.init_process_data_page(page)
        elif page_name == 'Reporting':
            self.init_reporting_page(page)
        elif page_name == 'Trending Charts':
            self.init_trending_chart_page(page)
        elif page_name == 'Limits':
            self.init_limits_page(page)
        elif page_name == 'Equipment Management':
            self.init_equipment_management_page(page)
        elif page_name == 'Instrument Verification':
            self.init_verification_page(page)
        elif page_name == 'RAD CoA Generator':
            self.init_rad_coa_page(page)
        elif page_name == 'Log In':
            self.init_consumable_login_page(page)
        elif page_name == 'Edit':
            self.edit_consumables(page)
        elif page_name == 'Equipment Verification':
            self.init_equipment_verification_page(page)
        elif page_name == 'AI Query':
            self.init_ai_query_page(page)

        # Replace the placeholder with the initialized page
        index = self.page_mapping.get(page_name)
        if index is not None:
            existing_page = self.stacked_widget.widget(index)
            if existing_page:
                self.stacked_widget.removeWidget(existing_page)  # Remove the placeholder
            self.stacked_widget.insertWidget(index, page)

        # Mark the page as initialized
        self.pages_initialized[page_name] = True

        logging.debug(f"Page {page_name} initialized successfully.")

    def init_ai_query_page(self, page):
        content_layout = QGridLayout()

        page.setLayout(content_layout)

# ██████  ███████ ██████   ██████  ██████  ████████ ██ ███    ██  ██████  
# ██   ██ ██      ██   ██ ██    ██ ██   ██    ██    ██ ████   ██ ██       
# ██████  █████   ██████  ██    ██ ██████     ██    ██ ██ ██  ██ ██   ███ 
# ██   ██ ██      ██      ██    ██ ██   ██    ██    ██ ██  ██ ██ ██    ██ 
# ██   ██ ███████ ██       ██████  ██   ██    ██    ██ ██   ████  ██████  
                                                                        
    def init_reporting_page(self, page):
        content_layout = QGridLayout()

        title = QLabel("Reporting")
        title.setFont(self.header_font)
        title.setContentsMargins(0, 20, 0, 80)

        sdg = QLineEdit()
        sdg.setFixedWidth(220)

        pdr_checkbox = QCheckBox("Preliminary Data Report")
        edd_checkbox = QCheckBox("Electronic Data Deliverable")
        form_1_checkbox = QCheckBox("Form 1")
        data_package_checkbox = QCheckBox("Data Package")

        checkbox_group = QVBoxLayout()

        checkbox_group.addWidget(pdr_checkbox)
        checkbox_group.addWidget(edd_checkbox)
        checkbox_group.addWidget(form_1_checkbox)
        checkbox_group.addWidget(data_package_checkbox)

        checkbox_container = QWidget()

        checkbox_container.setLayout(checkbox_group)

        button = QPushButton("Generate\nReport(s)")
        button.setFixedHeight(55)
        button.setFixedWidth(220)

        content_layout.addWidget(title, 0, 0, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addWidget(QLabel("SDG"), 1, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(sdg, 2, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(checkbox_container, 3, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(button, 4, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 5, 0, 1, 1)

        content_layout.setContentsMargins(0,0,0,0)
        
        button.clicked.connect(lambda: self.generate_reports(sdg.text(), pdr_checkbox, edd_checkbox, form_1_checkbox, data_package_checkbox))

        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page.setLayout(content_layout)

    def generate_reports(self, sdg, pdr_checkbox, edd_checkbox, form_1_checkbox, data_package_checkbox):
        if data_package_checkbox.isChecked():
            self.generate_pdr(sdg)
            self.generate_edd(sdg)
            self.generate_form_1(sdg)
            self.generate_data_package(sdg)
        else:
            if pdr_checkbox.isChecked():
                self.generate_pdr(sdg)
            if edd_checkbox.isChecked():
                self.generate_edd(sdg)
            if form_1_checkbox.isChecked():
                self.generate_form_1(sdg)

    def get_report_script_path(self, script_name):
        """Resolves the correct script path whether running frozen or not."""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.join(sys._MEIPASS, "reports")
        else:
            from lims.config import file_paths
            base_dir = file_paths.reports_directory

        return os.path.join(base_dir, script_name)

    def generate_pdr(self, sdg):
        script_path = self.get_report_script_path('pdr.py')

        with open(script_path) as script_file:
            script_code = script_file.read()
            exec(script_code, {'sdg': sdg, '__file__': script_path})
        return

    def generate_edd(self, sdg):
        script_path = self.get_report_script_path('edd.py')

        with open(script_path) as script_file:
            script_code = script_file.read()
            exec(script_code, {'sdg': sdg, '__file__': script_path})
        return

    def generate_form_1(self, sdg):
        script_path = self.get_report_script_path('form_1.py')

        with open(script_path) as script_file:
            script_code = script_file.read()
            exec(script_code, {'sdg': sdg, '__file__': script_path})
        return

    def generate_data_package(self, sdg):
        script_path = self.get_report_script_path('data_package.py')

        with open(script_path) as script_file:
            script_code = script_file.read()
            exec(script_code, {'sdg': sdg, '__file__': script_path})
        return

# ██      ██ ███    ███ ██ ████████ ███████ 
# ██      ██ ████  ████ ██    ██    ██      
# ██      ██ ██ ████ ██ ██    ██    ███████ 
# ██      ██ ██  ██  ██ ██    ██         ██ 
# ███████ ██ ██      ██ ██    ██    ███████ 
                                          
    def init_limits_page(self, page):
        content_layout = QGridLayout()

        limits_page_title = QLabel("Limits")
        limits_page_title.setFont(self.header_font)
        limits_page_title.setContentsMargins(0, 20, 0, 10)

        # When page loads and is selected, fetch the limits table
        self.edit_limits_radio = QRadioButton("Edit Limits")
        self.edit_limits_radio.setChecked(True)
        self.edit_limits_radio.toggled.connect(lambda: self.delay(self.limits_state_change))

        # When toggled, create new blank table 
        self.add_limits_radio = QRadioButton("Add Limits")
        # self.add_limits_radio.clicked.connect(lambda: self.delay(self.limits_state_change))

        # If the edit radio is selected, filter table by that date
        # If the add radio is selected, update the new blank table with that date
        self.limits_effective_date = QDateEdit()
        self.limits_effective_date.setCalendarPopup(True)
        self.limits_effective_date.setDate(QDate.currentDate())
        self.limits_effective_date.setDisplayFormat("MM-dd-yyyy")
        self.limits_effective_date.setFixedWidth(220)
        self.limits_effective_date.dateChanged.connect(self.update_limits_date)

        # Add line to the new limits table with blank entries
        # Enable if add radio is toggled
        self.add_limit_button = QPushButton("Add Line", self)
        self.add_limit_button.setFixedWidth(220)
        self.add_limit_button.clicked.connect(lambda: self.insert_blank_row(1))

        table_widget = QWidget()
        table_layout = QVBoxLayout()

        self.limits_table = QTableWidget()

        self.limits_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.limits_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)

        table_layout.addWidget(self.limits_table)
        table_widget.setLayout(table_layout)

        limits_notes = QLabel("Additional Notes")
        self.limits_notes = QTextEdit(self)
        line_height = self.limits_notes.fontMetrics().lineSpacing()
        self.limits_notes.setFixedHeight(line_height * 4 + 10)
        self.limits_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.limits_notes.setFixedWidth(330)

        limits_notes_layout = QVBoxLayout()
        limits_notes_widget = QWidget()
        limits_notes_layout.addWidget(limits_notes)
        limits_notes_layout.addWidget(self.limits_notes)
        limits_notes_widget.setLayout(limits_notes_layout)
        limits_notes_layout.setContentsMargins(0,0,0,0)

        self.update_limits_button = QPushButton("Submit", self)
        self.update_limits_button.clicked.connect(self.submit_limits)
        self.update_limits_button.setFixedHeight(55)
        self.update_limits_button.setFixedWidth(220)

        content_layout.addWidget(limits_page_title, 0, 0, 1, 3, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addWidget(self.edit_limits_radio, 1, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(self.add_limits_radio, 1, 2, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(self.limits_effective_date, 2, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(self.add_limit_button, 2, 2, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(table_widget, 3, 0, 1, 3)
        content_layout.addWidget(limits_notes_widget, 4, 0, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(self.update_limits_button, 4, 2, 1, 1, Qt.AlignHCenter)

        content_layout.setColumnStretch(0, 1)  
        content_layout.setColumnStretch(1, 1)
        content_layout.setColumnStretch(2, 1)

        self.limits_state_change()

        page.setLayout(content_layout)
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def delay(self, function, delay=50):
        QTimer.singleShot(delay, function)

    def limits_state_change(self):
        # Check the status of the buttons
        if self.edit_limits_radio.isChecked() and not self.add_limits_radio.isChecked():
            self.add_limit_button.setEnabled(False)
            self.get_limits_table_data(instruction='edit')
        elif self.add_limits_radio.isChecked() and not self.edit_limits_radio.isChecked():
            self.add_limit_button.setEnabled(True)
            self.get_limits_table_data(instruction='add')
    
    def get_limits_table_data(self, instruction):

        effective_date = self.limits_effective_date.date().toPyDate()

        self.limits_table.setRowCount(0)

        if instruction == 'edit':
            # Logic for implementing the initial table
            try:
                self.init_session()

                closest_date_record = self.session.query(LIMSLimits.EffectiveDate) \
                                    .filter(LIMSLimits.EffectiveDate <= effective_date) \
                                    .order_by(LIMSLimits.EffectiveDate.desc()) \
                                    .first()

                if closest_date_record:
                    closest_effective_date = closest_date_record.EffectiveDate
                    records = self.session.query(LIMSLimits) \
                        .filter(LIMSLimits.EffectiveDate == closest_effective_date) \
                        .all()
                else:
                    records = []

                if records:
                    print("Records exist")
                    data = [record.__dict__ for record in records]

                    # Drop the SQLAlchemy internal `_sa_instance_state` attribute if present
                    for item in data:
                        item.pop('_sa_instance_state', None)
                
                else:
                    data = []
                    print("Records do not exist")
                    QMessageBox.warning(self, "Error", f"No limits with effective date: {effective_date}")

                df = pd.DataFrame(data)

                columns = ['Method', 'Matrix', 'ResultType', 'Analyte', 'LowerLimit', 'UpperLimit', 'MDL', 'DL', 'LOD', 'LOQ', 'Units', 'EffectiveDate']

                df = df[columns]

                self.populate_limits_table(df)

            except Exception as e:
                self.session.rollback()
                print(f"An error occurred: {e}")
            finally:
                self.session.commit()
                self.session.close()

        elif instruction == 'add':
            try:
                df = None

                self.init_session()

                # Query to get the most recent EffectiveDate
                latest_date_record = self.session.query(LIMSLimits.EffectiveDate) \
                                    .order_by(LIMSLimits.EffectiveDate.desc()) \
                                    .first()

                if latest_date_record:
                    effective_date = latest_date_record.EffectiveDate

                    # Fetch only the specified columns for records with the latest EffectiveDate
                    records = self.session.query(
                        LIMSLimits.Method, LIMSLimits.Matrix, LIMSLimits.ResultType, LIMSLimits.Analyte
                    ).filter(LIMSLimits.EffectiveDate == effective_date).all()

                    # Convert the records to a list of dictionaries with the additional EffectiveDate field
                    data = [
                        {
                            'Method': record.Method,
                            'Matrix': record.Matrix,
                            'ResultType': record.ResultType,
                            'Analyte': record.Analyte,
                            'LowerLimit': '',
                            'UpperLimit': '',
                            'MDL': '',
                            'DL': '',
                            'LOD': '',
                            'LOQ': '',
                            'Units': '',
                            'EffectiveDate': effective_date
                        } for record in records
                    ]
                    print("Latest data fetched successfully.")
                else:
                    data = []

                df = pd.DataFrame(data)

                self.populate_limits_table(df)

            except Exception as e:
                self.session.rollback()
                print(f"An error occurred: {e}")
            except SQLAlchemyError as e:
                self.session.rollback()
                print(f"An SQLAlchemyError occurred: {e}")
            finally:
                self.session.commit()
                self.session.close()

    def populate_limits_table(self, df):
        columns = ['Method', 'Matrix', 'ResultType', 'Analyte', 'LowerLimit', 'UpperLimit', 'MDL', 'DL', 'LOD', 'LOQ', 'Units', 'EffectiveDate']
        self.limits_table.setRowCount(len(df))
        self.limits_table.setColumnCount(len(columns))

        self.limits_table.setHorizontalHeaderLabels(columns)

        if df is not None and not df.empty:
            for row in range(len(df)):
                for col in range(len(columns)):
                    # Create a QTableWidgetItem with the DataFrame cell value
                    item = QTableWidgetItem(str(df.iat[row, col]))
                    # Add the item to the table at the specified row and column
                    self.limits_table.setItem(row, col, item)
        else:
            self.insert_blank_row(1)
            
            # Optionally populate with placeholder text (e.g., "N/A")
            for row in range(self.limits_table):
                for col in range(len(columns)):
                    item = QTableWidgetItem("")  # Blank item or "N/A"
                    self.limits_table.setItem(row, col, item)

    def insert_blank_row(self, rows=1):
        # Get the current row count to insert at the end
        new_row_position = self.limits_table.rowCount()

        # Insert the specified number of blank rows
        for _ in range(rows):
            self.limits_table.insertRow(new_row_position)
            if self.add_limits_radio.isChecked() and not self.edit_limits_radio.isChecked():
                header_to_index = {self.limits_table.horizontalHeaderItem(i).text(): i for i in range(self.limits_table.columnCount())}
                
                column = header_to_index.get("EffectiveDate")

                effective_date = self.limits_effective_date.date().toPyDate()

                item = QTableWidgetItem(str(effective_date))

                self.limits_table.setItem(new_row_position, column, item)
            new_row_position += 1

    def update_limits_date(self):
        effective_date = self.limits_effective_date.date().toPyDate()

        if self.edit_limits_radio.isChecked() and not self.add_limits_radio.isChecked():
            self.get_limits_table_data(instruction='edit')
        elif self.add_limits_radio.isChecked() and not self.edit_limits_radio.isChecked():
            self.get_limits_table_data(instruction='add') 

    def convert_limits_table(self):
        """Convert QTableWidget data to a DataFrame."""
        # Get column names from the table header
        columns = [self.limits_table.horizontalHeaderItem(i).text() for i in range(self.limits_table.columnCount())]
        
        # Create a list to hold row data
        data = []
        for row in range(self.limits_table.rowCount()):
            row_data = {}
            for col in range(self.limits_table.columnCount()):
                item = self.limits_table.item(row, col)
                # Get the text of the cell or set to None if empty
                row_data[columns[col]] = item.text() if item else None
            data.append(row_data)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        return df

    def submit_limits(self):
        try:
            # Convert table to DataFrame
            df = self.convert_limits_table()

            # Initialize the session
            self.init_session()
            
            for _, row in df.iterrows():
                # Check if record exists based on a unique identifier (e.g., `Method`, `Matrix`, `ResultType`, `Analyte`, `EffectiveDate`)
                existing_record = self.session.query(LIMSLimits).filter(
                    LIMSLimits.Method == row['Method'],
                    LIMSLimits.Matrix == row['Matrix'],
                    LIMSLimits.ResultType == row['ResultType'],
                    LIMSLimits.Analyte == row['Analyte'],
                    LIMSLimits.EffectiveDate == row['EffectiveDate']
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.LowerLimit = row['LowerLimit']
                    existing_record.UpperLimit = row['UpperLimit']
                    existing_record.MDL = row['MDL']
                    existing_record.DL = row['DL']
                    existing_record.LOD = row['LOD']
                    existing_record.LOQ = row['LOQ']
                    existing_record.Units = row['Units']
                    print(f"Updated record for {row['Method']} - {row['Analyte']}")
                else:
                    # Add new record
                    new_record = LIMSLimits(
                        Method=row['Method'],
                        Matrix=row['Matrix'],
                        ResultType=row['ResultType'],
                        Analyte=row['Analyte'],
                        LowerLimit=row['LowerLimit'],
                        UpperLimit=row['UpperLimit'],
                        MDL=row['MDL'],
                        DL=row['DL'],
                        LOD=row['LOD'],
                        LOQ=row['LOQ'],
                        Units=row['Units'],
                        EffectiveDate=row['EffectiveDate']
                    )
                    self.session.add(new_record)
                    print(f"Added new record for {row['Method']} - {row['Analyte']}")

            # Commit the transaction
            self.session.commit()
            print("Database updated successfully.")

        except Exception as e:
            self.session.rollback()
            print(f"An error occurred: {e}")
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"An SQLAlchemyError occurred: {e}")
        finally:
            self.session.close()

# ████████ ██████  ███████ ███    ██ ██████  ██ ███    ██  ██████       ██████ ██   ██  █████  ██████  ████████ ███████ 
#    ██    ██   ██ ██      ████   ██ ██   ██ ██ ████   ██ ██           ██      ██   ██ ██   ██ ██   ██    ██    ██      
#    ██    ██████  █████   ██ ██  ██ ██   ██ ██ ██ ██  ██ ██   ███     ██      ███████ ███████ ██████     ██    ███████ 
#    ██    ██   ██ ██      ██  ██ ██ ██   ██ ██ ██  ██ ██ ██    ██     ██      ██   ██ ██   ██ ██   ██    ██         ██ 
#    ██    ██   ██ ███████ ██   ████ ██████  ██ ██   ████  ██████       ██████ ██   ██ ██   ██ ██   ██    ██    ███████ 

    def init_trending_chart_page(self, page):
        content_layout = QGridLayout()

        trending_chart_page_title = QLabel("Trending Charts")
        trending_chart_page_title.setFont(self.header_font)
        trending_chart_page_title.setContentsMargins(0, 20, 0, 10)

        trending_chart_from_date = QLabel("From Date")
        self.trending_chart_from_date = QDateEdit()
        self.trending_chart_from_date.setCalendarPopup(True)
        self.trending_chart_from_date.setDate(QDate.currentDate())
        self.trending_chart_from_date.setDisplayFormat("MM-dd-yyyy")
        self.trending_chart_from_date.dateChanged.connect(self.reset_trending_chart_inputs)

        input_from_date_layout = QVBoxLayout()
        input_from_date_layout.addWidget(trending_chart_from_date)
        input_from_date_layout.addWidget(self.trending_chart_from_date)
        input_from_date_layout.setContentsMargins(0,0,0,0)
        input_from_date_widget = QWidget()
        input_from_date_widget.setLayout(input_from_date_layout)

        trending_chart_to_date = QLabel("To Date")
        self.trending_chart_to_date = QDateEdit()
        self.trending_chart_to_date.setCalendarPopup(True)
        self.trending_chart_to_date.setDate(QDate.currentDate())
        self.trending_chart_to_date.setDisplayFormat("MM-dd-yyyy")
        self.trending_chart_to_date.dateChanged.connect(self.reset_trending_chart_inputs)

        input_to_date_layout = QVBoxLayout()
        input_to_date_layout.addWidget(trending_chart_to_date)
        input_to_date_layout.addWidget(self.trending_chart_to_date)
        input_to_date_layout.setContentsMargins(0,0,0,0)
        input_to_date_widget = QWidget()
        input_to_date_widget.setLayout(input_to_date_layout)

        input_date_layout = QHBoxLayout()
        input_date_layout.addWidget(input_from_date_widget)
        input_date_layout.addWidget(input_to_date_widget)
        input_date_widget = QWidget()
        input_date_widget.setLayout(input_date_layout)
        input_date_layout.setContentsMargins(0,0,0,0)

        trending_chart_method = QLabel("Table")
        self.trending_chart_table_select = QComboBox()
        self.trending_chart_table_select.addItems(self.trending_chart_get_tables())
        self.trending_chart_table_select.currentIndexChanged.connect(self.update_sample_matrix)

        trending_chart_sample_matrix = QLabel("Sample Matrix")
        self.trending_chart_sample_matrix = QComboBox()
        self.trending_chart_sample_matrix.setEnabled(False)
        self.trending_chart_sample_matrix.currentIndexChanged.connect(self.update_result_type)

        trending_chart_result_type = QLabel("Result Type")
        self.trending_chart_result_type = QComboBox()
        self.trending_chart_result_type.setEnabled(False)
        self.trending_chart_result_type.currentIndexChanged.connect(self.update_analyte)

        trending_chart_analyte = QLabel("Analyte")
        self.trending_chart_analyte = QComboBox()
        self.trending_chart_analyte.setEnabled(False)
        self.trending_chart_analyte.currentIndexChanged.connect(self.update_generate_button)

        self.trending_chart_generate_button = QPushButton("Generate Chart", self)
        self.trending_chart_generate_button.setEnabled(False)
        self.trending_chart_generate_button.clicked.connect(self.gather_chart_data)

        input_layout = QVBoxLayout()

        input_layout.addWidget(input_date_widget)
        input_layout.addWidget(trending_chart_method)
        input_layout.addWidget(self.trending_chart_table_select)
        input_layout.addWidget(trending_chart_sample_matrix)
        input_layout.addWidget(self.trending_chart_sample_matrix)
        input_layout.addWidget(trending_chart_result_type)
        input_layout.addWidget(self.trending_chart_result_type)
        input_layout.addWidget(trending_chart_analyte)
        input_layout.addWidget(self.trending_chart_analyte)
        input_layout.addWidget(self.trending_chart_generate_button)

        input_widget = QWidget()
        input_widget.setFixedWidth(260)
        input_widget.setLayout(input_layout)
        input_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        content_layout.addWidget(input_widget, 0, 0, 1, 1, Qt.AlignHCenter)

        # Separator between the top and bottom sections
        separatorV = QFrame()
        separatorV.setFrameShape(QFrame.VLine)
        separatorV.setFrameShadow(QFrame.Sunken)
        separatorV.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        separatorV.setContentsMargins(0, 0, 0, 0)

        content_layout.addWidget(separatorV, 0, 1, 1, 1, Qt.AlignHCenter)

        content_layout.setContentsMargins(0,0,0,0)

        page.setLayout(content_layout)

    def trending_chart_get_tables(self):
        try:
            self.init_session()
        
            result_tables = ['Select a Table', 'ALPHAResults', 'GAMMAResults', 'GFPCResults', 'METResults']
            return result_tables

        except SQLAlchemyError as e:
            print(f"An error occurred: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.session.close()

    def reset_trending_chart_inputs(self):
        self.trending_chart_table_select.setCurrentIndex(0)

        self.trending_chart_analyte.clear()
        self.trending_chart_analyte.setEnabled(False)
        self.trending_chart_result_type.clear()
        self.trending_chart_result_type.setEnabled(False)
        self.trending_chart_sample_matrix.clear()
        self.trending_chart_sample_matrix.setEnabled(False)
        
    def update_sample_matrix(self):
        self.table = self.trending_chart_table_select.currentText()
        self.trending_chart_sample_matrix.clear()

        if self.table != "Select a Table":
            sample_matrices = self.trending_chart_get_matrices(self.table)
            self.trending_chart_sample_matrix.setEnabled(True)
            self.trending_chart_sample_matrix.addItems(sample_matrices)
        else:
            self.trending_chart_sample_matrix.setEnabled(False)
    def trending_chart_get_matrices(self, chosen_table):
        try:
            self.init_session()
            
            # Dynamically retrieve the table based on the table name
            chosen_table = Table(chosen_table, self.metadata, autoload_with=self.engine)

            # Convert QDate to datetime
            from_date = self.trending_chart_from_date.dateTime().toPyDateTime()
            to_date = self.trending_chart_to_date.dateTime().toPyDateTime()

            # Query distinct Matrix values within the date range
            unique_matrices = self.session.query(chosen_table.c.Matrix).filter(
                between(chosen_table.c.AnalysisDateTime, from_date, to_date)
            ).distinct().all()

            # Extract Matrix values into a list
            matrix_list = [result[0] for result in unique_matrices]

            matrix_list.insert(0, "Select a Matrix")

            # Return the list of unique Matrix values
            return matrix_list

        except SQLAlchemyError as e:
            print(f"SQL Error: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.session.close()

    def update_result_type(self):
        self.trending_chart_result_type.clear()
        self.trending_chart_analyte.clear()
        self.trending_chart_analyte.setEnabled(False)

        sample_matrix = self.trending_chart_sample_matrix.currentText()

        if sample_matrix != "Select a Matrix" and sample_matrix != "":
            result_types = self.trending_chart_get_result_types(self.table)
            self.trending_chart_result_type.setEnabled(True)
            self.trending_chart_result_type.addItems(result_types)
        else:
            self.trending_chart_result_type.setEnabled(False)

    def trending_chart_get_result_types(self, chosen_table):
        try:
            self.init_session()
            
            # Dynamically retrieve the table based on the table name
            chosen_table = Table(chosen_table, self.metadata, autoload_with=self.engine)

            # Convert QDate to datetime
            from_date = self.trending_chart_from_date.dateTime().toPyDateTime()
            to_date = self.trending_chart_to_date.dateTime().toPyDateTime()

            # Query distinct Matrix values within the date range
            unique_result_types = self.session.query(chosen_table.c.ResultType).filter(
                and_(between(chosen_table.c.AnalysisDateTime, from_date, to_date), chosen_table.c.Matrix == self.trending_chart_sample_matrix.currentText())
            ).distinct().all()

            # Extract Matrix values into a list
            result_type_list = [result[0] for result in unique_result_types]

            result_type_list.insert(0, "Select a Result Type")

            # Return the list of unique Matrix values
            return result_type_list

        except SQLAlchemyError as e:
            print(f"SQL Error: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.session.close()

    def update_analyte(self):
        self.trending_chart_analyte.clear()
        self.trending_chart_generate_button.setEnabled(False)

        result_type = self.trending_chart_result_type.currentText()

        if result_type != "Select a Result Type" and result_type != "":
            analytes = self.trending_chart_get_analytes(self.table)
            self.trending_chart_analyte.setEnabled(True)
            self.trending_chart_analyte.addItems(analytes)
        else:
            self.trending_chart_analyte.setEnabled(False)

    def trending_chart_get_analytes(self, chosen_table):
        try:
            self.init_session()
            
            # Dynamically retrieve the table based on the table name
            chosen_table = Table(chosen_table, self.metadata, autoload_with=self.engine)

            # Convert QDate to datetime
            from_date = self.trending_chart_from_date.dateTime().toPyDateTime()
            to_date = self.trending_chart_to_date.dateTime().toPyDateTime()

            # Query distinct Matrix values within the date range
            unique_analytes = self.session.query(chosen_table.c.Analyte).filter(
                and_(between(chosen_table.c.AnalysisDateTime, from_date, to_date), chosen_table.c.Matrix == self.trending_chart_sample_matrix.currentText(),
                     chosen_table.c.ResultType == self.trending_chart_result_type.currentText())
            ).distinct().all()

            # Extract Matrix values into a list
            analyte_list = [result[0] for result in unique_analytes]

            self.trending_chart_analyte_list = analyte_list

            analyte_list.insert(0, "Select an Analyte")

            analyte_list.append("All Analytes")

            # Return the list of unique Matrix values
            return analyte_list

        except SQLAlchemyError as e:
            print(f"SQL Error: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.session.close()

    def update_generate_button(self):
        self.trending_chart_generate_button.setEnabled(True)

    def gather_chart_data(self):
        from_date = self.trending_chart_from_date.dateTime().toPyDateTime()
        to_date = self.trending_chart_to_date.dateTime().toPyDateTime()
        self.table = self.trending_chart_table_select.currentText()
        sample_matrix = self.trending_chart_sample_matrix.currentText()
        result_type = self.trending_chart_result_type.currentText()
        analyte = self.trending_chart_analyte.currentText()

        input_list = [self.table, sample_matrix, result_type, analyte]

        if any(item.startswith("Select a") for item in input_list) or any(item == "" for item in input_list):
            QMessageBox.warning(self, "Error", "Please choose an item from each input.")
        elif analyte == "All Analytes":
            for analyte_iter in self.trending_chart_analyte_list[1:-1]:
                trending_chart_df = self.generate_trending_chart_df(from_date, to_date, self.table, sample_matrix, result_type, analyte_iter)
                print(trending_chart_df, analyte_iter)
                self.generate_workbook(from_date, to_date, self.table, sample_matrix, result_type, analyte_iter, trending_chart_df)
        else:
            trending_chart_df = self.generate_trending_chart_df(from_date, to_date, self.table, sample_matrix, result_type, analyte)
            print(trending_chart_df)
            self.generate_workbook(from_date, to_date, self.table, sample_matrix, result_type, analyte, trending_chart_df)

    def generate_workbook(self, from_date, to_date, table, sample_matrix, result_type, analyte, df):
        # Get the date range name
        date_range, year = self.get_trending_chart_date_range(from_date, to_date)

        from_date_str = from_date.strftime("%Y-%m-%d")  # Format to YYYY-MM-DD
        to_date_str = to_date.strftime("%Y-%m-%d")      # Format to YYYY-MM-DD

        workbook_name = f"{table} from {from_date_str} to {to_date_str} for {result_type} {sample_matrix} {analyte}.xlsx"

        workbook_path = os.path.join(parentdir, "Reporting", "Trending Charts", year, date_range, workbook_name)

        # Create the directories if they don't exist
        os.makedirs(os.path.dirname(workbook_path), exist_ok=True)

        import xlsxwriter

        with pd.ExcelWriter(workbook_path, engine='xlsxwriter') as writer:
            workbook = xlsxwriter.Workbook(workbook_path, {"nan_inf_to_errors": True})

            workbook = writer.book

            # Summary Statistics worksheet
            summary_worksheet = workbook.add_worksheet("Summary Statistics")

            df_length = len(df) + 1

            summary_worksheet.write(0, 0, "Summary Statistic")
            summary_worksheet.write(0, 1, "Result")
            result_field = 'Result'

            if table == 'ALPHAResults':
                summary_worksheet.write(0, 2, "Tracer Recovery")
                result_field = 'Result'
                tracer_recovery_mean = df['TracerRecovery'].mean()
                tracer_recovery_stdev = df['TracerRecovery'].std()
                tracer_recovery_statistics = [
                    ("Count", df_length-1),
                    ("Mean", tracer_recovery_mean),
                    ("Standard Deviation", tracer_recovery_stdev),
                    ("2\u03C3 Upper Limit", tracer_recovery_mean+1.96*tracer_recovery_stdev),
                    ("3\u03C3 Upper Limit", tracer_recovery_mean+2.58*tracer_recovery_stdev),
                    ("2\u03C3 Lower Limit", tracer_recovery_mean-1.96*tracer_recovery_stdev),
                    ("3\u03C3 Lower Limit", tracer_recovery_mean-2.58*tracer_recovery_stdev)
                ]
                for i, (statistic, result) in enumerate(tracer_recovery_statistics, start=1):
                    summary_worksheet.write(i, 2, result)

            mean = df[result_field].mean()
            stdev = df[result_field].std()
            statistics = [
                    ("Count", df_length-1),
                    ("Mean", mean),
                    ("Standard Deviation", stdev),
                    ("2\u03C3 Upper Limit", mean+1.96*stdev),
                    ("3\u03C3 Upper Limit", mean+2.58*stdev),
                    ("2\u03C3 Lower Limit", mean-1.96*stdev),
                    ("3\u03C3 Lower Limit", mean-2.58*stdev)
                ]

            for i, (statistic, result) in enumerate(statistics, start=1):
                    summary_worksheet.write(i, 0, statistic)
                    summary_worksheet.write(i, 1, result)

            summary_worksheet.autofit()

            try: 
                self.init_session()
                
                method = table.replace("Results", "")

                for index, row in df.iterrows():
                    analysis_date = row['AnalysisDateTime'].to_pydatetime()

                    limits_query = self.session.query(LIMSLimits).filter(
                        and_(
                            LIMSLimits.Method == method,
                            LIMSLimits.Matrix == sample_matrix,
                            LIMSLimits.Analyte == analyte,
                            LIMSLimits.ResultType == result_type,
                            LIMSLimits.EffectiveDate <= analysis_date
                        )
                    ).order_by(LIMSLimits.EffectiveDate.desc()).first()

                    new_data = {}

                    new_data.update({
                        'ResultMean': mean,
                        'Result2SigmaUpper': mean + 1.96 * stdev,
                        'Result2SigmaLower': mean - 1.95 * stdev,
                        'Result3SigmaUpper': mean + 2.58 * stdev,
                        'Result3SigmaLower': mean - 2.58 * stdev,
                        'ResultAbsoluteUpperLimit': limits_query.UpperLimit if limits_query else 0,
                        'ResultAbsoluteLowerLimit': limits_query.LowerLimit if limits_query else 0,
                    })
                    
                    if table == 'ALPHAResults':
                        new_data.update({
                            'TracerRecoveryMean': tracer_recovery_mean,
                            'TracerRecovery2SigmaUpper': tracer_recovery_mean + 1.96 * tracer_recovery_stdev,
                            'TracerRecovery2SigmaLower': tracer_recovery_mean - 1.95 * tracer_recovery_stdev,
                            'TracerRecovery3SigmaUpper': tracer_recovery_mean + 2.58 * tracer_recovery_stdev,
                            'TracerRecovery3SigmaLower': tracer_recovery_mean - 2.58 * tracer_recovery_stdev,
                            'TracerRecoveryUpperLimit': 30,
                            'TracerRecoveryLowerLimit': 110,
                        })

                    df.loc[index, new_data.keys()] = new_data.values()
                
            except SQLAlchemyError as e:
                print(f"An error occurred: {e}")
                self.session.rollback()
            finally:
                self.session.close()

            df.to_excel(writer, sheet_name = 'Data', index=False)

            data_worksheet = writer.sheets['Data']

            datetime_columns = []

            date_columns = []

            time_columns = []

            for col in df.columns:
                if 'datetime' in col.lower():
                    datetime_columns.append(col)
                elif 'date' in col.lower():
                    date_columns.append(col)
                elif 'time' in col.lower():
                    time_columns.append(col)

            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            time_format = workbook.add_format({'num_format': 'hh:mm:ss'})

            for col in datetime_columns:
                col_idx = df.columns.get_loc(col)
                data_worksheet.set_column(col_idx, col_idx, 20, datetime_format)

            for col in date_columns:
                col_idx = df.columns.get_loc(col)
                data_worksheet.set_column(col_idx, col_idx, 15, date_format)

            for col in time_columns:
                col_idx = df.columns.get_loc(col)
                data_worksheet.set_column(col_idx, col_idx, 15, time_format)

            data_worksheet.autofit()

            # Charts
            results_chartsheet = workbook.add_chartsheet("Result Trending Chart")

            result_chart = workbook.add_chart({'type': 'line'})

            # Dynamically calculate the column indices
            col_indices = {col: idx for idx, col in enumerate(df.columns)}

            categories_column = self.excel_column_letter(col_indices['AnalysisDateTime'])
            results_column = self.excel_column_letter(col_indices[result_field])

            print(categories_column)
            print(results_column)

            # Add results
            result_chart.add_series({
                        'name':       f"{result_field}",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f"=Data!${results_column}$2:${results_column}${df_length}",
                        'line':       {'color': 'black', 'width': 1.75,},
                        'marker':     {'type': 'circle', 'fill': {'color': 'black'}},
                    })
            # Add mean
            mean_column_index = self.excel_column_letter(col_indices['ResultMean'])
            result_chart.add_series({
                        'name':       f"Mean",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${mean_column_index}$2:${mean_column_index}${df_length}',
                        'line':       {'color': 'black', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add 2 sigma upper
            two_sigma_upper = self.excel_column_letter(col_indices['Result2SigmaUpper'])
            result_chart.add_series({
                        'name':       f"2σ Upper Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${two_sigma_upper}$2:${two_sigma_upper}${df_length}',
                        'line':       {'color': 'green', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add 2 sigma lower
            two_sigma_lower = self.excel_column_letter(col_indices['Result2SigmaLower'])
            result_chart.add_series({
                        'name':       f"2σ Lower Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${two_sigma_lower}$2:${two_sigma_lower}${df_length}',
                        'line':       {'color': 'green', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add 3 sigma upper
            three_sigma_upper = self.excel_column_letter(col_indices['Result3SigmaUpper'])
            result_chart.add_series({
                        'name':       f"3σ Upper Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${three_sigma_upper}$2:${three_sigma_upper}${df_length}',
                        'line':       {'color': 'orange', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add 3 sigma lower
            three_sigma_lower = self.excel_column_letter(col_indices['Result3SigmaLower'])
            result_chart.add_series({
                        'name':       f"3σ Lower Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${three_sigma_lower}$2:${three_sigma_lower}${df_length}',
                        'line':       {'color': 'orange', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add absolute upper
            absolute_upper = self.excel_column_letter(col_indices['ResultAbsoluteUpperLimit'])
            result_chart.add_series({
                        'name':       f"Absolute Upper Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${absolute_upper}$2:${absolute_upper}${df_length}',
                        'line':       {'color': 'red', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            # Add absolute lower
            absolute_lower = self.excel_column_letter(col_indices['ResultAbsoluteLowerLimit'])
            result_chart.add_series({
                        'name':       f"Absolute Lower Limit",
                        'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                        'values':     f'=Data!${absolute_lower}$2:${absolute_lower}${df_length}',
                        'line':       {'color': 'red', 'width': 1.5, 'dash_type': 'long_dash'},
                    })
            
            result_chart.set_title({
                    'name': f"Trending Chart for {sample_matrix} Samples Analyzed by {method} for {analyte} from {from_date_str} to {to_date_str}\nMean +/- Sigma: {format(mean, '.4f')} +/- {format(stdev, '.4f')}%",
                    'overlay': False,
                    'name_font': {'size': 12, 'bold': False}
                    })

            min_datetime = df['AnalysisDateTime'].min()
            max_datetime = df['AnalysisDateTime'].max()

            result_chart.set_x_axis({
                            'num_format': 'yyyy-mm-dd',  # Set the format to just date for clarity
                            'text_axis': True,  # Treat the x-axis as a text axis, not a continuous date axis
                            'major_unit': 1,  # Set the interval to show labels for every day
                            'major_unit_type': 'days',  # Major unit is days, so labels are shown daily
                            'min': min_datetime,  # Optional: Set minimum date if needed
                            'max': max_datetime,  # Optional: Set maximum date if needed
                            'major_gridlines': {'visible': True}
                        })
            
            results_chartsheet.set_chart(result_chart)

            if table == 'ALPHAResults':
                tracer_recovery_chartsheet = workbook.add_chartsheet("Tracer Recovery Trending Chart")

                tracer_recovery_chart = workbook.add_chart({'type': 'line'})

                result_field = 'TracerRecovery'

                # Dynamically calculate the column indices
                col_indices = {col: idx for idx, col in enumerate(df.columns)}

                categories_column = self.excel_column_letter(col_indices['AnalysisDateTime'])
                results_column = self.excel_column_letter(col_indices[result_field])

                print(categories_column)
                print(results_column)

                # Add results
                tracer_recovery_chart.add_series({
                            'name':       f"Tracer Recovery",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f"=Data!${results_column}$2:${results_column}${df_length}",
                            'line':       {'color': 'black', 'width': 1.75,},
                            'marker':     {'type': 'circle', 'fill': {'color': 'black'}},
                        })
                # Add mean
                mean_column_index = self.excel_column_letter(col_indices['TracerRecoveryMean'])
                tracer_recovery_chart.add_series({
                            'name':       f"Mean",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${mean_column_index}$2:${mean_column_index}${df_length}',
                            'line':       {'color': 'black', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add 2 sigma upper
                two_sigma_upper = self.excel_column_letter(col_indices['TracerRecovery2SigmaUpper'])
                tracer_recovery_chart.add_series({
                            'name':       f"2σ Upper Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${two_sigma_upper}$2:${two_sigma_upper}${df_length}',
                            'line':       {'color': 'green', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add 2 sigma lower
                two_sigma_lower = self.excel_column_letter(col_indices['TracerRecovery2SigmaLower'])
                tracer_recovery_chart.add_series({
                            'name':       f"2σ Lower Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${two_sigma_lower}$2:${two_sigma_lower}${df_length}',
                            'line':       {'color': 'green', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add 3 sigma upper
                three_sigma_upper = self.excel_column_letter(col_indices['TracerRecovery3SigmaUpper'])
                tracer_recovery_chart.add_series({
                            'name':       f"3σ Upper Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${three_sigma_upper}$2:${three_sigma_upper}${df_length}',
                            'line':       {'color': 'orange', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add 3 sigma lower
                three_sigma_lower = self.excel_column_letter(col_indices['TracerRecovery3SigmaLower'])
                tracer_recovery_chart.add_series({
                            'name':       f"3σ Lower Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${three_sigma_lower}$2:${three_sigma_lower}${df_length}',
                            'line':       {'color': 'orange', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add absolute upper
                absolute_upper = self.excel_column_letter(col_indices['TracerRecoveryUpperLimit'])
                tracer_recovery_chart.add_series({
                            'name':       f"Absolute Upper Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${absolute_upper}$2:${absolute_upper}${df_length}',
                            'line':       {'color': 'red', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                # Add absolute lower
                absolute_lower = self.excel_column_letter(col_indices['TracerRecoveryLowerLimit'])
                tracer_recovery_chart.add_series({
                            'name':       f"Absolute Lower Limit",
                            'categories': f"=Data!${categories_column}$2:${categories_column}${df_length}",
                            'values':     f'=Data!${absolute_lower}$2:${absolute_lower}${df_length}',
                            'line':       {'color': 'red', 'width': 1.5, 'dash_type': 'long_dash'},
                        })
                
                tracer_recovery_chart.set_title({
                        'name': f"Trending Chart for {sample_matrix} Samples Analyzed by {method} for {analyte} from {from_date_str} to {to_date_str}\nMean +/- Sigma: {format(tracer_recovery_mean, '.4f')} +/- {format(tracer_recovery_stdev, '.4f')}%",
                        'overlay': False,
                        'name_font': {'size': 12, 'bold': False}
                        })

                tracer_recovery_chart.set_x_axis({
                            'num_format': 'yyyy-mm-dd',  # Set the format to just date for clarity
                            'text_axis': True,  # Treat the x-axis as a text axis, not a continuous date axis
                            'major_unit': 1,  # Set the interval to show labels for every day
                            'major_unit_type': 'days',  # Major unit is days, so labels are shown daily
                            'min': min_datetime,  # Optional: Set minimum date if needed
                            'max': max_datetime,  # Optional: Set maximum date if needed
                            'major_gridlines': {'visible': True}
                        })
                
                tracer_recovery_chartsheet.set_chart(tracer_recovery_chart)


    def excel_column_letter(self, col_idx):
        # Handles conversion to Excel-style column letters (A, B, C, ... AA, AB, etc.)
        string = ''
        while col_idx >= 0:
            string = chr(col_idx % 26 + ord('A')) + string
            col_idx = col_idx // 26 - 1
        return string
        
    def get_trending_chart_date_range(self, from_date, to_date):
        from datetime import date
        # Define the start and end dates for each quarter
        year = from_date.year
        
        quarters = {
            "Q1": (date(from_date.year, 1, 1), date(from_date.year, 3, 31)),
            "Q2": (date(from_date.year, 4, 1), date(from_date.year, 6, 30)),
            "Q3": (date(from_date.year, 7, 1), date(from_date.year, 9, 30)),
            "Q4": (date(from_date.year, 10, 1), date(from_date.year, 12, 31)),
        }

        # Convert from_date and to_date to date objects before comparing
        from_date_only = from_date.date()  # Converts datetime to date
        to_date_only = to_date.date()      # Converts datetime to date

        for quarter, (start, end) in quarters.items():
            if start <= from_date_only <= end and start <= to_date_only <= end:
                return quarter, str(year)

        # If no match, return "custom range"
        return "Custom Range", str(year)

    def generate_trending_chart_df(self, from_date, to_date, chosen_table, sample_matrix, result_type, analyte):
        try:
            self.init_session()

            # Dynamically retrieve the table based on the table name
            chosen_table = Table(chosen_table, self.metadata, autoload_with=self.engine)

            # Query distinct Matrix values within the date range
            chart_data = self.session.query(chosen_table).filter(
                and_(
                    between(chosen_table.c.AnalysisDateTime, from_date, to_date),
                    chosen_table.c.Matrix == sample_matrix,
                    chosen_table.c.ResultType == result_type,
                    chosen_table.c.Analyte == analyte
                )
            ).all()

            # Extract column names from the chosen_table
            column_names = [column.name for column in chosen_table.columns]

            # Convert SQLAlchemy query result to Pandas DataFrame
            if chart_data:
                df = pd.DataFrame([row._mapping for row in chart_data], columns=column_names)
            else:
                df = pd.DataFrame(columns=column_names)

            return df

        except SQLAlchemyError as e:
            print(f"SQL Error: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.session.close()

# ██████  ██████   ██████   ██████ ███████ ███████ ███████     ██████   █████  ████████  █████  
# ██   ██ ██   ██ ██    ██ ██      ██      ██      ██          ██   ██ ██   ██    ██    ██   ██ 
# ██████  ██████  ██    ██ ██      █████   ███████ ███████     ██   ██ ███████    ██    ███████ 
# ██      ██   ██ ██    ██ ██      ██           ██      ██     ██   ██ ██   ██    ██    ██   ██ 
# ██      ██   ██  ██████   ██████ ███████ ███████ ███████     ██████  ██   ██    ██    ██   ██ 

    def init_process_data_page(self, page):
        content_layout = QGridLayout()

        process_data_page_title = QLabel("Process Data")
        process_data_page_title.setFont(self.header_font)
        process_data_page_title.setContentsMargins(0, 20, 0, 10)

        self.process_file_list_widget = FileListWidget()
        self.process_file_list_widget.setFixedWidth(400)
        self.process_file_list_widget.setFixedHeight(200)
        
        self.process_drag_and_drop_label = DragAndDropLabel(self.process_file_list_widget)
        self.process_drag_and_drop_label.setFixedWidth(400)
        self.process_drag_and_drop_label.setFixedHeight(200)

        self.process_search_button = QPushButton("Search for Files")
        self.process_search_button.clicked.connect(self.open_process_file_dialog)

        self.process_data_button = QPushButton("Process Data", self)
        self.process_data_button.setFixedWidth(220)
        self.process_data_button.setFixedHeight(50)
        self.process_data_button.clicked.connect(self.submit_processed_data)

        file_drop_layout = QVBoxLayout()
        file_drop_layout.addWidget(self.process_drag_and_drop_label)
        file_drop_layout.addWidget(self.process_file_list_widget)
        file_drop_layout.addWidget(self.process_search_button)

        file_drop_widget = QWidget()
        file_drop_widget.setLayout(file_drop_layout)

        additional_notes_layout = QVBoxLayout()

        process_data_notes = QLabel("Additional Notes")
        self.process_data_notes = QTextEdit(self)
        line_height = self.process_data_notes.fontMetrics().lineSpacing()
        self.process_data_notes.setFixedHeight(line_height * 4 + 10)
        self.process_data_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.process_data_notes.setFixedWidth(330)

        additional_notes_layout.addWidget(process_data_notes)
        additional_notes_layout.addWidget(self.process_data_notes)

        additional_notes_widget = QWidget()
        additional_notes_widget.setLayout(additional_notes_layout)

        content_layout.addWidget(process_data_page_title, 0, 0, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addWidget(file_drop_widget, 1, 0, 1, 1, Qt.AlignCenter)
        content_layout.addWidget(additional_notes_widget, 2, 0, 1, 1, Qt.AlignCenter)
        content_layout.addWidget(self.process_data_button, 3, 0, 1, 1, Qt.AlignCenter)

        content_layout.setContentsMargins(0,0,0,0)

        page.setLayout(content_layout)

    def open_process_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        start_directory = file_paths.raw_data_directory
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Select Files", start_directory, "All Files (*);;Text Files (*.txt)", options=options)
        if filepaths:
            self.process_drag_and_drop_label.add_files(filepaths)

    def submit_processed_data(self):
            try:
                file_paths = self.process_file_list_widget.get_file_paths()
                print(f"Processing files: {file_paths}")  # Debugging print
                
                if not file_paths:
                    QMessageBox.critical(self, "Error", "Please select files to process.")
                    return
                if self.process_file_list_widget.get_file_paths() == []:
                    QMessageBox.critical(self, "Error", "Please select files to process.")
                    return

                for file_path in self.process_file_list_widget.get_file_paths():
                    head, tail = os.path.split(file_path)
                    analyst = settings.value("username")

                    instrument_type = os.path.basename(head)

                    instrument_type_list = lab_lists.method_list_directories

                    instrument_type = next((item for item in instrument_type_list if item in instrument_type), None)
                        
                    if instrument_type is None:
                        instrument_type = 'WetChem'

                    script_name = instrument_type + ".py"

                    # Detect if running as a bundled .exe
                    if getattr(sys, 'frozen', False):
                        base_dir = os.path.join(sys._MEIPASS, "core")  # Extracted PyInstaller files
                    else:
                        base_dir = os.path.join(os.path.dirname(__file__), "lims", "core")  # Normal path

                    script_path = os.path.join(base_dir, script_name)

                    if not os.path.exists(script_path):
                        QMessageBox.critical(self, "Error", f"Script {script_name} not found in {base_dir}")
                        return

                    try:
                        with open(script_path) as script_file:
                            script_code = script_file.read()
                            exec(script_code, {'file_path': file_path, 'analyst': analyst, '__file__': script_path})
                    except Exception as script_error:
                        QMessageBox.critical(self, "Script Execution Error", f"An error occurred while executing {script_name}:\n{str(script_error)}")
                        return

            except Exception as e:
                QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred:\n{str(e)}")

# ██████  ██████  ███████ ██████  ███████ ██   ██ ███████ ███████ ████████ ███████ 
# ██   ██ ██   ██ ██      ██   ██ ██      ██   ██ ██      ██         ██    ██      
# ██████  ██████  █████   ██████  ███████ ███████ █████   █████      ██    ███████ 
# ██      ██   ██ ██      ██           ██ ██   ██ ██      ██         ██         ██ 
# ██      ██   ██ ███████ ██      ███████ ██   ██ ███████ ███████    ██    ███████ 
                                                                                 
    def init_prepsheets_page(self, page):
        content_layout = QGridLayout()

        prepsheet_page_title = QLabel("Prepsheets")
        prepsheet_page_title.setFont(self.header_font)
        prepsheet_page_title.setContentsMargins(0, 10, 0, 10)

        # Select Batch Widget
        select_batch_label = QLabel("Batch ID")
        self.select_batch_input = QMultiSelectBox(self)
        self.select_batch_input.setMaximumWidth(440)
        self.select_batch_input.textChanged.connect(self.generate_prepsheet_name)
        self.select_batch_input.buttonClicked.connect(self.open_batch_window)

        # Prepsheet Name
        prepsheet_name_label = QLabel("Prepsheet Name")
        self.prepsheet_name_input = QLineEdit(self)
        self.prepsheet_name_input.setReadOnly(True)
        self.prepsheet_name_input.setMaximumWidth(220)

        # Generate Button
        self.generate_prepsheet_button = QPushButton("Generate Prepsheet", self)
        self.generate_prepsheet_button.clicked.connect(self.generate_prepsheet_content)
        self.generate_prepsheet_button.setMaximumWidth(165)
        self.generate_prepsheet_button.setFixedHeight(45)

        # Load Button
        self.load_prepsheet_button = QPushButton("Load Prepsheet", self)
        self.load_prepsheet_button.setMaximumWidth(165)
        self.load_prepsheet_button.setFixedHeight(45)
        self.load_prepsheet_button.clicked.connect(self.on_load_prepsheet_button_clicked)

        # Save Button
        self.save_prepsheet_button = QPushButton("Save Prepsheet", self)
        self.save_prepsheet_button.setMaximumWidth(165)
        self.save_prepsheet_button.setFixedHeight(45)
        self.save_prepsheet_button.clicked.connect(self.save_prepsheet)

        # Separator between the top and bottom sections
        separatorH = QFrame()
        separatorH.setFrameShape(QFrame.HLine)
        separatorH.setFrameShadow(QFrame.Sunken)
        separatorH.setContentsMargins(0, 0, 0, 0)

        # Initiate the Stacked Widget for Method-Specific Prepsheet contents
        self.method_widget = QStackedWidget()

        # Add Widgets to Content Layout
        content_layout.addWidget(prepsheet_page_title, 0, 0, 1, 5, Qt.AlignHCenter)
        content_layout.addWidget(select_batch_label, 1, 0, 1, 1)
        content_layout.addWidget(prepsheet_name_label, 1, 1, 1, 1)
        content_layout.addWidget(self.generate_prepsheet_button, 1, 2, 2, 1)
        content_layout.addWidget(self.load_prepsheet_button, 1, 3, 2, 1)
        content_layout.addWidget(self.save_prepsheet_button, 1, 4, 2, 1)
        content_layout.addWidget(self.select_batch_input, 2, 0, 1, 1)
        content_layout.addWidget(self.prepsheet_name_input, 2, 1, 1, 1)
        content_layout.addWidget(self.method_widget, 3, 0, 1, 5)

        page.setLayout(content_layout)

    def generate_prepsheet_name(self):
        batch = self.select_batch_input.getCurrentText().split(" (")[0]
        prepsheet_name = f"Prep-{batch}"

        self.prepsheet_name_input.setText(prepsheet_name)

    def get_batch_method(self, batch_ID):
        self.init_session()

        print("Batch ID", batch_ID)

        chosen_method = self.session.query(DQO.Method).filter_by(BatchID=batch_ID).first()[0]

        self.session.close()

        return chosen_method
    
    def open_batch_window(self):
        dialog = SelectBatchesPopup()
        if dialog.exec_() == QDialog.Accepted:
            selected_batch = dialog.getSelectedBatch()
            if selected_batch:
                self.select_batch_input.setCurrentText(selected_batch)

    def generate_prepsheet_content(self):
        if hasattr(self, 'prepsheet_scroll_area') and self.prepsheet_scroll_area:
        # Remove all child widgets from the scroll area
            for i in reversed(range(self.prepsheet_scroll_area.widget().layout().count())):
                widget_to_remove = self.prepsheet_scroll_area.widget().layout().itemAt(i).widget()
                if widget_to_remove is not None:
                    widget_to_remove.setParent(None)
            
            # Delete the scroll area itself
            self.prepsheet_scroll_area.deleteLater()
            self.prepsheet_scroll_area = None

        batch_id = self.select_batch_input.getCurrentText().split(" (")[0]
        self.chosen_method = self.get_batch_method(batch_id)

        self.sample_widgets = []
        self.sample_headers = []
        self.reagent_widgets = {}
        self.standard_widgets = {}
        self.tracer_widgets = {}
        self.lcs_widgets = {}
        self.consumables_widgets = {}

        self.prepsheet_content_layout = QGridLayout()
        self.prepsheet_row_index = 0

        # Get the matrix
        try:
            self.init_session()

            try:
                # Get unique SDGs
                sdg_results = self.session.query(DQO.SDG.distinct()).filter_by(BatchID=batch_id).all()
                sdgs = [result[0] for result in sdg_results]
                print(f"SDGs retrieved: {sdgs}")
            except Exception as e:
                print(f"Error retrieving SDGs: {e}")
                raise

            try:
                # Get unique Sample Matrices
                matrix_results = self.session.query(SampleLogin.Matrix.distinct()).filter(SampleLogin.SDG.in_(sdgs)).all()
                matrix = [result[0] for result in matrix_results]
                print(f"Sample matrices retrieved: {matrix}")
            except Exception as e:
                print(f"Error retrieving Sample Matrices: {e}")
                raise

            if len(matrix) > 1:
                error_message = "Batch contains more than one sample matrix, please rebatch."
                QMessageBox.warning(self, "Multiple Sample Matrices", error_message)
            elif len(matrix) == 1:
                chosen_matrix = matrix[0]
                print(f"Chosen matrix: {chosen_matrix}")
            else:
                QMessageBox.warning(self, "No Sample Matrices", "No sample matrices found for the provided SDGs.")

        except SQLAlchemyError as e:
            error_message = f"Database error occurred: {str(e)}"
            print(error_message)
            QMessageBox.warning(self, "Database Error", error_message)

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(f"Unexpected error: {error_message}")
            traceback.print_exc()
            QMessageBox.warning(self, "Error", error_message)

        finally:
            self.session.close()

        # Samples
        self.methods_samples = lab_lists.prepsheet_columns

        # Query to get all sampleIDs for chosen batch
        try:
            # Initialize the session
            self.init_session()

            # Query the database and filter by batch_id
            sample_id_results = self.session.query(DQO.SampleID).filter_by(BatchID=batch_id).all()

            # Convert the results to a list
            sample_ids = [result.SampleID for result in sample_id_results]

        except SQLAlchemyError as e:
            # Handle SQLAlchemy-specific errors
            error_message = f"Database error occurred: {str(e)}"
            print(error_message)  # Optional: print the error to the console

            # Show a QMessageBox warning
            QMessageBox.warning(self, "Database Error", error_message)

        except Exception as e:
            # Handle other exceptions
            error_message = f"An error occurred: {str(e)}"
            print(error_message)  # Optional: print the error to the console

            # Show a QMessageBox warning
            QMessageBox.warning(self, "Error", error_message)

        finally:
            self.session.close()

        if sample_ids:
            sample_title = QLabel("Samples")
            sample_title.setContentsMargins(0,10,0,10)
            sample_title.setFont(self.header_font)
            self.prepsheet_content_layout.addWidget(sample_title, self.prepsheet_row_index, 0, 1, 3) #Index 0
            self.prepsheet_row_index += 1 # Index 1

            # Create a QGridLayout for sample fields
            self.sample_grid_layout = QGridLayout()
            self.grid_row = 0

            if self.chosen_method == "MET":
                chosen_matrix = chosen_matrix.upper()
                matrix_key_map = {
                    "SMEAR": "SM",
                    "SM": "SM",
                    "Smear": "SM",
                    "AIR FILTER": 'AF',
                    "AF": "AF",
                    "Air Filter": "AF",
                    "AQUEOUS": "AQ",
                    "AQ": "AQ",
                    "Aqueous": "AQ",
                    "SOIL": "SO",
                    "SO": "SO",
                    "Soil": "SO"
                }

                chosen_matrix = matrix_key_map.get(chosen_matrix)

                self.chosen_method = f"{self.chosen_method} ({chosen_matrix})"

            # Set up column headers for the grid layout
            for col, field in enumerate(self.methods_samples.get(self.chosen_method, [])):
                header_label = QLabel(field)
                self.sample_grid_layout.addWidget(header_label, self.grid_row, col + 1, 1, 1, Qt.AlignHCenter | Qt.AlignTop)

                self.sample_form_layout = QVBoxLayout()
                self.sample_form_layout.setContentsMargins(0,0,0,0)

                self.sample_headers.append(header_label)

            self.sample_data = self.get_sample_data(sample_ids)
                
            for sample in sample_ids:
                self.grid_row += 1
                self.create_sample_rows(sample, self.chosen_method)

            sample_form_widget = QWidget()
            sample_form_widget.setLayout(self.sample_form_layout)

            # Remove margins and set minimal spacing
            self.sample_form_layout.setContentsMargins(0, 0, 0, 0)
            self.sample_form_layout.setSpacing(0)  # Set spacing between widgets in the layout
            sample_form_widget.setContentsMargins(0, 0, 0, 0)

            # Set the size policy to ensure the widget shrinks to fit its contents
            sample_form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.prepsheet_content_layout.addWidget(sample_form_widget, self.prepsheet_row_index, 0, 1, 3, Qt.AlignHCenter) # Index 1

            self.prepsheet_row_index += 1

        # Begin prepsheet content categories

        content_dict = self.generate_category_content(self.chosen_method, chosen_matrix)

        # ---------------------------------------------Reagents------------------------------------------------------

        self.reagent_dict = content_dict.get("Reagent", {})

        self.reagent_list = list(self.reagent_dict.keys())

        if self.reagent_list:
            reagent_title = QLabel("Reagents")
            reagent_title.setFont(self.header_font)
            self.prepsheet_content_layout.addWidget(reagent_title, self.prepsheet_row_index, 0, 1, 3)
            self.prepsheet_row_index += 1

            self.reagent_form_layout1 = QFormLayout()
            self.reagent_form_layout2 = QFormLayout()

            for reagent in self.reagent_list:
                self.create_reagent_dropdown(reagent)

            reagent_form_widget1 = QWidget()
            reagent_form_widget1.setLayout(self.reagent_form_layout1)
            self.reagent_form_layout1.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(reagent_form_widget1, self.prepsheet_row_index, 0, 1, 1)

            reagent_form_widget2 = QWidget()
            reagent_form_widget2.setLayout(self.reagent_form_layout2)
            self.reagent_form_layout2.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(reagent_form_widget2, self.prepsheet_row_index, 1, 1, 1)

            prep_date_starting_index = self.prepsheet_row_index

            self.prepsheet_row_index += 1

            self.prepsheet_content_layout.setColumnStretch(0, 1)
            self.prepsheet_content_layout.setColumnStretch(1, 1)
        else:
            prep_date_starting_index = self.prepsheet_row_index

        # ---------------------------------------------Standards------------------------------------------------------

        self.standard_dict = content_dict.get("Standard", {})

        self.standard_list = list(self.standard_dict.keys())

        if self.standard_list:
            standard_title = QLabel("Standards")
            standard_title.setFont(self.header_font)
            self.prepsheet_content_layout.addWidget(standard_title, self.prepsheet_row_index, 0, 1, 3)
            self.prepsheet_row_index += 1

            self.standard_form_layout1 = QFormLayout()
            self.standard_form_layout2 = QFormLayout()

            for standard in self.standard_list:
                self.create_standard_dropdown(standard)

            standard_form_widget1 = QWidget()
            standard_form_widget1.setLayout(self.standard_form_layout1)
            self.standard_form_layout1.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(standard_form_widget1, self.prepsheet_row_index, 0, 1, 1)

            standard_form_widget2 = QWidget()
            standard_form_widget2.setLayout(self.standard_form_layout2)
            self.standard_form_layout2.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(standard_form_widget2, self.prepsheet_row_index, 1, 1, 1)
            self.prepsheet_row_index += 1

            self.prepsheet_content_layout.setColumnStretch(0, 1)
            self.prepsheet_content_layout.setColumnStretch(1, 1)

        #---------------------------------------------Tracers------------------------------------------------------
        self.tracer_dict = content_dict.get("Tracer", {})

        self.tracer_list = list(self.tracer_dict.keys())

        if self.tracer_list:
            tracer_title = QLabel("Tracers")
            tracer_title.setFont(self.header_font)
            self.prepsheet_content_layout.addWidget(tracer_title, self.prepsheet_row_index, 0, 1, 3)
            self.prepsheet_row_index += 1

            self.tracer_form_layout1 = QFormLayout()
            self.tracer_form_layout2 = QFormLayout()

            for tracer in self.tracer_list:
                self.create_tracer_dropdown(tracer)

            tracer_form_widget1 = QWidget()
            tracer_form_widget1.setLayout(self.tracer_form_layout1)
            self.tracer_form_layout1.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(tracer_form_widget1, self.prepsheet_row_index, 0, 1, 1)

            tracer_form_widget2 = QWidget()
            tracer_form_widget2.setLayout(self.tracer_form_layout2)
            self.tracer_form_layout2.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(tracer_form_widget2, self.prepsheet_row_index, 1, 1, 1)
            self.prepsheet_row_index += 1

            self.prepsheet_content_layout.setColumnStretch(0, 1)
            self.prepsheet_content_layout.setColumnStretch(1, 1)

        # ---------------------------------------------LCS's------------------------------------------------------

        self.lcs_dict = content_dict.get("LCS", {})

        self.lcs_list = list(self.lcs_dict.keys())

        if self.lcs_list:
            lcs_title = QLabel("Laboratory Control Samples")
            lcs_title.setFont(self.header_font)
            self.prepsheet_content_layout.addWidget(lcs_title, self.prepsheet_row_index, 0, 1, 3)
            self.prepsheet_row_index += 1

            self.lcs_form_layout1 = QFormLayout()
            self.lcs_form_layout2 = QFormLayout()

            for lcs in self.lcs_list:
                self.create_lcs_dropdown(lcs)

            lcs_form_widget1 = QWidget()
            lcs_form_widget1.setLayout(self.lcs_form_layout1)
            self.lcs_form_layout1.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(lcs_form_widget1, self.prepsheet_row_index, 0, 1, 1)

            lcs_form_widget2 = QWidget()
            lcs_form_widget2.setLayout(self.lcs_form_layout2)
            self.lcs_form_layout2.setAlignment(Qt.AlignLeft)
            self.prepsheet_content_layout.addWidget(lcs_form_widget2, self.prepsheet_row_index, 1, 1, 1)

            prep_date_ending_index = self.prepsheet_row_index

            self.prepsheet_row_index += 1

            self.prepsheet_content_layout.setColumnStretch(0, 1)
            self.prepsheet_content_layout.setColumnStretch(1, 1)
        else:
            prep_date_ending_index = self.prepsheet_row_index

        # ---------------------------------------------Prep Dates------------------------------------------------------
        self.prep_date_scroll_area = QScrollArea(self)
        self.prep_date_scroll_area.setWidgetResizable(True)
        self.prep_date_scroll_content = QWidget()
        self.prep_date_scroll_area.setFixedWidth(770)

        self.prep_layout_with_button = QVBoxLayout(self.prep_date_scroll_content)

        self.prep_date_layout = QVBoxLayout()
        self.prep_layout_with_button.addLayout(self.prep_date_layout)

        self.scroll_spacer =  QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.prep_layout_with_button.addSpacerItem(self.scroll_spacer)

        self.add_prep_date_button = QPushButton("Add Prep Date", self)
        self.add_prep_date_button.clicked.connect(self.add_prep_date)
        self.prep_layout_with_button.addWidget(self.add_prep_date_button)

        self.prep_date_scroll_area.setWidget(self.prep_date_scroll_content)
        self.prep_dates = []

        # Add the prep date labels
        prep_date_labels_layout = QGridLayout()
        event_name_label = QLabel("Event Name")
        prep_date_label = QLabel("Event Date")
        prep_time_label = QLabel("Event Time")
        equipment_label = QLabel("Equipment Used")
        analyst_label = QLabel("Analyst")

        prep_date_labels_layout.addWidget(event_name_label, 0, 0, 1, 1, Qt.AlignRight)
        prep_date_labels_layout.addWidget(prep_date_label, 0, 1, 1, 1, Qt.AlignRight)
        prep_date_labels_layout.addWidget(prep_time_label, 0, 2, 1, 1, Qt.AlignRight)
        prep_date_labels_layout.addWidget(equipment_label, 0, 3, 1, 1, Qt.AlignHCenter)
        prep_date_labels_layout.addWidget(analyst_label, 0, 4, 1, 1, Qt.AlignHCenter)

        prep_date_labels_layout.setColumnStretch(0, 1)
        prep_date_labels_layout.setColumnStretch(1, 1)
        prep_date_labels_layout.setColumnStretch(2, 1)
        prep_date_labels_layout.setColumnStretch(3, 2)
        prep_date_labels_layout.setColumnStretch(4, 1)

        prep_date_labels_layout.setAlignment(Qt.AlignRight)

        prep_date_labels = QWidget()

        prep_date_labels.setLayout(prep_date_labels_layout)

        self.prep_date_layout.addWidget(prep_date_labels)

        self.add_prep_date()

        prep_date_stretch = (prep_date_ending_index - prep_date_starting_index) + 1

        self.prepsheet_content_layout.addWidget(self.prep_date_scroll_area, prep_date_starting_index, 1, prep_date_stretch, 2)

        self.prepsheet_content_layout.setAlignment(Qt.AlignHCenter)
        self.prepsheet_content_layout.setContentsMargins(0,0,0,0)

        self.content_widget = QWidget()
        self.content_widget.setLayout(self.prepsheet_content_layout)

        self.prepsheet_scroll_area = QScrollArea()
        self.prepsheet_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.prepsheet_scroll_area.setWidgetResizable(True)
        self.prepsheet_scroll_area.setWidget(self.content_widget)
        self.prepsheet_scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.method_widget.addWidget(self.prepsheet_scroll_area)
        self.method_widget.setContentsMargins(0,0,0,0)

    def add_prep_date(self):
        # Add to prep dates
        event_name = QLineEdit(self)
        event_name.setFixedWidth(155)

        if len(self.prep_dates) == 0:
            event_name.setText("Prep Date")
            event_name.setEnabled(False)

        prep_date = QDateEdit(self)
        prep_date.setCalendarPopup(True)
        prep_date.setDate(QDate.currentDate())
        prep_date.setDisplayFormat("MM-dd-yyyy")
        prep_date.setFixedWidth(100)

        prep_time = QTimeEdit(self)
        prep_time.setTime(QTime.currentTime())
        prep_time.setDisplayFormat("HH:mm")
        prep_time.setFixedWidth(100)

        equipment_select = QMultiSelectBox(self)
        equipment_select.buttonClicked.connect(lambda: self.select_equipment(equipment_select))
        equipment_select.setFixedWidth(220)

        analyst = QComboBox(self)
        analyst.addItems(self.users)

        widget_layout = QGridLayout()

        widget_layout.addWidget(event_name, 0, 0, 1, 1, Qt.AlignHCenter)
        widget_layout.addWidget(prep_date, 0, 1, 1, 1, Qt.AlignHCenter)
        widget_layout.addWidget(prep_time, 0, 2, 1, 1, Qt.AlignHCenter)
        widget_layout.addWidget(equipment_select, 0, 3, 1, 1, Qt.AlignHCenter)
        widget_layout.addWidget(analyst, 0, 4, 1, 1, Qt.AlignHCenter)

        widget_layout.setColumnStretch(0, 1)
        widget_layout.setColumnStretch(1, 1)
        widget_layout.setColumnStretch(2, 2)

        widget_layout.setContentsMargins(0,0,0,0)

        widget = QWidget()
        widget.setLayout(widget_layout)
        widget.setMaximumHeight(75)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.prep_date_layout.addWidget(widget)

        self.prep_dates.append({
            'Event Name': event_name,
            'Prep Date': prep_date,
            'Prep Time': prep_time,
            'Equipment Used': equipment_select,
            'Analyst': analyst
        })

        self.prep_date_scroll_content.adjustSize()

        QTimer.singleShot(50, self.scroll_prep_date)

    def select_equipment(self, equipment_select):
        equipment = []

        try:
            self.init_session()

            results = self.session.query(
                EquipmentManagement.EquipmentID,
                EquipmentManagement.Type
            ).distinct(
                EquipmentManagement.EquipmentID,
                EquipmentManagement.Type
            ).filter(
                EquipmentManagement.Status == 'Active'
            ).all()

            for equipment_id, equipment_type in results:
                equipment.append(f"{equipment_type} ({equipment_id})")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.session.rollback()
        finally:
            self.session.close()

        dialog = EquipmentSelectionPopup(equipment)
        if dialog.exec_() == QDialog.Accepted:
            selected_equipment = dialog.getSelectedEquipment()
            equipment_string = ', '.join(selected_equipment)
            if equipment_string:
                # Update the specific equipment_select passed as an argument
                equipment_select.setCurrentText(equipment_string)

    def scroll_prep_date(self):
        scrollbar = self.prep_date_scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def generate_category_content(self, chosen_method, chosen_matrix):
        print("Chosen Method: ", chosen_method)
        self.prepsheet_content_df = self.get_prepsheet_content(chosen_method, chosen_matrix)

        try:
            self.init_session()
            query = self.session.query(ConsumableManagement.Type).distinct().all()

            # Ensure content_categories is always a list, even if empty
            content_categories = [category[0] for category in query] if query else []
        except Exception as e:
            print(f"An exception occurred: {e}")
            content_categories = []  # Ensure it’s still defined
        finally: 
            self.session.close()

        content_dict = {category: {} for category in content_categories}  # Ensure all categories exist

        if self.prepsheet_content_df is not None and not self.prepsheet_content_df.empty:
            for category in content_categories:
                # Filter DataFrame by the current category
                filtered_df = self.prepsheet_content_df[self.prepsheet_content_df['Type'] == category]
                
                if not filtered_df.empty:
                    consumables = filtered_df['LotNumber'].unique()
                    for consumable in consumables:
                        content_df = filtered_df[filtered_df['LotNumber'] == consumable]

                        # Convert the relevant columns to a list of dictionaries
                        consumable_list = content_df[['ConsumableID', 'Status']].to_dict(orient='records')

                        # Add the consumable list to the corresponding category
                        content_dict[category][consumable] = consumable_list

        print(content_dict)
        return content_dict

    def get_prepsheet_content(self, chosen_method, chosen_matrix):
        if "(" in chosen_method:
            chosen_method = chosen_method.split(' ')[0]

        try:
            self.init_session()

            results = (
            self.session.query(ConsumableManagement)
            .filter(
                func.charindex(chosen_method, ConsumableManagement.Method) !=0,
                func.charindex(chosen_matrix, ConsumableManagement.Matrix) != 0
            )
            .all()
            )

            # Convert results to a list of dictionaries (assuming the result objects have a dictionary representation)
            result_list = [result.__dict__ for result in results]

            # Remove SQLAlchemy metadata if needed (usually under '_sa_instance_state')
            for result in result_list:
                result.pop('_sa_instance_state', None)
            
            # Convert to a pandas DataFrame
            df = pd.DataFrame(result_list)
            return df
        
        except Exception as e:
            print(f"Error fetching prepsheet content: {e}")
            return
        finally:
            self.session.close()

    def on_load_prepsheet_button_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        start_directory = file_paths.prepsheet_directory
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Prepsheet", start_directory, "JSON Files (*.json);;All Files (*)", options=options)
        
        if file_name:
            self.load_prepsheet(file_name)

    def load_prepsheet(self, file_name):
        import json
        import os

        try:
            with open(file_name, 'r') as file:
                data = json.load(file)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load prepsheet: {str(e)}")
            return

        # Set data back to the form
        self.select_batch_input.setCurrentText(data['batch_id'])
        self.prepsheet_name_input.setText(data['prepsheet_name'])

        # Ensure widgets are initialized before setting values
        self.generate_prepsheet_content()

        # Load Prep Dates, Times, and Equipment Used
        prep_data = data.get('Prep Data', [])

        # Ensure enough rows exist
        current_rows = len(self.prep_dates)
        required_rows = len(prep_data)
        for _ in range(required_rows - current_rows):
            self.add_prep_date()  # Dynamically add rows

        # Populate rows with data
        for i, prep_entry in enumerate(prep_data):
            if i < len(self.prep_dates):
                event_name_widget = self.prep_dates[i]['Event Name']
                prep_date_widget = self.prep_dates[i]['Prep Date']
                prep_time_widget = self.prep_dates[i]['Prep Time']
                equipment_widget = self.prep_dates[i]['Equipment Used']
                analyst_widget = self.prep_dates[i]['Analyst']

                # Set values for each widget
                event_name_widget.setText(prep_entry['Event Name'])
                prep_date_widget.setDate(QDate.fromString(prep_entry['Prep Date'], "MM-dd-yyyy"))
                prep_time_widget.setTime(QTime.fromString(prep_entry['Prep Time'], "HH:mm"))
                equipment_widget.setCurrentText(prep_entry['Equipment Used'])
                index = analyst_widget.findText(prep_entry['Analyst'])
                analyst_widget.setCurrentIndex(index)
            else:
                break
        
        # Set reagent dropdown and amount values
        for reagent, values in data['Reagents'].items():
            if reagent in self.reagent_widgets:
                self.reagent_widgets[reagent]['amount_input'].setText(values['amount'])

        # Set standard dropdown and amount values
        for standard, values in data['Standards'].items():
            if standard in self.standard_widgets:
                self.standard_widgets[standard]['amount_input'].setText(values['amount'])

        # Set tracer dropdown and amount values
        for tracer, values in data['Tracers'].items():
            if tracer in self.tracer_widgets:
                self.tracer_widgets[tracer]['amount_input'].setText(values['amount'])

        # Set LCS dropdown and amount values
        for lcs, values in data['LCSs'].items():
            if lcs in self.lcs_widgets:
                self.lcs_widgets[lcs]['amount_input'].setText(values['amount'])
        # Update sample widgets with new data (column-wise)
        for header, widget_data in data['Samples'].items():
            header_found = False
            print("HEADER", header)
            print("WIDGET DATA", widget_data)

            for i, sample_header in enumerate(self.sample_headers):
                print("THIS IS i", i)
                print("SAMPLE HEADER", sample_header)
                if sample_header.text() == header:
                    header_found = True
                    
                    # Ensure the widget_data aligns with the new column format
                    for row_index, value in enumerate(widget_data):
                        print("THIS IS row_index", row_index)
                        print("Value", value)
                        
                        if row_index >= len(self.sample_widgets):  # Ensure rows exist for each header
                            self.sample_widgets.append([])  # Add a new row for the column data

                        if i >= len(self.sample_widgets[row_index]):
                            # Create a new widget if it doesn't exist
                            if "Date" in self.methods_samples.get(self.chosen_method, [])[i]:
                                widget = QLineEdit()
                                widget.setInputMask("00/00/0000")
                                widget.setFixedWidth(100)
                            elif "Time" in self.methods_samples.get(self.chosen_method, [])[i]:
                                widget = QLineEdit()
                                widget.setInputMask("00:00:00")
                                widget.setFixedWidth(100)
                            else:
                                widget = QLineEdit()
                                widget.setFixedWidth(75)

                            # Add the widget to the grid layout if it's new
                            self.sample_grid_layout.addWidget(widget, row_index + 1, i + 1)
                            self.sample_widgets[row_index].append(widget)

                        widget = self.sample_widgets[row_index][i]

                        # Set widget values based on the type of widget
                        if isinstance(widget, QLineEdit):
                            widget.setText(value)
                        elif isinstance(widget, QDateEdit):
                            widget.setDate(QDate.fromString(value, 'yyyy-MM-dd'))
                        elif isinstance(widget, QComboBox):
                            widget.setCurrentText(value)
                        elif isinstance(widget, QTimeEdit):
                            widget.setTime(QTime.fromString(value, 'HH:mm:ss'))
                            widget.setDisplayFormat("HH:mm:ss")

            if not header_found:
                # Handle case where the header was not found in sample_headers
                pass

        # Optional: Set margins and spacing
        self.sample_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_grid_layout.setAlignment(Qt.AlignTop)

    def save_prepsheet(self):
        import json

        # Gather prep dates, times, and equipment
        prep_data = []
        for prep_entry in self.prep_dates:
            event_name = prep_entry['Event Name'].text()
            prep_date = prep_entry['Prep Date'].date().toString("MM-dd-yyyy")
            prep_time = prep_entry['Prep Time'].time().toString("HH:mm")
            equipment_used = prep_entry['Equipment Used'].getCurrentText()  # Assuming this method gets the selected equipment
            analyst = prep_entry['Analyst'].currentText()

            prep_data.append({
            'Event Name': event_name,
            'Prep Date': prep_date,
            'Prep Time': prep_time,
            'Equipment Used': equipment_used,
            'Analyst': analyst
            })

        # Gather data
        prepsheet_name = self.prepsheet_name_input.text()
        data = {
            'batch_id': self.select_batch_input.getCurrentText().split(" (")[0],
            'chosen_method': self.chosen_method.split(' (')[0],
            'prepsheet_name': prepsheet_name,
            'Samples': self.gather_widget_data(),
            'Reagents': {
                reagent: {
                    'lot_number': widgets['lot_number'],
                    'amount': widgets['amount_input'].text()
                } for reagent, widgets in self.reagent_widgets.items()
            },
            'Standards': {
                standard: {
                    'lot_number': widgets['lot_number'],
                    'amount': widgets['amount_input'].text()
                } for standard, widgets in self.standard_widgets.items()
            },
            'Tracers': {
                tracer: {
                    'lot_number': widgets['lot_number'],
                    'amount': widgets['amount_input'].text()
                } for tracer, widgets in self.tracer_widgets.items()
            },
            'LCSs': {
                lcs: {
                    'lot_number': widgets['lot_number'],
                    'amount': widgets['amount_input'].text()
                } for lcs, widgets in self.lcs_widgets.items()
            },
            'Prep Data': prep_data
        }

        sample_data = data['Samples']

        # Check if any item in any column's list of values is blank
        for column, values in sample_data.items():
            if any(value == "" for value in values):
                # Create a message box to warn the user
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Incomplete Data")
                msg_box.setText(
                                    f"One or more columns contain blank values. Do you want to autocomplete or review?"
                                    "<br><br><i>Autocomplete will fill in column values with the last non-blank value.</i>"
                                )

                # Add custom buttons
                autocomplete_button = msg_box.addButton("Autocomplete", QMessageBox.ActionRole)
                review_button = msg_box.addButton("Review", QMessageBox.RejectRole)

                # Display the message box and get the response
                msg_box.exec_()

                if msg_box.clickedButton() == autocomplete_button:
                    # Call the autocomplete function if "Autocomplete" is chosen
                    sample_data = self.autocomplete_sample_data(sample_data)
                    data = {
                        'batch_id': self.select_batch_input.getCurrentText().split(" (")[0],
                        'chosen_method': self.chosen_method.split(' (')[0],
                        'prepsheet_name': prepsheet_name,
                        'Samples': self.gather_widget_data(),
                        'Reagents': {
                            reagent: {
                                'lot_number': widgets['lot_number'],
                                'amount': widgets['amount_input'].text()
                            } for reagent, widgets in self.reagent_widgets.items()
                        },
                        'Standards': {
                            standard: {
                                'lot_number': widgets['lot_number'],
                                'amount': widgets['amount_input'].text()
                            } for standard, widgets in self.standard_widgets.items()
                        },
                        'Tracers': {
                            tracer: {
                                'lot_number': widgets['lot_number'],
                                'amount': widgets['amount_input'].text()
                            } for tracer, widgets in self.tracer_widgets.items()
                        },
                        'LCSs': {
                            lcs: {
                                'lot_number': widgets['lot_number'],
                                'amount': widgets['amount_input'].text()
                            } for lcs, widgets in self.lcs_widgets.items()
                        },
                        'Prep Data': prep_data
                    }
                elif msg_box.clickedButton() == review_button:
                    # Stop the process if "Review" is chosen
                    return
                break  # Exit after handling the first found blank entry

        # Define the specific filename
        file_name = f"{prepsheet_name}.json"
        
        # Construct the full path
        prepsheet_directory = file_paths.prepsheet_directory

        prepsheet_path = os.path.join(prepsheet_directory, file_name)

        try:
            # Save the file
            with open(prepsheet_path, 'w') as file:
                json.dump(data, file, indent=4)

            # Show success message
            QMessageBox.information(self, "Success", f"Prepsheet saved as {file_name}.")

        except Exception as e:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to save prepsheet: {str(e)}")

    def autocomplete_sample_data(self, data):
        # Define placeholders for time and date fields
        time_placeholder = "::"
        date_placeholder = "//"

        for column, values in data.items():
            latest_value = None
            for i, value in enumerate(values):
                # Check if the value is blank or matches a placeholder for date or time
                if value == "" or value == time_placeholder or value == date_placeholder or value.isspace():
                    # If the current value is "blank" or masked, use the latest non-blank value
                    if latest_value is not None:
                        values[i] = latest_value
                else:
                    # Update latest_value if current value is non-blank
                    latest_value = value
        return data
    
    def create_sample_rows(self, sample, chosen_method):
        # Get the list of fields based on the chosen method
        fields = self.methods_samples.get(chosen_method, [])

        sample_widget_list = []
        column = 1
        
        sample_info = self.sample_data.get(sample, {"date": None, "time": None}) if self.sample_data else {"date": None, "time": None}

        aliquot_units = ['']

        aliquot_units.extend(lab_lists.mass_units + lab_lists.volume_units)
        
        # Generate result units
        result_units = [''] + [f"{unit}/{subunit}" for unit in lab_lists.activity_units for subunit in (lab_lists.mass_units + lab_lists.volume_units)]

        # Generate concentration units (e.g., ug/L, mg/L, etc.)
        concentration_units = [f"{mass}/{volume}" for mass in lab_lists.mass_units for volume in lab_lists.volume_units]

        # Combine all units if needed
        all_units = result_units + concentration_units

        # Create input fields for each type
        for field in fields:
            if "Sample ID" in field:
                widget = QLineEdit()
                widget.setText(sample)
                widget.setEnabled(False)
                widget.setFixedWidth(200)
            elif "Result Units" in field:
                widget = QComboBox()
                widget.addItems(all_units)
                widget.setFixedWidth(200)
            elif "Aliquot Units" in field:
                widget = QComboBox()
                widget.addItems(aliquot_units)
                widget.setFixedWidth(200)
            elif "Date" in field:
                widget = QLineEdit()
                widget.setFixedWidth(100)
                widget.setInputMask("00/00/0000")
                if sample_info["date"]:
                    if field == 'Sample Date':
                        widget.setText(sample_info["date"].strftime("%m/%d/%Y"))
                    else:
                        widget.setText(QDate.currentDate().toString("MM/dd/yyyy"))
                else:
                    widget.setText(QDate.currentDate().toString("MM/dd/yyyy"))
            elif "Time" in field:
                widget = QLineEdit()
                widget.setInputMask("00:00:00")
                widget.setFixedWidth(100)
                if sample_info["time"]:
                    if field == 'Sample Time':
                        widget.setText(sample_info["time"].strftime("%H:%M:%S"))
                    else:
                        widget.setText(QTime.currentTime().toString("HH:mm:ss"))
                else:
                    widget.setText(QTime.currentTime().toString("HH:mm:ss"))
            else:  # For "Analyst" or other input types
                widget = QLineEdit()
                widget.setFixedWidth(75)

            # Add the widget to the grid layout
            self.sample_grid_layout.addWidget(widget, self.grid_row, column, 1, 1)
            sample_widget_list.append(widget)
            column += 1

        self.sample_widgets.append(sample_widget_list)
        
        # Optional: Set margins and spacing
        self.sample_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_grid_layout.setAlignment(Qt.AlignTop)

        grid_widget = QWidget()
        grid_widget.setLayout(self.sample_grid_layout)
        grid_widget.setContentsMargins(0,0,0,0)

        self.sample_form_layout.addWidget(grid_widget)

    def get_sample_data(self, samples):
        # Perform a single query to get the date and time for all samples in the provided list
        try:
            # Fetch the necessary columns (SampleID, Date, Time) in one query
            results = self.session.query(SampleLogin.SampleID, SampleLogin.SampleDate, SampleLogin.SampleTime).filter(
                SampleLogin.SampleID.in_(samples)
            ).all()

            # Create a dictionary for fast lookups
            sample_data = {result.SampleID: {"date": result.SampleDate, "time": result.SampleTime} for result in results}
            return sample_data

        except Exception as e:
            print(f"An error occurred: {e}")
            return {}

    def gather_widget_data(self):
        sample_data = {}
        
        # Initialize a dictionary for each header
        for header in self.sample_headers:
            header_text = header.text()  # Assuming header is a QLabel
            sample_data[header_text] = []

        # Assuming sample_widgets is structured as a list of rows (list of lists)
        for row_widgets in self.sample_widgets:
            for col_index, widget in enumerate(row_widgets):
                header_text = self.sample_headers[col_index].text()  # Get header for the current column
                if isinstance(widget, QLineEdit):
                    sample_data[header_text].append(widget.text())
                elif isinstance(widget, QDateEdit):
                    sample_data[header_text].append(widget.date().toString('yyyy-MM-dd'))  # Format date as string
                elif isinstance(widget, QComboBox):
                    sample_data[header_text].append(widget.currentText())
                elif isinstance(widget, QTimeEdit):
                    sample_data[header_text].append(widget.time().toString('HH:mm:ss'))  # Format time as string
                else:
                    sample_data[header_text].append(None)  # Handle unexpected widget types if needed
        
        return sample_data
    
    def create_lcs_dropdown(self, lcs_lot_number):

        lcs_label = QLabel(lcs_lot_number)
        amount_input = QLineEdit(self)
        amount_input.setPlaceholderText("Amount")
        amount_input.setFixedWidth(100)

        self.lcs_widgets[lcs_lot_number] = {
            "lot_number": lcs_lot_number,
            "amount_input": amount_input
        }

        hbox = QHBoxLayout()
        hbox.addWidget(lcs_label)
        hbox.addWidget(amount_input)

        self.lcs_form_layout1.addRow(hbox)
    
    def create_tracer_dropdown(self, tracer_lot_number):
        # Create label, dropdown, and amount entry
        tracer_label = QLabel(tracer_lot_number)

        amount_input = QLineEdit(self)
        amount_input.setPlaceholderText("Amount")
        amount_input.setFixedWidth(100)

        # Save widgets for later use if needed
        self.tracer_widgets[tracer_lot_number] = {
            "lot_number": tracer_lot_number,
            "amount_input": amount_input
        }

        # Create horizontal layout
        hbox = QHBoxLayout()
        hbox.addWidget(tracer_label)
        hbox.addWidget(amount_input)

        # Add horizontal layout to your form layout (assumed to be a QVBoxLayout or QFormLayout wrapper)
        self.tracer_form_layout1.addRow(hbox)
    
    def create_standard_dropdown(self, standard_lot_number):
        standard_label = QLabel(standard_lot_number)

        amount_input = QLineEdit(self)
        amount_input.setPlaceholderText("Amount")
        amount_input.setFixedWidth(100)

        self.standard_widgets[standard_lot_number] = {
            "lot_number": standard_lot_number,
            "amount_input": amount_input
        }

        hbox = QHBoxLayout()
        hbox.addWidget(standard_label)
        hbox.addWidget(amount_input)

        self.standard_form_layout1.addRow(hbox)
    
    def create_reagent_dropdown(self, reagent_lot_number):
        reagent_label = QLabel(reagent_lot_number)

        amount_input = QLineEdit(self)
        amount_input.setPlaceholderText("Amount")
        amount_input.setFixedWidth(100)

        self.reagent_widgets[reagent_lot_number] = {
            "lot_number": reagent_lot_number,
            "amount_input": amount_input
        }

        hbox = QHBoxLayout()
        hbox.addWidget(reagent_label)
        hbox.addWidget(amount_input)

        self.reagent_form_layout1.addRow(hbox)

# ███████  ██████  ██    ██ ██ ██████  ███    ███ ███████ ███    ██ ████████     ██    ██ ███████ ██████  ██ ███████ ██  ██████  █████  ████████ ██  ██████  ███    ██ 
# ██      ██    ██ ██    ██ ██ ██   ██ ████  ████ ██      ████   ██    ██        ██    ██ ██      ██   ██ ██ ██      ██ ██      ██   ██    ██    ██ ██    ██ ████   ██ 
# █████   ██    ██ ██    ██ ██ ██████  ██ ████ ██ █████   ██ ██  ██    ██        ██    ██ █████   ██████  ██ █████   ██ ██      ███████    ██    ██ ██    ██ ██ ██  ██ 
# ██      ██ ▄▄ ██ ██    ██ ██ ██      ██  ██  ██ ██      ██  ██ ██    ██         ██  ██  ██      ██   ██ ██ ██      ██ ██      ██   ██    ██    ██ ██    ██ ██  ██ ██ 
# ███████  ██████   ██████  ██ ██      ██      ██ ███████ ██   ████    ██          ████   ███████ ██   ██ ██ ██      ██  ██████ ██   ██    ██    ██  ██████  ██   ████ 
#             ▀▀                                                                                                                                                       

    def init_equipment_verification_page(self, page):
        content_layout = QGridLayout()

        # Title
        title = QLabel("Equipment Verification")
        title.setFont(self.header_font)
        title.setContentsMargins(0, 10, 0, 10)

        # Top Input Fields
        top_input_layout = QGridLayout()

        type_label = QLabel("Equipment Type")
        self.equipment_verification_type = QComboBox(self)
        self.equipment_verification_type.setFixedWidth(220)
        equipment_verification_list = ['Analytical Balance', 'Top-Loading Balance', 'Pipette', 'Hot Block', 'DI Water', 'Oven', 'Refrigerator']
        self.equipment_verification_type.addItems(equipment_verification_list)
        self.equipment_verification_type.currentIndexChanged.connect(self.change_equipment_verification_input)

        date_label = QLabel("Date")
        self.equipment_verification_date = QDateEdit(self)
        self.equipment_verification_date.setCalendarPopup(True)
        self.equipment_verification_date.setDate(QDate.currentDate())
        self.equipment_verification_date.setDisplayFormat("MM-dd-yyyy")
        self.equipment_verification_date.setFixedWidth(220)

        time_label = QLabel("Time")
        self.equipment_verification_time = QTimeEdit(self)
        self.equipment_verification_time.setTime(QTime.currentTime())
        self.equipment_verification_time.setDisplayFormat("HH:mm")
        self.equipment_verification_time.setFixedWidth(220)

        # Row 1
        top_input_layout.addWidget(type_label, 0, 0, 1, 1)
        top_input_layout.addWidget(date_label, 0, 1, 1, 1)
        top_input_layout.addWidget(time_label, 0, 2, 1, 1)

        # Row 2
        top_input_layout.addWidget(self.equipment_verification_type, 1, 0, 1, 1)
        top_input_layout.addWidget(self.equipment_verification_date, 1, 1, 1, 1)
        top_input_layout.addWidget(self.equipment_verification_time, 1, 2, 1, 1)

        top_input_widget = QWidget()

        top_input_widget.setLayout(top_input_layout)

        # Stacked Widget
        self.equipment_verification_stacked_widget = QStackedWidget()

        self.equipment_verification_df = pd.DataFrame()

        for equipment in equipment_verification_list:
            self.equipment_verification_stacked_widget.addWidget(self.create_equipment_verification_input_fields(equipment))
        
        # Bottom Inputs
        bottom_input_layout = QGridLayout(self)

        pass_fail_label = QLabel("Pass/Fail: ")
        self.pass_fail = QLineEdit()
        self.pass_fail.setEnabled(False)

        notes_label = QLabel("Additional Notes")
        self.equipment_verification_notes = QTextEdit(self)
        line_height = self.equipment_verification_notes.fontMetrics().lineSpacing()
        self.equipment_verification_notes.setFixedHeight(line_height * 4 + 10)
        self.equipment_verification_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.equipment_verification_notes.setFixedWidth(220)

        self.submit_equipment_verification_button = QPushButton("Submit Verification", self)
        self.submit_equipment_verification_button.setFixedWidth(200)
        self.submit_equipment_verification_button.setFixedHeight(100)

        bottom_input_layout.addWidget(pass_fail_label, 0, 0, 1, 2)
        bottom_input_layout.addWidget(self.pass_fail, 1, 0, 1, 2)
        bottom_input_layout.addWidget(notes_label, 2, 0, 1, 1)
        bottom_input_layout.addWidget(self.equipment_verification_notes, 3, 0, 1, 1)
        bottom_input_layout.addWidget(self.submit_equipment_verification_button, 2, 1, 2, 1)

        bottom_input_widget = QWidget()

        bottom_input_widget.setLayout(bottom_input_layout)

        content_layout.addWidget(title, 0, 0, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(top_input_widget, 1, 0, 1, 3)
        content_layout.addWidget(self.equipment_verification_stacked_widget, 2, 0, 1, 3)
        content_layout.addWidget(bottom_input_widget, 3, 0, 1, 3)

        content_layout.setAlignment(Qt.AlignHCenter)

        self.change_equipment_verification_input(0)

        page.setLayout(content_layout)

    def create_equipment_verification_input_fields(self, equipment_type):
        widget = QWidget()

        form_layout = QFormLayout(widget)

        if self.equipment_verification_df.empty:
            try:
                self.init_session()

                results = self.session.query(EquipmentManagement).filter(EquipmentManagement.Status == 'Active').all()

                # Convert query results to a DataFrame directly by leveraging ORM attributes
                data = [result.__dict__ for result in results]

                # Remove SQLAlchemy's internal `_sa_instance_state` attribute
                for row in data:
                    row.pop('_sa_instance_state', None)

                # Create a DataFrame
                self.equipment_verification_df = pd.DataFrame(data)

            except Exception as e:
                self.session.rollback()
                print(f"An error occurred: {e}")
            finally:
                self.session.close()
        else:
            pass

        if equipment_type == 'Top-Loading Balance':
            balance_layout = QGridLayout()

            mass_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Mass Weight Set', 'EquipmentID'
            ]

            low_mass_id = QComboBox(self)
            low_mass_id.addItems(mass_ids)

            target_low_mass = QLineEdit(self)
            target_low_mass.setEnabled(False)

            low_mass_id.currentIndexChanged.connect(lambda: self.get_target_mass(low_mass_id, target_low_mass))

            measured_low_mass = QLineEdit(self)

            high_mass_id = QComboBox(self)
            high_mass_id.addItems(mass_ids)

            target_high_mass = QLineEdit(self)
            target_high_mass.setEnabled(False)

            high_mass_id.currentIndexChanged.connect(lambda: self.get_target_mass(high_mass_id, target_high_mass))

            measured_high_mass = QLineEdit(self)

            verify_button = QPushButton("Verify")

            self.get_target_mass(low_mass_id, target_low_mass)
            self.get_target_mass(high_mass_id, target_high_mass)

            verify_button.clicked.connect(lambda: self.get_balance_pass_fail(target_low_mass.text(), target_high_mass.text(), measured_low_mass.text(), measured_high_mass.text(), 0.002, self.pass_fail))

            balance_layout.addWidget(QLabel("Low Mass ID"), 0, 0, 1, 1)
            balance_layout.addWidget(QLabel("Theoretical\nLow Mass (g)"), 0, 1, 1, 1)
            balance_layout.addWidget(QLabel("Measured\nLow Mass (g)"), 0, 2, 1, 1)
            balance_layout.addWidget(QLabel("High Mass ID"), 0, 3, 1, 1)
            balance_layout.addWidget(QLabel("Theoretical\nHigh Mass (g)"), 0, 4, 1, 1)
            balance_layout.addWidget(QLabel("Measured\nHigh Mass (g)"), 0, 5, 1, 1)
            
            balance_layout.addWidget(low_mass_id, 1, 0, 1, 1)
            balance_layout.addWidget(target_low_mass, 1, 1, 1, 1)
            balance_layout.addWidget(measured_low_mass, 1, 2, 1, 1)
            balance_layout.addWidget(high_mass_id, 1, 3, 1, 1)
            balance_layout.addWidget(target_high_mass, 1, 4, 1, 1)
            balance_layout.addWidget(measured_high_mass, 1, 5, 1, 1)
            balance_layout.addWidget(verify_button, 1, 6, 1, 1)

            balance_widget = QWidget()

            balance_widget.setLayout(balance_layout)

            form_layout.addWidget(balance_widget)

        elif equipment_type == 'Analytical Balance':
            balance_layout = QGridLayout()

            mass_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Mass Weight Set', 'EquipmentID'
            ]

            low_mass_id = QComboBox(self)
            low_mass_id.addItems(mass_ids)

            target_low_mass = QLineEdit(self)
            target_low_mass.setEnabled(False)

            low_mass_id.currentIndexChanged.connect(lambda: self.get_target_mass(low_mass_id, target_low_mass))

            measured_low_mass = QLineEdit(self)

            high_mass_id = QComboBox(self)
            high_mass_id.addItems(mass_ids)

            target_high_mass = QLineEdit(self)
            target_high_mass.setEnabled(False)

            high_mass_id.currentIndexChanged.connect(lambda: self.get_target_mass(high_mass_id, target_high_mass))

            measured_high_mass = QLineEdit(self)

            verify_button = QPushButton("Verify")

            self.get_target_mass(low_mass_id, target_low_mass)
            self.get_target_mass(high_mass_id, target_high_mass)

            verify_button.clicked.connect(lambda: self.get_balance_pass_fail(target_low_mass.text(), target_high_mass.text(), measured_low_mass.text(), measured_high_mass.text(), 0.002, self.pass_fail))

            balance_layout.addWidget(QLabel("Low Mass ID"), 0, 0, 1, 1)
            balance_layout.addWidget(QLabel("Theoretical\nLow Mass (g)"), 0, 1, 1, 1)
            balance_layout.addWidget(QLabel("Measured\nLow Mass (g)"), 0, 2, 1, 1)
            balance_layout.addWidget(QLabel("High Mass ID"), 0, 3, 1, 1)
            balance_layout.addWidget(QLabel("Theoretical\nHigh Mass (g)"), 0, 4, 1, 1)
            balance_layout.addWidget(QLabel("Measured\nHigh Mass (g)"), 0, 5, 1, 1)
            
            balance_layout.addWidget(low_mass_id, 1, 0, 1, 1)
            balance_layout.addWidget(target_low_mass, 1, 1, 1, 1)
            balance_layout.addWidget(measured_low_mass, 1, 2, 1, 1)
            balance_layout.addWidget(high_mass_id, 1, 3, 1, 1)
            balance_layout.addWidget(target_high_mass, 1, 4, 1, 1)
            balance_layout.addWidget(measured_high_mass, 1, 5, 1, 1)
            balance_layout.addWidget(verify_button, 1, 6, 1, 1)

            balance_widget = QWidget()

            balance_widget.setLayout(balance_layout)

            form_layout.addWidget(balance_widget)

        elif equipment_type == 'Pipette':
            pipette_layout = QGridLayout()

            pipette_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Pipette', 'EquipmentID'
            ]

            balance_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Analytical Balance', 'EquipmentID'
            ]

            # Top row clerical 
            pipette_id = QComboBox()
            balance_id = QComboBox()
            water_temp = QLineEdit()

            # Add queries to combo boxes
            pipette_id.addItems(pipette_ids)
            balance_id.addItems(balance_ids)

            # Low value row
            low_theoretical_value = QLineEdit()
            low_measurement_1 = QLineEdit()
            low_measurement_2 = QLineEdit()
            low_measurement_3 = QLineEdit()
            low_adj_measurement_1 = QLineEdit()
            low_adj_measurement_2 = QLineEdit()
            low_adj_measurement_3 = QLineEdit()
            low_average = QLineEdit()
            low_stdev = QLineEdit()
            low_rsd = QLineEdit()
            low_rsd_limit = QLineEdit()
            low_lower_limit = QLineEdit()
            low_upper_limit = QLineEdit()
            low_button = QPushButton("Verify")
            low_pass_fail = QLineEdit()

            # Low value widget disable
            low_adj_measurement_1.setEnabled(False)
            low_adj_measurement_2.setEnabled(False)
            low_adj_measurement_3.setEnabled(False)
            low_average.setEnabled(False)
            low_stdev.setEnabled(False)
            low_rsd.setEnabled(False)
            low_rsd_limit.setEnabled(False)
            low_lower_limit.setEnabled(False)
            low_upper_limit.setEnabled(False)
            low_pass_fail.setEnabled(False)

            # High value row
            high_theoretical_value = QLineEdit()
            high_measurement_1 = QLineEdit()
            high_measurement_2 = QLineEdit()
            high_measurement_3 = QLineEdit()
            high_adj_measurement_1 = QLineEdit()
            high_adj_measurement_2 = QLineEdit()
            high_adj_measurement_3 = QLineEdit()
            high_average = QLineEdit()
            high_stdev = QLineEdit()
            high_rsd = QLineEdit()
            high_rsd_limit = QLineEdit()
            high_lower_limit = QLineEdit()
            high_upper_limit = QLineEdit()
            high_button = QPushButton("Verify")
            high_pass_fail = QLineEdit()

            # High value widget disable
            high_adj_measurement_1.setEnabled(False)
            high_adj_measurement_2.setEnabled(False)
            high_adj_measurement_3.setEnabled(False)
            high_average.setEnabled(False)
            high_stdev.setEnabled(False)
            high_rsd.setEnabled(False)
            high_rsd_limit.setEnabled(False)
            high_lower_limit.setEnabled(False)
            high_upper_limit.setEnabled(False)
            high_pass_fail.setEnabled(False)

            # Add the clerical widget labels to layout
            pipette_layout.addWidget(QLabel("Equipment ID"), 0, 0, 1, 3)
            pipette_layout.addWidget(QLabel("Balance ID"), 0, 5, 1, 3)
            pipette_layout.addWidget(QLabel("Water Temperature (°C)"), 0, 10, 1, 3)

            # Add the clerical widgets to layout
            pipette_layout.addWidget(pipette_id, 1, 0, 1, 3)
            pipette_layout.addWidget(balance_id, 1, 5, 1, 3)
            pipette_layout.addWidget(water_temp, 1, 10, 1, 3)

            # Add first spacer
            spacer1 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
            pipette_layout.addItem(spacer1, 2, 0, 1, 7)

            # Add labels to layout
            pipette_layout.addWidget(QLabel('Theoretical\nValue (L)'), 3, 0, 1, 1)
            pipette_layout.addWidget(QLabel('Rep 1 (L)'), 3, 1, 1, 1)
            pipette_layout.addWidget(QLabel('Rep 2 (L)'), 3, 2, 1, 1)
            pipette_layout.addWidget(QLabel('Rep 3 (L)'), 3, 3, 1, 1)
            pipette_layout.addWidget(QLabel('Adjusted\nRep 1 (L)'), 3, 4, 1, 1)
            pipette_layout.addWidget(QLabel('Adjusted\nRep 2 (L)'), 3, 5, 1, 1)
            pipette_layout.addWidget(QLabel('Adjusted\nRep 3 (L)'), 3, 6, 1, 1)

            # Add low value to layout
            pipette_layout.addWidget(low_theoretical_value, 4, 0, 1, 1)
            pipette_layout.addWidget(low_measurement_1, 4, 1, 1, 1)
            pipette_layout.addWidget(low_measurement_2, 4, 2, 1, 1)
            pipette_layout.addWidget(low_measurement_3, 4, 3, 1, 1)
            pipette_layout.addWidget(low_adj_measurement_1, 4, 4, 1, 1)
            pipette_layout.addWidget(low_adj_measurement_2, 4, 5, 1, 1)
            pipette_layout.addWidget(low_adj_measurement_3, 4, 6, 1, 1)
            pipette_layout.addWidget(low_button, 4, 7, 1, 1)

            # Add high value to layout
            pipette_layout.addWidget(high_theoretical_value, 5, 0, 1, 1)
            pipette_layout.addWidget(high_measurement_1, 5, 1, 1, 1)
            pipette_layout.addWidget(high_measurement_2, 5, 2, 1, 1)
            pipette_layout.addWidget(high_measurement_3, 5, 3, 1, 1)
            pipette_layout.addWidget(high_adj_measurement_1, 5, 4, 1, 1)
            pipette_layout.addWidget(high_adj_measurement_2, 5, 5, 1, 1)
            pipette_layout.addWidget(high_adj_measurement_3, 5, 6, 1, 1)
            pipette_layout.addWidget(high_button, 5, 7, 1, 1)

            # Add second spacer
            spacer2 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
            pipette_layout.addItem(spacer1, 6, 0, 1, 7)

            # Add autocompleted labels to layout
            pipette_layout.addWidget(QLabel('Average (L)'), 7, 0, 1, 1)
            pipette_layout.addWidget(QLabel('Standard\nDeviation (L)'), 7, 1, 1, 1)
            pipette_layout.addWidget(QLabel('Percent\nRSD (%)'), 7, 2, 1, 1)
            pipette_layout.addWidget(QLabel('RSD\nLimit (%)'), 7, 3, 1, 1)
            pipette_layout.addWidget(QLabel('Lower\nLimit (L)'), 7, 4, 1, 1)
            pipette_layout.addWidget(QLabel('Upper\nLimit (L)'), 7, 5, 1, 1)
            pipette_layout.addWidget(QLabel('Pass/Fail'), 7, 6, 1, 1)

            pipette_layout.addWidget(low_average, 8, 0, 1, 1)
            pipette_layout.addWidget(low_stdev, 8, 1, 1, 1)
            pipette_layout.addWidget(low_rsd, 8, 2, 1, 1)
            pipette_layout.addWidget(low_rsd_limit, 8, 3, 1, 1)
            pipette_layout.addWidget(low_lower_limit, 8, 4, 1, 1)
            pipette_layout.addWidget(low_upper_limit, 8, 5, 1, 1)
            pipette_layout.addWidget(low_pass_fail, 8, 6, 1, 1)

            pipette_layout.addWidget(high_average, 9, 0, 1, 1)
            pipette_layout.addWidget(high_stdev, 9, 1, 1, 1)
            pipette_layout.addWidget(high_rsd, 9, 2, 1, 1)
            pipette_layout.addWidget(high_rsd_limit, 9, 3, 1, 1)
            pipette_layout.addWidget(high_lower_limit, 9, 4, 1, 1)
            pipette_layout.addWidget(high_upper_limit, 9, 5, 1, 1)
            pipette_layout.addWidget(high_pass_fail, 9, 6, 1, 1)

            # Add third spacer
            spacer3 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
            pipette_layout.addItem(spacer3, 10, 0, 1, 7)

            low_button.clicked.connect(lambda: (
                self.verify_pipette(water_temp, low_theoretical_value, low_measurement_1, low_measurement_2, low_measurement_3,
                                                low_adj_measurement_1, low_adj_measurement_2, low_adj_measurement_3, low_average, low_stdev, low_rsd, low_rsd_limit, low_lower_limit,
                                                low_upper_limit, low_pass_fail)
                , self.get_verification_data(pipette_layout)
            ))
            high_button.clicked.connect(lambda: (
                self.verify_pipette(water_temp, high_theoretical_value, high_measurement_1, high_measurement_2, high_measurement_3,
                                    high_adj_measurement_1, high_adj_measurement_2, high_adj_measurement_3, high_average, high_stdev, high_rsd, high_rsd_limit, high_lower_limit,
                                    high_upper_limit, high_pass_fail)
                , self.get_verification_data(pipette_layout) 
            ))

            low_pass_fail.textChanged.connect(lambda: self.complete_pipette_verification(low_pass_fail, high_pass_fail))
            high_pass_fail.textChanged.connect(lambda: self.complete_pipette_verification(low_pass_fail, high_pass_fail))

            pipette_widget = QWidget()
            pipette_widget.setLayout(pipette_layout)
            form_layout.addWidget(pipette_widget)

        elif equipment_type == 'Hot Block':
            hot_block_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Hot Block', 'EquipmentID'
            ]

            thermometer_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Thermometer', 'EquipmentID'
            ]

            hot_block_layout = QGridLayout()

            hot_block_id = QComboBox()
            hot_block_id.addItems(hot_block_ids)

            thermometer_id = QComboBox()
            thermometer_id.addItems(thermometer_ids)

            hot_block_location = QLineEdit()

            theoretical_temperature = QLineEdit()

            measured_temperature = QLineEdit()

            verify_button = QPushButton("Verify Hot Block")
            verify_button.clicked.connect(lambda: self.verify_hot_block(theoretical_temperature, measured_temperature))

            hot_block_layout.addWidget(QLabel("Hot Block ID"), 0, 0, 1, 1)
            hot_block_layout.addWidget(QLabel("Thermometer ID"), 0, 1, 1, 1)
            hot_block_layout.addWidget(QLabel("Hot Block Location"), 0, 2, 1, 1)
            hot_block_layout.addWidget(QLabel("Theoretical\nTemperature (°C)"), 0, 3, 1, 1)
            hot_block_layout.addWidget(QLabel("Measured\nTemperature (°C)"), 0, 4, 1, 1)

            hot_block_layout.addWidget(hot_block_id, 1, 0, 1, 1)
            hot_block_layout.addWidget(thermometer_id, 1, 1, 1, 1)
            hot_block_layout.addWidget(hot_block_location, 1, 2, 1, 1)
            hot_block_layout.addWidget(theoretical_temperature, 1, 3, 1, 1)
            hot_block_layout.addWidget(measured_temperature, 1, 4, 1, 1)
            hot_block_layout.addWidget(verify_button, 1, 5, 1, 1)

            hot_block_widget = QWidget()

            hot_block_widget.setLayout(hot_block_layout)

            form_layout.addWidget(hot_block_widget)

        elif equipment_type == 'DI Water':
            di_water_layout = QGridLayout()

            resistance = QLineEdit()

            verify_button = QPushButton("Verify DI Water")
            verify_button.clicked.connect(lambda: self.verify_di_water(resistance))

            di_water_widget = QWidget()

            di_water_layout.addWidget(QLabel("Resistance\n(M\u03A9/cm)"), 0, 0, 1, 1)
            di_water_layout.addWidget(resistance, 1, 0, 1, 1)
            di_water_layout.addWidget(verify_button, 1, 1, 1, 1)

            di_water_widget.setLayout(di_water_layout)

            form_layout.addWidget(di_water_widget)

        elif equipment_type == 'Oven':
            oven_layout = QGridLayout()

            oven_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Oven', 'EquipmentID'
            ]

            thermometer_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Thermometer', 'EquipmentID'
            ]

            oven_id = QComboBox()
            oven_id.addItems(oven_ids)

            thermometer_id = QComboBox()
            thermometer_id.addItems(thermometer_ids)

            theoretical_temperature = QLineEdit()

            measured_temperature = QLineEdit()

            oven_method = QComboBox()
            oven_methods = ['TSS', 'BeFinder']
            oven_method.addItems(oven_methods)

            verify_button = QPushButton("Verify Oven")
            verify_button.clicked.connect(lambda: self.verify_oven(theoretical_temperature, measured_temperature, oven_method))

            oven_layout.addWidget(QLabel("Oven ID"), 0, 0, 1, 1)
            oven_layout.addWidget(QLabel("Thermometer ID"), 0, 1, 1, 1)
            oven_layout.addWidget(QLabel("Method"), 0, 2, 1, 1)
            oven_layout.addWidget(QLabel("Theoretical\nTemperature"), 0, 3, 1, 1)
            oven_layout.addWidget(QLabel("Measured\nTemperature"), 0, 4, 1, 1)

            oven_layout.addWidget(oven_id, 1, 0, 1, 1)
            oven_layout.addWidget(thermometer_id, 1, 1, 1, 1)
            oven_layout.addWidget(oven_method, 1, 2, 1, 1)
            oven_layout.addWidget(theoretical_temperature, 1, 3, 1, 1)
            oven_layout.addWidget(measured_temperature, 1, 4, 1, 1)

            oven_widget = QWidget()

            oven_widget.setLayout(oven_layout)

            form_layout.addWidget(oven_widget)

        elif equipment_type == 'Refrigerator':
            fridge_layout = QGridLayout()

            fridge_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Refrigerator', 'EquipmentID'
            ]

            thermometer_ids = self.equipment_verification_df.loc[
                self.equipment_verification_df['Type'] == 'Thermometer', 'EquipmentID'
            ]

            fridge_id = QComboBox()
            fridge_id.addItems(fridge_ids)

            thermometer_id = QComboBox()
            thermometer_id.addItems(thermometer_ids)

            theoretical_temperature = QLineEdit()

            measured_temperature = QLineEdit()

            verify_button = QPushButton("Verify Fridge")
            verify_button.clicked.connect(lambda: self.verify_fridge(measured_temperature))

            fridge_layout.addWidget(QLabel("Refrigerator ID"), 0, 0, 1, 1)
            fridge_layout.addWidget(QLabel("Thermometer ID"), 0, 1, 1, 1)
            fridge_layout.addWidget(QLabel("Theoretical\nTemperature (°C)"), 0, 2, 1, 1)
            fridge_layout.addWidget(QLabel("Measured\nTemperature (°C)"), 0, 3, 1, 1)

            fridge_layout.addWidget(fridge_id, 1, 0, 1, 1)
            fridge_layout.addWidget(thermometer_id, 1, 1, 1, 1)
            fridge_layout.addWidget(theoretical_temperature, 1, 2, 1, 1)
            fridge_layout.addWidget(measured_temperature, 1, 3, 1, 1)
            fridge_layout.addWidget(verify_button, 1, 4, 1, 1)

            fridge_widget = QWidget()

            fridge_widget.setLayout(fridge_layout)

            form_layout.addWidget(fridge_widget)

        return widget

    def get_verification_data(self, layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()

            if widget is not None:
                if isinstance(widget, QtWidgets.QLineEdit):
                    print(widget.text())
                elif isinstance(widget, QtWidgets.QLabel):
                    print(widget.text())
                elif isinstance(widget, QtWidgets.QComboBox):
                    print(widget.currentText)
                else:
                    print("Widget not instanced")
        
    def verify_fridge(self, measured_temperature):
        measured_value = float(measured_temperature.text())

        if measured_value >= 0 and measured_value <=6:
            self.pass_fail.setText("Pass")
        else:
            self.pass_fail.setText("Fail")
        
    def verify_oven(self, theoretical_temperature, measured_temperature, oven_method):
        theoretical_value = float(theoretical_temperature.text())
        measured_value = float(measured_temperature.text())
        chosen_method = oven_method.currentText()

        result = ""

        if chosen_method == 'TSS':
            if measured_value >= 103 or measured_value <= 105:
                result = "Pass"
            else:
                result = "Fail"
        elif chosen_method == 'BeFinder':
            if abs(theoretical_value - measured_value) < 2.5:
                result = "Pass"
            else:
                result = "Fail"
        else:
            pass

        if result != "":
            self.pass_fail.setText(result)

    def verify_di_water(self, resistance):
        resistance_value = float(resistance.text())

        if resistance_value >= 18:
            self.pass_fail.setText("Pass")
        else:
            self.pass_fail.setText("Fail")

    def verify_hot_block(self, theoretical_temperature, measured_temperature):
        theoretical_temperature_value = float(theoretical_temperature.text())
        measured_temperature_value = float(measured_temperature.text())

        allowed_error = 5

        if theoretical_temperature_value - allowed_error < measured_temperature_value < theoretical_temperature_value + allowed_error:
            self.pass_fail.setText("Pass")
        else:
            self.pass_fail.setText("Fail")

    def complete_pipette_verification(self, low_pass_fail, high_pass_fail):
        if low_pass_fail.text() == 'Pass' and high_pass_fail.text() == 'Pass':
            self.pass_fail.setText('Pass')
        else:
            self.pass_fail.setText('Fail')

    def verify_pipette(self, water_temperature, theoretical_value, rep1, rep2, rep3, adj1, adj2, adj3, avg, stdev, rsd, rsd_limit, lower_limit, upper_limit, pass_fail):
        if any(field.text().strip() == "" for field in [water_temperature, theoretical_value, rep1, rep2, rep3]):
            QMessageBox.warning(self, 'Error', 'Please fill in all fields.')
            return

        temp = round(float(water_temperature.text()), 4)
        target = float(theoretical_value.text())
        rep1_value = round(float(rep1.text()), 4)
        rep2_value = round(float(rep2.text()), 4)
        rep3_value = round(float(rep3.text()), 4)

        temperature_density_dict = {
            15: 0.9991016,
            16: 0.998945,
            17: 0.9987769,
            18: 0.9985976,
            19: 0.9984073,
            20: 0.9982063,
            21: 0.9979948,
            22: 0.997773,
            23: 0.9975412,
            24: 0.9972994,
            25: 0.997048,
            26: 0.996787,
            27: 0.9965166,
            28: 0.9962371,
            29: 0.9959486,
            30: 0.9956511,
            31: 0.995345
        }

        density = temperature_density_dict[round(temp, 1)]

        # Perform calculations
        adj1_value = round(density * rep1_value, 4)
        adj2_value = round(density * rep2_value, 4)
        adj3_value = round(density * rep3_value, 4)

        # Calculate the average and round
        average = round((adj1_value + adj2_value + adj3_value) / 3, 4)

        # Create a list of adjusted values
        adj_value_list = [adj1_value, adj2_value, adj3_value]

        # Calculate standard deviation and round
        standard_deviation = round(statistics.stdev(adj_value_list), 4)

        # Calculate RSD value and round
        rsd_value = round(abs((standard_deviation / average) * 100), 4)

        rsd_limit_value = 1.00

        limit_accuracy = round(0.02 * target, 4)

        adj1.setText(str(adj1_value))
        adj2.setText(str(adj2_value))
        adj3.setText(str(adj3_value))

        avg.setText(str(average))

        stdev.setText(str(standard_deviation))

        rsd.setText(str(rsd_value))

        rsd_limit.setText(str(rsd_limit_value))

        lower_limit.setText(str(round(target-limit_accuracy, 4)))
        upper_limit.setText(str(round(target+limit_accuracy, 4)))

        if (rsd_value < rsd_limit_value) and (round(target - limit_accuracy, 4) < average < round(target + limit_accuracy, 4)):
            pass_fail.setText("Pass")
        else:
            pass_fail.setText("Fail")
    
    def get_balance_pass_fail(self, low_target, high_target, low_measured, high_measured, threshold, pass_fail_field):
        print(low_target, high_target, low_measured, high_measured, threshold, pass_fail_field)
        try:
            # Check if any input is None or an empty string
            if any(field in (None, "") for field in [low_target, high_target, low_measured, high_measured]):
                pass_fail_field.setText("Pass")
                return

            # Convert inputs to integers and evaluate the conditions
            low_condition = abs(1 - (float(low_target) / float(low_measured))) > threshold
            high_condition = abs(1 - (float(high_target) / float(high_measured))) > threshold

            print(low_condition, high_condition)

            # If either condition fails, overall result is "Fail"
            if low_condition or high_condition:
                pass_fail_field.setText("Fail")
            else:
                pass_fail_field.setText("Pass")
        except (ValueError, ZeroDivisionError):
            # Handle invalid or zero inputs
            pass_fail_field.setText("Invalid")
    
    def get_target_mass(self, retrieval_widget, target_widget):
        target_mass = self.equipment_verification_df.loc[
                self.equipment_verification_df['EquipmentID'] == f"{retrieval_widget.currentText()}", 'AssignedMass'
            ].iloc[0]
        
        print(target_mass)
        
        target_widget.setText(str(target_mass))
    
    def change_equipment_verification_input(self, index):
        self.equipment_verification_stacked_widget.setCurrentIndex(index)

# ██ ███    ██ ███████ ████████ ██████  ██    ██ ███    ███ ███████ ███    ██ ████████     ██    ██ ███████ ██████  ██ ███████ ██  ██████  █████  ████████ ██  ██████  ███    ██ 
# ██ ████   ██ ██         ██    ██   ██ ██    ██ ████  ████ ██      ████   ██    ██        ██    ██ ██      ██   ██ ██ ██      ██ ██      ██   ██    ██    ██ ██    ██ ████   ██ 
# ██ ██ ██  ██ ███████    ██    ██████  ██    ██ ██ ████ ██ █████   ██ ██  ██    ██        ██    ██ █████   ██████  ██ █████   ██ ██      ███████    ██    ██ ██    ██ ██ ██  ██ 
# ██ ██  ██ ██      ██    ██    ██   ██ ██    ██ ██  ██  ██ ██      ██  ██ ██    ██         ██  ██  ██      ██   ██ ██ ██      ██ ██      ██   ██    ██    ██ ██    ██ ██  ██ ██ 
# ██ ██   ████ ███████    ██    ██   ██  ██████  ██      ██ ███████ ██   ████    ██          ████   ███████ ██   ██ ██ ██      ██  ██████ ██   ██    ██    ██  ██████  ██   ████ 
                                                                                                                                                                               
    def init_verification_page(self, page):
        content_layout = QGridLayout()

        # Add Files Section 
        add_files_title = QLabel("Instrument Verification")
        add_files_title.setFont(self.header_font)
        add_files_title.setContentsMargins(0, 10, 0, 10)

        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)

        form_layout2 = QVBoxLayout()
        form_layout2.setAlignment(Qt.AlignCenter)

        self.verification_file_list_widget = FileListWidget()
        self.verification_file_list_widget.setFixedWidth(400)
        self.verification_file_list_widget.setFixedHeight(200)

        self.verification_drag_and_drop_label = DragAndDropLabel(self.verification_file_list_widget)
        self.verification_drag_and_drop_label.setFixedWidth(400)
        self.verification_drag_and_drop_label.setFixedHeight(200)

        self.search_button = QPushButton("Search for Files")
        self.search_button.clicked.connect(self.open_verification_file_dialog)

        self.instruments_list = {'Select an Instrument': [],
                                 'Alpha': ['Daily Pulser', 'Monthly Calibration', 'System Background'],
                       'GAMMA': ['Daily Background', 'Daily QC', 'System Background'],
                       'GFPC': ['Alpha', 'Beta', 'Annual Calibration', 'Weekly Background']}

        verification_instrument = QLabel("Instrument")
        self.verification_instrument_combobox = QComboBox(self)
        self.verification_instrument_combobox.addItems(list(self.instruments_list.keys()))
        self.verification_instrument_combobox.currentIndexChanged.connect(self.populate_verification_names)

        verification_name = QLabel("Verification")
        self.verification_name_combobox = QComboBox(self)
        
        verification_date = QLabel("Date")
        self.verification_date = QDateEdit(self)
        self.verification_date.setCalendarPopup(True)
        self.verification_date.setDate(QDate.currentDate())
        self.verification_date.setDisplayFormat("MM-dd-yyyy")
        self.verification_date.setFixedWidth(200)
        self.verification_date.setFixedWidth(200)

        verification_time = QLabel("Time")
        self.verification_time = QTimeEdit(self)
        self.verification_time.setTime(QTime.currentTime())
        self.verification_time.setDisplayFormat("HH:mm")
        self.verification_time.setFixedWidth(200)
        self.verification_time.setFixedWidth(200)

        self.verification_submit_button = QPushButton("Submit Verification(s)")
        self.verification_submit_button.clicked.connect(self.submit_instrument_verification)

        form_layout.addWidget(self.search_button)
        form_layout.addWidget(self.verification_drag_and_drop_label)
        form_layout.addWidget(self.verification_file_list_widget)

        form_layout2.addWidget(verification_instrument)
        form_layout2.addWidget(self.verification_instrument_combobox)
        form_layout2.addWidget(verification_name)
        form_layout2.addWidget(self.verification_name_combobox)
        form_layout2.addWidget(verification_date)
        form_layout2.addWidget(self.verification_date)
        form_layout2.addWidget(verification_time)
        form_layout2.addWidget(self.verification_time)
        form_layout2.addWidget(self.verification_submit_button)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)

        form_widget2 = QWidget()
        form_widget2.setLayout(form_layout2)

        spacer = QSpacerItem(300, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)

        content_layout.addWidget(add_files_title, 0, 0, 1, 2, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addWidget(form_widget, 1, 0, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addWidget(form_widget2, 1, 1, Qt.AlignHCenter | Qt.AlignTop)
        content_layout.addItem(spacer, 2, 0, 1, 2)

        content_layout.setRowStretch(0,1)
        content_layout.setRowStretch(1,2)
        content_layout.setRowStretch(2,3)

        content_layout.setAlignment(Qt.AlignHCenter)

        page.setLayout(content_layout)

    def populate_verification_names(self):
        chosen_instrument = self.verification_instrument_combobox.currentText()

        verification_list = self.instruments_list[chosen_instrument]

        self.verification_name_combobox.clear()
        self.verification_name_combobox.addItems(verification_list)

    def open_verification_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        start_directory = file_paths
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", start_directory, "All Files (*);;Text Files (*.txt)", options=options)
        if file_paths:
            self.verification_drag_and_drop_label.add_files(file_paths)

    def submit_instrument_verification(self):
        self.init_session()

        if len(self.verification_file_list_widget) >0:
            file_item = self.verification_file_list_widget.item(0)
            file_path = file_item.text()

            # Extract directories after "Instrument Verification"
            directories_after = self.get_directories_after("Instrument Verification", file_path)

            # Define new file path based on directories
            directory, old_file_name = os.path.split(file_path)
            new_file_name = self.generate_new_file_name(old_file_name, directories_after)
            new_file_path = os.path.join(directory, new_file_name)

            # Rename the file
            try:
                os.rename(file_path, new_file_path)
                print(f"Renamed {file_path} to {new_file_name}")
            except OSError as e:
                print(f"Error renaming {file_path} to {new_file_path}: {e}")

            try:
                query = Verifications(
                    Instrument=self.verification_instrument_combobox.currentText(),
                    Verification=self.verification_name_combobox.currentText(),
                    Date=self.verification_date.text(),
                    Time=self.verification_time.text(),
                    FilePath = self.verification_file_path
                )

                self.session.add(query)
            
                try:
                    current_datetime = datetime.now()

                    log_entry = LIMSActivity(
                        User=settings.value("username"),
                        TablesAffected="Verifications",
                        Action=f"{settings.value('username')} added verification)",
                        Notes=self.inorganic_notes_input.toPlainText(),
                        Date=current_datetime.date(),
                        Time=current_datetime.time()
                    )
                    self.session.add(log_entry)
                    self.session.commit()
                    # Show success message
                    QMessageBox.information(self, 'Success', 'Verification submitted')

                except SQLAlchemyError as log_error:
                    QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                    self.session.rollback()

                except Exception as e:
                    # Show error message
                    QMessageBox.critical(self, 'Error', f'Failed to add Verification: {str(e)}')

            finally:
                self.session.close()

    def get_directories_after(self, target_directory, full_path):
        # Normalize the path for consistency across different OS
        full_path = os.path.normpath(full_path)
        
        # Split the path into its components
        path_parts = full_path.split(os.sep)
        
        try:
            # Find the index of the target directory
            target_index = path_parts.index(target_directory)
            
            # Get all directory names after the target directory, excluding the file name
            directories_after = path_parts[target_index + 1:-1]
            
            return directories_after
        except ValueError:
            # Handle the case where the target directory is not found
            print(f"Directory '{target_directory}' not found in the path.")
            return []

    def generate_new_file_name(self, old_file_name, directories_after):
        # Extract the base name and extension from the old file name
        base, ext = os.path.splitext(os.path.basename(old_file_name))
        print(f"base, ext = {base}, {ext}")
        
        # Check if the last part of directories_after is a year
        if directories_after and directories_after[-1].isdigit() and len(directories_after[-1]) == 4:
            directories_parts = directories_after[:-1]
            print(directories_after)
            print(directories_parts)
        else:
            directories_parts = directories_after
            print(directories_after)
            print(directories_parts)
        
        # Join the directories parts to create the new file name
        new_file_name = f"{'_'.join(directories_parts)}_{base}{ext}"
        
        return new_file_name

# ██████   █████  ████████  ██████ ██   ██ ██ ███    ██  ██████  
# ██   ██ ██   ██    ██    ██      ██   ██ ██ ████   ██ ██       
# ██████  ███████    ██    ██      ███████ ██ ██ ██  ██ ██   ███ 
# ██   ██ ██   ██    ██    ██      ██   ██ ██ ██  ██ ██ ██    ██ 
# ██████  ██   ██    ██     ██████ ██   ██ ██ ██   ████  ██████  
                                                               
    def init_batching_page(self, page):
        self.method_pages = {}
        content_layout = QGridLayout()

        # Add Additional Files Section 
        batching_title = QLabel("Batching")
        batching_title.setFont(self.header_font)
        batching_title.setContentsMargins(0, 10, 0, 10)

        # Batch ID Widget
        batch_id_layout = QVBoxLayout()
        batch_id_label = QLabel('SDG')
        self.batch_id_input = QMultiSelectBox(self)

        self.batch_id_input.buttonClicked.connect(self.get_batching_sdgs)

        self.batch_id_button = QPushButton("Generate Batch", self)
        self.batch_id_button.clicked.connect(self.fetch_batching_methods)

        batch_id_layout.addWidget(batch_id_label)
        batch_id_layout.addWidget(self.batch_id_input)
        batch_id_layout.addWidget(self.batch_id_button)
        
        sdg_widget = QWidget()
        sdg_widget.setLayout(batch_id_layout)
        sdg_widget.setMaximumWidth(220)

        # Method QComboBox
        method_layout = QVBoxLayout()
        method_label = QLabel("Method")

        self.method_combobox = QComboBox(self)
        self.method_combobox.currentIndexChanged.connect(self.change_method)

        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combobox)

        method_widget = QWidget()
        method_widget.setLayout(method_layout)
        method_widget.setMaximumWidth(220)

        # Top Toolbar
        toolbar_layout = QHBoxLayout()

        toolbar_layout.addWidget(sdg_widget)
        toolbar_layout.addWidget(method_widget)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)

        # Separator between the top and bottom sections
        separatorH = QFrame()
        separatorH.setFrameShape(QFrame.HLine)
        separatorH.setFrameShadow(QFrame.Sunken)
        separatorH.setContentsMargins(0, 0, 0, 0)

        # Clerical Section
        form_layout = QHBoxLayout()

        self.submit_batch_button = QPushButton("Submit Batches", self)
        self.submit_batch_button.setFixedHeight(55)
        self.submit_batch_button.setFixedWidth(220)
        self.submit_batch_button.clicked.connect(self.submit_batch)

        additional_notes_layout = QVBoxLayout()

        batch_notes_label = QLabel("Additional Notes")
        self.batch_notes_input = QTextEdit(self)
        line_height = self.batch_notes_input.fontMetrics().lineSpacing()
        self.batch_notes_input.setFixedHeight(line_height * 4 + 10)
        self.batch_notes_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.batch_notes_input.setFixedWidth(220)

        additional_notes_layout.addWidget(batch_notes_label)
        additional_notes_layout.addWidget(self.batch_notes_input)

        additional_notes_widget = QWidget()
        additional_notes_widget.setLayout(additional_notes_layout)

        form_layout.addWidget(additional_notes_widget)
        form_layout.addWidget(self.submit_batch_button)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)

        content_layout.addWidget(batching_title, 0, 0, 1, 0, Qt.AlignHCenter)
        content_layout.addWidget(toolbar_widget, 1, 0, 1, 0, Qt.AlignTop)

        # Stacked Widget for Method-Specific Batch Boxes
        self.method_stack = QStackedWidget()
        content_layout.addWidget(self.method_stack, 2, 0, 9, 0)
        content_layout.addWidget(separatorH, 11, 0, 1, 1)
        content_layout.addWidget(form_widget, 12, 0, 1, 1)

        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        page.setLayout(content_layout)

    def get_batching_sdgs(self):
        try:
            self.init_session()

            results = (self.session.query(DQO.SDG.distinct())
                       .order_by(DQO.SDG.desc())
                       .all())
            
            sdgs = [result[0] for result in results]
            print("SDGS from get_batching_sdgs:", sdgs)

        except Exception as e:
            error_message = f"An error occurred while querying BatchID: {str(e)}"
            QMessageBox.critical(self, "Database Error", error_message)

        finally:
            if self.session:
                self.session.close()

        dialog = SDGSelectionPopup(sdgs)
        if dialog.exec_() == QDialog.Accepted:
            selected_sdg = dialog.getSelectedSDGs()
            self.batch_id_input.setCurrentText(selected_sdg)

    def submit_batch(self):
        try: 
            self.init_session()  # Initialize the database session
            if self.qc_to_delete:
                for sample_id, method in self.qc_to_delete:
                    qcs_to_delete = self.session.query(DQO).filter(
                        DQO.SampleID == sample_id,
                        DQO.Method == method
                    ).all()

                    for qc in qcs_to_delete:
                        print(f"Deleting QC sample: {qc.SampleID} (method: {qc.Method})")
                        self.session.delete(qc)

                self.session.commit()
            else:
                print("No QC samples to delete.")
        except Exception as e:
            print(f"An exception occurred during QC deletion: {e}")
            self.session.rollback()
        finally:
            self.session.close()

        methods_qc = lab_lists.methods_qc
        import random

        try:
            self.init_session()
            sdg = self.batch_id_input.getCurrentText()
            batch_box_contents = []
            batch_ids = []

            # Collecting methods and sample lists
            for method, page in self.method_pages.items():
                layout = page.layout()

                for i in range(layout.count()):
                    batch_box = layout.itemAt(i).widget()
                    sample_list = []
                    b = 0

                    for j in range(batch_box.sample_list.count()):
                        sample_item = batch_box.sample_list.item(j)
                        sample_id = sample_item.text()
                        sample_list.append(sample_id)

                    if sample_list:
                        batch_box_contents.append((method, sample_list))
                        b += 1
                        batch_id = f"{sdg}{method}{b}"
                        batch_ids.append(batch_id)

            batch_count = len(batch_box_contents)
            print(batch_ids)
            
            batches = {}

            for i in range(batch_count):
                method, samples = batch_box_contents[i]
                batches[batch_ids[i]] = {'method': method, 'samples': samples}

            try:

                matrix_results = self.session.query(DQO.Matrix.distinct()).filter(DQO.SDG == sdg).all()
                matrix_list = [result[0] for result in matrix_results]

                if len(matrix_list) > 1:
                    QMessageBox.warning(self, "Multiple Sample Matrices", "Batch contains more than one sample matrix, please rebatch.")
                    return
                elif len(matrix_list) == 1:
                    matrix = matrix_list[0]
                else:
                    QMessageBox.warning(self, "No Sample Matrices", "No sample matrices found for the provided SDGs.")
                    return

            except Exception as e:
                print(f"Error retrieving Sample Matrices: {e}")
                raise

            random_samples = []

            # Assign Batch IDs to samples and QC samples
            for batch_id, batch_info in batches.items():
                method = batch_info['method']
                samples = batch_info['samples']

                # Check if any sample in random_samples is also in the current batch's samples
                matched_sample = next((s for s in random_samples if s in samples), None)

                if matched_sample:
                    random_sample = matched_sample
                else:
                    random_sample = random.choice(samples)
                    random_samples.append(random_sample)

                # Determine QC samples based on method and matrix
                if method == "MET":
                    metals_method = f"{method} ({matrix})"
                    qc_samples = methods_qc.get(metals_method, [])
                    print(metals_method)
                else:
                    qc_samples = methods_qc.get(method, [])
                    print(method)

                # Create QC samples for this batch
                for qc in qc_samples:
                    if qc in ['DUP', 'MS', 'MSDUP']:
                        qc_sample_id = f"{random_sample}{qc}"
                    else:
                        qc_sample_id = f"{batch_id}{qc}"

                    # CHECK if QC sample already exists first
                    existing_qc_sample = self.session.query(DQO).filter(
                        DQO.SampleID == qc_sample_id,
                        DQO.Method == method
                    ).first()

                    if not existing_qc_sample:
                        sample_query = DQO(
                            BatchID=batch_id,
                            SampleID=qc_sample_id,
                            Method=method,
                            SDG=sdg,
                            Matrix=matrix
                        )
                        self.session.add(sample_query)
                    else:
                        print(f"QC sample {qc_sample_id} already exists. Skipping insertion.")

                # Update the BatchID for each sample
                for sample_id in samples:
                    existing_sample = self.session.query(DQO).filter(
                        DQO.SampleID == sample_id,
                        DQO.Method == method
                    ).first()

                    if existing_sample:
                        existing_sample.BatchID = batch_id
                    else:
                        new_sample = DQO(
                            SDG=sdg,
                            SampleID=sample_id,
                            Method=method,
                            BatchID=batch_id,
                            Matrix=matrix
                        )
                        self.session.add(new_sample)

            # Commit the batch assignments
            self.session.commit()

            # Generate the excel prepsheets
            from lims.reports.excel_prepsheets import GenerateExcelPrepsheets
            GenerateExcelPrepsheets.generate_prepsheets(sdg)

            QMessageBox.information(self, "Success", "Batch submitted successfully.")

        except Exception as e:
            self.session.rollback()
            print(f"Error occurred while submitting batches: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error occurred while updating batches: {str(e)}")
        finally:
            self.session.close()

    def fetch_batching_methods(self):
        sdgs = [sdg.strip() for sdg in self.batch_id_input.getCurrentText().strip().split(',')]

        try:
            self.init_session()

            method_query = (
                self.session.query(DQO.Method.distinct())
                .filter(DQO.SDG.in_(sdgs))
                .all()
            )

            self.unique_methods = [result[0] for result in method_query]

            self.method_combobox.clear()
            self.method_combobox.addItems(self.unique_methods)

            self.create_method_pages()

        except Exception as e:
            print(f"HERE ACTUALLY: Error occurred while reading SQL query: {str(e)}")
        finally:
            if self.session:
                self.session.close()

    """
    Known Issue:
    Need to make it so that the batches do not capture QC samples, deletes any QC for that batch, then regenerates them. Maybe just a complete delete batch id from the table, and any QC attached to it.
    """

    def create_method_pages(self):
        for method in self.unique_methods:
            page = QWidget()
            layout = QHBoxLayout()
            
            for j in range(6):
                label_text = f'Batch Box'
                batch_box = BatchBox(label_text)
                layout.addWidget(batch_box)
        
            page.setLayout(layout)
            self.method_pages[method] = page
            self.method_stack.addWidget(page)

        self.populate_sample_groups()

    def get_latest_batch(self):
        try:
            self.init_session()

            latest_batch = self.session.query(DQO.BatchID).order_by(desc(DQO.BatchID)).first()

            return latest_batch[0]
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.session.close()

    def change_method(self):
        method = self.method_combobox.currentText()
        if method in self.method_pages:
            self.method_stack.setCurrentWidget(self.method_pages[method])

    def populate_sample_groups(self):
        for method, page in self.method_pages.items():
            layout = page.layout()
            for i in range(layout.count()):
                batch_box = layout.itemAt(i).widget()
                print(f"Clearing samples in BatchBox for method {method}, BatchBox {i}")
                batch_box.clear_samples()

        sdgs = [sdg.strip() for sdg in self.batch_id_input.getCurrentText().strip().split(',')]

        list_of_dicts = []

        methods_qc = lab_lists.methods_qc

        try:
            self.init_session()
            for sdg in sdgs:
                sample_query = self.session.query(DQO).filter(DQO.SDG == sdg).all()

                # Get the first DQO object from the query results
                first_sample = sample_query[0]

                # Now you can access the 'Matrix' attribute of the first DQO object
                matrix = first_sample.Matrix

                for sample in sample_query:
                    sample_dict = sample.__dict__
                    list_of_dicts.append(sample_dict)

            batch_samples_df = pd.DataFrame(list_of_dicts)

            print("BATCH SAMPLES DF")
            print(batch_samples_df)

            self.qc_to_delete = set()

            # Populate the first BatchBox with all samples
            for _, row in batch_samples_df.iterrows():
                sample_name = row['SampleID']
                method = row['Method']

                if method in self.method_pages:
                    print(f"{method} in method pages")
                    if method == 'MET':
                        method = f"{method} ({matrix})"
                    if any(qc in sample_name.upper() for qc in methods_qc[method]):
                        method = row['Method']  # Reset if MET was renamed
                        self.qc_to_delete.add((sample_name, method))
                        print(f"Marked for deletion: {sample_name} (method: {method})")
                        pass
                    else:
                        method = row['Method']
                        page = self.method_pages[method]
                        layout = page.layout()
                        first_batch_box = layout.itemAt(0).widget()  # Get the first BatchBox
                        first_batch_box.add_sample(sample_name)

        except Exception as e:
            print(f"Error occurred while reading SQL query: {str(e)}")

        finally:
            self.session.close()

# ██████   █████  ██████       ██████  ██████   █████  
# ██   ██ ██   ██ ██   ██     ██      ██    ██ ██   ██ 
# ██████  ███████ ██   ██     ██      ██    ██ ███████ 
# ██   ██ ██   ██ ██   ██     ██      ██    ██ ██   ██ 
# ██   ██ ██   ██ ██████       ██████  ██████  ██   ██ 

    def init_rad_coa_page(self, page):
        from PyQt5.QtGui import QDoubleValidator
        validator = QDoubleValidator()

        page_container = QHBoxLayout()

        file_list_widget = FileListWidget()
        file_list_widget.setFixedWidth(400)
        file_list_widget.setFixedHeight(200)

        drag_and_drop_label = DragAndDropLabel(file_list_widget)
        drag_and_drop_label.setFixedWidth(400)
        drag_and_drop_label.setFixedHeight(200)

        file_search_button = QPushButton("Search for Files")
        file_search_button.clicked.connect(lambda: self.open_file_dialog(drag_and_drop_label))

        content_layout = QGridLayout()

        title = QLabel("Certificate of Calibration Generator")
        title.setFont(self.header_font)
        title.setContentsMargins(0,10,0,10)

        # Certificate info
        radionuclide = QComboBox()
        radionuclide_list = ['Select Radionuclide']
        radionuclide_list.extend(lab_lists.rad_isotopes)

        radionuclide.addItems(radionuclide_list)

        half_life = QLineEdit()
        half_life.setValidator(validator)

        srs = QLineEdit()

        source_activity = QLineEdit()
        source_activity.setValidator(validator)

        source_activity_units = QComboBox()
        source_activity_units.addItems(['Select Units', 'Bq', 'dpm', 'pCi'])

        source_volume = QLineEdit()
        source_volume.setValidator(validator)

        source_activity_date = QDateEdit()
        source_activity_date.setCalendarPopup(True)
        source_activity_date.setDate(QDate.currentDate())
        source_activity_date.setDisplayFormat("MM-dd-yyyy")
        source_activity_date.setFixedWidth(110)

        solution_prep_date = QDateEdit()
        solution_prep_date.setCalendarPopup(True)
        solution_prep_date.setDate(QDate.currentDate())
        solution_prep_date.setDisplayFormat("MM-dd-yyyy")
        solution_prep_date.setFixedWidth(110)

        chemical_composition = QSubscriptInput()

        # Laboratory operations
        initial_weight = QLineEdit()
        initial_weight.setValidator(validator)

        final_weight = QLineEdit()
        final_weight.setValidator(validator)

        solution_mass = QLineEdit()
        solution_mass.setValidator(validator)

        dilution_solution = QTextEdit()
        line_height = dilution_solution.fontMetrics().lineSpacing()
        dilution_solution.setFixedHeight(line_height * 4 + 10)
        dilution_solution.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        final_activity = QLineEdit()
        final_activity.setEnabled(False)

        percent_abundance = QLineEdit()
        percent_abundance.setValidator(validator)

        to_activity_date = QDateEdit()
        to_activity_date.setCalendarPopup(True)
        to_activity_date.setDate(QDate.currentDate())
        to_activity_date.setDisplayFormat("MM-dd-yyyy")
        to_activity_date.setFixedWidth(110)

        expiration_date = QDateEdit()
        expiration_date.setCalendarPopup(True)
        expiration_date.setDate(QDate.currentDate())
        expiration_date.setDisplayFormat("MM-dd-yyyy")
        expiration_date.setFixedWidth(110)

        analyst = QLineEdit()
        analyst.setEnabled(False)
        analyst.setText(settings.value("username"))

        calculation_date = QDateEdit()
        calculation_date.setCalendarPopup(True)
        calculation_date.setDate(QDate.currentDate())
        calculation_date.setDisplayFormat("MM-dd-yyyy")
        calculation_date.setFixedWidth(110)

        button = QPushButton("Generate")
        button.setFixedHeight(55)
        button.setFixedWidth(220)

        consumable_type = QComboBox()
        consumable_type.addItems(['Select Type', 'LCS', 'Tracer'])

        content_layout.setColumnStretch(0, 1)  # Allow column 0 to expand
        content_layout.setColumnStretch(7, 1)  # Allow column 7 to expand

        # Add new spacer at the first and last column
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0, 22, 1)
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 7, 22, 1)

        # Title
        content_layout.addWidget(title, 0, 1, 1, 6, Qt.AlignHCenter)

        # Header (Shifted down by 1 row)
        content_layout.addWidget(QLabel("Principle Radionuclide"), 1, 1, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(radionuclide, 2, 1, 1, 2, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Half-Life (Days)"), 1, 3, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(half_life, 2, 3, 1, 2, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Solution Prep Date"), 1, 5, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(solution_prep_date, 2, 5, 1, 2, Qt.AlignHCenter)

        # Spacer after header
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 3, 1, 1, 6)

        # Certificate info (Shifted down by 1 row)
        content_layout.addWidget(QLabel("SRS"), 4, 1, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(srs, 5, 1, 1, 1, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Source Activity"), 4, 2, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(source_activity, 5, 2, 1, 1, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Units"), 4, 3, 1, 1, Qt.AlignLeft)
        content_layout.addWidget(source_activity_units, 5, 3, 1, 1, Qt.AlignLeft)

        content_layout.addWidget(QLabel("Source Volume (L)"), 4, 4, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(source_volume, 5, 4, 1, 2, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Source Activity Date"), 4, 6, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(source_activity_date, 5, 6, 1, 1, Qt.AlignHCenter)

        # Spacer after certificate info
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 6, 1, 1, 6)

        # Chemical Composition (Shifted down by 1 row)
        content_layout.addWidget(QLabel("Chemical Composition"), 7, 1, 1, 1, Qt.AlignRight)
        content_layout.addWidget(chemical_composition, 7, 2, 1, 2, Qt.AlignLeft)

        content_layout.addWidget(QLabel("Dilution Solution"), 7, 4, 1, 1, Qt.AlignRight)
        content_layout.addWidget(dilution_solution, 7, 5, 1, 2, Qt.AlignLeft)

        # Spacer after Chemical Composition
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 8, 1, 1, 6)

        # Laboratory operations (Shifted down by 1 row)
        content_layout.addWidget(QLabel("Initial Container Weight (g)"), 9, 1, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(initial_weight, 10, 1, 1, 2, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Final Container Weight (g)"), 9, 3, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(final_weight, 10, 3, 1, 2, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Solution Mass (g)"), 9, 5, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(solution_mass, 10, 5, 1, 2, Qt.AlignHCenter)

        # Spacer after Laboratory operations
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 11, 1, 1, 6)

        # Spacer after Dilution Solution
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 13, 1, 1, 6)

        content_layout.addWidget(QLabel("Final Activity (pCi/g)"), 14, 2, 1, 1, Qt.AlignRight)
        content_layout.addWidget(final_activity, 14, 3, 1, 1, Qt.AlignLeft)

        content_layout.addWidget(QLabel("Percent Abundance"), 15, 2, 1, 1, Qt.AlignRight)
        content_layout.addWidget(percent_abundance, 15, 3, 1, 1, Qt.AlignLeft)

        content_layout.addWidget(QLabel("To Activity Date"), 14, 4, 1, 1, Qt.AlignRight)
        content_layout.addWidget(to_activity_date, 14, 5, 1, 1, Qt.AlignLeft)

        content_layout.addWidget(QLabel("Expiration Date"), 15, 4, 1, 1, Qt.AlignRight)
        content_layout.addWidget(expiration_date, 15, 5, 1, 1, Qt.AlignLeft)

        # Spacer after Calculations
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 17, 1, 1, 6)

        content_layout.addWidget(QLabel("Verified By"), 18, 1, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(analyst, 19, 1, 1, 3, Qt.AlignHCenter)

        content_layout.addWidget(QLabel("Calculation Date"), 18, 4, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(calculation_date, 19, 4, 1, 3, Qt.AlignHCenter)

        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 20, 1, 1, 6)

        content_layout.addWidget(button, 21, 6, 1, 1, Qt.AlignHCenter)
        content_layout.addWidget(QLabel("Consumable Type"), 21, 1, 1, 1, Qt.AlignRight)
        content_layout.addWidget(consumable_type, 21, 2, 1, 1, Qt.AlignLeft)

        # Spacer after final section
        content_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Expanding), 22, 1, 1, 6)

        widgets = [
            radionuclide, half_life, srs, source_activity, source_volume, source_activity_date, 
            solution_prep_date, chemical_composition, initial_weight, final_weight, solution_mass, 
            dilution_solution, final_activity, percent_abundance, to_activity_date, 
            expiration_date, analyst, calculation_date, consumable_type
        ]

        # Set max width dynamically
        for widget in widgets:
            widget.setFixedWidth(180)

        page.setLayout(content_layout)

        button.clicked.connect(lambda: self.gather_rad_coa_data(content_layout, chemical_composition.getCurrentText))

    def gather_rad_coa_data(self, content_layout, chemical_composition_text):
        data = {}

        # Map positions of labels for easy lookup
        label_positions = {}

        # First, find all labels and store their positions
        for i in range(content_layout.count()):
            item = content_layout.itemAt(i)
            widget = item.widget()

            if isinstance(widget, QLabel):
                row, col, _, _ = content_layout.getItemPosition(i)
                label_positions[(row, col)] = widget.text().strip()

        # Now, map the input widgets to their nearest label (to the left or above)
        for i in range(content_layout.count()):
            item = content_layout.itemAt(i)
            widget = item.widget()

            if widget and not isinstance(widget, QLabel):
                row, col, _, _ = content_layout.getItemPosition(i)

                # Try to find a label on the same row to the left
                label_text = None
                for offset in range(1, col + 1):
                    label_text = label_positions.get((row, col - offset))
                    if label_text:
                        break

                # If not found, try to find a label in the row above
                if not label_text:
                    label_text = label_positions.get((row - 1, col))

                # If a label was found, get the widget's value
                if label_text:
                    if isinstance(widget, QLineEdit):
                        data[label_text] = widget.text()
                    elif isinstance(widget, QDateEdit):
                        data[label_text] = widget.date().toString("MM-dd-yyyy")
                    elif isinstance(widget, QComboBox):
                        if 'Select' in widget.currentText():
                            QMessageBox.critical(self, "Error", f"Please select {label_text}.")
                            return
                        else:
                            data[label_text] = widget.currentText()
                    elif isinstance(widget, QTextEdit):
                        data[label_text] = widget.toPlainText()
                    elif isinstance(widget, QSubscriptInput):
                        data[label_text] = widget.getCurrentText()
                    elif hasattr(widget, 'text'):  # For custom widgets
                        data[label_text] = widget.text()

        print("Data", data)

        from lims.core import CalibrationCertificate

        self.upload_rad_coa_data(data)

        CalibrationCertificate.GenerateCertificate.generate_pdf(data)

    def upload_rad_coa_data(self, data):
        try:
            self.init_session()

            cleaned_data = {}

            # Rename the keys to be in SQL case
            for key, value in data.items():
                # Remove parentheses and their contents
                new_key = re.sub(r'\s*\(.*?\)', '', key)
                # Remove spaces and dashes, and convert to SQL-style
                new_key = new_key.strip().replace(' ', '')
                new_key = new_key.strip().replace('-', '')
                cleaned_data[new_key] = value

            print("Cleaned Data", cleaned_data)

            record = RADCerts(**cleaned_data)

            self.session.add(record)

            self.session.commit()

        except Exception as e:
            self.session.rollback()
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

#  ██████  ██████  ███    ██ ███████ ██    ██ ███    ███  █████  ██████  ██      ███████     ██       ██████   ██████  ██ ███    ██ 
# ██      ██    ██ ████   ██ ██      ██    ██ ████  ████ ██   ██ ██   ██ ██      ██          ██      ██    ██ ██       ██ ████   ██ 
# ██      ██    ██ ██ ██  ██ ███████ ██    ██ ██ ████ ██ ███████ ██████  ██      █████       ██      ██    ██ ██   ███ ██ ██ ██  ██ 
# ██      ██    ██ ██  ██ ██      ██ ██    ██ ██  ██  ██ ██   ██ ██   ██ ██      ██          ██      ██    ██ ██    ██ ██ ██  ██ ██ 
#  ██████  ██████  ██   ████ ███████  ██████  ██      ██ ██   ██ ██████  ███████ ███████     ███████  ██████   ██████  ██ ██   ████ 

    def init_consumable_login_page(self, page):
        content_layout = QGridLayout()

        title = QLabel("Consumable Login")
        title.setFont(self.header_font)
        title.setContentsMargins(0,10,0,10)

        # Consumable Widgets
        consumable_id = QLineEdit()
        consumable_id.setFixedWidth(220)
        consumable_id.setEnabled(False)

        lot_number = QLineEdit()
        lot_number.setFixedWidth(220)

        applicable_methods = QMultiSelectBox()
        applicable_methods.setFixedWidth(220)
        applicable_methods.buttonClicked.connect(lambda: self.method_multiselect(applicable_methods))

        applicable_matrices = QMultiSelectBox()
        applicable_matrices.setFixedWidth(220)
        applicable_matrices.buttonClicked.connect(lambda: self.matrix_multiselect(applicable_matrices))

        consumable_type = QComboBox()
        consumable_type.addItems(['Select a Type'] + lab_lists.consumable_type_list)
        consumable_type.setFixedWidth(175)

        start_date = QDateEdit()
        start_date.setCalendarPopup(True)
        start_date.setDate(QDate.currentDate())
        start_date.setDisplayFormat("MM-dd-yyyy")
        start_date.setFixedWidth(110)
        
        expiration_date = QDateEdit()
        expiration_date.setCalendarPopup(True)
        expiration_date.setDate(QDate.currentDate())
        expiration_date.setDisplayFormat("MM-dd-yyyy")
        expiration_date.setFixedWidth(110)

        compound = QSubscriptInput()
        compound.setFixedWidth(175)

        line_height = compound.fontMetrics().lineSpacing()
        compound.setFixedHeight(line_height + 10)

        file_list_widget = FileListWidget()
        file_list_widget.setFixedWidth(400)
        file_list_widget.setFixedHeight(200)
        
        drag_and_drop_label = DragAndDropLabel(file_list_widget)
        drag_and_drop_label.setFixedWidth(400)
        drag_and_drop_label.setFixedHeight(200)

        search_button = QPushButton("Search for Files")
        search_button.clicked.connect(lambda: self.open_file_dialogue(drag_and_drop_label, file_paths.consumables_inventory_directory))

        file_search_container = QVBoxLayout()
        file_search_container.addWidget(file_list_widget)
        file_search_container.addWidget(drag_and_drop_label)
        file_search_container.addWidget(search_button)

        file_search_widget = QWidget()

        file_search_widget.setLayout(file_search_container)

        # Scrollable area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()

        # Layout within the scrollable area to hold all content
        scroll_area_layout = QVBoxLayout(scroll_content)

        # Layout within the scrollable area to hold generated rows
        consumable_row_container = QVBoxLayout()
        consumable_row_container.setAlignment(Qt.AlignCenter)
        scroll_area_layout.addLayout(consumable_row_container)

        # Ad spacer to scrollable area
        scroll_area_layout.addItem(QSpacerItem(40, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Add line button
        add_line_button = QPushButton("Add Component")
        scroll_area_layout.addWidget(add_line_button)

        # Set the scroll content widget and its layout
        scroll_area.setWidget(scroll_content)
        scroll_area.setFixedHeight(300)
        scroll_area.setFixedWidth(900)

        # Notes and submit button
        notes = QTextEdit()
        line_height = notes.fontMetrics().lineSpacing()
        notes.setFixedHeight(line_height * 4 + 10)
        notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        button = QPushButton("Submit")
        button.setFixedWidth(220)
        button.setFixedHeight(75)

        # Track the added lines
        consumable_component_list = []

        # Title
        content_layout.addWidget(title, 0, 0, 1, 6, Qt.AlignHCenter)
        # Spacer
        content_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding), 1, 0, 1, 6)
        # Top row of input labels
        content_layout.addWidget(QLabel("Lot Number"), 2, 0, 1, 1)
        content_layout.addWidget(QLabel("Compound"), 2, 1, 1, 1)
        content_layout.addWidget(QLabel("Applicable Methods"), 2, 2, 1, 1)
        content_layout.addWidget(QLabel("Applicable Matrices"), 2, 3, 1, 1)
        content_layout.addWidget(QLabel("Opened / Prepped"), 2, 4, 1, 1)
        content_layout.addWidget(QLabel("Expiration Date"), 2, 5, 1, 1)
        # Top row of inputs
        content_layout.addWidget(lot_number, 3, 0, 1, 1)
        content_layout.addWidget(compound, 3, 1, 1, 1)
        content_layout.addWidget(applicable_methods, 3, 2, 1, 1)
        content_layout.addWidget(applicable_matrices, 3, 3, 1, 1)
        content_layout.addWidget(start_date, 3, 4, 1, 1)
        content_layout.addWidget(expiration_date, 3, 5, 1, 1)
        # Spacer
        content_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding), 4, 0, 1, 6)
        # Consumable ID
        content_layout.addWidget(QLabel("Consumable ID"), 5, 0, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(consumable_id, 6, 0, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(QLabel("Consumable Type"), 5, 3, 1, 3, Qt.AlignHCenter)
        content_layout.addWidget(consumable_type, 6, 3, 1, 3, Qt.AlignHCenter)
        # Spacer
        content_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding), 7, 0, 1, 6)
        # File Drag and Drop
        content_layout.addWidget(file_search_widget, 8, 0, 2, 2)
        # Scroll Area
        content_layout.addWidget(scroll_area, 8, 2, 2, 4, Qt.AlignHCenter)
        # Spacer
        content_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding), 10, 0, 1, 6)
        # Bottom button and notes
        content_layout.addWidget(QLabel("Additional Notes"), 11, 0, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(notes, 12, 0, 1, 2, Qt.AlignHCenter)
        content_layout.addWidget(button, 12, 4, 1, 2, Qt.AlignHCenter)

        headers = False 

        # Add initial component line
        self.add_consumable_component(headers, consumable_component_list, consumable_row_container, scroll_content, scroll_area)

        headers = True

        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0,0,0,0)

        page.setLayout(content_layout)

        self.consumable_id_generator(lot_number, start_date, consumable_id)

        # Add signals
        add_line_button.clicked.connect(lambda: self.add_consumable_component(headers, consumable_component_list, consumable_row_container, scroll_content, scroll_area))
        button.clicked.connect(lambda: self.log_consumable(consumable_id, lot_number, applicable_methods, consumable_type, start_date, expiration_date, compound, notes, consumable_component_list, file_list_widget, applicable_matrices))
        lot_number.textChanged.connect(lambda: self.consumable_id_generator(lot_number, start_date, consumable_id))
        start_date.dateChanged.connect(lambda: self.consumable_id_generator(lot_number, start_date, consumable_id))

    def open_file_dialogue(self, label, start_directory):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path_list, _ = QFileDialog.getOpenFileNames(self, "Select Vendor Certificate", start_directory, "All Files (*);;Text Files (*.txt)", options=options)
        if file_path_list:
            label.add_files(file_path_list)

    def log_consumable(self, consumable_id, lot_number, applicable_methods, consumable_type, start_date, expiration_date, compound, notes, consumable_component_list, file_list_widget, applicable_matrices):
        widget_dict = {key: [entry[key] for entry in consumable_component_list] for key in consumable_component_list[0]}

        extracted_data = {}

        for key, widget_list in widget_dict.items():
            extracted_values = []

            for widget in widget_list:
                text_value = widget.text().strip()  # Remove leading/trailing spaces
                if text_value:  # Only append non-empty values
                    extracted_values.append(text_value)
            
            widgets_string = ", ".join(extracted_values)

            extracted_data[key] = widgets_string

        file_path_list = file_list_widget.get_file_paths()

        file_path_string = ", ".join(file_path_list) if len(file_path_list) > 1 else file_path_list[0]

        consumable_data = {
            'ConsumableID': consumable_id.text(),
            'LotNumber': lot_number.text(),
            'Compound': compound.getCurrentText(),
            'Method': applicable_methods.getCurrentText(),
            'Matrix': applicable_matrices.getCurrentText(),
            'Type': consumable_type.currentText(),
            'StartDate': start_date.date().toPyDate(),
            'ExpirationDate': expiration_date.date().toPyDate(),
            'Component': extracted_data['Component'],
            'Volume': extracted_data['Volume'],
            'Mass': extracted_data['Mass'],
            'Concentration': extracted_data['Concentration'],
            'Activity': extracted_data['Activity'],
            'Status': True,
            'FilePath': file_path_string,
        }

        try:
            self.init_session()

            # Check for existing record
            existing_record = self.session.query(ConsumableManagement).filter(
                ConsumableManagement.Type == consumable_data['Type'],
                ConsumableManagement.ConsumableID == consumable_data['ConsumableID'],
                ConsumableManagement.LotNumber == consumable_data['LotNumber'],
                ConsumableManagement.Matrix == consumable_data['Matrix'],
                ConsumableManagement.Component == consumable_data['Component'],
                ConsumableManagement.StartDate == consumable_data['StartDate'],
                ConsumableManagement.Status == True
            ).first()

            if existing_record:
                QMessageBox.critical(self, "Error", f"This consumable has already been entered.\n\nEdit in Consumable Management instead.")
            else:
            # Insert record into table.
                new_consumable = ConsumableManagement(
                    ConsumableID=consumable_data['ConsumableID'],
                    Compound=consumable_data['Compound'],
                    Method=consumable_data['Method'],
                    Matrix=consumable_data['Matrix'],
                    Type=consumable_data['Type'],
                    StartDate=consumable_data['StartDate'],
                    ExpirationDate=consumable_data['ExpirationDate'],
                    LotNumber=consumable_data['LotNumber'],
                    Component=consumable_data['Component'],
                    Volume=consumable_data['Volume'],
                    Mass=consumable_data['Mass'],
                    Concentration=consumable_data['Concentration'],
                    Activity=consumable_data['Activity'],
                    Status=consumable_data['Status'],
                    FilePath=consumable_data['FilePath']
                )

                self.session.add(new_consumable)
                self.session.commit()
                QMessageBox.information(self, "Success", "Consumable added successfully!")

        except Exception as e:
            self.session.rollback()
            print(f"An exception occurred: {e}")
        finally:
            self.session.close()

            # Convert date fields before passing the data
            consumable_data['StartDate'] = consumable_data['StartDate'].strftime("%Y-%m-%d")
            consumable_data['ExpirationDate'] = consumable_data['ExpirationDate'].strftime("%Y-%m-%d")

            print(consumable_data)

            if len(file_path_list) > 0:
                consumable_form.GenerateConsumableForm.generate_form(consumable_data, file_path_list)

    def consumable_id_generator(self, consumable_name, start_date, consumable_id):
        consumable_name_text = consumable_name.text()
        start_date_text = start_date.date().toPyDate().strftime("%m-%d-%y")

        consumable_id_text = f"{consumable_name_text} {start_date_text}"

        consumable_id.setText(consumable_id_text)

    def matrix_multiselect(self, multiselect_widget):
        matrices = ['AF', 'AQ', 'SM', 'SO']

        dialog = MatrixSelectionPopup(matrices)

        if dialog.exec_() == QDialog.Accepted:
            selected_matrices = dialog.getSelectedMethods()
            if selected_matrices:
                selected_matrices_text = ', '.join(selected_matrices)
                multiselect_widget.setCurrentText(selected_matrices_text)

    def method_multiselect(self, multiselect_widget):
        methods = lab_lists.method_list

        dialog = MethodSelectionPopup(methods)

        if dialog.exec_() == QDialog.Accepted:
            selected_methods = dialog.getSelectedMethods()
            if selected_methods:
                selected_methods_text = ', '.join(selected_methods)
                multiselect_widget.setCurrentText(selected_methods_text)

    def add_consumable_component(self, headers, consumable_component_list, consumable_row_container, scroll_content, scroll_area):
        lot_number = QLineEdit()

        component = QLineEdit()

        volume = QLineEdit()

        mass = QLineEdit()

        concentration = QLineEdit()

        activity = QLineEdit()

        widget_layout = QGridLayout()

        line_height = lot_number.fontMetrics().lineSpacing()
        lot_number.setFixedHeight(line_height + 10)
        component.setFixedHeight(line_height + 10)
        volume.setFixedHeight(line_height + 10)
        mass.setFixedHeight(line_height + 10)
        concentration.setFixedHeight(line_height + 10)
        activity.setFixedHeight(line_height + 10)

        lot_number.setMaximumWidth(220)
        component.setMaximumWidth(220)
        volume.setMaximumWidth(110)
        mass.setMaximumWidth(110)
        concentration.setMaximumWidth(110)
        activity.setMaximumWidth(110)

        if not headers:
            widget_layout.addWidget(QLabel("Component"), 0, 0, 1, 1)
            widget_layout.addWidget(QLabel("Volume (L)"), 0, 1, 1, 1)
            widget_layout.addWidget(QLabel("Mass (g)"), 0, 2, 1, 1)
            widget_layout.addWidget(QLabel("Concentration"), 0, 3, 1, 1)
            widget_layout.addWidget(QLabel("Activity (pCi)"), 0, 4, 1, 1)
        else:
            pass

        widget_layout.addWidget(component, 1, 0, 1, 1)
        widget_layout.addWidget(volume, 1, 1, 1, 1)
        widget_layout.addWidget(mass, 1, 2, 1, 1)
        widget_layout.addWidget(concentration, 1, 3, 1, 1)
        widget_layout.addWidget(activity, 1, 4, 1, 1)

        widget_layout.setContentsMargins(0, 5, 0, 5)

        widget = QWidget()
        widget.setLayout(widget_layout)
        widget.setMaximumHeight(50)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        consumable_row_container.addWidget(widget)

        consumable_component_list.append({
            'Component': component,
            'Volume': volume,
            'Mass': mass,
            'Concentration': concentration,
            'Activity': activity
        })

        scroll_content.adjustSize()

        QTimer.singleShot(50, lambda: self.scroll_to_bottom(scroll_area))

    def scroll_to_bottom(self, scroll_area):
        scrollbar = scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

# ███████  ██████  ██    ██ ██ ██████  ███    ███ ███████ ███    ██ ████████     ███    ███  █████  ███    ██  █████   ██████  ███████ ███    ███ ███████ ███    ██ ████████ 
# ██      ██    ██ ██    ██ ██ ██   ██ ████  ████ ██      ████   ██    ██        ████  ████ ██   ██ ████   ██ ██   ██ ██       ██      ████  ████ ██      ████   ██    ██    
# █████   ██    ██ ██    ██ ██ ██████  ██ ████ ██ █████   ██ ██  ██    ██        ██ ████ ██ ███████ ██ ██  ██ ███████ ██   ███ █████   ██ ████ ██ █████   ██ ██  ██    ██    
# ██      ██ ▄▄ ██ ██    ██ ██ ██      ██  ██  ██ ██      ██  ██ ██    ██        ██  ██  ██ ██   ██ ██  ██ ██ ██   ██ ██    ██ ██      ██  ██  ██ ██      ██  ██ ██    ██    
# ███████  ██████   ██████  ██ ██      ██      ██ ███████ ██   ████    ██        ██      ██ ██   ██ ██   ████ ██   ██  ██████  ███████ ██      ██ ███████ ██   ████    ██    
#             ▀▀                                                                                                                                                             

    def init_equipment_management_page(self, page):
        content_layout = QGridLayout()

        # Add Equipment
        form_layout = QVBoxLayout()
        form_layout_2 = QVBoxLayout()
        form_layout_3 = QVBoxLayout()

        self.equipment_list = ["Select Equipment", "Pipette", "Meter", "Top-Loading Balance", "Analytical Balance", "Hot Block", "Mass Weight Set", "Thermometer", "Oven", "Refrigerator", "Water Purification System"]

        self.stacked_equipment_widget = QStackedWidget()

        # Editor Title
        equipment_login_title_layout = QHBoxLayout()
        equipment_login_title_layout.setAlignment(Qt.AlignHCenter)

        self.equipment_login_title = QLabel("Equipment Log In")
        self.equipment_login_title.setFont(self.header_font)
        self.equipment_login_title.setContentsMargins(0, 10, 0, 10)

        equipment_login_title_layout.addWidget(self.equipment_login_title)

        equipment_login_title_widget = QWidget()
        equipment_login_title_widget.setLayout(equipment_login_title_layout)

        self.add_equipment_label = QLabel("Add Equipment")
        self.add_equipment_combobox = QComboBox()
        self.add_equipment_combobox.addItems(self.equipment_list)
        self.add_equipment_combobox.currentIndexChanged.connect(self.init_stacked_equipment_widget)

        self.add_equipment_date_label = QLabel("Date")
        self.add_equipment_date_input = QDateEdit(self)
        self.add_equipment_date_input.setCalendarPopup(True)
        self.add_equipment_date_input.setDate(QDate.currentDate())
        self.add_equipment_date_input.setDisplayFormat("MM-dd-yyyy")

        self.add_equipment_time_label = QLabel("Time")
        self.add_equipment_time_input = QTimeEdit(self)
        self.add_equipment_time_input.setTime(QTime.currentTime())
        self.add_equipment_time_input.setDisplayFormat("HH:mm")

        self.serial_number_label = QLabel("Serial Number")
        self.serial_number_input = QLineEdit(self)

        self.model_label = QLabel("Model")
        self.model_input = QLineEdit(self)

        self.brands = []

        self.brand_label = QLabel("Brand")
        self.brand_input = QLineEdit(self)

        self.owners = []

        self.ownership_label = QLabel("Ownership")
        self.ownership_input = QLineEdit(self)

        self.locations = []

        self.location_label = QLabel("Location")
        self.location_input = QLineEdit(self)

        self.tag_number_label = QLabel("Tag Number")
        self.tag_number_input = QLineEdit(self)

        self.verified_label = QLabel("Verified")
        self.verified_checkbox = QCheckBox()
        self.verified_checkbox.setChecked(True)

        self.comments_label = QLabel("Additional Notes")
        self.comments_textbox = QTextEdit(self)
        # Calculate the height for 4 lines of text
        line_height = self.comments_textbox.fontMetrics().lineSpacing()
        self.comments_textbox.setFixedHeight(line_height * 4 + 10)
        self.comments_textbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.log_equipment_button = QPushButton("Log Equipment", self)
        self.log_equipment_button.clicked.connect(self.log_equipment)

        form_layout.addWidget(self.add_equipment_label)
        form_layout.addWidget(self.add_equipment_combobox)
        form_layout.addWidget(self.stacked_equipment_widget)
        form_layout_2.addWidget(self.add_equipment_date_label)
        form_layout_2.addWidget(self.add_equipment_date_input)
        form_layout_2.addWidget(self.add_equipment_time_label)
        form_layout_2.addWidget(self.add_equipment_time_input)
        form_layout_2.addWidget(self.serial_number_label)
        form_layout_2.addWidget(self.serial_number_input)
        form_layout_2.addWidget(self.model_label)
        form_layout_2.addWidget(self.model_input)
        form_layout_2.addWidget(self.brand_label)
        form_layout_2.addWidget(self.brand_input)
        form_layout_3.addWidget(self.ownership_label)
        form_layout_3.addWidget(self.ownership_input)
        form_layout_3.addWidget(self.location_label)
        form_layout_3.addWidget(self.location_input)
        form_layout_3.addWidget(self.tag_number_label)
        form_layout_3.addWidget(self.tag_number_input)
        form_layout_3.addWidget(self.comments_label)
        form_layout_3.addWidget(self.comments_textbox)
        form_layout_3.addWidget(self.log_equipment_button)

        form_layout.setAlignment(Qt.AlignTop)
        form_layout_2.setAlignment(Qt.AlignTop)
        form_layout_3.setAlignment(Qt.AlignTop)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setFixedWidth(220)

        form_widget_2 = QWidget()
        form_widget_2.setLayout(form_layout_2)
        form_widget_2.setFixedWidth(220)

        form_widget_3 = QWidget()
        form_widget_3.setLayout(form_layout_3)
        form_widget_3.setFixedWidth(220)

        forms_layout = QHBoxLayout()
        forms_widget = QWidget()

        forms_layout.addWidget(form_widget)
        forms_layout.addWidget(form_widget_2)
        forms_layout.addWidget(form_widget_3)

        forms_widget.setLayout(forms_layout)

        # Separator between the left and right sections
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setContentsMargins(0, 0, 0, 0)  # Set margins to zero for separator

        # Equipment Editor Title
        equipment_editor_title_layout = QHBoxLayout()
        equipment_editor_title_layout.setAlignment(Qt.AlignHCenter)

        self.equipment_editor_title = QLabel("Equipment Editor")
        self.equipment_editor_title.setFont(self.header_font)

        equipment_editor_title_layout.addWidget(self.equipment_editor_title)

        equipment_editor_title_widget = QWidget()
        equipment_editor_title_widget.setLayout(equipment_editor_title_layout)

        # Equipment Editor

        editor_equipment_id_layout = QVBoxLayout()

        self.equipment_ids = []

        self.editor_equipment_id_label = QLabel("Equipment ID")
        self.editor_equipment_id_input = QLineEdit(self)
        self.editor_equipment_id_input.textChanged.connect(self.edit_equipment)

        editor_equipment_id_layout.addWidget(self.editor_equipment_id_label)
        editor_equipment_id_layout.addWidget(self.editor_equipment_id_input)

        equipment_id_widget = QWidget()
        equipment_id_widget.setFixedWidth(220)

        equipment_id_widget.setLayout(editor_equipment_id_layout)

        # Editable Table
        table_layout = QVBoxLayout()

        self.equipment_editor_table = QTableWidget()

        table_layout.addWidget(self.equipment_editor_table)

        table_widget = QWidget()

        table_widget.setLayout(table_layout)

        self.equipment_editor_table.cellChanged.connect(self.equipment_editor_cell_changed_handler)

        update_button_layout = QVBoxLayout()

        self.update_equipment_button = QPushButton("Update Equipment", self)
        self.update_equipment_button.clicked.connect(self.update_equipment)
        self.update_equipment_button.setFixedWidth(220)

        update_button_widget = QWidget()
        update_button_layout.addWidget(self.update_equipment_button)

        update_button_widget.setLayout(update_button_layout)

        # Add everything to page
        content_layout.addWidget(equipment_login_title_widget, 0, 0, 1, 3 )
        content_layout.addWidget(forms_widget, 1, 0, 1, 3)
        content_layout.addWidget(separator, 2, 0, 1, 3)
        content_layout.addWidget(equipment_editor_title_widget, 3, 0, 1, 3)
        content_layout.addWidget(equipment_id_widget, 4, 0, 1, 1)
        content_layout.addWidget(table_widget, 5, 0, 1, 3)
        content_layout.addWidget(update_button_widget, 6, 0, 1, 1)

        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0,0,0,0)

        self.equipment_forms = {
            "Pipette": self.init_pipette_form,
            "Top-Loading Balance": self.init_balance_form,
            "Analytical Balance": self.init_balance_form,
            "Hot Block": self.init_hotblock_form,
            "Mass Weight Set": self.init_mass_weight_set_form,
            "Thermometer": self.init_thermometer_form,
            "Oven": self.init_oven_form,
            "Meter": self.init_meter_form,
            "Refrigerator": self.init_refrigerator_form,
            "Water Purification System": self.init_water_purification_system_form,
        }

        self.fetch_all_equipment()

        # Completers
        
        brand_completer = QCompleter(self.brands, self)
        brand_completer.setCaseSensitivity(False)
        self.brand_input.setCompleter(brand_completer)

        ownership_completer = QCompleter(self.owners, self)
        ownership_completer.setCaseSensitivity(False)
        self.ownership_input.setCompleter(ownership_completer)

        location_completer = QCompleter(self.locations, self)
        location_completer.setCaseSensitivity(False)
        self.location_input.setCompleter(location_completer)

        equipment_id_completer = QCompleter(self.equipment_ids, self)
        equipment_id_completer.setCaseSensitivity(False)
        self.editor_equipment_id_input.setCompleter(equipment_id_completer)

        page.setLayout(content_layout)

    def update_equipment(self):
        self.init_session()
        try:
            for index, row in self.equipment_df.iterrows():
                # Retrieve the existing record
                equipment = self.session.query(EquipmentManagement).filter_by(EquipmentID=row['EquipmentID']).first()
                if equipment:
                    # Update the fields
                    for column in self.equipment_df.columns:
                        value = row[column]
                        # Handle None values and type conversion
                        if pd.isna(value) or value == 'None' or value is None or value == 'nan':
                            if column in ['MinVolume', 'MaxVolume', 'AssignedMass', 'MinTemp', 'MaxTemp', 'Hysteresis']:
                                value = 0  # Change None to 0 for specified numeric columns
                            else:
                                value = None
                        elif column in ['MinVolume', 'MaxVolume', 'AssignedMass', 'MinTemp', 'MaxTemp', 'Hysteresis']:
                            value = int(value)
                        elif column in ['Date', 'Time']:
                            # Convert date and time to appropriate format if needed
                            value = pd.to_datetime(value) if value is not None else None
                        setattr(equipment, column, value)

                    try:
                        current_datetime = datetime.now()

                        log_entry = LIMSActivity(
                            User=settings.value("username"),
                            TablesAffected="EquipmentManagement",
                            Action=f"{settings.value("username")} updated a {self.add_equipment_combobox.currentText()}, ({self.equipment_id_input.text()})",
                            Notes=self.comments_textbox.toPlainText(),
                            Date=current_datetime.date(),
                            Time=current_datetime.time()
                        )
                        self.session.add(log_entry)
                        self.session.commit()

                    except SQLAlchemyError as log_error:
                        QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                        self.session.rollback()
                    
                    # Add the updated record to the session
                    self.session.add(equipment)
            
            # Commit the session
            self.session.commit()
            QMessageBox.information(self, "Success", f"Successfully updated equipment!")
        except SQLAlchemyError as e:
            # Handle any SQLAlchemy errors
            print("SQLAlchemy Error:", e)
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update equipment: {str(e)}")
            # Return None or handle the error as needed
            return None
        finally:
            # Close the session
            self.session.close()

    def edit_equipment(self):
        # Initialize session
        self.init_session()
        
        # Get the EquipmentID from the editor_equipment_id_input
        equipment_id = self.editor_equipment_id_input.text()
        
        try:
            if equipment_id.strip() == "":
                # If the EquipmentID input is blank, fetch all equipment
                self.fetch_all_equipment()
                self.populate_equipment_table()
            else:
                # Query the EquipmentManagement table based on the EquipmentID
                equipment = self.session.query(EquipmentManagement).filter_by(EquipmentID=equipment_id).first()
                
                # Check if equipment is found
                if equipment:
                    # If found, return the equipment
                    # Convert the equipment object to a dictionary
                    equipment_dict = equipment.__dict__
                    
                    # Remove the '_sa_instance_state' key
                    equipment_dict.pop('_sa_instance_state', None)
                    
                    # Convert the dictionary to a DataFrame
                    self.equipment_df = pd.DataFrame([equipment_dict])

                    self.populate_equipment_table()

                    self.session.close()
                    
                    # Print the DataFrame (optional)
                    print(self.equipment_df)
                    
                    return self.equipment_df
                else:
                    # If not found, return None or handle the case as needed
                    return None
        except SQLAlchemyError as e:
            # Handle any SQLAlchemy errors
            print("SQLAlchemy Error:", e)
            # Return None or handle the error as needed
            return None
        
    def fetch_all_equipment(self):
        self.init_session()

        try:
            # Query to get all equipment records
            equipment_records = self.session.query(EquipmentManagement).all()
            
            # Convert the records to a list of dictionaries
            equipment_list = [record.__dict__ for record in equipment_records]
            
            # Remove the '_sa_instance_state' key from each dictionary
            for equipment in equipment_list:
                equipment.pop('_sa_instance_state', None)
            
            # Convert the list of dictionaries to a DataFrame
            self.equipment_df = pd.DataFrame(equipment_list)

            print(self.equipment_df)

            self.populate_equipment_table()

            if equipment_records:
                # Populate all completer fields
                self.brands = self.equipment_df['Brand'].tolist()
                self.owners = self.equipment_df['Ownership'].tolist()
                self.locations = self.equipment_df['Location'].tolist()
                self.equipment_ids = self.equipment_df['EquipmentID'].tolist()
            
            return self.equipment_df
        except SQLAlchemyError as e:
            print("SQLAlchemy Error:", e)
            self.session.rollback()
            self.session.close()
            return None
    
    def populate_equipment_table(self):
        if self.equipment_df is not None and not self.equipment_df.empty:
            # Clear the table before populating it
            self.equipment_editor_table.clearContents()
            
            # Set the column count
            self.equipment_editor_table.setColumnCount(len(self.equipment_df.columns))
            
            # Set the row count
            self.equipment_editor_table.setRowCount(len(self.equipment_df.index))

            # Define the column order based on the EquipmentManagement class
            column_order = [
                'EquipmentID', 'Type', 'MinVolume', 'MaxVolume', 'AssignedMass',
                'MinTemp', 'MaxTemp', 'Hysteresis', 'Date', 'Time', 
                'SerialNumber', 'Model', 'Brand', 'Ownership', 
                'Location', 'TagNumber', 'Status', 'Notes'
            ]
            
            # Reindex the DataFrame to have the specified column order
            self.equipment_df = self.equipment_df.reindex(columns=column_order)
            
            # Set the horizontal header labels
            self.equipment_editor_table.setHorizontalHeaderLabels(self.equipment_df.columns)

            # Populate the table with data
            for i in range(len(self.equipment_df.index)):
                for j in range(len(self.equipment_df.columns)):
                    self.equipment_editor_table.setItem(i, j, QTableWidgetItem(str(self.equipment_df.iloc[i, j])))

            # Adjust column widths to fit contents
            self.equipment_editor_table.resizeColumnsToContents()

            # Optional: Add a slight delay to ensure the UI is fully rendered
            QTimer.singleShot(100, self.equipment_editor_table.resizeColumnsToContents)

            # Set resize mode for columns
            header = self.equipment_editor_table.horizontalHeader()
            for column in range(header.count()):
                header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

    def equipment_editor_cell_changed_handler(self, row, column):
        new_value = self.equipment_editor_table.item(row, column).text()
        self.equipment_df.iloc[row, column] = new_value
        return
    
    def log_equipment(self):
        self.init_session()

        try:
            new_equipment = EquipmentManagement(
                EquipmentID=self.equipment_id_input.text(),
                Type = self.add_equipment_combobox.currentText(),
                MinVolume=int(getattr(self, 'min_volume_input', None).text()) if getattr(self, 'min_volume_input', None) else None,
                MaxVolume=int(getattr(self, 'max_volume_input', None).text()) if getattr(self, 'max_volume_input', None) else None,
                AssignedMass=int(getattr(self, 'assigned_mass_input', None).text()) if getattr(self, 'assigned_mass_input', None) else None,
                MinTemp=int(getattr(self, 'min_temp_input', None).text()) if getattr(self, 'min_temp_input', None) else None,
                MaxTemp=int(getattr(self, 'max_temp_input', None).text()) if getattr(self, 'max_temp_input', None) else None,
                Hysteresis=int(getattr(self, 'hysteresis_input', None).text()) if getattr(self, 'hysteresis_input', None) else None,
                Date=self.add_equipment_date_input.text(),
                Time=self.add_equipment_time_input.text(),
                SerialNumber=self.serial_number_input.text(),
                Model=self.model_input.text(),
                Brand=self.brand_input.text(),
                Ownership=self.ownership_input.text(),
                Location=self.location_input.text(),
                TagNumber=self.tag_number_input.text(),
                Status="Active",
                Notes=self.comments_textbox.toPlainText()
            )

            self.session.add(new_equipment)

            # Log activity
            try:
                current_datetime = datetime.now()

                log_entry = LIMSActivity(
                    User=settings.value("username"),
                    TablesAffected="EquipmentManagement",
                    Action=f"{settings.value("username")} added a new {self.add_equipment_combobox.currentText()} ({self.equipment_id_input.text()})",
                    Notes=self.comments_textbox.toPlainText(),
                    Date=current_datetime.date(),
                    Time=current_datetime.time()
                )
                self.session.add(log_entry)
                self.session.commit()
                self.fetch_all_equipment()
            except SQLAlchemyError as log_error:
                QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                self.session.rollback()

            # Show success message
            QMessageBox.information(self, 'Success', 'Equipment added successfully!')

        except Exception as e:
            # Show error message
            QMessageBox.critical(self, 'Error', f'Failed to add equipment: {str(e)}')

        finally:
            self.session.close()
        
    def init_stacked_equipment_widget(self):
        # Clear the existing widget if any
        current_widget = self.stacked_equipment_widget.currentWidget()
        if current_widget:
            self.stacked_equipment_widget.removeWidget(current_widget)

        equipment_type = self.add_equipment_combobox.currentText()

        if equipment_type in self.equipment_forms:
            self.equipment_forms[equipment_type]()
        else:
            self.stacked_equipment_widget.setCurrentIndex(-1)

    def init_meter_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Meter ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_pipette_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Pipette ID")
        self.equipment_id_input = QLineEdit(self)
        self.min_volume_label = QLabel("Minimum Volume")
        self.min_volume_input = QLineEdit(self)
        self.max_volume_label = QLabel("Maximum Volume")
        self.max_volume_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)
        self.min_volume_label.setFixedWidth(200)
        self.min_volume_input.setFixedWidth(200)
        self.max_volume_label.setFixedWidth(200)
        self.max_volume_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)
        self.equipment_login_layout.addWidget(self.min_volume_label)
        self.equipment_login_layout.addWidget(self.min_volume_input)
        self.equipment_login_layout.addWidget(self.max_volume_label)
        self.equipment_login_layout.addWidget(self.max_volume_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_balance_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Balance ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_hotblock_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Hot Block ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_mass_weight_set_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Weight ID")
        self.equipment_id_input = QLineEdit(self)
        self.assigned_mass_label = QLabel("Assigned Mass (stone)")
        self.assigned_mass_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)
        self.assigned_mass_label.setFixedWidth(200)
        self.assigned_mass_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)
        self.equipment_login_layout.addWidget(self.assigned_mass_label)
        self.equipment_login_layout.addWidget(self.assigned_mass_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_thermometer_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Thermometer ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_oven_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Oven ID")
        self.equipment_id_input = QLineEdit(self)
        self.min_temp_label = QLabel("Minimum Oven Temp (\u2103)")
        self.min_temp_input = QLineEdit(self)
        self.max_temp_label = QLabel("Maximum Oven Temp (\u2103)")
        self.max_temp_input = QLineEdit(self)
        self.hysteresis_label = QLabel("Oven Hysteresis (\u00B1 \u2103)")
        self.hysteresis_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)
        self.min_temp_label.setFixedWidth(200)
        self.min_temp_input.setFixedWidth(200)
        self.max_temp_label.setFixedWidth(200)
        self.max_temp_input.setFixedWidth(200)
        self.hysteresis_label.setFixedWidth(200)
        self.hysteresis_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)
        self.equipment_login_layout.addWidget(self.min_temp_label)
        self.equipment_login_layout.addWidget(self.min_temp_input)
        self.equipment_login_layout.addWidget(self.max_temp_label)
        self.equipment_login_layout.addWidget(self.max_temp_input)
        self.equipment_login_layout.addWidget(self.hysteresis_label)
        self.equipment_login_layout.addWidget(self.hysteresis_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_refrigerator_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Refrigerator ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

    def init_water_purification_system_form(self):
        self.equipment_login_layout = QVBoxLayout()

        self.equipment_id_label = QLabel("Water Purification System ID")
        self.equipment_id_input = QLineEdit(self)

        self.equipment_id_label.setFixedWidth(200)
        self.equipment_id_input.setFixedWidth(200)

        self.equipment_login_layout.addWidget(self.equipment_id_label)
        self.equipment_login_layout.addWidget(self.equipment_id_input)

        self.equipment_login_layout.setAlignment(Qt.AlignTop)
        self.equipment_login_layout.setContentsMargins(0, 0, 0, 0)

        self.equipment_login_widget = QWidget()
        self.equipment_login_widget.setLayout(self.equipment_login_layout)

        self.stacked_equipment_widget.addWidget(self.equipment_login_widget)
        self.stacked_equipment_widget.setCurrentWidget(self.equipment_login_widget)

# ███████  █████  ███    ███ ██████  ██      ███████     ██       ██████   ██████  ██ ███    ██ 
# ██      ██   ██ ████  ████ ██   ██ ██      ██          ██      ██    ██ ██       ██ ████   ██ 
# ███████ ███████ ██ ████ ██ ██████  ██      █████       ██      ██    ██ ██   ███ ██ ██ ██  ██ 
#      ██ ██   ██ ██  ██  ██ ██      ██      ██          ██      ██    ██ ██    ██ ██ ██  ██ ██ 
# ███████ ██   ██ ██      ██ ██      ███████ ███████     ███████  ██████   ██████  ██ ██   ████ 

    def init_sample_login_page(self, page):
        content_layout = QGridLayout()

        # Left side form layout
        form_layout = QVBoxLayout()

        sample_login_title_layout = QHBoxLayout()
        sample_login_title_layout.setAlignment(Qt.AlignHCenter)

        self.sample_login_title = QLabel("Sample Login")
        self.sample_login_title.setFont(self.header_font)

        sample_login_title_layout.addWidget(self.sample_login_title)

        sample_login_title_widget = QWidget()
        sample_login_title_widget.setLayout(sample_login_title_layout)

        self.sample_type_label = QLabel("Survey Type:")
        self.sample_type_combobox = QComboBox()
        self.sample_type_combobox.setFixedWidth(200)
        self.get_coc_folders()

        self.coc_label = QLabel("CoC File Name:")
        self.coc_label.setFixedWidth(200)

        self.coc_input = QLineEdit()
        self.coc_input.setFixedWidth(200)

        self.or_label = QLabel("--or--")

        self.coc_search_button = QPushButton("Search for CoC", self)
        self.coc_search_button.clicked.connect(self.search_for_coc)
        self.coc_search_button.setFixedWidth(200)

        self.date_received_label = QLabel("Date Received")
        self.date_received_input = QDateEdit(self)
        self.date_received_input.setCalendarPopup(True)
        self.date_received_input.setDate(QDate.currentDate())
        self.date_received_input.setDisplayFormat("MM-dd-yyyy")
        self.date_received_input.setFixedWidth(200)
        self.date_received_label.setFixedWidth(200)

        self.time_received_label = QLabel("Time Received")
        self.time_received_input = QTimeEdit(self)
        self.time_received_input.setTime(QTime.currentTime())
        self.time_received_input.setDisplayFormat("HH:mm")
        self.time_received_label.setFixedWidth(200)
        self.time_received_input.setFixedWidth(200)

        self.received_by_label = QLabel("Received By")
        self.received_by_label.setFixedWidth(200)

        self.received_by_combobox = QComboBox()
        self.received_by_combobox.setFixedWidth(200)
        self.populate_received_by_combobox()

        self.sdg_label = QLabel("SDG Number:")
        self.sdg_label.setFixedWidth(200)

        self.sdg_input = QLineEdit()
        self.sdg_input.setFixedWidth(200)

        # Radio buttons for SDG option
        self.generate_sdg_radio = QRadioButton("Generate SDG")
        self.type_sdg_radio = QRadioButton("Type SDG")
        self.generate_sdg_radio.setChecked(True)  # Default to generate SDG

        # Connect radio buttons to the toggle method
        self.generate_sdg_radio.toggled.connect(self.toggle_sdg_input)
        self.type_sdg_radio.toggled.connect(self.toggle_sdg_input)

        self.sdg_option_layout = QHBoxLayout()
        self.sdg_option_layout.addWidget(self.generate_sdg_radio)
        self.sdg_option_layout.addWidget(self.type_sdg_radio)

        self.log_samples_button = QPushButton("Log CoC and Samples", self)
        self.log_samples_button.clicked.connect(self.log_samples)
        self.log_samples_button.setFixedWidth(200)

        # Create a QHBoxLayout for the or_label
        or_layout = QHBoxLayout()
        or_layout.addWidget(self.or_label)
        or_layout.setAlignment(Qt.AlignHCenter)

        form_layout.addWidget(sample_login_title_widget)
        form_layout.addStretch()
        form_layout.addWidget(self.sample_type_label)
        form_layout.addWidget(self.sample_type_combobox)
        form_layout.addWidget(self.coc_label)
        form_layout.addWidget(self.coc_input)
        form_layout.addLayout(or_layout)
        form_layout.addWidget(self.coc_search_button)
        form_layout.addStretch()
        form_layout.addWidget(self.date_received_label)
        form_layout.addWidget(self.date_received_input)
        form_layout.addWidget(self.time_received_label)
        form_layout.addWidget(self.time_received_input)
        form_layout.addWidget(self.received_by_label)
        form_layout.addWidget(self.received_by_combobox)
        form_layout.addStretch()
        form_layout.addWidget(self.sdg_label)
        form_layout.addWidget(self.sdg_input)
        form_layout.addLayout(self.sdg_option_layout)
        form_layout.addWidget(self.log_samples_button)
        form_layout.addStretch()
        form_layout.addStretch()

        form_layout.setAlignment(Qt.AlignCenter)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setMaximumWidth(220)

        # Separator between the left and right sections
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)

        # Editor Title
        sample_editor_title_layout = QHBoxLayout()
        sample_editor_title_layout.setAlignment(Qt.AlignHCenter)

        self.sample_editor_title = QLabel("Sample Editor")
        self.sample_editor_title.setFont(self.header_font)

        sample_editor_title_layout.addWidget(self.sample_editor_title)

        sample_editor_title_widget = QWidget()
        sample_editor_title_widget.setLayout(sample_editor_title_layout)

        editor_layout = QGridLayout()

        # Editable table
        table_layout = QVBoxLayout()

        self.table = QTableWidget()

        table_layout.addWidget(self.table)

        table_widget = QWidget()

        table_widget.setLayout(table_layout)

        self.table.cellChanged.connect(self.cell_changed_handler)

        # Editor Form Layout
        editor_form_layout = QGridLayout()

        # SQG and Checkbox Layout
        sdg_and_checkbox_layout = QVBoxLayout()

        self.editor_sdg_label = QLabel("SDG Number:")
        self.editor_sdg_input = QLineEdit()
        self.editor_sdg_input.textChanged.connect(self.on_text_changed)

        self.editor_sdg_label.setFixedWidth(200)
        self.editor_sdg_input.setFixedWidth(200)

        self.upload_dqo = QCheckBox()
        self.upload_dqo_label = QLabel("Upload DQO")
        self.upload_dqo.setChecked(True)

        dqo_checkbox_layout = QHBoxLayout()

        dqo_checkbox_layout.setAlignment(Qt.AlignLeft)

        dqo_widget = QWidget()

        dqo_widget.setLayout(dqo_checkbox_layout)
        dqo_widget.setFixedWidth(200)

        dqo_checkbox_layout.addWidget(self.upload_dqo)
        dqo_checkbox_layout.addWidget(self.upload_dqo_label)

        sdg_and_checkbox_layout.addWidget(self.editor_sdg_label)
        sdg_and_checkbox_layout.addWidget(self.editor_sdg_input)
        sdg_and_checkbox_layout.addWidget(dqo_widget)

        sdg_and_checkbox_layout.setSpacing(0)

        sdg_and_checkbox_widget = QWidget()

        sdg_and_checkbox_widget.setLayout(sdg_and_checkbox_layout)

        # Notes Layout
        notes_layout = QVBoxLayout()

        self.notes_label = QLabel("Additional Notes")
        self.notes_input = QTextEdit()

        notes_layout.addWidget(self.notes_label)
        notes_layout.addWidget(self.notes_input)

        notes_widget = QWidget()
        notes_widget.setLayout(notes_layout)
        notes_widget.setFixedWidth(400)

        # Submit Button
        self.submit_button = QPushButton("Submit", self)
        self.submit_button.clicked.connect(self.submit_data)
        self.submit_button.setFixedSize(100,100)

        submit_button_layout = QVBoxLayout()

        submit_button_layout.addWidget(self.submit_button)

        submit_button_widget = QWidget()
        submit_button_widget.setLayout(submit_button_layout)

        # Editor Form Layout
        editor_form_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 0)
        editor_form_layout.addWidget(sdg_and_checkbox_widget, 0, 1)
        editor_form_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2)
        editor_form_layout.addWidget(notes_widget, 0, 3)
        editor_form_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 4)
        editor_form_layout.addWidget(submit_button_widget, 0, 5)
        editor_form_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 6)

        editor_form_layout.setAlignment(Qt.AlignBottom)
        editor_form_layout.setContentsMargins(0,0,0,0)

        editor_form_widget = QWidget()
        editor_form_widget.setLayout(editor_form_layout)
        editor_form_widget.setFixedHeight(175)

        # Separator between the top and bottom editor sections
        editor_separator = QFrame()
        editor_separator.setFrameShape(QFrame.HLine)
        editor_separator.setFrameShadow(QFrame.Sunken)

        editor_layout.addWidget(sample_editor_title_widget, 0, 0)
        editor_layout.addWidget(table_widget, 1, 0)
        editor_layout.addWidget(editor_separator, 2, 0)
        editor_layout.addWidget(editor_form_widget, 3, 0)

        # Editor 
        editor_widget = QWidget()

        editor_widget.setLayout(editor_layout)

        content_layout.addWidget(form_widget, 0, 0)
        content_layout.addWidget(separator, 0, 1)
        content_layout.addWidget(editor_widget, 0, 2)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0,0,0,0)

        page.setLayout(content_layout)

        # Call the toggle method once to set the initial state
        self.toggle_sdg_input()
        self.initial_sample_login_table()

    def initial_sample_login_table(self):
        self.init_session()

        try:
            samples = self.session.query(SampleLogin).all()

            if samples:
                sample_dicts = [sample.__dict__ for sample in samples]

                for sample_dict in sample_dicts:
                    sample_dict.pop('_sa_instance_state', None)

                self.sample_login_df = pd.DataFrame(sample_dicts)

                boolean_columns = lab_lists.sample_login_bool_cols
            
                for column in boolean_columns:
                    self.sample_login_df[column] = self.sample_login_df[column].apply(lambda x: 1 if x is True else 0)

                self.populate_table()
            else:
                self.sample_login_df = pd.DataFrame()
            
            self.session.close()

        except SQLAlchemyError as e:
            print("SQLAlchemy Error: ", e)

    def populate_received_by_combobox(self):
        self.init_session()

        query = self.session.query(User.UserName)

        self.users = [user[0] for user in query.distinct().all()]

        self.received_by_combobox.addItems(self.users)

        self.session.close()

        cached_username = settings.value("username")

        if cached_username in self.users:
            index = self.received_by_combobox.findText(cached_username)
            if index != -1:
                self.received_by_combobox.setCurrentIndex(index)

    def cell_changed_handler(self, row, column):
        new_value = self.table.item(row, column).text()
        self.sample_login_df.iloc[row, column] = new_value

    def populate_table(self):
        if self.sample_login_df is not None and not self.sample_login_df.empty:
            # Extract and convert the numeric part after 'S' in SampleID to integers
            print(self.sample_login_df)

            column_order = [
                "SDG",
                "SampleID",
                "Matrix",
                "HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCSR",
                "LSCAB",
                "MET",
                "TCLP",
                "BEF",
                "SIO2",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP",
                "LocationID",
                "SampleVolume",
                "Count",
                "CPM",
                "SampleDate",
                "SampleTime",
                "DateReceived",
                "TimeReceived",
                "ReceivedBy",
                "DQO"
            ]
            
            self.sample_login_df = self.sample_login_df.reindex(columns=column_order)

            # Initialize table
            self.table.setColumnCount(len(self.sample_login_df.columns))
            self.table.setRowCount(len(self.sample_login_df.index))
            self.table.setHorizontalHeaderLabels(self.sample_login_df.columns)
            
            # Populate table
            for i in range(len(self.sample_login_df.index)):
                for j in range(len(self.sample_login_df.columns)):
                    self.table.setItem(i, j, QTableWidgetItem(str(self.sample_login_df.iloc[i, j])))

            self.table.resizeColumnsToContents()
            # Optional: Add a slight delay to ensure the UI is fully rendered
            QTimer.singleShot(100, self.table.resizeColumnsToContents)

    def on_text_changed(self):
        sdg_text = self.editor_sdg_input.text()

        if sdg_text == "":
            self.initial_sample_login_table()

        if self.valid_sdg(sdg_text):
            # Assuming self.session is already initialized
            if not hasattr(self, 'session'):
                self.init_session()

            # Construct the query to filter based on multiple SDGs, group by SDG, and order by SampleID
            query = (self.session.query(SampleLogin)
                                .filter(SampleLogin.SDG == sdg_text)
                                .order_by(SampleLogin.SampleID))

            # Execute the query and fetch all results
            result = query.all()

            # Convert each object to a dictionary
            result_dict = [row.__dict__ for row in result]

            # Remove the '_sa_instance_state' key from each dictionary
            for row in result_dict:
                row.pop('_sa_instance_state', None)

            self.sample_login_df = pd.DataFrame(result_dict)
            self.sample_login_df = self.sample_login_df.reindex(columns=[
                "SDG",
                "SampleID",
                "Matrix",
                "HG",
                "ISOAM",
                "ISOTH",
                "ISOU",
                "ISOPU",
                "GAMMA",
                "GFPC",
                "LSCPU",
                "LSCSR",
                "LSCAB",
                "MET",
                "TCLP",
                "BEF",
                "SIO2",
                'FLUOR',
                "NH3",
                "NO3",
                "NO2",
                "CRVI",
                "CL",
                "PH",
                "TSS",
                "TSP",
                "LocationID",
                "SampleVolume",
                "Count",
                "CPM",
                "SampleDate",
                "SampleTime",
                "DateReceived",
                "TimeReceived",
                "ReceivedBy",
                "DQO"
            ])
            
            boolean_columns = lab_lists.sample_login_bool_cols
            
            for column in boolean_columns:
                self.sample_login_df[column] = self.sample_login_df[column].apply(lambda x: 1 if x is True else 0)

            # Remember to close the session after use
            self.session.close()
            
            self.populate_table()
        else:
            self.sample_login_df = pd.DataFrame()
            return self.sample_login_df
    
    def valid_sdg(self, text):
        pattern = lims.config.patterns.sdg_pattern
        return re.match(pattern, text) is not None

    def submit_data(self):
        self.init_session()
        # List of boolean column names
        boolean_columns = lab_lists.sample_login_bool_cols

        # Convert '0' to False and '1' to True in boolean columns
        self.sample_login_df[boolean_columns] = self.sample_login_df[boolean_columns].applymap(lambda x: False if x == 0 or x == '0' else True)

        # Perform the update operation for each row in the DataFrame
        for index, row in self.sample_login_df.iterrows():
            # Extract SDG from the current row
            sdg = row['SDG']
            sample_id = row['SampleID']

            # Update the corresponding record in the database for this SDG
            self.update_sample_login(sdg, sample_id, row)

        self.session.close()

        if self.upload_dqo.isChecked():
            self.upload_dqo_method(self.sample_login_df)
            print("Self.sample_login_df", self.sample_login_df)
        else:
            pass

        return
    
    def update_sample_login(self, sdg, sample_id, row):
        try:
            # Assuming 'session' is an active SQLAlchemy session
            record = self.session.query(SampleLogin).filter(SampleLogin.SDG == sdg, SampleLogin.SampleID == sample_id).first()
            
            # Update the record with values from the DataFrame row
            for column in self.sample_login_df.columns:
                if column != 'SDG' or column != 'SampleID':  # Exclude SDG and SampleID column
                    setattr(record, column, row[column])

            # Commit the changes to the database
            self.session.commit()
        except Exception as e:
            # Handle any errors that occur during the update process
            print(f"Error updating record for SDG, SampleID {sdg, sample_id}: {e}")
            self.session.rollback()
    
    def upload_dqo_method(self, df):
        print("DQO UPLOAD DF", df)
        dqo_table = []

        df = df[df['DQO'] == 1]

        print("This is the dataframe for columns", df.head(5))
        
        for index, row in df.iterrows():
            sdg = row['SDG']
            sample_id = row['SampleID']
            matrix = row['Matrix']
            for method in df.columns[3:25]:
                if row[method]:
                    dqo_table.append({'Method': method, 'SDG': sdg, 'SampleID': sample_id, 'Matrix': matrix})

        dqo_df = pd.DataFrame(dqo_table)

        try:
            self.init_session()
            
            # Add data from clerical_data_df to DQO table
            for _, row in dqo_df.iterrows():
                record = DQO(**row.to_dict())  # Create an ORM object from the row
                self.session.merge(record)  
            
            # Log the activity
            try:
                current_datetime = datetime.now()

                log_entry = LIMSActivity(
                    User=settings.value("username"),
                    TablesAffected="DQO",
                    Action=f"{settings.value('username')} uploaded a DQO for ({sdg})",
                    Notes=self.notes_input.toPlainText(),
                    Date=current_datetime.date(),
                    Time=current_datetime.time()
                )
                self.session.add(log_entry)
                self.session.commit()

                # Show success message
                QMessageBox.information(self, "Success", "DQO uploaded and logged successfully.")

            except SQLAlchemyError as log_error:
                QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                self.session.rollback()

        except Exception as e:
            # Rollback the transaction if an error occurs
            self.session.rollback()
            print("An error occurred while adding data:", e)

            # Show error message
            QMessageBox.critical(self, "Error", f"An error occurred while adding data: {str(e)}")

        finally:
            # Close the session
            self.session.close()

    def toggle_sdg_input(self):
        if self.generate_sdg_radio.isChecked():
            self.sdg_input.setDisabled(True)
        else:
            self.sdg_input.setDisabled(False)

    def get_coc_folders(self):
        try:
            folders = ["Select a Survey Type"]
            for entry in os.listdir(file_paths.coc_directory):
                full_path = os.path.join(file_paths.coc_directory, entry)
                if os.path.isdir(full_path):
                    folders.append(entry)

            self.sample_type_combobox.addItems(folders)
            logging.info("Loaded CoC folders: %s", folders)

        except Exception as e:
            logging.exception("Failed to load CoC folders.")
            QMessageBox.critical(self, "Error", f"Failed to load folders: {str(e)}")

    def search_for_coc(self):
        try:
            sample_type = self.sample_type_combobox.currentText()

            if sample_type == "Select a Survey Type":
                QMessageBox.warning(self, "Warning", "Please select a survey type!")
                return

            directory = os.path.join(file_paths.coc_directory, sample_type)
            self.coc_file_path, _ = QFileDialog.getOpenFileName(self, "Select CoC File", directory)

            if self.coc_file_path:
                self.base_name = os.path.splitext(os.path.basename(self.coc_file_path))[0]
                self.coc_input.setText(self.base_name)

            directory = os.path.dirname(self.coc_file_path)
            coc_file_sample_type = os.path.basename(directory)
            logging.info(f"Selected CoC file: {self.coc_file_path}, Survey Type: {coc_file_sample_type}")

            combobox_index = self.sample_type_combobox.findText(coc_file_sample_type)

            if sample_type != combobox_index and combobox_index != -1:
                self.sample_type_combobox.setCurrentIndex(combobox_index)

        except Exception as e:
            logging.exception("Error in search_for_coc")
            QMessageBox.critical(self, "Error", f"Error selecting CoC: {str(e)}")

    def log_samples(self):
        self.init_session()
        logging.debug("Entering log_samples()")
        
        try:
            from openpyxl import load_workbook
            logging.debug("Successfully imported openpyxl")
        except ImportError as e:
            logging.exception("Failed to import openpyxl")
            QMessageBox.critical(self, "Import Error", "Could not import openpyxl. It may be missing from the PyInstaller build.")
            return
        
        try:
            logging.debug("Made it to the try block")
            # Capture if frozen (PyInstaller)
            is_frozen = getattr(sys, 'frozen', False)
            logging.info("App is %s", "frozen" if is_frozen else "not frozen")

            selected_sample_type = self.sample_type_combobox.currentText()
            coc_file_name = self.coc_input.text()

            logging.info("Selected survey type: %s", selected_sample_type)
            logging.info("CoC base file name: %s", coc_file_name)

            if not coc_file_name:
                QMessageBox.warning(self, "Invalid CoC", "Please select or enter a valid CoC.")
                return

            # Compose path to CoC workbook
            workbook_path = os.path.join(file_paths.coc_directory, selected_sample_type, f"{coc_file_name}.xlsm")
            logging.info("Attempting to open CoC file: %s", workbook_path)

            if not os.path.exists(workbook_path):
                logging.error("Workbook file not found: %s", workbook_path)
                QMessageBox.critical(self, "File Not Found", f"The CoC file does not exist:\n{workbook_path}")
                return

            # Try loading the Excel workbook
            wb = load_workbook(workbook_path, data_only=True)
            ws = wb.active
            logging.info("Workbook loaded successfully.")

            # Determine the SDG number based on the selected option
            if self.generate_sdg_radio.isChecked():
                sdg_number = self.generate_sdg()
            elif self.type_sdg_radio.isChecked():
                sdg_number = self.sdg_input.text()
                if not sdg_number:  # Check if sdg_number is empty or None
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText("Please enter a valid SDG number or generate one.")
                    msg.setWindowTitle("Invalid SDG Number")
                    msg.exec_()
                    return

            # Check if the SDG number already exists in the database
            existing_sdg = self.session.query(CoC).filter_by(SDG=sdg_number).first()

            if existing_sdg:
                reply = QMessageBox.question(self, 'SDG Exists', 'This SDG already exists. Would you like to replace the existing one?', QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return None  # User chose not to replace the existing SDG
                if reply == QMessageBox.Yes:
                    try:
                        # Delete existing records related to the SDG
                        self.session.query(CoC).filter_by(SDG=sdg_number).delete()
                        self.session.query(SampleLogin).filter_by(SDG=sdg_number).delete()

                        # Log the activity
                        try:
                            current_datetime = datetime.now()

                            log_entry = LIMSActivity(
                                User=settings.value("username"),
                                TablesAffected="SampleLogin, DQO",
                                Action=f"{settings.value("username")} updated an SDG ({sdg_number})",
                                Notes=self.notes_input.toPlainText(),
                                Date=current_datetime.date(),
                                Time=current_datetime.time()
                            )
                            self.session.add(log_entry)
                            self.session.commit()
                        except SQLAlchemyError as log_error:
                            QMessageBox.critical(self, "Error", f"Failed to log activity: {str(log_error)}")
                            self.session.rollback()
                            self.session.commit()

                    except SQLAlchemyError as e:
                        QMessageBox.critical(self, "Error", f"Failed to replace existing SDG: {str(e)}")
                        self.session.rollback()

            if ws.cell(row=17, column=29).value == True:
                turnaround_time = "3hr"
            elif ws.cell(row=17, column=32).value == True:
                turnaround_time = "24hr"
            elif ws.cell(row=17, column=35).value == True:
                turnaround_time = "48hr"
            elif ws.cell(row=17, column=38).value == True:
                turnaround_time = "72hr"
            elif ws.cell(row=18, column=31).value == True:
                turnaround_time = "5d"
            elif ws.cell(row=18, column=34).value == True:
                turnaround_time = "10d"
            elif ws.cell(row=18, column=37).value == True:
                turnaround_time = "21d"
            else:
                turnaround_time = None

            clerical_data = {
                "SDG": sdg_number,
                "CoCID": ws.cell(row=12, column=23).value,
                "Survey": ws.cell(row=18, column=2).value,
                "CompanyName": ws.cell(row=8, column=10).value,
                "Address":  str(ws.cell(row=9, column=10).value) + " " + str(ws.cell(row=10, column=10).value),
                "Phone": ws.cell(row=11, column=10).value,
                "EmailOne": ws.cell(row=12, column=10).value,
                "EmailTwo": ws.cell(row=13, column=10).value,
                "ClientContact": ws.cell(row=8, column=23).value,
                "PurchaseOrder": ws.cell(row=9, column=23).value,
                "Site": ws.cell(row=10, column=23).value,
                "SentTo": ws.cell(row=8, column=33).value,
                "SiteContact": ws.cell(row=9, column=33).value,
                "SiteAddress": str(ws.cell(row=10, column=33).value) + " " + str(ws.cell(row=11, column=33).value),
                "SitePhone": ws.cell(row=12, column=33).value,
                "SiteEmail": ws.cell(row=13, column=33).value,
                "AdditionalNotes": str(ws.cell(row=17, column=21).value) + " / " + str(ws.cell(row=18, column=21).value) + " / " + str(ws.cell(row=19, column=21).value),
                "TurnaroundTime": turnaround_time,
                "FilePath": workbook_path,
            }

            print("CLERICAL DATA", clerical_data)

            clerical_data_df = pd.DataFrame([clerical_data], index=[0])

            # Start reading from row 16 and iterate through specified ranges
            row_ranges = [(37, 59), (70, 119), (130, 156)]
            sample_data_list = []

            date_received = self.date_received_input.text()
            time_received = self.time_received_input.text()
            received_by = self.received_by_combobox.currentText()

            for start_row, end_row in row_ranges:
                for row_number in range(start_row, end_row + 1):

                    # Check if column 4 is None, indicating the end of the sample data
                    if ws.cell(row=row_number, column=7).value is None:
                        break

                    # Read values from data section
                    sample_data = {
                        "SDG": sdg_number,
                        "SampleID": ws.cell(row=row_number, column=7).value,
                        "Matrix": ws.cell(row=row_number, column=21).value,
                        "HG": ws.cell(row=row_number, column=25).value,
                        "ISOAM": ws.cell(row=row_number, column=26).value,
                        "ISOTH": ws.cell(row=row_number, column=27).value,
                        "ISOU": ws.cell(row=row_number, column=28).value,
                        "ISOPU": ws.cell(row=row_number, column=29).value,
                        "GAMMA": ws.cell(row=row_number, column=30).value,
                        "GFPC": ws.cell(row=row_number, column=31).value,
                        "LSCPU": ws.cell(row=row_number, column=32).value,
                        "LSCSR": ws.cell(row=row_number, column=33).value,
                        "LSCAB": ws.cell(row=row_number, column=34).value,
                        "MET": ws.cell(row=row_number, column=35).value,
                        "TCLP": ws.cell(row=row_number, column=36).value,
                        "BEF": ws.cell(row=row_number, column=37).value,
                        "SIO2": ws.cell(row=row_number, column=38).value,
                        'FLUOR': ws.cell(row=row_number, column=39).value,
                        "NH3": ws.cell(row=row_number, column=40).value,
                        "NO3": ws.cell(row=row_number, column=41).value,
                        "NO2": ws.cell(row=row_number, column=42).value,
                        "CRVI": ws.cell(row=row_number, column=43).value,
                        "CL": ws.cell(row=row_number, column=44).value,
                        "PH": ws.cell(row=row_number, column=45).value,
                        "TSS": ws.cell(row=row_number, column=46).value,
                        "TSP": ws.cell(row=row_number, column=47).value,
                        "LocationID": ws.cell(row=row_number, column=15).value,
                        "SampleVolume": ws.cell(row=row_number, column=23).value,
                        "Count": ws.cell(row=row_number, column=22).value,
                        "CPM": ws.cell(row=row_number, column=24).value,
                        "SampleDate": ws.cell(row=row_number, column=2).value,
                        "SampleTime": ws.cell(row=row_number, column=5).value,
                        "DateReceived": date_received,
                        "TimeReceived": time_received,
                        "ReceivedBy": received_by,
                        "DQO": 1
                    }

                    matrix_key_map = {
                        "SMEAR": "SM",
                        "SM": "SM",
                        "Smear": "SM",
                        "AIR FILTER": 'AF',
                        "AF": "AF",
                        "Air Filter": "AF",
                        "AQUEOUS": "AQ",
                        "AQ": "AQ",
                        "Aqueous": "AQ",
                        "SOIL": "SO",
                        "SO": "SO",
                        "Soil": "SO"
                    }

                    if sample_data: 
                        matrix = sample_data['Matrix'].upper()
                        if matrix in matrix_key_map:
                            sample_data['Matrix'] = matrix_key_map[matrix]

                    # Append the extracted data to the list
                    sample_data_list.append(sample_data)

            # Convert the list of dictionaries into a DataFrame
            sample_data_df = pd.DataFrame(sample_data_list)

            columns_to_update = [
                    "HG",
                    "ISOAM",
                    "ISOTH",
                    "ISOU",
                    "ISOPU",
                    "GAMMA",
                    "GFPC",
                    "LSCPU",
                    "LSCSR",
                    "LSCAB",
                    "MET",
                    "TCLP",
                    "BEF",
                    "SIO2",
                    'FLUOR',
                    "NH3",
                    "NO3",
                    "NO2",
                    "CRVI",
                    "CL",
                    "PH",
                    "TSS",
                    "TSP",
                    "DQO"
                ]
            
            print(sample_data_df)

            for column in columns_to_update:
                sample_data_df[column] = sample_data_df[column].apply(lambda x: 1 if x is not None else 0)

        except FileNotFoundError as fnfe:
            logging.exception("Workbook file not found")
            QMessageBox.critical(self, "File Not Found", f"The file was not found: {fnfe}")
            return

        except Exception as e:
            logging.exception("Unexpected error in log_samples")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
            return

        try:
            # Add data from clerical_data_df to CoC table
            clerical_data_df.to_sql('CoC', con=self.engine, if_exists='append', index=False)

            for index, row in sample_data_df.iterrows():
                new_row_data = {column: row[column] for column in sample_data_df.columns}
                new_record = SampleLogin(**new_row_data)
                self.session.add(new_record)

                # Commit the transaction
                self.session.commit()

            logging.info("Inserting CoC and SampleLogin records for SDG: %s", sdg_number)

        except Exception as e:
            self.session.rollback()
            logging.exception("Database error while adding sample data")
            QMessageBox.critical(self, "Database Error", f"Could not log samples: {str(e)}")
            return

        finally:
            self.session.close()
            logging.info("Session closed")

        self.editor_sdg_input.setText(sdg_number)

    def generate_sdg(self):
        try:
            # Get the latest SDG number
            latest_sdg_record = self.session.query(CoC.SDG).order_by(desc(CoC.SDG)).first()

            # Get the current year in 'yy' format
            current_year = datetime.now().strftime("%y")

            if latest_sdg_record:
                latest_sdg = latest_sdg_record[0]
                lab_code = settings.value("lab_code")
                latest_year = latest_sdg[:2]  # Grab the first two digits for the year
                latest_number = int(latest_sdg[-4:])  # Grab the last four digits for the number

                if latest_year == current_year:
                    new_number = latest_number + 1
                else:
                    new_number = 1
            else:
                lab_code = settings.value("lab_code")  # Default lab code
                new_number = 1

            new_sdg = f'{current_year}{lab_code}{new_number:04d}'
            print("NEW SDG:", new_sdg)

            # Log the activity
            try:
                current_datetime = datetime.now()

                log_entry = LIMSActivity(
                    User=settings.value("username"),
                    TablesAffected="CoC, SampleLogin",
                    Action=f"{settings.value('username')} generated ({new_sdg}))",
                    Notes="",
                    Date=current_datetime.date(),
                    Time=current_datetime.time()
                )

                self.session.add(log_entry)
                self.session.commit()

                # Show success message
                QMessageBox.information(self, "Success", "SDG generated successfully.")
            except SQLAlchemyError as log_error:
                QMessageBox.critical(self, "Error", f"Failed to generate SDG: {str(log_error)}")
                self.session.rollback()
            
            return new_sdg
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate SDG: {e}")
            return None  # Return None in case of error

    def init_banner(self):
        # Create a QHBoxLayout to hold the banner label and image label
        banner_layout = QHBoxLayout()
        banner_layout.setSpacing(0)

        # Add the banner label
        banner_label = QLabel("Main Menu")
        banner_label.setStyleSheet("background-color: #901588; color: white; padding: 5%")
        banner_label.setFixedHeight(50)

        banner_label.setFont(self.bold_font)

        # Add the image label
        image_label = QLabel()
        pixmap = QPixmap(os.path.join(file_paths.images_directory, 'leidos_logo_white.png'))
        image_label.setPixmap(pixmap)
        image_label.setMaximumSize(banner_label.sizeHint())

        # Scale the pixmap to fit within the maximum size of the image label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)

        # Align the image label to the top right and center it horizontally
        image_label.setAlignment(Qt.AlignRight | Qt.AlignHCenter)
        image_label.setStyleSheet("background-color: #901588; color: white; font-size: 24px; padding: 5%")

        # Add the banner label and image label to the banner layout
        banner_layout.addWidget(banner_label)
        banner_layout.addWidget(image_label)

        # Add the banner layout to the layout
        self.layout.addLayout(banner_layout)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create a widget to hold the layout
        self.banner_widget = QWidget()
        self.banner_widget.setLayout(self.layout)
        self.setCentralWidget(self.banner_widget)

    def init_fonts(self):
        """Load and initialize fonts from Qt Resource System."""
        print("🔍 Checking fonts in Qt Resources...")

        # Use the correct resource path
        font_id = QFontDatabase.addApplicationFont(":/AvenirNextCyr-Regular.ttf")
        bold_font_id = QFontDatabase.addApplicationFont(":/AvenirNextCyr-Bold.ttf")

        if font_id == -1 or bold_font_id == -1:
            print("⚠️ Font loading failed, using system default.")
            self.default_font = QFont("Arial", 10)
            self.bold_font = QFont("Arial", 16)
            self.header_font = QFont("Arial", 14)
            return

        font_family = QFontDatabase.applicationFontFamilies(font_id)
        bold_font_family = QFontDatabase.applicationFontFamilies(bold_font_id)

        if not font_family or not bold_font_family:
            print("⚠️ Font family not found, using default fonts.")
            self.default_font = QFont("Arial", 10)
            self.bold_font = QFont("Arial", 16)
            self.header_font = QFont("Arial", 14)
            return

        self.default_font = QFont(font_family[0], 10)
        self.bold_font = QFont(bold_font_family[0], 16)
        self.header_font = QFont(bold_font_family[0], 14)

        self.setFont(self.default_font)
        print(f"✅ Loaded Fonts: Default={self.default_font.family()}, Bold={self.bold_font.family()}")

    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 50 pixels
        top_left_point.setY(top_left_point.y() - 50)

        # Move the window to the new top-left position
        self.move(top_left_point)

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

class SelectBatchesPopup(QDialog):
    def __init__(self):
        super().__init__()
        self.batches = None
        self.selected_batch = None
        self.initUI()

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(config.CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def initUI(self):
        self.setWindowTitle("Search for Batch")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.15

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

        self.layout = QVBoxLayout()

        sdg = QLineEdit()

        self.layout.addWidget(QLabel("Search by SDG:"))
        self.layout.addWidget(sdg)

        batches = self.initial_batches()

        self.scroll_area = self.create_scroll_area(batches)
        self.layout.addWidget(self.scroll_area)

        # Add a button to confirm selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        self.layout.addWidget(confirm_button)

        self.setLayout(self.layout)

        sdg.textChanged.connect(lambda: self.sdg_textchanged(sdg))

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def sdg_textchanged(self, sdg):
        pattern = lims.config.patterns.sdg_pattern
        sdg_value = sdg.text().strip().upper()

        if len(sdg_value) == 8 and re.match(pattern, sdg_value):
            try:
                self.init_session()
                query = self.session.query(DQO.BatchID).distinct().filter(DQO.SDG == sdg_value).all()
                batches = [row[0] for row in query]  # BatchID
                print("Matching batches:", batches)

                # Replace the scroll area
                if hasattr(self, 'scroll_area'):
                    self.layout.removeWidget(self.scroll_area)
                    self.scroll_area.deleteLater()

                self.scroll_area = self.create_scroll_area(batches)
                self.layout.insertWidget(2, self.scroll_area)

            except Exception as e:
                QMessageBox.warning(self, "Error", f"An exception occurred while searching for batches via SDG: {e}")
            finally:
                if self.session:
                    self.session.close()

    def create_scroll_area(self, batches):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Create a radio button for each batch
        radio_buttons = []
        for batch_id in batches:
            radio_text = f"{batch_id}"  # Format the label
            radio_button = QRadioButton(radio_text)
            radio_button.toggled.connect(self.radioButtonToggled)
            scroll_layout.addWidget(radio_button)
            radio_buttons.append(radio_button)

        # Set the self.layout for the scroll widget and add it to the scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        return scroll_area

    def initial_batches(self):
        try:
            self.init_session()
            # Select both BatchID and SDG for sorting
            query = (
                self.session.query(DQO.BatchID, DQO.SDG)
                .order_by(DQO.SDG.desc())
                .limit(100)  # Slightly higher in case of duplicates
                .all()
            )

            # Deduplicate by BatchID in Python
            seen = set()
            batches = []
            for batch_id, _ in query:
                if batch_id not in seen:
                    seen.add(batch_id)
                    batches.append(batch_id)
                    if len(batches) == 50:
                        break

            return batches
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An exception occurred while selecting batches: {e}")
        finally:
            if self.session:
                self.session.close()

    def radioButtonToggled(self):
        radio_button = self.sender()
        if radio_button.isChecked():
            self.selected_batch = radio_button.text()

    def confirmSelection(self):
        if self.selected_batch:
            self.accept()

    def getSelectedBatch(self):
        return self.selected_batch

    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

class SDGSelectionPopup(QDialog):
    def __init__(self, sdgs):
        super().__init__()
        self.sdgs = sdgs
        self.selected_sdg = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Select SDG's")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        # Set the window flags to exclude the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.15

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area contents
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Create a button group to ensure only one radio button can be selected
        self.button_group = QButtonGroup(self)

        # Create a radio button for each SDG
        self.radio_buttons = []
        for sdg in self.sdgs:
            radio = QRadioButton(sdg)
            radio.toggled.connect(self.SDGRadioStateChanged)
            scroll_layout.addWidget(radio)
            self.radio_buttons.append(radio)

            # Add each radio button to the button group
            self.button_group.addButton(radio)

        # Set the layout for the scroll widget and add it to the scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        # Add the scroll area to the main layout
        layout.addWidget(scroll_area)

        # Add a button to confirm selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def SDGRadioStateChanged(self, state):
        radio = self.sender()
        sdg = radio.text()
        if state == 1:  # Checked state
            self.selected_sdg = sdg

    def confirmSelection(self):
        self.accept()

    def getSelectedSDGs(self):
        return self.selected_sdg
    
    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

class EquipmentSelectionPopup(QDialog):
    def __init__(self, equipment):
        super().__init__()
        self.equipment = equipment
        self.selected_equipment = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Select Equipment")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        # Set the window flags to exclude the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.15

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area contents
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Create a checkbox for each SDG
        self.checkboxes = []
        for equipment in self.equipment:
            checkbox = QCheckBox(equipment)
            checkbox.stateChanged.connect(self.checkboxStateChanged)
            scroll_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # Set the layout for the scroll widget and add it to the scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        # Add the scroll area to the main layout
        layout.addWidget(scroll_area)

        # Add a button to confirm selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def checkboxStateChanged(self, state):
        checkbox = self.sender()
        equipment = checkbox.text()
        if state == 2:  # Checked state
            self.selected_equipment.append(equipment)
        else:  # Unchecked state
            self.selected_equipment.remove(equipment)

    def confirmSelection(self):
        self.accept()

    def getSelectedEquipment(self):
        return self.selected_equipment
    
    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

class MethodSelectionPopup(QDialog):
    def __init__(self, methods):
        super().__init__()
        self.methods = methods
        self.selected_methods = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Select Method(s)")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        # Set the window flags to exclude the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.55

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area contents
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Create a checkbox for each SDG
        self.checkboxes = []
        for method in self.methods:
            checkbox = QCheckBox(method)
            checkbox.stateChanged.connect(self.checkboxStateChanged)
            scroll_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # Set the layout for the scroll widget and add it to the scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        # Add the scroll area to the main layout
        layout.addWidget(scroll_area)

        # Add a button to confirm selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        layout.addWidget(confirm_button)

        self.setLayout(layout)
    
    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def checkboxStateChanged(self, state):
        checkbox = self.sender()
        method = checkbox.text()
        if state == 2:  # Checked state
            self.selected_methods.append(method)
        else:  # Unchecked state
            self.selected_methods.remove(method)

    def confirmSelection(self):
        self.accept()

    def getSelectedMethods(self):
        return self.selected_methods
    
    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

class MatrixSelectionPopup(QDialog):
    def __init__(self, methods):
        super().__init__()
        self.methods = methods
        self.selected_methods = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Select Method(s)")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        # Set the window flags to exclude the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Calculate the width and height as a percentage of the screen resolution
        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.15

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)

        # Set geometry of window
        self.setGeometry(0, 0, self.width, self.height)

        # Set size policy for easy resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Center the window on the screen
        self.center_window()

        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area contents
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Create a checkbox for each SDG
        self.checkboxes = []
        for method in self.methods:
            checkbox = QCheckBox(method)
            checkbox.stateChanged.connect(self.checkboxStateChanged)
            scroll_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # Set the layout for the scroll widget and add it to the scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        # Add the scroll area to the main layout
        layout.addWidget(scroll_area)

        # Add a button to confirm selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        layout.addWidget(confirm_button)

        self.setLayout(layout)
    
    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def checkboxStateChanged(self, state):
        checkbox = self.sender()
        method = checkbox.text()
        if state == 2:  # Checked state
            self.selected_methods.append(method)
        else:  # Unchecked state
            self.selected_methods.remove(method)

    def confirmSelection(self):
        self.accept()

    def getSelectedMethods(self):
        return self.selected_methods
    
    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

class ReagentSelectionPopup(QDialog):
    def __init__(self, reagents):
        super().__init__()
        self.reagents = reagents
        self.selected_reagents = []
        self.checkbox_to_lot_number = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Select Reagents")
        icon_path = self.resource_path(os.path.join(file_paths.images_directory, "leidos_logo.ico"))
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        from PyQt5.QtWidgets import QDesktopWidget
        screen_geometry = QDesktopWidget().screenGeometry()
        width_percent = 0.15
        height_percent = 0.15

        self.width = int(screen_geometry.width() * width_percent)
        self.height = int(screen_geometry.height() * height_percent)
        self.setGeometry(0, 0, self.width, self.height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.center_window()

        layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        for display_text, lot_number in self.reagents.items():
            checkbox = QCheckBox(display_text)
            checkbox.stateChanged.connect(self.checkboxStateChanged)
            scroll_layout.addWidget(checkbox)
            self.checkbox_to_lot_number[checkbox] = lot_number

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirmSelection)
        layout.addWidget(confirm_button)

        self.setLayout(layout)

    def resource_path(self, relative_path):
        # This ensures it works both in dev and .exe
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def checkboxStateChanged(self, state):
        checkbox = self.sender()
        lot_number = self.checkbox_to_lot_number[checkbox]
        if state == Qt.Checked:
            if lot_number not in self.selected_reagents:
                self.selected_reagents.append(lot_number)
        else:
            if lot_number in self.selected_reagents:
                self.selected_reagents.remove(lot_number)

    def confirmSelection(self):
        self.accept()

    def getSelectedReagents(self):
        return self.selected_reagents

    def center_window(self):
        # Get the screen geometry of the primary screen
        screen_geometry = QApplication.primaryScreen().geometry()

        # Calculate the center point of the screen
        center_point = screen_geometry.center()

        # Get the geometry of the window (including the frame)
        window_geometry = self.frameGeometry()

        # Move the center of the window geometry to the screen center point
        window_geometry.moveCenter(center_point)

        # Get the top-left position
        top_left_point = window_geometry.topLeft()

        # Shift the top-left position up by 20 pixels
        top_left_point.setY(top_left_point.y() - 40)

        # Move the window to the new top-left position
        self.move(top_left_point)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_path, 'images', 'leidos_logo.ico')
    
    print(f"Taskbar icon path: {icon_path} | Exists? {os.path.exists(icon_path)}")

    app.setWindowIcon(QIcon(icon_path))  # This affects the taskbar icon

    login_window = LoginRegister()
    login_window.setWindowIcon(QIcon(icon_path))  # Optional, affects title bar

    login_window.show()

    try:
        sys.exit(app.exec_())
    except Exception as e:
        print("Exception occurred:", e)
"""
PDF Organizer – A PyQt5-based application for managing and renaming PDF invoices.

This module creates the main window and provides all the logic for:
 - Handling PDF drag and drop.
 - Managing directory navigation and file operations.
 - Extracting invoice data from PDFs.
 - Managing invoice creation, GST mappings, and regex patterns.
 - Applying UI customizations and auto-completion.

The code uses helper modules for tasks like file operations, invoice management,
directory utilities, and UI components.
"""

import sys
import os
import traceback
import logging
import datetime

# PyQt5 imports
from PyQt5.QtCore import Qt, QDir, QTimer, QSettings
from PyQt5.QtGui import QFont, QGuiApplication, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QListWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QAction,
    QStatusBar,
    QInputDialog,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QListWidgetItem,
    QCheckBox,
    QCompleter,
)

# Application-specific modules
from models import DirectoryFilterProxyModel
from workers import OrganizeWorker
from widgets import DragDropListWidget, DragDropTreeView
from dialogs import (
    DirectoryViewerDialog,
    PDFViewerDialog,
    SettingsDialog,
    RegexManagerDialog,
    GSTMappingDialog,
)
from file_operations import (
    auto_rename,
    delete_item,
    open_file,
    create_directory,
)
from invoice_manager import InvoiceManager
from directory_utils import setup_directory_model, get_selected_paths, update_tree_view
from ui_components import apply_fade_in_animation, create_context_menu, get_stylesheet
from pdf_extractor import PDFExtractor


# =============================================================================
# Global Exception Handling
# =============================================================================
def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception hook to log and show unhandled exceptions in a message box.
    """
    error_message = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )
    logging.error("Unhandled exception: %s", error_message)
    QMessageBox.critical(None, "Unhandled Exception", error_message)


# Set our custom exception hook.
sys.excepthook = exception_hook


# =============================================================================
# Main Application Window Class
# =============================================================================
class PDFOrganizer(QMainWindow):
    """
    Main window for the Drag & Drop PDF Organizer.
    It handles the UI setup, file and directory operations, PDF extraction, and invoice processing.
    """

    def __init__(self):
        """
        Initialize the main window, settings, and UI components.
        """
        super().__init__()
        self.setWindowTitle("InvoiceMaster: Smart PDF Invoice Organizer")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon(self.resource_path("icons/invoice.png")))

        # Initialize status bar for user messages.
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Load persistent settings using QSettings.
        self.qsettings = QSettings("MyCompany", "PDFOrganizer")
        self.settings = {
            "default_directory": self.qsettings.value(
                "default_directory",
                os.path.join(os.path.expanduser("~"), "PDFOrganizer"),
            ),
            "conflict_mode": self.qsettings.value("conflict_mode", "Prompt"),
            "font_size": int(self.qsettings.value("font_size", 12)),
        }

        # Ensure the default directory exists.
        create_directory(self.settings["default_directory"])
        self.main_dir = os.path.normpath(self.settings["default_directory"])
        self.current_directory = self.main_dir
        self.history = []
        self._refresh_in_progress = False

        # Initialize the invoice manager with the base directory.
        self.invoice_manager = InvoiceManager(self.settings["default_directory"])

        # Setup UI components, menus, and auto-completers.
        self.setup_ui()
        self.create_menu()
        self.apply_settings()
        self.setStyleSheet(get_stylesheet())
        self.setup_auto_completers()

    # -------------------------------------------------------------------------
    # UI Setup Methods
    # -------------------------------------------------------------------------
    def setup_ui(self):
        """
        Construct and arrange the UI elements.
        Left panel: PDF drop area, destination path, and invoice management.
        Right panel: Directory view and file operations.
        """
        central_widget = QWidget()
        central_widget.setMinimumSize(400, 300)
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)
        main_layout.setSpacing(15)

        # --------------------------
        # Left Panel – PDF and Invoice Management
        # --------------------------
        # PDF Drop Area Group
        drop_group = QGroupBox("Drop Your PDF Files Here (Click to Browse)")
        drop_layout = QVBoxLayout()
        self.pdf_list = DragDropListWidget()
        # Override mouse release event to handle both click and drag/drop
        self.pdf_list.mouseReleaseEvent = self.pdf_list_clicked
        drop_layout.addWidget(self.pdf_list)
        drop_group.setLayout(drop_layout)

        # Destination path display and navigation (Back button)
        dest_layout = QHBoxLayout()
        self.folder_label = QLabel("Destination:")
        self.folder_path_line = QLineEdit(self.current_directory)
        self.folder_path_line.setReadOnly(True)
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        dest_layout.addWidget(self.folder_label)
        dest_layout.addWidget(self.folder_path_line)
        dest_layout.addWidget(self.back_btn)

        # Invoice Management Group
        invoice_group = QGroupBox("Invoice Management")
        invoice_layout = QFormLayout(invoice_group)
        self.company_name_edit = QLineEdit()
        self.invoice_number_edit = QLineEdit()
        self.amount_edit = QLineEdit()
        # Checkbox to optionally include amount in the filename
        self.include_amount_checkbox = QCheckBox("Include Amount")
        self.include_amount_checkbox.setChecked(False)
        self.include_amount_checkbox.stateChanged.connect(self.toggle_amount_field)
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(self.amount_edit)
        amount_layout.addWidget(self.include_amount_checkbox)
        self.amount_edit.setEnabled(False)  # Initially disable amount field
        self.gst_number_edit = QLineEdit()
        invoice_layout.addRow("Company Name:", self.company_name_edit)
        invoice_layout.addRow("Invoice Number:", self.invoice_number_edit)
        invoice_layout.addRow("Amount:", amount_layout)
        invoice_layout.addRow("GST Number:", self.gst_number_edit)
        # Button to save the invoice after processing
        save_invoice_btn = QPushButton("Save Invoice")
        save_invoice_btn.clicked.connect(self.create_invoice_from_main)
        invoice_layout.addRow(save_invoice_btn)
        # Button to extract invoice data from a selected PDF
        extract_btn = QPushButton("Extract from PDF")
        extract_btn.clicked.connect(self.extract_from_selected_pdf)
        invoice_layout.addRow(extract_btn)
        # Invoice destination preview
        self.invoice_dest_label = QLabel("Invoice will be saved at:")
        self.invoice_dest_path = QLineEdit("")
        self.invoice_dest_path.setReadOnly(True)
        invoice_layout.addRow(self.invoice_dest_label, self.invoice_dest_path)
        # Update invoice destination preview as data changes
        self.company_name_edit.textChanged.connect(self.update_invoice_path_preview)
        self.invoice_number_edit.textChanged.connect(self.update_invoice_path_preview)

        # Left panel layout arrangement.
        left_layout = QVBoxLayout()
        left_layout.addWidget(drop_group)
        left_layout.addLayout(dest_layout)
        left_layout.addWidget(invoice_group)

        # --------------------------
        # Right Panel – Directory and File Operations
        # --------------------------
        right_group = QGroupBox("Directory Contents")
        right_layout = QVBoxLayout(right_group)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search files and folders...")
        self.filter_edit.textChanged.connect(self.filter_directory)

        # Setup directory model and proxy for filtering
        self.dir_model = setup_directory_model(self.current_directory)
        self.proxy_model = DirectoryFilterProxyModel(self.current_directory)
        self.proxy_model.setSourceModel(self.dir_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # Directory tree view setup with drag/drop support
        self.dir_tree = DragDropTreeView()
        self.dir_tree.setModel(self.proxy_model)
        update_tree_view(
            self.dir_tree, self.proxy_model, self.dir_model, self.current_directory
        )
        self.dir_tree.setSortingEnabled(True)
        self.dir_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dir_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.dir_tree.doubleClicked.connect(self.change_destination)
        self.dir_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        # Directory operation buttons
        btn_layout = QHBoxLayout()
        self.create_subfolder_btn = QPushButton("Create Folder")
        self.create_subfolder_btn.clicked.connect(self.create_subfolder)
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_directory)
        organize_btn = QPushButton("Organize PDFs")
        organize_btn.clicked.connect(self.organize_pdfs)
        btn_layout.addWidget(self.create_subfolder_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(organize_btn)

        # Assemble right panel layout.
        right_layout.addWidget(self.filter_edit)
        right_layout.addWidget(self.dir_tree)
        right_layout.addLayout(btn_layout)

        # Add left and right panels to the main grid layout.
        main_layout.addLayout(left_layout, 0, 0)
        main_layout.addWidget(right_group, 0, 1)

    def create_menu(self):
        """
        Create the application menu with basic options.
        """
        menubar = self.menuBar()

        # View Menu
        view_menu = menubar.addMenu("View")
        view_dir_action = QAction("View Current Directory", self)
        view_dir_action.triggered.connect(self.view_current_directory)
        view_menu.addAction(view_dir_action)

        view_pdf_action = QAction("View PDF Files in Current Directory", self)
        view_pdf_action.triggered.connect(self.view_pdf_files)
        view_menu.addAction(view_pdf_action)

        # Tools Menu (if needed)
        tools_menu = menubar.addMenu("Tools")
        regex_manager_action = QAction("Regex Pattern Manager", self)
        regex_manager_action.triggered.connect(self.open_regex_manager)
        tools_menu.addAction(regex_manager_action)

        # Settings Menu
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menubar.addAction(settings_action)

    # -------------------------------------------------------------------------
    # Context Menu and Auto-Completion Setup
    # -------------------------------------------------------------------------
    def show_tree_context_menu(self, pos):
        """
        Show a context menu for the directory tree view with options to:
         - Copy full file path.
         - Copy file name.
         - Open the file.
        """
        index = self.dir_tree.indexAt(pos)
        if not index.isValid():
            return

        # Map the proxy index to the actual file path.
        source_index = self.proxy_model.mapToSource(index)
        file_path = self.dir_model.filePath(source_index)

        # Define menu items and their callbacks.
        menu_items = [
            ("Copy Full Path", lambda: QGuiApplication.clipboard().setText(file_path)),
            (
                "Copy File Name",
                lambda: QGuiApplication.clipboard().setText(
                    os.path.basename(file_path)
                ),
            ),
            ("Open File", lambda: open_file(file_path)),
        ]

        # Create and execute the context menu.
        menu, actions = create_context_menu(menu_items, self.dir_tree)
        action = menu.exec_(self.dir_tree.viewport().mapToGlobal(pos))

        # Execute the callback associated with the selected action.
        for act, callback in actions.items():
            if action == act:
                callback()

    def setup_auto_completers(self):
        """
        Set up auto-completion for the GST and Company Name fields using saved mappings.
        """
        settings = QSettings("MyCompany", "PDFOrganizer")
        mappings = settings.value("gst_company_mappings", {}) or {}

        # Create completer for GST numbers.
        gst_completer = QCompleter(list(mappings.keys()), self)
        gst_completer.setCaseSensitivity(Qt.CaseInsensitive)
        gst_completer.setFilterMode(Qt.MatchContains)

        # Create completer for Company names by reversing the mapping.
        company_to_gst = {company: gst for gst, company in mappings.items()}
        company_completer = QCompleter(list(company_to_gst.keys()), self)
        company_completer.setCaseSensitivity(Qt.CaseInsensitive)
        company_completer.setFilterMode(Qt.MatchContains)

        # Apply completers to the respective fields.
        self.gst_number_edit.setCompleter(gst_completer)
        self.company_name_edit.setCompleter(company_completer)

        # Connect signals to auto-fill the other field when one is selected.
        gst_completer.activated.connect(self.gst_selected)
        company_completer.activated.connect(self.company_selected)

    def gst_selected(self, text):
        """
        Callback when a GST number is selected from the auto-completer.
        Fill in the corresponding company name.
        """
        settings = QSettings("MyCompany", "PDFOrganizer")
        mappings = settings.value("gst_company_mappings", {}) or {}
        if text in mappings:
            self.company_name_edit.setText(mappings[text])

    def company_selected(self, text):
        """
        Callback when a Company name is selected from the auto-completer.
        Fill in the corresponding GST number.
        """
        settings = QSettings("MyCompany", "PDFOrganizer")
        mappings = settings.value("gst_company_mappings", {}) or {}
        for gst, company in mappings.items():
            if company == text:
                self.gst_number_edit.setText(gst)
                break

    # -------------------------------------------------------------------------
    # Settings and Filtering Methods
    # -------------------------------------------------------------------------
    def apply_settings(self):
        """
        Apply persistent settings (e.g., font size, default directory) to the UI.
        Update the directory model and invoice manager base directory.
        """
        # Set global application font.
        font = QFont()
        font.setPointSize(self.settings.get("font_size", 10))
        QApplication.instance().setFont(font)

        # Reapply stylesheet to refresh the UI.
        current_style = self.styleSheet()
        self.setStyleSheet("")
        self.setStyleSheet(current_style)

        # Update main directory and ensure it exists.
        self.main_dir = os.path.normpath(
            self.settings.get("default_directory", self.main_dir)
        )
        create_directory(self.main_dir)

        # Update current directory and refresh view if necessary.
        if not self.current_directory or self.current_directory == self.main_dir:
            self.current_directory = self.main_dir
            self.folder_path_line.setText(self.current_directory)
            self.refresh_directory()

        # Update invoice manager's base directory.
        self.invoice_manager.base_directory = self.main_dir

    def filter_directory(self, text):
        """
        Filter the directory view based on user input.
        Expand all nodes if there is a search term; otherwise, collapse the view.
        """
        if text.strip():
            self.dir_tree.expandAll()
            QTimer.singleShot(50, lambda: self.apply_filter(text))
        else:
            self.dir_tree.collapseAll()
            self.proxy_model.setFilterWildcard("")
            self.proxy_model.invalidateFilter()

    def apply_filter(self, text):
        """Helper method to apply filter text to the proxy model."""
        self.proxy_model.setFilterWildcard(text)
        self.proxy_model.invalidateFilter()

    def open_settings(self):
        """
        Open the Settings dialog.
        Apply any new settings once the dialog is accepted.
        """
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.settings = dialog.get_settings()
            self.apply_settings()
            self.status_bar.showMessage("Settings updated.", 3000)

    def open_regex_manager(self):
        """
        Open the Regex Pattern Manager dialog.
        Update PDF extractor patterns if necessary.
        """
        dialog = RegexManagerDialog(self)
        dialog.exec_()

        if hasattr(self, "pdf_extractor"):
            try:
                settings = QSettings("MyCompany", "PDFOrganizer")
                if settings.contains("regex_patterns"):
                    patterns = settings.value("regex_patterns")
                    if patterns:
                        self.pdf_extractor.patterns = patterns
                        # Optionally reinitialize the extractor.
                        self.pdf_extractor = PDFExtractor()
                        self.status_bar.showMessage(
                            "Updated PDF extractor patterns", 3000
                        )
            except Exception as e:
                logging.error(f"Failed to update PDF extractor patterns: {e}")

    def open_gst_mapping(self):
        """
        Open the GST to Company Mapping dialog.
        Reload mappings for the PDF extractor and auto-completers afterward.
        """
        dialog = GSTMappingDialog(self)
        dialog.exec_()

        if hasattr(self, "pdf_extractor"):
            try:
                settings = QSettings("MyCompany", "PDFOrganizer")
                mappings = settings.value("gst_company_mappings", {}) or {}
                self.pdf_extractor.gst_company_mappings = mappings
                self.status_bar.showMessage("Updated GST to company mappings", 3000)
            except Exception as e:
                logging.error(f"Failed to update GST to company mappings: {e}")

        self.setup_auto_completers()

    # -------------------------------------------------------------------------
    # PDF and Invoice Methods
    # -------------------------------------------------------------------------
    def extract_from_selected_pdf(self):
        """
        Extract invoice data from the selected PDF.
        Populate the form fields based on the extracted information.
        """
        if self.pdf_list.count() == 0:
            QMessageBox.warning(
                self, "No PDF Selected", "Please select a PDF file first."
            )
            return

        pdf_path = self.pdf_list.item(0).toolTip()
        self.status_bar.showMessage(
            f"Extracting data from {os.path.basename(pdf_path)}...", 3000
        )

        try:
            if not hasattr(self, "pdf_extractor"):
                self.pdf_extractor = PDFExtractor()
            extracted_data = self.pdf_extractor.extract_from_pdf(
                pdf_path, all_matches=True
            )

            # Handle multiple invoice candidates.
            if (
                "invoice_number_candidates" in extracted_data
                and extracted_data["invoice_number_candidates"]
            ):
                candidates = extracted_data["invoice_number_candidates"]
                if len(candidates) > 1:
                    selected_invoice = self.select_invoice_number(candidates)
                    if selected_invoice:
                        extracted_data["invoice_number"] = selected_invoice
                elif len(candidates) == 1:
                    extracted_data["invoice_number"] = candidates[0]

            # Handle multiple GST candidates.
            if (
                "gst_number_candidates" in extracted_data
                and extracted_data["gst_number_candidates"]
            ):
                candidates = extracted_data["gst_number_candidates"]
                if len(candidates) > 1:
                    selected_gst = self.select_gst_number(candidates)
                    if selected_gst:
                        extracted_data["gst_number"] = selected_gst
                elif len(candidates) == 1:
                    extracted_data["gst_number"] = candidates[0]

            # Populate form fields with extracted data.
            if extracted_data["company_name"]:
                self.company_name_edit.setText(extracted_data["company_name"])
            if extracted_data["invoice_number"]:
                self.invoice_number_edit.setText(extracted_data["invoice_number"])
            if extracted_data["gst_number"]:
                self.gst_number_edit.setText(extracted_data["gst_number"])
            if extracted_data["amount"]:
                self.amount_edit.setText(extracted_data["amount"])
                self.include_amount_checkbox.setChecked(True)
                self.amount_edit.setEnabled(True)

            if any(extracted_data.values()):
                self.status_bar.showMessage("Data extracted successfully!", 5000)
            else:
                self.status_bar.showMessage(
                    "No data could be extracted from the PDF.", 5000
                )
        except Exception as e:
            logging.error(f"Error in PDF extraction: {e}")
            QMessageBox.critical(
                self, "Extraction Error", f"Failed to extract data: {str(e)}"
            )
            self.status_bar.showMessage("Failed to extract data from PDF.", 5000)

    def select_invoice_number(self, candidates):
        """
        Open a dialog for the user to select an invoice number from multiple candidates.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Invoice Number")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel("Multiple invoice numbers were found. Please select one:")
        )
        list_widget = QListWidget(dialog)
        for candidate in candidates:
            list_widget.addItem(candidate)
        layout.addWidget(list_widget)
        button_box = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(select_btn)
        button_box.addWidget(cancel_btn)
        layout.addLayout(button_box)
        select_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                return selected_items[0].text()
        return None

    def select_gst_number(self, candidates):
        """
        Open a dialog for the user to select a GST number from multiple candidates.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Select GST Number")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Multiple GST numbers were found. Please select one:"))
        list_widget = QListWidget(dialog)
        for candidate in candidates:
            list_widget.addItem(candidate)
        layout.addWidget(list_widget)
        button_box = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(select_btn)
        button_box.addWidget(cancel_btn)
        layout.addLayout(button_box)
        select_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                return selected_items[0].text()
        return None

    def create_invoice_from_main(self):
        """
        Gather invoice data from the form, check for required fields, and process the invoice.
        Moves/renames the selected PDF file accordingly.
        """
        data = {
            "company_name": self.company_name_edit.text().strip(),
            "invoice_number": self.invoice_number_edit.text().strip(),
            "amount": self.amount_edit.text().strip(),
            "gst_number": self.gst_number_edit.text().strip(),
            "include_amount": self.include_amount_checkbox.isChecked(),
        }
        required_fields = ["company_name", "invoice_number"]
        if not all(data.get(field) for field in required_fields):
            QMessageBox.warning(
                self, "Missing Data", "Company name and invoice number are required."
            )
            return

        if data["include_amount"] and not data["amount"]:
            QMessageBox.warning(
                self,
                "Missing Amount",
                "Please provide an amount or uncheck 'Include Amount'.",
            )
            return

        if self.pdf_list.count() == 0:
            QMessageBox.warning(
                self,
                "Missing PDF",
                "Please drop the PDF file to be renamed as the invoice.",
            )
            return

        source_pdf = self.pdf_list.item(0).toolTip()
        success, result = self.invoice_manager.process_invoice(data, source_pdf)
        if success:
            self.status_bar.showMessage(f"Invoice saved to {result}", 5000)
            final_path = self.invoice_dest_path.text()
            # Temporarily disconnect signals before clearing fields.
            self.company_name_edit.textChanged.disconnect(
                self.update_invoice_path_preview
            )
            self.invoice_number_edit.textChanged.disconnect(
                self.update_invoice_path_preview
            )
            self.pdf_list.clear()
            self.company_name_edit.clear()
            self.invoice_number_edit.clear()
            self.amount_edit.clear()
            self.gst_number_edit.clear()
            # Restore path preview and reconnect signals.
            self.invoice_dest_path.setText(final_path)
            self.company_name_edit.textChanged.connect(self.update_invoice_path_preview)
            self.invoice_number_edit.textChanged.connect(
                self.update_invoice_path_preview
            )
        else:
            QMessageBox.critical(self, "Error", f"Failed to process invoice: {result}")

    def update_invoice_path_preview(self):
        """
        Update the preview text showing where the invoice will be saved,
        based on the company name.
        """
        company = self.company_name_edit.text().strip()
        if company:
            path = self.invoice_manager.get_invoice_path(company)
            self.invoice_dest_path.setText(path)
        else:
            self.invoice_dest_path.setText("")

    def toggle_amount_field(self, state):
        """
        Enable or disable the amount field based on the state of the checkbox.
        """
        self.amount_edit.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.amount_edit.clear()

    # -------------------------------------------------------------------------
    # Directory Navigation and File Operations
    # -------------------------------------------------------------------------
    def pdf_list_clicked(self, event):
        """
        Handle mouse click events on the PDF list widget.
        Left-click on an item opens the PDF file; otherwise, open a file dialog to add PDFs.
        """
        if event.button() != Qt.LeftButton:
            return super(DragDropListWidget, self.pdf_list).mouseReleaseEvent(event)

        item = self.pdf_list.itemAt(event.pos())
        if item:
            success, error = open_file(item.toolTip())
            if not success:
                QMessageBox.critical(self, "Error", f"Failed to open file:\n{error}")
        else:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Select PDF Files", "", "PDF Files (*.pdf)"
            )
            if file_paths:
                for path in file_paths:
                    new_item = QListWidgetItem(os.path.basename(path))
                    new_item.setToolTip(path)
                    self.pdf_list.addItem(new_item)
        return super(DragDropListWidget, self.pdf_list).mouseReleaseEvent(event)

    def change_destination(self, proxy_index):
        """
        Handle double-click events on the directory tree.
        Change the current directory if a folder is double-clicked or open a file if it's a file.
        """
        if not proxy_index.isValid():
            return

        proxy_index = proxy_index.sibling(proxy_index.row(), 0)
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            return

        path = self.dir_model.filePath(source_index)
        if not path:
            return

        logging.info("Double-clicked path: %s", path)
        if os.path.isdir(path):
            self.history.append(self.current_directory)
            self.current_directory = os.path.normpath(path)
            self.folder_path_line.setText(self.current_directory)
            self.refresh_directory()
            self.status_bar.showMessage(
                f"Changed destination to: {self.current_directory}", 5000
            )
            self.back_btn.setEnabled(True)
        elif os.path.isfile(path):
            success, error = open_file(path)
            if not success:
                QMessageBox.critical(self, "Error", f"Failed to open file:\n{error}")

    def go_back(self):
        """
        Navigate back to the previous directory.
        """
        if self.history:
            self.current_directory = os.path.normpath(self.history.pop())
            self.folder_path_line.setText(self.current_directory)
            self.proxy_model.setRootPath(self.current_directory)
            self.refresh_directory()
            self.status_bar.showMessage(f"Returned to: {self.current_directory}", 5000)
            if not self.history:
                self.back_btn.setEnabled(False)

    def refresh_directory(self):
        """
        Refresh the directory model and view.
        Apply a fade-in animation to indicate the update.
        """
        logging.debug(f"Refreshing directory: {self.current_directory}")
        self._refresh_in_progress = True

        # Reset the directory model.
        self.dir_model = setup_directory_model(self.current_directory)
        self.proxy_model.setRootPath(self.current_directory)
        self.proxy_model.setSourceModel(self.dir_model)
        update_tree_view(
            self.dir_tree, self.proxy_model, self.dir_model, self.current_directory
        )
        apply_fade_in_animation(self.dir_tree)

        self.status_bar.showMessage("Directory refreshed.", 3000)
        self._refresh_in_progress = False

    def delete_selected(self):
        """
        Delete selected files or folders from the directory tree after user confirmation.
        """
        paths = get_selected_paths(self.dir_tree, self.proxy_model)
        if not paths:
            QMessageBox.warning(self, "Delete Error", "No file or folder selected.")
            return

        confirm_text = (
            "Are you sure you want to delete the following items?\n" + "\n".join(paths)
        )
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for path in paths:
                success, error = delete_item(path)
                if not success:
                    QMessageBox.critical(
                        self, "Error", f"Deletion failed for {path}:\n{error}"
                    )
            self.status_bar.showMessage("Selected item(s) deleted successfully.", 5000)
            self.refresh_directory()

    def organize_pdfs(self):
        """
        Organize PDF files by copying them to the current directory.
        This is done in the background using an OrganizeWorker.
        """
        if self._refresh_in_progress:
            QMessageBox.warning(
                self, "Busy", "Directory refresh in progress. Please wait."
            )
            return

        dest_folder = self.current_directory
        if not os.path.isdir(dest_folder):
            QMessageBox.warning(
                self, "Destination Error", "The destination folder does not exist."
            )
            return

        # Gather all source file paths from the PDF list.
        source_files = [
            self.pdf_list.item(i).toolTip() for i in range(self.pdf_list.count())
        ]

        worker = OrganizeWorker(
            source_files,
            dest_folder,
            self.settings.get("conflict_mode", "Prompt"),
            auto_rename,
        )
        worker.finished.connect(self.on_organize_finished)
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        worker.start()

        self.status_bar.showMessage("Organizing PDF files...", 2000)

    def on_organize_finished(self, count):
        """
        Callback once the OrganizeWorker finishes processing.
        Clears the PDF list and refreshes the directory view.
        """
        self.pdf_list.clear()
        self.status_bar.showMessage(
            f"Organized {count} PDF(s) to {self.current_directory}", 5000
        )
        QTimer.singleShot(100, self.refresh_directory)

    # -------------------------------------------------------------------------
    # Directory Viewing Methods
    # -------------------------------------------------------------------------
    def view_current_directory(self):
        """
        Open a dialog to view the contents of the current directory.
        """
        dialog = DirectoryViewerDialog(self.current_directory, self)
        dialog.exec_()

    def view_pdf_files(self):
        """
        Open a dialog to view PDF files within the current directory.
        """
        dialog = PDFViewerDialog(self.current_directory, self)
        dialog.exec_()

    def create_subfolder(self):
        """
        Create a new subfolder within the current directory.
        Suggests a default folder name based on today's date.
        """
        default_name = datetime.date.today().strftime("%Y-%m-%d")
        folder_name, ok = QInputDialog.getText(
            self, "New Subfolder", "Enter subfolder name:", text=default_name
        )
        if not ok or not folder_name:
            return

        new_folder_path = os.path.normpath(
            os.path.join(self.current_directory, folder_name)
        )
        if os.path.exists(new_folder_path):
            choice = QMessageBox.question(
                self,
                "Folder Exists",
                f"The folder '{folder_name}' already exists.\nDo you want to use the existing folder?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if choice == QMessageBox.No:
                return
        else:
            success, error = create_directory(new_folder_path)
            if not success:
                QMessageBox.critical(
                    self, "Error", f"Error creating subfolder:\n{error}"
                )
                return
            self.status_bar.showMessage(f"Subfolder created: {new_folder_path}", 5000)

        QTimer.singleShot(200, self.refresh_directory)

    # -------------------------------------------------------------------------
    # Close Event – Save Settings
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Save settings (default directory, font size, conflict mode) before closing the application.
        """
        self.qsettings.setValue(
            "default_directory", self.settings.get("default_directory", self.main_dir)
        )
        self.qsettings.setValue("font_size", self.settings.get("font_size", 10))
        self.qsettings.setValue(
            "conflict_mode", self.settings.get("conflict_mode", "Prompt")
        )
        super().closeEvent(event)

    # =============================================================================
    # Resource Path Method
    # =============================================================================

    def resource_path(self, relative_path):
        """Get absolute path to resource, works in development and PyInstaller modes."""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # Fallback to looking in multiple potential locations
            potential_paths = [
                os.path.abspath("."),  # Current directory
                os.path.abspath(".."),  # Parent directory
                os.path.join(os.path.abspath(".."), "top_scan"),  # Project root
                os.path.dirname(os.path.abspath(__file__)),  # Script directory
            ]

            # Try each path until we find the file
            for path in potential_paths:
                full_path = os.path.join(path, relative_path)
                if os.path.exists(full_path):
                    return full_path

            # Default to current directory if not found
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)


# =============================================================================
# Main Application Entry Point
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icons/invoice.png"))
    organizer = PDFOrganizer()
    organizer.show()
    sys.exit(app.exec_())

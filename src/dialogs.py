import os
import subprocess
import sys
import re
from PyQt5.QtWidgets import (
    QDialog,
    QTreeView,
    QVBoxLayout,
    QHeaderView,
    QFileSystemModel,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QLabel,
    QInputDialog,
    QListWidget,
)
from convert_regex import RegexConverter
from PyQt5.QtCore import QSettings


class DirectoryViewerDialog(QDialog):
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Current Directory Contents")
        self.resize(600, 400)
        self.model = QFileSystemModel()
        self.model.setRootPath(folder_path)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(folder_path))
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)


class PDFViewerDialog(QDialog):
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Files in Current Directory")
        self.resize(600, 400)
        self.model = QFileSystemModel()
        self.model.setRootPath(folder_path)
        self.model.setNameFilters(["*.pdf"])
        self.model.setNameFilterDisables(False)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(folder_path))
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.doubleClicked.connect(self.open_pdf)
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def open_pdf(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            try:
                if sys.platform.startswith("darwin"):
                    subprocess.call(("open", path))
                elif os.name == "nt":
                    os.startfile(path)
                elif os.name == "posix":
                    subprocess.call(("xdg-open", path))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file:\n{e}")


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings.copy()
        self.resize(400, 200)
        layout = QFormLayout()

        self.default_dir_edit = QLineEdit(self.settings.get("default_directory", ""))
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.default_dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addRow("Default Directory:", dir_layout)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems(["Prompt", "Overwrite", "Auto-Rename"])
        current_mode = self.settings.get("conflict_mode", "Prompt")
        index = self.conflict_combo.findText(current_mode)
        if index >= 0:
            self.conflict_combo.setCurrentIndex(index)
        layout.addRow("File Conflict Mode:", self.conflict_combo)

        self.font_size_edit = QLineEdit(str(self.settings.get("font_size", 10)))
        layout.addRow("Font Size:", self.font_size_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def browse_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Directory")
        if folder:
            self.default_dir_edit.setText(folder)

    def accept(self):
        try:
            self.settings["default_directory"] = self.default_dir_edit.text().strip()
            self.settings["conflict_mode"] = self.conflict_combo.currentText()
            self.settings["font_size"] = int(self.font_size_edit.text().strip())
        except Exception as e:
            QMessageBox.warning(self, "Invalid Input", f"Error in input: {e}")
            return
        super().accept()

    def get_settings(self):
        return self.settings


class RegexManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regex Pattern Manager")
        self.resize(800, 500)

        # Load existing patterns
        self.regex_converter = RegexConverter()
        self.pattern_categories = self.load_patterns()

        # Main layout
        layout = QVBoxLayout(self)

        # Category selection
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.pattern_categories.keys())
        self.category_combo.currentTextChanged.connect(self.load_category_patterns)
        category_layout.addWidget(QLabel("Category:"))
        category_layout.addWidget(self.category_combo, 1)  # Stretch

        # Add/remove category buttons
        self.add_category_btn = QPushButton("Add Category")
        self.add_category_btn.clicked.connect(self.add_category)
        self.remove_category_btn = QPushButton("Remove Category")
        self.remove_category_btn.clicked.connect(self.remove_category)
        category_layout.addWidget(self.add_category_btn)
        category_layout.addWidget(self.remove_category_btn)
        layout.addLayout(category_layout)

        # Pattern list and editor
        patterns_layout = QHBoxLayout()

        # Left side: pattern list
        list_layout = QVBoxLayout()
        self.patterns_list = QListWidget()
        self.patterns_list.currentRowChanged.connect(self.load_pattern)
        list_layout.addWidget(QLabel("Patterns:"))
        list_layout.addWidget(self.patterns_list)

        # Add/remove buttons
        btn_layout = QHBoxLayout()
        self.add_pattern_btn = QPushButton("Add")
        self.add_pattern_btn.clicked.connect(self.add_pattern)
        self.remove_pattern_btn = QPushButton("Remove")
        self.remove_pattern_btn.clicked.connect(self.remove_pattern)
        btn_layout.addWidget(self.add_pattern_btn)
        btn_layout.addWidget(self.remove_pattern_btn)
        list_layout.addLayout(btn_layout)
        patterns_layout.addLayout(list_layout)

        # Right side: pattern editor
        editor_layout = QVBoxLayout()
        editor_layout.addWidget(QLabel("Pattern Editor:"))

        # Plain text input
        editor_layout.addWidget(QLabel("Plain Text:"))
        self.plain_text_edit = QLineEdit()
        self.plain_text_edit.textChanged.connect(self.update_regex_preview)
        editor_layout.addWidget(self.plain_text_edit)

        # Controls for regex conversion
        options_layout = QHBoxLayout()
        self.generic_matching_cb = QCheckBox("Generic Matching")
        self.generic_matching_cb.setChecked(True)
        self.generic_matching_cb.stateChanged.connect(self.update_regex_preview)
        self.full_match_cb = QCheckBox("Full Match")
        self.full_match_cb.stateChanged.connect(self.update_regex_preview)
        options_layout.addWidget(self.generic_matching_cb)
        options_layout.addWidget(self.full_match_cb)
        editor_layout.addLayout(options_layout)

        # Convert button and regex result
        convert_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Convert to Regex")
        self.convert_btn.clicked.connect(self.convert_to_regex)
        convert_layout.addWidget(self.convert_btn)
        editor_layout.addLayout(convert_layout)

        editor_layout.addWidget(QLabel("Regular Expression:"))
        self.regex_edit = QLineEdit()
        editor_layout.addWidget(self.regex_edit)

        # Test area
        editor_layout.addWidget(QLabel("Test Text:"))
        self.test_edit = QLineEdit()
        self.test_btn = QPushButton("Test Regex")
        self.test_btn.clicked.connect(self.test_regex)
        editor_layout.addWidget(self.test_edit)
        editor_layout.addWidget(self.test_btn)

        self.test_result_label = QLabel("")
        editor_layout.addWidget(self.test_result_label)

        # Save button
        self.save_btn = QPushButton("Save Pattern")
        self.save_btn.clicked.connect(self.save_pattern)
        editor_layout.addWidget(self.save_btn)

        patterns_layout.addLayout(editor_layout)
        layout.addLayout(patterns_layout)

        # Close button at bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        layout.addLayout(bottom_layout)

        # Select the first category by default
        if self.pattern_categories:
            self.load_category_patterns(next(iter(self.pattern_categories.keys())))

    # In the RegexManagerDialog class, modify the load_patterns and save_patterns methods

    def load_patterns(self):
        """Load patterns from QSettings or return defaults"""
        settings = QSettings("MyCompany", "PDFOrganizer")

        if settings.contains("regex_patterns"):
            # If patterns exist in settings, load them
            try:
                patterns_json = settings.value("regex_patterns")
                if patterns_json:
                    return patterns_json
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load patterns: {str(e)}"
                )

        # Return default pattern structure if not in settings or loading failed
        return {
            "gst_number": [
                r"GST(?:\s+|:|\s*No\.?\s*|Number\s*:?)\s*([0-9A-Z]{15})",
                r"GSTIN\s*:?\s*([0-9A-Z]{15})",
            ],
            "invoice_number": [
                r"Invoice\s+(?:No\.?|Number|#)\s*:?\s*([\w\d\-/]+)",
                r"Bill\s+(?:No\.?|Number|#)\s*:?\s*([\w\d\-/]+)",
                r"(?:Invoice|Bill)\s*:?\s*([\w\d\-/]+)",
            ],
            "amount": [
                r"Total\s+Amount\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"Grand\s+Total\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"Amount\s+(?:Due|Payable|Total)\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)",
            ],
            "company_name": [
                r"(?:Company|Business|Vendor|Seller|From)[\s:]+([^\n]+)",
                r"(?:^|\n)([A-Z][A-Za-z\s]+(?:Ltd|Limited|Inc|LLC|LLP|Pvt|Corporation|Corp|\&\s*Co)\.?)(?:\n|$)",
            ],
        }

    def save_patterns(self):
        """Save patterns to QSettings"""
        try:
            settings = QSettings("MyCompany", "PDFOrganizer")
            settings.setValue("regex_patterns", self.pattern_categories)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save patterns: {str(e)}")

    def load_category_patterns(self, category):
        """Load patterns for the selected category"""
        if not category:
            return

        self.patterns_list.clear()
        if category in self.pattern_categories:
            for pattern in self.pattern_categories[category]:
                self.patterns_list.addItem(pattern)

    def load_pattern(self, row):
        """Load the selected pattern into the editor"""
        if row < 0:
            return

        category = self.category_combo.currentText()
        if category in self.pattern_categories and row < len(
            self.pattern_categories[category]
        ):
            pattern = self.pattern_categories[category][row]
            self.regex_edit.setText(pattern)
            self.plain_text_edit.clear()  # Clear plain text when loading a regex

    def add_category(self):
        """Add a new pattern category"""
        name, ok = QInputDialog.getText(self, "New Category", "Enter category name:")
        if ok and name:
            if name in self.pattern_categories:
                QMessageBox.warning(
                    self, "Warning", f"Category '{name}' already exists."
                )
                return

            self.pattern_categories[name] = []
            self.category_combo.addItem(name)
            self.category_combo.setCurrentText(name)
            self.save_patterns()

    def remove_category(self):
        """Remove the current pattern category"""
        category = self.category_combo.currentText()
        if not category:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the category '{category}' and all its patterns?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            if category in self.pattern_categories:
                del self.pattern_categories[category]
                self.category_combo.removeItem(self.category_combo.currentIndex())
                self.save_patterns()

    def add_pattern(self):
        """Add a new pattern to the current category"""
        category = self.category_combo.currentText()
        if not category:
            QMessageBox.warning(
                self, "Warning", "Please select or create a category first."
            )
            return

        if category not in self.pattern_categories:
            self.pattern_categories[category] = []

        # Use the current regex or an empty one
        pattern = self.regex_edit.text() or r""
        if pattern:
            self.pattern_categories[category].append(pattern)
            self.patterns_list.addItem(pattern)
            self.save_patterns()

    def remove_pattern(self):
        """Remove the selected pattern"""
        row = self.patterns_list.currentRow()
        if row < 0:
            return

        category = self.category_combo.currentText()
        if category in self.pattern_categories and row < len(
            self.pattern_categories[category]
        ):
            del self.pattern_categories[category][row]
            self.patterns_list.takeItem(row)
            self.save_patterns()

    def convert_to_regex(self):
        """Convert plain text to regex pattern"""
        text = self.plain_text_edit.text()
        if not text:
            return

        try:
            pattern = self.regex_converter.string_to_regex(
                text,
                generic_matching=self.generic_matching_cb.isChecked(),
                full_match=self.full_match_cb.isChecked(),
            )

            # Check if pattern has capture groups, if not, add them
            if "(" not in pattern or not re.search(r"\([^)]*\)", pattern):
                # Wrap the entire pattern in capture group
                pattern = f"({pattern})"

            self.regex_edit.setText(pattern)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert to regex: {str(e)}")

    def update_regex_preview(self):
        """Update regex preview when options change"""
        if self.plain_text_edit.text():
            self.convert_to_regex()

    def test_regex(self):
        """Test the current regex against the test text"""
        pattern = self.regex_edit.text()
        test_text = self.test_edit.text()
        if not pattern or not test_text:
            return

        try:
            import re

            regex = re.compile(pattern)
            match = regex.search(test_text)

            if match:
                self.test_result_label.setText(f"MATCH! Found: '{match.group(0)}'")
                # If the pattern has a capture group, show that too
                if match.groups():
                    self.test_result_label.setText(
                        f"MATCH! Found: '{match.group(0)}', Captured: '{match.group(1)}'"
                    )
            else:
                self.test_result_label.setText("No match.")
        except Exception as e:
            self.test_result_label.setText(f"Error: {str(e)}")

    def save_pattern(self):
        """Save the current pattern"""
        pattern = self.regex_edit.text()
        if not pattern:
            return

        # Check if pattern has capture groups, if not, add them
        if "(" not in pattern or not re.search(r"\([^)]*\)", pattern):
            # Wrap the entire pattern in capture group
            pattern = f"({pattern})"
            self.regex_edit.setText(pattern)
            QMessageBox.information(
                self,
                "Capture Group Added",
                "Added capture groups to your pattern. Capture groups are required for proper extraction.",
            )

        category = self.category_combo.currentText()
        if not category:
            QMessageBox.warning(
                self, "Warning", "Please select or create a category first."
            )
            return

        row = self.patterns_list.currentRow()
        if row >= 0:
            # Update existing pattern
            self.pattern_categories[category][row] = pattern
            self.patterns_list.item(row).setText(pattern)
        else:
            # Add as new pattern
            if category not in self.pattern_categories:
                self.pattern_categories[category] = []
            self.pattern_categories[category].append(pattern)
            self.patterns_list.addItem(pattern)

        self.save_patterns()
        QMessageBox.information(self, "Success", "Pattern saved successfully.")


# Add this new class to dialogs.py


class GSTMappingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GST Number to Company Mapping")
        self.resize(600, 400)

        # Load existing mappings
        self.mappings = self.load_mappings()

        # Main layout
        layout = QVBoxLayout(self)

        # Mapping table layout
        table_layout = QHBoxLayout()

        # Left side: List of GST numbers with company names
        list_layout = QVBoxLayout()
        self.mapping_list = QListWidget()
        self.mapping_list.currentRowChanged.connect(self.load_mapping)
        list_layout.addWidget(QLabel("GST Mappings:"))
        list_layout.addWidget(self.mapping_list)

        # Populate the list with format "GST: Company"
        self.refresh_mapping_list()

        # Button layout
        btn_layout = QHBoxLayout()
        self.new_mapping_btn = QPushButton("New")
        self.new_mapping_btn.clicked.connect(self.clear_fields)
        self.remove_mapping_btn = QPushButton("Remove")
        self.remove_mapping_btn.clicked.connect(self.remove_mapping)
        btn_layout.addWidget(self.new_mapping_btn)
        btn_layout.addWidget(self.remove_mapping_btn)
        list_layout.addLayout(btn_layout)
        table_layout.addLayout(list_layout)

        # Right side: Mapping editor
        editor_layout = QVBoxLayout()
        editor_layout.addWidget(QLabel("Mapping Details:"))

        # GST Number input
        editor_layout.addWidget(QLabel("GST Number:"))
        self.gst_edit = QLineEdit()
        self.gst_edit.setPlaceholderText("Enter 15-digit GST number")
        editor_layout.addWidget(self.gst_edit)

        # Company Name input
        editor_layout.addWidget(QLabel("Company Name:"))
        self.company_name_edit = QLineEdit()
        self.company_name_edit.setPlaceholderText("Enter company name")
        editor_layout.addWidget(self.company_name_edit)

        # Save button
        self.save_btn = QPushButton("Save Mapping")
        self.save_btn.clicked.connect(self.save_mapping)
        editor_layout.addWidget(self.save_btn)

        # Add a spacer
        editor_layout.addStretch()

        table_layout.addLayout(editor_layout)
        layout.addLayout(table_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        layout.addLayout(bottom_layout)

    def refresh_mapping_list(self):
        """Refresh the list of mappings"""
        self.mapping_list.clear()
        for gst_number, company_name in self.mappings.items():
            self.mapping_list.addItem(f"{gst_number}: {company_name}")

    def load_mappings(self):
        """Load GST to company mappings from settings"""
        settings = QSettings("MyCompany", "PDFOrganizer")
        mappings = settings.value("gst_company_mappings", {})
        return mappings if mappings else {}

    def save_mappings(self):
        """Save mappings to settings"""
        settings = QSettings("MyCompany", "PDFOrganizer")
        settings.setValue("gst_company_mappings", self.mappings)

    def load_mapping(self, row):
        """Load the selected mapping into the editor"""
        if row < 0:
            return

        # Extract GST number from the item text (format is "GST: Company")
        item_text = self.mapping_list.item(row).text()
        try:
            gst_number = item_text.split(":", 1)[0].strip()
            company_name = self.mappings.get(gst_number, "")

            self.gst_edit.setText(gst_number)
            self.company_name_edit.setText(company_name)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading mapping: {str(e)}")

    def clear_fields(self):
        """Clear the form fields for a new mapping"""
        self.gst_edit.clear()
        self.company_name_edit.clear()
        self.mapping_list.clearSelection()
        self.gst_edit.setFocus()

    def remove_mapping(self):
        """Remove the selected mapping"""
        row = self.mapping_list.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, "No Selection", "Please select a mapping to remove."
            )
            return

        # Extract GST number from the selected item
        item_text = self.mapping_list.item(row).text()
        try:
            gst_number = item_text.split(":", 1)[0].strip()

            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to remove the mapping for GST number '{gst_number}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                if gst_number in self.mappings:
                    del self.mappings[gst_number]
                    self.save_mappings()
                    self.refresh_mapping_list()
                    self.clear_fields()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error removing mapping: {str(e)}")

    def save_mapping(self):
        """Save the current mapping"""
        gst_number = self.gst_edit.text().strip()
        company_name = self.company_name_edit.text().strip()

        if not gst_number:
            QMessageBox.warning(
                self, "Missing GST Number", "Please enter a GST number."
            )
            return

        if not company_name:
            QMessageBox.warning(
                self, "Missing Company Name", "Please enter a company name."
            )
            return

        # Validate GST number format (basic validation)
        if not re.match(r"^[0-9A-Z]{15}$", gst_number):
            QMessageBox.warning(
                self,
                "Invalid GST Number",
                "GST number should be 15 characters (digits and uppercase letters).",
            )
            return

        # Save the mapping
        self.mappings[gst_number] = company_name
        self.save_mappings()

        # Update the list
        self.refresh_mapping_list()

        # Find and select the newly added/updated item
        for i in range(self.mapping_list.count()):
            if self.mapping_list.item(i).text().startswith(gst_number + ":"):
                self.mapping_list.setCurrentRow(i)
                break

        QMessageBox.information(self, "Success", "Mapping saved successfully.")

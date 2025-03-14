from PyQt5.QtWidgets import QMessageBox
from file_operations import move_file, create_directory, auto_rename
import os
import datetime


class InvoiceManager:
    def __init__(self, base_directory, parent=None):
        self.base_directory = base_directory
        self.parent = parent  # Make sure to pass the main window as parent

    def get_invoice_path(self, company_name, date_format="%Y-%m-%d"):
        if not company_name:
            return ""
        date_str = datetime.datetime.now().strftime(date_format)
        return os.path.join(self.base_directory, company_name, date_str)

    def process_invoice(self, data, source_pdf=None):
        if not data.get("company_name") or not data.get("invoice_number"):
            return False, "Missing required invoice data."

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        invoice_dir = os.path.join(self.base_directory, data["company_name"], date_str)
        success, err = create_directory(invoice_dir)
        if not success:
            return False, err

        if source_pdf:
            if not os.path.exists(source_pdf):
                return False, f"Source PDF does not exist: {source_pdf}"
            # Determine filename format
            if data.get("include_amount") and data.get("amount"):
                filename = f"{data['invoice_number']}-{data['amount']}.pdf"
            else:
                filename = f"{data['invoice_number']}.pdf"
            dest_pdf = os.path.join(invoice_dir, filename)
            # If file exists, prompt the user as in your organize routine.
            if os.path.exists(dest_pdf):
                ret = QMessageBox.question(
                    self.parent,
                    "File exists",
                    f"The file '{filename}' already exists in '{invoice_dir}'.\nDo you want to auto-rename the new invoice?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.Yes:
                    dest_pdf = auto_rename(invoice_dir, filename)
                else:
                    return False, "Operation cancelled: File already exists."
            success, err = move_file(source_pdf, dest_pdf)
            if not success:
                return False, err
        return True, invoice_dir

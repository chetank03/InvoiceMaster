import os
import shutil
import logging
from PyQt5.QtCore import QThread, pyqtSignal


class OrganizeWorker(QThread):
    # Signal that emits the count of files successfully organized.
    finished = pyqtSignal(int)
    # Signal that emits an error message string when an error occurs.
    error = pyqtSignal(str)

    def __init__(
        self, file_items, dest_folder, conflict_mode, auto_rename_func, parent=None
    ):
        """
        Initialize the worker thread with files to organize.

        Args:
            file_items (list): List of source file paths.
            dest_folder (str): Destination folder where files should be copied.
            conflict_mode (str): Mode to handle file name conflicts ("Overwrite", "Auto-Rename", etc.).
            auto_rename_func (function): Function to auto-rename a file if needed.
            parent: Optional thread parent.
        """
        super().__init__(parent)
        self.file_items = file_items  # List of source file paths to be processed.
        self.dest_folder = dest_folder  # Destination directory to copy files into.
        self.conflict_mode = conflict_mode  # Conflict mode setting.
        self.auto_rename_func = (
            auto_rename_func  # Function to handle automatic renaming.
        )

    def run(self):
        """
        Process each file: copy the file to the destination folder taking into account
        conflict modes. Emit a 'finished' signal with the count of files organized or an
        'error' signal for any encountered errors.
        """
        count = 0  # Counter for successfully organized files.
        for source in self.file_items:
            try:
                # Check if the source file exists.
                if not os.path.exists(source):
                    logging.warning("Source does not exist: %s", source)
                    continue

                # Get the base filename and first construct the default destination path.
                filename = os.path.basename(source)
                dest_file = os.path.join(self.dest_folder, filename)

                # Avoid copying the file onto itself.
                if os.path.abspath(source) == os.path.abspath(dest_file):
                    logging.info("Skipping same source and destination: %s", source)
                    continue

                # If the destination file already exists, resolve conflict based on conflict_mode.
                if os.path.exists(dest_file):
                    if self.conflict_mode == "Overwrite":
                        logging.info("Overwriting existing file: %s", dest_file)
                    elif self.conflict_mode == "Auto-Rename":
                        # Call the provided auto_rename_func to generate a new destination path.
                        dest_file = self.auto_rename_func(self.dest_folder, filename)
                        logging.info("Auto-renamed file to: %s", dest_file)
                    else:
                        # For other modes, skip processing this file.
                        logging.info("Skipping file due to conflict: %s", filename)
                        continue

                # Copy the source file to the destination.
                shutil.copy(source, dest_file)
                count += 1  # Increment successful copy count.
            except Exception as e:
                # In case of error, log the error and emit an error signal.
                error_msg = f"Failed to copy {source}: {e}"
                logging.error(error_msg)
                self.error.emit(error_msg)
        # Emit finished signal with the total count of files processed.
        self.finished.emit(count)

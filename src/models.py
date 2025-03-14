import os
import logging
import re
from PyQt5.QtCore import QSortFilterProxyModel, Qt


class DirectoryFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy model that filters directory listings based on the provided root and filter text.

    An item is accepted if:
      - Its path is under the specified root path.
      - The base name of the file or folder contains the filter text.
      - For directories, if any of its descendants match the filter text.
    """

    def __init__(self, root_path, *args, **kwargs):
        """
        Initialize the proxy model with the given root path.

        Args:
            root_path (str): The base directory path to filter within.
        """
        super().__init__(*args, **kwargs)
        # Normalize and store the root path
        self.root_path = os.path.normpath(root_path)
        # Set the filtering to work on the first column (typically the name)
        self.setFilterKeyColumn(0)
        # Enable case-insensitive matching
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Enable recursive filtering to check children folders
        self.setRecursiveFilteringEnabled(True)

    def setRootPath(self, root_path):
        """
        Update the root path and refresh the filtering.

        Args:
            root_path (str): New root directory path.
        """
        self.root_path = os.path.normpath(root_path)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Determines if a row in the source model should be accepted by the filter.

        Conditions:
         1. The item's file path must be under the root path.
         2. If there's filter text, the base name of the item must contain it.
         3. If the item is a directory, any of its descendants matching the filter qualifies it.

        Args:
            source_row (int): The row in the source model.
            source_parent (QModelIndex): The parent index in the source model.

        Returns:
            bool: True if the item passes the filter criteria, False otherwise.
        """
        try:
            # Get the index of the current item in the source model
            index = self.sourceModel().index(source_row, 0, source_parent)
            if not index.isValid():
                return False

            # Retrieve and normalize the file path
            file_path = os.path.normpath(self.sourceModel().filePath(index))
            # Ensure that the file path is under the specified root directory
            if os.path.commonpath([file_path, self.root_path]) != self.root_path:
                return False

            # Get the current filter text in lowercase (filterRegExp is a QRegExp or QRegularExpression)
            filter_text = self.filterRegExp().pattern().lower()

            # Always show the root directory regardless of the filter text
            if os.path.normcase(file_path) == os.path.normcase(self.root_path):
                return True

            # Get the base name (last part of path) in lower case
            base_name = os.path.basename(file_path).lower()

            # If there is no filter text, all items are accepted
            if not filter_text:
                return True

            # Direct match: check if the base name contains the filter text
            if filter_text in base_name:
                return True

            # For directories, check if any descendant contains the filter text
            if self.sourceModel().isDir(index):
                if self.hasAcceptedChildren(index, filter_text):
                    return True

            # If none of the above conditions are met, do not accept the row
            return False
        except Exception as e:
            logging.error("Error in filterAcceptsRow: %s", e)
            return False

    def hasAcceptedChildren(self, parent_index, filter_text):
        """
        Recursively checks if any descendant of a directory matches the filter text.

        Args:
            parent_index (QModelIndex): The index of the directory.
            filter_text (str): The filter text to match against.

        Returns:
            bool: True if at least one descendant's name contains filter_text, False otherwise.
        """
        row_count = self.sourceModel().rowCount(parent_index)
        for i in range(row_count):
            child_index = self.sourceModel().index(i, 0, parent_index)
            if not child_index.isValid():
                continue

            # Normalize file path and get the child name in lower case
            file_path = os.path.normpath(self.sourceModel().filePath(child_index))
            child_name = os.path.basename(file_path).lower()

            # If the child's name contains the filter text, accept
            if filter_text in child_name:
                return True

            # If the child is a directory, recurse into it
            if self.sourceModel().isDir(child_index):
                if self.hasAcceptedChildren(child_index, filter_text):
                    return True

        # No children accepted the filter
        return False

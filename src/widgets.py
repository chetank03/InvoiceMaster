import os
import shutil
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMenu, QTreeView, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
import sys


# =============================================================================
# Drag and Drop Widgets
# =============================================================================
class DragDropListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        # Allow the widget to accept dragged items
        self.setAcceptDrops(True)
        # Allow internal reordering of list items via drag and drop
        self.setDragDropMode(QListWidget.InternalMove)
        self.setMinimumHeight(200)
        # Set a dashed border style as visual cue for a drop area
        self.setStyleSheet("border: 1px dashed gray;")

    def dragEnterEvent(self, event):
        # Accept the event if it contains URLs (dropped files)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        # Accept move event to allow dropping continuously
        event.acceptProposedAction()

    def dropEvent(self, event):
        # Get an icon for PDF files by retrieving the resource path (see resource_path method)
        pdf_icon = QIcon(self.resource_path("icons/pdf.png"))
        # Iterate over each dropped file URL
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            # Only process files ending with .pdf (case-insensitive)
            if file_path.lower().endswith(".pdf"):
                # Create a new list item with the PDF icon and basename as text
                item = QListWidgetItem(pdf_icon, os.path.basename(file_path))
                # Store the full file path in the tooltip for later access
                item.setToolTip(file_path)
                self.addItem(item)
        event.acceptProposedAction()

    def contextMenuEvent(self, event):
        # Create a context menu with a "Remove" option
        menu = QMenu(self)
        remove_action = menu.addAction("Remove")
        action = menu.exec_(event.globalPos())
        # Remove all selected items when "Remove" is clicked
        if action == remove_action:
            for item in self.selectedItems():
                self.takeItem(self.row(item))

    def paintEvent(self, event):
        # Execute default painting first
        super().paintEvent(event)
        # If the list has no items, draw a placeholder image in the center
        if self.count() == 0:
            painter = QPainter(self.viewport())
            # Load the placeholder image (e.g., a search icon)
            pixmap = QPixmap(self.resource_path("icons/search.png"))
            if not pixmap.isNull():
                # Scale the pixmap to a fixed size (64x64) using smooth transformation
                scaled_pixmap = pixmap.scaled(
                    64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                # Calculate centered position for the pixmap
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)

    # =============================================================================
    # Resource Path Method
    # =============================================================================
    def resource_path(self, relative_path):
        """
        Get the absolute path to a resource, supporting both development and PyInstaller modes.

        Args:
            relative_path (str): The relative file path of the resource.

        Returns:
            str: The absolute file path to the resource.
        """
        try:
            # When packaged by PyInstaller, the base path is stored in sys._MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # Fall back to multiple potential base paths when running in development
            potential_paths = [
                os.path.abspath("."),  # Current directory
                os.path.abspath(".."),  # Parent directory
                os.path.join(
                    os.path.abspath(".."), "top_scan"
                ),  # Project root (if applicable)
                os.path.dirname(os.path.abspath(__file__)),  # Directory of the script
            ]
            # Search each potential path for the resource file
            for path in potential_paths:
                full_path = os.path.join(path, relative_path)
                if os.path.exists(full_path):
                    return full_path
            # Default to current directory if resource is not found
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


# =============================================================================
# Drag and Drop TreeView
# =============================================================================
class DragDropTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Enable dragging from this view
        self.setDragEnabled(True)
        # Accept dropped items (for moving files)
        self.setAcceptDrops(True)
        # Show indicator while dragging over target items
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        # Accept event with file URLs; otherwise, call default event handling
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        # Accept move events with URLs to provide better user feedback
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        # Determine target directory based on drop location in the tree view
        target_index = self.indexAt(event.pos())
        if not target_index.isValid():
            # If not dropped over a valid item, use the model's root path
            target_dir = self.model().root_path
        else:
            # Map from proxy to source if model supports that
            if hasattr(self.model(), "mapToSource"):
                source_index = self.model().mapToSource(
                    target_index.sibling(target_index.row(), 0)
                )
            else:
                source_index = target_index.sibling(target_index.row(), 0)
            # Get the file path from the file system model
            target_dir = (
                self.model().sourceModel().filePath(source_index)
                if hasattr(self.model(), "sourceModel")
                else self.model().filePath(source_index)
            )
            # If target is a file, use its parent directory for dropping
            if not os.path.isdir(target_dir):
                target_dir = os.path.dirname(target_dir)

        # Process each dropped file and move it to the target directory
        for url in event.mimeData().urls():
            source_path = url.toLocalFile()
            if not os.path.exists(source_path):
                continue
            try:
                # Move the file using shutil
                shutil.move(source_path, target_dir)
            except Exception as e:
                # Show error message if moving fails
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to move:\n{source_path}\nto\n{target_dir}:\n{e}",
                )
        event.acceptProposedAction()

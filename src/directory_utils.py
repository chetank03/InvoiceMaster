import os
import logging
from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtCore import QDir


def setup_directory_model(directory_path):
    """Create and configure a QFileSystemModel for the given directory"""
    model = QFileSystemModel()
    model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
    model.setRootPath(directory_path)
    return model


def get_selected_paths(tree_view, proxy_model, column=0):
    """Extract file paths from selected items in a tree view"""
    selected_indexes = tree_view.selectionModel().selectedIndexes()
    paths = set()

    for index in selected_indexes:
        if index.column() == column:
            source_index = proxy_model.mapToSource(index)
            path = proxy_model.sourceModel().filePath(source_index)
            if path:
                paths.add(path)

    return paths


def update_tree_view(tree_view, proxy_model, dir_model, current_directory):
    """Update a tree view with proper indexes for the directory"""
    source_root_index = dir_model.index(current_directory)
    if not source_root_index.isValid():
        logging.error("Source root index is invalid for: %s", current_directory)
        return False

    proxy_root_index = proxy_model.mapFromSource(source_root_index)
    if not proxy_root_index.isValid():
        logging.error("Proxy root index is invalid after mapping from source.")
        return False

    tree_view.setModel(proxy_model)
    tree_view.setRootIndex(proxy_root_index)
    return True

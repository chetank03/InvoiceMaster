import os
import shutil
import logging
import sys
import subprocess


def auto_rename(folder, filename):
    """Generate a unique filename when a file already exists"""
    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        new_path = os.path.join(folder, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def copy_file(source, dest_file):
    """Copy a file with appropriate error handling"""
    try:
        shutil.copy(source, dest_file)
        return True, None
    except Exception as e:
        err_msg = f"Failed to copy {source} to {dest_file}: {e}"
        logging.error(err_msg)
        return False, err_msg


def move_file(source, dest_file):
    """Move a file with appropriate error handling"""
    try:
        shutil.move(source, dest_file)
        return True, None
    except Exception as e:
        err_msg = f"Failed to move {source} to {dest_file}: {e}"
        logging.error(err_msg)
        return False, err_msg


def delete_item(path):
    """Delete a file or directory with appropriate error handling"""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True, None
    except Exception as e:
        err_msg = f"Failed to delete {path}: {e}"
        logging.error(err_msg)
        return False, err_msg


def open_file(path):
    """Open a file with the default application"""
    try:
        if sys.platform.startswith("darwin"):
            subprocess.call(("open", path))
        elif os.name == "nt":
            os.startfile(path)
        elif os.name == "posix":
            subprocess.call(("xdg-open", path))
        return True, None
    except Exception as e:
        err_msg = f"Failed to open file: {e}"
        logging.error(err_msg)
        return False, err_msg


def create_directory(path):
    """Create a directory with appropriate error handling"""
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except Exception as e:
        err_msg = f"Failed to create directory {path}: {e}"
        logging.error(err_msg)
        return False, err_msg

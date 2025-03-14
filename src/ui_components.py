from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QMenu


def apply_fade_in_animation(widget, duration=500):
    """Apply a fade-in animation to a widget"""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.InOutQuad)
    animation.start()
    # Keep a reference to prevent garbage collection
    widget.animation = animation
    return animation


def create_context_menu(items, parent=None):
    """
    Create a context menu with specified items
    items: List of tuples (name, callback)
    """
    menu = QMenu(parent)
    actions = {}

    for name, callback in items:
        action = menu.addAction(name)
        actions[action] = callback

    return menu, actions


def get_stylesheet():
    """Return the application stylesheet"""
    return """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 14px;
            font-weight: bold;
            color: #333333;
            padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QLineEdit {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px;
            background-color: white;
            font-size: 12px;
        }
        QStatusBar {
            background-color: #e0e0e0;
            color: #333333;
            font-size: 12px;
        }
        QTreeView {
            font-size: 12px;
            background-color: white;
            border: 1px solid #cccccc;
            border-radius: 4px;
        }
        QTreeView::item:hover {
            background-color: #e0e0e0;
        }
        QTreeView::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QLabel {
            font-size: 12px;
            color: #333333;
        }
    """

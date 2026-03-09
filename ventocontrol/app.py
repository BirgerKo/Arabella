"""VentoApp — QApplication subclass with dark theme."""
from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG       = "#1e1e2e"
SURFACE  = "#2a2a3e"
SURFACE2 = "#313145"
ACCENT   = "#5e81f4"
SUCCESS  = "#50fa7b"
WARNING  = "#ffb86c"
DANGER   = "#ff5555"
TEXT     = "#f8f8f2"
TEXT2    = "#6272a4"
BORDER   = "#44475a"

DARK_QSS = f"""
/* ── Global ── */
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

/* ── Group boxes ── */
QGroupBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 20px;
    padding: 8px;
    font-weight: 600;
    color: {TEXT2};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: {TEXT2};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

/* ── Generic buttons ── */
QPushButton {{
    background-color: {SURFACE2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #3a3a55;
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT};
    color: #ffffff;
}}
QPushButton:checked {{
    background-color: {ACCENT};
    color: #ffffff;
    border-color: {ACCENT};
}}
QPushButton:disabled {{
    color: {TEXT2};
    background-color: {SURFACE};
    border-color: {BORDER};
}}

/* ── Speed buttons ── */
QPushButton#SpeedBtn {{
    min-width: 52px;
    min-height: 36px;
    font-size: 15px;
    font-weight: 700;
    border-radius: 8px;
}}
QPushButton#SpeedBtn:checked {{
    background-color: {ACCENT};
    color: #ffffff;
    border-color: {ACCENT};
}}

/* ── Mode buttons ── */
QPushButton#ModeBtn {{
    min-height: 34px;
    font-size: 12px;
    border-radius: 6px;
}}
QPushButton#ModeBtn:checked {{
    background-color: #2d5a8e;
    color: #ffffff;
    border-color: #5e9be8;
}}

/* ── Boost button ── */
QPushButton#BoostBtn {{
    min-width: 56px;
}}
QPushButton#BoostBtn:checked {{
    background-color: {WARNING};
    color: {BG};
    border-color: {WARNING};
    font-weight: 700;
}}

/* ── Labels ── */
QLabel {{
    background: transparent;
    color: {TEXT};
}}
QLabel#DeviceHeader {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT};
}}
QLabel#ScanStatus {{
    color: {TEXT2};
    font-size: 12px;
}}

/* ── RPM display ── */
QWidget#RPMDisplay {{
    background-color: {SURFACE2};
    border-radius: 8px;
    min-width: 110px;
}}
QLabel#RPMValue {{
    font-size: 28px;
    font-weight: 700;
    color: {ACCENT};
    font-family: "SF Mono", "Menlo", "Courier New", monospace;
}}
QLabel#RPMUnit {{
    font-size: 11px;
    color: {TEXT2};
}}
QLabel#RPMLabel {{
    font-size: 11px;
    color: {TEXT2};
    font-weight: 600;
    text-transform: uppercase;
}}

/* ── Humidity ── */
QLabel#HumidityValue {{
    font-size: 32px;
    font-weight: 700;
    color: {SUCCESS};
    font-family: "SF Mono", "Menlo", "Courier New", monospace;
}}
QLabel#HumidityUnit {{
    font-size: 11px;
    color: {TEXT2};
}}

/* ── Inputs ── */
QLineEdit, QSpinBox {{
    background-color: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {ACCENT};
}}

/* ── Sliders ── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    border: 2px solid {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* ── List widget ── */
QListWidget {{
    background-color: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}
QListWidget::item:hover {{
    background-color: #3a3a55;
}}

/* ── Checkbox ── */
QCheckBox {{
    color: {TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {BORDER};
    background: {SURFACE2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Divider ── */
QFrame#Divider {{
    color: {BORDER};
}}

/* ── Dialog buttons ── */
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT2};
    border-top: 1px solid {BORDER};
    font-size: 11px;
}}
QStatusBar QLabel {{
    color: {TEXT2};
    font-size: 11px;
}}

/* ── Quick scenario buttons ── */
QPushButton#QuickScenarioBtn {{
    min-width: 52px;
    min-height: 30px;
    font-size: 11px;
    padding: 4px 6px;
}}

/* ── Save as Scenario button ── */
QPushButton#SaveScenarioBtn {{
    color: {SUCCESS};
    border-color: {SUCCESS};
}}
QPushButton#SaveScenarioBtn:hover {{
    background-color: #1a3a2a;
}}
QPushButton#SaveScenarioBtn:disabled {{
    color: {TEXT2};
    border-color: {BORDER};
}}

/* ── Danger button (used in Manage Scenarios dialog) ── */
QPushButton#DangerBtn {{
    background-color: #3a1a1a;
    border-color: {DANGER};
    color: {DANGER};
    min-width: 64px;
}}
QPushButton#DangerBtn:hover {{
    background-color: {DANGER};
    color: #ffffff;
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: {SURFACE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class VentoApp(QApplication):
    def __init__(self, argv=None):
        super().__init__(argv or sys.argv)
        self.setApplicationName("VentoControl")
        self.setOrganizationName("Blauberg")
        self.setApplicationVersion("1.0.0")
        self.setStyleSheet(DARK_QSS)

        # Default font
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

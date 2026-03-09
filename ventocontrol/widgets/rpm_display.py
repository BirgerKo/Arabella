"""RPMDisplay — numeric RPM readout for a single fan."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RPMDisplay(QWidget):
    """Shows a large RPM number with a label underneath."""

    def __init__(self, label: str = "Fan", parent=None):
        super().__init__(parent)
        self._value_lbl = QLabel("—")
        self._value_lbl.setObjectName("RPMValue")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._unit_lbl = QLabel("RPM")
        self._unit_lbl.setObjectName("RPMUnit")
        self._unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._name_lbl = QLabel(label)
        self._name_lbl.setObjectName("RPMLabel")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(self._name_lbl)
        layout.addWidget(self._value_lbl)
        layout.addWidget(self._unit_lbl)

        self.setObjectName("RPMDisplay")

    def set_rpm(self, rpm: int | None):
        if rpm is None:
            self._value_lbl.setText("—")
        else:
            self._value_lbl.setText(f"{rpm:,}")

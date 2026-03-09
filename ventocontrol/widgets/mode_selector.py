"""ModeSelector — exclusive toggle group for operation mode."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

_MODES = {
    0: ("Ventilation", "Vent"),
    1: ("Heat Recovery", "HR"),
    2: ("Supply", "Supply"),
}


class ModeSelector(QWidget):
    """Emits mode_changed(int) with 0=Vent, 1=HR, 2=Supply."""

    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._btns: dict[int, QPushButton] = {}
        for mode_id, (label, _) in _MODES.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("ModeBtn")
            self._btns[mode_id] = btn
            self._group.addButton(btn, mode_id)
            layout.addWidget(btn)

        self._group.idClicked.connect(self.mode_changed.emit)

    def set_mode(self, mode: int):
        btn = self._btns.get(mode)
        if btn:
            btn.setChecked(True)

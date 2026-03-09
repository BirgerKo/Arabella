"""SpeedControl — three preset speed buttons plus a manual slider."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget,
)

_SPEED_LABELS = {1: "Speed 1", 2: "Speed 2", 3: "Speed 3"}
_MANUAL_SPEED = 255


class SpeedControl(QWidget):
    """Emits speed_changed(int 1/2/3) or manual_speed_changed(int 0-255)."""

    speed_changed        = pyqtSignal(int)   # 1, 2, or 3
    manual_speed_changed = pyqtSignal(int)   # 0-255

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preset_group = QButtonGroup(self)
        self._preset_group.setExclusive(True)

        # Preset buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._btns: dict[int, QPushButton] = {}
        for spd in (1, 2, 3):
            btn = QPushButton(f"  {spd}  ")
            btn.setCheckable(True)
            btn.setObjectName("SpeedBtn")
            self._btns[spd] = btn
            self._preset_group.addButton(btn, spd)
            btn_row.addWidget(btn)

        # Manual slider row
        self._manual_btn = QPushButton("Manual")
        self._manual_btn.setCheckable(True)
        self._manual_btn.setObjectName("SpeedBtn")
        self._preset_group.addButton(self._manual_btn, _MANUAL_SPEED)
        btn_row.addWidget(self._manual_btn)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 255)
        self._slider.setValue(128)
        self._slider.setEnabled(False)
        self._slider_label = QLabel("128")
        self._slider_label.setFixedWidth(32)
        self._slider_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Manual speed:"))
        slider_row.addWidget(self._slider)
        slider_row.addWidget(self._slider_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(btn_row)
        layout.addLayout(slider_row)

        # Connections
        self._preset_group.idClicked.connect(self._on_preset_clicked)
        self._slider.valueChanged.connect(self._on_slider_changed)

    def _on_preset_clicked(self, btn_id: int):
        is_manual = (btn_id == _MANUAL_SPEED)
        self._slider.setEnabled(is_manual)
        if not is_manual:
            self.speed_changed.emit(btn_id)
        else:
            self.manual_speed_changed.emit(self._slider.value())

    def _on_slider_changed(self, value: int):
        self._slider_label.setText(str(value))
        if self._manual_btn.isChecked():
            self.manual_speed_changed.emit(value)

    def set_speed(self, speed: int):
        """Update UI to reflect current speed (1/2/3/255=manual)."""
        btn = self._btns.get(speed) or (self._manual_btn if speed == _MANUAL_SPEED else None)
        if btn:
            btn.setChecked(True)
            self._slider.setEnabled(speed == _MANUAL_SPEED)

    def set_manual_value(self, value: int):
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider_label.setText(str(value))
        self._slider.blockSignals(False)

"""HumidityWidget — live RH readout + sensor enable + threshold control."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget,
)


class HumidityWidget(QWidget):
    """Displays current humidity and controls the sensor/threshold."""

    sensor_toggled    = Signal(int)   # 0=Off, 1=On
    threshold_changed = Signal(int)   # 40-80 %RH

    def __init__(self, parent=None):
        super().__init__(parent)

        # Current RH value
        self._rh_lbl = QLabel("—")
        self._rh_lbl.setObjectName("HumidityValue")
        self._rh_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._rh_unit = QLabel("%RH")
        self._rh_unit.setObjectName("HumidityUnit")
        self._rh_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sensor enable checkbox
        self._sensor_cb = QCheckBox("Sensor enabled")
        self._sensor_cb.setObjectName("HumidityCB")

        # Threshold spinner
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Threshold:"))
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(40, 80)
        self._threshold_spin.setValue(60)
        self._threshold_spin.setSuffix(" %")
        threshold_row.addWidget(self._threshold_spin)
        threshold_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._rh_lbl)
        layout.addWidget(self._rh_unit)
        layout.addWidget(self._sensor_cb)
        layout.addLayout(threshold_row)

        self._sensor_cb.stateChanged.connect(self._on_sensor_toggled)
        self._threshold_spin.editingFinished.connect(self._on_threshold_changed)

    def _on_sensor_toggled(self, state: int):
        enabled = state == Qt.CheckState.Checked
        self.sensor_toggled.emit(1 if enabled else 0)

    def _on_threshold_changed(self):
        self.threshold_changed.emit(self._threshold_spin.value())

    def set_humidity(self, rh: int | None):
        self._rh_lbl.setText("—" if rh is None else str(rh))

    def set_sensor_enabled(self, enabled: bool):
        self._sensor_cb.blockSignals(True)
        self._sensor_cb.setChecked(enabled)
        self._sensor_cb.blockSignals(False)

    def set_threshold(self, rh: int):
        self._threshold_spin.blockSignals(True)
        self._threshold_spin.setValue(rh)
        self._threshold_spin.blockSignals(False)

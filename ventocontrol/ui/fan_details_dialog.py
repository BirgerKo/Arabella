"""FanDetailsDialog — non-modal detail view for a single fan."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QGroupBox, QHBoxLayout, QLabel,
    QMenu, QPushButton, QVBoxLayout,
)

from blauberg_vento.models import DeviceState
from ventocontrol.scenarios import ScenarioStore
from ventocontrol.widgets.humidity_widget import HumidityWidget
from ventocontrol.widgets.rpm_display import RPMDisplay


class FanDetailsDialog(QDialog):
    """Shows boost, humidity, RPM, schedule and scenario controls for one fan."""

    boost_changed             = Signal(bool)
    hum_sensor_changed        = Signal(int)
    hum_threshold_changed     = Signal(int)
    schedule_enable_changed   = Signal(bool)
    schedule_period_changed   = Signal(int, int, int, int, int)
    schedule_edit_requested   = Signal()
    sync_rtc                  = Signal()
    save_scenario_requested   = Signal()
    add_to_scenario_requested = Signal(str)

    def __init__(self, title: str, scenarios: ScenarioStore, parent=None):
        super().__init__(parent)
        self._scenarios = scenarios
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addLayout(self._build_boost_row())
        layout.addWidget(self._build_humidity_box())
        layout.addWidget(self._build_rpm_box())
        layout.addWidget(self._build_schedule_box())
        layout.addWidget(self._build_scenario_btn())
        layout.addStretch()

    def _build_boost_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Boost:"))
        self._boost_btn = QPushButton("OFF")
        self._boost_btn.setCheckable(True)
        self._boost_btn.setObjectName("BoostBtn")
        self._boost_btn.clicked.connect(self._on_boost_clicked)
        row.addWidget(self._boost_btn)
        row.addStretch()
        return row

    def _build_humidity_box(self) -> QGroupBox:
        box = QGroupBox("Humidity")
        layout = QVBoxLayout(box)
        self._hum_widget = HumidityWidget()
        self._hum_widget.sensor_toggled.connect(self.hum_sensor_changed)
        self._hum_widget.threshold_changed.connect(self.hum_threshold_changed)
        layout.addWidget(self._hum_widget)
        return box

    def _build_rpm_box(self) -> QGroupBox:
        box = QGroupBox("Fan Speed")
        row = QHBoxLayout(box)
        self._fan1 = RPMDisplay("Fan 1")
        self._fan2 = RPMDisplay("Fan 2")
        row.addWidget(self._fan1)
        row.addWidget(self._fan2)
        return box

    def _build_schedule_box(self) -> QGroupBox:
        box = QGroupBox("Schedule")
        layout = QVBoxLayout(box)

        en_row = QHBoxLayout()
        en_row.addWidget(QLabel("Weekly schedule:"))
        self._sched_en_btn = QPushButton("OFF")
        self._sched_en_btn.setCheckable(True)
        self._sched_en_btn.setObjectName("ScheduleEnBtn")
        self._sched_en_btn.clicked.connect(self._on_schedule_enable_clicked)
        en_row.addWidget(self._sched_en_btn)
        en_row.addStretch()
        layout.addLayout(en_row)

        btns_row = QHBoxLayout()
        self._sched_edit_btn = QPushButton("Edit Schedule…")
        self._sched_edit_btn.setObjectName("ScheduleEditBtn")
        self._sched_edit_btn.clicked.connect(self._on_schedule_edit_clicked)
        btns_row.addWidget(self._sched_edit_btn)

        self._sync_rtc_btn = QPushButton("Sync RTC")
        self._sync_rtc_btn.setObjectName("SyncRtcBtn")
        self._sync_rtc_btn.setToolTip("Synchronise the device clock to this computer's time")
        self._sync_rtc_btn.clicked.connect(self.sync_rtc)
        btns_row.addWidget(self._sync_rtc_btn)

        layout.addLayout(btns_row)
        return box

    def _build_scenario_btn(self) -> QPushButton:
        self._scenario_btn = QPushButton("Scenario")
        self._scenario_btn.setObjectName("SaveScenarioBtn")
        self._scenario_btn.clicked.connect(self._on_scenario_btn_clicked)
        return self._scenario_btn

    # ------------------------------------------------------------------
    # Slots — user actions
    # ------------------------------------------------------------------

    def _on_boost_clicked(self) -> None:
        on = self._boost_btn.isChecked()
        self._boost_btn.setText("ON" if on else "OFF")
        self.boost_changed.emit(on)

    def _on_schedule_enable_clicked(self) -> None:
        enabled = self._sched_en_btn.isChecked()
        self._sched_en_btn.setText("ON" if enabled else "OFF")
        self.schedule_enable_changed.emit(enabled)

    def _on_schedule_edit_clicked(self) -> None:
        self.schedule_edit_requested.emit()

    def _on_scenario_btn_clicked(self) -> None:
        menu = QMenu(self)
        new_act = menu.addAction("Create new scenario…")
        new_act.triggered.connect(self.save_scenario_requested)
        scenarios = self._scenarios.get_scenarios()
        if scenarios:
            menu.addSeparator()
            add_sub = menu.addMenu("Add to existing…")
            for s in scenarios:
                act = add_sub.addAction(s.name)
                act.triggered.connect(
                    lambda checked=False, name=s.name:
                        self.add_to_scenario_requested.emit(name)
                )
        btn = self._scenario_btn
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, state: DeviceState) -> None:
        """Update all detail widgets from the latest device state."""
        if state.boost_active is not None:
            self._boost_btn.setChecked(state.boost_active)
            self._boost_btn.setText("ON" if state.boost_active else "OFF")

        self._fan1.set_rpm(state.fan1_rpm)
        self._fan2.set_rpm(state.fan2_rpm)

        self._hum_widget.set_humidity(state.current_humidity)
        if state.humidity_sensor is not None:
            self._hum_widget.set_sensor_enabled(bool(state.humidity_sensor))
        if state.humidity_threshold is not None:
            self._hum_widget.set_threshold(state.humidity_threshold)

        if state.weekly_schedule_enabled is not None:
            self._sched_en_btn.setChecked(state.weekly_schedule_enabled)
            self._sched_en_btn.setText(
                "ON" if state.weekly_schedule_enabled else "OFF"
            )

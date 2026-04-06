"""MainWindow — the fan control dashboard."""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPushButton,
    QStatusBar, QVBoxLayout, QWidget,
)

from blauberg_vento.models import DeviceState
from ventocontrol.app import ACCENT, BORDER, TEXT, TEXT2
from ventocontrol.controllers.device_worker import DeviceWorker
from ventocontrol.history import DeviceHistory
from ventocontrol.registry import WindowRegistry
from ventocontrol.scenarios import (
    FanSettings, ScenarioEntry, ScenarioSettings, ScenarioStore,
)
from ventocontrol.controllers.poller import Poller
from ventocontrol.ui.connect_dialog import ConnectDialog
from ventocontrol.ui.fan_details_dialog import FanDetailsDialog
from ventocontrol.ui.rename_dialog import RenameDialog
from ventocontrol.ui.schedule_dialog import ScheduleDialog
from ventocontrol.ui.scenario_dialog import (
    ManageScenariosDialog, SaveScenarioDialog,
)
from ventocontrol.widgets.mode_selector import ModeSelector
from ventocontrol.widgets.power_button import PowerButton
from ventocontrol.widgets.speed_control import SpeedControl
from ventocontrol.widgets.status_led import StatusLED

# Inline styles for quick-scenario buttons
_QS_ASSIGNED = (
    f"QPushButton#QuickScenarioBtn {{"
    f"color:{TEXT}; border-style:solid; border-color:{ACCENT};}}"
)
_QS_UNASSIGNED = (
    f"QPushButton#QuickScenarioBtn {{"
    f"color:{TEXT2}; border-style:dashed; border-color:{BORDER};}}"
)


def _schedule_btn_text(enabled: bool) -> str:
    return f"Schedule\n{'ON' if enabled else 'OFF'}"


class MainWindow(QMainWindow):
    # ── Command signals (emitted on main thread, received on worker thread) ──
    _sig_connect        = Signal(str, str, str)
    _sig_poll           = Signal()
    _sig_set_power      = Signal(bool)
    _sig_set_speed      = Signal(int)
    _sig_set_manual_spd = Signal(int)
    _sig_set_mode       = Signal(int)
    _sig_set_boost         = Signal(bool)
    _sig_set_hum_sensor    = Signal(int)
    _sig_set_hum_thresh    = Signal(int)
    _sig_set_schedule_en   = Signal(bool)
    _sig_get_schedule      = Signal()

    def __init__(
        self,
        host: str = "",
        device_id: str = "",
        password: str = "",
        history:  DeviceHistory  | None = None,
        registry: WindowRegistry | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("VentoControl")
        self.setMinimumSize(380, 460)

        self._host              = host
        self._password          = password
        self._history           = history
        self._registry          = registry
        self._current_device_id = ""
        self._last_state:    Optional[DeviceState] = None
        self._last_poll_time: Optional[float]      = None
        self._child_windows: list[MainWindow]      = []

        # Global scenario store (shared across all windows via same file)
        self._scenarios      = ScenarioStore()
        # Quick-slot buttons — built in _build_ui
        self._quick_btns: list[QPushButton]          = []
        self._fan_details_dlg: Optional[FanDetailsDialog] = None
        self._schedule_dlg:    Optional[ScheduleDialog]   = None

        # Register with the window registry so multi-fan scenarios can find us
        if self._registry is not None:
            self._registry.register(self)

        # ── Worker thread ──
        self._thread = QThread(self)
        self._worker = DeviceWorker()
        self._worker.moveToThread(self._thread)

        # Worker → UI
        self._worker.connected.connect(self._on_connected)
        self._worker.state_updated.connect(self._on_state_updated)
        self._worker.error.connect(self._on_error)
        self._worker.command_done.connect(self._on_command_done)
        self._worker.connection_failed.connect(self._on_connection_failed)

        # UI → Worker
        self._sig_connect.connect(self._worker.do_connect)
        self._sig_poll.connect(self._worker.do_poll)
        self._sig_set_power.connect(self._worker.do_set_power)
        self._sig_set_speed.connect(self._worker.do_set_speed)
        self._sig_set_manual_spd.connect(self._worker.do_set_manual_speed)
        self._sig_set_mode.connect(self._worker.do_set_mode)
        self._sig_set_boost.connect(self._worker.do_set_boost)
        self._sig_set_hum_sensor.connect(self._worker.do_set_humidity_sensor)
        self._sig_set_hum_thresh.connect(self._worker.do_set_humidity_threshold)
        self._sig_set_schedule_en.connect(self._worker.do_set_schedule_enabled)
        self._sig_get_schedule.connect(self._worker.do_get_full_schedule)
        self._worker.schedule_loaded.connect(self._on_schedule_loaded)

        self._thread.start()

        # ── Poller ──
        self._poller = Poller(self._worker)

        # ── Build UI ──
        self._build_ui()
        self._build_status_bar()
        self._build_menu_bar()

        # ── Connect to device ──
        if host:
            self._start_connecting(host)
            self._sig_connect.emit(host, device_id, password)
        else:
            QTimer.singleShot(0, self._open_initial_connect_dialog)

        # Update "last poll" label every second
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._update_poll_age)
        self._tick.start()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Device header row
        device_row = QHBoxLayout()
        self._device_lbl = QLabel("Connecting…")
        self._device_lbl.setObjectName("DeviceHeader")
        device_row.addWidget(self._device_lbl)
        device_row.addStretch()
        self._details_btn = QPushButton("Details…")
        self._details_btn.setObjectName("DetailsBtn")
        self._details_btn.setToolTip(
            "Show fan details: boost, humidity, RPM, schedule, scenarios"
        )
        self._details_btn.setEnabled(False)
        self._details_btn.clicked.connect(self._open_fan_details)
        device_row.addWidget(self._details_btn)
        self._switch_btn = QPushButton("Switch…")
        self._switch_btn.setObjectName("SwitchBtn")
        self._switch_btn.setToolTip("Connect to a different device")
        self._switch_btn.clicked.connect(self._switch_device)
        device_row.addWidget(self._switch_btn)
        root.addLayout(device_row)

        self._power_btn = PowerButton()
        self._power_btn.toggled_power.connect(self._on_power_toggled)
        root.addWidget(self._power_btn, 0, Qt.AlignmentFlag.AlignLeft)

        speed_box = QGroupBox("Speed")
        speed_layout = QVBoxLayout(speed_box)
        self._speed_ctrl = SpeedControl()
        self._speed_ctrl.speed_changed.connect(self._on_speed_changed)
        self._speed_ctrl.manual_speed_changed.connect(self._on_manual_speed_changed)
        speed_layout.addWidget(self._speed_ctrl)
        root.addWidget(speed_box)

        # Mode group — mode selector + schedule on/off toggle
        mode_box = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_box)
        self._mode_sel = ModeSelector()
        self._mode_sel.mode_changed.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_sel)

        self._sched_en_btn = QPushButton(_schedule_btn_text(False))
        self._sched_en_btn.setCheckable(True)
        self._sched_en_btn.setObjectName("ScheduleEnBtn")
        self._sched_en_btn.setEnabled(False)
        self._sched_en_btn.clicked.connect(self._on_schedule_enable_clicked)
        mode_layout.addWidget(self._sched_en_btn)
        root.addWidget(mode_box)

        # Quick scenarios — separate group below Mode
        quick_box = QGroupBox("Quick Scenarios")
        quick_layout = QHBoxLayout(quick_box)
        quick_layout.setSpacing(4)
        self._quick_btns = []
        for i in range(3):
            btn = QPushButton(f"Q{i + 1}")
            btn.setObjectName("QuickScenarioBtn")
            btn.setToolTip("Right-click to assign a scenario")
            btn.setEnabled(False)
            btn.setStyleSheet(_QS_UNASSIGNED)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_quick_clicked(idx))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, idx=i: self._on_quick_context(idx, pos)
            )
            self._quick_btns.append(btn)
            quick_layout.addWidget(btn)
        root.addWidget(quick_box)

        # Status group box
        stat_box = QGroupBox("Status")
        stat_layout = QVBoxLayout(stat_box)

        conn_row = QHBoxLayout()
        self._conn_led = StatusLED("grey")
        conn_row.addWidget(self._conn_led)
        self._conn_lbl = QLabel("Not connected")
        conn_row.addWidget(self._conn_lbl)
        conn_row.addStretch()
        stat_layout.addLayout(conn_row)

        alarm_row = QHBoxLayout()
        self._alarm_led = StatusLED("grey")
        alarm_row.addWidget(self._alarm_led)
        self._alarm_lbl = QLabel("—")
        alarm_row.addWidget(self._alarm_lbl)
        alarm_row.addStretch()
        stat_layout.addLayout(alarm_row)

        root.addWidget(stat_box)
        root.addStretch()

    def _build_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._sb_conn_led = StatusLED("grey", 10)
        self._sb_id_lbl   = QLabel("—")
        self._sb_ip_lbl   = QLabel(self._host)
        self._sb_poll_lbl = QLabel("—")
        sb.addPermanentWidget(self._sb_conn_led)
        sb.addPermanentWidget(self._sb_id_lbl)
        sb.addPermanentWidget(QLabel("·"))
        sb.addPermanentWidget(self._sb_ip_lbl)
        sb.addPermanentWidget(QLabel("|"))
        sb.addPermanentWidget(self._sb_poll_lbl)

    def _build_menu_bar(self):
        dev_menu = self.menuBar().addMenu("Device")

        act_switch = QAction("Switch Device…", self)
        act_switch.setShortcut("Ctrl+D")
        act_switch.triggered.connect(self._switch_device)
        dev_menu.addAction(act_switch)

        act_new = QAction("Open in New Window…", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._open_new_window)
        dev_menu.addAction(act_new)

        dev_menu.addSeparator()

        self._act_rename = QAction("Rename Device…", self)
        self._act_rename.setShortcut("Ctrl+R")
        self._act_rename.setEnabled(False)
        self._act_rename.triggered.connect(self._rename_device)
        dev_menu.addAction(self._act_rename)

        # Scenarios menu — populated dynamically
        self._scenarios_menu = self.menuBar().addMenu("Scenarios")
        self._rebuild_scenarios_menu()

    # ------------------------------------------------------------------
    # Slots — device state
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_connected(self, state: DeviceState):
        for w in self._control_widgets():
            w.setEnabled(True)
        self._act_rename.setEnabled(True)
        self._set_status("Connected", "green")
        self._poller.start()
        self._apply_state(state)
        # Record in history
        if self._history is not None:
            self._history.record(
                device_id=state.device_id,
                ip=state.ip,
                unit_type_name=state.unit_type_name,
                password=self._password,
            )
        # Refresh scenario UI now that device_id is known
        self._rebuild_scenarios_menu()
        self._refresh_quick_buttons()

    @Slot(object)
    def _on_state_updated(self, state: DeviceState):
        self._last_poll_time = time.monotonic()
        self._apply_state(state)

    @Slot(str)
    def _on_error(self, msg: str):
        self.statusBar().showMessage(f"⚠  {msg}", 6000)

    @Slot()
    def _on_command_done(self):
        self._sig_poll.emit()

    @Slot(str)
    def _on_connection_failed(self, _msg: str):
        """Handle a failed connection attempt.

        Resets the window to an unconnected state and shows a clear
        message so the user knows they can use Switch… to retry.
        """
        self._go_to_unconnected()
        self._device_lbl.setText("Device not found or connected yet…")
        self.statusBar().showMessage("Connection failed — use Switch… to try again", 0)

    # ------------------------------------------------------------------
    # State → UI
    # ------------------------------------------------------------------

    def _apply_state(self, s: DeviceState):
        self._last_state        = s
        self._current_device_id = s.device_id
        display_name = self._get_display_name(s)
        self._device_lbl.setText(display_name)
        self._device_lbl.setToolTip(s.ip or self._host)
        self.setWindowTitle(f"VentoControl — {display_name}")
        self._sb_id_lbl.setText(s.device_id or "—")
        self._sb_ip_lbl.setText(s.ip or self._host)

        if s.power is not None:
            self._power_btn.set_on(s.power)

        if s.speed is not None:
            self._speed_ctrl.set_speed(s.speed)
        if s.manual_speed is not None:
            self._speed_ctrl.set_manual_value(s.manual_speed)

        if s.operation_mode is not None:
            self._mode_sel.set_mode(s.operation_mode)

        if s.weekly_schedule_enabled is not None:
            self._sched_en_btn.setChecked(s.weekly_schedule_enabled)
            self._sched_en_btn.setText(_schedule_btn_text(s.weekly_schedule_enabled))

        if self._fan_details_dlg is not None and self._fan_details_dlg.isVisible():
            self._fan_details_dlg.refresh(s)

        if s.alarm_status == 0:
            self._alarm_led.set_ok();      self._alarm_lbl.setText("OK")
        elif s.alarm_status == 1:
            self._alarm_led.set_error();   self._alarm_lbl.setText("ALARM")
        elif s.alarm_status == 2:
            self._alarm_led.set_warning(); self._alarm_lbl.setText("Warning")
        else:
            self._alarm_led.set_inactive(); self._alarm_lbl.setText("—")

    def _set_status(self, text: str, colour: str):
        self._conn_led.set_colour(colour)
        self._conn_lbl.setText(text)
        self._sb_conn_led.set_colour(colour)

    def _update_poll_age(self):
        if self._last_poll_time is None:
            self._sb_poll_lbl.setText("No data yet")
        else:
            age = int(time.monotonic() - self._last_poll_time)
            self._sb_poll_lbl.setText(f"Last poll: {age}s ago")

    # ------------------------------------------------------------------
    # Slots — user control actions
    # ------------------------------------------------------------------

    def _on_power_toggled(self, on: bool):
        self._sig_set_power.emit(on)

    def _on_speed_changed(self, speed: int):
        self._sig_set_speed.emit(speed)

    def _on_manual_speed_changed(self, value: int):
        self._sig_set_manual_spd.emit(value)

    def _on_mode_changed(self, mode: int):
        self._sig_set_mode.emit(mode)

    def _on_schedule_enable_clicked(self) -> None:
        enabled = self._sched_en_btn.isChecked()
        self._sched_en_btn.setText(_schedule_btn_text(enabled))
        self._sig_set_schedule_en.emit(enabled)

    def _open_fan_details(self) -> None:
        """Open (or bring to front) the fan details dialog."""
        if self._fan_details_dlg is not None and self._fan_details_dlg.isVisible():
            self._fan_details_dlg.raise_()
            self._fan_details_dlg.activateWindow()
            return

        display_name = (
            self._get_display_name(self._last_state)
            if self._last_state else "Fan Details"
        )
        dlg = FanDetailsDialog(
            title=display_name,
            scenarios=self._scenarios,
            parent=self,
        )
        dlg.boost_changed.connect(self._worker.do_set_boost)
        dlg.hum_sensor_changed.connect(self._worker.do_set_humidity_sensor)
        dlg.hum_threshold_changed.connect(self._worker.do_set_humidity_threshold)
        dlg.schedule_enable_changed.connect(self._worker.do_set_schedule_enabled)
        dlg.schedule_period_changed.connect(self._worker.do_set_schedule_period)
        dlg.schedule_edit_requested.connect(self._on_schedule_edit_requested)
        dlg.sync_rtc.connect(self._worker.do_sync_rtc)
        dlg.save_scenario_requested.connect(self._save_scenario)
        dlg.add_to_scenario_requested.connect(self._add_to_scenario)
        dlg.finished.connect(self._on_fan_details_closed)

        if self._last_state is not None:
            dlg.refresh(self._last_state)

        self._fan_details_dlg = dlg
        dlg.show()

    def _on_fan_details_closed(self) -> None:
        """Clean up after the fan details dialog closes."""
        self._fan_details_dlg = None

    def _on_schedule_edit_requested(self) -> None:
        """Open the schedule editor and trigger a full-schedule read from the device."""
        if self._schedule_dlg is not None and self._schedule_dlg.isVisible():
            self._schedule_dlg.raise_()
            self._schedule_dlg.activateWindow()
            return
        dlg = ScheduleDialog(parent=self)
        dlg.period_changed.connect(self._worker.do_set_schedule_period)
        dlg.finished.connect(self._on_schedule_dialog_closed)
        self._schedule_dlg = dlg
        dlg.show()
        self._sig_get_schedule.emit()

    def _on_schedule_dialog_closed(self) -> None:
        self._schedule_dlg = None

    @Slot(object)
    def _on_schedule_loaded(self, schedule: dict) -> None:
        """Receive full schedule (or partial on error) and populate the open editor.

        Always calls load() so the dialog leaves the loading state even when
        the device read failed — the user can still edit from empty defaults.
        """
        if self._schedule_dlg is not None and self._schedule_dlg.isVisible():
            self._schedule_dlg.load(schedule)

    # ------------------------------------------------------------------
    # Scenario — apply settings to this window
    # ------------------------------------------------------------------

    def _do_apply_settings(self, s: ScenarioSettings) -> None:
        """Emit command signals for each non-None field in *s*."""
        if s.power is not None:
            self._sig_set_power.emit(s.power)
        if s.operation_mode is not None:
            self._sig_set_mode.emit(s.operation_mode)
        if s.speed is not None:
            self._sig_set_speed.emit(s.speed)
            if s.speed == 255 and s.manual_speed is not None:
                self._sig_set_manual_spd.emit(s.manual_speed)
        if s.boost_active is not None:
            self._sig_set_boost.emit(s.boost_active)
        if s.humidity_sensor is not None:
            self._sig_set_hum_sensor.emit(s.humidity_sensor)
        if s.humidity_threshold is not None:
            self._sig_set_hum_thresh.emit(s.humidity_threshold)

    # ------------------------------------------------------------------
    # Scenario — activate
    # ------------------------------------------------------------------

    def _activate_scenario(self, entry: ScenarioEntry) -> None:
        """Dispatch each fan's settings to the correct window via the registry."""
        applied: list[str] = []
        skipped: list[str] = []

        for fan in entry.fans:
            # Try to find the window via the registry first
            win = self._registry.get_for_device(fan.device_id) \
                if self._registry is not None else None

            # Fallback: apply to self if this window matches the device_id
            if win is None and fan.device_id == self._current_device_id:
                win = self

            if win is not None:
                win._do_apply_settings(fan.settings)
                applied.append(fan.device_id)
            else:
                skipped.append(fan.device_id)

        msg = f'Scenario "{entry.name}" applied.'
        if skipped:
            msg += f"  ({len(skipped)} fan(s) not connected)"
        self.statusBar().showMessage(msg, 3000)

    # ------------------------------------------------------------------
    # Scenario — save
    # ------------------------------------------------------------------

    def _on_scenario_btn_clicked(self) -> None:
        """Show a menu to create a new scenario or add to an existing one."""
        menu = QMenu(self)
        new_act = menu.addAction("Create new scenario…")
        new_act.triggered.connect(self._save_scenario)
        scenarios = self._scenarios.get_scenarios()
        if scenarios:
            menu.addSeparator()
            add_sub = menu.addMenu("Add to existing…")
            for s in scenarios:
                act = add_sub.addAction(s.name)
                act.triggered.connect(
                    lambda checked=False, name=s.name: self._add_to_scenario(name)
                )
        btn = self._save_scenario_btn
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _add_to_scenario(self, name: str) -> None:
        """Add or update the current fan's state in an existing scenario."""
        if self._last_state is None or not self._current_device_id:
            return
        scenarios = self._scenarios.get_scenarios()
        target = next((s for s in scenarios if s.name == name), None)
        if target is None:
            return
        s = self._last_state
        new_fan = FanSettings(
            device_id=self._current_device_id,
            settings=ScenarioSettings(
                power=s.power,
                speed=s.speed,
                manual_speed=s.manual_speed,
                operation_mode=s.operation_mode,
                boost_active=s.boost_active,
                humidity_sensor=s.humidity_sensor,
                humidity_threshold=s.humidity_threshold,
            ),
        )
        updated_fans = [f for f in target.fans if f.device_id != self._current_device_id]
        updated_fans.append(new_fan)
        self._scenarios.save_scenario(ScenarioEntry(name=target.name, fans=updated_fans))
        self._rebuild_scenarios_menu()
        self._refresh_quick_buttons()
        self.statusBar().showMessage(f'Added to scenario "{name}".', 3000)

    def _save_scenario(self) -> None:
        """Capture state from all connected windows, prompt for a name, persist."""
        if self._last_state is None or not self._current_device_id:
            return

        # Collect FanSettings from every connected window (including self)
        all_fans:    list[FanSettings]    = []
        device_labels: dict[str, str]    = {}

        windows_to_capture = (
            self._registry.all_connected
            if self._registry is not None
            else []
        )
        # Ensure self is always included
        seen_ids: set[str] = set()
        for win in windows_to_capture:
            if win._last_state is None:
                continue
            s   = win._last_state
            did = win._current_device_id
            if did in seen_ids:
                continue
            seen_ids.add(did)
            all_fans.append(FanSettings(
                device_id=did,
                settings=ScenarioSettings(
                    power=s.power,
                    speed=s.speed,
                    manual_speed=s.manual_speed,
                    operation_mode=s.operation_mode,
                    boost_active=s.boost_active,
                    humidity_sensor=s.humidity_sensor,
                    humidity_threshold=s.humidity_threshold,
                ),
            ))
            device_labels[did] = self._get_display_name(s) \
                if win is self else win._get_display_name(s)

        # Fallback: registry not set or empty — use self
        if not all_fans and self._last_state is not None:
            s = self._last_state
            all_fans.append(FanSettings(
                device_id=self._current_device_id,
                settings=ScenarioSettings(
                    power=s.power,
                    speed=s.speed,
                    manual_speed=s.manual_speed,
                    operation_mode=s.operation_mode,
                    boost_active=s.boost_active,
                    humidity_sensor=s.humidity_sensor,
                    humidity_threshold=s.humidity_threshold,
                ),
            ))
            device_labels[self._current_device_id] = self._get_display_name(s)

        existing = [e.name for e in self._scenarios.get_scenarios()]
        dlg = SaveScenarioDialog(
            fan_settings=all_fans,
            existing_names=existing,
            device_labels=device_labels,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        entry = dlg.scenario()
        self._scenarios.save_scenario(entry)
        self._rebuild_scenarios_menu()
        self._refresh_quick_buttons()
        self.statusBar().showMessage(f'Scenario "{entry.name}" saved.', 3000)

    # ------------------------------------------------------------------
    # Scenario — manage
    # ------------------------------------------------------------------

    def _manage_scenarios(self) -> None:
        dlg = ManageScenariosDialog(
            store=self._scenarios,
            device_id=self._current_device_id,
            registry=self._registry,
            history=self._history,
            parent=self,
        )
        dlg.exec()
        self._rebuild_scenarios_menu()
        self._refresh_quick_buttons()

    # ------------------------------------------------------------------
    # Scenario — menu rebuild
    # ------------------------------------------------------------------

    def _rebuild_scenarios_menu(self) -> None:
        """Clear and repopulate the Scenarios menu."""
        menu = self._scenarios_menu
        menu.clear()

        act_save = QAction("Save Scenario…", self)
        act_save.setEnabled(self._last_state is not None)
        act_save.triggered.connect(self._save_scenario)
        menu.addAction(act_save)

        act_manage = QAction("Manage Scenarios…", self)
        act_manage.triggered.connect(self._manage_scenarios)
        menu.addAction(act_manage)

        scenarios = self._scenarios.get_scenarios()
        if not scenarios:
            return

        menu.addSeparator()
        for entry in scenarios:
            act = QAction(entry.name, self)
            act.triggered.connect(
                lambda checked=False, e=entry: self._activate_scenario(e)
            )
            menu.addAction(act)

    # ------------------------------------------------------------------
    # Quick-scenario buttons
    # ------------------------------------------------------------------

    def _refresh_quick_buttons(self) -> None:
        """Update label, tooltip, enabled state, and style of all 3 quick buttons."""
        if not self._current_device_id:
            return
        slots     = self._scenarios.get_quick_slots(self._current_device_id)
        entry_map = {e.name: e for e in self._scenarios.get_scenarios()}

        for i, btn in enumerate(self._quick_btns):
            slot_name = slots[i] if i < len(slots) else None

            if slot_name is not None and slot_name in entry_map:
                label = slot_name[:12] + "…" if len(slot_name) > 12 else slot_name
                btn.setText(label)
                btn.setToolTip(f"Activate: {slot_name}\nRight-click to change")
                btn.setEnabled(True)
                btn.setStyleSheet(_QS_ASSIGNED)
            elif slot_name is not None:
                btn.setText("(missing)")
                btn.setToolTip(f'"{slot_name}" was deleted — right-click to reassign')
                btn.setEnabled(False)
                btn.setStyleSheet(_QS_UNASSIGNED)
            else:
                btn.setText(f"Q{i + 1}")
                btn.setToolTip("Right-click to assign a scenario")
                btn.setEnabled(False)
                btn.setStyleSheet(_QS_UNASSIGNED)

    def _on_quick_clicked(self, index: int) -> None:
        """Activate the scenario assigned to quick slot *index*."""
        if not self._current_device_id:
            return
        slots = self._scenarios.get_quick_slots(self._current_device_id)
        if index >= len(slots) or slots[index] is None:
            return
        entry_map = {e.name: e for e in self._scenarios.get_scenarios()}
        entry = entry_map.get(slots[index])
        if entry:
            self._activate_scenario(entry)

    def _on_quick_context(self, index: int, pos) -> None:
        """Right-click context menu to assign or clear a quick slot."""
        if not self._current_device_id:
            return
        scenarios    = self._scenarios.get_scenarios()
        slots        = self._scenarios.get_quick_slots(self._current_device_id)
        current_asgn = slots[index] if index < len(slots) else None

        menu = QMenu(self)

        if scenarios:
            hdr = QAction("Assign scenario:", self)
            hdr.setEnabled(False)
            menu.addAction(hdr)
            for entry in scenarios:
                act = QAction(entry.name, self)
                act.setCheckable(True)
                act.setChecked(entry.name == current_asgn)
                act.triggered.connect(
                    lambda checked=False, n=entry.name, idx=index:
                        self._assign_quick_slot(idx, n)
                )
                menu.addAction(act)
        else:
            no_act = QAction("No scenarios saved yet", self)
            no_act.setEnabled(False)
            menu.addAction(no_act)

        if current_asgn is not None:
            menu.addSeparator()
            clear_act = QAction("Clear slot", self)
            clear_act.triggered.connect(
                lambda checked=False, idx=index: self._assign_quick_slot(idx, None)
            )
            menu.addAction(clear_act)

        btn = self._quick_btns[index]
        menu.exec(btn.mapToGlobal(pos))

    def _assign_quick_slot(self, index: int, name: Optional[str]) -> None:
        slots        = self._scenarios.get_quick_slots(self._current_device_id)
        slots[index] = name
        self._scenarios.set_quick_slots(self._current_device_id, slots)
        self._refresh_quick_buttons()

    # ------------------------------------------------------------------
    # Device switching / naming
    # ------------------------------------------------------------------

    def _control_widgets(self):
        """Return the interactive control widgets (used for enable/disable)."""
        return (self._power_btn, self._speed_ctrl, self._mode_sel,
                self._sched_en_btn, self._details_btn)

    def _get_display_name(self, state: DeviceState) -> str:
        """Return the user-set name if available, otherwise the unit type name."""
        if self._history and state.device_id:
            entry = next(
                (e for e in self._history.entries if e.device_id == state.device_id),
                None,
            )
            if entry and entry.name:
                return entry.name
        return state.unit_type_name or "Vento Fan"

    def _rename_device(self) -> None:
        """Open the rename dialog for the currently connected device."""
        if not self._history or not self._current_device_id:
            return
        entry = next(
            (e for e in self._history.entries if e.device_id == self._current_device_id),
            None,
        )
        dlg = RenameDialog(current_name=entry.name if entry else "", parent=self)
        if dlg.exec() != RenameDialog.DialogCode.Accepted:
            return
        new_name = dlg.name()
        self._history.rename(self._current_device_id, new_name)
        display_name = new_name or (entry.unit_type_name if entry else "Vento Fan")
        self._device_lbl.setText(display_name)
        self.setWindowTitle(f"VentoControl — {display_name}")

    def _go_to_unconnected(self) -> None:
        """Reset the window to an unconnected state with no fan displayed."""
        self._poller.stop()
        for w in self._control_widgets():
            w.setEnabled(False)
        self._act_rename.setEnabled(False)
        for btn in self._quick_btns:
            btn.setEnabled(False)
        self._set_status("No fan connected", "grey")
        self.setWindowTitle("VentoControl")
        self._device_lbl.setText("No fan connected")
        self._sb_id_lbl.setText("—")
        self._sb_ip_lbl.setText("—")
        self._last_poll_time = None
        self._current_device_id = ""

    def _start_connecting(self, ip: str) -> None:
        """Grey out controls and show an amber 'Connecting' status."""
        for w in self._control_widgets():
            w.setEnabled(False)
        self._act_rename.setEnabled(False)
        for btn in self._quick_btns:
            btn.setEnabled(False)
        self._set_status("Connecting…", "amber")
        self.setWindowTitle("VentoControl — Connecting…")
        self._sb_id_lbl.setText("—")
        self._sb_ip_lbl.setText(ip)
        self._last_poll_time = None

    def _open_initial_connect_dialog(self) -> None:
        """Auto-open connect dialog on first launch when no fan is pre-selected."""
        dlg = ConnectDialog(self, history=self._history)
        result = dlg.exec()
        if result == ConnectDialog.DialogCode.Accepted:
            host, device_id, password = dlg.connection_params()
        elif self._history and self._history.last_used:
            entry = self._history.last_used
            host, device_id, password = entry.ip, entry.device_id, entry.password
        else:
            self.close()
            return
        self._host = host
        self._password = password
        self._start_connecting(host)
        self._sig_connect.emit(host, device_id, password)

    def _switch_device(self) -> None:
        """Show the connect dialog and, if accepted, reconnect in-place."""
        self._poller.stop()
        dlg = ConnectDialog(self, history=self._history)
        if dlg.exec() != ConnectDialog.DialogCode.Accepted:
            if not self._history or not self._history.last_used:
                self._go_to_unconnected()
                self._open_initial_connect_dialog()
            else:
                self._poller.start()
            return
        host, device_id, password = dlg.connection_params()
        self._host     = host
        self._password = password
        self._start_connecting(host)
        self._sig_connect.emit(host, device_id, password)

    def _open_new_window(self) -> None:
        """Open an independent dashboard for a different device."""
        dlg = ConnectDialog(self, history=self._history)
        if dlg.exec() != ConnectDialog.DialogCode.Accepted:
            return
        host, device_id, password = dlg.connection_params()
        win = MainWindow(
            host=host,
            device_id=device_id,
            password=password,
            history=self._history,
            registry=self._registry,
        )
        self._child_windows.append(win)
        win.show()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._registry is not None:
            self._registry.unregister(self)
        self._poller.stop()
        self._tick.stop()
        self._thread.quit()
        self._thread.wait(3000)
        super().closeEvent(event)

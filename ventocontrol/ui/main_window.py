"""MainWindow — the fan control dashboard."""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
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
from ventocontrol.ui.connect_dialog import ConnectDialog
from ventocontrol.ui.rename_dialog import RenameDialog
from ventocontrol.ui.scenario_dialog import (
    ManageScenariosDialog, SaveScenarioDialog,
)
from ventocontrol.controllers.poller import Poller
from ventocontrol.widgets.humidity_widget import HumidityWidget
from ventocontrol.widgets.mode_selector import ModeSelector
from ventocontrol.widgets.power_button import PowerButton
from ventocontrol.widgets.rpm_display import RPMDisplay
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


class MainWindow(QMainWindow):
    # ── Command signals (emitted on main thread, received on worker thread) ──
    _sig_connect        = Signal(str, str, str)
    _sig_poll           = Signal()
    _sig_set_power      = Signal(bool)
    _sig_set_speed      = Signal(int)
    _sig_set_manual_spd = Signal(int)
    _sig_set_mode       = Signal(int)
    _sig_set_boost      = Signal(bool)
    _sig_set_hum_sensor = Signal(int)
    _sig_set_hum_thresh = Signal(int)

    def __init__(
        self,
        host: str,
        device_id: str,
        password: str,
        history:  DeviceHistory  | None = None,
        registry: WindowRegistry | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("VentoControl")
        self.setMinimumSize(680, 460)

        self._host              = host
        self._password          = password
        self._history           = history
        self._registry          = registry
        self._current_device_id = ""
        self._last_state:    Optional[DeviceState] = None
        self._last_poll_time: Optional[float]      = None
        self._child_windows: list[MainWindow]      = []

        # Global scenario store (shared across all windows via same file)
        self._scenarios   = ScenarioStore()
        # Quick-slot buttons — built in _build_ui
        self._quick_btns: list[QPushButton] = []

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

        self._thread.start()

        # ── Poller ──
        self._poller = Poller(self._worker)

        # ── Build UI ──
        self._build_ui()
        self._build_status_bar()
        self._build_menu_bar()

        # ── Connect to device ──
        self._start_connecting(host)
        self._sig_connect.emit(host, device_id, password)

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
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── LEFT COLUMN ──
        left = QVBoxLayout()
        left.setSpacing(12)

        device_row = QHBoxLayout()
        self._device_lbl = QLabel("Connecting…")
        self._device_lbl.setObjectName("DeviceHeader")
        device_row.addWidget(self._device_lbl)
        device_row.addStretch()
        self._switch_btn = QPushButton("Switch…")
        self._switch_btn.setObjectName("SwitchBtn")
        self._switch_btn.setToolTip("Connect to a different device")
        self._switch_btn.clicked.connect(self._switch_device)
        device_row.addWidget(self._switch_btn)
        left.addLayout(device_row)

        self._power_btn = PowerButton()
        self._power_btn.toggled_power.connect(self._on_power_toggled)
        left.addWidget(self._power_btn, 0, Qt.AlignmentFlag.AlignLeft)

        speed_box = QGroupBox("Speed")
        speed_layout = QVBoxLayout(speed_box)
        self._speed_ctrl = SpeedControl()
        self._speed_ctrl.speed_changed.connect(self._on_speed_changed)
        self._speed_ctrl.manual_speed_changed.connect(self._on_manual_speed_changed)
        speed_layout.addWidget(self._speed_ctrl)
        left.addWidget(speed_box)

        # Mode group — includes quick-scenario buttons below the mode selector
        mode_box = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_box)
        self._mode_sel = ModeSelector()
        self._mode_sel.mode_changed.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_sel)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
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
            quick_row.addWidget(btn)
        mode_layout.addLayout(quick_row)
        left.addWidget(mode_box)

        boost_row = QHBoxLayout()
        boost_row.addWidget(QLabel("Boost:"))
        self._boost_btn = QPushButton("OFF")
        self._boost_btn.setCheckable(True)
        self._boost_btn.setObjectName("BoostBtn")
        self._boost_btn.clicked.connect(self._on_boost_clicked)
        boost_row.addWidget(self._boost_btn)
        boost_row.addStretch()
        left.addLayout(boost_row)

        # Save as Scenario button
        self._save_scenario_btn = QPushButton("Save as Scenario…")
        self._save_scenario_btn.setObjectName("SaveScenarioBtn")
        self._save_scenario_btn.setEnabled(False)
        self._save_scenario_btn.clicked.connect(self._save_scenario)
        left.addWidget(self._save_scenario_btn)

        left.addStretch()
        root.addLayout(left, 2)

        # ── DIVIDER ──
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("Divider")
        root.addWidget(line)

        # ── RIGHT COLUMN ──
        right = QVBoxLayout()
        right.setSpacing(12)

        rpm_box = QGroupBox("Fan Speed")
        rpm_row = QHBoxLayout(rpm_box)
        self._fan1 = RPMDisplay("Fan 1")
        self._fan2 = RPMDisplay("Fan 2")
        rpm_row.addWidget(self._fan1)
        rpm_row.addWidget(self._fan2)
        right.addWidget(rpm_box)

        hum_box = QGroupBox("Humidity")
        hum_layout = QVBoxLayout(hum_box)
        self._hum_widget = HumidityWidget()
        self._hum_widget.sensor_toggled.connect(self._on_humidity_sensor)
        self._hum_widget.threshold_changed.connect(self._on_humidity_threshold)
        hum_layout.addWidget(self._hum_widget)
        right.addWidget(hum_box)

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

        right.addWidget(stat_box)
        right.addStretch()
        root.addLayout(right, 3)

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
        self._save_scenario_btn.setEnabled(True)
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

    # ------------------------------------------------------------------
    # State → UI
    # ------------------------------------------------------------------

    def _apply_state(self, s: DeviceState):
        self._last_state        = s
        self._current_device_id = s.device_id
        display_name = self._get_display_name(s)
        self._device_lbl.setText(f"{display_name}  ·  {s.ip}")
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

        if s.boost_active is not None:
            self._boost_btn.setChecked(s.boost_active)
            self._boost_btn.setText("ON" if s.boost_active else "OFF")

        self._fan1.set_rpm(s.fan1_rpm)
        self._fan2.set_rpm(s.fan2_rpm)

        self._hum_widget.set_humidity(s.current_humidity)
        if s.humidity_sensor is not None:
            self._hum_widget.set_sensor_enabled(bool(s.humidity_sensor))
        if s.humidity_threshold is not None:
            self._hum_widget.set_threshold(s.humidity_threshold)

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

    def _on_boost_clicked(self):
        on = self._boost_btn.isChecked()
        self._boost_btn.setText("ON" if on else "OFF")
        self._sig_set_boost.emit(on)

    def _on_humidity_sensor(self, state: int):
        self._sig_set_hum_sensor.emit(state)

    def _on_humidity_threshold(self, rh: int):
        self._sig_set_hum_thresh.emit(rh)

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

        act_save = QAction("Save as Scenario…", self)
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
        return (self._power_btn, self._speed_ctrl,
                self._mode_sel, self._boost_btn, self._hum_widget)

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
        current_ip   = self._sb_ip_lbl.text() or self._host
        self._device_lbl.setText(f"{display_name}  ·  {current_ip}")
        self.setWindowTitle(f"VentoControl — {display_name}")

    def _start_connecting(self, ip: str) -> None:
        """Grey out controls and show an amber 'Connecting' status."""
        for w in self._control_widgets():
            w.setEnabled(False)
        self._act_rename.setEnabled(False)
        self._save_scenario_btn.setEnabled(False)
        for btn in self._quick_btns:
            btn.setEnabled(False)
        self._set_status("Connecting…", "amber")
        self.setWindowTitle("VentoControl — Connecting…")
        self._sb_id_lbl.setText("—")
        self._sb_ip_lbl.setText(ip)
        self._last_poll_time = None

    def _switch_device(self) -> None:
        """Show the connect dialog and, if accepted, reconnect in-place."""
        self._poller.stop()
        dlg = ConnectDialog(self, history=self._history)
        if dlg.exec() != ConnectDialog.DialogCode.Accepted:
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

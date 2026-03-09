"""Scenario dialogs and widgets.

Classes
-------
ScenarioSettingsEditor   — per-fan settings form (checkbox + control per field)
SaveScenarioDialog       — name + fan-picker when saving a new scenario
ManageScenariosDialog    — list all scenarios with per-row Delete buttons
EditScenarioDialog       — full editor: name + fan list + settings editor
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ventocontrol.scenarios import (
    FanSettings, ScenarioEntry, ScenarioSettings, ScenarioStore,
    get_settings_for_device,
)

_NAME_MIN = 1
_NAME_MAX = 30

# Speed preset labels ↔ protocol values
_SPEED_LABELS = ["Speed 1", "Speed 2", "Speed 3", "Manual"]
_SPEED_VALUES = [1, 2, 3, 255]

# Operation-mode labels ↔ protocol values
_MODE_LABELS = ["Ventilation", "Heat Recovery", "Supply"]
_MODE_VALUES = [0, 1, 2]


# ---------------------------------------------------------------------------
# ScenarioSettingsEditor
# ---------------------------------------------------------------------------

class ScenarioSettingsEditor(QWidget):
    """
    Displays [checkbox] [label] [control] rows for every ScenarioSettings field.

    When a checkbox is unchecked the corresponding field returns ``None``
    (= "don't change when activating").  When checked the control is enabled
    and its value is returned.

    Public API::

        editor.load(settings)   # populate from an existing ScenarioSettings
        editor.value()          # → ScenarioSettings reflecting the current UI
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(6)

        # ── Power ──────────────────────────────────────────────────────
        self._cb_power = QCheckBox()
        self._co_power = QComboBox()
        self._co_power.addItems(["ON", "OFF"])
        self._cb_power.toggled.connect(self._co_power.setEnabled)
        self._co_power.setEnabled(False)
        form.addRow("Power:", self._row(self._cb_power, self._co_power))

        # ── Speed ──────────────────────────────────────────────────────
        self._cb_speed  = QCheckBox()
        self._co_speed  = QComboBox()
        self._co_speed.addItems(_SPEED_LABELS)
        self._sp_manual = QSpinBox()
        self._sp_manual.setRange(0, 255)
        self._sp_manual.setToolTip("Manual speed value (0–255)")

        self._cb_speed.toggled.connect(self._co_speed.setEnabled)
        self._cb_speed.toggled.connect(self._on_speed_cb_toggle)
        self._co_speed.currentIndexChanged.connect(self._on_speed_combo_changed)
        self._co_speed.setEnabled(False)
        self._sp_manual.setEnabled(False)

        speed_w = QWidget()
        speed_r = QHBoxLayout(speed_w)
        speed_r.setContentsMargins(0, 0, 0, 0)
        speed_r.setSpacing(4)
        speed_r.addWidget(self._cb_speed)
        speed_r.addWidget(self._co_speed)
        speed_r.addWidget(self._sp_manual)
        form.addRow("Speed:", speed_w)

        # ── Mode ───────────────────────────────────────────────────────
        self._cb_mode = QCheckBox()
        self._co_mode = QComboBox()
        self._co_mode.addItems(_MODE_LABELS)
        self._cb_mode.toggled.connect(self._co_mode.setEnabled)
        self._co_mode.setEnabled(False)
        form.addRow("Mode:", self._row(self._cb_mode, self._co_mode))

        # ── Boost ──────────────────────────────────────────────────────
        self._cb_boost = QCheckBox()
        self._co_boost = QComboBox()
        self._co_boost.addItems(["ON", "OFF"])
        self._cb_boost.toggled.connect(self._co_boost.setEnabled)
        self._co_boost.setEnabled(False)
        form.addRow("Boost:", self._row(self._cb_boost, self._co_boost))

        # ── Humidity sensor ────────────────────────────────────────────
        self._cb_hum_sensor = QCheckBox()
        self._co_hum_sensor = QComboBox()
        self._co_hum_sensor.addItems(["ON", "OFF"])
        self._cb_hum_sensor.toggled.connect(self._co_hum_sensor.setEnabled)
        self._co_hum_sensor.setEnabled(False)
        form.addRow("Humidity sensor:", self._row(self._cb_hum_sensor, self._co_hum_sensor))

        # ── Humidity threshold ─────────────────────────────────────────
        self._cb_hum_thresh = QCheckBox()
        self._sp_hum_thresh = QSpinBox()
        self._sp_hum_thresh.setRange(40, 80)
        self._sp_hum_thresh.setSuffix(" %RH")
        self._cb_hum_thresh.toggled.connect(self._sp_hum_thresh.setEnabled)
        self._sp_hum_thresh.setEnabled(False)
        form.addRow("Humidity threshold:", self._row(self._cb_hum_thresh, self._sp_hum_thresh))

    # ── Public ──────────────────────────────────────────────────────────

    def load(self, settings: ScenarioSettings) -> None:
        """Populate the form from an existing ScenarioSettings object."""
        # Power
        if settings.power is not None:
            self._cb_power.setChecked(True)
            self._co_power.setCurrentIndex(0 if settings.power else 1)
        else:
            self._cb_power.setChecked(False)

        # Speed
        if settings.speed is not None:
            self._cb_speed.setChecked(True)
            idx = _SPEED_VALUES.index(settings.speed) if settings.speed in _SPEED_VALUES else 0
            self._co_speed.setCurrentIndex(idx)
            if settings.speed == 255 and settings.manual_speed is not None:
                self._sp_manual.setValue(settings.manual_speed)
        else:
            self._cb_speed.setChecked(False)

        # Mode
        if settings.operation_mode is not None:
            self._cb_mode.setChecked(True)
            idx = _MODE_VALUES.index(settings.operation_mode) \
                if settings.operation_mode in _MODE_VALUES else 0
            self._co_mode.setCurrentIndex(idx)
        else:
            self._cb_mode.setChecked(False)

        # Boost
        if settings.boost_active is not None:
            self._cb_boost.setChecked(True)
            self._co_boost.setCurrentIndex(0 if settings.boost_active else 1)
        else:
            self._cb_boost.setChecked(False)

        # Humidity sensor
        if settings.humidity_sensor is not None:
            self._cb_hum_sensor.setChecked(True)
            self._co_hum_sensor.setCurrentIndex(0 if settings.humidity_sensor else 1)
        else:
            self._cb_hum_sensor.setChecked(False)

        # Humidity threshold
        if settings.humidity_threshold is not None:
            self._cb_hum_thresh.setChecked(True)
            self._sp_hum_thresh.setValue(settings.humidity_threshold)
        else:
            self._cb_hum_thresh.setChecked(False)

    def value(self) -> ScenarioSettings:
        """Read the current form state and return a ScenarioSettings object."""
        power = speed = manual_speed = operation_mode = None
        boost_active = humidity_sensor = humidity_threshold = None

        if self._cb_power.isChecked():
            power = (self._co_power.currentIndex() == 0)

        if self._cb_speed.isChecked():
            speed = _SPEED_VALUES[self._co_speed.currentIndex()]
            if speed == 255:
                manual_speed = self._sp_manual.value()

        if self._cb_mode.isChecked():
            operation_mode = _MODE_VALUES[self._co_mode.currentIndex()]

        if self._cb_boost.isChecked():
            boost_active = (self._co_boost.currentIndex() == 0)

        if self._cb_hum_sensor.isChecked():
            humidity_sensor = 1 if self._co_hum_sensor.currentIndex() == 0 else 0

        if self._cb_hum_thresh.isChecked():
            humidity_threshold = self._sp_hum_thresh.value()

        return ScenarioSettings(
            power=power,
            speed=speed,
            manual_speed=manual_speed,
            operation_mode=operation_mode,
            boost_active=boost_active,
            humidity_sensor=humidity_sensor,
            humidity_threshold=humidity_threshold,
        )

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _row(cb: QCheckBox, widget: QWidget) -> QWidget:
        """Wrap a [checkbox][widget] pair in a compact QWidget."""
        container = QWidget()
        layout    = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(cb)
        layout.addWidget(widget)
        layout.addStretch()
        return container

    def _on_speed_cb_toggle(self, checked: bool) -> None:
        is_manual = (self._co_speed.currentIndex() == _SPEED_LABELS.index("Manual"))
        self._sp_manual.setEnabled(checked and is_manual)

    def _on_speed_combo_changed(self, index: int) -> None:
        is_manual = (index == _SPEED_LABELS.index("Manual"))
        self._sp_manual.setEnabled(self._cb_speed.isChecked() and is_manual)


# ---------------------------------------------------------------------------
# SaveScenarioDialog
# ---------------------------------------------------------------------------

class SaveScenarioDialog(QDialog):
    """
    Name and save the current fan state as a scenario.

    Supports single-fan and multi-fan saves.  When ``fan_settings`` has more
    than one entry, checkboxes are shown so the user can include/exclude
    individual fans.  At least one fan must remain selected.

    Usage::

        dlg = SaveScenarioDialog(
            fan_settings=[fs1, fs2],
            existing_names=names,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry = dlg.scenario()
    """

    def __init__(
        self,
        fan_settings: list[FanSettings],
        existing_names: list[str],
        device_labels: Optional[dict[str, str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._fan_settings   = fan_settings
        self._existing_names = existing_names
        self._device_labels  = device_labels or {}
        self.setWindowTitle("Save as Scenario")
        self.setMinimumWidth(380)
        self.setModal(True)

        # ── Name input ──────────────────────────────────────────────────
        self._edit = QLineEdit()
        self._edit.setMaxLength(_NAME_MAX)
        self._edit.setPlaceholderText("e.g. Night Mode")
        self._edit.textChanged.connect(self._on_text_changed)

        self._counter = QLabel()
        self._counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._counter.setMinimumWidth(50)

        input_row = QHBoxLayout()
        input_row.addWidget(self._edit, 1)
        input_row.addWidget(self._counter)

        hint = QLabel(f"Name must be {_NAME_MIN}–{_NAME_MAX} characters.")
        hint.setObjectName("HintLabel")

        self._warn = QLabel()
        self._warn.setObjectName("HintLabel")
        self._warn.setVisible(False)

        # ── Fan checkboxes (shown only when >1 fan is available) ────────
        self._fan_checks: list[tuple[QCheckBox, FanSettings]] = []
        self._fan_group: Optional[QGroupBox] = None

        if len(fan_settings) > 1:
            self._fan_group = QGroupBox("Include fans:")
            fan_layout = QVBoxLayout(self._fan_group)
            for fs in fan_settings:
                label = self._label_for(fs.device_id)
                cb    = QCheckBox(label)
                cb.setChecked(True)
                cb.toggled.connect(self._update_ok_btn)
                self._fan_checks.append((cb, fs))
                fan_layout.addWidget(cb)

        # ── Buttons ─────────────────────────────────────────────────────
        self._bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = self._bbox.button(QDialogButtonBox.StandardButton.Save)
        self._bbox.accepted.connect(self.accept)
        self._bbox.rejected.connect(self.reject)

        # ── Layout ──────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Scenario name:"))
        layout.addLayout(input_row)
        layout.addWidget(hint)
        layout.addWidget(self._warn)
        if self._fan_group is not None:
            layout.addWidget(self._fan_group)
        layout.addWidget(self._bbox)

        self._on_text_changed("")

    # ── Public ──────────────────────────────────────────────────────────

    def scenario(self) -> ScenarioEntry:
        """Return the ScenarioEntry to save.  Call only after accept()."""
        if self._fan_checks:
            fans = [fs for cb, fs in self._fan_checks if cb.isChecked()]
        else:
            fans = list(self._fan_settings)
        return ScenarioEntry(name=self._edit.text().strip(), fans=fans)

    # ── Internal ────────────────────────────────────────────────────────

    def _label_for(self, device_id: str) -> str:
        if device_id in self._device_labels:
            return self._device_labels[device_id]
        return f"…{device_id[-8:]}" if len(device_id) > 8 else device_id

    def _on_text_changed(self, text: str) -> None:
        stripped = text.strip()
        n        = len(stripped)
        valid    = _NAME_MIN <= n <= _NAME_MAX

        self._counter.setText(f"{n}\u202f/\u202f{_NAME_MAX}")
        colour = "#6272a4" if n == 0 else ("#50fa7b" if valid else "#ff5555")
        self._counter.setStyleSheet(f"color: {colour}; font-weight: bold;")

        if stripped in self._existing_names:
            self._warn.setText(
                f'\u26a0\ufe0f  "{stripped}" already exists — it will be overwritten.'
            )
            self._warn.setStyleSheet("color: #ffb86c;")
            self._warn.setVisible(True)
        else:
            self._warn.setVisible(False)

        self._update_ok_btn()

    def _update_ok_btn(self) -> None:
        stripped = self._edit.text().strip()
        name_ok  = _NAME_MIN <= len(stripped) <= _NAME_MAX
        fans_ok  = any(cb.isChecked() for cb, _ in self._fan_checks) \
                   if self._fan_checks else True
        self._ok.setEnabled(name_ok and fans_ok)


# ---------------------------------------------------------------------------
# ManageScenariosDialog
# ---------------------------------------------------------------------------

class ManageScenariosDialog(QDialog):
    """
    List all scenarios with per-row Edit, Delete, and Q-slot controls.

    All changes (edit, delete, slot assignment) are applied immediately to
    the store.  The dialog only needs a Close button.

    Usage::

        dlg = ManageScenariosDialog(
            store=store,
            device_id=device_id,
            registry=registry,
            history=history,
            parent=self,
        )
        dlg.exec()
        # caller refreshes menu / quick buttons after close
    """

    def __init__(
        self,
        store:     ScenarioStore,
        device_id: str = "",    # needed for quick-slot management; "" disables combos
        registry  = None,       # WindowRegistry | None — forwarded to EditScenarioDialog
        history   = None,       # DeviceHistory  | None — forwarded to EditScenarioDialog
        parent    = None,
    ):
        super().__init__(parent)
        self._store     = store
        self._device_id = device_id
        self._registry  = registry
        self._history   = history

        self._row_widgets: list[QWidget]        = []
        self._row_combos:  dict[str, QComboBox] = {}

        self.setWindowTitle("Manage Scenarios")
        self.setMinimumWidth(540)
        self.setModal(True)

        # "No scenarios" placeholder
        self._status_lbl = QLabel("No scenarios saved yet.")
        self._status_lbl.setVisible(False)

        # Container for scenario rows
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(4)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(self._status_lbl)
        root.addLayout(self._rows_layout)
        root.addWidget(close_box)

        self._populate()

    # ── Internal — build / rebuild ────────────────────────────────────

    def _populate(self) -> None:
        """Rebuild all scenario rows from the current store state."""
        # Detach and destroy every existing row widget
        for w in self._row_widgets:
            self._rows_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._row_widgets.clear()
        self._row_combos.clear()

        scenarios = self._store.get_scenarios()

        if not scenarios:
            self._status_lbl.setVisible(True)
            return
        self._status_lbl.setVisible(False)

        slots    = self._store.get_quick_slots(self._device_id) if self._device_id else []
        slot_map = {name: idx for idx, name in enumerate(slots) if name is not None}

        for entry in scenarios:
            self._add_row(entry, slot_map.get(entry.name, -1))

    def _add_row(self, entry: ScenarioEntry, slot_idx: int) -> None:
        """Create and append one scenario row to self._rows_layout."""
        row_widget = QWidget()
        row        = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)

        # Name
        name_lbl = QLabel(entry.name)
        name_lbl.setToolTip(entry.name)
        row.addWidget(name_lbl, 1)

        # Fan count (muted)
        n       = len(entry.fans)
        fan_lbl = QLabel(f"{n} fan{'s' if n != 1 else ''}")
        fan_lbl.setStyleSheet("color: #6272a4; font-size: 11px;")
        row.addWidget(fan_lbl)

        # Quick-slot combo
        slot_combo = QComboBox()
        slot_combo.setFixedWidth(68)
        slot_combo.addItems(["—", "Q1", "Q2", "Q3"])
        slot_combo.setCurrentIndex(max(0, slot_idx + 1))  # -1 → 0 ("—")
        slot_combo.setEnabled(bool(self._device_id))
        slot_combo.setToolTip("Assign to a Mode quick-access slot")
        slot_combo.currentIndexChanged.connect(
            lambda idx, n=entry.name: self._on_slot_changed(n, idx)
        )
        self._row_combos[entry.name] = slot_combo
        row.addWidget(slot_combo)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda checked=False, e=entry: self._on_edit(e))
        row.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(lambda checked=False, n=entry.name: self._on_delete(n))
        row.addWidget(del_btn)

        self._rows_layout.addWidget(row_widget)
        self._row_widgets.append(row_widget)

    # ── Internal — slot management ────────────────────────────────────

    def _on_slot_changed(self, scenario_name: str, combo_idx: int) -> None:
        """Update quick-slot assignments in the store and refresh all combos."""
        if not self._device_id:
            return
        slots = list(self._store.get_quick_slots(self._device_id))
        # Remove this scenario from any slot it currently occupies
        for i, s in enumerate(slots):
            if s == scenario_name:
                slots[i] = None
        # Assign to the chosen slot (combo_idx 0 = "—")
        if combo_idx > 0:
            slots[combo_idx - 1] = scenario_name  # 1→Q1(0), 2→Q2(1), 3→Q3(2)
        self._store.set_quick_slots(self._device_id, slots)
        self._refresh_combos()

    def _refresh_combos(self) -> None:
        """Sync every slot combo to the current store state (no signal loops)."""
        if not self._device_id:
            return
        slots    = self._store.get_quick_slots(self._device_id)
        slot_map = {name: idx for idx, name in enumerate(slots) if name is not None}
        for name, combo in self._row_combos.items():
            combo.blockSignals(True)
            combo.setCurrentIndex(slot_map.get(name, -1) + 1)
            combo.blockSignals(False)

    # ── Internal — edit / delete ──────────────────────────────────────

    def _on_edit(self, entry: ScenarioEntry) -> None:
        """Open EditScenarioDialog; on accept, persist and rebuild rows."""
        dlg = EditScenarioDialog(
            entry=entry,
            all_scenarios=self._store.get_scenarios(),
            registry=self._registry,
            history=self._history,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.entry()
        if updated.name != entry.name:
            self._store.delete_scenario(entry.name)
        self._store.save_scenario(updated)
        self._populate()

    def _on_delete(self, name: str) -> None:
        """Delete the scenario from the store and rebuild rows."""
        self._store.delete_scenario(name)
        self._populate()


# ---------------------------------------------------------------------------
# EditScenarioDialog
# ---------------------------------------------------------------------------

class EditScenarioDialog(QDialog):
    """
    Full editor for a scenario: rename it and edit per-fan settings.

    Layout
    ------
    * Top row: name input + character counter
    * Middle: fan list (left) + ScenarioSettingsEditor (right)
              with [Add fan…] / [Remove fan] buttons below the list
    * Bottom: [Save] [Cancel]

    Usage::

        dlg = EditScenarioDialog(
            entry=entry,
            all_scenarios=all_entries,
            registry=registry,
            history=history,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.entry()
    """

    def __init__(
        self,
        entry: ScenarioEntry,
        all_scenarios: list[ScenarioEntry],
        registry,                            # WindowRegistry | None
        history=None,                        # DeviceHistory  | None
        parent=None,
    ):
        super().__init__(parent)
        self._original_name = entry.name
        self._all_scenarios = all_scenarios
        self._registry      = registry
        self._history       = history

        # Working copy of the fan list
        self._fans: list[FanSettings] = [
            FanSettings(device_id=f.device_id, settings=f.settings)
            for f in entry.fans
        ]
        # Index of the fan whose settings are currently shown in the editor
        self._pending_idx: Optional[int] = None

        self.setWindowTitle(f'Edit Scenario — "{entry.name}"')
        self.setMinimumWidth(580)
        self.setMinimumHeight(500)
        self.setModal(True)

        # ── Name input ──────────────────────────────────────────────────
        self._name_edit = QLineEdit(entry.name)
        self._name_edit.setMaxLength(_NAME_MAX)
        self._name_edit.textChanged.connect(self._on_name_changed)

        self._name_counter = QLabel()
        self._name_counter.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._name_counter.setMinimumWidth(50)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Scenario name:"))
        name_row.addWidget(self._name_edit, 1)
        name_row.addWidget(self._name_counter)

        self._name_warn = QLabel()
        self._name_warn.setVisible(False)

        # ── Fan list (left panel) ────────────────────────────────────────
        self._fan_list = QListWidget()
        self._fan_list.setMinimumWidth(160)
        self._fan_list.setMaximumWidth(240)
        self._fan_list.currentRowChanged.connect(self._on_fan_row_changed)

        self._add_fan_btn    = QPushButton("Add fan…")
        self._remove_fan_btn = QPushButton("Remove fan")
        self._remove_fan_btn.setObjectName("DangerBtn")
        self._add_fan_btn.clicked.connect(self._on_add_fan)
        self._remove_fan_btn.clicked.connect(self._on_remove_fan)

        fan_btn_row = QHBoxLayout()
        fan_btn_row.addWidget(self._add_fan_btn)
        fan_btn_row.addWidget(self._remove_fan_btn)
        fan_btn_row.addStretch()

        fan_col = QVBoxLayout()
        fan_col.addWidget(QLabel("Fans in scenario:"))
        fan_col.addWidget(self._fan_list)
        fan_col.addLayout(fan_btn_row)

        # ── Settings editor (right panel) ───────────────────────────────
        self._settings_label  = QLabel("Select a fan to edit its settings.")
        self._settings_label.setWordWrap(True)
        self._settings_editor = ScenarioSettingsEditor()
        self._settings_editor.setVisible(False)

        settings_col = QVBoxLayout()
        settings_col.addWidget(QLabel("Fan settings:"))
        settings_col.addWidget(self._settings_label)
        settings_col.addWidget(self._settings_editor)
        settings_col.addStretch()

        fans_row = QHBoxLayout()
        fans_row.addLayout(fan_col, 1)
        fans_row.addLayout(settings_col, 2)

        # ── Buttons ─────────────────────────────────────────────────────
        self._bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = self._bbox.button(QDialogButtonBox.StandardButton.Save)
        self._bbox.accepted.connect(self._on_accept)
        self._bbox.rejected.connect(self.reject)

        # ── Main layout ─────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.addLayout(name_row)
        layout.addWidget(self._name_warn)
        layout.addLayout(fans_row, 1)
        layout.addWidget(self._bbox)

        # Populate fan list and trigger initial state
        self._populate_fan_list()
        self._on_name_changed(entry.name)

    # ── Public ──────────────────────────────────────────────────────────

    def entry(self) -> ScenarioEntry:
        """Return the edited ScenarioEntry.  Call only after accept()."""
        return ScenarioEntry(
            name=self._name_edit.text().strip(),
            fans=list(self._fans),
        )

    # ── Internal — helpers ───────────────────────────────────────────────

    def _label_for_device(self, device_id: str) -> str:
        """Return a friendly label using history if available."""
        if self._history:
            hist_entry = next(
                (e for e in self._history.entries if e.device_id == device_id),
                None,
            )
            if hist_entry and hist_entry.name:
                return f"{hist_entry.name}  (…{device_id[-6:]})"
        return device_id

    def _flush_editor(self) -> None:
        """Save current editor state back to self._fans[_pending_idx]."""
        if self._pending_idx is not None and 0 <= self._pending_idx < len(self._fans):
            self._fans[self._pending_idx] = FanSettings(
                device_id=self._fans[self._pending_idx].device_id,
                settings=self._settings_editor.value(),
            )

    def _populate_fan_list(self) -> None:
        """Rebuild the fan list widget from self._fans."""
        self._fan_list.blockSignals(True)
        self._fan_list.clear()
        for fan in self._fans:
            item = QListWidgetItem(self._label_for_device(fan.device_id))
            item.setToolTip(fan.device_id)
            self._fan_list.addItem(item)
        self._fan_list.blockSignals(False)

        if self._fans:
            self._fan_list.setCurrentRow(0)
        else:
            self._pending_idx = None
            self._settings_label.setText("No fans in this scenario.")
            self._settings_editor.setVisible(False)

        self._update_remove_btn()

    def _update_remove_btn(self) -> None:
        self._remove_fan_btn.setEnabled(len(self._fans) > 1)

    # ── Internal — slots ─────────────────────────────────────────────────

    def _on_fan_row_changed(self, row: int) -> None:
        """Flush pending edits, then load settings for the newly selected fan."""
        self._flush_editor()
        self._pending_idx = row if 0 <= row < len(self._fans) else None

        if self._pending_idx is not None:
            fan = self._fans[self._pending_idx]
            self._settings_label.setText(
                f"Settings for: {self._label_for_device(fan.device_id)}"
            )
            self._settings_editor.setVisible(True)
            self._settings_editor.load(fan.settings)
        else:
            self._settings_label.setText("Select a fan to edit its settings.")
            self._settings_editor.setVisible(False)

    def _on_name_changed(self, text: str) -> None:
        stripped = text.strip()
        n        = len(stripped)
        valid    = _NAME_MIN <= n <= _NAME_MAX

        self._name_counter.setText(f"{n}\u202f/\u202f{_NAME_MAX}")
        colour = "#6272a4" if n == 0 else ("#50fa7b" if valid else "#ff5555")
        self._name_counter.setStyleSheet(f"color: {colour}; font-weight: bold;")

        # Warn on name collision with a *different* scenario
        if stripped != self._original_name and \
                any(e.name == stripped for e in self._all_scenarios):
            self._name_warn.setText(
                f'\u26a0\ufe0f  "{stripped}" already exists — it will be overwritten.'
            )
            self._name_warn.setStyleSheet("color: #ffb86c;")
            self._name_warn.setVisible(True)
        else:
            self._name_warn.setVisible(False)

        self._ok.setEnabled(valid)

    def _on_add_fan(self) -> None:
        """Offer to add a connected fan that is not yet in this scenario."""
        if self._registry is None:
            return

        existing_ids = {f.device_id for f in self._fans}
        candidates   = [
            w for w in self._registry.all_connected
            if w._current_device_id not in existing_ids
        ]

        menu = QMenu(self)
        if not candidates:
            act = menu.addAction("All connected fans are already in this scenario")
            act.setEnabled(False)
        else:
            for win in candidates:
                label = self._label_for_device(win._current_device_id)
                act   = menu.addAction(label)
                act.setData(win)

        chosen = menu.exec(
            self._add_fan_btn.mapToGlobal(self._add_fan_btn.rect().bottomLeft())
        )
        if chosen is None or chosen.data() is None:
            return

        win       = chosen.data()
        device_id = win._current_device_id
        s         = win._last_state

        new_settings = ScenarioSettings(
            power=s.power,
            speed=s.speed,
            manual_speed=s.manual_speed,
            operation_mode=s.operation_mode,
            boost_active=s.boost_active,
            humidity_sensor=s.humidity_sensor,
            humidity_threshold=s.humidity_threshold,
        ) if s is not None else ScenarioSettings()

        # Flush current editor before modifying the list
        self._flush_editor()
        self._pending_idx = None

        self._fans.append(FanSettings(device_id=device_id, settings=new_settings))
        self._populate_fan_list()
        self._fan_list.setCurrentRow(len(self._fans) - 1)

    def _on_remove_fan(self) -> None:
        """Remove the selected fan (disabled when only 1 fan remains)."""
        if len(self._fans) <= 1:
            return
        row = self._fan_list.currentRow()
        if row < 0 or row >= len(self._fans):
            return
        self._pending_idx = None   # discard pending edits for removed fan
        self._fans.pop(row)
        self._populate_fan_list()
        self._fan_list.setCurrentRow(min(row, len(self._fans) - 1))

    def _on_accept(self) -> None:
        """Flush settings editor before closing."""
        self._flush_editor()
        self.accept()

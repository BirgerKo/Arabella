"""OverviewWindow — the opening window showing two live cards per line.

The window uses the same portrait "mobile" format as the per-fan dashboard.
Each card is a narrow tile showing the fan name (elided if long), the airflow
house icon with arrows (Supply = into the house, Ventilation = out, Heat
Recovery = both), the humidity printed below the icon, and the fan's RTC time
above its date.  The house is green while the fan is reachable, grey when not,
and yellow when the fan reports an alarm or an expired filter timer.  Clicking
a card opens that fan's control window.

The bottom bar keeps the Refresh and "Sync All Clocks to PC" actions plus a
"Connect New Fan…" entry for adding fans not yet in the history.
"""

from __future__ import annotations

from blauberg_vento.models import DeviceState
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ventocontrol.app import ACCENT, BORDER, SURFACE, TEXT, TEXT2
from ventocontrol.controllers.overview_worker import FanSpec, OverviewWorker
from ventocontrol.history import DeviceHistory
from ventocontrol.scenarios import ScenarioStore
from ventocontrol.ui.rename_dialog import RenameDialog
from ventocontrol.ui.scenario_dialog import ManageScenariosDialog
from ventocontrol.widgets.airflow_fan_icon import AirflowFanIcon, needs_attention

_AUTO_REFRESH_MS = 10_000

_EMPTY_MESSAGE = "No fans yet — connect to a fan to get started."

# Right-click menu on a fan tile: (action key, menu label)
_CARD_ACTIONS = (
    ("open", "Open…"),
    ("details", "Details…"),
    ("rename", "Rename…"),
    ("scenario", "Scenario…"),
    ("sync_clock", "Sync Clock to PC"),
    ("remove", "Remove from List"),
)

_CARD_QSS = f"""
FanCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
FanCard:hover {{
    border-color: {ACCENT};
}}
QLabel#CardTitle {{
    font-weight: 600;
    font-size: 14px;
    color: {TEXT};
}}
QLabel#CardHumidity {{
    font-size: 12px;
    color: {TEXT};
}}
QLabel#CardTime {{
    color: {TEXT};
}}
QLabel#CardDate {{
    color: {TEXT2};
    font-size: 11px;
}}
QLabel#EmptyHint {{
    color: {TEXT2};
    font-size: 14px;
}}
"""


# ---------------------------------------------------------------------
# Formatting helpers (pure — unit-testable without a running Qt app)
# ---------------------------------------------------------------------


def format_time(state: DeviceState) -> str:
    return str(state.rtc_time) if state.rtc_time is not None else "—"


def format_date(state: DeviceState) -> str:
    return str(state.rtc_calendar) if state.rtc_calendar is not None else "—"


def format_humidity(state: DeviceState) -> str:
    if state.current_humidity is None:
        return "—"
    return f"{state.current_humidity}% RH"


# ---------------------------------------------------------------------
# ElidedLabel
# ---------------------------------------------------------------------


class ElidedLabel(QLabel):
    """Single-line label that ellipsizes long text instead of wrapping."""

    _MAX_HINT_WIDTH = 120  # keep the layout narrow; the text elides to fit

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self._apply_elision()

    def setElidedText(self, text: str) -> None:
        self._full_text = text
        self._apply_elision()

    def full_text(self) -> str:
        return self._full_text

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(min(hint.width(), self._MAX_HINT_WIDTH))
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(min(hint.width(), self._MAX_HINT_WIDTH))
        return hint

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_elision()

    def _apply_elision(self) -> None:
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, max(self.width(), 1))
        super().setText(elided)


# ---------------------------------------------------------------------
# FanCard
# ---------------------------------------------------------------------


class FanCard(QWidget):
    """Clickable narrow tile for one fan: name, airflow icon, humidity, time."""

    activated = Signal(str)  # device_id — emitted when the user clicks the card
    action_requested = Signal(str, str)  # device_id, action key — right-click menu

    def __init__(self, title: str, device_id: str, parent=None):
        super().__init__(parent)
        self.setObjectName("FanCard")
        self._device_id = device_id
        self._online = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        self._title_lbl = ElidedLabel(title)
        self._title_lbl.setObjectName("CardTitle")
        root.addWidget(self._title_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        self._icon = AirflowFanIcon()
        root.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self._humidity_lbl = QLabel("—")
        self._humidity_lbl.setObjectName("CardHumidity")
        root.addWidget(self._humidity_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        # The fan's internal clock: time above date, no row names
        self._time_lbl = QLabel("—")
        self._time_lbl.setObjectName("CardTime")
        root.addWidget(self._time_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        self._date_lbl = QLabel("—")
        self._date_lbl.setObjectName("CardDate")
        root.addWidget(self._date_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        self.setStyleSheet(_CARD_QSS)

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def title(self) -> str:
        """The full fan name, even when the visible text is ellipsized."""
        return self._title_lbl.full_text()

    def set_title(self, title: str) -> None:
        self._title_lbl.setElidedText(title)

    def is_online(self) -> bool:
        return self._online

    @property
    def humidity(self) -> str:
        """Humidity text printed below the icon (for tests/inspection)."""
        return self._humidity_lbl.text()

    @property
    def time_text(self) -> str:
        return self._time_lbl.text()

    @property
    def date_text(self) -> str:
        return self._date_lbl.text()

    def refresh(self, state: DeviceState) -> None:
        """Update the card from a freshly polled device state."""
        self._online = True
        self._icon.set_available(True)
        self._icon.set_warning(needs_attention(state))
        self._icon.set_mode(state.operation_mode)
        self._humidity_lbl.setText(format_humidity(state))
        self._time_lbl.setText(format_time(state))
        self._date_lbl.setText(format_date(state))

    def mark_offline(self) -> None:
        """Grey the card out after the fan failed to answer a poll."""
        self._online = False
        self._icon.set_available(False)
        self._icon.set_warning(False)
        self._icon.set_mode(None)
        self._humidity_lbl.setText("—")
        self._time_lbl.setText("—")
        self._date_lbl.setText("—")

    def mousePressEvent(self, event) -> None:
        """Only the left button opens the fan window — right opens the menu."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._device_id)

    def contextMenuEvent(self, event) -> None:
        """Right-click on a tile shows the per-fan action menu."""
        self._build_action_menu().exec(event.globalPos())

    def _build_action_menu(self) -> QMenu:
        """The right-click menu (built separately so tests can trigger it)."""
        menu = QMenu(self)
        for key, label in _CARD_ACTIONS:
            menu.addAction(label).triggered.connect(
                lambda checked=False, k=key: self.action_requested.emit(self._device_id, k)
            )
        return menu


# ---------------------------------------------------------------------
# OverviewWindow
# ---------------------------------------------------------------------


class OverviewWindow(QMainWindow):
    """The opening window: a live overview card per known fan."""

    _sig_poll_all = Signal()
    _sig_sync_rtc = Signal()
    _sig_sync_one = Signal(str)

    def __init__(
        self,
        history: DeviceHistory | None = None,
        registry=None,
        polling_enabled: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("VentoControl")
        self.setMinimumSize(380, 600)

        self._history = history
        self._registry = registry
        self._polling_enabled = polling_enabled
        self._scenarios = ScenarioStore()
        self._cards: dict[str, FanCard] = {}
        self._fan_windows: dict[str, QWidget] = {}
        self._connect_windows: list[QWidget] = []
        self._specs: list[FanSpec] = []
        self._thread: QThread | None = None
        self._worker: OverviewWorker | None = None
        self._synced_count = 0
        self._sync_all_active = False

        self._timer = QTimer(self)
        self._timer.setInterval(_AUTO_REFRESH_MS)
        self._timer.timeout.connect(self._sig_poll_all.emit)

        self._build_ui()
        self._sync_cards()
        self._restart_worker_if_changed()

        if self._history is not None:
            self._history.add_observer(self._on_history_changed)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._empty_lbl = QLabel(_EMPTY_MESSAGE)
        self._empty_lbl.setObjectName("EmptyHint")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setVisible(False)

        self._cards_grid = QGridLayout()
        self._cards_grid.setContentsMargins(16, 16, 16, 16)
        self._cards_grid.setHorizontalSpacing(12)
        self._cards_grid.setVerticalSpacing(12)
        self._cards_grid.setColumnStretch(0, 1)
        self._cards_grid.setColumnStretch(1, 1)
        cards_host = QWidget()
        cards_host.setLayout(self._cards_grid)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(cards_host)

        # Bottom action bar — refresh and clock sync stay on the start window
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._sig_poll_all.emit)
        self._sync_btn = QPushButton("Sync All Clocks to PC")
        self._sync_btn.setToolTip("Set every fan's internal clock from this computer's system time")
        self._sync_btn.clicked.connect(self._on_sync_clicked)
        self._connect_btn = QPushButton("Connect New Fan…")
        self._connect_btn.setToolTip("Discover and connect to a fan not yet in the list")
        self._connect_btn.clicked.connect(self._on_connect_new_clicked)
        self._sync_lbl = QLabel("")

        bar = QWidget()
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(16, 8, 16, 12)
        bar_row.setSpacing(8)
        bar_row.addWidget(self._refresh_btn)
        bar_row.addWidget(self._sync_btn)
        bar_row.addWidget(self._connect_btn)
        bar_row.addStretch()
        bar_row.addWidget(self._sync_lbl)

        # The central widget layers the empty hint, the scroll area and the bar
        layered = QWidget()
        layer_box = QVBoxLayout(layered)
        layer_box.setContentsMargins(0, 0, 0, 0)
        layer_box.setSpacing(0)
        layer_box.addWidget(self._empty_lbl, 1)
        layer_box.addWidget(self._scroll, 1)
        layer_box.addWidget(bar)
        self.setCentralWidget(layered)

    # ------------------------------------------------------------------
    # Card list maintenance
    # ------------------------------------------------------------------

    def _sync_cards(self) -> None:
        """Create, remove and retitle cards to match the current history."""
        entries = self._history.entries if self._history is not None else []
        by_id = {e.device_id: e for e in entries}

        for did in [d for d in self._cards if d not in by_id]:
            card = self._cards.pop(did)
            card.deleteLater()

        for entry in entries:
            card = self._cards.get(entry.device_id)
            if card is None:
                card = FanCard(title=self._display_name(entry), device_id=entry.device_id)
                card.activated.connect(self._open_fan_window)
                card.action_requested.connect(self._on_card_action)
                self._cards[entry.device_id] = card
            else:
                card.set_title(self._display_name(entry))

        self._repopulate_layout()

    def _repopulate_layout(self) -> None:
        """Place the cards into the scroll grid, two per line, in history order."""
        while self._cards_grid.count():
            self._cards_grid.takeAt(0)
        entries = self._history.entries if self._history is not None else []
        for index, entry in enumerate(entries):
            self._cards_grid.addWidget(self._cards[entry.device_id], index // 2, index % 2)
        # Push the tiles to the top instead of stretching them vertically
        for row in range(self._cards_grid.rowCount()):
            self._cards_grid.setRowStretch(row, 0)
        self._cards_grid.setRowStretch(len(entries) // 2 + 1, 1)

        has_cards = bool(self._cards)
        self._empty_lbl.setVisible(not has_cards)
        self._scroll.setVisible(has_cards)
        self._refresh_btn.setEnabled(has_cards)
        self._sync_btn.setEnabled(has_cards)

    @staticmethod
    def _display_name(entry) -> str:
        return entry.name or entry.unit_type_name or "Vento Fan"

    @staticmethod
    def _to_spec(entry) -> FanSpec:
        return FanSpec(device_id=entry.device_id, host=entry.ip, password=entry.password)

    # ------------------------------------------------------------------
    # Worker wiring
    # ------------------------------------------------------------------

    def _current_specs(self) -> list[FanSpec]:
        entries = self._history.entries if self._history is not None else []
        return [self._to_spec(e) for e in entries]

    def _restart_worker_if_changed(self) -> None:
        """(Re)start the polling worker whenever the fan list changes."""
        specs = self._current_specs()
        if specs == self._specs and self._thread is not None:
            return
        self._specs = specs
        self._stop_worker()
        if specs and self._polling_enabled:
            self._start_worker(specs)

    def _stop_worker(self) -> None:
        self._timer.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None

    def _start_worker(self, specs: list[FanSpec]) -> None:
        self._thread = QThread(self)
        self._worker = OverviewWorker(specs)
        self._worker.moveToThread(self._thread)

        self._worker.fan_state_updated.connect(self._on_fan_state)
        self._worker.fan_unreachable.connect(self._on_fan_unreachable)
        self._worker.rtc_synced.connect(self._on_rtc_synced)
        self._worker.rtc_sync_finished.connect(self._on_rtc_sync_finished)
        self._sig_poll_all.connect(self._worker.do_poll_all)
        self._sig_sync_rtc.connect(self._worker.do_sync_all_rtc)
        self._sig_sync_one.connect(self._worker.do_sync_rtc)

        self._thread.start()
        self._timer.start()
        self._sig_poll_all.emit()  # first poll immediately

    def _on_history_changed(self) -> None:
        """Observer callback — a fan was added, removed, renamed or cleared."""
        self._sync_cards()
        self._restart_worker_if_changed()

    # ------------------------------------------------------------------
    # Slots — worker results
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_fan_state(self, state: DeviceState) -> None:
        card = self._cards.get(state.device_id)
        if card is not None:
            card.refresh(state)

    @Slot(str)
    def _on_fan_unreachable(self, device_id: str) -> None:
        card = self._cards.get(device_id)
        if card is not None:
            card.mark_offline()

    def _on_sync_clicked(self) -> None:
        """Kick off an RTC sync of all fans and show progress in the status label."""
        self._synced_count = 0
        self._sync_all_active = True
        self._sync_lbl.setText("Syncing clocks…")
        self._sync_btn.setEnabled(False)
        self._sig_sync_rtc.emit()

    @Slot(str)
    def _on_rtc_synced(self, device_id: str) -> None:
        """Show progress for the all-fans sync; single-fan syncs stay silent."""
        if not self._sync_all_active:
            return
        self._synced_count += 1
        self._sync_lbl.setText(f"Clocks synced: {self._synced_count}")

    @Slot()
    def _on_rtc_sync_finished(self) -> None:
        """Re-enable the button once the whole sync pass is done."""
        self._sync_all_active = False
        offline = len(self._cards) - self._synced_count
        text = f"Clocks synced: {self._synced_count}"
        if offline:
            text += f" ({offline} offline)"
        self._sync_lbl.setText(text)
        self._sync_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Fan windows and tile actions
    # ------------------------------------------------------------------

    def _open_fan_window(self, device_id: str) -> None:
        """Open (or bring to front) the per-fan control window for a card."""
        win = self._fan_windows.get(device_id)
        if win is not None and win.isVisible():
            win.raise_()
            win.activateWindow()
            return
        self._fan_window_for(device_id)

    def _fan_window_for(self, device_id: str):
        """Return the open fan window for the device, opening it if needed."""
        from ventocontrol.ui.fan_window import (
            FanWindow,  # local import: keeps the launcher decoupled from the fan window
        )

        entry = self._entry_for(device_id)
        if entry is None:
            return None
        win = FanWindow(
            host=entry.ip,
            device_id=entry.device_id,
            password=entry.password,
            history=self._history,
            registry=self._registry,
        )
        self._fan_windows[device_id] = win
        win.show()
        return win

    def _entry_for(self, device_id: str):
        """The history entry for a device, or None if unknown."""
        if self._history is None:
            return None
        return next((e for e in self._history.entries if e.device_id == device_id), None)

    def _on_connect_new_clicked(self) -> None:
        """Open a blank fan window that runs the connect/discovery dialog."""
        from ventocontrol.ui.fan_window import FanWindow  # local import: same decoupling reason as above

        win = FanWindow(history=self._history, registry=self._registry)
        self._connect_windows.append(win)
        win.show()

    # ------------------------------------------------------------------
    # Tile right-click actions
    # ------------------------------------------------------------------

    def _on_card_action(self, device_id: str, action: str) -> None:
        """Dispatch a right-click tile action to its handler."""
        handlers = {
            "open": self._open_fan_window,
            "details": self._open_fan_details,
            "rename": self._rename_fan,
            "scenario": self._open_fan_scenarios,
            "sync_clock": self._sync_fan_clock,
            "remove": self._remove_fan,
        }
        handler = handlers.get(action)
        if handler is not None:
            handler(device_id)

    def _open_fan_details(self, device_id: str) -> None:
        """Open the fan window and its Details dialog; it fills in once connected."""
        win = self._fan_window_for(device_id)
        if win is not None:
            win._open_fan_details()

    def _open_fan_scenarios(self, device_id: str) -> None:
        """Manage the global scenarios with this fan's quick-slots enabled."""
        dlg = ManageScenariosDialog(
            store=self._scenarios,
            device_id=device_id,
            registry=self._registry,
            history=self._history,
            parent=self,
        )
        dlg.exec()

    def _rename_fan(self, device_id: str) -> None:
        """Rename the fan via the dialog; the observer retitles the tile."""
        entry = self._entry_for(device_id)
        if entry is None or self._history is None:
            return
        dlg = RenameDialog(current_name=entry.name, parent=self)
        if dlg.exec() != RenameDialog.DialogCode.Accepted:
            return
        self._history.rename(device_id, dlg.name())

    def _sync_fan_clock(self, device_id: str) -> None:
        """Set this one fan's clock from the PC system time."""
        card = self._cards.get(device_id)
        if card is None or self._worker is None:
            return
        # No label here: the refreshed clock on the tile is the feedback
        self._sig_sync_one.emit(device_id)

    def _remove_fan(self, device_id: str) -> None:
        """Drop the fan from the list; the observer removes the tile."""
        if self._history is None:
            return
        self._history.remove(device_id)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent):
        self._timer.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        # The Overview is the app's home window — closing it closes every
        # fan window and blank connect window it opened.
        for win in list(self._fan_windows.values()) + list(self._connect_windows):
            win.close()
        self._fan_windows.clear()
        self._connect_windows.clear()
        super().closeEvent(event)

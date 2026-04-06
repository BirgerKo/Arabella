"""ScheduleDialog — weekly schedule editor for the desktop UI.

Presents a mode-selector (All Days / Weekdays / Weekend / Days) at the top,
and a period grid below.  Each cell lets the user choose a speed and an end
time (HH:MM).

Day group encoding (Blauberg protocol):
  0 = Weekdays group (Mon–Fri shorthand)
  1 = Monday … 7 = Sunday
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QStackedWidget, QTimeEdit, QVBoxLayout, QWidget,
)

_SPEED_LABELS = ["Standby", "Speed 1", "Speed 2", "Speed 3"]

_DAY_LABELS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

_MODE_ALL     = 0   # one row → writes to days 1–7
_MODE_WEEKDAY = 1   # one row → writes to day group 0 (Mon–Fri)
_MODE_WEEKEND = 2   # one row → writes to days 6–7
_MODE_DAYS    = 3   # seven rows — one per day (1–7)


@dataclass
class _PeriodCell:
    speed_combo: QComboBox
    time_edit:   QTimeEdit


class ScheduleDialog(QDialog):
    """Weekly schedule editor.

    Emits ``period_changed(day, period, speed, end_h, end_m)`` for each
    affected cell when the user clicks "Apply to device".
    """

    period_changed = Signal(int, int, int, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Weekly Schedule")
        self.setMinimumWidth(720)

        self._mode: int = _MODE_ALL

        self._all_cells:     list[_PeriodCell]       = []
        self._weekday_cells: list[_PeriodCell]        = []
        self._weekend_cells: list[_PeriodCell]        = []
        self._day_cells:     list[list[_PeriodCell]]  = []  # [7][4]

        self._build_ui()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, schedule: dict) -> None:
        """Populate all grid views from a ``{(day, period): SchedulePeriod}`` dict.

        Switches from the loading page to the editor once data has arrived.
        """
        self._populate_single_row(self._all_cells,     schedule, day=1)
        self._populate_single_row(self._weekday_cells, schedule, day=0)
        self._populate_single_row(self._weekend_cells, schedule, day=6)
        for d_i in range(7):
            self._populate_single_row(self._day_cells[d_i], schedule, day=d_i + 1)
        self._stack.setCurrentIndex(1)   # switch to editor page

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        root.addLayout(self._build_mode_selector())

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_loading_page())
        self._stack.addWidget(self._build_editor_page())
        root.addWidget(self._stack)

        hint = QLabel(
            "Set fan speed and end time for each period.  "
            "Periods run in sequence and together cover 24 hours."
        )
        hint.setWordWrap(True)
        hint.setObjectName("HintLabel")
        root.addWidget(hint)

        root.addWidget(self._build_button_box())

    def _build_mode_selector(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Apply to:</b>"))
        self._mode_group = QButtonGroup(self)
        for i, label in enumerate(["All Days", "Weekdays", "Weekend", "Days"]):
            rb = QRadioButton(label)
            rb.setChecked(i == 0)
            self._mode_group.addButton(rb, i)
            row.addWidget(rb)
        row.addStretch()
        self._mode_group.idClicked.connect(self._on_mode_changed)
        return row

    def _build_loading_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        lbl = QLabel("Loading schedule from device…")
        lbl.setObjectName("HintLabel")
        layout.addWidget(lbl)
        return page

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self._inner_stack = QStackedWidget()

        cells, widget = self._build_single_row_widget("All Days")
        self._all_cells = cells
        self._inner_stack.addWidget(widget)

        cells, widget = self._build_single_row_widget("Weekdays  (Mon – Fri)")
        self._weekday_cells = cells
        self._inner_stack.addWidget(widget)

        cells, widget = self._build_single_row_widget("Weekend  (Sat – Sun)")
        self._weekend_cells = cells
        self._inner_stack.addWidget(widget)

        day_cells_all, widget = self._build_days_grid_widget()
        self._day_cells = day_cells_all
        self._inner_stack.addWidget(widget)

        layout.addWidget(self._inner_stack)
        return page

    def _build_single_row_widget(
        self, row_label: str
    ) -> tuple[list[_PeriodCell], QWidget]:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)

        grid.addWidget(self._header_label("Day"), 0, 0)
        for p in range(4):
            grid.addWidget(self._header_label(f"Period {p + 1}"), 0, p + 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(sep, 1, 0, 1, 5)

        lbl = QLabel(row_label)
        lbl.setObjectName("DayLabel")
        grid.addWidget(lbl, 2, 0)

        cells: list[_PeriodCell] = []
        for p_i in range(4):
            cell_widget, cell = self._build_cell()
            grid.addWidget(cell_widget, 2, p_i + 1)
            cells.append(cell)

        return cells, container

    def _build_days_grid_widget(
        self,
    ) -> tuple[list[list[_PeriodCell]], QWidget]:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)

        grid.addWidget(self._header_label("Day"), 0, 0)
        for p in range(4):
            grid.addWidget(self._header_label(f"Period {p + 1}"), 0, p + 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(sep, 1, 0, 1, 5)

        all_cells: list[list[_PeriodCell]] = []
        for d_i, day_label in enumerate(_DAY_LABELS):
            row = d_i + 2
            lbl = QLabel(day_label)
            lbl.setObjectName("DayLabel")
            grid.addWidget(lbl, row, 0)

            day_cells: list[_PeriodCell] = []
            for p_i in range(4):
                cell_widget, cell = self._build_cell()
                grid.addWidget(cell_widget, row, p_i + 1)
                day_cells.append(cell)
            all_cells.append(day_cells)

        return all_cells, container

    def _build_cell(self) -> tuple[QWidget, _PeriodCell]:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        speed_combo = QComboBox()
        speed_combo.addItems(_SPEED_LABELS)
        speed_combo.setMinimumWidth(90)
        layout.addWidget(speed_combo)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setMinimumWidth(72)
        layout.addWidget(time_edit)

        return container, _PeriodCell(speed_combo, time_edit)

    def _build_button_box(self) -> QDialogButtonBox:
        btn_box = QDialogButtonBox()
        apply_btn = QPushButton("Apply to device")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        btn_box.addButton(apply_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        close_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.reject)
        return btn_box

    @staticmethod
    def _header_label(text: str) -> QLabel:
        lbl = QLabel(f"<b>{text}</b>")
        lbl.setObjectName("ScheduleHeader")
        return lbl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _populate_single_row(
        cells: list[_PeriodCell], schedule: dict, day: int
    ) -> None:
        for p_i, cell in enumerate(cells):
            entry = schedule.get((day, p_i + 1))
            if entry is not None:
                cell.speed_combo.setCurrentIndex(entry.speed)
                cell.time_edit.setTime(QTime(entry.end_hours, entry.end_minutes))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self, mode_id: int) -> None:
        self._mode = mode_id
        self._inner_stack.setCurrentIndex(mode_id)

    def _on_apply(self) -> None:
        if self._mode == _MODE_ALL:
            for day in range(1, 8):
                self._emit_row(day, self._all_cells)
        elif self._mode == _MODE_WEEKDAY:
            self._emit_row(0, self._weekday_cells)
        elif self._mode == _MODE_WEEKEND:
            for day in (6, 7):
                self._emit_row(day, self._weekend_cells)
        elif self._mode == _MODE_DAYS:
            for d_i, day_cells in enumerate(self._day_cells):
                self._emit_row(d_i + 1, day_cells)
        self.accept()

    def _emit_row(self, day: int, cells: list[_PeriodCell]) -> None:
        for p_i, cell in enumerate(cells):
            t = cell.time_edit.time()
            self.period_changed.emit(
                day, p_i + 1,
                cell.speed_combo.currentIndex(),
                t.hour(), t.minute(),
            )

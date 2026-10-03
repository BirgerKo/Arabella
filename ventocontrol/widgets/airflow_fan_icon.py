"""AirflowFanIcon — a house outline with arrows showing where the air goes.

The icon is green while the fan is reachable, grey when it is not, and yellow
when the fan needs attention (an alarm or an expired filter timer):

- Supply mode:          one arrow entering the house (air into the house)
- Ventilation mode:     one arrow leaving the house (air out of the house)
- Heat Recovery mode:   two arrows, one in and one out (air flowing both ways)
"""

from __future__ import annotations

from blauberg_vento.models import DeviceState
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

_WIDTH = 72
_HEIGHT = 64
_AVAILABLE_COLOUR = "#50fa7b"  # green — fan reachable
_WARNING_COLOUR = "#ffb86c"  # yellow — alarm or expired filter timer
_UNAVAILABLE_COLOUR = "#6272a4"  # grey — fan not answering


def attention_reason(state: DeviceState) -> str | None:
    """Human-readable reason the fan needs attention, or None when healthy.

    Alarm takes precedence over the filter timer, and both are reported
    together, joined with " · ", when the device reports both.
    """
    reasons: list[str] = []
    if state.alarm_status == 1:
        reasons.append("Alarm")
    countdown = state.filter_countdown
    if state.filter_needs_replacement or (
        countdown is not None and (countdown.days, countdown.hours, countdown.minutes) == (0, 0, 0)
    ):
        reasons.append("Filter timer expired")
    return " · ".join(reasons) if reasons else None


def needs_attention(state: DeviceState) -> bool:
    """True when the fan reports an alarm or an expired filter timer."""
    return attention_reason(state) is not None


# House outline (pentagon) geometry
_HOUSE_X0 = 16.0
_HOUSE_X1 = 56.0
_HOUSE_CX = _WIDTH / 2
_HOUSE_APEX_Y = 8.0
_HOUSE_EAVE_Y = 24.0
_HOUSE_BASE_Y = 44.0

# Arrow geometry — horizontal arrows crossing the house walls
_ARROW_BODY = 6.0  # distance between arrowhead tip and its tail lines
_ARROW_TAIL = 3.0  # vertical spread of the arrowhead tail lines


class AirflowFanIcon(QWidget):
    """Per-fan icon: availability colour on a house, airflow direction as arrows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._available = False
        self._warning = False
        self._mode: int | None = None
        self.setFixedSize(_WIDTH, _HEIGHT)

    def set_available(self, available: bool) -> None:
        if available != self._available:
            self._available = available
            self.update()

    def is_available(self) -> bool:
        return self._available

    def set_warning(self, warning: bool) -> None:
        if warning != self._warning:
            self._warning = warning
            self.update()

    def is_warning(self) -> bool:
        return self._warning

    def set_mode(self, mode: int | None) -> None:
        if mode != self._mode:
            self._mode = mode
            self.update()

    def mode(self) -> int | None:
        return self._mode

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._warning:
            colour = _WARNING_COLOUR
        elif self._available:
            colour = _AVAILABLE_COLOUR
        else:
            colour = _UNAVAILABLE_COLOUR
        pen = QPen(QColor(colour), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        self._paint_house(painter)
        if self._mode is not None:
            self._paint_airflow(painter)

    def _paint_house(self, painter: QPainter) -> None:
        painter.drawLine(int(_HOUSE_X0), int(_HOUSE_BASE_Y), int(_HOUSE_X0), int(_HOUSE_EAVE_Y))
        painter.drawLine(int(_HOUSE_X0), int(_HOUSE_EAVE_Y), int(_HOUSE_CX), int(_HOUSE_APEX_Y))
        painter.drawLine(int(_HOUSE_CX), int(_HOUSE_APEX_Y), int(_HOUSE_X1), int(_HOUSE_EAVE_Y))
        painter.drawLine(int(_HOUSE_X1), int(_HOUSE_EAVE_Y), int(_HOUSE_X1), int(_HOUSE_BASE_Y))

    def _paint_airflow(self, painter: QPainter) -> None:
        """Arrows crossing the house walls, per operation mode."""
        in_y = (_HOUSE_EAVE_Y + _HOUSE_BASE_Y) / 2  # single arrow height
        if self._mode == 0:  # Ventilation — air out of the house
            self._paint_arrow(painter, from_x=_HOUSE_CX + 8, to_x=_HOUSE_X1 + 12, y=in_y)
        elif self._mode == 1:  # Heat Recovery — air in and out
            self._paint_arrow(painter, from_x=_HOUSE_X0 - 12, to_x=_HOUSE_CX - 8, y=in_y - 5)
            self._paint_arrow(painter, from_x=_HOUSE_CX + 8, to_x=_HOUSE_X1 + 12, y=in_y + 5)
        elif self._mode == 2:  # Supply — air into the house
            self._paint_arrow(painter, from_x=_HOUSE_X0 - 12, to_x=_HOUSE_CX - 8, y=in_y)

    def _paint_arrow(self, painter: QPainter, from_x: float, to_x: float, y: float) -> None:
        painter.drawLine(int(from_x), int(y), int(to_x), int(y))
        if to_x > from_x:  # pointing right
            painter.drawLine(int(to_x), int(y), int(to_x - _ARROW_BODY), int(y - _ARROW_TAIL))
            painter.drawLine(int(to_x), int(y), int(to_x - _ARROW_BODY), int(y + _ARROW_TAIL))
        else:  # pointing left
            painter.drawLine(int(to_x), int(y), int(to_x + _ARROW_BODY), int(y - _ARROW_TAIL))
            painter.drawLine(int(to_x), int(y), int(to_x + _ARROW_BODY), int(y + _ARROW_TAIL))

    def sizeHint(self) -> QSize:
        return QSize(_WIDTH, _HEIGHT)

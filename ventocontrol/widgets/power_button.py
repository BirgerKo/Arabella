"""PowerButton — large circular power toggle whose colour shows fan health.

The button colour follows the same rules as the Overview tile icon:

- Green — the fan is connected and everything is OK
- Yellow — the fan reports an alarm or an expired filter timer
- Grey — the fan is not connected

The power state itself is shown by the glow: ON fills and glows the circle,
OFF leaves it a plain outline.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QAbstractButton

_OK_COLOUR = "#50fa64"  # green — connected and healthy
_WARNING_COLOUR = "#ffb86c"  # yellow — alarm or expired filter timer
_OFFLINE_COLOUR = "#6272a4"  # grey — not connected
_OFF_BORDER = "#444455"  # grey — circle border while OFF
_ON_TINT_ALPHA = 31  # 12 % of 255 — fill tint when ON
_GLOW_INNER_ALPHA = 80  # inner glow opacity
_GLOW_OUTER_ALPHA = 0  # outer glow (fully transparent)


class PowerButton(QAbstractButton):
    """Circular power button: colour = health, glow = power state."""

    toggled_power = Signal(bool)  # emits new desired state

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self._available = False
        self._warning = False
        self.setCheckable(True)
        self.setFixedSize(90, 90)
        self.clicked.connect(self._on_click)

    # ── Power state ────────────────────────────────────────────────────

    def set_on(self, on: bool):
        if on != self._on:
            self._on = on
            self.setChecked(on)
            self.update()

    def is_on(self) -> bool:
        return self._on

    # ── Health state ───────────────────────────────────────────────────

    def set_available(self, available: bool):
        if available != self._available:
            self._available = available
            self.update()

    def is_available(self) -> bool:
        return self._available

    def set_warning(self, warning: bool):
        if warning != self._warning:
            self._warning = warning
            self.update()

    def is_warning(self) -> bool:
        return self._warning

    def _health_colour(self) -> str:
        if self._warning:
            return _WARNING_COLOUR
        if self._available:
            return _OK_COLOUR
        return _OFFLINE_COLOUR

    def _on_click(self):
        self.toggled_power.emit(not self._on)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 4

        health = QColor(self._health_colour())

        # Radial glow halo when ON — carries the health colour
        if self._on:
            glow = QRadialGradient(cx, cy, r * 1.5)
            glow_inner = QColor(health)
            glow_inner.setAlpha(_GLOW_INNER_ALPHA)
            glow_outer = QColor(health)
            glow_outer.setAlpha(_GLOW_OUTER_ALPHA)
            glow.setColorAt(0.0, glow_inner)
            glow.setColorAt(1.0, glow_outer)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(int(cx - r * 1.5), int(cy - r * 1.5), int(r * 3), int(r * 3))

        # Circle: health-tinted fill + border when ON; grey border when OFF
        border_colour = health if self._on else QColor(_OFF_BORDER)
        painter.setPen(QPen(border_colour, 2, Qt.PenStyle.SolidLine))
        if self._on:
            tint = QColor(health)
            tint.setAlpha(_ON_TINT_ALPHA)
            painter.setBrush(tint)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # Power icon in the health colour
        pen = QPen(health, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # vertical bar
        painter.drawLine(int(cx), int(cy - r * 0.55), int(cx), int(cy + r * 0.15))
        # arc (150° … 390° → gap at top)
        arc_r = int(r * 0.45)
        painter.drawArc(
            int(cx - arc_r),
            int(cy - arc_r),
            arc_r * 2,
            arc_r * 2,
            120 * 16,
            300 * 16,  # 120° → 60°, gap centred at 90° (top)
        )

    def sizeHint(self) -> QSize:
        return QSize(90, 90)

"""PowerButton — large circular toggle with glow effect."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QAbstractButton

_ON_COLOUR   = "#50fa64"   # green — icon colour when power is ON
_OFF_COLOUR  = "#f8f8f2"   # near-white — icon colour when power is OFF


class PowerButton(QAbstractButton):
    """Circular power button that glows green when ON."""

    toggled_power = Signal(bool)   # emits new desired state

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.setCheckable(True)
        self.setFixedSize(90, 90)
        self.clicked.connect(self._on_click)

    def set_on(self, on: bool):
        if on != self._on:
            self._on = on
            self.setChecked(on)
            self.update()

    def is_on(self) -> bool:
        return self._on

    def _on_click(self):
        self.toggled_power.emit(not self._on)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 4

        # Soft green glow halo when ON (background stays transparent)
 #       if self._on:
 #           glow = QRadialGradient(cx, cy, r * 1.5)
 #           glow.setColorAt(0.0, QColor(_ON_COLOUR + "50"))
 #           glow.setColorAt(1.0, QColor(_ON_COLOUR + "00"))
 #           painter.setPen(Qt.PenStyle.NoPen)
 #           painter.setBrush(glow)
 #           painter.drawEllipse(int(cx - r * 1.5), int(cy - r * 1.5),
 #                               int(r * 3), int(r * 3))

        # Power icon: green when ON, near-white when OFF
        icon_colour = _ON_COLOUR if self._on else _OFF_COLOUR
        pen = QPen(QColor(icon_colour), 3, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # vertical bar
        painter.drawLine(int(cx), int(cy - r * 0.55), int(cx), int(cy + r * 0.15))
        # arc (150° … 390° → gap at top)
        arc_r = int(r * 0.45)
        painter.drawArc(
            int(cx - arc_r), int(cy - arc_r),
            arc_r * 2, arc_r * 2,
            210 * 16, 300 * 16,   # from 210° clockwise 300°
        )

    def sizeHint(self) -> QSize:
        return QSize(90, 90)

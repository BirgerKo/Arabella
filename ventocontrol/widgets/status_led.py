"""StatusLED — small circular indicator widget."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

# Colour presets
LED_COLOURS = {
    "green":  ("#50fa7b", "#27ae60"),
    "red":    ("#ff5555", "#c0392b"),
    "amber":  ("#ffb86c", "#e67e22"),
    "blue":   ("#5e81f4", "#2c3e8c"),
    "grey":   ("#6272a4", "#44475a"),
}


class StatusLED(QWidget):
    """A small filled circle used as a status indicator."""

    def __init__(self, colour: str = "grey", diameter: int = 14, parent=None):
        super().__init__(parent)
        self._colour = colour
        self._diameter = diameter
        self.setFixedSize(diameter + 4, diameter + 4)

    def set_colour(self, colour: str):
        if colour != self._colour:
            self._colour = colour
            self.update()

    # Convenience helpers
    def set_ok(self):      self.set_colour("green")
    def set_error(self):   self.set_colour("red")
    def set_warning(self): self.set_colour("amber")
    def set_inactive(self): self.set_colour("grey")
    def set_active(self):  self.set_colour("blue")

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bright, dark = LED_COLOURS.get(self._colour, LED_COLOURS["grey"])
        cx = self.width() / 2
        cy = self.height() / 2
        r  = self._diameter / 2

        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.2)
        grad.setColorAt(0.0, QColor(bright))
        grad.setColorAt(1.0, QColor(dark))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(
            int(cx - r), int(cy - r),
            self._diameter, self._diameter,
        )

    def sizeHint(self) -> QSize:
        d = self._diameter + 4
        return QSize(d, d)

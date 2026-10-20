from __future__ import annotations

from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QRadialGradient
from PyQt6.QtWidgets import QWidget

OFF_COLOR = "#3a3f44"
IDLE_ON_COLOR = "#2f7d46"
PULSE_COLOR = "#00e676"
ERROR_COLOR = "#e5484d"


class LedIndicator(QWidget):
    """A small circular LED. Two ways to drive it:

    - set_state(color, lit=True): steady state (e.g. connection status).
    - pulse(color, ms): transient bright flash that reverts to whatever
      steady state was set before the pulse.

    One widget serves both use cases so every LED in the app looks the same.
    """

    DIAMETER = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.DIAMETER, self.DIAMETER)
        self._steady_color = QColor(OFF_COLOR)
        self._current_color = QColor(OFF_COLOR)
        self._lit = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setSingleShot(True)
        self._pulse_timer.timeout.connect(self._end_pulse)

    def set_state(self, color: str, lit: bool = True):
        self._steady_color = QColor(color)
        self._lit = lit
        if not self._pulse_timer.isActive():
            self._current_color = self._steady_color if lit else QColor(OFF_COLOR)
            self.update()

    def pulse(self, color: str = PULSE_COLOR, ms: int = 350):
        self._current_color = QColor(color)
        self._lit = True
        self.update()
        self._pulse_timer.start(ms)

    def _end_pulse(self):
        self._current_color = self._steady_color if self._lit else QColor(OFF_COLOR)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        color = self._current_color

        if self._lit or self._pulse_timer.isActive():
            glow = QRadialGradient(QPointF(rect.center()), self.DIAMETER * 0.7)
            glow_color = QColor(color)
            glow_color.setAlpha(120)
            glow.setColorAt(0, glow_color)
            glow_color.setAlpha(0)
            glow.setColorAt(1, glow_color)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect.adjusted(-3, -3, 3, 3))

        painter.setBrush(color)
        painter.setPen(QColor("#15181b"))
        painter.drawEllipse(rect)

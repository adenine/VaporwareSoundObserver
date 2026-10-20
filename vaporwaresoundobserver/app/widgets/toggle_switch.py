from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

TRACK_OFF = "#3a3f44"
TRACK_ON = "#2f7d46"
KNOB_COLOR = "#f2f2f2"


class ToggleSwitch(QWidget):
    """An iOS-style animated on/off switch."""

    toggled = pyqtSignal(bool)

    WIDTH = 40
    HEIGHT = 22
    MARGIN = 2

    def __init__(self, parent=None, checked: bool = False):
        super().__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        knob_d = self.HEIGHT - 2 * self.MARGIN
        self._knob_x = float(self.WIDTH - self.MARGIN - knob_d) if checked else float(self.MARGIN)

        self._anim = QPropertyAnimation(self, b"knobX", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animate: bool = False):
        if checked == self._checked:
            return
        self._checked = checked
        knob_d = self.HEIGHT - 2 * self.MARGIN
        end_x = float(self.WIDTH - self.MARGIN - knob_d) if checked else float(self.MARGIN)
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(end_x)
            self._anim.start()
        else:
            self._knob_x = end_x
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked, animate=True)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, x: float):
        self._knob_x = x
        self.update()

    knobX = pyqtProperty(float, _get_knob_x, _set_knob_x)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_color = QColor(TRACK_ON if self._checked else TRACK_OFF)
        track_rect = QRectF(0, 0, self.WIDTH, self.HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, self.HEIGHT / 2, self.HEIGHT / 2)

        knob_d = self.HEIGHT - 2 * self.MARGIN
        knob_rect = QRectF(self._knob_x, self.MARGIN, knob_d, knob_d)
        painter.setBrush(QColor(KNOB_COLOR))
        painter.drawEllipse(knob_rect)

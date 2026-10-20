from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.widgets.led_indicator import LedIndicator
from app.widgets.toggle_switch import ToggleSwitch


class IORow(QWidget):
    """label + LED + on/off switch, one row per input/output/publish channel."""

    toggled = pyqtSignal(bool)

    def __init__(self, label: str, checked: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.led = LedIndicator()
        layout.addWidget(self.led)

        self._label = QLabel(label)
        self._label.setObjectName("ioRowLabel")
        layout.addWidget(self._label, stretch=1)

        self.switch = ToggleSwitch(checked=checked)
        self.switch.toggled.connect(self.toggled.emit)
        layout.addWidget(self.switch)

    def is_on(self) -> bool:
        return self.switch.isChecked()

    def set_on(self, checked: bool):
        self.switch.setChecked(checked, animate=False)

    def pulse(self):
        self.led.pulse()

    def set_disabled_stub(self, tooltip: str = "Coming soon"):
        self.switch.setEnabled(False)
        self.setToolTip(tooltip)
        self._label.setEnabled(False)

from datetime import datetime

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class LiveFeedWidget(QWidget):
    """A small titled scrolling list of timestamped entries."""

    def __init__(self, title: str, max_items: int = 200, parent=None):
        super().__init__(parent)
        self._max_items = max_items
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("feedTitle")
        layout.addWidget(title_label)

        self._list = QListWidget()
        layout.addWidget(self._list)

    def add_entry(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._list.insertItem(0, QListWidgetItem(f"[{ts}] {text}"))
        while self._list.count() > self._max_items:
            self._list.takeItem(self._list.count() - 1)

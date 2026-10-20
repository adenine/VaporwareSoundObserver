STYLESHEET = """
QMainWindow, QDialog {
    background: #1b1e21;
}

QWidget {
    color: #e8e8e8;
    font-size: 12px;
}

QGroupBox {
    background: #202327;
    border: 1px solid #33383d;
    border-radius: 8px;
    margin-top: 18px;
    padding: 10px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: #9fe8b8;
}

#columnHeader {
    font-size: 14px;
    font-weight: 700;
    color: #f2f2f2;
    padding: 2px 0 6px 0;
    border-bottom: 1px solid #33383d;
    margin-bottom: 6px;
}

#appTitle {
    font-size: 24px;
    font-weight: 800;
    color: #f2f2f2;
}

#appDescription {
    font-size: 12px;
    color: #9aa1a6;
}

#sessionButton {
    font-size: 15px;
    font-weight: 700;
    padding: 12px 16px;
    background: #2f7d46;
    border: 1px solid #3a9457;
    border-radius: 7px;
    color: #f2f2f2;
}

#sessionButton:hover {
    background: #368b4f;
}

#sessionButton:pressed {
    background: #276639;
}

#micStatus {
    font-size: 11px;
    color: #8a9296;
    padding-bottom: 4px;
}

#ioRowLabel {
    font-size: 12px;
    color: #d6d6d6;
}

#ioRowLabel:disabled {
    color: #52585d;
}

#feedTitle {
    font-size: 11px;
    font-weight: 600;
    color: #8a9296;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

#wordTicker {
    background: #15181b;
    border: 1px solid #33383d;
    border-radius: 6px;
    padding: 6px 8px;
    color: #9fe8b8;
    font-family: Menlo, monospace;
    font-size: 12px;
}

QListWidget {
    background: #15181b;
    border: 1px solid #2a2e32;
    border-radius: 6px;
    font-family: Menlo, monospace;
    font-size: 11px;
    padding: 2px;
}

QListWidget::item {
    padding: 2px 4px;
}

QComboBox, QLineEdit, QSpinBox {
    background: #15181b;
    border: 1px solid #33383d;
    border-radius: 4px;
    padding: 3px 6px;
}

QPushButton {
    background: #2a2e32;
    border: 1px solid #3a3f44;
    border-radius: 5px;
    padding: 5px 12px;
}

QPushButton:hover {
    background: #33383d;
}

QPushButton:pressed {
    background: #1f2226;
}

QToolBar {
    background: #1b1e21;
    border: none;
    spacing: 6px;
    padding: 4px;
}

QStatusBar {
    background: #1b1e21;
    color: #8a9296;
}

QMenuBar {
    background: #1b1e21;
}

QMenu {
    background: #202327;
    border: 1px solid #33383d;
}
"""

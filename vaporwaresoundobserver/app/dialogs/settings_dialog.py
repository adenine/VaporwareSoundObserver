from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from config.settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(360)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_transcriber_group())
        layout.addWidget(self._build_mqtt_group())
        layout.addWidget(self._build_spacebrew_group())
        layout.addWidget(self._build_buttons())

    def _build_transcriber_group(self) -> QGroupBox:
        group = QGroupBox("Transcription (VoiceBox)")
        form = QFormLayout(group)

        self._voicebox_url = QLineEdit(self._settings.voicebox_url)
        self._voicebox_url.setPlaceholderText("http://127.0.0.1:17493")
        form.addRow("VoiceBox URL:", self._voicebox_url)

        return group

    def _build_mqtt_group(self) -> QGroupBox:
        group = QGroupBox("MQTT Broker")
        form = QFormLayout(group)

        self._host = QLineEdit(self._settings.mqtt_host)
        self._host.setPlaceholderText("localhost")
        form.addRow("Host:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(self._settings.mqtt_port)
        form.addRow("Port:", self._port)

        self._topic_base = QLineEdit(self._settings.mqtt_topic_base)
        self._topic_base.setPlaceholderText("vaporwaresoundobserver")
        form.addRow("Topic base:", self._topic_base)

        form.addRow(QLabel("Topics will be published as <base>/speech/transcribed etc."))

        return group

    def _build_spacebrew_group(self) -> QGroupBox:
        group = QGroupBox("Spacebrew")
        form = QFormLayout(group)

        self._spacebrew_host = QLineEdit(self._settings.spacebrew_host)
        self._spacebrew_host.setPlaceholderText("localhost")
        form.addRow("Host:", self._spacebrew_host)

        self._spacebrew_port = QSpinBox()
        self._spacebrew_port.setRange(1, 65535)
        self._spacebrew_port.setValue(self._settings.spacebrew_port)
        form.addRow("Port:", self._spacebrew_port)

        form.addRow(QLabel("Publishes speech_transcribed and sound_detected messages."))

        return group

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        return buttons

    def _save(self):
        self._settings.voicebox_url = self._voicebox_url.text().strip() or "http://127.0.0.1:17493"
        self._settings.mqtt_host = self._host.text().strip() or "localhost"
        self._settings.mqtt_port = self._port.value()
        self._settings.mqtt_topic_base = self._topic_base.text().strip() or "vaporwaresoundobserver"
        self._settings.spacebrew_host = self._spacebrew_host.text().strip() or "localhost"
        self._settings.spacebrew_port = self._spacebrew_port.value()
        self.accept()

from __future__ import annotations

import threading

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.dialogs.settings_dialog import SettingsDialog
from app.style import STYLESHEET
from app.widgets.io_row import IORow
from app.widgets.led_indicator import ERROR_COLOR, IDLE_ON_COLOR, OFF_COLOR
from app.widgets.live_feed import LiveFeedWidget
from config.settings import Settings
from mqtt import events as mqtt_events
from mqtt.client import MQTTClient
from outputs import apple_tts, voicebox_tts
from pipeline.classifiers.yamnet import YamnetClassifier
from pipeline.pipeline import Pipeline
from pipeline.transcribers.apple_native import AppleSpeechTranscriber
from pipeline.transcribers.voicebox import VoiceBoxTranscriber
from privacy.mode import PrivacyMode
from spacebrew import events as spacebrew_events
from spacebrew.client import SpacebrewClient

WORD_TICKER_LENGTH = 12


class MainWindow(QMainWindow):
    _tts_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._settings = Settings()
        self.setWindowTitle("Vaporware SoundObserver")
        self.setMinimumSize(940, 640)
        self.setStyleSheet(STYLESHEET)

        self._recent_words: list[str] = []
        self._voicebox_transcriber = VoiceBoxTranscriber(self._settings.voicebox_url)
        self._apple_transcriber: AppleSpeechTranscriber | None = None
        self._yamnet_classifier: YamnetClassifier | None = None

        self._pipeline = Pipeline()
        self._pipeline.set_mic_device(self._settings.mic_device)
        self._pipeline.set_mode(self._settings.privacy_mode)
        self._pipeline.audio_event.connect(self._on_audio_event)
        self._pipeline.status_changed.connect(self._on_status)
        self._pipeline.source_activity.connect(self._on_source_activity)

        self._mqtt = MQTTClient(self._settings.mqtt_host, self._settings.mqtt_port)
        self._mqtt.connected.connect(self._on_mqtt_connected)
        self._mqtt.disconnected.connect(self._on_mqtt_disconnected)
        self._mqtt.error.connect(self._on_mqtt_error)

        self._spacebrew = SpacebrewClient(self._settings.spacebrew_host, self._settings.spacebrew_port)
        self._spacebrew.connected.connect(self._on_spacebrew_connected)
        self._spacebrew.disconnected.connect(self._on_spacebrew_disconnected)
        self._spacebrew.error.connect(self._on_spacebrew_error)
        self._spacebrew.tts_requested.connect(self._on_tts_requested)

        self._tts_error.connect(lambda msg: self.statusBar().showMessage(msg, 5000))

        self._build_menu()
        self._build_central()
        self._apply_initial_source_states()

        self._mqtt.connect_broker()
        self._spacebrew.connect_broker()

    # ---- construction -------------------------------------------------

    def _build_menu(self):
        menu = self.menuBar()
        app_menu = menu.addMenu("Vaporware SoundObserver")
        app_menu.addAction("Settings…", self._open_settings)
        app_menu.addSeparator()
        app_menu.addAction("Quit", self.close)

    def _build_central(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.addWidget(self._build_header())

        columns = QHBoxLayout()
        columns.setSpacing(10)
        columns.addWidget(self._build_inputs_column(), stretch=1)
        columns.addWidget(self._build_settings_column(), stretch=1)
        columns.addWidget(self._build_outputs_column(), stretch=1)
        outer.addLayout(columns)

        self.setCentralWidget(central)

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)

        title = QLabel("Vaporware SoundObserver")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        description = QLabel(
            "The Vaporware SoundObserver helps you to observe speech and other audio "
            "events coming from people, objects, or your environment."
        )
        description.setObjectName("appDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        return header

    def _build_inputs_column(self) -> QGroupBox:
        group = QGroupBox("Audio Observers")
        layout = QVBoxLayout(group)

        self._voicebox_stt_row = IORow("VoiceBox STT", checked=self._settings.voicebox_stt_enabled)
        self._voicebox_stt_row.toggled.connect(self._on_voicebox_stt_toggled)
        layout.addWidget(self._voicebox_stt_row)

        self._apple_stt_row = IORow("Apple Native STT", checked=self._settings.apple_stt_enabled)
        self._apple_stt_row.toggled.connect(self._on_apple_stt_toggled)
        layout.addWidget(self._apple_stt_row)

        self._yamnet_row = IORow("YAMNet (sound)", checked=self._settings.yamnet_enabled)
        self._yamnet_row.toggled.connect(self._on_yamnet_toggled)
        layout.addWidget(self._yamnet_row)

        layout.addStretch()
        return group

    def _build_settings_column(self) -> QGroupBox:
        group = QGroupBox("Settings")
        layout = QVBoxLayout(group)

        self._session_button = QPushButton("Start Session")
        self._session_button.setObjectName("sessionButton")
        self._session_button.clicked.connect(self._toggle_session)
        layout.addWidget(self._session_button)

        self._status_label = QLabel("Mic: closed")
        self._status_label.setObjectName("micStatus")
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("Privacy Mode"))
        self._mode_selector = QComboBox()
        for mode in PrivacyMode:
            self._mode_selector.addItem(mode.label, mode)
        self._mode_selector.setCurrentIndex(self._settings.privacy_mode.value - 1)
        self._mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self._mode_selector)

        self._mqtt_row = IORow("MQTT publish", checked=self._settings.mqtt_publish_enabled)
        self._mqtt_row.toggled.connect(self._on_mqtt_publish_toggled)
        layout.addWidget(self._mqtt_row)

        self._spacebrew_row = IORow("Spacebrew 2.0 publish", checked=self._settings.spacebrew_publish_enabled)
        self._spacebrew_row.toggled.connect(self._on_spacebrew_publish_toggled)
        layout.addWidget(self._spacebrew_row)

        layout.addWidget(QLabel("Words"))
        self._word_ticker = QLabel("—")
        self._word_ticker.setObjectName("wordTicker")
        layout.addWidget(self._word_ticker)

        self._segments_feed = LiveFeedWidget("Segments")
        layout.addWidget(self._segments_feed, stretch=1)

        self._sounds_feed = LiveFeedWidget("Sounds (YAMNet)")
        layout.addWidget(self._sounds_feed, stretch=1)

        return group

    def _build_outputs_column(self) -> QGroupBox:
        group = QGroupBox("Audio Outputs")
        layout = QVBoxLayout(group)

        self._apple_tts_row = IORow("Apple Native TTS", checked=self._settings.apple_tts_enabled)
        self._apple_tts_row.toggled.connect(self._on_apple_tts_toggled)
        layout.addWidget(self._apple_tts_row)

        self._voicebox_tts_row = IORow("VoiceBox TTS", checked=self._settings.voicebox_tts_enabled)
        self._voicebox_tts_row.toggled.connect(self._on_voicebox_tts_toggled)
        layout.addWidget(self._voicebox_tts_row)

        self._song_gen_row = IORow("Song Generator", checked=False)
        self._song_gen_row.set_disabled_stub("TBD — no backend yet")
        layout.addWidget(self._song_gen_row)

        layout.addStretch()
        return group

    def _apply_initial_source_states(self):
        self._pipeline.set_voicebox_stt(self._voicebox_transcriber, self._voicebox_stt_row.is_on())

        if self._apple_stt_row.is_on():
            self._apple_transcriber = AppleSpeechTranscriber()
        self._pipeline.set_apple_stt(self._apple_transcriber, self._apple_stt_row.is_on())

        if self._yamnet_row.is_on():
            self._yamnet_classifier = self._make_yamnet_classifier()
        self._pipeline.set_yamnet(self._yamnet_classifier, self._yamnet_row.is_on())

    def _make_yamnet_classifier(self) -> YamnetClassifier:
        return YamnetClassifier(status_callback=lambda msg: self._pipeline.status_changed.emit({"yamnet": msg}))

    # ---- settings dialog ------------------------------------------------

    def _open_settings(self):
        dialog = SettingsDialog(self._settings, parent=self)
        if dialog.exec():
            self._voicebox_transcriber = VoiceBoxTranscriber(self._settings.voicebox_url)
            self._pipeline.set_voicebox_stt(self._voicebox_transcriber, self._voicebox_stt_row.is_on())
            self._reconnect_mqtt()
            self._reconnect_spacebrew()

    def _reconnect_mqtt(self):
        self._mqtt.disconnect()
        self._mqtt = MQTTClient(self._settings.mqtt_host, self._settings.mqtt_port)
        self._mqtt.connected.connect(self._on_mqtt_connected)
        self._mqtt.disconnected.connect(self._on_mqtt_disconnected)
        self._mqtt.error.connect(self._on_mqtt_error)
        self._mqtt_row.led.set_state(OFF_COLOR, lit=False)
        self._mqtt.connect_broker()

    def _reconnect_spacebrew(self):
        self._spacebrew.disconnect()
        self._spacebrew = SpacebrewClient(self._settings.spacebrew_host, self._settings.spacebrew_port)
        self._spacebrew.connected.connect(self._on_spacebrew_connected)
        self._spacebrew.disconnected.connect(self._on_spacebrew_disconnected)
        self._spacebrew.error.connect(self._on_spacebrew_error)
        self._spacebrew.tts_requested.connect(self._on_tts_requested)
        self._spacebrew_row.led.set_state(OFF_COLOR, lit=False)
        self._spacebrew.connect_broker()

    # ---- session --------------------------------------------------------

    def _toggle_session(self):
        if self._pipeline.isRunning():
            self._pipeline.stop()
            self._session_button.setText("Start Session")
        else:
            self._pipeline.start()
            self._session_button.setText("Stop Session")

    def _on_mode_changed(self, index: int):
        mode: PrivacyMode = self._mode_selector.itemData(index)
        self._pipeline.set_mode(mode)
        self._settings.privacy_mode = mode

    # ---- input toggles ----------------------------------------------------

    def _on_voicebox_stt_toggled(self, checked: bool):
        self._settings.voicebox_stt_enabled = checked
        self._pipeline.set_voicebox_stt(self._voicebox_transcriber, checked)

    def _on_apple_stt_toggled(self, checked: bool):
        self._settings.apple_stt_enabled = checked
        if checked and self._apple_transcriber is None:
            self._apple_transcriber = AppleSpeechTranscriber()
        self._pipeline.set_apple_stt(self._apple_transcriber, checked)

    def _on_yamnet_toggled(self, checked: bool):
        self._settings.yamnet_enabled = checked
        if checked and self._yamnet_classifier is None:
            self._yamnet_classifier = self._make_yamnet_classifier()
        self._pipeline.set_yamnet(self._yamnet_classifier, checked)

    def _on_source_activity(self, source: str):
        row = {
            "voicebox": self._voicebox_stt_row,
            "apple": self._apple_stt_row,
            "yamnet": self._yamnet_row,
        }.get(source)
        if row:
            row.pulse()

    # ---- output toggles ---------------------------------------------------

    def _on_apple_tts_toggled(self, checked: bool):
        self._settings.apple_tts_enabled = checked

    def _on_voicebox_tts_toggled(self, checked: bool):
        self._settings.voicebox_tts_enabled = checked

    # ---- publish toggles --------------------------------------------------

    def _on_mqtt_publish_toggled(self, checked: bool):
        self._settings.mqtt_publish_enabled = checked

    def _on_spacebrew_publish_toggled(self, checked: bool):
        self._settings.spacebrew_publish_enabled = checked

    # ---- audio events -------------------------------------------------

    def _on_audio_event(self, event: dict):
        kind = event["event"]
        if kind == "SpeechTranscribed":
            source = event.get("source", "?")
            self._segments_feed.add_entry(f'[{source}] "{event["text"]}" ({event["duration"]:.1f}s)')
            self._update_word_ticker(event["text"])
        elif kind == "SoundDetected":
            self._sounds_feed.add_entry(f'{event["label"]} ({event["confidence"]:.2f})')
        self._publish_event(event)

    def _update_word_ticker(self, text: str):
        self._recent_words.extend(text.split())
        self._recent_words = self._recent_words[-WORD_TICKER_LENGTH:]
        self._word_ticker.setText(" ".join(self._recent_words) or "—")

    def _publish_event(self, event: dict):
        kind = event["event"]
        mode = event["mode"]
        base = self._settings.mqtt_topic_base

        if kind == "SpeechTranscribed":
            topic, payload = mqtt_events.speech_transcribed(event["text"], event["duration"], mode, base)
            if self._mqtt_row.is_on():
                self._mqtt.publish(topic, payload)
                self._mqtt_row.pulse()
            self._publish_spacebrew_transcript(event["text"])
        elif kind == "SoundDetected":
            topic, payload = mqtt_events.sound_detected(event["label"], event["confidence"], mode, base)
            if self._mqtt_row.is_on():
                self._mqtt.publish(topic, payload)
                self._mqtt_row.pulse()
            if self._spacebrew_row.is_on():
                sb_name, sb_value = spacebrew_events.sound_detected(event["label"], event["confidence"], mode)
                self._spacebrew.publish(sb_name, sb_value)
                self._spacebrew_row.pulse()

    def _publish_spacebrew_transcript(self, text: str):
        if not self._spacebrew_row.is_on():
            return
        segment_name, segment_value = spacebrew_events.segment(text)
        self._spacebrew.publish(segment_name, segment_value)
        for w in text.split():
            word_name, word_value = spacebrew_events.word(w)
            self._spacebrew.publish(word_name, word_value)
        self._spacebrew_row.pulse()

    # ---- text-to-speech -----------------------------------------------

    def _on_tts_requested(self, text: str):
        if self._apple_tts_row.is_on():
            apple_tts.speak(text)
            self._apple_tts_row.pulse()
        if self._voicebox_tts_row.is_on():
            self._voicebox_tts_row.pulse()
            base_url = self._settings.voicebox_url
            threading.Thread(target=self._voicebox_tts_worker, args=(text, base_url), daemon=True).start()

    def _voicebox_tts_worker(self, text: str, base_url: str):
        try:
            voicebox_tts.speak(text, base_url)
        except Exception as e:  # noqa: BLE001
            self._tts_error.emit(f"VoiceBox TTS: {e}")

    # ---- status / connection indicators --------------------------------

    def _on_status(self, status: dict):
        parts = []
        for key, value in status.items():
            if key == "mic":
                self._status_label.setText(f"Mic: {value}")
                parts.append(f"Mic: {value}")
            elif key == "sample_rate":
                parts.append(f"{value} Hz")
            elif key == "error":
                parts.append(f"Error: {value}")
            else:
                parts.append(f"{key}: {value}")
        if parts:
            self.statusBar().showMessage("  |  ".join(parts))

    def _on_mqtt_connected(self):
        self._mqtt_row.led.set_state(IDLE_ON_COLOR, lit=True)
        host = self._settings.mqtt_host
        port = self._settings.mqtt_port
        self.statusBar().showMessage(f"MQTT connected: {host}:{port}", 3000)

    def _on_mqtt_disconnected(self):
        self._mqtt_row.led.set_state(OFF_COLOR, lit=False)

    def _on_mqtt_error(self, message: str):
        self._mqtt_row.led.set_state(ERROR_COLOR, lit=True)
        self.statusBar().showMessage(f"MQTT: {message}", 5000)

    def _on_spacebrew_connected(self):
        self._spacebrew_row.led.set_state(IDLE_ON_COLOR, lit=True)
        host = self._settings.spacebrew_host
        port = self._settings.spacebrew_port
        self.statusBar().showMessage(f"Spacebrew connected: {host}:{port}", 3000)

    def _on_spacebrew_disconnected(self):
        self._spacebrew_row.led.set_state(OFF_COLOR, lit=False)

    def _on_spacebrew_error(self, message: str):
        self._spacebrew_row.led.set_state(ERROR_COLOR, lit=True)
        self.statusBar().showMessage(f"Spacebrew: {message}", 5000)

    def closeEvent(self, event):
        if self._pipeline.isRunning():
            self._pipeline.stop()
        self._mqtt.disconnect()
        self._spacebrew.disconnect()
        super().closeEvent(event)

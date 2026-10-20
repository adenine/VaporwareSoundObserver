from __future__ import annotations

from PyQt6.QtCore import QSettings

from privacy.mode import PrivacyMode


class Settings:
    def __init__(self):
        self._qs = QSettings("Vaporware", "VaporwareSoundObserver")

    @property
    def mic_device(self) -> int | str | None:
        v = self._qs.value("mic/device", "")
        if v == "" or v is None:
            return None
        return int(v) if str(v).isdigit() else v

    @mic_device.setter
    def mic_device(self, value: int | str | None):
        self._qs.setValue("mic/device", value if value is not None else "")

    @property
    def voicebox_url(self) -> str:
        return self._qs.value("voicebox/url", "http://127.0.0.1:17493")

    @voicebox_url.setter
    def voicebox_url(self, value: str):
        self._qs.setValue("voicebox/url", value)

    @property
    def mqtt_host(self) -> str:
        return self._qs.value("mqtt/host", "localhost")

    @mqtt_host.setter
    def mqtt_host(self, value: str):
        self._qs.setValue("mqtt/host", value)

    @property
    def mqtt_port(self) -> int:
        return int(self._qs.value("mqtt/port", 1883))

    @mqtt_port.setter
    def mqtt_port(self, value: int):
        self._qs.setValue("mqtt/port", value)

    @property
    def mqtt_topic_base(self) -> str:
        return self._qs.value("mqtt/topic_base", "vaporwaresoundobserver")

    @mqtt_topic_base.setter
    def mqtt_topic_base(self, value: str):
        self._qs.setValue("mqtt/topic_base", value)

    @property
    def spacebrew_host(self) -> str:
        return self._qs.value("spacebrew/host", "localhost")

    @spacebrew_host.setter
    def spacebrew_host(self, value: str):
        self._qs.setValue("spacebrew/host", value)

    @property
    def spacebrew_port(self) -> int:
        return int(self._qs.value("spacebrew/port", 1883))

    @spacebrew_port.setter
    def spacebrew_port(self, value: int):
        self._qs.setValue("spacebrew/port", value)

    @property
    def privacy_mode(self) -> PrivacyMode:
        v = int(self._qs.value("privacy/mode", PrivacyMode.ANONYMIZED_REALTIME.value))
        return PrivacyMode(v)

    @privacy_mode.setter
    def privacy_mode(self, value: PrivacyMode):
        self._qs.setValue("privacy/mode", value.value)

    def _bool(self, key: str, default: bool) -> bool:
        v = self._qs.value(key, default)
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("true", "1")

    @property
    def voicebox_stt_enabled(self) -> bool:
        return self._bool("inputs/voicebox_stt_enabled", True)

    @voicebox_stt_enabled.setter
    def voicebox_stt_enabled(self, value: bool):
        self._qs.setValue("inputs/voicebox_stt_enabled", value)

    @property
    def apple_stt_enabled(self) -> bool:
        return self._bool("inputs/apple_stt_enabled", False)

    @apple_stt_enabled.setter
    def apple_stt_enabled(self, value: bool):
        self._qs.setValue("inputs/apple_stt_enabled", value)

    @property
    def yamnet_enabled(self) -> bool:
        return self._bool("inputs/yamnet_enabled", False)

    @yamnet_enabled.setter
    def yamnet_enabled(self, value: bool):
        self._qs.setValue("inputs/yamnet_enabled", value)

    @property
    def apple_tts_enabled(self) -> bool:
        return self._bool("outputs/apple_tts_enabled", True)

    @apple_tts_enabled.setter
    def apple_tts_enabled(self, value: bool):
        self._qs.setValue("outputs/apple_tts_enabled", value)

    @property
    def voicebox_tts_enabled(self) -> bool:
        return self._bool("outputs/voicebox_tts_enabled", False)

    @voicebox_tts_enabled.setter
    def voicebox_tts_enabled(self, value: bool):
        self._qs.setValue("outputs/voicebox_tts_enabled", value)

    @property
    def mqtt_publish_enabled(self) -> bool:
        return self._bool("mqtt/publish_enabled", True)

    @mqtt_publish_enabled.setter
    def mqtt_publish_enabled(self, value: bool):
        self._qs.setValue("mqtt/publish_enabled", value)

    @property
    def spacebrew_publish_enabled(self) -> bool:
        return self._bool("spacebrew/publish_enabled", True)

    @spacebrew_publish_enabled.setter
    def spacebrew_publish_enabled(self, value: bool):
        self._qs.setValue("spacebrew/publish_enabled", value)

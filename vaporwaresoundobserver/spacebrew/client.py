import paho.mqtt.client as mqtt
from PyQt6.QtCore import QObject, pyqtSignal


class SpacebrewClient(QObject):
    """Registers with a Spacebrew 2.0 router (github.com/.../Spacebrew2.0), which
    is itself just an MQTT client speaking a small registration protocol on top
    of the same broker: publish "name, desc, pubs(p:t,...), subs(s:t,...)" to
    the `YuxiSpace` topic, then publish routed data to `<name>/<pub>` and
    receive routed data on `<name>/<sub>`.
    """

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    tts_requested = pyqtSignal(str)

    DESCRIPTION = "Vaporware SoundObserver sound-event and speech publisher"
    # Kept in sync with spacebrew/events.py's message names.
    PUBLISHERS = ["word:string", "segments:string", "sound_detected:string"]
    # A word or a full segment routed here is spoken aloud via TTS.
    SUBSCRIBERS = ["tts:string"]

    def __init__(self, host: str = "localhost", port: int = 1883, name: str = "VaporwareSoundObserver"):
        super().__init__()
        self._host = host
        self._port = port
        self._name = name
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, name)
        self._client.will_set("YuxiSpace/leave", payload=name, qos=1)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def connect_broker(self):
        try:
            self._client.connect_async(self._host, self._port)
            self._client.loop_start()
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))

    def publish(self, name: str, value: str):
        self._client.publish(f"{self._name}/{name}", value, qos=1)

    def disconnect(self):
        try:
            self._client.publish("YuxiSpace/leave", self._name, qos=1).wait_for_publish()
        except Exception:  # noqa: BLE001
            pass
        self._client.loop_stop()
        self._client.disconnect()

    def _register(self):
        pubs_str = ", ".join(self.PUBLISHERS)
        subs_str = ", ".join(self.SUBSCRIBERS)
        registration = f"{self._name}, {self.DESCRIPTION}, pubs({pubs_str}), subs({subs_str})"
        self._client.publish("YuxiSpace", registration)
        for sub in self.SUBSCRIBERS:
            sub_name = sub.split(":")[0]
            self._client.subscribe(f"{self._name}/{sub_name}")

    # paho-mqtt v2 on_connect: (client, userdata, connect_flags, reason_code, properties)
    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            self.error.emit(f"Spacebrew connect failed: {reason_code}")
        else:
            self._register()
            self.connected.emit()

    # paho-mqtt v2 on_disconnect: (client, userdata, disconnect_flags, reason_code, properties)
    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.disconnected.emit()

    def _on_message(self, client, userdata, msg):
        if msg.topic == f"{self._name}/tts":
            self.tts_requested.emit(msg.payload.decode(errors="replace"))

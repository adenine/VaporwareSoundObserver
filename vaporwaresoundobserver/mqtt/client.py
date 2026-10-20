import paho.mqtt.client as mqtt
from PyQt6.QtCore import QObject, pyqtSignal


class MQTTClient(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, host: str = "localhost", port: int = 1883):
        super().__init__()
        self._host = host
        self._port = port
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect_broker(self):
        try:
            self._client.connect_async(self._host, self._port)
            self._client.loop_start()
        except Exception as e:
            self.error.emit(str(e))

    def publish(self, topic: str, payload: str):
        self._client.publish(topic, payload)

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    # paho-mqtt v2 on_connect: (client, userdata, connect_flags, reason_code, properties)
    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            self.error.emit(f"MQTT connect failed: {reason_code}")
        else:
            self.connected.emit()

    # paho-mqtt v2 on_disconnect: (client, userdata, disconnect_flags, reason_code, properties)
    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.disconnected.emit()

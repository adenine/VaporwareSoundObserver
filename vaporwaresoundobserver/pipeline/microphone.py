from __future__ import annotations

import numpy as np
import sounddevice as sd


class Microphone:
    """Captures mic audio into independently-flushable named buffers.

    Different consumers read the same live stream on different cadences
    (e.g. an 8s STT chunk vs a 1s YAMNet window), so each named buffer
    accumulates from the same callback but is cleared on its own schedule.
    """

    def __init__(self, device: int | str | None = None, sample_rate: int = 16000):
        self._device = device
        self._sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._buffers: dict[str, list[np.ndarray]] = {}

    def open(self, buffers: list[str] = ("stt",)):
        self._buffers = {name: [] for name in buffers}
        self._stream = sd.InputStream(
            device=self._device,
            channels=1,
            samplerate=self._sample_rate,
            callback=self._on_audio,
        )
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        chunk = indata.copy()
        for buf in self._buffers.values():
            buf.append(chunk)

    def flush(self, name: str = "stt") -> np.ndarray:
        """Return samples accumulated since the last flush of `name` and clear it."""
        buf = self._buffers.get(name)
        if not buf:
            return np.zeros((0, 1), dtype=np.float32)
        chunk = np.concatenate(buf)
        buf.clear()
        return chunk

    def close(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

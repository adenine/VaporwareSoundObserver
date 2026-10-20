from __future__ import annotations

import io
import time
import wave

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from pipeline.classifiers.base import BaseClassifier
from pipeline.microphone import Microphone
from pipeline.transcribers.base import BaseTranscriber
from privacy.mode import PrivacyMode


def _encode_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    pcm16 = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm16.tobytes())
    return buf.getvalue()


class Pipeline(QThread):
    audio_event = pyqtSignal(dict)
    status_changed = pyqtSignal(dict)
    # Emitted the moment a source is dispatched (before its result comes
    # back) so the UI can pulse that source's LED immediately.
    source_activity = pyqtSignal(str)

    STT_CHUNK_SECONDS = 8
    YAMNET_CHUNK_SECONDS = 1

    def __init__(self):
        super().__init__()
        self._mic = Microphone()
        self._mode = PrivacyMode.ANONYMIZED_REALTIME
        self._running = False

        self._voicebox_stt: BaseTranscriber | None = None
        self._voicebox_stt_enabled = False
        self._apple_stt: BaseTranscriber | None = None
        self._apple_stt_enabled = False
        self._yamnet: BaseClassifier | None = None
        self._yamnet_enabled = False

    def set_mic_device(self, device: int | str | None):
        self._mic = Microphone(device)

    def set_mode(self, mode: PrivacyMode):
        if mode == self._mode:
            return
        self._mode = mode
        self.status_changed.emit({"mode": mode.label})

    def set_voicebox_stt(self, transcriber: BaseTranscriber | None, enabled: bool):
        self._voicebox_stt = transcriber
        self._voicebox_stt_enabled = enabled

    def set_apple_stt(self, transcriber: BaseTranscriber | None, enabled: bool):
        self._apple_stt = transcriber
        self._apple_stt_enabled = enabled

    def set_yamnet(self, classifier: BaseClassifier | None, enabled: bool):
        self._yamnet = classifier
        self._yamnet_enabled = enabled

    def run(self):
        self._running = True
        self._mic.open(buffers=["stt", "yamnet"])
        self.status_changed.emit({"mic": "open", "sample_rate": self._mic.sample_rate})

        next_stt_flush = time.monotonic() + self.STT_CHUNK_SECONDS
        next_yamnet_flush = time.monotonic() + self.YAMNET_CHUNK_SECONDS
        while self._running:
            time.sleep(0.1)
            now = time.monotonic()
            if now >= next_stt_flush:
                next_stt_flush = now + self.STT_CHUNK_SECONDS
                self._process_stt_chunk()
            if now >= next_yamnet_flush:
                next_yamnet_flush = now + self.YAMNET_CHUNK_SECONDS
                self._process_yamnet_chunk()

        self._mic.close()
        self.status_changed.emit({"mic": "closed"})

    def _process_stt_chunk(self):
        samples = self._mic.flush("stt")
        if samples.size == 0:
            return
        if self._mode != PrivacyMode.ANONYMIZED_REALTIME:
            # Modes 2/3 (anonymous speaker diarization, named speaker
            # identification) are stubs — see README status table. Mode 1
            # already transcribes; 2/3 only differ in identity attribution,
            # which isn't built yet.
            return

        wav_bytes = _encode_wav(samples, self._mic.sample_rate)
        if self._voicebox_stt_enabled and self._voicebox_stt:
            self._run_transcriber("voicebox", self._voicebox_stt, wav_bytes)
        if self._apple_stt_enabled and self._apple_stt:
            self._run_transcriber("apple", self._apple_stt, wav_bytes)

    def _run_transcriber(self, source: str, transcriber: BaseTranscriber, wav_bytes: bytes):
        self.source_activity.emit(source)
        try:
            result = transcriber.transcribe(wav_bytes, "chunk.wav")
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit({"error": f"{source}: {e}"})
            return
        if result and result.text.strip():
            self.audio_event.emit(
                {
                    "event": "SpeechTranscribed",
                    "text": result.text,
                    "duration": result.duration,
                    "mode": self._mode,
                    "source": source,
                }
            )

    def _process_yamnet_chunk(self):
        if not (self._yamnet_enabled and self._yamnet):
            self._mic.flush("yamnet")
            return
        samples = self._mic.flush("yamnet")
        if samples.size == 0:
            return
        if self._mode != PrivacyMode.ANONYMIZED_REALTIME:
            return

        self.source_activity.emit("yamnet")
        try:
            result = self._yamnet.classify(samples.reshape(-1), self._mic.sample_rate)
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit({"error": f"yamnet: {e}"})
            return
        if result:
            self.audio_event.emit(
                {
                    "event": "SoundDetected",
                    "label": result.label,
                    "confidence": result.confidence,
                    "mode": self._mode,
                    "source": "yamnet",
                }
            )

    def stop(self):
        self._running = False
        self.wait()

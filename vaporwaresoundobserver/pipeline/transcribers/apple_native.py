from __future__ import annotations

import tempfile
import threading
import wave
from pathlib import Path

from pipeline.transcribers.base import BaseTranscriber, TranscriptionResult


class AppleSpeechTranscriber(BaseTranscriber):
    """On-device transcription via macOS's Speech.framework (SFSpeechRecognizer).

    Mirrors VoiceBoxTranscriber's shape (bytes-in, TranscriptionResult-out)
    so it drops into the same chunk-based pipeline unchanged. Each chunk is
    written to a temp WAV file and recognized synchronously — the completion
    handler fires on a framework-owned queue, so a threading.Event is used
    to block the calling (pipeline) thread until it arrives.
    """

    def __init__(self, locale: str = "en-US", timeout: float = 20.0):
        self._locale = locale
        self._timeout = timeout
        self._recognizer = None
        self._authorized: bool | None = None

    def _ensure_authorized(self):
        if self._authorized is not None:
            return
        import Speech

        done = threading.Event()
        result = {}

        def handler(status):
            result["status"] = status
            done.set()

        Speech.SFSpeechRecognizer.requestAuthorization_(handler)
        done.wait(self._timeout)
        self._authorized = result.get("status") == Speech.SFSpeechRecognizerAuthorizationStatusAuthorized

        if not self._authorized:
            raise RuntimeError("Speech recognition not authorized (check System Settings > Privacy > Speech Recognition)")

    def _ensure_recognizer(self):
        if self._recognizer is not None:
            return
        import Speech
        from Foundation import NSLocale

        self._recognizer = Speech.SFSpeechRecognizer.alloc().initWithLocale_(NSLocale.localeWithLocaleIdentifier_(self._locale))
        if self._recognizer is None or not self._recognizer.isAvailable():
            raise RuntimeError(f"Apple Speech recognizer unavailable for locale {self._locale}")

    def transcribe(
        self, audio_bytes: bytes, filename: str = "chunk.wav", language: str | None = None
    ) -> TranscriptionResult | None:
        import Speech
        from Foundation import NSURL

        self._ensure_authorized()
        self._ensure_recognizer()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            duration = self._wav_duration(tmp_path)
            url = NSURL.fileURLWithPath_(tmp_path)
            request = Speech.SFSpeechURLRecognitionRequest.alloc().initWithURL_(url)
            request.setRequiresOnDeviceRecognition_(True)
            request.setShouldReportPartialResults_(False)

            done = threading.Event()
            result = {}

            def handler(recognition_result, error):
                if error is not None:
                    result["error"] = str(error)
                    done.set()
                    return
                if recognition_result is not None and recognition_result.isFinal():
                    result["text"] = str(recognition_result.bestTranscription().formattedString())
                    done.set()

            self._recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)
            if not done.wait(self._timeout):
                raise RuntimeError("Apple Speech recognition timed out")
            if "error" in result:
                raise RuntimeError(result["error"])

            text = result.get("text", "")
            if not text.strip():
                return None
            return TranscriptionResult(text=text, duration=duration)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _wav_duration(path: str) -> float:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())

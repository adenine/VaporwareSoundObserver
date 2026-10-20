from __future__ import annotations

import requests

from pipeline.transcribers.base import BaseTranscriber, TranscriptionResult


class VoiceBoxTranscriber(BaseTranscriber):
    """Calls VoiceBox's local /transcribe REST endpoint.

    Validated against a real running VoiceBox instance while
    prototyping in vaporware-core before this module was extracted
    into its own project: VoiceBox can return 202 (Whisper model still
    downloading) with a body that has no "text" field, so success is
    judged by the field's presence, not just the HTTP status code.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:17493", timeout: float = 30.0):
        self._base_url = base_url
        self._timeout = timeout

    def transcribe(
        self, audio_bytes: bytes, filename: str = "chunk.wav", language: str | None = None
    ) -> TranscriptionResult | None:
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data = {"language": language} if language else {}
        resp = requests.post(f"{self._base_url}/transcribe", files=files, data=data, timeout=self._timeout)
        body = resp.json()
        if resp.status_code != 200 or "text" not in body:
            detail = body.get("detail", body)
            if isinstance(detail, dict):
                detail = detail.get("message", str(detail))
            raise RuntimeError(f"{resp.status_code}: {detail}")
        return TranscriptionResult(text=body["text"], duration=body["duration"])

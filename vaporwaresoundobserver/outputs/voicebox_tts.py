from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import requests

_CONTENT_TYPE_EXT = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".m4a",
}

_TERMINAL_STATUSES = {"completed", "failed", "error", "cancelled"}


def speak(text: str, base_url: str, timeout: float = 60.0, poll_interval: float = 0.5):
    """Speak text aloud via a local VoiceBox instance's /speak REST flow.

    POST /speak kicks off generation and returns an id; poll
    GET /generate/{id}/status until it leaves "generating", then fetch the
    rendered audio from GET /audio/{id} and play it with `afplay`. Runs
    synchronously — callers dispatch this on a background thread so a slow
    VoiceBox round trip never blocks the UI.
    """
    text = text.strip()
    if not text:
        return

    resp = requests.post(f"{base_url}/speak", json={"text": text}, timeout=10)
    resp.raise_for_status()
    generation_id = resp.json()["id"]

    deadline = time.monotonic() + timeout
    status = "generating"
    while status not in _TERMINAL_STATUSES and time.monotonic() < deadline:
        time.sleep(poll_interval)
        status_resp = requests.get(f"{base_url}/generate/{generation_id}/status", timeout=10)
        status_resp.raise_for_status()
        status = status_resp.json().get("status", "generating")

    if status != "completed":
        raise RuntimeError(f"VoiceBox generation did not complete (status={status})")

    audio_resp = requests.get(f"{base_url}/audio/{generation_id}", timeout=30)
    audio_resp.raise_for_status()

    content_type = audio_resp.headers.get("content-type", "").split(";")[0].strip()
    ext = _CONTENT_TYPE_EXT.get(content_type, ".wav")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_resp.content)
        tmp_path = f.name

    try:
        subprocess.run(["afplay", tmp_path], check=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

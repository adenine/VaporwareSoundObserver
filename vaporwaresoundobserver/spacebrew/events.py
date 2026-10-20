import json

from privacy.mode import PrivacyMode


def word(text: str) -> tuple[str, str]:
    return "word", text


def segment(text: str) -> tuple[str, str]:
    return "segments", text


def sound_detected(label: str, confidence: float, mode: PrivacyMode) -> tuple[str, str]:
    payload = {"label": label, "confidence": confidence, "mode": mode.value}
    return "sound_detected", json.dumps(payload)

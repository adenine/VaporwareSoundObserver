import json

from privacy.mode import PrivacyMode


def speech_transcribed(
    text: str, duration: float, mode: PrivacyMode, topic_base: str = "vaporwaresoundobserver"
) -> tuple[str, str]:
    payload = {"text": text, "duration": duration, "mode": mode.value}
    return f"{topic_base}/speech/transcribed", json.dumps(payload)


def sound_detected(
    label: str, confidence: float, mode: PrivacyMode, topic_base: str = "vaporwaresoundobserver"
) -> tuple[str, str]:
    payload = {"label": label, "confidence": confidence, "mode": mode.value}
    return f"{topic_base}/sound/detected", json.dumps(payload)


def speaker_entered(speaker_id, mode: PrivacyMode, topic_base: str = "vaporwaresoundobserver") -> tuple[str, str]:
    payload = {"id": speaker_id, "mode": mode.value}
    return f"{topic_base}/speaker/entered", json.dumps(payload)


def speaker_exited(speaker_id, mode: PrivacyMode, topic_base: str = "vaporwaresoundobserver") -> tuple[str, str]:
    payload = {"id": speaker_id, "mode": mode.value}
    return f"{topic_base}/speaker/exited", json.dumps(payload)

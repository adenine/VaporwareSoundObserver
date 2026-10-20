from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    duration: float


class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(
        self, audio_bytes: bytes, filename: str, language: str | None = None
    ) -> TranscriptionResult: ...

    def close(self):
        pass

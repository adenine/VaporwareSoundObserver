from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

import numpy as np
import requests

from pipeline.classifiers.base import BaseClassifier, ClassificationResult


class YamnetClassifier(BaseClassifier):
    """Local ambient-sound classification via the MediaPipe YAMNet tflite model.

    Takes a raw 16kHz mono waveform directly (no manual mel-spectrogram
    step — this model bundles feature extraction). Model + class map are
    downloaded once to ~/.cache/vaporwaresoundobserver/yamnet/ on first use.
    """

    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite"
    CLASS_MAP_URL = (
        "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
    )
    CACHE_DIR = Path.home() / ".cache" / "vaporwaresoundobserver" / "yamnet"
    DEFAULT_INPUT_LENGTH = 15600  # 0.975s at 16kHz, YAMNet's native frame size
    CONFIDENCE_FLOOR = 0.3
    SILENCE_LABELS = {"Silence"}

    def __init__(self, status_callback: Callable[[str], None] | None = None):
        self._status_callback = status_callback
        self._interpreter = None
        self._labels: list[str] = []
        self._input_index = None
        self._output_index = None
        self._input_length = self.DEFAULT_INPUT_LENGTH

    def _status(self, message: str):
        if self._status_callback:
            self._status_callback(message)

    def _ensure_loaded(self):
        if self._interpreter is not None:
            return

        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        model_path = self.CACHE_DIR / "yamnet.tflite"
        class_map_path = self.CACHE_DIR / "yamnet_class_map.csv"

        if not model_path.exists():
            self._status("Downloading YAMNet model…")
            self._download(self.MODEL_URL, model_path)
        if not class_map_path.exists():
            self._status("Downloading YAMNet class map…")
            self._download(self.CLASS_MAP_URL, class_map_path)

        self._labels = self._load_labels(class_map_path)

        from ai_edge_litert.interpreter import Interpreter

        interpreter = Interpreter(model_path=str(model_path))
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        self._input_index = input_details[0]["index"]
        self._output_index = output_details[0]["index"]

        shape = input_details[0]["shape"]
        # Fixed-length waveform input reports its true length; a dynamic
        # input reports a placeholder like [1] and must be resized first.
        if len(shape) and shape[-1] > 1:
            self._input_length = int(shape[-1])
        interpreter.resize_tensor_input(self._input_index, [self._input_length])
        interpreter.allocate_tensors()

        self._interpreter = interpreter
        self._status("YAMNet ready")

    @staticmethod
    def _download(url: str, dest: Path):
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)

    @staticmethod
    def _load_labels(class_map_path: Path) -> list[str]:
        with open(class_map_path, newline="") as f:
            return [row["display_name"] for row in csv.DictReader(f)]

    def classify(self, samples: np.ndarray, sample_rate: int) -> ClassificationResult | None:
        if samples.size == 0:
            return None
        self._ensure_loaded()

        waveform = samples.reshape(-1).astype(np.float32)
        waveform = self._fit_length(waveform, self._input_length)

        self._interpreter.set_tensor(self._input_index, waveform)
        self._interpreter.invoke()
        scores = self._interpreter.get_tensor(self._output_index)
        if scores.ndim == 2:
            # Per-frame scores [frames, classes] — average over the window.
            scores = scores.mean(axis=0)

        top_index = int(np.argmax(scores))
        confidence = float(scores[top_index])
        label = self._labels[top_index] if top_index < len(self._labels) else f"class_{top_index}"

        if confidence < self.CONFIDENCE_FLOOR or label in self.SILENCE_LABELS:
            return None
        return ClassificationResult(label=label, confidence=confidence)

    @staticmethod
    def _fit_length(waveform: np.ndarray, length: int) -> np.ndarray:
        if waveform.shape[0] == length:
            return waveform
        if waveform.shape[0] > length:
            return waveform[:length]
        return np.pad(waveform, (0, length - waveform.shape[0]))

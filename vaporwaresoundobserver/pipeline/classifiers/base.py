from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class ClassificationResult:
    label: str
    confidence: float


class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, samples: np.ndarray, sample_rate: int) -> ClassificationResult | None: ...

    def close(self):
        pass

from enum import Enum


class PrivacyMode(Enum):
    ANONYMIZED_REALTIME = 1
    ANONYMIZED_RECOGNITION = 2
    IDENTIFIED_RECOGNITION = 3

    @property
    def label(self) -> str:
        return {
            PrivacyMode.ANONYMIZED_REALTIME: "Mode 1: Anonymized Realtime",
            PrivacyMode.ANONYMIZED_RECOGNITION: "Mode 2: Anonymized Recognition",
            PrivacyMode.IDENTIFIED_RECOGNITION: "Mode 3: Identified Recognition",
        }[self]

"""
Wake word and stop word detection — uses openWakeWord for wake word detection.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Offline wake word detection using openWakeWord.

    Usage:
        detector = WakeWordDetector(model="hey_jarvis")
        detector.start()
        ...
        result = detector.process_chunk(pcm_bytes)
        if result == "wake":
            # start listening
    """

    WAKE_WORDS = "wake"

    def __init__(
        self,
        model: str = "hey_jarvis",
        stop_model: str = "stop",
        refractory_seconds: float = 2.0,
        sensitivity: float = 0.5,
    ):
        self._model_name = model
        self._refractory_seconds = refractory_seconds
        self._sensitivity = sensitivity
        self._last_wake_time = 0.0
        self._oww_model = None
        self._block_size = 1280  # 80ms at 16kHz

    def start(self):
        """Load wake word model."""
        try:
            self._load_models()
            logger.info("Wake word detector started with model=%s", self._model_name)
        except Exception as e:
            logger.error("Failed to load wake word models: %s", e)
            logger.info("Will try to continue without wake word detection")

    def _load_models(self):
        """Load openWakeWord model."""
        from openwakeword.model import Model

        self._oww_model = Model(wakeword_models=[self._model_name])
        logger.info("Loaded openWakeWord model: %s", self._model_name)

    def process_chunk(self, pcm_bytes: bytes) -> Optional[str]:
        """Process a PCM audio chunk and detect wake word.

        Args:
            pcm_bytes: 16-bit signed little-endian PCM, 16kHz mono.

        Returns:
            "wake" if wake word detected, None otherwise.
        """
        if self._oww_model is None:
            return None

        try:
            # openWakeWord expects numpy array of int16
            pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)
            prediction = self._oww_model.predict(pcm_array)

            # Log all predictions for debugging
            for name, score in prediction.items():
                if score > 0.2:
                    logger.debug("Wake score: %s=%.3f", name, score)

            # Check prediction score
            for name, score in prediction.items():
                if score > self._sensitivity:
                    now = time.monotonic()
                    if now - self._last_wake_time > self._refractory_seconds:
                        self._last_wake_time = now
                        logger.info("Wake word DETECTED: %s (score=%.3f)", name, score)
                        return self.WAKE_WORDS

        except Exception as e:
            logger.debug("Wake detection error: %s", e)

        return None

    @property
    def is_loaded(self) -> bool:
        return self._oww_model is not None
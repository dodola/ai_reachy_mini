"""
Wake word and stop word detection — uses pymicro_wakeword and pyopen_wakeword
to detect activation phrases offline on the Reachy Mini's audio stream.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Offline wake word and stop word detection.

    Uses pymicro_wakeword (TFLite) for primary wake word detection
    and pyopen_wakeword for additional models.

    Usage:
        detector = WakeWordDetector(model="okay_nabu", stop_model="stop")
        detector.start()
        ...
        result = detector.process_chunk(pcm_bytes)
        if result == "wake":
            # start listening
        elif result == "stop":
            # abort TTS
    """

    WAKE_WORDS = "wake"
    STOP_WORD = "stop"

    def __init__(
        self,
        model: str = "okay_nabu",
        stop_model: str = "stop",
        refractory_seconds: float = 2.0,
        sensitivity: float = 0.5,
    ):
        self._model_name = model
        self._stop_model_name = stop_model
        self._refractory_seconds = refractory_seconds
        self._sensitivity = sensitivity
        self._last_wake_time = 0.0

        self._wake_models = []
        self._stop_model = None
        self._micro_features = None
        self._oww_features = None
        self._has_oww = False
        self._block_size = 512

        self._audio_buffer: deque[float] = deque(maxlen=self._block_size * 40)

    def start(self):
        """Load wake word and stop word models."""
        try:
            self._load_models()
            logger.info("Wake word detector started with model=%s", self._model_name)
        except Exception as e:
            logger.error("Failed to load wake word models: %s", e)
            logger.info("Will try to continue without wake word detection")

    def _load_models(self):
        """Load all wake word and stop word models."""
        from pymicro_wakeword import MicroWakeWord, MicroWakeWordFeatures

        self._micro_features = MicroWakeWordFeatures()

        wake_model = MicroWakeWord.from_slug(self._model_name)
        if wake_model is not None:
            self._wake_models.append(wake_model)
            logger.info("Loaded wake model: %s", self._model_name)

        try:
            stop_model = MicroWakeWord.from_slug(self._stop_model_name)
            if stop_model is not None:
                self._stop_model = stop_model
                logger.info("Loaded stop model: %s", self._stop_model_name)
        except Exception as e:
            logger.warning("Could not load stop model: %s", e)

        try:
            from pyopen_wakeword import OpenWakeWord, OpenWakeWordFeatures
            self._oww_features = OpenWakeWordFeatures.from_builtin()
            oww = OpenWakeWord()
            self._has_oww = True
            self._wake_models.append(oww)
            logger.info("Loaded OpenWakeWord model")
        except ImportError:
            logger.info("pyopen_wakeword not available, skipping")
        except Exception as e:
            logger.warning("Failed to load OpenWakeWord: %s", e)

        if not self._wake_models:
            logger.warning("No wake word models loaded — detection disabled")

    def process_chunk(self, pcm_bytes: bytes) -> Optional[str]:
        """Process a PCM audio chunk and detect wake/stop words.

        Args:
            pcm_bytes: 16-bit signed little-endian PCM, 16kHz mono,
                       self._block_size samples.

        Returns:
            "wake" if wake word detected,
            "stop" if stop word detected,
            None otherwise.
        """
        if not self._wake_models:
            return None

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)

        self._audio_buffer.extend(samples.tolist())

        if len(self._audio_buffer) < self._block_size:
            return None

        chunk = np.array([self._audio_buffer.popleft() for _ in range(self._block_size)], dtype=np.float32)
        result = None

        try:
            micro_inputs = self._micro_features.process_streaming(pcm_bytes) if self._micro_features else []

            for model in self._wake_models:
                activated = False
                try:
                    from pymicro_wakeword import MicroWakeWord
                    from pyopen_wakeword import OpenWakeWord

                    if isinstance(model, MicroWakeWord):
                        for micro_input in micro_inputs:
                            if model.process_streaming(micro_input):
                                activated = True
                    elif isinstance(model, OpenWakeWord):
                        if self._oww_features:
                            oww_inputs = self._oww_features.process_streaming(pcm_bytes)
                            for prob in model.process_streaming(oww_inputs):
                                if prob > self._sensitivity:
                                    activated = True
                except Exception as e:
                    logger.debug("Wake model error: %s", e)
                    continue

                if activated:
                    now = time.monotonic()
                    if now - self._last_wake_time > self._refractory_seconds:
                        self._last_wake_time = now
                        result = self.WAKE_WORDS
                        logger.info("Wake word detected!")
                        break

            if result is None and self._stop_model and self._is_active_context():
                for micro_input in micro_inputs:
                    try:
                        if self._stop_model.process_streaming(micro_input):
                            result = self.STOP_WORD
                            logger.info("Stop word detected!")
                            break
                    except Exception:
                        pass

        except Exception as e:
            logger.debug("Process chunk error: %s", e)

        return result

    def _is_active_context(self) -> bool:
        """Check if stop word should be active (during TTS playback)."""
        return time.monotonic() - self._last_wake_time < 30.0

    @property
    def is_loaded(self) -> bool:
        return len(self._wake_models) > 0
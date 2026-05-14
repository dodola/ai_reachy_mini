"""
OPUS codec wrapper — encode/decode for xiaozhi WebSocket audio streaming.

Encode: 16kHz mono PCM int16 → OPUS frame (60ms)
Decode: OPUS frame → 16kHz or 24kHz mono PCM int16
"""

from __future__ import annotations

import logging
import struct

import numpy as np

logger = logging.getLogger(__name__)

try:
    import opuslib

    HAS_OPUSLIB = True
except ImportError:
    HAS_OPUSLIB = False
    logger.warning("opuslib not available — audio will use raw PCM fallback")


class OpusCodec:
    """OPUS encoder/decoder for xiaozhi audio streaming."""

    FRAME_DURATION_MS = 60
    INPUT_SAMPLE_RATE = 16000
    OUTPUT_SAMPLE_RATE = 24000
    CHANNELS = 1

    def __init__(self):
        self._encoder = None
        self._decoder = None
        self._use_opus = HAS_OPUSLIB
        self._frame_size = int(self.INPUT_SAMPLE_RATE * self.FRAME_DURATION_MS / 1000)

        if self._use_opus:
            try:
                self._encoder = opuslib.Encoder(
                    self.INPUT_SAMPLE_RATE, self.CHANNELS, opuslib.APPLICATION_VOIP
                )
                self._decoder = opuslib.Decoder(self.OUTPUT_SAMPLE_RATE, self.CHANNELS)
                logger.info(
                    "OPUS codec initialized: encode=%dHz decode=%dHz frame=%dms",
                    self.INPUT_SAMPLE_RATE,
                    self.OUTPUT_SAMPLE_RATE,
                    self.FRAME_DURATION_MS,
                )
            except Exception as e:
                logger.warning("Failed to init OPUS codec: %s — using PCM fallback", e)
                self._use_opus = False
                self._encoder = None
                self._decoder = None

    @property
    def use_opus(self) -> bool:
        return self._use_opus

    @property
    def frame_size(self) -> int:
        """Number of samples per frame at input sample rate."""
        return self._frame_size

    @property
    def input_bytes_per_frame(self) -> int:
        """Expected bytes per PCM frame (int16 mono)."""
        return self._frame_size * 2

    def encode(self, pcm_bytes: bytes) -> bytes | None:
        """Encode PCM int16 bytes → OPUS frame bytes.

        Args:
            pcm_bytes: Raw PCM data, 16-bit signed little-endian, mono, 16kHz.
                       Must be exactly frame_size * 2 bytes.

        Returns:
            OPUS-encoded bytes, or None if encoding fails.
        """
        if not self._use_opus or self._encoder is None:
            return pcm_bytes

        if len(pcm_bytes) != self.input_bytes_per_frame:
            logger.warning(
                "PCM frame size mismatch: got %d, expected %d",
                len(pcm_bytes),
                self.input_bytes_per_frame,
            )
            if len(pcm_bytes) < self.input_bytes_per_frame:
                pcm_bytes = pcm_bytes + b"\x00" * (self.input_bytes_per_frame - len(pcm_bytes))
            else:
                pcm_bytes = pcm_bytes[: self.input_bytes_per_frame]

        try:
            return self._encoder.encode(pcm_bytes, self._frame_size)
        except Exception as e:
            logger.error("OPUS encode error: %s", e)
            return None

    def decode(self, opus_frame: bytes) -> bytes | None:
        """Decode OPUS frame → PCM int16 bytes at output sample rate.

        Args:
            opus_frame: OPUS-encoded bytes.

        Returns:
            PCM int16 bytes at OUTPUT_SAMPLE_RATE (24kHz mono), or None.
        """
        if not self._use_opus or self._decoder is None:
            return opus_frame

        try:
            decode_frame_size = int(self.OUTPUT_SAMPLE_RATE * self.FRAME_DURATION_MS / 1000)
            pcm = self._decoder.decode(opus_frame, decode_frame_size)
            return pcm
        except Exception as e:
            logger.error("OPUS decode error: %s", e)
            return None

    @staticmethod
    def pcm_to_float32(pcm_bytes: bytes) -> np.ndarray:
        """Convert PCM int16 bytes → float32 array [-1, 1]."""
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return np.clip(samples, -1.0, 1.0)

    @staticmethod
    def float32_to_pcm(float_array: np.ndarray) -> bytes:
        """Convert float32 array [-1, 1] → PCM int16 bytes."""
        return (np.clip(float_array, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()

    @staticmethod
    def resample(data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """Resample float32 audio array using scipy."""
        if src_rate == dst_rate:
            return data
        from scipy.signal import resample

        new_len = int(len(data) * dst_rate / src_rate)
        if new_len <= 0:
            return np.array([], dtype=np.float32)
        return resample(data, new_len).astype(np.float32)
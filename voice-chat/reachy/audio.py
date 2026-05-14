"""
Reachy Mini audio bridge — microphone capture and speaker playback.

Uses reachy-mini-sdk to capture audio from the built-in microphone array
and push audio to the built-in speaker. The SDK handles GStreamer pipeline
management internally.

Audio pipeline:
  Mic:  get_audio_sample() → float32 (samples,2) → mono float32 → PCM int16 → OPUS → WS
  Spk:  WS → OPUS → PCM int16 → float32 → resample 24kHz→16kHz → push_audio_sample()
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class ReachyAudioBridge:
    """Bridge between Reachy Mini hardware audio and the xiaozhi client."""

    BLOCK_SIZE = 512
    MIC_SAMPLE_RATE = 16000

    def __init__(self, reachy_mini, codec, config: Optional[dict] = None):
        self._mini = reachy_mini
        self._codec = codec
        self._config = config or {}

        self._speaker_buffer_seconds = self._config.get("speaker_buffer_seconds", 2.0)
        self._mic_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=100)
        self._spk_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=200)

        self._mic_thread: Optional[threading.Thread] = None
        self._spk_thread: Optional[threading.Thread] = None
        self._running = False
        self._recording = False
        self._playing = False

    def start(self):
        """Start microphone capture and speaker playback."""
        self._running = True
        self._mini.media.start_recording()
        self._mini.media.start_playing()
        self._recording = True
        self._playing = True
        logger.info("Audio bridge started: mic + speaker")

        self._mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
        self._spk_thread = threading.Thread(target=self._spk_loop, daemon=True)
        self._mic_thread.start()
        self._spk_thread.start()

    def stop(self):
        """Stop all audio processing."""
        self._running = False
        self._mic_queue.put(None)
        self._spk_queue.put(None)

        if self._mic_thread:
            self._mic_thread.join(timeout=2.0)
        if self._spk_thread:
            self._spk_thread.join(timeout=2.0)

        try:
            self._mini.media.stop_recording()
        except Exception:
            pass
        try:
            self._mini.media.stop_playing()
        except Exception:
            pass
        self._recording = False
        self._playing = False
        logger.info("Audio bridge stopped")

    def get_mic_frame(self, timeout: float = 0.1) -> Optional[bytes]:
        """Get one PCM frame from the microphone queue (blocking).

        Returns PCM int16 bytes, 16kHz mono, BLOCK_SIZE samples.
        """
        try:
            return self._mic_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def push_speaker_frame(self, opus_frame: bytes):
        """Push an OPUS frame to the speaker queue."""
        if opus_frame and self._running:
            try:
                self._spk_queue.put_nowait(opus_frame)
            except queue.Full:
                logger.warning("Speaker queue full, dropping frame")

    def _mic_loop(self):
        """Background thread: capture audio from Reachy Mini microphone."""
        import numpy as np

        audio_buffer = []
        target_samples = self.BLOCK_SIZE

        while self._running:
            try:
                sample = self._mini.media.get_audio_sample()
                if sample is None or not isinstance(sample, np.ndarray) or sample.size == 0:
                    time.sleep(0.005)
                    continue

                audio = sample.astype(np.float32, copy=False)
                audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)

                if audio.ndim == 2 and audio.shape[1] >= 2:
                    audio = audio[:, 0]
                elif audio.ndim == 2:
                    audio = audio[:, 0]

                src_rate = self._mini.media.get_input_audio_samplerate()
                if src_rate != self.MIC_SAMPLE_RATE and src_rate > 0:
                    from scipy.signal import resample
                    new_len = int(len(audio) * self.MIC_SAMPLE_RATE / src_rate)
                    if new_len > 0:
                        audio = resample(audio, new_len).astype(np.float32)

                audio_buffer.extend(audio.tolist())

                while len(audio_buffer) >= target_samples:
                    chunk = audio_buffer[:target_samples]
                    audio_buffer = audio_buffer[target_samples:]
                    pcm = (np.clip(np.array(chunk, dtype=np.float32), -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                    try:
                        self._mic_queue.put_nowait(pcm)
                    except queue.Full:
                        pass

            except Exception as e:
                if self._running:
                    logger.error("Mic loop error: %s", e)
                    time.sleep(0.05)

    def _spk_loop(self):
        """Background thread: decode OPUS and push to Reachy Mini speaker."""
        target_rate = 16000

        while self._running:
            try:
                opus_frame = self._spk_queue.get(timeout=0.1)
                if opus_frame is None:
                    continue

                pcm_bytes = self._codec.decode(opus_frame)
                if pcm_bytes is None:
                    continue

                audio_float = self._codec.pcm_to_float32(pcm_bytes)

                src_rate = self._codec.OUTPUT_SAMPLE_RATE
                if src_rate != target_rate:
                    audio_float = self._codec.resample(audio_float, src_rate, target_rate)

                audio_float = np.nan_to_num(audio_float, nan=0.0, posinf=1.0, neginf=-1.0)
                audio_float = np.clip(audio_float, -1.0, 1.0)

                if audio_float.ndim == 1:
                    audio_float = audio_float.reshape(-1, 1)

                try:
                    self._mini.media.push_audio_sample(audio_float)
                except Exception as e:
                    if self._running:
                        logger.debug("push_audio_sample error: %s", e)

            except queue.Empty:
                continue
            except Exception as e:
                if self._running:
                    logger.error("Speaker loop error: %s", e)
                    time.sleep(0.05)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_playing(self) -> bool:
        return self._playing
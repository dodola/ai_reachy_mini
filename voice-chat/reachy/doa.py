"""
Direction-of-Arrival (DoA) tracking — uses the Reachy Mini's microphone array
to track sound source direction and turn the robot's head.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class DoATracker:
    """Sound source direction tracker using reachy-mini-sdk's get_DoA().

    When a wake word is detected, turns the robot's head toward the sound source.
    Continues to track during listening for a more natural interaction.
    """

    def __init__(self, reachy_mini, motion, smoothing: float = 0.3):
        self._mini = reachy_mini
        self._motion = motion
        self._smoothing = smoothing
        self._current_yaw = 0.0
        self._running = False
        self._tracking = False
        self._thread: Optional[threading.Thread] = None

    def start_tracking(self):
        """Begin background DoA tracking."""
        self._tracking = True
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self._thread.start()
            logger.info("DoA tracking started")

    def stop_tracking(self):
        """Stop DoA tracking."""
        self._tracking = False
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("DoA tracking stopped")

    def look_at_sound_source(self):
        """Immediately turn head toward the current sound source direction."""
        try:
            doa_angle, is_speech = self._mini.media.get_DoA()
            if is_speech:
                target_yaw = self._doa_to_head_yaw(doa_angle)
                self._current_yaw = self._smooth_yaw(self._current_yaw, target_yaw)
                self._mini.set_target(body_yaw=self._current_yaw)
                logger.debug("Look at sound: doa=%.2f, yaw=%.2f", doa_angle, self._current_yaw)
        except Exception as e:
            logger.debug("DoA look error: %s", e)

    def _tracking_loop(self):
        """Background thread: periodically check DoA and adjust head."""
        while self._running:
            if not self._tracking:
                time.sleep(0.1)
                continue

            try:
                doa_angle, is_speech = self._mini.media.get_DoA()
                if is_speech:
                    target_yaw = self._doa_to_head_yaw(doa_angle)
                    self._current_yaw = self._smooth_yaw(self._current_yaw, target_yaw)
                    self._mini.set_target(body_yaw=self._current_yaw)
            except Exception as e:
                logger.debug("DoA tracking error: %s", e)

            time.sleep(0.1)

    def _doa_to_head_yaw(self, doa_angle: float) -> float:
        """Convert DoA angle to body yaw command.

        DoA angle: 0 rad = left, π/2 = front/back, π rad = right
        Body yaw: positive = left, negative = right

        We map: left(0) → +0.5, front(π/2) → 0, right(π) → -0.5
        """
        normalized = math.cos(doa_angle)
        yaw = normalized * 0.5
        return max(-1.0, min(1.0, yaw))

    def _smooth_yaw(self, current: float, target: float) -> float:
        """Exponential smoothing for yaw angle."""
        alpha = self._smoothing
        return current * (1 - alpha) + target * alpha
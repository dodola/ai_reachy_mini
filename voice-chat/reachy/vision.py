"""
Vision module — MediaPipe face tracking for Reachy Mini voice chat.

Captures frames from the robot's camera, detects face landmarks,
extracts 6DoF head pose (roll, pitch, yaw) and key blendshapes,
then maps them to robot motor commands.

Camera: mini.media.get_frame() → numpy RGB array
Face: mediapipe FaceLandmarker → head pose + blendshapes
Mapping: head pose → set_target() for smooth tracking

Runs in a background thread at ~15fps to balance responsiveness
with CPU usage on embedded hardware.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    logger.warning("mediapipe not available — face tracking disabled")


@dataclass
class FaceFeatures:
    """Extracted face features from a single frame."""

    face_detected: bool = False
    head_roll: float = 0.0
    head_pitch: float = 0.0
    head_yaw: float = 0.0
    head_x: float = 0.0
    head_y: float = 0.0
    head_z: float = 0.0

    mouth_smile: float = 0.0
    mouth_open: float = 0.0
    brow_inner_up: float = 0.0
    eye_blink_left: float = 0.0
    eye_blink_right: float = 0.0
    jaw_open: float = 0.0


@dataclass
class TrackerConfig:
    """Configuration for face tracking behavior."""

    fps: int = 15
    head_amp_roll: float = 1.0
    head_amp_pitch: float = 1.0
    head_amp_yaw: float = 1.0
    roll_max_deg: float = 20.0
    pitch_max_deg: float = 20.0
    yaw_max_deg: float = 30.0
    smoothing: float = 0.3
    detection_confidence: float = 0.5
    tracking_confidence: float = 0.5
    model_asset_path: str = ""


BLEND_SHAPE_NAMES = [
    "browDownLeft", "browDownRight", "browInnerUpLeft", "browInnerUpRight",
    "browOuterUpLeft", "browOuterUpRight", "cheekPuffLeft", "cheekPuffRight",
    "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight",
    "eyeOpenLeft", "eyeOpenRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen",
    " jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthLeft",
    "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
    "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower",
    "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft",
    "mouthStretchRight", "mouthUpLeft", "mouthUpRight", "noseSneerLeft",
    "noseSneerRight",
]


class FaceTracker:
    """MediaPipe FaceLandmarker-based face tracker for Reachy Mini.

    Captures camera frames, detects face landmarks, extracts head pose
    and blendshapes, and provides smooth motor target updates.
    """

    def __init__(self, reachy_mini, config: Optional[TrackerConfig] = None):
        self._mini = reachy_mini
        self._config = config or TrackerConfig()
        self._landmarker: Optional[FaceLandmarker] = None
        self._running = False
        self._tracking = False
        self._thread: Optional[threading.Thread] = None

        self._smooth_roll = 0.0
        self._smooth_pitch = 0.0
        self._smooth_yaw = 0.0

        self._last_features = FaceFeatures()
        self._frame_count = 0
        self._fps_actual = 0.0

        self._on_features_callbacks = []

    def start(self):
        """Initialize MediaPipe and start tracking thread."""
        if not HAS_MEDIAPIPE:
            logger.error("mediapipe not installed — cannot start face tracking")
            return False

        try:
            self._init_landmarker()
        except Exception as e:
            logger.error("Failed to init FaceLandmarker: %s", e)
            return False

        self._running = True
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("Face tracker started at %d fps", self._config.fps)
        return True

    def stop(self):
        """Stop tracking and release resources."""
        self._running = False
        self._tracking = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
        logger.info("Face tracker stopped")

    def enable_tracking(self, enabled: bool = True):
        """Enable or disable face tracking (camera still runs)."""
        self._tracking = enabled
        if not enabled:
            self._smooth_roll = 0.0
            self._smooth_pitch = 0.0
            self._smooth_yaw = 0.0
            self._last_features = FaceFeatures()
        logger.info("Face tracking %s", "enabled" if enabled else "disabled")

    def on_features(self, callback):
        """Register a callback for face features updates.

        callback signature: fn(features: FaceFeatures)
        """
        self._on_features_callbacks.append(callback)

    @property
    def is_tracking(self) -> bool:
        return self._tracking

    @property
    def last_features(self) -> FaceFeatures:
        return self._last_features

    def _init_landmarker(self):
        """Initialize MediaPipe FaceLandmarker."""
        model_path = self._config.model_asset_path
        if not model_path:
            import os
            candidate = os.path.join(
                os.path.dirname(__file__), "..", "models", "face_landmarker_v2.task"
            )
            if os.path.exists(candidate):
                model_path = candidate

        if model_path:
            base_options = BaseOptions(model_asset_path=model_path)
        else:
            base_options = BaseOptions(
                model_asset_path="face_landmarker_v2.task"
            )

        options = FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=self._config.detection_confidence,
            min_face_presence_confidence=self._config.tracking_confidence,
            min_tracking_confidence=self._config.tracking_confidence,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = FaceLandmarker.create_from_options(options)
        logger.info("FaceLandmarker initialized")

    def _tracking_loop(self):
        """Background thread: capture frames and detect faces."""
        frame_interval = 1.0 / self._config.fps
        last_time = time.monotonic()
        frame_ms = 0

        while self._running:
            try:
                frame = self._mini.media.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                if self._tracking and self._landmarker is not None:
                    frame_ms = int(time.monotonic() * 1000)
                    features = self._process_frame(frame, frame_ms)
                    self._last_features = features

                    if features.face_detected:
                        self._apply_head_pose(features)

                    for cb in self._on_features_callbacks:
                        try:
                            cb(features)
                        except Exception as e:
                            logger.debug("Features callback error: %s", e)

                self._frame_count += 1
                elapsed = time.monotonic() - last_time
                if elapsed > 0:
                    self._fps_actual = self._fps_actual * 0.9 + (1.0 / max(elapsed, 0.001)) * 0.1
                last_time = time.monotonic()

                sleep_time = frame_interval - (time.monotonic() - last_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                if self._running:
                    logger.error("Face tracking error: %s", e)
                    time.sleep(0.05)

    def _process_frame(self, frame: np.ndarray, timestamp_ms: int) -> FaceFeatures:
        """Process a single frame through FaceLandmarker."""
        features = FaceFeatures()

        try:
            rgb_frame = frame
            if rgb_frame.ndim == 3 and rgb_frame.shape[2] == 3:
                pass
            elif rgb_frame.ndim == 2:
                rgb_frame = np.stack([rgb_frame] * 3, axis=-1)
            else:
                return features

            result = self._landmarker.detect_for_video(rgb_frame, timestamp_ms)

            if not result.face_landmarks:
                return features

            features.face_detected = True

            if result.facial_transformation_matrixes:
                matrix = result.facial_transformation_matrixes[0]
                rpy = self._matrix_to_roll_pitch_yaw(matrix)
                features.head_roll = rpy[0]
                features.head_pitch = rpy[1]
                features.head_yaw = rpy[2]

                transform = np.array(matrix).reshape(4, 4)
                features.head_x = transform[0, 3]
                features.head_y = transform[1, 3]
                features.head_z = transform[2, 3]

            if result.face_blendshapes:
                bs = result.face_blendshapes[0]
                for category in bs:
                    name = category.category_name
                    score = category.score

                    if name == "mouthSmileLeft":
                        features.mouth_smile = max(features.mouth_smile, score)
                    elif name == "mouthSmileRight":
                        features.mouth_smile = max(features.mouth_smile, score)
                    elif name == "jawOpen":
                        features.mouth_open = score
                        features.jaw_open = score
                    elif name == "browInnerUp":
                        features.brow_inner_up = score
                    elif name == "eyeBlinkLeft":
                        features.eye_blink_left = score
                    elif name == "eyeBlinkRight":
                        features.eye_blink_right = score

        except Exception as e:
            logger.debug("Frame processing error: %s", e)

        return features

    @staticmethod
    def _matrix_to_roll_pitch_yaw(matrix) -> tuple[float, float, float]:
        """Extract roll, pitch, yaw from a 4x4 transformation matrix.

        Matches the mime_bot JS implementation:
          pitch = -atan2(-m12, m22)  (nose down = positive)
          yaw   = -asin(m02)         (look left = positive)
          roll  = -atan2(-m01, m00)  (tilt left = positive)

        Returns (roll, pitch, yaw) in radians.
        """
        m = np.array(matrix).reshape(4, 4)
        m00, m01, m02 = m[0, 0], m[0, 1], m[0, 2]
        m10, m11, m12 = m[1, 0], m[1, 1], m[1, 2]
        m20, m21, m22 = m[2, 0], m[2, 1], m[2, 2]

        pitch = -math.atan2(-m12, m22)
        yaw = -math.asin(max(-1.0, min(1.0, m02)))
        roll = -math.atan2(-m01, m00)

        return (roll, pitch, yaw)

    def _apply_head_pose(self, features: FaceFeatures):
        """Apply smoothed head pose to robot motors."""
        cfg = self._config
        alpha = cfg.smoothing

        target_roll = math.degrees(features.head_roll) * cfg.head_amp_roll
        target_pitch = math.degrees(features.head_pitch) * cfg.head_amp_pitch
        target_yaw = math.degrees(features.head_yaw) * cfg.head_amp_yaw

        target_roll = max(-cfg.roll_max_deg, min(cfg.roll_max_deg, target_roll))
        target_pitch = max(-cfg.pitch_max_deg, min(cfg.pitch_max_deg, target_pitch))
        target_yaw = max(-cfg.yaw_max_deg, min(cfg.yaw_max_deg, target_yaw))

        smooth_roll = self._smooth_roll * (1 - alpha) + target_roll * alpha
        smooth_pitch = self._smooth_pitch * (1 - alpha) + target_pitch * alpha
        smooth_yaw = self._smooth_yaw * (1 - alpha) + target_yaw * alpha

        self._smooth_roll = smooth_roll
        self._smooth_pitch = smooth_pitch
        self._smooth_yaw = smooth_yaw

        roll_rad = math.radians(smooth_roll)
        pitch_rad = math.radians(smooth_pitch)
        yaw_rad = math.radians(smooth_yaw)

        try:
            self._mini.set_target(
                head=np.array([roll_rad, pitch_rad, yaw_rad, 0.0, 0.0, 0.0])
            )
        except Exception as e:
            logger.debug("set_target error: %s", e)

    def detect_emotion(self, features: FaceFeatures) -> str:
        """Map blendshapes to a simple emotion label.

        Returns one of: happy, sad, surprised, angry, neutral, thinking
        """
        if not features.face_detected:
            return "neutral"

        smile = features.mouth_smile
        mouth_open = features.mouth_open
        brow_up = features.brow_inner_up
        blink = (features.eye_blink_left + features.eye_blink_right) / 2

        if smile > 0.5:
            return "happy"
        if mouth_open > 0.6:
            return "surprised"
        if blink > 0.7:
            return "thinking"
        if brow_up > 0.4 and smile < 0.2:
            return "sad"

        return "neutral"

    @property
    def fps(self) -> float:
        return self._fps_actual
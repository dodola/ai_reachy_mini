"""
Gemma 4 Vision — local multimodal understanding via Ollama or vLLM.

Captures frames from Reachy Mini's camera, sends them to a local
Gemma 4 model running on GPU (via Ollama), and returns scene descriptions,
visual Q&A responses, or emotion detections.

With RTX 4060 16GB, recommended models:
  - gemma3:12b (Q4_K_M, ~7GB VRAM) — best balance
  - gemma3:27b (Q2_K, ~10GB VRAM) — maximum quality
  - gemma3:4b  — fastest, lowest quality

Two modes:
  1. Periodic scene description — auto-captures and describes every N seconds
  2. On-demand visual Q&A — triggered by MCP tool or voice command
"""

from __future__ import annotations

import base64
import io
import json
import logging
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class GemmaVision:
    """Local multimodal vision understanding using Gemma 4 via Ollama.

    Supports:
    - Scene description (periodic auto-capture)
    - Visual Q&A (on-demand)
    - Emotion detection (from camera)
    - Object recognition
    - Scene change detection
    """

    def __init__(
        self,
        reachy_mini,
        model: str = "gemma3:12b",
        ollama_url: str = "http://localhost:11434",
        capture_fps: float = 0.5,
        auto_describe_interval: float = 0,
        max_history: int = 10,
        system_prompt: str = "",
    ):
        self._mini = reachy_mini
        self._model = model
        self._ollama_url = ollama_url.rstrip("/")
        self._capture_fps = capture_fps
        self._auto_describe_interval = auto_describe_interval
        self._max_history = max_history

        self._system_prompt = system_prompt or (
            "You are a helpful AI assistant embedded in a Reachy Mini robot. "
            "You can see through the robot's camera. Answer questions about what you see "
            "concisely and naturally. When describing scenes, focus on people, objects, "
            "and activities that are relevant for conversation."
        )

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_description: str = ""
        self._last_emotion: str = "neutral"
        self._scene_history: list[dict] = []
        self._last_capture_time = 0.0
        self._available = False
        self._request_timeout = 30.0

        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is running and the model is available."""
        try:
            import requests

            resp = requests.get(f"{self._ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self._model.split(":")[0]
                if any(model_base in m for m in models):
                    self._available = True
                    logger.info("Ollama model %s available", self._model)
                else:
                    logger.warning(
                        "Model %s not found in Ollama. Available: %s. "
                        "Run: ollama pull %s",
                        self._model,
                        ", ".join(models[:5]),
                        self._model,
                    )
            else:
                logger.warning("Ollama returned status %d", resp.status_code)
        except ImportError:
            logger.error("requests not installed — pip install requests")
        except Exception as e:
            logger.warning(
                "Ollama not reachable at %s: %s. "
                "Vision features will be disabled. "
                "Start Ollama: ollama serve && ollama pull %s",
                self._ollama_url,
                e,
                self._model,
            )

    @property
    def available(self) -> bool:
        return self._available

    @property
    def last_description(self) -> str:
        return self._last_description

    @property
    def last_emotion(self) -> str:
        return self._last_emotion

    def start(self):
        """Start background auto-describe thread if configured."""
        if not self._available:
            logger.warning("GemmaVision not available — not starting")
            return
        if self._auto_describe_interval <= 0:
            logger.info("Auto-describe disabled (interval=0)")
            return

        self._running = True
        self._thread = threading.Thread(target=self._auto_describe_loop, daemon=True)
        self._thread.start()
        logger.info(
            "GemmaVision started: model=%s, auto_describe=%.1fs",
            self._model,
            self._auto_describe_interval,
        )

    def stop(self):
        """Stop background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("GemmaVision stopped")

    def describe_scene(self, prompt: str = "Describe what you see briefly.") -> str:
        """Capture current frame and get description from Gemma 4.

        Args:
            prompt: What to ask the model about the image.

        Returns:
            Model's text description, or empty string if unavailable.
        """
        if not self._available:
            return ""

        frame = self._capture_frame()
        if frame is None:
            return ""

        return self._query_vlm(frame, prompt)

    def ask_about_scene(self, question: str) -> str:
        """Ask a question about the current scene.

        Args:
            question: The question to ask (e.g., "Is there a person in the room?")

        Returns:
            Model's answer, or empty string if unavailable.
        """
        if not self._available:
            return ""

        frame = self._capture_frame()
        if frame is None:
            return ""

        prompt = f"Look at this image and answer: {question}\nAnswer concisely."
        return self._query_vlm(frame, prompt)

    def detect_emotions(self) -> list[dict]:
        """Detect emotions of people in the current frame.

        Returns:
            List of dicts with 'emotion' and 'confidence' keys.
        """
        if not self._available:
            return []

        frame = self._capture_frame()
        if frame is None:
            return []

        prompt = (
            "Look at the people in this image. For each person, identify their "
            "primary emotion. Respond ONLY in this JSON format: "
            '[{"emotion": "happy|sad|angry|surprised|neutral|thinking|confused", '
            '"confidence": 0.0-1.0}]'
        )
        response = self._query_vlm(frame, prompt)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                emotions = json.loads(response[start:end])
                if emotions:
                    emotion = emotions[0].get("emotion", "neutral")
                    self._last_emotion = emotion
                return emotions
        except (json.JSONDecodeError, IndexError):
            pass

        return []

    def get_conversation_context(self) -> str:
        """Get recent scene history as context string for LLM conversation.

        Returns:
            Formatted string of recent scene descriptions.
        """
        if not self._scene_history:
            return ""
        recent = self._scene_history[-3:]
        parts = []
        for entry in recent:
            ts = entry.get("time", "")
            desc = entry.get("description", "")
            parts.append(f"[{ts}] {desc}")
        return "Visual context:\n" + "\n".join(parts)

    def _capture_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from the robot's camera."""
        try:
            frame = self._mini.media.get_frame()
            if frame is not None and isinstance(frame, np.ndarray) and frame.size > 0:
                return frame
        except Exception as e:
            logger.debug("Frame capture error: %s", e)
        return None

    def _frame_to_base64(self, frame: np.ndarray, quality: int = 85) -> str:
        """Convert numpy frame to base64 JPEG string."""
        try:
            import cv2

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except ImportError:
            from PIL import Image

            img = Image.fromarray(frame)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _query_vlm(self, frame: np.ndarray, prompt: str) -> str:
        """Send image + prompt to Ollama's Gemma 4 model.

        Args:
            frame: numpy array (H, W, 3) RGB image
            prompt: text prompt

        Returns:
            Model's text response.
        """
        import requests

        image_b64 = self._frame_to_base64(frame)

        payload = {
            "model": self._model,
            "prompt": prompt,
            "images": [image_b64],
            "system": self._system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 256,
            },
        }

        try:
            resp = requests.post(
                f"{self._ollama_url}/api/generate",
                json=payload,
                timeout=self._request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except requests.Timeout:
            logger.warning("Ollama request timed out")
            return ""
        except requests.ConnectionError:
            logger.warning("Ollama connection failed — is it running?")
            self._available = False
            return ""
        except Exception as e:
            logger.error("Ollama query error: %s", e)
            return ""

    def _auto_describe_loop(self):
        """Background thread: periodically capture and describe scenes."""
        while self._running:
            try:
                description = self.describe_scene(
                    "Describe this scene in 1-2 sentences. Focus on people and their activities."
                )
                if description:
                    self._last_description = description
                    self._last_emotion = self._extract_emotion(description)
                    self._scene_history.append(
                        {
                            "time": time.strftime("%H:%M:%S"),
                            "description": description,
                            "emotion": self._last_emotion,
                        }
                    )
                    if len(self._scene_history) > self._max_history:
                        self._scene_history = self._scene_history[-self._max_history:]
                    logger.debug("Scene: %s", description[:80])
            except Exception as e:
                logger.error("Auto-describe error: %s", e)

            interval = self._auto_describe_interval
            deadline = time.monotonic() + interval
            while self._running and time.monotonic() < deadline:
                time.sleep(0.5)

    @staticmethod
    def _extract_emotion(text: str) -> str:
        """Extract dominant emotion from description text."""
        text_lower = text.lower()
        emotions = {
            "happy": 0,
            "smiling": 0,
            "sad": 0,
            "angry": 0,
            "surprised": 0,
            "thinking": 0,
            "confused": 0,
            "neutral": 1,
        }
        for word in text_lower.split():
            for key in emotions:
                if key in word:
                    emotions[key] += 1
                    emotions["neutral"] = 0

        best = max(emotions, key=emotions.get)
        return best if emotions[best] > 0 else "neutral"
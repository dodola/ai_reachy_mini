"""
Reachy Mini motion control — bridges MCP tool calls to SDK actions.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

from . import mcp_tools

logger = logging.getLogger(__name__)


class ReachyMotion:
    """Control Reachy Mini motors via SDK, driven by MCP tool calls."""

    def __init__(self, reachy_mini, config: Optional[dict] = None):
        self._mini = reachy_mini
        self._config = config or {}
        self._idle_antennas = mcp_tools.IDLE_ANTENNAS
        self._speaker_volume = 100
        self._last_emote_time = 0.0
        self._gemma = None  # Set via set_gemma()

    def set_gemma(self, gemma):
        """Set the GemmaVision instance for visual Q&A tools."""
        self._gemma = gemma

    def handle_mcp_call(self, tool_name: str, arguments: dict) -> str:
        """Dispatch an MCP tool call to the appropriate SDK method.

        Returns a result string for the MCP response.
        """
        try:
            if tool_name == "reachy.goto_pose":
                return self._goto_pose(arguments)
            elif tool_name == "reachy.set_target":
                return self._set_target(arguments)
            elif tool_name == "reachy.emote":
                return self._emote(arguments)
            elif tool_name == "reachy.set_volume":
                return self._set_volume(arguments)
            elif tool_name == "reachy.look_at":
                return self._look_at(arguments)
            elif tool_name == "reachy.enable_motors":
                return self._enable_motors()
            elif tool_name == "reachy.disable_motors":
                return self._disable_motors()
            elif tool_name == "reachy.look_around":
                return self._look_around(arguments)
            elif tool_name == "reachy.describe_scene":
                return self._describe_scene(arguments)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error("MCP call %s failed: %s", tool_name, e)
            return f"Error: {e}"

    def _goto_pose(self, args: dict) -> str:
        head = args.get("head")
        antennas = args.get("antennas")
        body_yaw = args.get("body_yaw")
        duration = args.get("duration", 0.5)
        method = args.get("method", "minjerk")

        kwargs = {"duration": float(duration), "method": method}
        if head is not None:
            pose = np.zeros(6)
            for i, v in enumerate(head[:6]):
                pose[i] = float(v)
            kwargs["head"] = pose
        if antennas is not None:
            kwargs["antennas"] = [float(a) for a in antennas[:2]]
        if body_yaw is not None:
            kwargs["body_yaw"] = float(body_yaw)

        self._mini.goto_target(**kwargs)
        return f"Moved to pose: head={head}, antennas={antennas}, body_yaw={body_yaw}"

    def _set_target(self, args: dict) -> str:
        kwargs = {}
        head = args.get("head")
        antennas = args.get("antennas")
        body_yaw = args.get("body_yaw")

        if head is not None:
            pose = np.zeros(6)
            for i, v in enumerate(head[:6]):
                pose[i] = float(v)
            kwargs["head"] = pose
        if antennas is not None:
            kwargs["antennas"] = [float(a) for a in antennas[:2]]
        if body_yaw is not None:
            kwargs["body_yaw"] = float(body_yaw)

        self._mini.set_target(**kwargs)
        return f"Set target: head={head}, antennas={antennas}, body_yaw={body_yaw}"

    def _emote(self, args: dict) -> str:
        name = args.get("name", "neutral")
        now = time.monotonic()
        if now - self._last_emote_time < 0.5:
            return f"Emote {name} skipped (too frequent)"
        self._last_emote_time = now

        pose = mcp_tools.EMOTE_POSES.get(name, mcp_tools.EMOTE_POSES["neutral"])
        self._mini.goto_target(
            head=np.array(pose["head"]),
            antennas=pose["antennas"],
            duration=pose["duration"],
            method="minjerk",
        )
        return f"Playing emote: {name}"

    def _set_volume(self, args: dict) -> str:
        volume = max(0, min(100, int(args.get("volume", 100))))
        self._speaker_volume = volume
        # Volume scaling is handled in the audio bridge
        return f"Volume set to {volume}"

    def _look_at(self, args: dict) -> str:
        x = float(args.get("x", 1.0))
        y = float(args.get("y", 0.0))
        z = float(args.get("z", 0.0))
        self._mini.look_at_world(x, y, z)
        return f"Looking at ({x}, {y}, {z})"

    def _enable_motors(self) -> str:
        self._mini.enable_motors()
        return "Motors enabled"

    def _disable_motors(self) -> str:
        self._mini.disable_motors()
        return "Motors disabled"

    def _look_around(self, args: dict) -> str:
        question = args.get("question", "")
        if self._gemma and self._gemma.available:
            if question:
                answer = self._gemma.ask_about_scene(question)
            else:
                answer = self._gemma.describe_scene(
                    "Look around and describe what you see. Focus on people, objects, and their activities."
                )
            return answer or "I can't see anything right now."
        elif self._gemma:
            return "Vision model is not available. Please install Ollama and pull the model."
        else:
            return "Vision not configured."

    def _describe_scene(self, args: dict) -> str:
        detail = args.get("detail", "normal")
        prompt_map = {
            "brief": "Describe this scene in one short sentence.",
            "normal": "Describe this scene in 2-3 sentences. Focus on people and their activities.",
            "detailed": "Describe this scene in detail. Include all visible people, objects, their positions, activities, and the overall atmosphere.",
        }
        prompt = prompt_map.get(detail, prompt_map["normal"])
        if self._gemma and self._gemma.available:
            return self._gemma.describe_scene(prompt) or "I can't see anything right now."
        elif self._gemma:
            return "Vision model is not available."
        else:
            return "Vision not configured."

    def on_wake(self):
        """Called when wake word is detected — look up and reset pose."""
        self._mini.goto_target(
            head=np.array([0.0, -0.1, 0.0, 0.0, 0.0, 0.0]),
            antennas=self._idle_antennas,
            duration=0.4,
            method="minjerk",
        )

    def on_listening(self):
        """Called when listening starts — tilt head slightly."""
        self._mini.goto_target(
            head=np.array([0.0, 0.05, 0.0, 0.0, 0.0, 0.0]),
            duration=0.3,
            method="minjerk",
        )

    def on_thinking(self):
        """Called when AI is processing — tilt head and antennas."""
        self._mini.goto_target(
            head=np.array([0.05, 0.1, -0.1, 0.0, 0.0, 0.0]),
            antennas=[0.1, -0.1],
            duration=0.4,
            method="ease_in_out",
        )

    def on_speaking(self):
        """Called when TTS starts — neutral head pose."""
        self._mini.goto_target(
            head=np.array([0.0, -0.05, 0.0, 0.0, 0.0, 0.0]),
            antennas=self._idle_antennas,
            duration=0.3,
            method="minjerk",
        )

    def on_idle(self):
        """Called when returning to idle — reset to default pose."""
        self._mini.goto_target(
            head=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            antennas=self._idle_antennas,
            duration=0.8,
            method="ease_in_out",
        )

    @property
    def volume(self) -> float:
        """Returns volume as 0.0-1.0 float."""
        return self._speaker_volume / 100.0
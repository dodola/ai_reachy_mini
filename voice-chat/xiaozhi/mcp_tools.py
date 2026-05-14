"""
MCP tool definitions for Reachy Mini — registered with xiaozhi server
so the AI can control robot joints, emotions, and volume.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

MCP_TOOLS = [
    {
        "name": "reachy.goto_pose",
        "description": "控制机器人平滑移动到指定姿态。可以同时控制头部、天线和身体。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "head": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "头部姿态 [roll, pitch, yaw, x, y, z]（弧度/米），可选，最多6个元素",
                },
                "antennas": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "天线角度 [左, 右]（弧度），左天线正值为向前倾，右天线负值为向前倾",
                },
                "body_yaw": {
                    "type": "number",
                    "description": "身体偏转角度（弧度），正值为向左",
                },
                "duration": {
                    "type": "number",
                    "description": "运动持续时间（秒），默认0.5",
                },
                "method": {
                    "type": "string",
                    "enum": ["linear", "minjerk", "ease_in_out", "cartoon"],
                    "description": "插值方法，默认minjerk",
                },
            },
        },
    },
    {
        "name": "reachy.set_target",
        "description": "立即设置机器人目标位置（无过渡动画），用于实时跟踪。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "head": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "头部姿态 [roll, pitch, yaw, x, y, z]（弧度/米）",
                },
                "antennas": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "天线角度 [左, 右]（弧度）",
                },
                "body_yaw": {
                    "type": "number",
                    "description": "身体偏转角度（弧度）",
                },
            },
        },
    },
    {
        "name": "reachy.emote",
        "description": "播放预设情绪动作，让机器人表现情感。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["happy", "sad", "curious", "surprised", "angry", "neutral", "thinking"],
                    "description": "情绪名称",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "reachy.set_volume",
        "description": "设置机器人音量。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "volume": {
                    "type": "integer",
                    "description": "音量 0-100",
                },
            },
            "required": ["volume"],
        },
    },
    {
        "name": "reachy.look_at",
        "description": "让机器人看向指定方向的3D坐标点（世界坐标系，前方为X正，左侧为Y正，上方为Z正）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "前方距离（米）"},
                "y": {"type": "number", "description": "左侧距离（米）"},
                "z": {"type": "number", "description": "上方距离（米）"},
            },
            "required": ["x", "y", "z"],
        },
    },
    {
        "name": "reachy.enable_motors",
        "description": "启用电机（僵硬模式），机器人会保持当前姿态。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "reachy.disable_motors",
        "description": "禁用电机（松弛模式），机器人会软下来。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def get_tools_list() -> list[dict]:
    """Return MCP tools list for tools/list response."""
    return MCP_TOOLS


EMOTE_POSES = {
    "happy": {
        "antennas": [0.3, -0.3],
        "head": [0.0, -0.15, 0.0, 0.0, 0.0, 0.0],
        "duration": 0.8,
    },
    "sad": {
        "antennas": [-0.2, 0.2],
        "head": [0.0, 0.25, 0.0, 0.0, 0.0, 0.0],
        "duration": 1.0,
    },
    "curious": {
        "antennas": [0.15, -0.05],
        "head": [0.1, -0.1, 0.15, 0.0, 0.0, 0.0],
        "duration": 0.6,
    },
    "surprised": {
        "antennas": [0.4, -0.4],
        "head": [0.0, -0.3, 0.0, 0.0, 0.0, 0.0],
        "duration": 0.4,
    },
    "angry": {
        "antennas": [-0.3, 0.3],
        "head": [0.0, 0.15, 0.0, 0.0, 0.0, 0.0],
        "duration": 0.5,
    },
    "neutral": {
        "antennas": [-0.1745, 0.1745],
        "head": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "duration": 0.5,
    },
    "thinking": {
        "antennas": [0.1, -0.1],
        "head": [0.05, 0.05, -0.1, 0.0, 0.0, 0.0],
        "duration": 0.7,
    },
}

IDLE_ANTENNAS = [-0.1745, 0.1745]


def parse_head_pose(head_list: list) -> dict | None:
    """Parse head pose from MCP tool arguments.

    Accepts [roll, pitch, yaw] or [roll, pitch, yaw, x, y, z].
    Returns dict suitable for reachy_mini.goto_target/set_target.
    """
    if not head_list:
        return None
    import numpy as np

    pose = np.zeros(6)
    for i, v in enumerate(head_list[:6]):
        if i < len(head_list):
            pose[i] = float(v)
    return {"head": pose}


def parse_antennas(antennas_list: list) -> dict | None:
    """Parse antenna angles from MCP tool arguments.

    Accepts [left, right] in radians.
    """
    if not antennas_list:
        return None
    left = float(antennas_list[0]) if len(antennas_list) > 0 else 0.0
    right = float(antennas_list[1]) if len(antennas_list) > 1 else 0.0
    return {"antennas": [left, right]}
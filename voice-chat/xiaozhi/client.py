"""
Xiaozhi WebSocket client — implements the xiaozhi-esp32 protocol.

Protocol reference: https://github.com/78/xiaozhi-esp32/blob/main/docs/websocket.md

State machine: IDLE → CONNECTING → HELLO → LISTENING → THINKING → SPEAKING → IDLE
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
import uuid
from enum import Enum, auto
from typing import Callable, Optional

import websockets

from .codec import OpusCodec

logger = logging.getLogger(__name__)


class DeviceState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    HELLO = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    ERROR = auto()


class XiaozhiClient:
    """Async WebSocket client for the xiaozhi voice chat protocol."""

    def __init__(
        self,
        server_url: str = "",
        token: str = "",
        device_id: str = "",
        client_id: str = "",
        protocol_version: int = 3,
        codec: Optional[OpusCodec] = None,
        on_stt: Optional[Callable[[str], None]] = None,
        on_llm: Optional[Callable[[str, str], None]] = None,
        on_tts_start: Optional[Callable[[], None]] = None,
        on_tts_stop: Optional[Callable[[], None]] = None,
        on_tts_text: Optional[Callable[[str], None]] = None,
        on_mcp_call: Optional[Callable[[str, dict], dict]] = None,
        on_state_change: Optional[Callable[[DeviceState], None]] = None,
        on_audio_received: Optional[Callable[[bytes], None]] = None,
        reconnect_max_retries: int = 10,
        reconnect_base_delay: float = 1.0,
    ):
        self.server_url = server_url
        self.token = token
        if not device_id or not client_id:
            from .activator import load_or_create_identity
            _did, _cid = load_or_create_identity()
            device_id = device_id or _did
            client_id = client_id or _cid

        self.device_id = device_id
        self.client_id = client_id
        self.protocol_version = protocol_version
        self.codec = codec or OpusCodec()

        self._state = DeviceState.IDLE
        self._session_id: str = ""
        self._ws: Optional[websockets.asyncio.client.WebSocketClientProtocol] = None
        self._mcp_id = 0
        self._server_sample_rate = 24000
        self._server_frame_duration = 60
        self._reconnect_max_retries = reconnect_max_retries
        self._reconnect_base_delay = reconnect_base_delay
        self._running = False

        self.on_stt = on_stt
        self.on_llm = on_llm
        self.on_tts_start = on_tts_start
        self.on_tts_stop = on_tts_stop
        self.on_tts_text = on_tts_text
        self.on_mcp_call = on_mcp_call
        self.on_state_change = on_state_change
        self.on_audio_received = on_audio_received

    @property
    def state(self) -> DeviceState:
        return self._state

    def apply_activation(self, activation_result) -> None:
        """Apply OTA activation result to update connection parameters.

        This replaces server_url, token, and protocol_version from the
        activation flow (matching xiaozhi-esp32 websocket_protocol.cc).
        """
        from .activator import ActivationResult

        if not isinstance(activation_result, ActivationResult):
            raise TypeError("Expected ActivationResult")

        if activation_result.websocket_url:
            self.server_url = activation_result.websocket_url
            logger.info("Activation: server_url updated to %s", self.server_url)
        if activation_result.websocket_token:
            self.token = activation_result.websocket_token
            logger.info("Activation: token updated")
        if activation_result.websocket_version:
            self.protocol_version = activation_result.websocket_version
            logger.info("Activation: protocol_version updated to %d", self.protocol_version)

    def _set_state(self, state: DeviceState):
        old = self._state
        self._state = state
        if old != state:
            logger.info("State: %s → %s", old.name, state.name)
            if self.on_state_change:
                self.on_state_change(state)

    async def connect(self) -> bool:
        """Open WebSocket connection and perform hello handshake."""
        self._set_state(DeviceState.CONNECTING)
        headers = {}
        if self.token:
            auth = self.token if " " in self.token else f"Bearer {self.token}"
            headers["Authorization"] = auth
        headers["Protocol-Version"] = str(self.protocol_version)
        headers["Device-Id"] = self.device_id
        headers["Client-Id"] = self.client_id

        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self.server_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=30,
                    max_size=None,
                ),
                timeout=15.0,
            )
            logger.info("WebSocket connected to %s", self.server_url)
        except asyncio.TimeoutError:
            logger.error("WebSocket connection timeout (15s)")
            self._set_state(DeviceState.ERROR)
            return False
        except Exception as e:
            logger.error("WebSocket connection failed: %s", e)
            self._set_state(DeviceState.ERROR)
            return False

        hello_msg = {
            "type": "hello",
            "version": 1,
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 20,  # Match Android app
            },
        }
        await self._send_json(hello_msg)
        logger.debug("Sent hello message, waiting for response...")

        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Hello handshake timeout")
            self._set_state(DeviceState.ERROR)
            return False

        msg = self._parse_message(raw)
        if msg and msg.get("type") == "hello":
            transport = msg.get("transport", "")
            if transport != "websocket":
                logger.error("Unsupported transport: %s", transport)
                self._set_state(DeviceState.ERROR)
                return False
            self._session_id = msg.get("session_id", "")
            audio_params = msg.get("audio_params", {})
            self._server_sample_rate = audio_params.get("sample_rate", 24000)
            self._server_frame_duration = audio_params.get("frame_duration", 60)
            logger.info(
                "Hello OK: session=%s, server_rate=%d, frame_dur=%d",
                self._session_id,
                self._server_sample_rate,
                self._server_frame_duration,
            )
            self._set_state(DeviceState.HELLO)
            return True

        logger.error("Expected hello, got: %s", msg)
        self._set_state(DeviceState.ERROR)
        return False

    async def start_listening(self, mode: str = "auto"):
        """Tell server we're starting to stream audio."""
        msg = {
            "session_id": self._session_id,
            "type": "listen",
            "state": "start",
            "mode": mode,
        }
        await self._send_json(msg)
        self._set_state(DeviceState.LISTENING)

    async def stop_listening(self):
        """Tell server we're stopping audio stream."""
        msg = {
            "session_id": self._session_id,
            "type": "listen",
            "state": "stop",
        }
        await self._send_json(msg)

    async def send_wake_word(self, wake_word: str = "小智小智"):
        """Notify server that wake word was detected."""
        msg = {
            "session_id": self._session_id,
            "type": "listen",
            "state": "detect",
            "text": wake_word,
        }
        await self._send_json(msg)

    async def abort(self, reason: str = "user_stop"):
        """Abort current TTS or session."""
        msg = {
            "session_id": self._session_id,
            "type": "abort",
            "reason": reason,
        }
        await self._send_json(msg)

    async def send_audio(self, pcm_data: bytes):
        """Encode PCM audio and send as binary frame."""
        if self._ws is None or self._state == DeviceState.IDLE:
            return
        opus_frame = self.codec.encode(pcm_data)
        if opus_frame is None:
            return

        try:
            if self.protocol_version == 3:
                payload = struct.pack("!BBH", 0, 0, len(opus_frame)) + opus_frame
                await self._ws.send(payload)
            elif self.protocol_version == 2:
                ts = int(time.time() * 1000) & 0xFFFFFFFF
                payload = struct.pack("!HHIII", 2, 0, 0, ts, len(opus_frame)) + opus_frame
                await self._ws.send(payload)
            else:
                await self._ws.send(opus_frame)
        except Exception as e:
            logger.error("send_audio failed: %s", e)
            raise

        if not hasattr(self, '_send_count'):
            self._send_count = 0
        self._send_count += 1
        if self._send_count % 500 == 0:
            logger.debug("[SEND] Sent %d frames, protocol=%d, opus_size=%d",
                       self._send_count, self.protocol_version, len(opus_frame))

    async def send_mcp_response(self, request_id: int, result: dict):
        """Send MCP tool call response back to server."""
        msg = {
            "session_id": self._session_id,
            "type": "mcp",
            "payload": {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            },
        }
        await self._send_json(msg)

    async def receive_loop(self):
        """Main receive loop: process incoming messages."""
        if self._ws is None:
            return
        self._running = True
        try:
            async for raw in self._ws:
                if not self._running:
                    break
                msg = self._parse_message(raw)
                if msg is None:
                    continue
                await self._handle_message(msg)
        except websockets.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception:
            logger.exception("Receive loop error")
        finally:
            self._running = False

    async def _handle_message(self, msg):
        if isinstance(msg, bytes):
            await self._handle_audio(msg)
            return

        msg_type = msg.get("type", "")
        if msg_type == "stt":
            text = msg.get("text", "")
            logger.info("STT: %s", text)
            if self.on_stt:
                self.on_stt(text)
        elif msg_type == "llm":
            emotion = msg.get("emotion", "neutral")
            text = msg.get("text", "")
            logger.info("LLM: emotion=%s text=%s", emotion, text)
            if self.on_llm:
                self.on_llm(emotion, text)
        elif msg_type == "tts":
            state = msg.get("state", "")
            if state == "start":
                logger.info("TTS start")
                self._set_state(DeviceState.SPEAKING)
                if self.on_tts_start:
                    self.on_tts_start()
            elif state == "stop":
                logger.info("TTS stop")
                # Multi-turn: notify server before entering LISTENING so it accepts next audio turn
                await self._send_json({
                    "session_id": self._session_id,
                    "type": "listen",
                    "state": "start",
                    "mode": "auto",
                })
                self._set_state(DeviceState.LISTENING)
                if self.on_tts_stop:
                    self.on_tts_stop()
            elif state == "sentence_start":
                text = msg.get("text", "")
                logger.debug("TTS sentence: %s", text)
                if self.on_tts_text:
                    self.on_tts_text(text)
        elif msg_type == "mcp":
            await self._handle_mcp(msg)
        elif msg_type == "system":
            command = msg.get("command", "")
            logger.info("System command: %s", command)
        elif msg_type == "alert":
            status = msg.get("status", "")
            message = msg.get("message", "")
            emotion = msg.get("emotion", "neutral")
            logger.warning("Alert: [%s] %s (emotion=%s)", status, message, emotion)
        elif msg_type == "hello":
            logger.info("Hello from server (late?)")
        else:
            logger.debug("Unknown message type: %s", msg_type)

    async def _handle_audio(self, data: bytes):
        opus_frame = self._extract_opus_payload(data)
        if opus_frame is None:
            return
        if self.on_audio_received:
            self.on_audio_received(opus_frame)

    def _extract_opus_payload(self, data: bytes) -> Optional[bytes]:
        if self.protocol_version == 3:
            if len(data) < 4:
                return None
            _, _, payload_size = struct.unpack("!BBH", data[:4])
            return data[4 : 4 + payload_size]
        elif self.protocol_version == 2:
            if len(data) < 16:
                return None
            _, _, _, _, payload_size = struct.unpack("!HHIII", data[:16])
            return data[16 : 16 + payload_size]
        else:
            return data

    async def _handle_mcp(self, msg: dict):
        payload = msg.get("payload", {})
        method = payload.get("method", "")
        params = payload.get("params", {})
        request_id = payload.get("id", 0)

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "Reachy Mini",
                    "version": "1.0.0",
                },
            }
            await self.send_mcp_response(request_id, result)
        elif method == "tools/list":
            from .mcp_tools import get_tools_list

            result = {"tools": get_tools_list(), "nextCursor": ""}
            await self.send_mcp_response(request_id, result)
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            logger.info("MCP tools/call: %s(%s)", tool_name, arguments)
            if self.on_mcp_call:
                try:
                    tool_result = self.on_mcp_call(tool_name, arguments)
                    result = {
                        "content": [{"type": "text", "text": str(tool_result)}],
                        "isError": False,
                    }
                except Exception as e:
                    result = {
                        "content": [{"type": "text", "text": f"Error: {e}"}],
                        "isError": True,
                    }
            else:
                result = {
                    "content": [{"type": "text", "text": "Not implemented"}],
                    "isError": True,
                }
            await self.send_mcp_response(request_id, result)
        else:
            logger.warning("Unknown MCP method: %s", method)

    async def _send_json(self, msg: dict):
        if self._ws is None:
            return
        try:
            await self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error("Failed to send JSON: %s", e)

    def _parse_message(self, raw):
        if isinstance(raw, bytes):
            return raw
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse message: %s", type(raw))
            return None

    async def close(self):
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._set_state(DeviceState.IDLE)
        logger.info("Xiaozhi client closed")
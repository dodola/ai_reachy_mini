"""
Voice Chat for Reachy Mini — Main entry point.

Integrates xiaozhi voice chat with Reachy Mini's built-in
microphone, speaker, and motor control.

State machine:
  IDLE → (wake word) → CONNECTING → (hello) → LISTENING
    → (VAD end) → THINKING → (TTS start) → SPEAKING
    → (TTS end, multi-turn) → LISTENING  (continues without wake word)
    → (TTS end, single-turn) → IDLE

  Face tracking runs in background during active conversation:
    - LISTENING: head tracks detected face
    - THINKING/SPEAKING: head tracks detected face (subtle)
    - IDLE: face tracking paused, returns to neutral

Usage:
  python main.py --config config.yaml
  python main.py --no-face-tracking  # disable face tracking
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

import numpy as np

import yaml

from xiaozhi.activator import check_and_activate
from xiaozhi.client import DeviceState, XiaozhiClient
from xiaozhi.codec import OpusCodec
from xiaozhi.mcp_tools import EMOTE_POSES
from reachy.audio import ReachyAudioBridge
from reachy.doa import DoATracker
from reachy.motion import ReachyMotion
from reachy.vision import FaceTracker, FaceFeatures, TrackerConfig, HAS_MEDIAPIPE
from reachy.vision_gemma import GemmaVision
from reachy.wakeword import WakeWordDetector

logger = logging.getLogger(__name__)


class VoiceChatApp:
    """Main application — orchestrates audio, WebSocket, wake word, and motion."""

    def __init__(self, config: dict):
        self._config = config
        self._running = False
        self._state = DeviceState.IDLE

        # Reachy Mini SDK
        self._mini = None
        self._audio: ReachyAudioBridge | None = None
        self._motion: ReachyMotion | None = None
        self._doa: DoATracker | None = None
        self._wakeword: WakeWordDetector | None = None

        # Xiaozhi client
        self._codec = OpusCodec()
        self._client: XiaozhiClient | None = None

        # Face tracking
        self._face_tracker: FaceTracker | None = None
        self._face_tracking_enabled = self._config.get("vision", {}).get("enabled", True)

        # Gemma 4 vision (local VLM via Ollama)
        self._gemma: GemmaVision | None = None

        # Async event loop
        self._loop: asyncio.AbstractEventLoop | None = None

    def _init_reachy(self):
        """Initialize Reachy Mini SDK and hardware."""
        from reachy_mini import ReachyMini

        reachy_cfg = self._config.get("reachy", {})
        self._mini = ReachyMini(
            connection_mode=reachy_cfg.get("connection_mode", "auto"),
            media_backend=reachy_cfg.get("media_backend", "local"),
        )
        logger.info("Reachy Mini connected")

        motion_cfg = self._config.get("motion", {})
        self._motion = ReachyMotion(self._mini, motion_cfg)
        self._audio = ReachyAudioBridge(self._mini, self._codec, self._config.get("audio", {}))
        self._doa = DoATracker(
            self._mini,
            self._motion,
            smoothing=motion_cfg.get("doa_smoothing", 0.3),
        )
        logger.info("Reachy Mini subsystems initialized")

    def _init_wakeword(self):
        """Initialize wake word detection."""
        ww_cfg = self._config.get("wakeword", {})
        if not ww_cfg.get("enabled", True):
            logger.info("Wake word detection disabled by config")
            return
        self._wakeword = WakeWordDetector(
            wake_keywords=ww_cfg.get("wake_keywords", ["小智小智"]),
            stop_keywords=ww_cfg.get("stop_keywords", ["停止"]),
            model_dir=ww_cfg.get("model_dir", ""),
            refractory_seconds=ww_cfg.get("refractory_seconds", 2.0),
            keywords_score=ww_cfg.get("keywords_score", 1.0),
            keywords_threshold=ww_cfg.get("keywords_threshold", 0.25),
            num_threads=ww_cfg.get("num_threads", 1),
        )
        self._wakeword.start()
        logger.info("Wake word detector initialized")

    def _init_face_tracking(self):
        """Initialize face tracking if mediapipe is available."""
        if not self._face_tracking_enabled:
            logger.info("Face tracking disabled by user")
            return
        if not HAS_MEDIAPIPE:
            logger.warning("mediapipe not installed — face tracking unavailable")
            logger.warning("Install with: pip install mediapipe")
            return

        vision_cfg = self._config.get("vision", {})
        tracker_config = TrackerConfig(
            fps=vision_cfg.get("fps", 15),
            head_amp_roll=vision_cfg.get("head_amp_roll", 1.0),
            head_amp_pitch=vision_cfg.get("head_amp_pitch", 1.0),
            head_amp_yaw=vision_cfg.get("head_amp_yaw", 1.0),
            roll_max_deg=vision_cfg.get("roll_max_deg", 20.0),
            pitch_max_deg=vision_cfg.get("pitch_max_deg", 20.0),
            yaw_max_deg=vision_cfg.get("yaw_max_deg", 30.0),
            smoothing=vision_cfg.get("smoothing", 0.3),
            detection_confidence=vision_cfg.get("detection_confidence", 0.5),
            tracking_confidence=vision_cfg.get("tracking_confidence", 0.5),
            model_asset_path=vision_cfg.get("model_asset_path", ""),
        )

        self._face_tracker = FaceTracker(self._mini, tracker_config)
        self._face_tracker.on_features(self._on_face_features)
        success = self._face_tracker.start()
        if success:
            logger.info("Face tracking initialized")
        else:
            logger.warning("Face tracking failed to start")
            self._face_tracker = None

    def _init_gemma(self):
        """Initialize Gemma 4 vision model via Ollama."""
        gemma_cfg = self._config.get("gemma", {})
        if not gemma_cfg.get("enabled", False):
            logger.info("Gemma 4 vision disabled in config")
            return

        self._gemma = GemmaVision(
            reachy_mini=self._mini,
            model=gemma_cfg.get("model", "gemma3:12b"),
            ollama_url=gemma_cfg.get("ollama_url", "http://localhost:11434"),
            auto_describe_interval=gemma_cfg.get("auto_describe_interval", 0),
            max_history=gemma_cfg.get("max_history", 10),
            system_prompt=gemma_cfg.get("system_prompt", ""),
            capture_fps=gemma_cfg.get("capture_fps", 1.0),
        )

        if self._gemma.available:
            self._gemma.start()
            logger.info("Gemma 4 vision initialized: model=%s", gemma_cfg.get("model", "gemma3:12b"))
        else:
            logger.warning("Gemma 4 vision not available — install Ollama and pull model")
            logger.warning("  curl -fsSL https://ollama.com/install.sh | sh")
            logger.warning("  ollama pull gemma3:12b")
            self._gemma = None

    def _init_client(self):
        """Initialize xiaozhi WebSocket client."""
        xz_cfg = self._config.get("xiaozhi", {})
        self._client = XiaozhiClient(
            server_url=xz_cfg.get("server_url", "wss://api.xiaozhi.me/v1/"),
            token=xz_cfg.get("token", ""),
            device_id=xz_cfg.get("device_id", ""),
            client_id=xz_cfg.get("client_id", ""),
            protocol_version=xz_cfg.get("protocol_version", 3),
            codec=self._codec,
            on_stt=self._on_stt,
            on_llm=self._on_llm,
            on_tts_start=self._on_tts_start,
            on_tts_stop=self._on_tts_stop,
            on_tts_text=self._on_tts_text,
            on_mcp_call=self._on_mcp_call,
            on_state_change=self._on_state_change,
            on_audio_received=self._on_audio_received,
            reconnect_max_retries=xz_cfg.get("reconnect_max_retries", 10),
            reconnect_base_delay=xz_cfg.get("reconnect_base_delay", 1.0),
        )
        logger.info("Xiaozhi client initialized")

    async def _activate(self):
        """Run OTA activation flow to get websocket URL and token.

        This replicates the xiaozhi-esp32 CheckVersion + Activate flow:
        1. POST system info to OTA URL
        2. Parse websocket config (url, token, version)
        3. If activation challenge, POST to /activate
        4. Apply results to the xiaozhi client
        """
        xz_cfg = self._config.get("xiaozhi", {})
        activation_cfg = xz_cfg.get("activation", {})

        if not activation_cfg.get("enabled", False):
            logger.info("OTA activation disabled, using config values")
            return True

        ota_url = activation_cfg.get("ota_url", "https://api.tenclass.net/xiaozhi/ota/")
        logger.info("Running OTA activation: %s", ota_url)

        result = await check_and_activate(
            ota_url=ota_url,
            device_id=self._client.device_id,
            client_id=self._client.client_id,
            ota_url_override=activation_cfg.get("ota_url_override", ""),
            max_activate_retries=activation_cfg.get("max_activate_retries", 10),
            activate_retry_delay=activation_cfg.get("activate_retry_delay", 3.0),
            http_timeout=activation_cfg.get("http_timeout", 30.0),
        )

        if not result.websocket_url:
            logger.error("OTA activation failed — no websocket URL returned")
            # Fall back to config values
            return False

        self._client.apply_activation(result)

        if result.activation_code:
            logger.info("Activation code: %s — %s", result.activation_code, result.activation_message)

        if not result.activated and result.websocket_url:
            logger.warning("Activation may be incomplete, but websocket URL available — continuing")

        logger.info("OTA activation complete: url=%s, version=%d, activated=%s",
                     result.websocket_url, result.websocket_version, result.activated)
        return True

    # ── Callbacks (called from async context) ────────────────────

    def _on_stt(self, text: str):
        logger.info("[STT] %s", text)
        # If gemma vision is available and user asks about the scene,
        # inject visual context
        if self._gemma and self._gemma.available:
            visual_keywords = ["看到", "看", "什么", "谁", "哪里", "那里", "这里",
                               "see", "look", "what", "who", "where", "there", "here"]
            text_lower = text.lower()
            if any(kw in text_lower for kw in visual_keywords):
                context = self._gemma.get_conversation_context()
                if context:
                    logger.info("[VISION] Injecting context: %s", context[:100])

    def _on_llm(self, emotion: str, text: str):
        logger.info("[LLM] emotion=%s text=%s", emotion, text)
        if self._motion:
            emotion_map = {
                "happy": "happy", "sad": "sad", "surprised": "surprised",
                "angry": "angry", "neutral": "neutral", "thinking": "thinking",
            }
            emote_name = emotion_map.get(emotion, "neutral")
            if emote_name in EMOTE_POSES:
                self._motion._emote({"name": emote_name})

    def _on_tts_start(self):
        logger.info("[TTS] start")
        if self._motion:
            self._motion.on_speaking()
        if self._doa and self._config.get("motion", {}).get("look_at_speaker", True):
            self._doa.stop_tracking()

    def _on_tts_stop(self):
        logger.info("[TTS] stop — ready for next turn")

    def _on_tts_text(self, text: str):
        logger.debug("[TTS sentence] %s", text)

    def _on_mcp_call(self, tool_name: str, arguments: dict) -> dict:
        if self._motion:
            return self._motion.handle_mcp_call(tool_name, arguments)
        return {"error": "Motion not initialized"}

    def _on_state_change(self, state: DeviceState):
        self._state = state
        logger.info("State → %s", state.name)
        if state == DeviceState.LISTENING:
            if self._motion:
                self._motion.on_listening()
            if self._doa and self._config.get("motion", {}).get("look_at_speaker", True):
                self._doa.start_tracking()
            if self._face_tracker:
                self._face_tracker.enable_tracking(True)
        elif state == DeviceState.IDLE:
            if self._face_tracker:
                self._face_tracker.enable_tracking(False)
            if self._doa:
                self._doa.stop_tracking()

    def _on_audio_received(self, opus_frame: bytes):
        if self._audio:
            self._audio.push_speaker_frame(opus_frame)

    def _on_face_features(self, features: FaceFeatures):
        """Callback from face tracker — detect emotion and report to xiaozhi."""
        if not features.face_detected:
            return

        # Detect emotion from face and update robot behavior
        if self._face_tracker and self._state in (DeviceState.LISTENING, DeviceState.THINKING):
            emotion = self._face_tracker.detect_emotion(features)
            if emotion != "neutral":
                # Map face emotion to subtle antenna movement
                if emotion == "happy":
                    self._mini.set_target(antennas=[0.2, -0.2])
                elif emotion == "surprised":
                    self._mini.set_target(antennas=[0.35, -0.35])
                elif emotion == "thinking":
                    self._mini.set_target(antennas=[0.05, 0.0])

    # ── Main loop ────────────────────────────────────────────────

    async def run(self):
        """Main async entry point."""
        self._init_reachy()
        self._init_wakeword()
        self._init_client()
        self._init_face_tracking()
        self._init_gemma()

        # Run OTA activation (xiaozhi-esp32 compatible)
        await self._activate()

        self._audio.start()
        self._motion.on_wake()

        # Wire gemma to motion for MCP visual tools
        if self._gemma:
            self._motion.set_gemma(self._gemma)

        self._loop = asyncio.get_running_loop()
        self._running = True

        # Start xiaozhi receive loop as a task
        receive_task = asyncio.create_task(self._xiaozhi_loop())
        # Start audio/wake-word loop
        audio_task = asyncio.create_task(self._audio_loop())

        # Handle signals (not supported on Windows)
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                self._loop.add_signal_handler(sig, lambda: asyncio.create_task(self._shutdown()))

        logger.info("Voice Chat running — say wake word to start")
        try:
            await asyncio.gather(receive_task, audio_task)
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def _xiaozhi_loop(self):
        """Manage the WebSocket connection to xiaozhi server."""
        xz_cfg = self._config.get("xiaozhi", {})
        retry_count = 0
        max_retries = xz_cfg.get("reconnect_max_retries", 10)
        base_delay = xz_cfg.get("reconnect_base_delay", 1.0)

        # If wake word is disabled, connect immediately
        if not self._wakeword:
            logger.info("Wake word disabled — waiting 1s before connecting...")
            await asyncio.sleep(1.0)  # Wait for subsystems to initialize
            logger.info("Ready to connect, client state: %s", self._client.state)

        while self._running:
            try:
                logger.debug("Xiaozhi loop tick, client state: %s", self._client.state)
                if self._client.state in (DeviceState.IDLE, DeviceState.ERROR):
                    logger.info("Connecting to xiaozhi server...")
                    success = await self._client.connect()
                    logger.info("Connect result: %s, state: %s", success, self._client.state)
                    if success:
                        retry_count = 0
                        logger.info("Connected, entering receive_loop...")
                        await self._client.receive_loop()
                        logger.info("receive_loop ended")
                    else:
                        retry_count += 1
                elif self._client.state == DeviceState.HELLO:
                    # Connected but waiting for wake word - just wait
                    await asyncio.sleep(0.1)

                delay = min(base_delay * (2 ** min(retry_count, 5)), 30.0)
                if retry_count == 0:
                    logger.info("Session ended, reconnecting in %.1fs...", delay)
                else:
                    logger.info("Reconnect attempt %d/%d in %.1fs", retry_count, max_retries, delay)
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error("Xiaozhi loop error: %s", e)
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Max retries reached, giving up")
                    self._running = False
                    break

    async def _audio_loop(self):
        """Process audio: wake word detection and send to xiaozhi."""
        idle_sleep = 0.005
        loop = asyncio.get_event_loop()
        logger.info("[AUDIO] Audio loop started")

        while self._running:
            try:
                # Run blocking get_mic_frame in thread pool to avoid blocking event loop
                pcm_frame = await loop.run_in_executor(None, lambda: self._audio.get_mic_frame(timeout=0.05))
                if pcm_frame is None:
                    await asyncio.sleep(idle_sleep)
                    continue

                # Log that we got a frame
                if not hasattr(self, '_audio_loop_count'):
                    self._audio_loop_count = 0
                self._audio_loop_count += 1
                if self._audio_loop_count % 200 == 0:
                    logger.debug("[AUDIO] Loop tick #%d, client state=%s", self._audio_loop_count, self._client.state if self._client else "None")

                # Wake word detection (only in HELLO or IDLE state)
                if (
                    self._wakeword 
                    and self._wakeword.is_loaded 
                    and self._client 
                    and self._client.state in (DeviceState.HELLO, DeviceState.IDLE)
                ):
                    result = self._wakeword.process_chunk(pcm_frame)
                    if result == "wake":
                        logger.info("[WAKE] Wake word detected! client state=%s", self._client.state)
                        if self._motion:
                            self._motion.on_wake()
                        if self._doa:
                            self._doa.look_at_sound_source()
                        # If connected (HELLO state), start listening
                        if self._client and self._client.state == DeviceState.HELLO:
                            logger.info("[WAKE] Starting listening after wake word...")
                            await self._client.start_listening(mode="auto")
                            logger.info("[WAKE] Listening started, state=%s", self._client.state)
                        elif self._client and self._client.state == DeviceState.IDLE:
                            logger.info("[WAKE] Not connected, connecting first...")
                            asyncio.create_task(self._client.connect())
                    elif result == "stop":
                        logger.info("Stop word detected!")
                        if self._client:
                            await self._client.abort(reason="stop_word_detected")

                # Send audio to xiaozhi when listening
                if (
                    self._client
                    and self._client.state == DeviceState.LISTENING
                    and self._audio.is_recording
                ):
                    try:
                        # Check audio level before sending
                        pcm_array = np.frombuffer(pcm_frame, dtype=np.int16)
                        audio_level = np.abs(pcm_array).mean()
                        is_silent = audio_level < 500  # Threshold for silence
                        
                        await self._client.send_audio(pcm_frame)
                        # Log audio sending periodically
                        if not hasattr(self, '_audio_send_count'):
                            self._audio_send_count = 0
                        self._audio_send_count += 1
                        if self._audio_send_count % 100 == 0:
                            logger.info("[AUDIO] Sent %d frames, level=%.1f, silent=%s", 
                                       self._audio_send_count, audio_level, is_silent)
                    except Exception as e:
                        logger.error("[AUDIO] Failed to send audio: %s", e)

            except Exception as e:
                logger.error("Audio loop error: %s", e)
                await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down...")
        self._running = False

        if self._client:
            await self._client.close()
        if self._audio:
            self._audio.stop()
        if self._doa:
            self._doa.stop_tracking()
        if self._face_tracker:
            self._face_tracker.stop()
        if self._gemma:
            self._gemma.stop()
        if self._motion:
            self._motion.on_idle()
        if self._wakeword:
            self._wakeword.stop()

        if self._mini:
            try:
                self._mini.media.stop_recording()
                self._mini.media.stop_playing()
            except Exception:
                pass

        logger.info("Shutdown complete")


def setup_logging(level: str = "INFO", log_file: str = ""):
    """Configure logging."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    root.addHandler(handler)

    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        root.addHandler(fh)


def load_config(config_path: str) -> dict:
    """Load YAML configuration."""
    path = Path(config_path)
    if not path.exists():
        logger.error("Config file not found: %s", path)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(description="Voice Chat for Reachy Mini")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-face-tracking", action="store_true", help="Disable face tracking")
    args = parser.parse_args()

    config = load_config(args.config)

    # Command-line overrides
    if args.no_face_tracking:
        config.setdefault("vision", {})["enabled"] = False

    log_cfg = config.get("logging", {})
    setup_logging(
        level="DEBUG" if args.verbose else log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file", ""),
    )

    app = VoiceChatApp(config)
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
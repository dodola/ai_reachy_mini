"""
Wake word and stop word detection — Sherpa-ONNX keyword spotting.

Model: sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01 (Chinese, 3.3M params, offline)
Downloads automatically to ~/.cache/sherpa-onnx/ on first run (~30 MB).

Detection runs in a background thread so process_chunk() never blocks the async loop.
"""

from __future__ import annotations

import logging
import queue
import tarfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"
_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/"
    f"{_MODEL_NAME}.tar.bz2"
)
_CACHE_DIR = Path.home() / ".cache" / "sherpa-onnx"


class WakeWordDetector:
    """Offline keyword spotting using Sherpa-ONNX.

    Supports multiple wake words and stop words in a single model pass.
    Inference runs in a background thread — process_chunk() is non-blocking.

    Usage:
        detector = WakeWordDetector(
            wake_keywords=["小智小智"],
            stop_keywords=["停止"],
        )
        detector.start()
        result = detector.process_chunk(pcm_bytes)
        # "wake", "stop", or None
    """

    def __init__(
        self,
        wake_keywords: list[str] | None = None,
        stop_keywords: list[str] | None = None,
        model_dir: str = "",
        refractory_seconds: float = 2.0,
        keywords_score: float = 1.0,
        keywords_threshold: float = 0.25,
        num_threads: int = 1,
    ):
        self._wake_keywords = set(wake_keywords or ["小智小智"])
        self._stop_keywords = set(stop_keywords or ["停止"])
        self._model_dir = Path(model_dir) if model_dir else None
        self._refractory_seconds = refractory_seconds
        self._keywords_score = keywords_score
        self._keywords_threshold = keywords_threshold
        self._num_threads = num_threads

        self._spotter = None
        self._stream = None
        self._last_wake_time = 0.0

        # maxsize=30 ≈ 2.4s of audio at 80ms/frame; drops frames if thread falls behind
        self._audio_queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=30)
        self._result_queue: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        """Download model if needed, load it, and start the background detection thread."""
        try:
            model_dir = self._resolve_model_dir()
            self._load_model(model_dir)
            self._running = True
            self._thread = threading.Thread(
                target=self._detection_loop, daemon=True, name="wakeword-detect"
            )
            self._thread.start()
            logger.info(
                "Sherpa-ONNX KWS started — wake=%s stop=%s",
                sorted(self._wake_keywords),
                sorted(self._stop_keywords),
            )
        except ImportError:
            logger.error("sherpa-onnx not installed — run: pip install sherpa-onnx")
        except Exception as e:
            logger.error("Failed to start wake word detector: %s", e)

    def stop(self):
        """Stop the background detection thread."""
        self._running = False
        try:
            self._audio_queue.put_nowait(None)  # unblock thread
        except queue.Full:
            pass
        if self._thread:
            self._thread.join(timeout=2.0)

    # ── Model setup ──────────────────────────────────────────────

    def _resolve_model_dir(self) -> Path:
        if self._model_dir and self._model_dir.exists():
            return self._model_dir
        cached = _CACHE_DIR / _MODEL_NAME
        if not cached.exists():
            self._download_model(cached)
        return cached

    def _download_model(self, target: Path):
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        archive = _CACHE_DIR / f"{_MODEL_NAME}.tar.bz2"
        logger.info("Downloading Sherpa-ONNX KWS model (~30 MB): %s", _MODEL_URL)

        last_pct = [-1]

        def _progress(count, block_size, total):
            pct = min(count * block_size * 100 // total, 100)
            if pct // 10 != last_pct[0] // 10:
                last_pct[0] = pct
                logger.info("  Downloading... %d%%", pct)

        urllib.request.urlretrieve(_MODEL_URL, archive, reporthook=_progress)
        logger.info("Extracting model to %s", _CACHE_DIR)
        with tarfile.open(archive, "r:bz2") as t:
            t.extractall(_CACHE_DIR)
        archive.unlink()
        logger.info("Model ready: %s", target)

    def _find_onnx_files(self, model_dir: Path) -> tuple[str, str, str]:
        """Glob for encoder/decoder/joiner without hardcoding checkpoint names."""
        encoders = sorted(model_dir.glob("encoder*.onnx"))
        decoders = sorted(model_dir.glob("decoder*.onnx"))
        joiners = sorted(model_dir.glob("joiner*.onnx"))
        if not (encoders and decoders and joiners):
            raise FileNotFoundError(f"ONNX files not found in {model_dir}")
        return str(encoders[0]), str(decoders[0]), str(joiners[0])

    def _write_keywords_file(self, model_dir: Path) -> Path:
        """Write keywords.txt using exact byte sequences from tokens.txt.

        Reads tokens.txt in binary mode so the bytes written to keywords.txt
        are identical to what C++ will find — completely encoding-agnostic.
        Also logs a sample of tokens.txt and any missing characters.
        """
        tokens_file = model_dir / "tokens.txt"
        kw_file = _CACHE_DIR / "keywords.txt"
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Log first 5 raw lines — visible in default (non-verbose) output
        with open(tokens_file, "rb") as f:
            sample = [f.readline().rstrip(b"\r\n") for _ in range(5)]
        logger.warning("tokens.txt first 5 lines (raw): %s", sample)

        # Build char → raw_bytes map from tokens.txt (binary, no encoding assumption)
        # split() handles both space and tab separators
        char_to_bytes: dict[str, bytes] = {}
        with open(tokens_file, "rb") as f:
            for raw_line in f:
                parts = raw_line.rstrip().split()  # any whitespace separator
                if len(parts) < 2:
                    continue
                token_raw = parts[0]  # token is always the first field
                for enc in ("utf-8", "gbk"):
                    try:
                        char = token_raw.decode(enc)
                        if char not in char_to_bytes:
                            char_to_bytes[char] = token_raw
                        break
                    except (UnicodeDecodeError, ValueError):
                        pass

        all_kw = sorted(self._wake_keywords) + sorted(self._stop_keywords)
        all_chars = set("".join(all_kw))
        missing = all_chars - set(char_to_bytes)
        if missing:
            logger.warning("Chars not in tokens.txt: %s — keywords may not work", sorted(missing))
        else:
            logger.info("All keyword chars found in tokens.txt")

        with open(kw_file, "wb") as f:
            for kw in all_kw:
                parts = [char_to_bytes.get(c, c.encode("utf-8")) for c in kw]
                f.write(b" ".join(parts) + b"\n")

        logger.debug("Keywords written: %s", [" ".join(kw) for kw in all_kw])
        return kw_file

    def _load_model(self, model_dir: Path):
        import sherpa_onnx

        encoder, decoder, joiner = self._find_onnx_files(model_dir)
        keywords_file = self._write_keywords_file(model_dir)

        self._spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(model_dir / "tokens.txt"),
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            keywords_file=str(keywords_file),
            keywords_score=self._keywords_score,
            keywords_threshold=self._keywords_threshold,
            num_threads=self._num_threads,
            num_trailing_blanks=1,
            provider="cpu",
        )
        self._stream = self._spotter.create_stream()

    # ── Detection loop (background thread) ───────────────────────

    def _detection_loop(self):
        while self._running:
            try:
                pcm_bytes = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if pcm_bytes is None:  # stop sentinel
                break

            try:
                audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                self._stream.accept_waveform(16000, audio)
                while self._spotter.is_ready(self._stream):
                    self._spotter.decode_stream(self._stream)

                result = self._spotter.get_result(self._stream)
                if not result.keyword:
                    continue

                # Normalize: model may return space-separated chars ("小 智 小 智")
                keyword = result.keyword.strip().replace(" ", "")
                logger.info("Keyword detected: %r", keyword)

                # Reset stream to avoid immediate re-trigger on the same audio
                self._stream = self._spotter.create_stream()

                now = time.monotonic()
                if keyword in self._wake_keywords:
                    if now - self._last_wake_time > self._refractory_seconds:
                        self._last_wake_time = now
                        self._result_queue.put("wake")
                elif keyword in self._stop_keywords:
                    self._result_queue.put("stop")

            except Exception as e:
                logger.debug("Detection error: %s", e)

    # ── Public API ────────────────────────────────────────────────

    def process_chunk(self, pcm_bytes: bytes) -> Optional[str]:
        """Non-blocking. Enqueue audio; return any pending detection result.

        Returns "wake", "stop", or None.
        """
        try:
            self._audio_queue.put_nowait(pcm_bytes)
        except queue.Full:
            pass  # drop frame; detection thread is catching up

        try:
            return self._result_queue.get_nowait()
        except queue.Empty:
            return None

    @property
    def is_loaded(self) -> bool:
        return self._spotter is not None

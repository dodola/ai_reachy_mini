"""Standalone wake word detector test.

Usage:
    conda activate voice-chat
    python test_wakeword.py

Speak "小智小智" to test wake word detection.
Press Ctrl+C to quit.
"""

import logging
import signal
import sys
import time

import numpy as np
import sounddevice as sd

from reachy.wakeword import WakeWordDetector

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")

CHUNK_MS = 80  # ms per audio chunk
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 1280 samples


def main():
    detector = WakeWordDetector(
        wake_keywords=["小智小智"],
        stop_keywords=["停止"],
        keywords_threshold=0.1,
        refractory_seconds=1.0,
    )
    detector.start()

    if not detector.is_loaded:
        print("ERROR: Wake word detector failed to load.")
        print("Install sherpa-onnx:  pip install sherpa-onnx")
        sys.exit(1)

    # List audio devices for debugging
    print(f"Default input device: {sd.default.device[0]}")
    print(f"Available input devices:")
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] > 0:
            print(f"  [{i}] {dev['name']} (in:{dev['max_input_channels']}, rate:{dev['default_samplerate']})")

    # Use the Reachy Mini mic (device index 6) if available
    device_index = 6  # Reachy Mini Audio
    print(f"\nUsing device index: {device_index}")
    print(f"Listening... Say '小智小智' (wake) or '停止' (stop). Ctrl+C to quit.")
    print(f"Audio: {SAMPLE_RATE}Hz, mono, block={BLOCK_SIZE} samples ({CHUNK_MS}ms)")

    running = True
    chunk_count = 0

    def on_stop(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, on_stop)

    def audio_callback(indata, frames, time_info, status):
        nonlocal chunk_count
        if status:
            print(f"Audio status: {status}")
        chunk_count += 1
        if chunk_count % 100 == 0:
            rms = np.sqrt(np.mean(indata[:, 0] ** 2))
            print(f"  [audio] chunk #{chunk_count}, rms={rms:.4f}, len={len(indata)}")
        pcm = (indata[:, 0] * 32768.0).astype(np.int16).tobytes()
        result = detector.process_chunk(pcm)
        if result == "wake":
            print(">>> WAKE WORD DETECTED! <<<")
        elif result == "stop":
            print(">>> STOP WORD DETECTED! <<<")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            device=device_index,
            callback=audio_callback,
        ):
            while running:
                time.sleep(0.1)
    except Exception as e:
        print(f"Audio error: {e}")
    finally:
        detector.stop()
        print("\nStopped.")


if __name__ == "__main__":
    main()
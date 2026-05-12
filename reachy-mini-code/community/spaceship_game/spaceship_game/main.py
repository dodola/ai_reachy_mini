import json
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from reachy_mini import ReachyMini, ReachyMiniApp
import numpy as np
import scipy.signal
import soundfile as sf
import time
from scipy.spatial.transform import Rotation as R
from pydantic import BaseModel

try:
    from . import hf_leaderboard
except ImportError:
    import hf_leaderboard  # type: ignore

# Disable uvicorn access logs to prevent spam
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("spaceship_game")

ASSETS_DIR = Path(__file__).parent / "assets"
LEADERBOARD_PATH = Path(__file__).parent / "leaderboard.json"
SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms per chunk


def load_leaderboard() -> list[dict]:
    if not LEADERBOARD_PATH.exists():
        return []
    try:
        with LEADERBOARD_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("Failed to read leaderboard: %s", exc)
    return []


def save_leaderboard(entries: list[dict]) -> None:
    try:
        LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEADERBOARD_PATH.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception as exc:
        logger.error("Failed to save leaderboard: %s", exc)


def load_audio(path: Path) -> np.ndarray:
    data, sr = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    if sr != SAMPLE_RATE:
        data = scipy.signal.resample(data, int(len(data) * SAMPLE_RATE / sr))
    return data.astype(np.float32)


class ScoreData(BaseModel):
    points: int


class DamageData(BaseModel):
    damage: int


class LeaderboardEntry(BaseModel):
    score: int
    name: str | None = None
    waves_completed: int | None = None


class SpaceshipGame(ReachyMiniApp):
    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = None

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        # Pre-decode audio files once at startup
        try:
            piew_data = load_audio(ASSETS_DIR / "piew.mp3")
            music_data = load_audio(ASSETS_DIR / "ost.mp3")
        except Exception as e:
            print(f"Warning: could not load audio files: {e}")
            piew_data = np.zeros(0, dtype=np.float32)
            music_data = np.zeros(CHUNK_SIZE, dtype=np.float32)

        # Audio mixing state
        piew_state = {"offset": -1}  # -1 = not playing
        piew_lock = threading.Lock()
        music_started = threading.Event()

        # Shared state for sensor data
        current_head_pose = np.eye(4)
        current_antennas = [0.0, 0.0]
        game_score = 0
        player_health = 100

        # Game state
        fire_left = False
        fire_right = False

        # Start audio pipeline
        reachy_mini.media.start_playing()

        def audio_loop():
            pos = 0
            while not stop_event.is_set():
                if music_started.is_set() and len(music_data) > 0:
                    end = pos + CHUNK_SIZE
                    if end <= len(music_data):
                        chunk = music_data[pos:end].copy()
                    else:
                        chunk = np.concatenate(
                            [music_data[pos:], music_data[: end - len(music_data)]]
                        )
                    pos = end % len(music_data)
                else:
                    chunk = np.zeros(CHUNK_SIZE, dtype=np.float32)

                with piew_lock:
                    if piew_state["offset"] >= 0 and len(piew_data) > 0:
                        remaining = len(piew_data) - piew_state["offset"]
                        mix_len = min(CHUNK_SIZE, remaining)
                        chunk[:mix_len] = np.clip(
                            chunk[:mix_len]
                            + piew_data[
                                piew_state["offset"] : piew_state["offset"] + mix_len
                            ],
                            -1.0,
                            1.0,
                        )
                        piew_state["offset"] += mix_len
                        if piew_state["offset"] >= len(piew_data):
                            piew_state["offset"] = -1

                reachy_mini.media.push_audio_sample(chunk)
                time.sleep(CHUNK_SIZE / SAMPLE_RATE)

            reachy_mini.media.stop_playing()

        threading.Thread(target=audio_loop, daemon=True).start()

        # REST endpoints
        @self.settings_app.get("/sensor_data")
        def get_sensor_data():
            rotation_matrix = current_head_pose[:3, :3]
            r = R.from_matrix(rotation_matrix)
            roll, pitch, yaw = r.as_euler("xyz", degrees=True)

            return {
                "roll": float(roll),
                "pitch": float(pitch),
                "yaw": float(yaw),
                "antennas": {
                    "right": float(current_antennas[0]),
                    "left": float(current_antennas[1]),
                },
                "fire_left": fire_left,
                "fire_right": fire_right,
                "score": game_score,
                "health": player_health,
            }

        @self.settings_app.post("/add_score")
        def add_score_endpoint(data: ScoreData):
            nonlocal game_score
            game_score += data.points
            return {"score": game_score}

        @self.settings_app.post("/damage_player")
        def damage_player_endpoint(data: DamageData):
            nonlocal player_health
            player_health = max(0, player_health - data.damage)
            return {"health": player_health}

        @self.settings_app.post("/reset_game")
        def reset_game():
            nonlocal game_score, player_health
            game_score = 0
            player_health = 100
            return {"score": game_score, "health": player_health}

        @self.settings_app.post("/start_music")
        def start_music():
            music_started.set()
            return {"status": "music_started"}

        @self.settings_app.post("/stop_music")
        def stop_music():
            music_started.clear()
            return {"status": "music_stopped"}

        @self.settings_app.get("/leaderboard")
        def get_leaderboard():
            return {"entries": load_leaderboard()}

        @self.settings_app.post("/leaderboard")
        def submit_leaderboard(entry: LeaderboardEntry):
            entries = load_leaderboard()
            now = datetime.now(timezone.utc)
            record = {
                "score": int(entry.score),
                "name": entry.name or "Anonymous",
                "timestamp": time.time(),
                "date": now.isoformat(),
            }
            if entry.waves_completed is not None:
                record["waves_completed"] = entry.waves_completed
            entries.append(record)
            entries.sort(key=lambda item: item.get("score", 0), reverse=True)
            entries = entries[:10]
            save_leaderboard(entries)
            try:
                hf_leaderboard.get_manager().sync_async()
            except Exception as exc:
                logger.debug("Failed to trigger global sync: %s", exc)
            return {"entries": entries}

        @self.settings_app.get("/hf_status")
        def get_hf_status():
            try:
                manager = hf_leaderboard.get_manager()
                return manager.check_status()
            except Exception as exc:
                logger.warning("Failed to check HF status: %s", exc)
                return {"available": False, "logged_in": False, "username": None, "message": str(exc)}

        @self.settings_app.get("/global_leaderboard")
        def get_global_leaderboard():
            try:
                manager = hf_leaderboard.get_manager()
                return manager.get_state()
            except Exception as exc:
                logger.warning("Failed to get global leaderboard: %s", exc)
                return {"entries": [], "sync_error": str(exc), "is_syncing": False}

        @self.settings_app.post("/global_leaderboard/sync")
        def sync_global_leaderboard():
            try:
                manager = hf_leaderboard.get_manager()
                manager.sync_async()
                return {"status": "sync_started"}
            except Exception as exc:
                logger.warning("Failed to start global sync: %s", exc)
                return {"status": "error", "error": str(exc)}

        @self.settings_app.post("/global_leaderboard/publish")
        def publish_to_global_leaderboard():
            try:
                manager = hf_leaderboard.get_manager()
                local_entries = load_leaderboard()
                if not local_entries:
                    return {"success": False, "error": "No local scores to publish", "repo_url": None}
                return manager.publish(local_entries)
            except Exception as exc:
                logger.warning("Failed to publish leaderboard: %s", exc)
                return {"success": False, "error": str(exc), "repo_url": None}

        # Trigger initial global leaderboard sync on startup
        try:
            manager = hf_leaderboard.get_manager()
            manager.check_status()
            manager.sync_async()
            logger.info("Started initial global leaderboard sync")
        except Exception as exc:
            logger.warning("Failed to start initial global sync: %s", exc)

        # Main control loop
        prev_fire_left = False
        prev_fire_right = False
        PULL_THRESHOLD = 0.25

        while not stop_event.is_set():
            current_head_pose = reachy_mini.get_current_head_pose()
            current_antennas = reachy_mini.get_present_antenna_joint_positions()

            # Right antenna controls LEFT gun (pull down = negative)
            new_fire_left = current_antennas[0] < -PULL_THRESHOLD
            if new_fire_left and not prev_fire_left:
                fire_left = True
                with piew_lock:
                    piew_state["offset"] = 0
            elif not new_fire_left:
                fire_left = False
            prev_fire_left = new_fire_left

            # Left antenna controls RIGHT gun (pull down = positive)
            new_fire_right = current_antennas[1] > PULL_THRESHOLD
            if new_fire_right and not prev_fire_right:
                fire_right = True
                with piew_lock:
                    piew_state["offset"] = 0
            elif not new_fire_right:
                fire_right = False
            prev_fire_right = new_fire_right

            time.sleep(0.02)


if __name__ == "__main__":
    app = SpaceshipGame()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()

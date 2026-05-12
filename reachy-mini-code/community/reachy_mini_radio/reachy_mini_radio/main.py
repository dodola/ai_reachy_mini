import json
import queue
import threading
import time
from pathlib import Path

import av
import numpy as np
from reachy_mini import ReachyMini, ReachyMiniApp

from reachy_mini_radio.antenna_button import AntennaButton

# -----------------------------
# Config
# -----------------------------
RADIOS_FILE = Path(__file__).parent / "webradios.json"

SAMPLE_RATE = 16000
NB_CHANNELS = 1
BLOCKSIZE = 1024

# Station ranges (in radians)
station_bandwidth = np.deg2rad(20)  # where station fades in/out
station_sweetspot = np.deg2rad(5)  # zone with no static around station

# Noise parameters
noise_std = 0.3  # noise amplitude
max_noise_gain = 1.0  # maximum noise when off-station


def clean_station_entries(data):
    cleaned = []
    seen_urls = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        if not url:
            continue
        url_lower = url.lower()
        if url_lower in seen_urls:
            continue
        seen_urls.add(url_lower)
        name = (item.get("name") or url).strip()
        cleaned.append({"name": name, "url": url})
    return cleaned


def save_stations_to_file(path: Path, stations: list[dict[str, str]]):
    cleaned = clean_station_entries(stations)
    try:
        path.write_text(
            json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[save_stations_to_file] JSON error: {e}")
        raise
    return cleaned


# -----------------------------
# Radio decoding
# -----------------------------
class RadioDecoder:
    def __init__(self, name, url, sr, channels):
        self.name = name
        self.url = url
        self.sr = sr
        self.channels = channels
        self.buffer_tmp = []
        self.queue = queue.Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        print("stopping decoder", self.name)
        if self.thread.is_alive():
            print("here")
            self.thread.join()

    def _run(self):
        try:
            container = av.open(self.url, timeout=5.0)
            audio_stream = next(s for s in container.streams if s.type == "audio")

            resampler = av.audio.resampler.AudioResampler(
                format="flt",
                layout="mono",
                rate=self.sr,
            )

            for packet in container.demux(audio_stream):
                if self.stop_event.is_set():
                    break

                for frame in packet.decode():
                    for out_frame in resampler.resample(frame):
                        arr = out_frame.to_ndarray()

                        if arr.ndim == 1:
                            arr = arr[np.newaxis, :]

                        pcm = arr.T  # (samples, channels)
                        # print(pcm.shape)

                        if len(self.buffer_tmp) == 0:
                            self.buffer_tmp = pcm
                        else:
                            self.buffer_tmp = np.concatenate(
                                (self.buffer_tmp, pcm), axis=0
                            )
                        """
                        i = 0
                        n = pcm.shape[0]
                        while i < n and not self.stop_event.is_set():
                            chunk = pcm[i : i + BLOCKSIZE, :]
                            i += BLOCKSIZE
                            try:
                                print("put chunk", chunk.shape)
                                self.queue.put(chunk, timeout=0.1)
                            except queue.Full:
                                # drop if output can't keep up
                                # print("drop")
                                # break
                                # drop old chunk to make space
                                self.queue.get(timeout=0.1)
                                self.queue.put(chunk, timeout=0.1)
                        """
                if len(self.buffer_tmp) >= BLOCKSIZE:
                    chunk = self.buffer_tmp[0:BLOCKSIZE, :]
                    self.buffer_tmp = self.buffer_tmp[BLOCKSIZE:, :]
                    try:
                        self.queue.put(chunk, timeout=0.1)
                    except queue.Full:
                        # drop if output can't keep up
                        self.queue.get(timeout=0.1)
                        self.queue.put(chunk, timeout=0.1)
                time.sleep(0.02)

        except Exception as e:
            print(f"[RadioDecoder] {self.name} error: {e}")
        finally:
            print(f"[RadioDecoder] {self.name} stopped")

    def get_samples(self, chunk_size):
        out = np.zeros((chunk_size, self.channels), dtype=np.float32)
        filled = 0
        while filled < chunk_size:
            needed = chunk_size - filled
            try:
                chunk = self.queue.get(timeout=0.1)
            except queue.Empty:
                # print(f"no more chunks {time.time()}")
                # break
                continue

            length = min(needed, chunk.shape[0])
            out[filled : filled + length, :] = chunk[:length, :]
            filled += length

            """
            if chunk.shape[0] > length:
                remainder = chunk[length:, :]
                try:
                    self.queue.put_nowait(remainder)
                    print("remainder")
                except queue.Full:
                    pass
            """
        return out[:filled, :]

    def get_samples2(self):
        try:
            chunk = self.queue.get(timeout=0.1)
            return chunk
        except queue.Empty:
            return None


# -----------------------------
# Shared radio set (for hot reload)
# -----------------------------
class RadioSet:
    """Holds current set of stations and their decoders, with a lock."""

    def __init__(self):
        self.lock = threading.Lock()
        self.station_names = []  # list[str]
        self.station_angles = np.array([], dtype=np.float32)  # radians
        self.decoders: list[RadioDecoder] = []  # list[RadioDecoder]

    def update(self, stations):
        """
        stations: list of dicts [{"name":..., "url":...}, ...]
        Stops old decoders, creates new ones, randomizes angles.
        """
        print(f"[RadioSet] Updating stations ({len(stations)} entries)")

        # Stop old decoders
        with self.lock:
            old_decoders = self.decoders
            self.decoders = []
            self.station_names = []
            self.station_angles = np.array([], dtype=np.float32)

        for d in old_decoders:
            d.stop()

        if not stations:
            print("[RadioSet] No stations, only static will be played.")
            return

        # Build new decoders
        new_decoders: list[RadioDecoder] = []
        station_names: list[str] = []
        for s in stations:
            name = s.get("name") or s.get("url") or "Unnamed"
            url = s.get("url")
            if not url:
                continue
            dec = RadioDecoder(name, url, sr=SAMPLE_RATE, channels=NB_CHANNELS)
            dec.start()
            new_decoders.append(dec)
            station_names.append(name)
            print(f"[RadioSet] Added station: {name} -> {url}")

        if not new_decoders:
            print("[RadioSet] No valid stations after cleaning.")
            return

        # Random angles on circle [0, 2π)
        station_angles = np.random.uniform(0, 2 * np.pi, size=len(new_decoders)).astype(
            np.float32
        )
        print("STATION ANGLES (radians):", station_angles)

        with self.lock:
            self.decoders = new_decoders
            self.station_names = station_names
            self.station_angles = station_angles

        print("[RadioSet] Update complete.")


def load_stations_from_file(path: Path):
    """Read stations from JSON file; returns list[dict{name,url}]."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text("utf-8"))
    except Exception as e:
        print(f"[load_stations_from_file] JSON error: {e}")
        return []

    if not isinstance(data, list):
        return []

    return clean_station_entries(data)


def stations_watcher(stop_event: threading.Event, radioset: RadioSet, path: Path):
    """Background thread: watch JSON file and hot-reload when it changes."""
    last_mtime = None
    while not stop_event.is_set():
        try:
            stat = path.stat()
            mtime = stat.st_mtime
        except FileNotFoundError:
            mtime = None

        if mtime != last_mtime:
            last_mtime = mtime
            print(f"[Watcher] Detected change in {path}, reloading stations...")
            stations = load_stations_from_file(path)
            radioset.update(stations)

        stop_event.wait(1.0)  # check once per second


# -----------------------------
# Antenna + tuning logic
# -----------------------------
def circular_distance(a, b):
    diff = np.abs(a - b)
    return np.minimum(diff, 2 * np.pi - diff)


def between_angles(angle, _angles):
    """
    Given an angle (float) and a list of _angles (floats, in radians),
    return the previous and next angles in circular order.
    If angle is too close to an angle in _angles, ignore that angle in _angles to avoid returning it as both previous and next.
    """

    angles = _angles.copy()
    # Sort angles
    sorted_angles = sorted(angles)

    # if there are only two angles, find the closest one and return the other as previous and next
    if len(sorted_angles) == 2:
        dists = circular_distance(angle, np.array(sorted_angles))
        nearest_idx = int(np.argmin(dists))
        if nearest_idx == 0:
            return sorted_angles[1], sorted_angles[1]
        else:
            return sorted_angles[0], sorted_angles[0]

    # Insert angle into sorted list to find position
    import bisect

    idx = bisect.bisect_left(sorted_angles, angle)
    if idx > 0 and abs(sorted_angles[idx - 1] - angle) < 0.05:
        # too close to previous angle, ignore it
        sorted_angles.pop(idx - 1)
        idx -= 1
    elif idx < len(sorted_angles) and abs(sorted_angles[idx] - angle) < 0.05:
        # too close to next angle, ignore it
        sorted_angles.pop(idx)

    # Previous angle (circular)
    prev_angle = sorted_angles[idx - 1]  # works even if idx = 0 (wraps)

    # Next angle (circular)
    if idx == len(sorted_angles):
        next_angle = sorted_angles[0]  # wrap
    else:
        next_angle = sorted_angles[idx]  # next in sorted list

    return prev_angle, next_angle


class ReachyMiniRadio(ReachyMiniApp):
    # If your webradio selector serves the UI at this URL:
    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = "gstreamer_no_video"

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        # Configure audio output with a small buffer to enable responsive station switching
        reachy_mini.media.audio.stop_playing()
        reachy_mini.media.audio.set_max_output_buffers(3)
        reachy_mini.media.audio.start_playing()

        # Shared radio set
        radioset = RadioSet()

        @self.settings_app.get("/api/webradios")
        async def get_webradios():
            """Expose the current list of stations to the settings UI."""
            return load_stations_from_file(RADIOS_FILE)

        @self.settings_app.post("/api/webradios")
        async def save_webradios(payload: list[dict[str, str]]):
            """Persist the stations selected in the settings UI."""
            cleaned = save_stations_to_file(RADIOS_FILE, payload)
            return {"ok": True, "count": len(cleaned)}

        self.antenna_button = AntennaButton(reachy_mini, stop_event)

        # Initial load of stations
        initial_stations = load_stations_from_file(RADIOS_FILE)
        radioset.update(initial_stations)

        # Start watcher thread that reloads stations when JSON changes
        watcher_thread = threading.Thread(
            target=stations_watcher,
            args=(stop_event, radioset, RADIOS_FILE),
            daemon=True,
        )
        watcher_thread.start()

        # Antenna calibration
        state = {"angle": 0.0}
        # calib = {"center": None, "range": 2 * np.pi}  # very rough mapping

        def update_angle():
            raw = reachy_mini.get_present_antenna_joint_positions()[1]
            return raw % (2 * np.pi)

        reachy_mini.enable_motors(["left_antenna"])
        reachy_mini.goto_target(np.eye(4), antennas=[0, 0])
        reachy_mini.disable_motors(["left_antenna"])

        rng = np.random.default_rng()

        def audio_callback(outdata, frames, time_info, status):
            if status:
                print(status, flush=True)

            angle = state["angle"]

            with radioset.lock:
                station_angles = radioset.station_angles
                decoders = list(radioset.decoders)

            # Always produce some output (static), even with no stations
            if station_angles.size == 0 or not decoders:
                noise = rng.normal(0.0, noise_std, size=(frames, NB_CHANNELS)).astype(
                    np.float32
                )
                np.clip(noise, -1.0, 1.0, out=noise)
                outdata[:] = noise
                return

            # Find nearest station
            dists = circular_distance(angle, station_angles)
            nearest_idx = int(np.argmin(dists))
            d_min = float(dists[nearest_idx])

            # Station gain (0 outside bandwidth, 1 at station)
            if d_min >= station_bandwidth:
                station_gain = 0.0
            else:
                station_gain = 1.0 - (d_min / station_bandwidth)

            # Get radio samples for nearest station only
            decoder = decoders[nearest_idx]
            # radio = decoder.get_samples(frames)
            radio = decoder.get_samples2()
            if radio is None:
                outdata = None
                print("no radio samples")
                return

            # Noise gain with "sweet spot"
            if d_min <= station_sweetspot:
                # In sweet spot: no static at all
                noise_gain = 0.0
            elif d_min >= station_bandwidth:
                # Completely off any station: maximum noise
                noise_gain = max_noise_gain
            else:
                # Between sweet spot and bandwidth: ramp from 0 to max_noise_gain
                t = (d_min - station_sweetspot) / (
                    station_bandwidth - station_sweetspot
                )
                t = max(0.0, min(1.0, t))
                noise_gain = t * max_noise_gain

            noise = rng.normal(
                0.0, noise_std, size=(radio.shape[0], NB_CHANNELS)
            ).astype(np.float32)
            # print("station gain:", station_gain, "noise gain:", noise_gain)

            mix = station_gain * radio + noise_gain * noise
            np.clip(mix, -1.0, 1.0, out=mix)
            outdata[:] = mix
            # outdata = radio

        print(
            "ReachyMiniRadio running. Move the left antenna to tune stations (hot-reload from webradios.json)."
        )
        try:
            # chunk_size = 1024

            reachy_mini.media.start_playing()
            outdata = np.zeros((BLOCKSIZE, NB_CHANNELS), dtype=np.float32)
            while not stop_event.is_set():
                state["angle"] = update_angle()  # 0 to 2pi range

                audio_callback(outdata, BLOCKSIZE, None, None)

                if outdata is not None:
                    reachy_mini.media.push_audio_sample(outdata)

                triggered, direction = self.antenna_button.is_triggered()
                if triggered:
                    print(f"[AntennaButton] Triggered! Direction: {direction}")
                    # use radioset.station_angles to get the next angle to jump to depending on direction "left" or "right"
                    with radioset.lock:
                        if (
                            radioset.station_angles.size == 0
                            or radioset.station_angles.size == 1
                        ):
                            continue
                        current_angle = state["angle"]  # 0 to 2pi range
                        before_angle, after_angle = between_angles(
                            current_angle, radioset.station_angles.copy()
                        )

                        if before_angle > np.pi:
                            before_angle -= 2 * np.pi
                        if before_angle < -np.pi:
                            before_angle += 2 * np.pi
                        if after_angle > np.pi:
                            after_angle -= 2 * np.pi
                        if after_angle < -np.pi:
                            after_angle += 2 * np.pi
                        if current_angle > np.pi:
                            current_angle -= 2 * np.pi
                        if current_angle < -np.pi:
                            current_angle += 2 * np.pi

                        print(
                            "before:",
                            before_angle,
                            "current angle:",
                            current_angle,
                            "after:",
                            after_angle,
                        )
                        if direction == "right":
                            target_angle = after_angle
                        else:
                            target_angle = before_angle
                        print(
                            f"[AntennaButton] Jumping to angle: {target_angle:.2f} rad"
                        )
                        reachy_mini.enable_motors(["left_antenna"])
                        reachy_mini.set_target_antenna_joint_positions(
                            [0.0, float(target_angle)]
                        )
                        time.sleep(0.3)  # wait for movement
                        reachy_mini.disable_motors(["left_antenna"])

                time.sleep(0.01)
        finally:
            # Stop watcher
            stop_event.set()
            watcher_thread.join(timeout=1.0)

            # Stop decoders
            with radioset.lock:
                decoders = list(radioset.decoders)
            for d in decoders:
                d.stop()

            reachy_mini.enable_motors(["left_antenna"])
            time.sleep(0.5)



if __name__ == "__main__":
    app = ReachyMiniRadio()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()

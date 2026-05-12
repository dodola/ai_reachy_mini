import http.server
import json
import threading
from pathlib import Path
from typing import List, Dict

# Where we persist selected stations
RADIOS_FILE = Path(__file__).parent / "webradios.json"

_selected_radios: List[Dict[str, str]] = []
_radios_lock = threading.Lock()


def get_radios() -> List[Dict[str, str]]:
    with _radios_lock:
        return list(_selected_radios)


def set_radios(radios: List[Dict[str, str]]):
    global _selected_radios
    with _radios_lock:
        _selected_radios = radios


def load_radios_from_disk():
    if RADIOS_FILE.exists():
        try:
            data = json.loads(RADIOS_FILE.read_text("utf-8"))
            if isinstance(data, list):
                cleaned = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    url = (item.get("url") or "").strip()
                    if not url:
                        continue
                    name = (item.get("name") or url).strip()
                    cleaned.append({"name": name, "url": url})
                set_radios(cleaned)
                print(f"Loaded {len(cleaned)} radios from {RADIOS_FILE}")
        except Exception as e:
            print(f"Failed to load {RADIOS_FILE}: {e}")
    else:
        set_radios([])


def save_radios_to_disk():
    radios = get_radios()
    try:
        RADIOS_FILE.write_text(
            json.dumps(radios, indent=2, ensure_ascii=False), "utf-8"
        )
        print(f"Saved {len(radios)} radios to {RADIOS_FILE}")
    except Exception as e:
        print(f"Failed to save {RADIOS_FILE}: {e}")


# --- HTTP Handler with tiny JSON API ---
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve from current directory
        self.directory = str(Path(__file__).parent)
        super().__init__(*args, directory=self.directory, **kwargs)

    def log_message(self, fmt, *args):
        # Quiet logs
        pass

    def _send_json(self, obj, status=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        print("DO GET")
        if self.path == "/api/webradios":
            radios = get_radios()
            self._send_json(radios)
            return
        # Static files (index.html, etc.)
        super().do_GET()

    def do_POST(self):
        print("DO POST")
        if self.path != "/api/webradios":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)
        except Exception:
            self._send_json({"ok": False, "error": "invalid-json"}, status=400)
            return

        if not isinstance(payload, list):
            self._send_json({"ok": False, "error": "expected-list"}, status=400)
            return

        cleaned = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            url = (item.get("url") or "").strip()
            if not url:
                continue
            name = (item.get("name") or url).strip()
            cleaned.append({"name": name, "url": url})

        set_radios(cleaned)
        save_radios_to_disk()
        self._send_json({"ok": True, "count": len(cleaned)})


def start_server(
    stop_event: threading.Event, host: str = "localhost", port: int = 8080
):
    httpd = http.server.HTTPServer((host, port), Handler)
    httpd.timeout = 0.5
    print(f"Serving on http://{host}:{port}")

    while not stop_event.is_set():
        httpd.handle_request()

    httpd.server_close()
    print("HTTP server stopped.")


def run_webradio_selector(stop_event: threading.Event):
    load_radios_from_disk()

    try:
        start_server(stop_event)
    except KeyboardInterrupt:
        print("Stopping...")
        stop.set()

    print("Done.")


if __name__ == "__main__":
    stop = threading.Event()
    run_webradio_selector(stop)

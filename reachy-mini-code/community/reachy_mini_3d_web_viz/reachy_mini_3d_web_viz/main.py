import threading
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from reachy_mini import ReachyMiniApp
from reachy_mini.reachy_mini import ReachyMini
from scipy.spatial.transform import Rotation as R


# Module-level URL for app managers that scan the file without importing.
custom_app_url = "http://127.0.0.1:8080"

# Directory containing static files
STATIC_DIR = Path(__file__).resolve().parent / "static"


def register_routes(app: FastAPI) -> None:
    """Register routes to serve static files."""

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/style.css")
    async def style_css() -> FileResponse:
        return FileResponse(STATIC_DIR / "style.css")

    # Mount static directories
    app.mount("/src", StaticFiles(directory=STATIC_DIR / "src"), name="src")
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


class ReachyMini3dWebViz(ReachyMiniApp):
    custom_app_url: str | None = "http://127.0.0.1:8080"

    def __init__(self):
        super().__init__()

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        if self.settings_app is not None:
            register_routes(self.settings_app)
            print(f"📄 3D Viewer: {ReachyMini3dWebViz.custom_app_url}")

        try:
            while not stop_event.is_set():
                # now = time.time()
                # swing = np.sin(2 * np.pi * 0.3 * now + np.pi)
                # bob = np.sin(2 * np.pi * 0.5 * now)

                # pose = np.eye(4)
                # pose[:3, :3] = R.from_euler("z", 0.5 * swing, degrees=False).as_matrix()
                # pose[2, 3] = 0.005 * swing + 0.01 * bob

                # antennas = np.full(2, bob)
                # reachy_mini.set_target(head=pose, antennas=antennas)
                time.sleep(10)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    print("🤖 Starting Reachy Mini 3D Web Visualizer...")
    ReachyMini3dWebViz().wrapped_run()
    print("👋 Goodbye!")
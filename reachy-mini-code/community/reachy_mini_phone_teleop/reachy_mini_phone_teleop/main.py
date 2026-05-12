import threading
import os
import numpy as np
from fastapi.responses import FileResponse, JSONResponse
from fastapi import status
from fastapi.staticfiles import StaticFiles
from importlib.resources import files
from reachy_mini import ReachyMini, ReachyMiniApp
from teleop import Teleop
import teleop


class ReachyMiniPhoneTeleop(ReachyMiniApp):
    custom_app_url: str | None = "https://0.0.0.0:8042"
    dont_start_webserver = True
    _web_root = files(__package__) / "web"

    @staticmethod
    def _remove_default_route(app) -> None:
        """Drop the packaged index route so we can serve our custom UI."""
        filtered_routes = []
        for route in app.router.routes:
            if getattr(route, "path", None) == "/" and getattr(route, "methods", set()) == {"GET"}:
                continue
            filtered_routes.append(route)
        app.router.routes = filtered_routes

    def _attach_custom_ui(self, teleop_instance: Teleop, reachy_mini: ReachyMini) -> None:
        """Serve the local UI instead of the one baked into teleop and expose a reset endpoint."""
        app = teleop_instance._Teleop__app  # type: ignore[attr-defined]

        if self._web_root.is_dir():
            self._remove_default_route(app)

            # Ensure assets are mounted (in case there's an issue with the default mount on Windows)
            teleop_assets_dir = os.path.join(os.path.dirname(teleop.__file__), "assets")
            if os.path.exists(teleop_assets_dir):
                # Remove existing assets mount if present to avoid conflicts
                filtered_routes = []
                for route in app.router.routes:
                    if hasattr(route, 'path') and route.path == '/assets':
                        continue
                    filtered_routes.append(route)
                app.router.routes = filtered_routes
                # Re-mount the assets directory
                app.mount("/assets", StaticFiles(directory=teleop_assets_dir), name="assets")

            @app.get("/")
            async def index():
                return FileResponse(str(self._web_root / "index.html"))

            @app.post("/reset")
            async def reset_pose():
                # Reset robot to neutral
                reachy_mini.goto_target(np.eye(4))
                # Reset teleop internal state so phone pose is re-baselined
                teleop_instance.set_pose(np.eye(4))
                teleop_instance._Teleop__relative_pose_init = None  # type: ignore[attr-defined]
                teleop_instance._Teleop__absolute_pose_init = None  # type: ignore[attr-defined]
                teleop_instance._Teleop__previous_received_pose = None  # type: ignore[attr-defined]
                return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        port = self.custom_app_url.split(":")[-1].split("/")[0]
        print(f"Starting Teleop server on port {port}...")

        def callback(pose, message):
            pose[:3, 3] *= 0.3
            antennas = None
            if isinstance(message, dict) and message.get("antennas") is not None:
                try:
                    antennas_arr = np.array(message.get("antennas"), dtype=float).flatten()
                    if antennas_arr.shape == (2,):
                        antennas = np.clip(antennas_arr, -3.0, 3.0)
                except Exception:
                    antennas = None

            reachy_mini.set_target(head=pose, antennas=antennas)

        teleop = Teleop(port=int(port))
        self._attach_custom_ui(teleop, reachy_mini)
        teleop.set_pose(np.eye(4))
        teleop.subscribe(callback)
        teleop.run()


if __name__ == "__main__":
    app = ReachyMiniPhoneTeleop()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()

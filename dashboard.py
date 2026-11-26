import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from camera import build_camera_source, check_connection
from monitor import Monitor

PAGE = Path(__file__).with_name("dashboard.html").read_bytes()
STREAM_INTERVAL_SECONDS = 0.1


class Dashboard:
    def __init__(self, monitor: Monitor, port: int):
        self._monitor = monitor
        self._port = port

    def start(self):
        server = ThreadingHTTPServer(("127.0.0.1", self._port), self._make_handler())
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Dashboard: http://localhost:{self._port}", flush=True)

    def _state(self) -> dict:
        return {"cameras": self._monitor.camera_states(), "sensitivity": self._monitor.sensitivity}

    def _test_camera(self, request: dict) -> dict:
        source = build_camera_source(request.get("address", ""), request.get("username", ""), request.get("password", ""))
        return {"connected": check_connection(source)}

    def _add_camera(self, request: dict) -> dict:
        source = build_camera_source(request.get("address", ""), request.get("username", ""), request.get("password", ""))
        self._monitor.add_camera(request.get("name", ""), source)
        return {}

    def _set_sensitivity(self, request: dict) -> dict:
        self._monitor.set_sensitivity(request.get("level", ""))
        return {}

    def _make_handler(self):
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    self._send("text/html", PAGE)
                elif self.path == "/api/state":
                    self._send("application/json", json.dumps(dashboard._state()).encode())
                elif self.path.startswith("/stream/"):
                    self._stream_mjpeg(unquote(self.path.removeprefix("/stream/")))
                else:
                    self.send_error(404)

            def do_POST(self):
                actions = {
                    "/api/cameras/test": dashboard._test_camera,
                    "/api/cameras": dashboard._add_camera,
                    "/api/sensitivity": dashboard._set_sensitivity,
                }
                self._call_api(actions.get(self.path))

            def do_DELETE(self):
                prefix = "/api/cameras/"
                if not self.path.startswith(prefix):
                    return self.send_error(404)
                name = unquote(self.path.removeprefix(prefix))
                self._call_api(lambda _: dashboard._monitor.remove_camera(name) or {})

            def _call_api(self, action):
                if action is None:
                    return self.send_error(404)
                try:
                    result = {"ok": True, **action(self._read_json())}
                except ValueError as error:
                    result = {"ok": False, "error": str(error)}
                self._send("application/json", json.dumps(result).encode())

            def _read_json(self) -> dict:
                # Requiring JSON blocks other websites from sending forms to this local server.
                if self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Unsupported request.")
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                return json.loads(body or b"{}")

            def _send(self, content_type: str, body: bytes):
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _stream_mjpeg(self, camera_name: str):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while True:
                        jpeg = dashboard._monitor.latest_jpeg(camera_name)
                        if jpeg:
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                        time.sleep(STREAM_INTERVAL_SECONDS)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        return Handler

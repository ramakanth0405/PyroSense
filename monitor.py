import threading
import time

import cv2

from alerts import Alerter
from camera import Camera
from config import save_config
from detector import Detector

SENSITIVITY_LEVELS = {"low": (0.7, 5), "medium": (0.5, 3), "high": (0.3, 2)}  # confidence, confirm frames
ALERT_BADGE_SECONDS = 30


class AlertGate:
    """Fires only after N consecutive detections, then stays quiet for a cooldown."""

    def __init__(self, confirm_frames: int, cooldown_seconds: int):
        self._confirm_frames = confirm_frames
        self._cooldown_seconds = cooldown_seconds
        self._streak = 0
        self._last_alert_time = 0.0

    def should_alert(self, hazards: set[str]) -> bool:
        self._streak = self._streak + 1 if hazards else 0
        confirmed = self._streak >= self._confirm_frames
        cooled_down = time.time() - self._last_alert_time >= self._cooldown_seconds
        if confirmed and cooled_down:
            self._last_alert_time = time.time()
            return True
        return False


class Monitor:
    """Watches all cameras, raises alerts, and can be changed while running."""

    def __init__(self, config: dict):
        self._config = config
        self._lock = threading.Lock()
        confidence, self._confirm_frames = SENSITIVITY_LEVELS[config["sensitivity"]]
        self._detector = Detector(config["model"], confidence)
        self._alerter = Alerter(config["snapshot_dir"], config["webhook_url"])
        self._cameras: dict[str, Camera] = {}
        self._gates: dict[str, AlertGate] = {}
        self._jpegs: dict[str, bytes] = {}
        self._last_alert_times: dict[str, float] = {}
        for camera in config["cameras"]:
            self._start_camera(camera["name"], camera["url"])

    def run(self):
        while True:
            fresh = self._collect_fresh_frames()
            if fresh:
                self._process(fresh)
            else:
                time.sleep(0.05)

    def add_camera(self, name: str, source: str | int):
        name = name.strip()
        if not name:
            raise ValueError("Give the camera a name.")
        with self._lock:
            if name in self._cameras:
                raise ValueError(f"A camera named '{name}' already exists.")
            self._start_camera(name, source)
            self._config["cameras"].append({"name": name, "url": source})
            save_config(self._config)

    def remove_camera(self, name: str):
        with self._lock:
            camera = self._cameras.pop(name, None)
            if camera is None:
                return
            camera.stop()
            del self._gates[name]
            self._config["cameras"] = [c for c in self._config["cameras"] if c["name"] != name]
            save_config(self._config)

    def set_sensitivity(self, level: str):
        if level not in SENSITIVITY_LEVELS:
            raise ValueError(f"Sensitivity must be one of {list(SENSITIVITY_LEVELS)}.")
        with self._lock:
            confidence, self._confirm_frames = SENSITIVITY_LEVELS[level]
            self._detector.confidence = confidence
            self._gates = {name: self._new_gate() for name in self._cameras}
            self._config["sensitivity"] = level
            save_config(self._config)

    @property
    def sensitivity(self) -> str:
        return self._config["sensitivity"]

    def camera_states(self) -> list[dict]:
        now = time.time()
        with self._lock:
            return [
                {"name": name, "alert": now - self._last_alert_times.get(name, 0) < ALERT_BADGE_SECONDS}
                for name in self._cameras
            ]

    def latest_jpeg(self, camera_name: str) -> bytes | None:
        return self._jpegs.get(camera_name)

    def _start_camera(self, name: str, source: str | int):
        self._cameras[name] = Camera(name, source)
        self._gates[name] = self._new_gate()

    def _new_gate(self) -> AlertGate:
        return AlertGate(self._confirm_frames, self._config["cooldown_seconds"])

    def _collect_fresh_frames(self) -> list:
        with self._lock:
            watched = [(camera, self._gates[name]) for name, camera in self._cameras.items()]
        fresh = [(camera, gate, camera.latest_frame()) for camera, gate in watched]
        return [(camera, gate, frame) for camera, gate, frame in fresh if frame is not None]

    def _process(self, fresh: list):
        detections = self._detector.detect([frame for _, _, frame in fresh])
        for (camera, gate, frame), detection in zip(fresh, detections):
            _, jpeg = cv2.imencode(".jpg", detection.annotated_frame)
            self._jpegs[camera.name] = jpeg.tobytes()
            if gate.should_alert(detection.hazards):
                self._alerter.raise_alert(camera.name, detection.hazards, frame)
                self._last_alert_times[camera.name] = time.time()

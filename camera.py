import threading
import time
from urllib.parse import quote

import cv2

RECONNECT_DELAY_SECONDS = 5
CONNECT_TIMEOUT_MS = 8000


def build_camera_source(address: str, username: str = "", password: str = "") -> str | int:
    """Turns what a person types into something OpenCV can open."""
    address = address.strip()
    if not address:
        raise ValueError("Enter the camera address.")
    if address.isdigit():
        return int(address)
    if not username:
        return address
    scheme, separator, rest = address.partition("://")
    if not separator:
        raise ValueError("The address should start with rtsp://, rtsps:// or http://.")
    credentials = f"{quote(username, safe='')}:{quote(password, safe='')}"
    return f"{scheme}://{credentials}@{rest}"


def check_connection(source: str | int) -> bool:
    capture = _open(source)
    connected, _ = capture.read() if capture.isOpened() else (False, None)
    capture.release()
    return connected


def _open(source: str | int) -> cv2.VideoCapture:
    if isinstance(source, int):
        return cv2.VideoCapture(source)
    timeouts = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, CONNECT_TIMEOUT_MS,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, CONNECT_TIMEOUT_MS]
    return cv2.VideoCapture(source, cv2.CAP_FFMPEG, timeouts)


class Camera:
    """Reads a stream in the background and keeps only the newest frame."""

    def __init__(self, name: str, url: str | int):
        self.name = name
        self.url = url
        self._frame = None
        self._stopped = False
        self._lock = threading.Lock()
        threading.Thread(target=self._read_forever, daemon=True).start()

    def latest_frame(self):
        with self._lock:
            frame, self._frame = self._frame, None
        return frame

    def stop(self):
        self._stopped = True

    def _read_forever(self):
        while not self._stopped:
            self._read_until_stream_drops()
            time.sleep(RECONNECT_DELAY_SECONDS)

    def _read_until_stream_drops(self):
        capture = _open(self.url)
        while not self._stopped and capture.isOpened():
            ok, frame = capture.read()
            if not ok:
                break
            with self._lock:
                self._frame = frame
        capture.release()

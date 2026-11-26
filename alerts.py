import json
import time
import urllib.request
from pathlib import Path

import cv2


class Alerter:
    def __init__(self, snapshot_dir: str, webhook_url: str):
        self._snapshot_dir = Path(snapshot_dir)
        self._snapshot_dir.mkdir(exist_ok=True)
        self._webhook_url = webhook_url

    def raise_alert(self, camera_name: str, hazards: set[str], frame):
        snapshot = self._save_snapshot(camera_name, frame)
        print(f"ALERT {camera_name}: {sorted(hazards)} -> {snapshot}", flush=True)
        if self._webhook_url:
            self._post_webhook(camera_name, hazards, snapshot)

    def _save_snapshot(self, camera_name: str, frame) -> Path:
        path = self._snapshot_dir / f"{camera_name}_{int(time.time())}.jpg"
        cv2.imwrite(str(path), frame)
        return path

    def _post_webhook(self, camera_name: str, hazards: set[str], snapshot: Path):
        body = json.dumps(
            {"camera": camera_name, "hazards": sorted(hazards), "snapshot": str(snapshot)}
        ).encode()
        request = urllib.request.Request(
            self._webhook_url, body, {"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except OSError as error:
            print(f"Webhook failed: {error}", flush=True)

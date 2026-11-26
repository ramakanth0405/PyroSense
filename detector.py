from dataclasses import dataclass

from ultralytics import YOLO

TARGET_LABELS = {"fire", "smoke"}


@dataclass
class Detection:
    hazards: set[str]
    annotated_frame: object


class Detector:
    def __init__(self, model_path: str, confidence: float):
        self._model = YOLO(model_path)
        self.confidence = confidence
        self._target_class_ids = [
            class_id for class_id, label in self._model.names.items() if label in TARGET_LABELS
        ]

    def detect(self, frames: list) -> list[Detection]:
        results = self._model.predict(
            frames, classes=self._target_class_ids, conf=self.confidence, verbose=False
        )
        return [
            Detection({result.names[int(c)] for c in result.boxes.cls}, result.plot())
            for result in results
        ]

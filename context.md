# Fire Detection System Context

## Objective
Implement a real-time IP camera-based fire and smoke detection system using the custom-trained YOLOv8n weights in `best.pt`.

## Model Details
- **Weights:** `best.pt` (fine-tuned from `yolov8n.pt` via Ultralytics/PyTorch)
- **Classes:** `0: fire`, `1: light`, `2: no-fire`, `3: smoke`
- **Inference:** Filter to `classes=[0, 3]` (`fire` and `smoke`) so `light` and `no-fire` act as hard negatives to reduce false alarms.



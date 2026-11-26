# Fire Detection

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Package manager](https://img.shields.io/badge/uv-managed-purple.svg)](https://docs.astral.sh/uv/)
[![Model](https://img.shields.io/badge/Model-YOLOv8n-orange.svg)](https://docs.ultralytics.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Description

Watches several IP cameras (and your computer's webcam) at the same time, detects **fire** and **smoke** with a custom-trained YOLOv8n model (`best.pt`), and raises an alert. A browser dashboard shows every live feed and lets anyone add or remove cameras without editing files.

- **Motivation**: Fire is only useful to catch early, and nobody can watch a wall of cameras all day.
- **Problems Solved**:
  1. One process reads many camera streams in parallel, always working on the newest frame so a slow model never builds up lag.
  2. False alarms are reduced: an alert needs several detections in a row, and each camera has a cooldown between alerts.
  3. Setup does not need a terminal after the first launch: cameras, connection tests and sensitivity are managed in the browser.
- **Target Outcomes**:
  - Run the system with your webcam in a few minutes.
  - Connect real IP cameras (RTSP, RTSPS or HTTP streams).
  - Receive a snapshot file and an optional webhook call when fire or smoke is detected.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Verification: Testing Your Setup](#verification-testing-your-setup)
- [Adding an IP Camera](#adding-an-ip-camera)
- [Readiness Checklist](#readiness-checklist)
- [Features](#features)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## How It Works

```text
camera 1 ──┐
camera 2 ──┼─▶ newest frame per camera ─▶ YOLO (fire / smoke) ─▶ N detections in a row? ─▶ alert
webcam   ──┘                                                                                 │
                                                          dashboard (live boxes) ◀───────────┘
```

| File | Role |
|---|---|
| `main.py` | Starts the monitor and the dashboard |
| `monitor.py` | Watches all cameras, applies the alert rules, lets cameras be added or removed live |
| `camera.py` | Reads one stream in the background and reconnects if it drops |
| `detector.py` | Runs the model; only `fire` and `smoke` count (`light` and `no-fire` are ignored on purpose) |
| `alerts.py` | Saves a snapshot and calls the webhook |
| `dashboard.py` / `dashboard.html` | The web page and its small API |
| `config.py` | Reads and writes `config.toml` |
| `requirements.txt` | Dependency list for the `pip` install |

---

## Prerequisites

- **Python 3.13**, plus either **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (recommended) or plain `pip`.
- A camera: your computer's webcam is enough to start.
- Tested on **macOS**. Linux and Windows have not been tested.

> [!NOTE]
> The first time you use the webcam, macOS asks for camera permission for the app that runs the command (Terminal or VS Code). Allow it, then run again.

---

## Installation

```bash
git clone https://github.com/ramakanth0405/PyroSense.git
cd PyroSense
```

Then install the dependencies with **one** of these:

**Option A: uv (recommended).** Installs the exact versions recorded in `uv.lock`.

```bash
uv sync
```

**Option B: pip.** Uses [requirements.txt](requirements.txt) (`ultralytics`, `opencv-python-headless`, `tomli-w`).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> [!NOTE]
> `requirements.txt` does not pin versions (except `tomli-w`), so `pip` may install newer releases than `uv sync` does. If you add a dependency, add it to both `requirements.txt` and `pyproject.toml`.

The model file `best.pt` is included in the repository.

Create your settings file. It is **not** in the repository because it can hold camera passwords:

```bash
cat > config.toml <<'EOF'
model = "best.pt"
sensitivity = "medium"
cooldown_seconds = 60
snapshot_dir = "alerts"
dashboard_port = 8080
webhook_url = ""
insecure_tls = false
cameras = [
    { name = "webcam", url = 0 },
]
EOF
```

> [!IMPORTANT]
> `config.toml` is listed in `.gitignore`. Never commit it: camera URLs can contain usernames and passwords.

---

## Configuration

| Setting | Meaning |
|---|---|
| `model` | Path to the YOLO weights |
| `sensitivity` | `low`, `medium` or `high`. Also changeable in the dashboard |
| `cooldown_seconds` | Minimum gap between two alerts from the same camera |
| `snapshot_dir` | Folder where alert snapshots are saved |
| `dashboard_port` | Port for the web page |
| `webhook_url` | Optional. Receives a JSON `POST` on every alert. Leave `""` to disable |
| `insecure_tls` | `true` to accept self-signed certificates (needed by some phone camera apps) |
| `cameras` | List of `{ name, url }`. Use `url = 0` for the webcam, or a stream address |

**Sensitivity levels**

| Level | Detection confidence | Detections in a row before alerting | Use when |
|---|---|---|---|
| `low` | 70% | 5 | You get false alarms |
| `medium` | 50% | 3 | Default |
| `high` | 30% | 2 | Real fires are being missed |

**Webhook payload**

```json
{"camera": "webcam", "hazards": ["fire"], "snapshot": "alerts/webcam_1795672447.jpg"}
```

---

## Verification: Testing Your Setup

Do this before trusting the system. It checks the model, the camera, the dashboard and the alert path with your webcam.

### Step 1: Start the system

```bash
uv run main.py          # Option A (uv)
python main.py          # Option B (pip, with the virtual environment activated)
```

You should see `Dashboard: http://localhost:8080`.

### Step 2: Open the dashboard

Go to **http://localhost:8080**. You should see a tile with your webcam feed.

### Step 3: Trigger a detection

> [!CAUTION]
> Never use a real flame to test. Play a fire video on a phone or another screen and point the webcam at it.

After a few frames the tile gets a red border and a **FIRE / SMOKE ALERT** badge.

### Step 4: Check the alert output

- The terminal prints a line like `ALERT webcam: ['fire'] -> alerts/webcam_<time>.jpg`.
- The snapshot image exists in the `alerts/` folder.

> [!TIP]
> If nothing triggers, set **Sensitivity** to **High** in the dashboard. A fire video on a screen is harder for the model than a real scene.

---

## Adding an IP Camera

In the dashboard click **`+ Add camera`**, fill in the form, click **`Test connection`**, then **`Add`**.

| Field | Example |
|---|---|
| Name | `Warehouse` |
| Camera address | `rtsp://192.168.1.10:554/stream` |
| Username / Password | Only if the camera asks for them |

Passwords with special characters such as `@` are handled for you in the form.

> [!CAUTION]
> `rtsp://` and `rtsps://` are different. The extra **s** means the stream is encrypted. Using the wrong one fails with a timeout or "connection refused". Copy the address exactly as the camera app shows it, including the port.

> [!NOTE]
> Phone apps such as "Android IP Camera" use `rtsps://` with a self-signed certificate. Set `insecure_tls = true` in `config.toml` and restart for those.

If you edit `config.toml` by hand, URL-encode special characters in passwords yourself (`@` becomes `%40`).


---

## Features

- Several cameras at once, each read in its own background thread
- Model runs on all cameras' newest frames together, so lag does not build up
- Automatic reconnect when a camera drops, without affecting the others
- Live dashboard with detection boxes and per-camera alert badges
- Add, test and remove cameras from the browser while running
- Sensitivity setting instead of technical thresholds
- Snapshot and optional webhook on every alert
- Settings saved to `config.toml` and kept across restarts

> [!NOTE]
> The dashboard listens on `127.0.0.1` only and has no login. It can only be opened on the computer that runs it.

---

## Troubleshooting

| Problem | Root cause | Fix |
|---|---|---|
| `Connection refused` on a camera port | The camera app is not streaming, or the port is wrong | Start the stream in the camera app and copy the exact address it shows |
| Camera test fails after about 8 seconds | Wrong address, wrong password, or the camera is on another network | Check the address, the login, and that the camera and computer share a network |
| `401 Unauthorized` in the log | Wrong username or password | Re-enter the credentials from the camera app |
| Works in VLC but not here | `rtsp` against `rtsps`, or a self-signed certificate | Match the scheme exactly and set `insecure_tls = true` |
| Password containing `@` breaks the URL | Special characters were not encoded in `config.toml` | Add the camera through the dashboard form, or use `%40` for `@` |
| Webcam tile stays empty | macOS camera permission not given | System Settings → Privacy & Security → Camera, allow your terminal, run again |
| Webcam not found | The webcam has a different index (for example with Continuity Camera) | Use `url = 1` |
| Smoke alerts on a dark or blurry view | Small model reads featureless grey frames as smoke | Set **Sensitivity** to **Low** and aim the camera at a normal scene |
| Fire video on a screen is not detected | Screens are harder for the model than real scenes | Set **Sensitivity** to **High** while testing |
| `Address already in use` | Port 8080 is taken | Change `dashboard_port` in `config.toml` |
| Tile shows an old frame | The camera dropped; the dashboard keeps the last image | Check the camera. It reconnects every few seconds by itself |

---

## License

Released under the [MIT License](LICENSE).

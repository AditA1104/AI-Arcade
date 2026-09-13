# 🎮 Pose-Controlled AI Arcade

> A live, webcam-controlled arcade game — no keyboard, no mouse, no controller. Just you.

Players control the game entirely through body movement, tracked live via webcam, competing for the top spot on a real-time leaderboard.

**100% free · Fully offline · No GPU required · Runs on a standard laptop CPU**

---

## ✨ What It Does

Stand in front of a webcam, raise your hand, and start playing. Your body becomes the controller — a live pose-tracking pipeline reads your hand position and maps it directly onto the game, powering a Fruit-Ninja-style slicer where you compete for a spot on the leaderboard.

No sensors. No wearables. No install beyond Python. Just a laptop and a webcam.

---

## ⚡ Quick Start (recommended)

One command sets up everything — Python venv, dependencies, and launches the game. No manual pip wrangling.

**Requirement:** Python 3.11 installed first ([python.org](https://www.python.org/downloads/) or `brew install python@3.11` on macOS). This is the one thing the script can't install for you.

<details>
<summary><b>macOS / Linux</b></summary>

```bash
git clone https://github.com/AditA1104/AI-Arcade.git
cd AI-Arcade
chmod +x setup.sh
./setup.sh
```
</details>

<details>
<summary><b>Windows</b></summary>

```bash
git clone https://github.com/AditA1104/AI-Arcade.git
cd AI-Arcade
setup.bat
```
(or just double-click `setup.bat` in File Explorer)
</details>

Re-running the script later just reuses the existing environment and relaunches the game — safe to run any time you want to play again.

If the script fails or you'd rather do it by hand, see the manual steps below — same result, more control over each step.

---

## 🧠 How It Works

```
   Webcam Feed              Vision Pipeline              Game Engine
┌────────────────┐      ┌────────────────────┐      ┌──────────────────┐
│                │      │  MediaPipe Pose    │      │  Pygame          │
│  Live camera   │ ───► │  Calibration       │ ───► │  Slicer mechanics│
│  capture       │      │  EMA smoothing     │      │  Leaderboard     │
│                │      │  Threaded tracking │      │  Booth UI flow   │
└────────────────┘      └────────────────────┘      └──────────────────┘
                              get_player_position()
                                  ⬇ (x, y)
```

Two independently-built modules connect through a single shared contract:

```python
get_player_position() -> (x, y)
```

This is the entire integration surface. The vision module fills it with real, live-tracked coordinates; the game module simply reads from it every frame — which is what let both halves of this project be built fully in parallel.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 👁️ Body tracking | **MediaPipe Pose** |
| 📷 Camera capture | **OpenCV** |
| 🕹️ Game engine | **Pygame** |
| 🏆 Leaderboard | **SQLite** |
| 🐍 Language | **Python 3.11** |

---

## 📁 Project Structure

```
AI-Arcade/
├── vision.py             # Body tracking — camera, MediaPipe, calibration, smoothing
├── input.py              # Integration boundary — main.py's only link to player input
├── main.py                # Game — Pygame mechanics, states, leaderboard, booth UI
├── leaderboard.py         # SQLite leaderboard persistence
├── sprites.py             # Fruit/bomb sprite rendering
├── requirements.txt       # Pinned, tested dependency versions
├── setup.sh / setup.bat   # One-command environment setup + launch
├── fruit_assets/          # Sprites
└── README.md
```

---

## 🚀 Manual Setup (if you skipped the Quick Start above)

### 1 — Install Python 3.11

<details>
<summary><b>macOS</b></summary>

```bash
brew install python@3.11
```
</details>

<details>
<summary><b>Windows</b></summary>

Download from [python.org](https://www.python.org/downloads/) — ✅ make sure to check **"Add Python to PATH"** during install.
</details>

> ⚠️ Stick to **3.11** — not the newest release (3.13+), and not your OS's default Python. MediaPipe support lags behind bleeding-edge Python versions, and this was the tested, working combination.

### 2 — Clone the repo

```bash
git clone https://github.com/AditA1104/AI-Arcade.git
cd AI-Arcade
```

### 3 — Create & activate a virtual environment

<details>
<summary><b>macOS</b></summary>

```bash
python3.11 -m venv venv
source venv/bin/activate
```
</details>

<details>
<summary><b>Windows</b></summary>

```bash
python -m venv venv
venv\Scripts\activate
```
</details>

You'll know it worked when your terminal prompt shows `(venv)`.

### 4 — Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Don't run `pip install mediapipe` on its own.** MediaPipe's `1.0.x` release removed the legacy `mp.solutions` API this project relies on. `requirements.txt` pins the last stable version that still supports it — always install from the file.

---

## 🧪 Testing the Vision Module Standalone

```bash
python vision.py
```

This runs:

1. **Warmup** (2s) — lets the tracker lock onto you
2. **Calibration** (7s) — wave your hand around your full intended play area
3. **Live tracking** — prints `Player pos: x=, y=` continuously until `Ctrl+C`

> 🎯 Calibration is **per-person, per-camera** — every player (and every laptop) should run it fresh, not reuse someone else's saved range.

---

## 🔌 Using It In the Game

```python
from input import init_tracker, get_player_position, shutdown_tracker

init_tracker()          # once at startup — blocks ~7s for warmup + calibration

# every frame in the game loop:
x, y = get_player_position()   # (int, int), already mapped to 1280×720, non-blocking

# on exit:
shutdown_tracker()
```

`input.py` is the integration boundary — `main.py` never imports `vision.py` directly. It currently wires straight through to live pose tracking, but the file also has a commented-out mouse-control fallback for quick local testing without a camera; swap the import block if you need it.

---

## 📝 Platform Notes

- **macOS** — OpenCV's GUI calls (`imshow`/`waitKey`) only run safely on the main thread. The calibration window closes intentionally before background tracking begins — this is expected, not a bug.
- **Windows** — No equivalent restriction, but the module behaves identically either way.
- **Webcam resolution** — varies by device; calibration reads actual camera dimensions live rather than assuming a fixed size.

---

## ⚡ Performance

Runs smoothly at **30+ FPS** on a MacBook Air M4, CPU-only. MediaPipe Pose is a lightweight model built for mobile/edge devices — any reasonably modern laptop handles it comfortably, no dedicated GPU needed.

---

## 👥 Team

| Role | Owner | Scope |
|---|---|---|
| 👁️ Vision & Integration | **Adit** | Camera pipeline, MediaPipe, calibration, smoothing, threading |
| 🕹️ Game & UI | **Srujan** | Pygame mechanics, game states, leaderboard, booth UX flow |

---

## 📄 License

The source code in this repository is licensed under the [MIT License](LICENSE) — free to use, fork, and modify.

The fruit sprite images in `fruit_assets/` were sourced during development; their original license hasn't been independently verified. Confirm provenance before redistributing this project widely.

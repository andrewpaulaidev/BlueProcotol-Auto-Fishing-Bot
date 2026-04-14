# Blue Protocol: Star Resonance — Auto Fishing Bot

A Python bot that automates the fishing minigame using OpenCV template matching and Win32 API input simulation. Supports **1920×1080**, **2560×1440**, and **3840×2160** in fullscreen or borderless window mode.

> **Disclaimer:** This project is for educational purposes only. Using automation tools may violate the game's Terms of Service and could result in a ban. Use at your own risk.

## Features

- **Auto-Cast** — Casts the fishing line automatically at a configurable point
- **Bite Detection** — Detects the exclamation mark template and hooks the fish instantly
- **Tension Control** — Monitors the tension bar color and holds/releases the mouse to avoid snapping the line
- **Directional Control** — Detects left/right arrow prompts and presses `A`/`D` to follow the fish
- **Bite Timeout** — Re-casts automatically if no fish bites within a configurable time limit
- **Auto Rod Re-buy** — Detects an empty rod slot and buys a new rod before re-casting
- **Auto-Restart** — Closes the results screen and begins casting again after catching a fish
- **Multi-Resolution** — Scales all coordinates automatically for 1920×1080, 2560×1440, and 3840×2160

## Requirements

- Python 3.x
- Packages from `requirements.txt`:
  - `numpy`
  - `opencv-python`
  - `pywin32`
- An `assets/` folder with the following template images (crop from your own game screenshots):
  - `exclamation_mark.png`
  - `arrow_left.png`
  - `arrow_right.png`
  - `end.png` — the Fish Caught / results screen UI
  - `fishing_rod_empty.png` — the empty rod slot icon

## Setup

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Configure `config.ini`

| Setting | Options | Default | Description |
|---|---|---|---|
| `resolution` | `1080` · `2k` · `4k` | `1080` | Your monitor resolution (`1080` = 1920×1080, `2k` = 2560×1440, `4k` = 3840×2160) |
| `bite_timeout` | any number (seconds) | `30` | Seconds to wait for a bite before re-casting |
| `cooldown_seconds` | any number (seconds) | `1.5` | Minimum delay between `A`/`D` presses during the fish fight |

Example `config.ini`:
```ini
[Settings]
resolution       = 1080
bite_timeout     = 30
cooldown_seconds = 1.5
```

### 3. Run the bot

Open your game and go to your fishing spot, then run:
```
python main.py
```

You have **5 seconds** to switch to the game window before the bot starts.

### 4. Stop the bot

Switch back to the terminal and press `Ctrl+C`. All inputs are released cleanly on exit.

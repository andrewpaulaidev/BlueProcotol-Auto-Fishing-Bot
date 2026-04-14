# =============================================================================
#  Blue Protocol: Star Resonance — Auto Fishing Bot
#  Author  : Andrew
#  Version : 2.0
#
#  Description:
#    Automates the fishing minigame using OpenCV template matching and
#    Win32 API input simulation. Supports 1920x1080, 2560x1440, and 3840x2160 resolutions.
#
#  Usage:
#    1. Set your resolution in config.ini
#    2. Run:  python main.py
#    3. Switch to the game window within 5 seconds
#    4. Press Ctrl+C to stop at any time
#
#  Features:
#    - Auto-cast with configurable cast point
#    - Bite detection via exclamation mark template
#    - Fish fighting: tension bar control + directional (A/D) input
#    - Auto rod re-buy when rod durability runs out
#    - Auto-exit minigame UI and re-cast on fish caught
#    - Bite timeout: re-casts if no fish bites within N seconds
#    - Multi-resolution: 1920x1080 / 2560x1440 / 3840x2160 (set in config.ini)
# =============================================================================

import time
import sys
import configparser
import logging
import os
from datetime import datetime

import cv2
from win32api import SetCursorPos

from vision import capture_screen, find_template, check_color_in_region
from controls import hold_left_click, release_left_click, hold_key, release_key, click


# =============================================================================
#  RESOLUTION PROFILES
#  All base coordinates are defined for 1920x1080.
#  Scale factors are computed automatically from your chosen resolution.
# =============================================================================

RESOLUTION_PROFILES = {
    "1080": {"width": 1920, "height": 1080, "label": "1920 x 1080"},
    "2k":   {"width": 2560, "height": 1440, "label": "2560 x 1440"},
    "4k":   {"width": 3840, "height": 2160, "label": "3840 x 2160"},
}

_BASE_W = 1920
_BASE_H = 1080

# Base screen coordinates (tuned for 1920x1080 fullscreen / borderless)
_BASE_COORDS = {
    # Absolute screen regions  (x, y, width, height)
    "FISHING_MONITOR_REGION": (640,  270, 700, 762),
    "FISHING_ROD_REGION":     (1000, 800, 1040, 338),  # 1100-762 = 338

    # Absolute screen points   (x, y)
    "CAST_POINT":             (960,  600),
    "EXIT_POINT":             (1595, 982),
    "FISHING_ROD_BUY":        (1711, 598),

    # Relative regions inside the FISHING_MONITOR_REGION capture
    # (x, y, width, height) — origin is top-left of the capture
    "TENSION_BAR_REGION":     (120, 627, 4,   4),
    "ARROW_REGION":           (100, 187, 440, 148),
}

# Tension bar colors (BGR) — independent of resolution
_TENSION_RED   = (9,   11,  199)
_TENSION_WHITE = (254, 254, 255)


def _scale_point(pt, sx, sy):
    """Scale an (x, y) point by the given factors."""
    return (int(pt[0] * sx), int(pt[1] * sy))


def _scale_region(r, sx, sy):
    """Scale an (x, y, w, h) region by the given factors."""
    return (int(r[0] * sx), int(r[1] * sy), int(r[2] * sx), int(r[3] * sy))


def _build_coords(sx, sy):
    """Return a dict of all coordinates scaled to the target resolution."""
    b = _BASE_COORDS
    return {
        "FISHING_MONITOR_REGION": _scale_region(b["FISHING_MONITOR_REGION"], sx, sy),
        "FISHING_ROD_REGION":     _scale_region(b["FISHING_ROD_REGION"],     sx, sy),
        "CAST_POINT":             _scale_point (b["CAST_POINT"],             sx, sy),
        "EXIT_POINT":             _scale_point (b["EXIT_POINT"],             sx, sy),
        "FISHING_ROD_BUY":        _scale_point (b["FISHING_ROD_BUY"],        sx, sy),
        # Relative regions (within the capture) also need scaling
        "TENSION_BAR_REGION":     _scale_region(b["TENSION_BAR_REGION"],     sx, sy),
        "ARROW_REGION":           _scale_region(b["ARROW_REGION"],           sx, sy),
    }


# =============================================================================
#  LOGGING SETUP
# =============================================================================

class _Tee:
    """Mirrors every write() to both the real stdout and a log file."""
    def __init__(self, log_path: str):
        self._stdout = sys.stdout
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._file   = open(log_path, "w", encoding="utf-8", buffering=1)
        sys.stdout   = self

    def write(self, data):
        self._stdout.write(data)
        self._file.write(data)

    def flush(self):
        self._stdout.flush()
        self._file.flush()

    def close(self):
        sys.stdout = self._stdout
        self._file.close()
        print(f"[LOG] Session log saved to: {self._file.name}")


def setup_logging() -> _Tee:
    """Creates logs/ directory and opens a timestamped log file."""
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(os.path.dirname(__file__), "logs", f"session_{ts}.log")
    return _Tee(log_path)


# =============================================================================
#  CONFIG LOADER
# =============================================================================

def load_config():
    """
    Reads config.ini and returns (resolution_key, bite_timeout, cooldown).

    Keys in config.ini  [Settings] section:
      resolution      = 1080 | 2k | 4k      (default: 1080)
      bite_timeout    = <seconds>            (default: 30)
      cooldown_seconds= <seconds>            (default: 1.5)
    """
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    s = cfg["Settings"] if "Settings" in cfg else {}

    resolution   = s.get("resolution",       "1080").lower().strip()
    bite_timeout = float(s.get("bite_timeout",    "30"))
    cooldown     = float(s.get("cooldown_seconds", "1.5"))

    return resolution, bite_timeout, cooldown


# =============================================================================
#  MAIN BOT
# =============================================================================

def main():
    # -------------------------------------------------------------------------
    # 0. Start logging — mirrors all print() to logs/session_*.log
    # -------------------------------------------------------------------------
    tee = setup_logging()

    # -------------------------------------------------------------------------
    # 1. Load and validate config
    # -------------------------------------------------------------------------
    resolution_key, BITE_TIMEOUT, COOLDOWN = load_config()

    if resolution_key not in RESOLUTION_PROFILES:
        print(f"[ERROR] Unknown resolution '{resolution_key}' in config.ini.")
        print(f"        Valid options: {', '.join(RESOLUTION_PROFILES.keys())}")
        sys.exit(1)

    profile = RESOLUTION_PROFILES[resolution_key]
    sx = int(profile["width"])  / _BASE_W
    sy = int(profile["height"]) / _BASE_H
    C  = _build_coords(sx, sy)

    # -------------------------------------------------------------------------
    # 2. Startup banner
    # -------------------------------------------------------------------------
    print("=" * 55)
    print("  Blue Protocol: Star Resonance — Auto Fishing Bot")
    print("  by Andrew  |  v2.0")
    print("=" * 55)
    print(f"  Resolution   : {profile['label']}")
    print(f"  Bite Timeout : {int(BITE_TIMEOUT)}s")
    print(f"  Cooldown     : {COOLDOWN}s")
    print("=" * 55)
    print("Starting in 5 seconds... Switch to the game window!")
    time.sleep(5)
    print("Bot is active. Press Ctrl+C to stop.\n")

    # -------------------------------------------------------------------------
    # 3. State machine
    # -------------------------------------------------------------------------
    state         = "CASTING"
    is_mouse_held = False
    last_release  = 0.0
    last_action   = 0.0
    wait_start    = 0.0
    last_arrow    = 0        # 0 = none, 1 = left, 2 = right

    try:
        while True:

            # =================================================================
            # STATE: CASTING
            # =================================================================
            if state == "CASTING":
                print("[CAST] Swapping / rebuying fishing rod...")
                time.sleep(1.0)

                # Open map / shop shortcut and buy a rod
                hold_key('m');  time.sleep(0.1);  release_key('m')
                time.sleep(0.5)
                click(*C["FISHING_ROD_BUY"])
                click(*C["FISHING_ROD_BUY"])
                time.sleep(0.5)

                # Release any lingering inputs before casting
                release_left_click()
                release_key('a')
                release_key('d')

                # Cast twice (game sometimes needs a double-click to confirm)
                print("[CAST] Casting line...")
                for _ in range(2):
                    SetCursorPos(C["CAST_POINT"])
                    time.sleep(0.1)
                    hold_left_click()
                    time.sleep(0.1)
                    release_left_click()

                print(f"[CAST] Line cast. Waiting up to {int(BITE_TIMEOUT)}s for a bite...")
                state      = "WAITING_FOR_BITE"
                wait_start = time.time()
                last_arrow = 0
                time.sleep(1.0)

            # =================================================================
            # STATE: WAITING FOR BITE
            # =================================================================
            elif state == "WAITING_FOR_BITE":
                screen = capture_screen(C["FISHING_MONITOR_REGION"])

                if find_template(screen, "assets/exclamation_mark.png", threshold=0.5):
                    print("[BITE] Fish on! Hooking...")
                    hold_left_click();  time.sleep(0.1);  release_left_click()
                    state         = "FIGHTING_FISH"
                    is_mouse_held = False
                    last_release  = 0.0
                    time.sleep(1.0)

                elif time.time() - wait_start > BITE_TIMEOUT:
                    print(f"[TIMEOUT] No bite in {int(BITE_TIMEOUT)}s — re-casting.")
                    state = "CASTING"

                else:
                    elapsed = int(time.time() - wait_start)
                    print(f"[WAIT] Waiting for bite... ({elapsed}s / {int(BITE_TIMEOUT)}s)")
                    time.sleep(0.5)

            # =================================================================
            # STATE: FIGHTING THE FISH
            # =================================================================
            elif state == "FIGHTING_FISH":
                screen  = capture_screen(C["FISHING_MONITOR_REGION"])
                screen1 = capture_screen(C["FISHING_ROD_REGION"])

                # --- Tension bar control (hold = reel in, release = ease off) ---
                is_red   = check_color_in_region(screen, C["TENSION_BAR_REGION"], _TENSION_RED)
                is_white = check_color_in_region(screen, C["TENSION_BAR_REGION"], _TENSION_WHITE)

                if is_red or is_white:
                    if is_mouse_held:
                        print("[FIGHT] Tension high — releasing mouse.")
                        release_left_click()
                        is_mouse_held = False
                        last_release  = time.time()
                else:
                    if not is_mouse_held and (time.time() - last_release > 2.0):
                        print("[FIGHT] Tension safe — holding mouse.")
                        hold_left_click()
                        is_mouse_held = True

                # --- Directional arrow control (A / D) ---
                ar = C["ARROW_REGION"]
                arrow_roi   = screen[ar[1]:ar[1]+ar[3], ar[0]:ar[0]+ar[2]]
                found_left  = find_template(arrow_roi, "assets/arrow_left.png",  threshold=0.4)
                found_right = find_template(arrow_roi, "assets/arrow_right.png", threshold=0.4)
                now = time.time()

                if found_left:
                    if last_arrow == 2:
                        release_key('a');  release_key('d')
                        last_arrow = 0;    last_action = now
                    elif last_arrow == 0 and now - last_action > COOLDOWN:
                        print("[FIGHT] Fish going left — holding 'a'.")
                        hold_key('a');  release_key('d')
                        last_arrow = 1;  last_action = now

                elif found_right:
                    if last_arrow == 1:
                        release_key('a');  release_key('d')
                        last_arrow = 0;    last_action = now
                    elif last_arrow == 0 and now - last_action > COOLDOWN:
                        print("[FIGHT] Fish going right — holding 'd'.")
                        hold_key('d');  release_key('a')
                        last_arrow = 2;  last_action = now

                # --- End condition 1: rod ran out of durability ---
                if find_template(screen1, "assets/fishing_rod_empty.png", threshold=0.7):
                    print("[ROD] Rod empty — re-buying and re-casting.")
                    state = "CASTING"
                    cv2.destroyAllWindows()

                # --- End condition 2: minigame over (fish caught) ---
                elif find_template(screen, "assets/end.png", threshold=0.4):
                    print("[DONE] Fish caught! Closing results screen...")
                    time.sleep(1.0)
                    for _ in range(4):
                        click(*C["EXIT_POINT"])
                    print("[DONE] Waiting for idle state...")
                    time.sleep(3.0)
                    state      = "CASTING"
                    last_arrow = 0
                    cv2.destroyAllWindows()

                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user — releasing all inputs.")
        release_left_click()
        release_key('a')
        release_key('d')
        cv2.destroyAllWindows()
        print("[STOP] Clean exit. Goodbye!")
    finally:
        tee.close()


if __name__ == "__main__":
    main()
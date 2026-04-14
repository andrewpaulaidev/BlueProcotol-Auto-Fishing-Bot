# controls.py
import win32api
import win32con
import time
from win32api import SetCursorPos

# --- Key Code Dictionary ---
KEY_MAP = {
    "a": 0x41, # used in left arrow
    "d": 0x44, # used in right arrow
    "m": 0x4D, # used to change fishing rod when its durability ends
}

# --- Mouse Functions ---
def hold_left_click():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)

def release_left_click():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

def click(x, y):
    """
    Moves the mouse to a coordinate and performs a realistic left click.
    """
    print(f"Moving to ({x}, {y}) and clicking.")
    SetCursorPos((x, y))
    # A short pause after moving the mouse can be crucial
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    # A short hold time
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

# --- Keyboard Functions ---
def hold_key(key):
    """Holds down a key. Expects a single character like 'a'."""
    key_code = KEY_MAP.get(key.lower())
    if key_code:
        win32api.keybd_event(key_code, 0, 0, 0)

def release_key(key):
    """Releases a key. Expects a single character like 'a'."""
    key_code = KEY_MAP.get(key.lower())
    if key_code:
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
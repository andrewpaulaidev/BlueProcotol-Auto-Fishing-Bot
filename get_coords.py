import pyautogui
import time
from pynput import mouse

def on_click(x, y, button, pressed):
    """
    This function is called every time a mouse click occurs.
    """
    # We only want to capture the event when the button is pressed, not released.
    # And we only care about the left button.
    if pressed and button == mouse.Button.left:
        rgb_color = pyautogui.pixel(x, y)
        
        print(f"Left-click at (X={x}, Y={y})  |  RGB: {rgb_color}")

print("Listening for mouse clicks... Press Ctrl+C in this terminal to stop.")

try:
    while True:
        # Get and print the current mouse position.
        x, y = pyautogui.position()
        position_str = f"X: {str(x).rjust(4)} Y: {str(y).rjust(4)}"
        print(position_str, end='\r')
        
        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nDone.")
    print("\nListener stopped.")



# vision.py
import numpy as np
import cv2
import win32gui
import win32ui
import win32con
import win32api

def capture_screen(region=None):
    # This function remains the same as before.
    hwin = win32gui.GetDesktopWindow()
    if region:
        x, y, width, height = region
    else:
        width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        x = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        y = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    hwindc = win32gui.GetWindowDC(hwin)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, width, height)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (width, height), srcdc, (x, y), win32con.SRCCOPY)
    signedIntsArray = bmp.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype='uint8')
    img.shape = (height, width, 4)
    srcdc.DeleteDC()
    memdc.DeleteDC()
    win32gui.ReleaseDC(hwin, hwindc)
    win32gui.DeleteObject(bmp.GetHandle())
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def find_template(screen, template_path, threshold=0.8):
    # This function also remains the same.
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template.shape[2] == 4:
        template = template[:,:,:3]
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return max_loc
    return None

def check_color_in_region(screen, region, bgr_color, tolerance=30):
    """
    Checks if a specified color exists within a rectangular region.
    `region` is (x, y, width, height) relative to the screen capture.
    """
    x, y, w, h = region
    # Crop the image to the region of interest
    roi = screen[y:y+h, x:x+w]

    # Define the lower and upper bounds for the color
    lower_bound = np.array([max(0, c - tolerance) for c in bgr_color])
    upper_bound = np.array([min(255, c + tolerance) for c in bgr_color])

    # Create a mask. Pixels within the color range will be white.
    mask = cv2.inRange(roi, lower_bound, upper_bound)

    # If there are any white pixels in the mask, the color is present
    return np.any(mask)
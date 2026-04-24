import pyautogui
import time

print("Press Ctrl+C to stop...")

try:
    while True:
        # Get the current mouse coordinates
        x, y = pyautogui.position()
        
        # Get the RGB color of the pixel at x, y
        # .pixel() returns a tuple like (R, G, B)
        rgb = pyautogui.pixel(x, y)
        
        print(f"Mouse position: X={x}, Y={y} | RGB: {rgb}")
        
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopped.")
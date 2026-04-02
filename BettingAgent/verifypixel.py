import pyautogui
import time

print("Press Ctrl+C to stop...")

try:
    while True:
        x, y = pyautogui.position()
        print(f"Mouse position: X={x}, Y={y}")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nStopped.")
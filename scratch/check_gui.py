import pyautogui
import time

print("Checking mouse position and screen size...")
print(f"Screen size: {pyautogui.size()}")
print(f"Current mouse position: {pyautogui.position()}")

# Try to move mouse slightly to see if it works
try:
    pyautogui.moveRel(10, 10, duration=0.2)
    print("Mouse moved successfully.")
    pyautogui.moveRel(-10, -10, duration=0.2)
except Exception as e:
    print(f"Mouse move failed: {e}")

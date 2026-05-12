"""
set_bet.py — Changes the bet amount at two on-screen input locations.

Usage (called from new8.py):
    from set_bet import set_bet_amount
    set_bet_amount(0.6)
"""

import pyautogui
import time


def set_bet_amount(amount: float):
    """
    Sets the bet amount at both on-screen bet input fields.

    Location 1: click 698,439 → backspace ×4 → type amount → confirm at 707,391
    Location 2: click 705,665 → backspace ×4 → type amount → confirm at 715,617

    :param amount: The bet value to type (e.g. 0.2, 0.6, 1.2)
    """
    amount_str = str(amount)

    def _set_field(input_x, input_y, confirm_x, confirm_y, label):
        try:
            print(f"[{label}] Clicking input field at ({input_x}, {input_y})...", flush=True)
            pyautogui.click(input_x, input_y)
            time.sleep(0.3)

            # Clear existing value with 4 backspaces
            for _ in range(4):
                pyautogui.press('backspace')
                time.sleep(0.1)

            # Type the new amount
            pyautogui.typewrite(amount_str, interval=0.1)
            time.sleep(0.2)

            # Confirm
            print(f"[{label}] Confirming at ({confirm_x}, {confirm_y})...", flush=True)
            pyautogui.click(confirm_x, confirm_y)
            time.sleep(0.3)

            print(f"[{label}] Bet amount set to {amount_str}", flush=True)
        except Exception as e:
            print(f"[{label}] set_bet_amount error: {e}", flush=True)

    # --- Field 1 ---
    _set_field(698, 439, 707, 391, "Field-1")

    # Short pause between the two fields
    time.sleep(0.4)

    # --- Field 2 ---
    _set_field(705, 665, 715, 617, "Field-2")

    print(f"Bet amount updated to {amount_str} on both fields.", flush=True)


if __name__ == "__main__":
    # Quick test — call with a sample value
    import sys
    val = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
    set_bet_amount(val)

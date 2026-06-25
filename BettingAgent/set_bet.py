"""
set_bet.py — Changes the bet amount at two on-screen input locations.

Usage (called from new8.py or realtime_predictor.py):
    from set_bet import set_bet_amount
    set_bet_amount(0.2)   # base bet
    set_bet_amount(0.4)   # doubled after loss
"""

import time

def set_bet_amount(amount: float):
    """
    Sets the bet amount at both on-screen bet input fields.
    Currently disabled via user request to avoid pyautogui.
    """
    print(f"[set_bet] (DISABLED) Would have set bet amount to {amount}...", flush=True)

if __name__ == "__main__":
    import sys
    val = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
    set_bet_amount(val)

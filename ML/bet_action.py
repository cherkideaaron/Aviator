"""
bet_action.py
─────────────────────────────────────────────────────────────────────
Handles the physical bet click (pyautogui) and Martingale state
when realtime_predictor.py decides to bet.

Bet amounts (real / platform):
  Sequence:  1  →  2  →  4  →  8  →  (cap)
  Reset to 1 on any WIN.

Simulated equivalent (for reporting only — 1/5 scale):
  Sequence:  0.2  →  0.4  →  0.8  →  1.6  →  (cap)

Both real and simulated balance are tracked with min/max.
State persists in  ML/ml_bet_state.json.
─────────────────────────────────────────────────────────────────────
"""

import os
import json
import threading
import pyautogui

# ── Pixel coordinates ─────────────────────────────────────────────
# Two bet-button positions; alternate each click (same toggle as new8.py)
BET_POINTS = [(862, 680), (869, 447)]

# ── Martingale sequence (real amounts) ────────────────────────────
BASE_BET      = 1.0
MAX_BET       = 16.0                   # cap — stays here until WIN
SCALE_FACTOR  = 5.0                    # real / SCALE_FACTOR = simulated

# ── State file ────────────────────────────────────────────────────
_HERE          = os.path.dirname(os.path.abspath(__file__))
BET_STATE_FILE = os.path.join(_HERE, 'ml_bet_state.json')

# ── Import set_bet from BettingAgent ─────────────────────────────
import sys
_BETTING_AGENT = os.path.join(os.path.dirname(_HERE), 'BettingAgent')
if _BETTING_AGENT not in sys.path:
    sys.path.insert(0, _BETTING_AGENT)

from set_bet import set_bet_amount   # noqa: E402


# ─────────────────────────────────────────────────────────────────
class BetAction:
    """Manages pyautogui click + full Martingale + dual balance tracking."""

    def __init__(self, initial_real_balance: float = 0.0):
        """
        :param initial_real_balance: Starting real balance (net P&L starts at 0
               unless you pass your actual account balance here).
        """
        self._lock        = threading.Lock()
        self._toggle      = 0
        self._current_bet = BASE_BET
        self._loss_streak = 0          # how many consecutive losses

        # Balance tracking (real)
        self._real_balance = initial_real_balance
        self._real_min     = initial_real_balance
        self._real_max     = initial_real_balance

        # Balance tracking (simulated = real / SCALE_FACTOR)
        self._sim_balance  = initial_real_balance / SCALE_FACTOR
        self._sim_min      = self._sim_balance
        self._sim_max      = self._sim_balance

        self._load_state(initial_real_balance)

    # ── Persistence ──────────────────────────────────────────────

    def _load_state(self, initial_real_balance: float):
        if os.path.exists(BET_STATE_FILE):
            try:
                with open(BET_STATE_FILE, 'r') as f:
                    d = json.load(f)
                self._toggle       = int(d.get('toggle',        0)) % len(BET_POINTS)
                self._current_bet  = float(d.get('current_bet', BASE_BET))
                self._loss_streak  = int(d.get('loss_streak',   0))
                self._real_balance = float(d.get('real_balance', initial_real_balance))
                self._real_min     = float(d.get('real_min',    self._real_balance))
                self._real_max     = float(d.get('real_max',    self._real_balance))
                self._sim_balance  = float(d.get('sim_balance', self._real_balance / SCALE_FACTOR))
                self._sim_min      = float(d.get('sim_min',     self._sim_balance))
                self._sim_max      = float(d.get('sim_max',     self._sim_balance))

                # ── Safety clamp: old state files may have 0.2 from previous version ──
                if self._current_bet < BASE_BET:
                    print(
                        f"[BetAction] ⚠️  Saved bet ({self._current_bet}) is below platform minimum "
                        f"({BASE_BET}) — resetting to {BASE_BET}.",
                        flush=True
                    )
                    self._current_bet = BASE_BET
                    self._loss_streak = 0

                print(
                    f"[BetAction] State loaded → bet={self._current_bet} | "
                    f"losses={self._loss_streak} | "
                    f"real={self._real_balance:+.2f} (min={self._real_min:.2f} max={self._real_max:.2f}) | "
                    f"sim={self._sim_balance:+.4f} (min={self._sim_min:.4f} max={self._sim_max:.4f})",
                    flush=True
                )
            except Exception as e:
                print(f"[BetAction] Could not load state: {e}", flush=True)
        else:
            print(f"[BetAction] No saved state — starting fresh (bet={BASE_BET})", flush=True)

    def _save_state(self):
        try:
            with open(BET_STATE_FILE, 'w') as f:
                json.dump({
                    'toggle':       self._toggle,
                    'current_bet':  self._current_bet,
                    'loss_streak':  self._loss_streak,
                    'real_balance': self._real_balance,
                    'real_min':     self._real_min,
                    'real_max':     self._real_max,
                    'sim_balance':  self._sim_balance,
                    'sim_min':      self._sim_min,
                    'sim_max':      self._sim_max,
                }, f, indent=2)
        except Exception as e:
            print(f"[BetAction] Could not save state: {e}", flush=True)

    # ── Public properties ────────────────────────────────────────

    @property
    def current_bet(self) -> float:
        return self._current_bet

    @property
    def current_sim_bet(self) -> float:
        """Simulated equivalent bet (real / SCALE_FACTOR)."""
        return round(self._current_bet / SCALE_FACTOR, 4)

    # ── Place bet click ──────────────────────────────────────────

    def place_bet(self):
        """
        Physically clicks the bet button for the NEXT round.
        Call this when realtime_predictor.py predicts WIN.
        """
        with self._lock:
            point  = BET_POINTS[self._toggle]
            toggle = self._toggle
            bet    = self._current_bet
            sbet   = self.current_sim_bet

        print(
            f"[BetAction] 🖱  Clicking at {point} (toggle={toggle}) | "
            f"Real bet: {bet} | Sim bet: {sbet}",
            flush=True
        )

        def _click(pt):
            try:
                pyautogui.click(pt)
                print(f"[BetAction] ✅ Click at {pt}", flush=True)
            except Exception as e:
                print(f"[BetAction] ❌ Click failed: {e}", flush=True)

        threading.Thread(target=_click, args=(point,), daemon=True).start()

        with self._lock:
            self._toggle = (self._toggle + 1) % len(BET_POINTS)
            self._save_state()

    # ── Record result ────────────────────────────────────────────

    def record_result(self, is_win: bool, odd_threshold: float = 2.0):
        """
        Call after the round result is known.
        Updates balance (real + sim) and adjusts the martingale bet.

        :param is_win:        True if the bet won.
        :param odd_threshold: Cash-out multiplier used (default 2.0x).
                              Win payout = bet * (odd_threshold - 1).
        """
        with self._lock:
            bet      = self._current_bet
            sim_bet  = bet / SCALE_FACTOR
            payout   = round(bet * (odd_threshold - 1), 4)   # net gain on win
            sim_pay  = round(payout / SCALE_FACTOR, 6)

            if is_win:
                # ── WIN ──────────────────────────────────────────
                self._real_balance += payout
                self._sim_balance  += sim_pay
                self._loss_streak   = 0
                next_bet            = BASE_BET   # reset to 1

                label = f"🟢 WIN  +{payout:.2f} real  +{sim_pay:.4f} sim"
            else:
                # ── LOSS ─────────────────────────────────────────
                self._real_balance -= bet
                self._sim_balance  -= sim_bet
                self._loss_streak  += 1
                # Double up, cap at MAX_BET
                next_bet = min(bet * 2, MAX_BET)

                label = f"🔴 LOSS -{bet:.2f} real  -{sim_bet:.4f} sim"

            # Update min / max
            self._real_min = min(self._real_min, self._real_balance)
            self._real_max = max(self._real_max, self._real_balance)
            self._sim_min  = min(self._sim_min,  self._sim_balance)
            self._sim_max  = max(self._sim_max,  self._sim_balance)

            self._current_bet = next_bet
            self._save_state()

            real_b   = self._real_balance
            real_mn  = self._real_min
            real_mx  = self._real_max
            sim_b    = self._sim_balance
            sim_mn   = self._sim_min
            sim_mx   = self._sim_max
            losses   = self._loss_streak
            n_bet    = self._current_bet
            n_sbet   = self.current_sim_bet

        # Print dual-balance report
        print(
            f"\n{'─'*60}\n"
            f"  {label}  (loss streak: {losses})\n"
            f"\n"
            f"  📊 REAL BALANCE   : {real_b:+.2f}   "
            f"(min: {real_mn:.2f}  max: {real_mx:.2f})\n"
            f"  📊 SIM  BALANCE   : {sim_b:+.4f}   "
            f"(min: {sim_mn:.4f}  max: {sim_mx:.4f})\n"
            f"\n"
            f"  ➡️  Next bet       : {n_bet} real  /  {n_sbet} sim\n"
            f"{'─'*60}",
            flush=True
        )

        # Apply the new bet amount to the UI in the background
        def _set():
            try:
                set_bet_amount(n_bet)
            except Exception as e:
                print(f"[BetAction] set_bet_amount error: {e}", flush=True)

        threading.Thread(target=_set, daemon=True).start()

"""
analyze_predictions.py
======================
Analyzes a win_predictions_detail.txt file and prints:
  - Total Actual wins / losses
  - Highest consecutive actual losses
  - Total Actual 1.5 wins / losses
  - Highest consecutive actual 1.5 losses

Usage:
  python analyze_predictions.py                          <- uses win_predictions_detail.txt in same folder
  python analyze_predictions.py my_other_file.txt        <- specify a different file
"""

import sys
import re
import os

# ── File to analyze ─────────────────────────────────────────────────────────
if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = os.path.join(os.path.dirname(__file__), "win_predictions_detail.txt")

if not os.path.exists(file_path):
    print(f"[!] File not found: {file_path}")
    sys.exit(1)

print(f"\n[+] Analyzing: {file_path}\n")

# ── Counters ─────────────────────────────────────────────────────────────────
actual_wins   = 0
actual_losses = 0
max_consec_actual_loss = 0
cur_consec_actual_loss = 0

actual_15_wins   = 0
actual_15_losses = 0
max_consec_15_loss = 0
cur_consec_15_loss = 0

total_lines = 0

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        total_lines += 1

        # ── Actual (2x threshold) ────────────────────────────────────────────
        actual_match = re.search(r"Actual:\s*(\w+)", line)
        if actual_match:
            val = actual_match.group(1).lower()
            if val == "win":
                actual_wins += 1
                cur_consec_actual_loss = 0
            elif val == "loss":
                actual_losses += 1
                cur_consec_actual_loss += 1
                max_consec_actual_loss = max(max_consec_actual_loss, cur_consec_actual_loss)

        # ── Actual 1.5x threshold ────────────────────────────────────────────
        actual_15_match = re.search(r"Actual 1\.5:\s*(\w+)", line)
        if actual_15_match:
            val15 = actual_15_match.group(1).lower()
            if val15 == "win":
                actual_15_wins += 1
                cur_consec_15_loss = 0
            elif val15 in ["loss", "lose"]:
                actual_15_losses += 1
                cur_consec_15_loss += 1
                max_consec_15_loss = max(max_consec_15_loss, cur_consec_15_loss)

# ── Results ──────────────────────────────────────────────────────────────────
total_actual  = actual_wins + actual_losses
total_15      = actual_15_wins + actual_15_losses

win_rate      = actual_wins / total_actual * 100   if total_actual  > 0 else 0
win_rate_15   = actual_15_wins / total_15 * 100    if total_15      > 0 else 0

print("=" * 45)
print("  ACTUAL (2x threshold) Statistics")
print("=" * 45)
print(f"  [+] Wins              : {actual_wins}")
print(f"  [-] Losses            : {actual_losses}")
print(f"  [*] Total             : {total_actual}")
print(f"  [%] Win Rate          : {win_rate:.1f}%")
print(f"  [!] Highest Consec.   : {max_consec_actual_loss} losses in a row")
print()
print("=" * 45)
print("  ACTUAL 1.5x Statistics")
print("=" * 45)
print(f"  [+] Wins              : {actual_15_wins}")
print(f"  [-] Losses            : {actual_15_losses}")
print(f"  [*] Total             : {total_15}")
print(f"  [%] Win Rate          : {win_rate_15:.1f}%")
print(f"  [!] Highest Consec.   : {max_consec_15_loss} losses in a row")
print()

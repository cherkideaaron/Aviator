from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import mysql.connector
import threading
import time
import random
import pyautogui
import sys
import os
import subprocess
import json
from set_bet import set_bet_amount

round_counter = 0

app = Flask(__name__)
CORS(app)

# --- SUPPRESS FLASK LOGS ---
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
# ---------------------------

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',         # Replace with your MySQL username
    'password': 'Et3aa@123', # Replace with your MySQL password
    'database': 'aviator_db'
}

# --- MISSING CONSTANTS ---
WATCH_PATTERNS = [[0, 1, 0], [0, 1, 1]] 
PATTERN_EVENTS_FILE_121 = 'pattern_events.txt'
PATTERN_EVENTS_FILE_134 = 'pattern_events2.txt'
PATTERN_EVENTS_FILE_151 = 'pattern_events3.txt'
# -------------------------

# --- NEW: BETTING & IDLE STATE ---
BET_POINTS = [(862, 680), (869, 447)]
bet_click_toggle = 0
last_bet_click_time = time.time()
# ---------------------------------

# --- BET SIZING STATE ---
# Sequence: 0.2 → 0.6 → 1.8 (CAP) → Keep at 1.8 until recovery complete
BASE_BET = 0.2
MAX_RECOVERY_BET = 1.8
BET_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bet_state.json')

def load_bet_state():
    """Load persisted bet state from disk so restarts remember the streak."""
    if os.path.exists(BET_STATE_FILE):
        try:
            with open(BET_STATE_FILE, 'r') as _f:
                _d = json.load(_f)
            return (
                _d.get('current_bet', BASE_BET), 
                _d.get('loss_streak', 0), 
                _d.get('max_bet_reached', BASE_BET),
                _d.get('max_balance', 0.0),
                _d.get('consecutive_high_bets', 0)
            )
        except Exception:
            pass
    return BASE_BET, 0, BASE_BET, 0.0, 0

def save_bet_state(cb, ls, mb, mbal, chb):
    """Persist bet state to disk."""
    try:
        with open(BET_STATE_FILE, 'w') as _f:
            json.dump({
                'current_bet': cb, 
                'loss_streak': ls, 
                'max_bet_reached': mb,
                'max_balance': mbal,
                'consecutive_high_bets': chb
            }, _f, indent=2)
    except Exception as _e:
        print(f"⚠️ Could not save bet state: {_e}", flush=True)

# Load state on startup — survives restarts
current_bet, loss_streak, max_bet_reached, max_balance, consecutive_high_bets = load_bet_state()
print(f"💾 Bet state loaded → current_bet={current_bet} | loss_streak={loss_streak} | max_bet_reached={max_bet_reached} | max_balance={max_balance} | streak1.8={consecutive_high_bets}", flush=True)
# -------------------------

# --- IDLE SIMULATION TOGGLE ---
idle_active = True  # Press Q to pause random movement, S to resume
# --------------------------------



@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

def get_category(value):
    """Categorizes the value based on your rules."""
    if value < 2.0:
        return 0
    elif 2.0 <= value < 10.0:
        return 1
    else:
        return 2

#def delayed_click(x, y, delay):
#    """Wait for delay then click at (x, y)."""
#    time.sleep(delay)
#    pyautogui.click(x, y)
#    print(f"🖱️ Delayed click performed at ({x}, {y}) after {delay}s", flush=True)

def restart_program(reason):
    """Restarts the current program, with an optional reason."""
    print(f"\n🔄 RESTARTING: {reason}...", flush=True)
    
    python = sys.executable
    args = sys.argv[:]
    if "--no-truncate" not in args:
        args.append("--no-truncate")
        
    # Use background command to wait 2 seconds before launching new instance
    # This allows the current process to fully exit and free up resources
    cmd_args = [f'"{a}"' for a in args]
    cmd = f'timeout /t 2 /nobreak && "{python}" ' + " ".join(cmd_args)
    
    print(f"👋 Closing current process. New instance will start in 2s...", flush=True)
    subprocess.Popen(f'start /b cmd /c "{cmd}"', shell=True)
    sys.exit(0)

def delayed_restart(delay=5):
    """Wait and then trigger the program restart."""
    print(f"⏳ Click detected! Waiting {delay}s for round completion...", flush=True)
    time.sleep(delay)
    restart_program("Click/Bet placed")

# ─────────────────────────────────────────────────────────────
# NEW: Grid data endpoint for the /more frontend page
# Returns every category ever recorded (from all_games) in order
# ─────────────────────────────────────────────────────────────
@app.route('/grid-data', methods=['GET'])
def get_grid_data():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT category FROM all_games ORDER BY id ASC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({
            "status": "success",
            "categories": [r[0] for r in rows],
            "total": len(rows)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/analysis-data', methods=['GET'])
def get_analysis_data():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all CURRENT SESSION games (game_data reset on startup)
        cursor.execute("SELECT id, timestamp, raw_value FROM game_data ORDER BY id ASC")
        rows = cursor.fetchall()
        
        # Fetch current session timeline (last 400 of the current session)
        cursor.execute("SELECT id, timestamp, raw_value FROM game_data ORDER BY id DESC LIMIT 400")
        recent_rows = cursor.fetchall()
        recent_rows.reverse() # Back to chronological order
        
        cursor.close()
        conn.close()
        
        def calculate_gaps(threshold):
            gaps = []
            last_id = None
            last_time = None
            
            for row in rows:
                if row['raw_value'] < threshold:
                    if last_id is not None:
                        gap_rounds = row['id'] - last_id
                        gap_seconds = (row['timestamp'] - last_time).total_seconds()
                        gaps.append({
                            "id": row['id'],
                            "timestamp": row['timestamp'].isoformat(),
                            "gap_rounds": int(gap_rounds),
                            "gap_seconds": int(gap_seconds)
                        })
                    last_id = row['id']
                    last_time = row['timestamp']
            return gaps

        def get_timeline(threshold):
            return [
                {
                    "rounds_ago": len(recent_rows) - i - 1,
                    "time": r['timestamp'].strftime('%H:%M:%S'),
                    "hit": 1 if r['raw_value'] < threshold else 0,
                    "value": float(r['raw_value'])
                } for i, r in enumerate(recent_rows)
            ]

        return jsonify({
            "status": "success",
            "threshold_111": calculate_gaps(1.11),
            "threshold_121": calculate_gaps(1.21),
            "threshold_151": calculate_gaps(1.51),
            "timeline_111": get_timeline(1.11),
            "timeline_121": get_timeline(1.21),
            "timeline_151": get_timeline(1.51)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/patterns', methods=['GET'])
def get_top_patterns():
    length = request.args.get('length', type=int)
    
    if not length or length not in [3, 4, 5]:
        return jsonify({"status": "error", "message": "Please provide a length of 3, 4, or 5"}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Fetch patterns of the specified length, sorted by occurrence count
        query = """
            SELECT pattern_string, COUNT(*) as occurrence_count 
            FROM all_patterns 
            WHERE pattern_length = %s
            GROUP BY pattern_string
            ORDER BY occurrence_count DESC
            LIMIT 15
        """
        
        cursor.execute(query, (length,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "length": length,
            "data": results
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/latest', methods=['GET'])
def get_latest_data():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT timestamp, raw_value, category, current_diff, max_diff, pzs_diff, pzs_0012_diff, pzs_12012_diff, pzs_source, good_distance, p3zs_diff FROM game_data ORDER BY id DESC LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({
                "status": "success",
                "data": result
            }), 200
        else:
            return jsonify({"status": "success", "data": None}), 200
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/tracker-data', methods=['GET'])
def get_tracker_data():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM tracker_state WHERE id = 1")
        tracker_state = cursor.fetchone()
        if tracker_state and tracker_state.get('extreme_start_time'):
            tracker_state['extreme_start_time'] = tracker_state['extreme_start_time'].isoformat()
            
        cursor.execute("SELECT max_diff_value, duration_seconds, rounds_count, ended_at FROM extreme_durations ORDER BY id DESC LIMIT 5")
        extreme_durations = cursor.fetchall()
        for row in extreme_durations:
            if row.get('ended_at'):
                row['ended_at'] = row['ended_at'].isoformat()
                
        cursor.execute("SELECT max_difference, time_difference_seconds, rounds_to_converge, recorded_at FROM convergence_history ORDER BY id DESC LIMIT 5")
        convergence_history = cursor.fetchall()
        for row in convergence_history:
            if row.get('recorded_at'):
                row['recorded_at'] = row['recorded_at'].isoformat()
                
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "data": {
                "tracker_state": tracker_state,
                "extreme_durations": extreme_durations,
                "convergence_history": convergence_history
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/probabilities', methods=['GET'])
def get_probabilities():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get the most recent categories from all-time history (all_games)
        cursor.execute("SELECT category FROM all_games ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        recent_cats = [str(row['category']) for row in rows]
        recent_cats.reverse()  # Current order: [oldest, ..., newest]
        
        results = {}
        lengths = [3, 4, 5]
        
        for length in lengths:
            prefix_len = length - 1
            if len(recent_cats) >= prefix_len:
                prefix = "".join(recent_cats[-prefix_len:])
                
                query = """
                    SELECT pattern_string, COUNT(*) as occurrence_count 
                    FROM all_patterns 
                    WHERE pattern_string LIKE %s AND pattern_length = %s
                    GROUP BY pattern_string
                """
                cursor.execute(query, (prefix + '%', length))
                patterns = cursor.fetchall()
                
                counts = {'0': 0, '1': 0, '2': 0}
                total_for_prefix = 0
                
                for p in patterns:
                    next_val = p['pattern_string'][-1]
                    count = p['occurrence_count']
                    if next_val in counts:
                        counts[next_val] += count
                        total_for_prefix += count
                
                good_count = counts['1'] + counts['2']
                prob = (good_count / total_for_prefix * 100) if total_for_prefix > 0 else 0
                
                results[f'pattern_{length}'] = {
                    'prefix': prefix,
                    'counts': counts,
                    'total': total_for_prefix,
                    'good_count': good_count,
                    'probability': round(prob, 2)
                }
            else:
                results[f'pattern_{length}'] = None

        valid_probs = [v['probability'] for v in results.values() if v is not None]
        total_prob = round(sum(valid_probs) / len(valid_probs), 2) if valid_probs else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "data": {
                "probabilities": results,
                "total_probability": total_prob
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/save', methods=['POST', 'OPTIONS'])
def save_data():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        global round_counter
        data = request.json
        multiplier_str = data.get('multiplier', '0')
        balance_val = data.get('balance', '0.00')
        
        print(f"📩 Incoming Request: {multiplier_str} | Balance: {balance_val}", flush=True)
        # 1. Clean data & categorize
        clean_value = float(multiplier_str.replace('x', '').strip())
        category = get_category(clean_value)
        now = datetime.now()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # --- NEW LOGIC: Dual Tracking ---
        import json
        import os
        new_click_target_rounds = None
        PENDING_CLICK_FILE = 'pending_click.json'
        pending_just_fired = False
        
        cursor.execute("SELECT raw_value FROM all_games ORDER BY id DESC LIMIT 6")
        past_6_rows = cursor.fetchall()

        # --- NEW: Target Balance Tracking & Bet Sizing ---
        PENDING_BET_BALANCE_FILE = 'pending_bet_balance.json'
        if os.path.exists(PENDING_BET_BALANCE_FILE):
            try:
                with open(PENDING_BET_BALANCE_FILE, 'r') as f:
                    bet_data = json.load(f)
                
                # Simple cleanup of balance strings for calculation
                def clean_bal(b): return float(str(b).replace('$', '').replace(',', '').replace(' ', '').strip())
                
                before_balance = clean_bal(bet_data.get('before_balance', '0.00'))
                after_balance = clean_bal(balance_val)
                change = round(after_balance - before_balance, 2)
                placed_bet = float(bet_data.get('bet_amount', BASE_BET))
                
                timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
                
                # --- Build density string (always, win or loss) ---
                density_str = ""
                try:
                    TRACKING_FILE_134_DENSITY = 'post_bad_tracking2.txt'
                    if os.path.exists(TRACKING_FILE_134_DENSITY):
                        with open(TRACKING_FILE_134_DENSITY, 'r') as dtf:
                            density_data = json.load(dtf)
                        # Collect all values across all 6 lists, then take last 10
                        all_vals = []
                        for li in range(6):
                            all_vals.extend(density_data.get(str(li), []))
                        last_10 = all_vals[-10:] if len(all_vals) >= 10 else all_vals
                        bad_in_10 = sum(1 for v in last_10 if v == 0)
                        total_in_10 = len(last_10)
                        density_str = f" | density(last10)={bad_in_10}/{total_in_10}"
                except Exception as de:
                    density_str = f" | density=err"
                
                result_line = f"[{timestamp_str}] Before: {before_balance} | After: {after_balance} | Result: {change:+.2f} | odd: {clean_value}x | bet: {placed_bet}{density_str}\n"
                with open('bet_results.txt', 'a') as f:
                    f.write(result_line)
                
                print(f"💰 Bet Outcome Logged: {change:+.2f} (Odd: {clean_value}x | Bet: {placed_bet} | Before: {before_balance} -> After: {after_balance}){density_str}", flush=True)

                # --- BET SIZING LOGIC (HIGH WATER MARK RECOVERY - CAPPED AT 1.8) ---
                global current_bet, loss_streak, max_bet_reached, max_balance, consecutive_high_bets
                
                # 1. Initialize max_balance if this is the first round
                if max_balance == 0.0:
                    max_balance = after_balance
                    print(f"🚩 Initialized max_balance to: {max_balance}", flush=True)

                # 2. Update Max Balance if we hit a new peak
                if after_balance > max_balance:
                    max_balance = after_balance
                    print(f"⭐ New Session High: {max_balance}", flush=True)

                # 3. Check if we have fully recovered
                if after_balance >= (max_balance - 0.005):
                    # We are at or above the peak → Reset to Base
                    if loss_streak > 0:
                        print(f"✅ RECOVERY COMPLETE! Balance {after_balance} >= Max {max_balance}. Resetting bet from {placed_bet} to {BASE_BET} (Streak1.8 was: {consecutive_high_bets})", flush=True)
                    else:
                        print(f"📈 Balance at Peak ({after_balance}). Bet stays at {BASE_BET}", flush=True)
                    
                    loss_streak = 0
                    consecutive_high_bets = 0
                    current_bet = BASE_BET
                    save_bet_state(current_bet, loss_streak, max_bet_reached, max_balance, consecutive_high_bets)
                    threading.Thread(target=set_bet_amount, args=(BASE_BET,), daemon=True).start()
                else:
                    # We are below the peak → Recovery Mode
                    if after_balance < before_balance:
                        # Balance reduced → it was a loss, increment aggression
                        loss_streak += 1
                        # Cap at 1.8
                        next_bet = min(round(placed_bet * 3, 2), MAX_RECOVERY_BET)
                        current_bet = next_bet
                        if next_bet > max_bet_reached:
                            max_bet_reached = next_bet
                        
                        # Tracking streak at 1.8
                        if next_bet >= MAX_RECOVERY_BET:
                            consecutive_high_bets += 1
                        else:
                            consecutive_high_bets = 0
                        
                        save_bet_state(current_bet, loss_streak, max_bet_reached, max_balance, consecutive_high_bets)
                        streak_str = f" | [Streak1.8: {consecutive_high_bets}]" if consecutive_high_bets > 0 else ""
                        print(f"📉 LOSS #{loss_streak} (Below Peak: {after_balance} < {max_balance}) → Bet: {next_bet}{streak_str}", flush=True)
                        threading.Thread(target=set_bet_amount, args=(next_bet,), daemon=True).start()
                    else:
                        # Balance same or increased → Win/Push but still under peak
                        # STAY at the current high bet to continue recovery
                        if placed_bet >= MAX_RECOVERY_BET:
                            consecutive_high_bets += 1
                        
                        current_bet = placed_bet
                        save_bet_state(current_bet, loss_streak, max_bet_reached, max_balance, consecutive_high_bets)
                        streak_str = f" | [Streak1.8: {consecutive_high_bets}]" if consecutive_high_bets > 0 else ""
                        print(f"📈 WIN/PUSH (Still Below Peak: {after_balance} < {max_balance}) → Staying at bet {placed_bet} to recover faster{streak_str}", flush=True)
                        
                        # Ensure the UI reflects this
                        threading.Thread(target=set_bet_amount, args=(placed_bet,), daemon=True).start()
                # ---------------------------------------------------
                # -------------------------

                os.remove(PENDING_BET_BALANCE_FILE)
            except Exception as e:
                print(f"⚠️ Error logging bet result: {e}", flush=True)
        # ------------------------------------

        # =========================================
        # 1. Tracking for 1.21 Threshold (Silent)
        # =========================================
        if len(past_6_rows) >= 1:
            TRACKING_FILE_121 = 'post_bad_tracking.txt'
            if os.path.exists(TRACKING_FILE_121):
                try:
                    with open(TRACKING_FILE_121, 'r') as f:
                        tracking_data_121 = json.load(f)
                except Exception:
                    tracking_data_121 = {str(i): [] for i in range(6)}
            else:
                tracking_data_121 = {str(i): [] for i in range(6)}
                
            is_good_121 = 1 if clean_value >= 1.21 else 0
            
            updated_121 = False
            for idx, row in enumerate(past_6_rows):
                if float(row[0]) < 1.21:
                    tracking_data_121[str(idx)].append(is_good_121)
                    updated_121 = True
                    
            if updated_121:
                with open(TRACKING_FILE_121, 'w') as f:
                    json.dump(tracking_data_121, f)

                pattern_logged_this_round = False
                for list_idx in range(6):
                    if pattern_logged_this_round: break
                    
                    lst = tracking_data_121[str(list_idx)]
                    if len(lst) >= 3:
                        tail = lst[-3:]
                        for wp in WATCH_PATTERNS:
                            if tail == wp:
                                cursor.execute("SELECT raw_value FROM all_games ORDER BY id DESC LIMIT 10")
                                last_10_rows = cursor.fetchall()
                                last_10_vals = [float(r[0]) for r in last_10_rows]
                                bad_count = sum(1 for v in last_10_vals if v < 2.0)
                                total_count = len(last_10_vals)
                                bad_pct = round((bad_count / total_count) * 100, 1) if total_count > 0 else 0.0

                                pattern_str = f"{wp[0]}, {wp[1]}, {wp[2]}"
                                event_time = now.strftime('%Y-%m-%d %H:%M:%S')
                                flag = "  |  [<=40% ZONE]" if bad_pct <= 40.0 else ""
                                log_line = f"{pattern_str}  |  {event_time}  |  bad%={bad_pct}%  |  list={list_idx}  |  CLICKED=IGNORED(1.21){flag}  |  Balance: {balance_val}\n"

                                # Immediate Logging (Commented out in favor of Delayed/Pending logging)
                                # with open(PATTERN_EVENTS_FILE_121, 'a') as pf:
                                #     pf.write(log_line)
                                
                                # --- Store Log for Pending Trigger ---
                                p_data = {}
                                if os.path.exists(PENDING_CLICK_FILE):
                                    try:
                                        with open(PENDING_CLICK_FILE, 'r') as f: p_data = json.load(f)
                                    except: pass
                                if 'pending_logs' not in p_data: p_data['pending_logs'] = []
                                p_data['pending_logs'].append({'file': PATTERN_EVENTS_FILE_121, 'line': log_line, 'threshold': 1.21})
                                with open(PENDING_CLICK_FILE, 'w') as f: json.dump(p_data, f)
                                print(f"📝 Logging Arming (1.21): Pattern {pattern_str} in List {list_idx} wait for < 1.21", flush=True)
                                
                                pattern_logged_this_round = True
                                break # Exit WATCH_PATTERNS loop
        # =========================================
        # 2. Tracking for 1.34 Threshold (Active)
        # =========================================
        if len(past_6_rows) >= 1:
            TRACKING_FILE_134_ACTIVE = 'post_bad_tracking2.txt'
            if os.path.exists(TRACKING_FILE_134_ACTIVE):
                try:
                    with open(TRACKING_FILE_134_ACTIVE, 'r') as f:
                        tracking_data_134_active = json.load(f)
                except Exception:
                    tracking_data_134_active = {str(i): [] for i in range(6)}
            else:
                tracking_data_134_active = {str(i): [] for i in range(6)}
                
            is_good_134_active = 1 if clean_value >= 1.34 else 0
            
            updated_134_active = False
            updated_lists_134_active = []
            for idx, row in enumerate(past_6_rows):
                if float(row[0]) < 1.34:
                    tracking_data_134_active[str(idx)].append(is_good_134_active)
                    updated_134_active = True
                    updated_lists_134_active.append(idx)
                    
            if updated_134_active:
                with open(TRACKING_FILE_134_ACTIVE, 'w') as f:
                    json.dump(tracking_data_134_active, f)

                print("📊 Post-Bad Tracking Updated (1.34):")
                for i in range(6):
                    print(f"   List {i}: {tracking_data_134_active[str(i)]}", flush=True)

                pattern_logged_this_round_134_active = False
                for list_idx in range(6):
                    if pattern_logged_this_round_134_active: break
                    
                    lst = tracking_data_134_active[str(list_idx)]
                    if len(lst) >= 3:
                        tail = lst[-3:]
                        for wp in WATCH_PATTERNS:
                            if tail == wp:
                                cursor.execute("SELECT raw_value FROM all_games ORDER BY id DESC LIMIT 10")
                                last_10_rows = cursor.fetchall()
                                last_10_vals = [float(r[0]) for r in last_10_rows]
                                bad_count = sum(1 for v in last_10_vals if v < 2.0)
                                total_count = len(last_10_vals)
                                bad_pct = round((bad_count / total_count) * 100, 1) if total_count > 0 else 0.0

                                cursor.execute("SELECT MAX(id) FROM game_data")
                                last_id_row = cursor.fetchone()
                                predicted_id = (last_id_row[0] + 1) if last_id_row and last_id_row[0] else 1

                                click_msg = "  |  CLICKED=NO"
                                try:
                                    if os.path.exists('last_click.json'):
                                        with open('last_click.json', 'r') as f:
                                            lc = json.load(f)
                                            if lc.get("click_for_id") == predicted_id:
                                                click_msg = f"  |  CLICKED=YES"
                                except: pass

                                pattern_str = f"{wp[0]}, {wp[1]}, {wp[2]}"
                                event_time = now.strftime('%Y-%m-%d %H:%M:%S')
                                flag = "  |  [<=40% ZONE]" if bad_pct <= 40.0 else ""
                                log_line = f"{pattern_str}  |  {event_time}  |  bad%={bad_pct}%  |  list={list_idx}{click_msg}{flag}  |  Balance: {balance_val}\n"

                                # We will arm the actual log entry inside the "PENDING SET (1.34)" block below to ensure consistency.
                                print(f"🔔 Pattern [{pattern_str}] detected in List {list_idx}! (1.34 Active - Prioritized match)", flush=True)
                                pattern_logged_this_round_134_active = True
                                # Store temp log context for arming block
                                last_pattern_found_134_active = log_line
                                break 

                # --- CLICK SCHEDULE: [0,1] tail ---
                lists_with_01 = [
                    i for i in updated_lists_134_active
                    if len(tracking_data_134_active[str(i)]) >= 2
                    and tracking_data_134_active[str(i)][-2] == 0
                    and tracking_data_134_active[str(i)][-1] == 1
                    and i in [0, 1, 5]  # Prioritized lists
                ]

                if lists_with_01:
                    primary_list = lists_with_01[0]
                    print(f"📌 [0,1] tail in prioritized list {primary_list} → Scheduling click (1.34 threshold)", flush=True)
                    
                    cursor.execute("SELECT MAX(id) FROM game_data")
                    last_id_row = cursor.fetchone()
                    predicted_current_id = (last_id_row[0] + 1) if last_id_row and last_id_row[0] else 1

                    ACTIVE_TARGETS_FILE = 'active_targets.json'
                    active_targets = []
                    if os.path.exists(ACTIVE_TARGETS_FILE):
                        try:
                            with open(ACTIVE_TARGETS_FILE, 'r') as atf:
                                active_targets = json.load(atf)
                        except: pass

                    # --- PENDING SET (1.34) ---
                    if clean_value >= 1.34:
                        p_data = {}
                        if os.path.exists(PENDING_CLICK_FILE):
                            try:
                                with open(PENDING_CLICK_FILE, 'r') as f: p_data = json.load(f)
                            except: pass
                        
                        p_data.update({'targets': lists_with_01, 'lists': lists_with_01, 'threshold': 1.34})
                        if 'pending_logs' not in p_data: p_data['pending_logs'] = []
                        if 'last_pattern_found_134_active' in locals():
                            p_data['pending_logs'].append({'file': PATTERN_EVENTS_FILE_134, 'line': last_pattern_found_134_active, 'threshold': 1.34})

                        with open(PENDING_CLICK_FILE, 'w') as pcf:
                            json.dump(p_data, pcf)
                        print(f"🔔 PENDING SET (1.34): will click {lists_with_01} rounds after next bad result (< 1.34)", flush=True)
                    else:
                        print(f"⏭️ PENDING SKIPPED: current result ({clean_value}) is already bad (< 1.34) — waiting for a good result first", flush=True)
        # =========================================
        # 3. Tracking for 1.51 Threshold (Silent - pending log same as 1.21)
        # =========================================
        if len(past_6_rows) >= 1:
            TRACKING_FILE_151 = 'post_bad_tracking3.txt'
            if os.path.exists(TRACKING_FILE_151):
                try:
                    with open(TRACKING_FILE_151, 'r') as f:
                        tracking_data_151 = json.load(f)
                except Exception:
                    tracking_data_151 = {str(i): [] for i in range(6)}
            else:
                tracking_data_151 = {str(i): [] for i in range(6)}
                
            is_good_151 = 1 if clean_value >= 1.51 else 0
            
            updated_151 = False
            for idx, row in enumerate(past_6_rows):
                if float(row[0]) < 1.51:
                    tracking_data_151[str(idx)].append(is_good_151)
                    updated_151 = True
                    
            if updated_151:
                with open(TRACKING_FILE_151, 'w') as f:
                    json.dump(tracking_data_151, f)
                
                pattern_logged_this_round_151_silent = False
                for list_idx in range(6):
                    if pattern_logged_this_round_151_silent: break
                    
                    lst = tracking_data_151[str(list_idx)]
                    if len(lst) >= 3:
                        tail = lst[-3:]
                        for wp in WATCH_PATTERNS:
                            if tail == wp:
                                cursor.execute("SELECT raw_value FROM all_games ORDER BY id DESC LIMIT 10")
                                last_10_rows = cursor.fetchall()
                                last_10_vals = [float(r[0]) for r in last_10_rows]
                                bad_count = sum(1 for v in last_10_vals if v < 2.0)
                                total_count = len(last_10_vals)
                                bad_pct = round((bad_count / total_count) * 100, 1) if total_count > 0 else 0.0

                                pattern_str = f"{wp[0]}, {wp[1]}, {wp[2]}"
                                event_time = now.strftime('%Y-%m-%d %H:%M:%S')
                                flag = "  |  [<=40% ZONE]" if bad_pct <= 40.0 else ""
                                log_line = f"{pattern_str}  |  {event_time}  |  bad%={bad_pct}%  |  list={list_idx}  |  CLICKED=IGNORED(1.51){flag}  |  Balance: {balance_val}\n"

                                # --- Store Log for Pending Trigger (same as 1.21) ---
                                p_data = {}
                                if os.path.exists(PENDING_CLICK_FILE):
                                    try:
                                        with open(PENDING_CLICK_FILE, 'r') as f: p_data = json.load(f)
                                    except: pass
                                if 'pending_logs' not in p_data: p_data['pending_logs'] = []
                                p_data['pending_logs'].append({'file': PATTERN_EVENTS_FILE_151, 'line': log_line, 'threshold': 1.51})
                                with open(PENDING_CLICK_FILE, 'w') as f: json.dump(p_data, f)
                                print(f"📝 Logging Arming (1.51 Silent): Pattern {pattern_str} in List {list_idx} — wait for < 1.51", flush=True)

                                pattern_logged_this_round_151_silent = True
                                break
        # --------------------------------------------------------

        
        # --- CALCULATE TRACKER STATE ---
        cursor.execute("SELECT status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count, click_delay_target, click_delay_count, gap_last_hit_id, gap_measured_value, gap_click_target_id, gap_hist_1, gap_hist_2, gap_hist_3 FROM tracker_state WHERE id = 1")
        state_row = cursor.fetchone()
        
        round_val = 1 if category in [1, 2] else -1
        save_current_diff = 0
        save_max_diff = 0
        save_pzs_diff = 0
        save_pzs_0012_diff = 0
        save_pzs_12012_diff = 0
        save_pzs_source = None
        save_good_distance = None
        save_p3zs_diff = 0
        
        if state_row:
            status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count, click_delay_target, click_delay_count, gap_last_hit_id, gap_measured_value, gap_click_target_id, gap_hist_1, gap_hist_2, gap_hist_3 = state_row
            
            # --- START TRACKING ROUND ---
            # Pre-insert into game_data to get the current round ID
            mock_diff = 0 # Temporarily placeholder as it's computed below
            insert_query = "INSERT INTO game_data (timestamp, raw_value, category, current_diff, max_diff, pzs_diff, pzs_0012_diff, pzs_12012_diff, pzs_source, good_distance, p3zs_diff) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (now, clean_value, category, 0, 0, 0, 0, 0, None, None, 0))
            current_game_id = cursor.lastrowid

            print(f"📩 Data: {clean_value}x (ID: {current_game_id}) | G-Target: {gap_click_target_id} | Measured-G: {gap_measured_value}", flush=True)

            # --- OLD GAP CLICKER LOGIC (COMMENTED OUT) ---
            # if clean_value < 1.21:
            #     # 1. Measurement: Calculate gap between last hit and this hit
            #     if gap_last_hit_id > 0:
            #         new_g = current_game_id - gap_last_hit_id - 1
            #
            #         if new_g >= 3:
            #             # REAL/BETTER HIT: Reset the base and update the schedule
            #             old_target = gap_click_target_id
            #             gap_measured_value = new_g
            #             gap_last_hit_id = current_game_id
            #             gap_click_target_id = current_game_id + gap_measured_value
            #
            #             status_str = "OVERRIDDEN" if old_target > 0 else "Triggered"
            #             print(f"🎯 {status_str}! New Gap={gap_measured_value}. Click at Round {gap_click_target_id}", flush=True)
            #         else:
            #             # NOISE HIT: Don't let small gaps (0,1,2) reset our good G or Target
            #             print(f"ℹ️ NOISE HIT (Gap {new_g} < 3). Ignoring and keeping Target {gap_click_target_id} (G={gap_measured_value})", flush=True)
            #     else:
            #         # First hit of the session: Set the starting base
            #         gap_last_hit_id = current_game_id
            #         print(f"🏁 First reference hit recorded at ID: {gap_last_hit_id}. Waiting for next hit to measure gap.", flush=True)
            #
            # # 2. Execution: Check if we reached the targeted round
            # if gap_click_target_id > 0 and current_game_id == gap_click_target_id:
            #     print(f"🎯 TARGET REACHED! (ID: {current_game_id} == Target: {gap_click_target_id}). Checking window...", flush=True)
            #
            #     # Check previous 10 results for Category 0 density from all_games
            #     cursor.execute("SELECT category FROM all_games ORDER BY id DESC LIMIT 10")
            #     last_10_rows = cursor.fetchall()
            #     last_10_cats = [r[0] for r in last_10_rows]
            #     zero_count = last_10_cats.count(0)
            #
            #     if zero_count >= 7:
            #         print(f"⚠️ SKIP CLICK! Window has {zero_count}/10 zeros (Category 0). Skipping click for safety.", flush=True)
            #     else:
            #         print(f"✅ Safe to click: Window has {zero_count}/10 zeros. Clicking...", flush=True)
            #         threading.Thread(target=lambda: pyautogui.click(1054, 822)).start()
            #
            #     gap_click_target_id = 0

            # --- NEW: 3-GAP AVERAGE CLICKER LOGIC ---
            import math
            gap_hist_1 = int(gap_hist_1) if gap_hist_1 is not None else -1
            gap_hist_2 = int(gap_hist_2) if gap_hist_2 is not None else -1
            gap_hist_3 = int(gap_hist_3) if gap_hist_3 is not None else -1

            # Check for a pending log/click schedule
            if os.path.exists(PENDING_CLICK_FILE):
                try:
                    p_updated = False
                    with open(PENDING_CLICK_FILE, 'r') as pcf:
                        pending = json.load(pcf)
                    
                    # 1. Process Delayed Logs (Regardless of betting threshold)
                    pending_logs = pending.get('pending_logs', [])
                    remaining_logs = []
                    for log_entry in pending_logs:
                        if clean_value < log_entry['threshold']:
                            with open(log_entry['file'], 'a') as pf:
                                pf.write(log_entry['line'])
                            print(f"✅ DELAYED LOG WRITTEN: {log_entry['file']} (Thresh {log_entry['threshold']} met by {clean_value})", flush=True)
                            p_updated = True
                        else:
                            remaining_logs.append(log_entry)
                    pending['pending_logs'] = remaining_logs
                    
                    # 2. Process Betting Trigger
                    pending_threshold = pending.get('threshold', 1.21)
                    bet_fired = False
                    if clean_value < pending_threshold and 'targets' in pending:
                        if 'targets' in pending:
                            pending_targets = pending['targets']
                        else:
                            pending_targets = [pending.get('rounds', 0)]
                        pending_lists = pending.get('lists', [])
                        
                        ACTIVE_TARGETS_FILE = 'active_targets.json'
                        active_targets = []
                        if os.path.exists(ACTIVE_TARGETS_FILE):
                            try:
                                with open(ACTIVE_TARGETS_FILE, 'r') as atf:
                                    active_targets = json.load(atf)
                            except: pass
                        
                        new_target_ids = [current_game_id + r for r in pending_targets if r >= 0]
                        active_targets.extend(new_target_ids)
                        active_targets = list(set(active_targets))
                        
                        with open(ACTIVE_TARGETS_FILE, 'w') as atf:
                            json.dump(active_targets, atf)
                            
                        gap_click_target_id = new_target_ids[0] if new_target_ids else 0
                        bet_fired = True
                        pending_just_fired = True
                        print(f"🎯 PENDING FIRED! Bad result (<{pending_threshold}) hit [1.34 Active]. Lists {pending_lists} → clicking at specific rounds {new_target_ids}", flush=True)
                    
                    if bet_fired:
                        # If bet fired, remove the bet arming keys but keep remaining logs if any
                        pending.pop('targets', None)
                        pending.pop('lists', None)
                        pending.pop('threshold', None)
                        p_updated = True
                    
                    if p_updated:
                        if not pending.get('pending_logs') and 'targets' not in pending:
                            os.remove(PENDING_CLICK_FILE)
                        else:
                            with open(PENDING_CLICK_FILE, 'w') as pcf:
                                json.dump(pending, pcf)
                except Exception as pe:
                    print(f"⚠️ Pending click file error: {pe}", flush=True)
                # [3-GAP CLICKER DISABLED — pending [0,1] system only]
                # if gap_last_hit_id > 0:
                #     new_g = current_game_id - gap_last_hit_id - 1
                #     gap_hist_3 = gap_hist_2
                #     gap_hist_2 = gap_hist_1
                #     gap_hist_1 = new_g
                #     recorded = [g for g in [gap_hist_1, gap_hist_2, gap_hist_3] if g >= 0]
                #     if len(recorded) == 3:
                #         avg_gap = sum(recorded) / 3
                #         click_rounds_away = math.ceil(avg_gap)
                #         if not pending_just_fired:
                #             gap_click_target_id = current_game_id + click_rounds_away
                #             print(f"📊 Gap: {new_g} | Avg: {avg_gap:.2f} | Click at Round {gap_click_target_id}", flush=True)
                #     else:
                #         print(f"📊 Gap recorded: {new_g} | History: {recorded} ({len(recorded)}/3)", flush=True)
                #     gap_last_hit_id = current_game_id
                # else:
                #     gap_last_hit_id = current_game_id
                #     print(f"🏁 First reference hit at ID: {gap_last_hit_id}.", flush=True)


            ACTIVE_TARGETS_FILE = 'active_targets.json'
            active_targets = []
            if os.path.exists(ACTIVE_TARGETS_FILE):
                try:
                    with open(ACTIVE_TARGETS_FILE, 'r') as atf:
                        active_targets = json.load(atf)
                except: pass

            should_click_now = (current_game_id in active_targets) or (gap_click_target_id > 0 and current_game_id == gap_click_target_id)

            if should_click_now:
                print(f"🎯 CLICK TARGET REACHED! (ID: {current_game_id}). Executing click immediately (all conditions bypassed!)...", flush=True)

                # --- ALL CHECKING CONDITIONS COMMENTED OUT ---
                # Check bad% at click time: raw_value < 2.0 over last 10
                # cursor.execute("SELECT raw_value FROM all_games ORDER BY id DESC LIMIT 10")
                # exec_10_rows = cursor.fetchall()
                # exec_10_vals = [float(r[0]) for r in exec_10_rows]
                # exec_bad_count = sum(1 for v in exec_10_vals if v < 2.0)
                # exec_total = len(exec_10_vals)
                # exec_bad_pct = round((exec_bad_count / exec_total) * 100, 1) if exec_total > 0 else 0.0

                # if exec_bad_pct > 40.0:
                #     print(f"🚫 Click SKIPPED at execution: bad%={exec_bad_pct}% > 40% — conditions not safe", flush=True)
                # else:
                print(f"✅ Clicking! (1.34 Threshold [0,1] tail triggered)", flush=True)
                
                # --- ALTERNATING CLICK LOGIC ---
                global bet_click_toggle, last_bet_click_time
                target_point = BET_POINTS[bet_click_toggle]
                print(f"🚀 [Toggle {bet_click_toggle}] Clicking at {target_point}", flush=True)
                
                threading.Thread(target=lambda: pyautogui.click(target_point)).start()
                
                # Update state
                bet_click_toggle = (bet_click_toggle + 1) % len(BET_POINTS)
                last_bet_click_time = time.time()
                # ------------------------------

                # --- NEW: Save balance before bet (including current bet amount) ---
                try:
                    with open('pending_bet_balance.json', 'w') as f:
                        json.dump({
                            "before_balance": balance_val,
                            "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
                            "bet_amount": current_bet
                        }, f)
                except: pass
                # ------------------------------------

                threading.Thread(target=delayed_restart, args=(5,), daemon=True).start()

                try:
                    with open('last_click.json', 'w') as f:
                        json.dump({"click_for_id": current_game_id + 1, "exec_bad": 0.0}, f)
                except: pass

                if current_game_id in active_targets:
                    active_targets.remove(current_game_id)
                    with open(ACTIVE_TARGETS_FILE, 'w') as atf:
                        json.dump(active_targets, atf)
                        
                gap_click_target_id = 0


            # --- RANDOM CLICKER LOGIC (COMMENTED) ---
            # triggered_this_round = False
            # if clean_value < 1.21:
            #     click_delay_target = random.randint(1, 5)
            #     click_delay_count = 0
            #     triggered_this_round = True
            #     print(f"🎲 HIT (<1.21)! Target set: Click in {click_delay_target} rounds", flush=True)
            #
            # if click_delay_target > 0 and not triggered_this_round:
            #     click_delay_count += 1
            #     print(f"⏳ Counting towards random click: {click_delay_count}/{click_delay_target}", flush=True)
            #     if click_delay_count >= click_delay_target:
            #         print(f"🎯 TARGET REACHED! Clicking...", flush=True)
            #         threading.Thread(target=lambda: pyautogui.click(1054, 822)).start()
            #         click_delay_target = 0
            #         click_delay_count = 0
            
            # --- PZS LOGIC ---
            pzs_state = int(pzs_state) if pzs_state is not None else 0
            pzs_current_diff = int(pzs_current_diff) if pzs_current_diff is not None else 0
            pzs_0012_state = int(pzs_0012_state) if pzs_0012_state is not None else 0
            pzs_0012_diff = int(pzs_0012_diff) if pzs_0012_diff is not None else 0
            pzs_12012_state = int(pzs_12012_state) if pzs_12012_state is not None else 0
            pzs_12012_diff = int(pzs_12012_diff) if pzs_12012_diff is not None else 0
            zeros_since_last_good = int(zeros_since_last_good) if zeros_since_last_good is not None else 0
            p3zs_current_diff = int(p3zs_current_diff) if p3zs_current_diff is not None else 0
            p3zs_state = int(p3zs_state) if p3zs_state is not None else 0
            p3zs_zeros_count = int(p3zs_zeros_count) if p3zs_zeros_count is not None else 0

            # Get recent category history
            cursor.execute("SELECT category FROM all_games ORDER BY id DESC LIMIT 4")
            history_rows = cursor.fetchall()
            hist = [r[0] for r in reversed(history_rows)]
            
            # Sequence detection
            is_0012 = False
            is_12012 = False
            if len(hist) >= 3:
                prev_3 = hist[-3:]
                if prev_3 == [0, 0, 1] or prev_3 == [0, 0, 2]: is_0012 = True
                if (prev_3[0] in [1, 2]) and prev_3[1] == 0 and (prev_3[2] in [1, 2]): is_12012 = True

            # --- P3ZS LOGIC ---
            if category == 0:
                if p3zs_state == 1:
                    p3zs_current_diff -= 1
                    p3zs_state = 0
                    p3zs_zeros_count = 1
                else:
                    p3zs_zeros_count += 1
            elif category in [1, 2]:
                if p3zs_state == 1:
                    print(f"🎯 P3ZS Success! (Click disabled in favor of universal trigger)", flush=True)
                    # pyautogui.click(1782, 473)
                    p3zs_current_diff += 1
                    p3zs_state = 0
                    p3zs_zeros_count = 0
                else:
                    if p3zs_zeros_count >= 3:
                        p3zs_state = 1
                    p3zs_zeros_count = 0
            save_p3zs_diff = p3zs_current_diff

            # --- DISTANCE & PATTERN LOGIC ---
            if category == 0:
                zeros_since_last_good += 1
            elif category in [1, 2]:
                save_good_distance = zeros_since_last_good
                zeros_since_last_good = 0
            
            # Pattern Clicker Logic: [Good, Bad, Good] -> [1/2, 0, current=1/2]
            if len(hist) >= 2:
                if (hist[-2] in [1, 2]) and (hist[-1] == 0) and (category in [1, 2]):
                    print(f"🎯 Pattern Matched ([{hist[-2]}, {hist[-1]}, {category}])! (Click disabled in favor of universal trigger)", flush=True)
                    # pyautogui.click(1782, 473)

            # State machine for main PZS:
            if category == 0:
                if pzs_state == 2:
                    pzs_current_diff -= 1
                    if is_0012: save_pzs_source = '0012'
                    elif is_12012: save_pzs_source = '12012'
                pzs_state = 1
            elif category in [1, 2]:
                if pzs_state == 1:
                    pzs_state = 2
                elif pzs_state == 2:
                    pzs_current_diff += 1
                    if is_12012: save_pzs_source = '12012'
                    elif is_0012: save_pzs_source = '0012'
                    pzs_state = 0
            
            # Specific sequence trackers
            if is_0012:
                if category == 0: pzs_0012_diff -= 1
                elif category in [1, 2]: pzs_0012_diff += 1
            
            if is_12012:
                if category == 0: pzs_12012_diff -= 1
                elif category in [1, 2]: pzs_12012_diff += 1

            save_pzs_diff = pzs_current_diff
            save_pzs_0012_diff = pzs_0012_diff
            save_pzs_12012_diff = pzs_12012_diff

            if status == 'WAITING':
                rounds_collected += 1
                current_diff += round_val
                if rounds_collected == 5:
                    status = 'TRACKING'
                    max_diff = current_diff
                    extreme_start_time = now
                    rounds_since_extreme = 0
            elif status == 'TRACKING':
                current_diff += round_val
                rounds_since_extreme += 1
                
                is_new_extreme = False
                if max_diff < 0 and current_diff < max_diff: is_new_extreme = True
                elif max_diff > 0 and current_diff > max_diff: is_new_extreme = True
                    
                if is_new_extreme:
                    duration_held = int((now - extreme_start_time).total_seconds()) if extreme_start_time else 0
                    cursor.execute("INSERT INTO extreme_durations (max_diff_value, duration_seconds, rounds_count, ended_at) VALUES (%s, %s, %s, %s)", (max_diff, duration_held, rounds_since_extreme, now))
                    max_diff = current_diff
                    extreme_start_time = now
                    rounds_since_extreme = 0
                
                if current_diff == 0:
                    time_diff_secs = int((now - extreme_start_time).total_seconds()) if extreme_start_time else 0
                    cursor.execute("INSERT INTO convergence_history (max_difference, time_difference_seconds, rounds_to_converge, recorded_at) VALUES (%s, %s, %s, %s)", (max_diff, time_diff_secs, rounds_since_extreme, now))
                    status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme = 'WAITING', 0, 0, 0, None, 0
            
            if status == 'TRACKING':
                save_current_diff = current_diff
                save_max_diff = max_diff
            else:
                save_current_diff = 0
                save_max_diff = 0

            cursor.execute("""
                UPDATE tracker_state 
                SET status=%s, rounds_collected=%s, current_diff=%s, max_diff=%s, extreme_start_time=%s, rounds_since_extreme=%s, pzs_current_diff=%s, pzs_state=%s, pzs_0012_diff=%s, pzs_0012_state=%s, pzs_12012_diff=%s, pzs_12012_state=%s, zeros_since_last_good=%s, p3zs_current_diff=%s, p3zs_state=%s, p3zs_zeros_count=%s, click_delay_target=%s, click_delay_count=%s, gap_last_hit_id=%s, gap_measured_value=%s, gap_click_target_id=%s, gap_hist_1=%s, gap_hist_2=%s, gap_hist_3=%s
                WHERE id = 1
            """, (status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count, click_delay_target, click_delay_count, gap_last_hit_id, gap_measured_value, gap_click_target_id, gap_hist_1, gap_hist_2, gap_hist_3))

        # --- UPDATE RECENT INSERT WITH CALC DATA ---
        update_query = "UPDATE game_data SET current_diff=%s, max_diff=%s, pzs_diff=%s, pzs_0012_diff=%s, pzs_12012_diff=%s, pzs_source=%s, good_distance=%s, p3zs_diff=%s WHERE id=%s"
        cursor.execute(update_query, (save_current_diff, save_max_diff, save_pzs_diff, save_pzs_0012_diff, save_pzs_12012_diff, save_pzs_source, save_good_distance, save_p3zs_diff, current_game_id))
        
        # --- SAVE TO RAW HISTORY ---
        cursor.execute("INSERT INTO all_games (timestamp, raw_value, category) VALUES (%s, %s, %s)", (now, clean_value, category))
        
        # --- LOG RAW PATTERNS ---
        cursor.execute("SELECT category FROM all_games ORDER BY id DESC LIMIT 5")
        history_rows = cursor.fetchall()
        hist_cats = [str(r[0]) for r in reversed(history_rows)]
        
        for length in [3, 4, 5]:
            if len(hist_cats) >= length:
                pattern = "".join(hist_cats[-length:])
                cursor.execute("INSERT INTO all_patterns (pattern_string, pattern_length, timestamp) VALUES (%s, %s, %s)", (pattern, length, now))
        
        # --- PATTERN TRACKING (Aggregated Table) ---
        cursor.execute("SELECT category FROM game_data ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        
        recent_cats = [str(row[0]) for row in rows]
        recent_cats.reverse()
        
        patterns = []
        n = len(recent_cats)
        if n >= 3: patterns.append("".join(recent_cats[-3:]))
        if n >= 4: patterns.append("".join(recent_cats[-4:]))
        if n >= 5: patterns.append("".join(recent_cats[-5:]))
            
        if patterns:
            upsert_query = """
                INSERT INTO pattern_counts (pattern_string, pattern_length, occurrence_count) 
                VALUES (%s, %s, 1) 
                ON DUPLICATE KEY UPDATE occurrence_count = occurrence_count + 1
            """
            for pattern in patterns:
                cursor.execute(upsert_query, (pattern, len(pattern)))

        conn.commit()
        cursor.close()
        conn.close()

        # Trigger delayed click on EVERY data entry
        #threading.Thread(target=delayed_click, args=(1054, 822, 1.5), daemon=True).start()

        print(f"✅ Saved: {clean_value} (Cat: {category})", flush=True)

        # Round counter tracker (Restart trigger now handled by click event)
        round_counter += 1
        print(f"🔢 Round Counter: {round_counter}", flush=True)

        return jsonify({
            "status": "success", 
            "message": "Saved",
            "category": category,
            "good_distance": save_good_distance,
            "p3zs_diff": save_p3zs_diff
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def auto_click_center():
    """Clicks the center of the screen every 30 minutes."""
    while True:
        time.sleep(1800)  # Wait 30 minutes BEFORE the first click
        try:
            screen_width, screen_height = pyautogui.size()
            center_x = screen_width // 2
            center_y = screen_height // 2
            pyautogui.moveTo(center_x, center_y, duration=0.2)
            print(f"🖱️ Moved to center of screen ({center_x}, {center_y})", flush=True)
        except Exception as e:
            print(f"⚠️ Auto-click center error: {e}", flush=True)


def simulate_idle_activity():
    """Simulates random mouse activity if no betting click has triggered for 10 minutes.
    Press Q to PAUSE movement | Press S to RESUME movement.
    """
    global last_bet_click_time, idle_active
    print("👻 Idle Simulation Thread Started (Q=stop | S=start | triggers after 10 mins idle)", flush=True)
    while True:
        # Check every 60 seconds for better responsiveness
        time.sleep(60)
        if not idle_active:
            continue  # Q was pressed — skip this cycle silently
        if time.time() - last_bet_click_time >= 600:  # 10 minutes of inactivity
            try:
                # Random X [97, 550], Random Y [200, 900]
                rand_x = random.randint(97, 550)
                rand_y = random.randint(200, 900)

                print(f"👻 Idle for 10 mins! Simulating movement at ({rand_x}, {rand_y})...", flush=True)
                pyautogui.moveTo(rand_x, rand_y, duration=0.5)

                # Reset the clock after simulation so we do it again only after another 10 mins idle
                last_bet_click_time = time.time()
            except Exception as e:
                print(f"⚠️ Idle simulation error: {e}", flush=True)


def pixel_check_loop():
    """
    Checks pixel (608, 496) every 30 seconds.
    If the R value equals 245, clicks at (691, 260) once and continues normal operation.
    """
    CHECK_X, CHECK_Y = 608, 496
    CLICK_X, CLICK_Y = 691, 260
    INTERVAL = 30  # seconds between checks

    print(f"🔍 Pixel Check Thread Started (checking ({CHECK_X},{CHECK_Y}) every {INTERVAL}s)", flush=True)
    while True:
        time.sleep(INTERVAL)
        try:
            r, g, b = pyautogui.pixel(CHECK_X, CHECK_Y)
            if r == 245:
                print(f"✅ Pixel ({CHECK_X},{CHECK_Y}) R={r} — clicking ({CLICK_X},{CLICK_Y})", flush=True)
                pyautogui.click(CLICK_X, CLICK_Y)
            else:
                print(f"🔎 Pixel ({CHECK_X},{CHECK_Y}) R={r} (not 245, skipping)", flush=True)
        except Exception as e:
            print(f"⚠️ Pixel check error: {e}", flush=True)


def keyboard_listener():
    """Listens for Q (stop idle movement) and S (start idle movement) key presses."""
    global idle_active
    try:
        from pynput import keyboard

        def on_press(key):
            global idle_active
            try:
                ch = key.char.lower() if hasattr(key, 'char') and key.char else None
                if ch == 'q':
                    idle_active = False
                    print("⏸️  Idle mouse movement PAUSED (Q pressed)", flush=True)
                elif ch == 's':
                    idle_active = True
                    print("▶️  Idle mouse movement RESUMED (S pressed)", flush=True)
            except Exception:
                pass  # Special key — ignore

        with keyboard.Listener(on_press=on_press) as listener:
            print("⌨️  Keyboard listener active: Q=pause idle | S=resume idle", flush=True)
            listener.join()
    except ImportError:
        print("⚠️  pynput not installed — Q/S toggle unavailable. Run: pip install pynput", flush=True)
    except Exception as ke:
        print(f"⚠️  Keyboard listener error: {ke}", flush=True)


if __name__ == '__main__':
    # --- RESET SESSION DATA ON STARTUP (ONLY IF NOT A RESTART) ---
    SHOULD_RESET = "--no-truncate" not in sys.argv
    
    if SHOULD_RESET:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # Migration: Ensure all needed columns exist in tracker_state
            for col in [
                "pzs_current_diff INT DEFAULT 0", "pzs_state INT DEFAULT 0",
                "pzs_0012_diff INT DEFAULT 0", "pzs_0012_state INT DEFAULT 0",
                "pzs_12012_diff INT DEFAULT 0", "pzs_12012_state INT DEFAULT 0",
                "zeros_since_last_good INT DEFAULT 0", "p3zs_current_diff INT DEFAULT 0",
                "p3zs_state INT DEFAULT 0", "p3zs_zeros_count INT DEFAULT 0",
                "click_delay_target INT DEFAULT 0", "click_delay_count INT DEFAULT 0",
                "gap_last_hit_id BIGINT DEFAULT 0", "gap_measured_value INT DEFAULT 0",
                "gap_click_target_id BIGINT DEFAULT 0",
                "gap_hist_1 INT DEFAULT -1", "gap_hist_2 INT DEFAULT -1",
                "gap_hist_3 INT DEFAULT -1"
            ]:
                try: cursor.execute(f"ALTER TABLE tracker_state ADD COLUMN {col}")
                except: pass
            
            # Migration: Ensure all needed columns exist in game_data
            for col in [
                "pzs_diff INT DEFAULT 0", "pzs_0012_diff INT DEFAULT 0",
                "pzs_12012_diff INT DEFAULT 0", "pzs_source VARCHAR(50)",
                "good_distance INT DEFAULT NULL", "p3zs_diff INT DEFAULT 0"
            ]:
                try: cursor.execute(f"ALTER TABLE game_data ADD COLUMN {col}")
                except: pass
    
            print("🔄 Starting new session: Clearing session-specific data...")
            cursor.execute("TRUNCATE TABLE game_data")
            cursor.execute("UPDATE tracker_state SET status='WAITING', rounds_collected=0, current_diff=0, max_diff=0, extreme_start_time=NULL, rounds_since_extreme=0, pzs_current_diff=0, pzs_state=0, pzs_0012_diff=0, pzs_0012_state=0, pzs_12012_diff=0, pzs_12012_state=0, zeros_since_last_good=0, p3zs_current_diff=0, p3zs_state=0, p3zs_zeros_count=0, click_delay_target=0, click_delay_count=0, gap_last_hit_id=0, gap_measured_value=0, gap_click_target_id=0, gap_hist_1=-1, gap_hist_2=-1, gap_hist_3=-1 WHERE id=1")
            
            # Also reset max_balance and streak for a fresh session
            save_bet_state(BASE_BET, 0, BASE_BET, 0.0, 0)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Session reset complete. (Historical patterns & all_games preserved)")
        except Exception as e:
            print(f"⚠️ Session reset error: {e}")
    else:
        print("⏭️ RESTART DETECTED: Preserving game_data and tracker_state.")

    print("\n" + "="*50)
    print("🚀 FLYER BACKEND ACTIVE: Port 5000 is listening!")
    print("Watching for Game results and GAPs...")
    print("="*50 + "\n", flush=True)


    click_thread = threading.Thread(target=auto_click_center, daemon=True)
    click_thread.start()

    idle_thread = threading.Thread(target=simulate_idle_activity, daemon=True)
    idle_thread.start()

    pixel_thread = threading.Thread(target=pixel_check_loop, daemon=True)
    pixel_thread.start()

    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()

    app.run(host='127.0.0.1', port=5000)

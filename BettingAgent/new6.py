from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import mysql.connector
import threading
import time
import pyautogui

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',         # Replace with your MySQL username
    'password': 'Et3aa@123', # Replace with your MySQL password
    'database': 'aviator_db'
}

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
        # This allows probabilities to show immediately even on fresh session restart
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
                
                # Search for any pattern starting with this prefix
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
                    # pattern_string is like "101" where the last char is the "next" result
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

        # Calculate Total Probability (simple average of valid length results)
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
        data = request.json
        multiplier_str = data.get('multiplier', '0')
        
        # 1. Clean data & categorize
        clean_value = float(multiplier_str.replace('x', '').strip())
        category = get_category(clean_value)
        now = datetime.now()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # --- NEW: CALCULATE TRACKER STATE ---
        cursor.execute("SELECT status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count FROM tracker_state WHERE id = 1")
        state_row = cursor.fetchone()
        
        # Good = +1 (categories 1, 2), Bad = -1 (category 0)
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
            status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count = state_row
            
            # --- PZS LOGIC ---
            # Ensure values are never None
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

            # Get recent category history to identify trigger sequences
            cursor.execute("SELECT category FROM all_games ORDER BY id DESC LIMIT 4")
            history_rows = cursor.fetchall()
            # history_rows is [newest, ..., oldest]
            # We want [oldest, ..., newest] excluding the *current* category (which isn't in DB yet)
            # Actually, let's just use the list we'll fetch later or fetch it now.
            hist = [r[0] for r in reversed(history_rows)] # [oldest -> newest]
            
            # Sequence detection (current category is the 'outcome')
            is_0012 = False
            is_12012 = False
            if len(hist) >= 3:
                # hist[-3:] would be the 3 rounds before current
                prev_3 = hist[-3:]
                if prev_3 == [0, 0, 1] or prev_3 == [0, 0, 2]: is_0012 = True
                if (prev_3[0] in [1, 2]) and prev_3[1] == 0 and (prev_3[2] in [1, 2]): is_12012 = True

            # --- P3ZS LOGIC ---
            # 3+ zeros then 1 repeat (+1) or fail (-1)
            if category == 0:
                if p3zs_state == 1:
                    p3zs_current_diff -= 1
                    p3zs_state = 0
                    p3zs_zeros_count = 1
                else:
                    p3zs_zeros_count += 1
            elif category in [1, 2]:
                if p3zs_state == 1:
                    print(f"🎯 P3ZS Success! Clicking at (1782, 473)...", flush=True)
                    pyautogui.click(1782, 473)
                    p3zs_current_diff += 1
                    p3zs_state = 0
                    p3zs_zeros_count = 0
                else:
                    if p3zs_zeros_count >= 3:
                        p3zs_state = 1
                    p3zs_zeros_count = 0
            save_p3zs_diff = p3zs_current_diff

            # --- DISTANCE & PATTERN LOGIC ---
            # Distance logic
            if category == 0:
                zeros_since_last_good += 1
            elif category in [1, 2]:
                save_good_distance = zeros_since_last_good
                zeros_since_last_good = 0
            
            # Pattern Clicker Logic: [Good, Bad, Good] -> [1/2, 0, current=1/2]
            if len(hist) >= 2:
                # hist is [oldest -> newest] excluding current category
                # Looking for [hist[-2], hist[-1], category]
                if (hist[-2] in [1, 2]) and (hist[-1] == 0) and (category in [1, 2]):
                    print(f"🎯 Pattern Matched ([{hist[-2]}, {hist[-1]}, {category}])! Clicking at (1782, 473)...", flush=True)
                    pyautogui.click(1782, 473)

            # State machine for main PZS:
            if category == 0:
                if pzs_state == 2:
                    pzs_current_diff -= 1
                    # Identify source of downfall
                    if is_0012: save_pzs_source = '0012'
                    elif is_12012: save_pzs_source = '12012'
                pzs_state = 1
            elif category in [1, 2]:
                if pzs_state == 1:
                    pzs_state = 2
                elif pzs_state == 2:
                    pzs_current_diff += 1
                    # Identify source of rise
                    if is_12012: save_pzs_source = '12012'
                    elif is_0012: save_pzs_source = '0012'
                    pzs_state = 0
            
            # Specific sequence trackers
            # 0012 tracker
            if is_0012:
                if category == 0: pzs_0012_diff -= 1
                elif category in [1, 2]: pzs_0012_diff += 1
            
            # 12012 tracker
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
            
            # Finalize values for snapshot
            if status == 'TRACKING':
                save_current_diff = current_diff
                save_max_diff = max_diff
            else:
                save_current_diff = 0
                save_max_diff = 0

            # Update tracker_state table
            cursor.execute("""
                UPDATE tracker_state 
                SET status=%s, rounds_collected=%s, current_diff=%s, max_diff=%s, extreme_start_time=%s, rounds_since_extreme=%s, pzs_current_diff=%s, pzs_state=%s, pzs_0012_diff=%s, pzs_0012_state=%s, pzs_12012_diff=%s, pzs_12012_state=%s, zeros_since_last_good=%s, p3zs_current_diff=%s, p3zs_state=%s, p3zs_zeros_count=%s
                WHERE id = 1
            """, (status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme, pzs_current_diff, pzs_state, pzs_0012_diff, pzs_0012_state, pzs_12012_diff, pzs_12012_state, zeros_since_last_good, p3zs_current_diff, p3zs_state, p3zs_zeros_count))

        # --- ORIGINAL INSERT ---
        insert_query = "INSERT INTO game_data (timestamp, raw_value, category, current_diff, max_diff, pzs_diff, pzs_0012_diff, pzs_12012_diff, pzs_source, good_distance, p3zs_diff) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (now, clean_value, category, save_current_diff, save_max_diff, save_pzs_diff, save_pzs_0012_diff, save_pzs_12012_diff, save_pzs_source, save_good_distance, save_p3zs_diff))
        
        # --- NEW: SAVE TO RAW HISTORY ---
        cursor.execute("INSERT INTO all_games (timestamp, raw_value, category) VALUES (%s, %s, %s)", (now, clean_value, category))
        
        # --- NEW: LOG RAW PATTERNS ---
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

        # Pattern tracking and raw history insertion continues...

        # Commit everything
        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Saved: {clean_value} (Cat: {category})", flush=True)
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
    """Clicks the center of the screen every 5 minutes."""
    while True:
        screen_width, screen_height = pyautogui.size()
        center_x = screen_width // 2
        center_y = screen_height // 2
        pyautogui.click(center_x, center_y)
        print(f"🖱️ Auto-clicked center of screen ({center_x}, {center_y})", flush=True)
        time.sleep(1800)  # Wait 5 minutes


if __name__ == '__main__':
    # --- NEW: RESET SESSION DATA ON STARTUP ---
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Migration: Ensure PZS columns exist
        try:
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_current_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_state INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_0012_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_0012_state INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_12012_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN pzs_12012_state INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN zeros_since_last_good INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN p3zs_current_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN p3zs_state INT DEFAULT 0")
            cursor.execute("ALTER TABLE tracker_state ADD COLUMN p3zs_zeros_count INT DEFAULT 0")
        except: pass 
        
        try:
            cursor.execute("ALTER TABLE game_data ADD COLUMN pzs_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE game_data ADD COLUMN pzs_0012_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE game_data ADD COLUMN pzs_12012_diff INT DEFAULT 0")
            cursor.execute("ALTER TABLE game_data ADD COLUMN pzs_source VARCHAR(50)")
            cursor.execute("ALTER TABLE game_data ADD COLUMN good_distance INT DEFAULT NULL")
            cursor.execute("ALTER TABLE game_data ADD COLUMN p3zs_diff INT DEFAULT 0")
        except: pass

        print("🔄 Starting new session: Clearing session-specific data...")
        cursor.execute("TRUNCATE TABLE game_data")
        # Reset tracker state to initial values
        cursor.execute("UPDATE tracker_state SET status='WAITING', rounds_collected=0, current_diff=0, max_diff=0, extreme_start_time=NULL, rounds_since_extreme=0, pzs_current_diff=0, pzs_state=0, pzs_0012_diff=0, pzs_0012_state=0, pzs_12012_diff=0, pzs_12012_state=0, zeros_since_last_good=0, p3zs_current_diff=0, p3zs_state=0, p3zs_zeros_count=0 WHERE id=1")
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Session reset complete. (Historical patterns & all_games preserved)")
    except Exception as e:
        print(f"⚠️ Session reset error: {e}")

    click_thread = threading.Thread(target=auto_click_center, daemon=True)
    click_thread.start()
    app.run(host='127.0.0.1', port=5000)
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
        
        query = """
            SELECT pattern_string, occurrence_count 
            FROM pattern_counts 
            WHERE pattern_length = %s 
            ORDER BY occurrence_count DESC
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
        
        # --- ORIGINAL INSERT ---
        insert_query = "INSERT INTO game_data (timestamp, raw_value, category) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (now, clean_value, category))
        
        # --- PATTERN TRACKING ---
        cursor.execute("SELECT category FROM game_data ORDER BY timestamp DESC LIMIT 5")
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

        # --- CONVERGENCE TRACKING ---
        # Good = +1 (categories 1, 2), Bad = -1 (category 0)
        round_val = 1 if category in [1, 2] else -1
        
        # Fetch current state
        cursor.execute("SELECT status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme FROM tracker_state WHERE id = 1")
        state_row = cursor.fetchone()
        
        if state_row:
            status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme = state_row
            
            if status == 'WAITING':
                rounds_collected += 1
                current_diff += round_val
                
                if rounds_collected == 5:
                    # After 5 rounds, transition to TRACKING phase
                    status = 'TRACKING'
                    max_diff = current_diff
                    extreme_start_time = now
                    rounds_since_extreme = 0
                
            elif status == 'TRACKING':
                current_diff += round_val
                rounds_since_extreme += 1
                
                # Check if we hit a new extreme difference
                is_new_extreme = False
                if max_diff < 0 and current_diff < max_diff:
                    is_new_extreme = True
                elif max_diff > 0 and current_diff > max_diff:
                    is_new_extreme = True
                    
                if is_new_extreme:
                    # --- NEW FEATURE: SAVE DURATION OF THE PREVIOUS EXTREME ---
                    duration_held = int((now - extreme_start_time).total_seconds()) if extreme_start_time else 0
                    
                    # Log the old max_diff and how long it lasted before being broken
                    cursor.execute("""
                        INSERT INTO extreme_durations (max_diff_value, duration_seconds, rounds_count, ended_at)
                        VALUES (%s, %s, %s, %s)
                    """, (max_diff, duration_held, rounds_since_extreme, now))
                    
                    # Reset tracking targets to the new extreme
                    max_diff = current_diff
                    extreme_start_time = now
                    rounds_since_extreme = 0
                
                # Check if converged back to 0
                if current_diff == 0:
                    time_diff_secs = int((now - extreme_start_time).total_seconds()) if extreme_start_time else 0
                    
                    # Save to convergence history
                    cursor.execute("""
                        INSERT INTO convergence_history (max_difference, time_difference_seconds, rounds_to_converge, recorded_at)
                        VALUES (%s, %s, %s, %s)
                    """, (max_diff, time_diff_secs, rounds_since_extreme, now))
                    
                    print(f"🎯 Converged! Max Diff: {max_diff}, Time: {time_diff_secs}s, Rounds: {rounds_since_extreme}")
                    
                    # Reset back to WAITING for the next 5-round batch
                    status = 'WAITING'
                    rounds_collected = 0
                    current_diff = 0
                    max_diff = 0
                    extreme_start_time = None
                    rounds_since_extreme = 0
            
            # Update the live state in the database
            cursor.execute("""
                UPDATE tracker_state 
                SET status=%s, rounds_collected=%s, current_diff=%s, max_diff=%s, extreme_start_time=%s, rounds_since_extreme=%s 
                WHERE id = 1
            """, (status, rounds_collected, current_diff, max_diff, extreme_start_time, rounds_since_extreme))

        # Commit everything
        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Saved: {clean_value} (Cat: {category})")
        return jsonify({"status": "success", "message": "Data, Patterns & Extreme History saved"}), 200
        
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
        print(f"🖱️ Auto-clicked center of screen ({center_x}, {center_y})")
        time.sleep(1800)  # Wait 5 minutes


if __name__ == '__main__':
    click_thread = threading.Thread(target=auto_click_center, daemon=True)
    click_thread.start()
    app.run(host='127.0.0.1', port=5000)
import requests
import time
import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def clean_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE game_data")
    cursor.execute("TRUNCATE TABLE all_games")
    cursor.execute("TRUNCATE TABLE all_patterns")
    cursor.execute("TRUNCATE TABLE pattern_counts")
    cursor.execute("UPDATE tracker_state SET status='WAITING', rounds_collected=0, current_diff=0, max_diff=0, extreme_start_time=NULL, rounds_since_extreme=0, pzs_current_diff=0, pzs_state=0, pzs_0012_diff=0, pzs_0012_state=0, pzs_12012_diff=0, pzs_12012_state=0, zeros_since_last_good=0 WHERE id=1")
    conn.commit()
    cursor.close()
    conn.close()
    print("🧹 DB Cleaned")

def send_multiplier(val):
    resp = requests.post("http://127.0.0.1:5000/save", json={"multiplier": str(val)})
    print(f"Sent {val}: {resp.status_code}")
    return resp.json()

def check_results():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT category, good_distance FROM game_data ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Cat: {row['category']}, Distance: {row['good_distance']}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Clean first
    clean_db()
    
    # Sequence: 1.5, 2.5, 3.0, 1.1, 1.2, 1.3, 2.1, 1.05, 2.2
    multipliers = [1.5, 2.5, 3.0, 1.1, 1.2, 1.3, 2.1, 1.05, 2.2]
    for m in multipliers:
        send_multiplier(m)
        time.sleep(0.5)
    
    print("\n--- Results ---")
    check_results()

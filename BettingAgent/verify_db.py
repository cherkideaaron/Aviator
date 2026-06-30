import mysql.connector
import requests
import time

db_config = {'host': '127.0.0.1', 'user': 'root', 'password': 'Et3aa@123', 'database': 'aviator_db'}
BASE_URL = "http://127.0.0.1:5000"

def clear_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE game_data")
    cursor.execute("UPDATE tracker_state SET p3zs_current_diff=0, p3zs_state=0, p3zs_zeros_count=0, zeros_since_last_good=0 WHERE id=1")
    conn.commit()
    cursor.close()
    conn.close()

def save_cat(cat):
    # Map category back to a representative multiplier
    m_map = {0: "1.5x", 1: "3.5x", 2: "15.0x"}
    requests.post(f"{BASE_URL}/save", json={"multiplier": m_map[cat]})

def check_results():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM game_data ORDER BY id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def test_sequence_success():
    print("Testing Sequence: 0, 0, 0, 1, 1 (Expected P3ZS Diff: 1)")
    clear_db()
    for cat in [0, 0, 0, 1, 1]:
        save_cat(cat)
        time.sleep(0.1)
    
    rows = check_results()
    last_row = rows[-1]
    print(f"Result: Category {last_row['category']}, P3ZS Diff: {last_row['p3zs_diff']}")
    if last_row['p3zs_diff'] == 1:
        print("PASS-P3ZS-SUCCESS")
    else:
        print("FAIL-P3ZS-SUCCESS")

def test_sequence_fail():
    print("\nTesting Sequence: 0, 0, 0, 1, 0 (Expected P3ZS Diff: -1)")
    clear_db()
    for cat in [0, 0, 0, 1, 0]:
        save_cat(cat)
        time.sleep(0.1)
    
    rows = check_results()
    last_row = rows[-1]
    print(f"Result: Category {last_row['category']}, P3ZS Diff: {last_row['p3zs_diff']}")
    if last_row['p3zs_diff'] == -1:
        print("PASS-P3ZS-FAIL")
    else:
        print("FAIL-P3ZS-FAIL")

def test_distance():
    print("\nTesting Distance: 1, 0, 0, 2 (Expected Distance: 2)")
    clear_db()
    for cat in [1, 0, 0, 2]:
        save_cat(cat)
        time.sleep(0.1)
    
    rows = check_results()
    last_row = rows[-1]
    print(f"Result: Category {last_row['category']}, Good Distance: {last_row['good_distance']}")
    if last_row['good_distance'] == 2:
        print("PASS-DISTANCE")
    else:
        print("FAIL-DISTANCE")

if __name__ == "__main__":
    test_sequence_success()
    test_sequence_fail()
    test_distance()

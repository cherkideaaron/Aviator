import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def check_snapshots():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        print("--- TABLE: tracker_state (LIVE BOX) ---")
        cursor.execute("SELECT status, current_diff, max_diff FROM tracker_state WHERE id = 1")
        live = cursor.fetchone()
        print(f"LIVE Status: {live['status']} | Curr: {live['current_diff']} | Max: {live['max_diff']}")

        print("\n--- TABLE: game_data (LATEST RECORDS) ---")
        cursor.execute("SELECT id, timestamp, category, current_diff, max_diff FROM game_data ORDER BY timestamp DESC LIMIT 3")
        rows = cursor.fetchall()
        
        for row in rows:
            gap = abs(row['max_diff'] - row['current_diff'])
            print(f"ID: {row['id']} | Cat: {row['category']} | Curr: {row['current_diff']} | Max: {row['max_diff']} | Gap: {gap}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_snapshots()

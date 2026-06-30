import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Aaron@123',
    'database': 'aviator_db'
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tracker_state")
    print(f"tracker_state rows: {cursor.fetchone()[0]}")

    cursor.execute("SELECT * FROM tracker_state WHERE id=1")
    row = cursor.fetchone()
    print(f"id=1 row: {row}")

    cursor.execute("SELECT COUNT(*) FROM game_data")
    print(f"game_data rows: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM all_games")
    print(f"all_games rows: {cursor.fetchone()[0]}")

    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

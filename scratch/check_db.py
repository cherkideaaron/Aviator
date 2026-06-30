import mysql.connector
import json

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Aaron@123',
    'database': 'aviator_db'
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM game_data")
    max_id = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(id) FROM all_games")
    all_max_id = cursor.fetchone()[0]
    print(f"game_data MAX(id): {max_id}")
    print(f"all_games MAX(id): {all_max_id}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

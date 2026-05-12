import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM game_data")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(id) FROM game_data")
    max_id = cursor.fetchone()[0]
    print(f"COUNT:{count}")
    print(f"MAX_ID:{max_id}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

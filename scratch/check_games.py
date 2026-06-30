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
    cursor.execute("SELECT id, raw_value, timestamp FROM game_data ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    print("Latest game_data entries:")
    for r in rows:
        print(r)
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

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
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM balance_history ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    print("Latest 10 balance_history rows:")
    for row in rows:
        print(row)
        
    cursor.execute("SELECT COUNT(*) as count FROM balance_history")
    count = cursor.fetchone()['count']
    print(f"\nTotal rows in balance_history: {count}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

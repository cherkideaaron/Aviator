import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Aaron@123',
    'database': 'aviator_db',
    'connection_timeout': 5
}

def inspect_db():
    try:
        print("Connecting to MySQL...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("Connected successfully!")
        
        # List tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("=== Tables in Database ===")
        for table in tables:
            print(table[0])
        
        # Describe game_data
        cursor.execute("DESCRIBE game_data")
        columns = cursor.fetchall()
        print("\n=== Column schema for game_data ===")
        for col in columns:
            print(f"{col[0]}: {col[1]} (Null: {col[2]}, Key: {col[3]}, Default: {col[4]}, Extra: {col[5]})")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    inspect_db()

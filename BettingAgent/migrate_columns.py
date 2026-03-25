import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def migrate():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("SHOW COLUMNS FROM game_data LIKE 'current_diff'")
        if not cursor.fetchone():
            print("Adding current_diff column...")
            cursor.execute("ALTER TABLE game_data ADD COLUMN current_diff INT DEFAULT 0")
        
        cursor.execute("SHOW COLUMNS FROM game_data LIKE 'max_diff'")
        if not cursor.fetchone():
            print("Adding max_diff column...")
            cursor.execute("ALTER TABLE game_data ADD COLUMN max_diff INT DEFAULT 0")
            
        conn.commit()
        print("✅ Database migration successful.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration error: {e}")

if __name__ == '__main__':
    migrate()

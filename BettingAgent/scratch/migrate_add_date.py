import mysql.connector
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from new8 import db_config, GRAPH_CONFIGS
except ImportError as e:
    print("Could not import new8:", e)
    sys.exit(1)

def migrate_add_date_column():
    print("Connecting to MySQL...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for cfg in GRAPH_CONFIGS:
        table = cfg['table_name']
        # Check if column already exists
        cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'date'")
        if cursor.fetchone():
            print(f"  {table}: date column already exists, skipping.")
            continue
        try:
            # Add date column right after timestamp
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN date DATE AFTER timestamp")
            # Add index on date
            cursor.execute(f"ALTER TABLE {table} ADD INDEX (date)")
            print(f"  {table}: date column added + index created.")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    # Backfill date from existing timestamp values
    print("Backfilling date column from timestamp for all 17 tables...")
    for cfg in GRAPH_CONFIGS:
        table = cfg['table_name']
        cursor.execute(f"UPDATE {table} SET date = DATE(timestamp) WHERE date IS NULL")
        print(f"  {table}: backfilled {cursor.rowcount} rows.")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_add_date_column()

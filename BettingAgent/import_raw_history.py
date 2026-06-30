import mysql.connector
import csv
import glob
import os
from datetime import datetime

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def import_raw_history():
    # 1. Find all game_data CSV files
    csv_files = glob.glob('History/game_data*.csv') + glob.glob('History/gamedat.csv')
    
    if not csv_files:
        print("No game_data CSV files found in History/ directory.")
        return

    all_raw_data = [] # List of (timestamp, raw_value, category)

    for file_path in csv_files:
        print(f"Reading {file_path}...")
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                # Content has delimiter ';' and headers: "id";"timestamp";"raw_value";"category"
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    ts = row['timestamp'].strip('"')
                    rv = float(row['raw_value'])
                    cat = int(row['category'])
                    all_raw_data.append((ts, rv, cat))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    if not all_raw_data:
        print("No raw game data found.")
        return

    # Sort by timestamp to ensure sequence is correct for pattern calculation
    all_raw_data.sort(key=lambda x: x[0])
    print(f"Sorted {len(all_raw_data)} total game records.")

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 0. Clear existing data for a clean consolidation
        print("Truncating 'all_games' and 'pattern_counts' for a clean import...")
        cursor.execute("TRUNCATE TABLE all_games")
        cursor.execute("TRUNCATE TABLE pattern_counts")
        conn.commit()

        # 2. Insert into all_games (raw storage)
        print("Inserting raw data into 'all_games' table...")
        insert_query = "INSERT INTO all_games (timestamp, raw_value, category) VALUES (%s, %s, %s)"
        
        # Batch insert
        chunk_size = 1000
        for i in range(0, len(all_raw_data), chunk_size):
            chunk = all_raw_data[i:i+chunk_size]
            cursor.executemany(insert_query, chunk)
            conn.commit()
            print(f"Inserted {i + len(chunk)} records into all_games...")

        # 3. Calculate and Aggregate Patterns All-Time
        print("Calculating all-time patterns from raw data...")
        categories = [str(d[2]) for d in all_raw_data]
        pattern_counts_aggregated = {} # (pattern_string, length) -> count

        n = len(categories)
        for i in range(n):
            for length in [3, 4, 5]:
                if i >= length - 1:
                    pattern = "".join(categories[i-(length-1):i+1])
                    key = (pattern, length)
                    pattern_counts_aggregated[key] = pattern_counts_aggregated.get(key, 0) + 1

        print(f"Generated {len(pattern_counts_aggregated)} unique patterns. Updating 'pattern_counts' table...")

        # 4. Upsert into pattern_counts (ensure we DON'T double count if rows were already there)
        # But for absolute sync, let's clear pattern_counts first if we want it to PERFECTLY match the raw history?
        # User said: "first we have to combine multiple csv files... and when a new data comes we add on top of it"
        # Since pattern_counts is already used by new5.py, let's just UPSERT.
        
        upsert_query = """
            INSERT INTO pattern_counts (pattern_string, pattern_length, occurrence_count) 
            VALUES (%s, %s, %s) 
            ON DUPLICATE KEY UPDATE occurrence_count = occurrence_count + VALUES(occurrence_count)
        """

        pattern_chunk = [(p, l, c) for (p, l), c in pattern_counts_aggregated.items()]
        for i in range(0, len(pattern_chunk), chunk_size):
            chunk = pattern_chunk[i:i+chunk_size]
            cursor.executemany(upsert_query, chunk)
            conn.commit()
            print(f"Upserted {i + len(chunk)} patterns into pattern_counts...")

        print("✅ Raw history import and pattern synchronization complete.")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    import_raw_history()

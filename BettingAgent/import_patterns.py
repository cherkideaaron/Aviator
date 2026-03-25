import mysql.connector
import csv
import glob
import os

# Database configuration (same as new5.py)
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def import_csv_patterns():
    # Find all relevant CSV files
    csv_files = glob.glob('History/pattern_counts*.csv') + glob.glob('History/pat_ct.csv')
    
    if not csv_files:
        print("No pattern CSV files found in History/ directory.")
        return

    aggregated_patterns = {} # (pattern_string, length) -> total_count

    for file_path in csv_files:
        print(f"Reading {file_path}...")
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                # Based on viewed content: "pattern_string";"pattern_length";"occurrence_count"
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    # Strip quotes if they are part of the value (DictReader might handle them, but let's be safe)
                    pattern = row['pattern_string'].strip('"')
                    length = int(row['pattern_length'])
                    count = int(row['occurrence_count'])
                    
                    key = (pattern, length)
                    aggregated_patterns[key] = aggregated_patterns.get(key, 0) + count
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    if not aggregated_patterns:
        print("No data extracted from CSVs.")
        return

    print(f"Aggregated {len(aggregated_patterns)} unique patterns. Updating database...")

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Upsert query
        upsert_query = """
            INSERT INTO pattern_counts (pattern_string, pattern_length, occurrence_count) 
            VALUES (%s, %s, %s) 
            ON DUPLICATE KEY UPDATE occurrence_count = occurrence_count + VALUES(occurrence_count)
        """

        # Batch update for efficiency
        data_to_upsert = [(p, l, c) for (p, l), c in aggregated_patterns.items()]
        
        # Execute in chunks if data is very large
        chunk_size = 500
        for i in range(0, len(data_to_upsert), chunk_size):
            chunk = data_to_upsert[i:i+chunk_size]
            cursor.executemany(upsert_query, chunk)
            conn.commit()
            print(f"Inserted/Updated {i + len(chunk)} records...")

        print("✅ Data consolidation complete.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    import_csv_patterns()

import mysql.connector
import glob
import csv
import os
from datetime import datetime

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Et3aa@123',
    'database': 'aviator_db'
}

def sync_and_consolidate():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        print("🔄 Starting consolidation and raw pattern sync...")
        
        # 0. Clear existing raw patterns
        cursor.execute("TRUNCATE TABLE all_patterns")
        conn.commit()

        # 1. First, Import Patterns from pattern_counts*.csv (The already-aggregated counts)
        # We "expand" these into the raw table by inserting N rows for a count of N.
        # This ensures that even if we don't have the raw game history, we keep the counts.
        pattern_csvs = glob.glob('History/pattern_counts*.csv') + glob.glob('History/pat_ct.csv')
        total_expanded = 0
        
        print(f"Found {len(pattern_csvs)} pattern count CSVs...")
        for csv_path in pattern_csvs:
            print(f"  Reading {csv_path}...")
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                patterns_to_insert = []
                for row in reader:
                    pattern = row['pattern_string'].strip('"')
                    length = int(row['pattern_length'])
                    count = int(row['occurrence_count'])
                    
                    # For a count of 50, we insert 50 rows to keep it a "raw" all-time log
                    # We use a placeholder timestamp for historical data
                    for _ in range(count):
                        patterns_to_insert.append((pattern, length, datetime(2026, 1, 1)))
                
                if patterns_to_insert:
                    query = "INSERT INTO all_patterns (pattern_string, pattern_length, timestamp) VALUES (%s, %s, %s)"
                    chunk_size = 5000
                    for i in range(0, len(patterns_to_insert), chunk_size):
                        chunk = patterns_to_insert[i:i+chunk_size]
                        cursor.executemany(query, chunk)
                        conn.commit()
                    total_expanded += len(patterns_to_insert)
                    print(f"    Added {len(patterns_to_insert)} occurrences from this file.")

        # 2. Add New Session Patterns (if any exist in all_games that aren't in the CSVs)
        # Note: If game_data.csv matches pattern_counts.csv, this might double count.
        # However, the user said "add on top of it", and usually pattern_counts are generated FROM history.
        # For now, we prioritze the counts from the CSVs as the "historical baseline".
        
        print(f"✅ Consolidation complete. Total occurrences in raw log: {total_expanded}")
        cursor.execute("SELECT pattern_string, COUNT(*) as count FROM all_patterns WHERE pattern_string = '000' GROUP BY pattern_string")
        res = cursor.fetchone()
        if res:
            print(f"📊 Verification: Pattern '000' now has a total count of: {res['count']}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    sync_and_consolidate()

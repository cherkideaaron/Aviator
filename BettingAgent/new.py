from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import mysql.connector

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',         # Replace with your MySQL username
    'password': 'Et3aa@123', # Replace with your MySQL password
    'database': 'aviator_db'
}

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

def get_category(value):
    """Categorizes the value based on your rules."""
    if value < 2.0:
        return 0
    elif 2.0 <= value < 10.0:
        return 1
    else:
        return 2


@app.route('/patterns', methods=['GET'])
def get_top_patterns():
    length = request.args.get('length', type=int) # Get ?length= from URL
    
    if not length or length not in [3, 4, 5]:
        return jsonify({"status": "error", "message": "Please provide a length of 3, 4, or 5"}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True) # Returns results as a list of dicts
        
        # Query to get the patterns for a specific length, highest count first
        query = """
            SELECT pattern_string, occurrence_count 
            FROM pattern_counts 
            WHERE pattern_length = %s 
            ORDER BY occurrence_count DESC
        """
        
        cursor.execute(query, (length,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "length": length,
            "data": results
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


        
@app.route('/save', methods=['POST', 'OPTIONS'])
def save_data():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.json
        multiplier_str = data.get('multiplier', '0')
        
        # 1. Clean the data: Remove 'x' and convert to float
        clean_value = float(multiplier_str.replace('x', '').strip())
        
        # 2. Get the category
        category = get_category(clean_value)
        
        # 3. Get current timestamp
        now = datetime.now()

        # 4. Connect to DB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # --- ORIGINAL INSERT ---
        insert_query = "INSERT INTO game_data (timestamp, raw_value, category) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (now, clean_value, category))
        
        # --- NEW FEATURE: PATTERN TRACKING ---
        
        # Fetch the last 5 categories (including the one we just inserted)
        # Assuming you have an auto-incrementing ID or reliable timestamp.
        cursor.execute("SELECT category FROM game_data ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        
        # Extract categories and reverse them so they are in chronological order (oldest to newest)
        recent_cats = [str(row[0]) for row in rows]
        recent_cats.reverse()
        
        # Generate patterns of length 3, 4, and 5 based on available history
        patterns = []
        n = len(recent_cats)
        if n >= 3:
            patterns.append( "".join(recent_cats[-3:]) ) # e.g., '021'
        if n >= 4:
            patterns.append( "".join(recent_cats[-4:]) ) # e.g., '1021'
        if n >= 5:
            patterns.append( "".join(recent_cats[-5:]) ) # e.g., '01021'
            
        # Insert or update pattern counts
        if patterns:
            upsert_query = """
                INSERT INTO pattern_counts (pattern_string, pattern_length, occurrence_count) 
                VALUES (%s, %s, 1) 
                ON DUPLICATE KEY UPDATE occurrence_count = occurrence_count + 1
            """
            for pattern in patterns:
                cursor.execute(upsert_query, (pattern, len(pattern)))
                print(f"🔄 Pattern Updated: {pattern} (Length: {len(pattern)})")

        # Commit all changes (both the raw data and the patterns)
        conn.commit()
        
        cursor.close()
        conn.close()

        print(f"✅ DB Saved: {clean_value} (Cat: {category})")
        return jsonify({"status": "success", "message": "Data & Patterns saved to DB"}), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
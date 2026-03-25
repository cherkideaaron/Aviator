from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import mysql.connector # Import the connector

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

        # 4. Insert into MySQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        query = "INSERT INTO game_data (timestamp, raw_value, category) VALUES (%s, %s, %s)"
        values = (now, clean_value, category)
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()

        print(f"✅ DB Saved: {clean_value} (Cat: {category})")
        return jsonify({"status": "success", "message": "Data saved to DB"}), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
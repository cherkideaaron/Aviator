from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
# Enable CORS for all domains
CORS(app) 

# This hook forces the server to accept Private Network Access requests
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

@app.route('/save', methods=['POST', 'OPTIONS'])
def save_data():
    # Handle the "preflight" check the browser sends before the actual POST
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.json
        multiplier = data.get('multiplier')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format the line to write
        entry = f"{timestamp} -> {multiplier}\n"
        
        # Append to a .txt file
        with open('aviator_data.txt', 'a') as file:
            file.write(entry)
            
        print(f"✅ Saved to file: {multiplier}")
        return jsonify({"status": "success", "message": "Data saved"}), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(host='127.0.0.1', port=5000)
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import time
from tracker import ResultTracker

app = Flask(__name__)

# Allow all origins and expose Private Network Access headers
CORS(app, resources={r"/*": {"origins": "*"}})

tracker = ResultTracker()

def add_pna_headers(response):
    """Add Private Network Access header required by Chrome when a public
    website (https://eu.crash.aviator.studio) fetches from loopback (127.0.0.1)."""
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response

app.after_request(add_pna_headers)

def categorize_multiplier(multiplier_str):
    """
    CONVERT STRING TO 0, 1, or 2.
    NOTE: You need to define the exact rules here!
    """
    # Remove 'x' or spaces
    clean_str = multiplier_str.replace('x', '').strip()
    try:
        val = float(clean_str)
        # EXAMPLE LOGIC (Adjust to your game's rules):
        if val < 2.0:
            return 0
        elif val >= 10.0:
            return 2
        else:
            return 1
    except ValueError:
        return None

# Handle the OPTIONS preflight that Chrome sends for Private Network Access
@app.route('/save', methods=['OPTIONS', 'POST'])
def save_data():
    if request.method == 'OPTIONS':
        # Respond to PNA preflight
        response = make_response('', 204)
        return response

    data = request.json
    multiplier_str = data.get("multiplier", "")
    
    result_class = categorize_multiplier(multiplier_str)
    
    if result_class is not None:
        timestamp = time.time()
        tracker.process_result(result_class, timestamp)
        
        # Print the cool formatted dropdown data to console
        print(f"--- Just added {result_class} ---")
        print("Groups of 5:", tracker.get_formatted_patterns(5)[:5]) # Show top 5
        print("Groups of 4:", tracker.get_formatted_patterns(4)[:5])
        print("Groups of 3:", tracker.get_formatted_patterns(3)[:5])
        
        return jsonify({"status": "success", "recorded": result_class}), 200
    
    return jsonify({"error": "Invalid multiplier"}), 400

if __name__ == '__main__':
    app.run(port=5000)
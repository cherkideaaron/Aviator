import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def save_cat(cat, val=1.5):
    print(f"Sending category: {cat}")
    r = requests.post(f"{BASE_URL}/save", json={"value": val, "category": cat})
    data = r.json()
    print(f"Response: {data}")
    return data

def test_p3zs_success():
    print("\n--- Testing P3ZS Success (0,0,0,1,1) ---")
    # Reset first? Restarting new6.py resets it.
    save_cat(0)
    save_cat(0)
    save_cat(0)
    save_cat(1) # Triage state
    res = save_cat(1) # Success -> +1
    print(f"P3ZS Diff: {res.get('p3zs_diff')}")

def test_p3zs_fail():
    print("\n--- Testing P3ZS Fail (0,0,0,1,0) ---")
    # Need to clear state or just continue if it resets properly
    # Sequence: 0,0,0,1,0
    save_cat(1) # Break zero streak
    save_cat(0)
    save_cat(0)
    save_cat(0)
    save_cat(1) # Triage state
    res = save_cat(0) # Fail -> -1
    print(f"P3ZS Diff: {res.get('p3zs_diff')}")

def test_distance():
    print("\n--- Testing Distance (1,0,0,2) ---")
    save_cat(1) # Reset distance counter
    save_cat(0)
    save_cat(0)
    res = save_cat(2) # Distance should be 2
    print(f"Good Distance: {res.get('good_distance')}")

if __name__ == "__main__":
    try:
        test_p3zs_success()
        test_p3zs_fail()
        test_distance()
    except Exception as e:
        print(f"Error: {e}")

import json
import os

# Path to the tracking file (assuming it's in the parent directory as shown in metadata)
file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'post_bad_tracking3.txt')

def analyze():
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                print("⚠️ File is empty.")
                return
            data = json.loads(content)
        
        print(f"{'List ID':<10} | {'1s (Wins)':<10} | {'0s (Losses)':<10} | {'Total':<10} | {'Win %':<10}")
        print("-" * 60)
        
        # Sort keys 0-5
        for key in sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else x):
            results = data[key]
            ones = results.count(1)
            zeros = results.count(0)
            total = len(results)
            win_rate = (ones / total * 100) if total > 0 else 0
            
            print(f"{key:<10} | {ones:<10} | {zeros:<10} | {total:<10} | {win_rate:>6.1f}%")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    analyze()

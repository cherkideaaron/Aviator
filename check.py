from collections import Counter
import io

def remove_duplicate_timestamps(file_path):
    seen_timestamps = set()
    cleaned_lines = []
    
    with open(file_path, 'r') as file:
        for line in file:
            line_str = line.strip()
            if not line_str:
                continue
                
            try:
                parts = line_str.split('|')
                timestamp = parts[1].strip()
                
                if timestamp not in seen_timestamps:
                    seen_timestamps.add(timestamp)
                    cleaned_lines.append(line_str)
            except Exception as e:
                cleaned_lines.append(line_str)
                
    with open(file_path, 'w') as file:
        for line in cleaned_lines:
            file.write(line + '\n')
            
    print(f"Cleaned duplicates from {file_path}! Kept {len(cleaned_lines)} unique timestamp events.")

def count_patterns(file_path):
    counter = Counter()

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                parts = line.split('|')
                pattern = parts[0].strip()

                bad_part = parts[2].strip()  # e.g. "bad%=50.0%"
                bad_value = float(bad_part.split('=')[1].replace('%', ''))

                if bad_value != 0.0:
                    counter[pattern] += 1

            except Exception as e:
                print(f"Skipping bad line: {line}")
                continue

    return counter


# 🔹 Usage
file_path = "pattern_events3.txt"  # replace with your file path

# 1. Clean duplicates first
remove_duplicate_timestamps(file_path)

# 2. Count patterns
result = count_patterns(file_path)

# Print specific counts
print("Count of '0, 1, 1':", result.get("0, 1, 1", 0))
print("Count of '0, 1, 0':", result.get("0, 1, 0", 0))
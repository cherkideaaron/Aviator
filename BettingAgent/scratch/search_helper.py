import sys
import os

def search_file(filepath, query):
    encodings = ['utf-16', 'utf-8', 'latin-1']
    content = None
    used_encoding = None
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except Exception:
            continue
            
    if content is None:
        print(f"Could not read {filepath} with any standard encoding.")
        return
        
    lines = content.splitlines()
    matches = []
    for idx, line in enumerate(lines):
        if query.lower() in line.lower():
            matches.append((idx + 1, line))
            
    print(f"=== Found {len(matches)} matches in {filepath} (encoding: {used_encoding}) ===")
    for line_num, line_content in matches[:100]:
        print(f"{line_num}: {line_content}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search_helper.py <filepath> <query>")
    else:
        search_file(sys.argv[1], sys.argv[2])

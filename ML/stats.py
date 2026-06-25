import csv
from collections import defaultdict

file_path = "predictions_log.csv"

win_count = 0
correct_count = 0

win_true = 0
win_false = 0

confidence_stats = defaultdict(lambda: {"correct": 0, "wrong": 0})

consecutive_win_false = 0
max_consecutive_win_false = 0

with open(file_path, "r") as f:
    reader = csv.DictReader(f)

    for row in reader:
        prediction = row["prediction"].strip()
        is_correct = row["is_correct"].strip() == "True"
        confidence = row["confidence"].strip()

        # Count WIN predictions
        if prediction == "WIN":
            win_count += 1

        # Count correct predictions
        if is_correct:
            correct_count += 1

        # WIN + True / False breakdown + streak tracking
        if prediction == "WIN":
            if is_correct:
                win_true += 1
                consecutive_win_false = 0
            else:
                win_false += 1
                consecutive_win_false += 1
                max_consecutive_win_false = max(
                    max_consecutive_win_false,
                    consecutive_win_false
                )
        else:
            consecutive_win_false = 0

        # Confidence stats
        if is_correct:
            confidence_stats[confidence]["correct"] += 1
        else:
            confidence_stats[confidence]["wrong"] += 1


# ---- RESULTS ----
print("===== RESULTS =====")
print("Total WIN predictions:", win_count)
print("Total correct predictions:", correct_count)

print("\nWIN breakdown:")
print("WIN & True:", win_true)
print("WIN & False:", win_false)

print("\nMax consecutive WIN & False streak:", max_consecutive_win_false)

print("\nConfidence Analysis:")
for conf, stats in confidence_stats.items():
    total = stats["correct"] + stats["wrong"]
    accuracy = (stats["correct"] / total * 100) if total > 0 else 0
    print(f"{conf}: Correct={stats['correct']}, Wrong={stats['wrong']}, Accuracy={accuracy:.2f}%")
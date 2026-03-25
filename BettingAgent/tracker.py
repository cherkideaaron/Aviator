import time

class ResultTracker:
    def __init__(self):
        # Overall Stats
        self.absolute_round = 0
        self.all_time_counts = {0: 0, 1: 0, 2: 0}
        
        # Difference & Event Tracking
        self.current_event_counts = {0: 0, 1: 0, 2: 0}
        self.relative_round = 0
        self.cooldown_rounds_remaining = 5 # Starts needing 5 rounds
        self.active_event = None
        self.event_history = []
        
        # Pattern Tracking (Sliding Window)
        self.recent_history = []
        self.patterns = {3: {}, 4: {}, 5: {}}
        
        # Tracking '2's
        self.last_two_time = None
        self.last_two_round = None
        self.two_history = [] # Stores dicts of time_diff and round_diff

    def process_result(self, result: int, timestamp: float):
        """Main pipeline triggered every time a new result comes in."""
        self.absolute_round += 1
        self.all_time_counts[result] += 1
        self.recent_history.append(str(result))
        
        # 1. Update Patterns
        self._update_patterns()
        
        # 2. Track '2's
        if result == 2:
            self._track_two(timestamp)
            
        # 3. Imbalance & Convergence Logic
        self._handle_difference_logic(result, timestamp)

    def _track_two(self, timestamp):
        """Handles the tracking of the rare '2' results."""
        if self.last_two_time is not None:
            time_diff_seconds = timestamp - self.last_two_time
            round_diff = self.absolute_round - self.last_two_round
            
            # Save the gap between 2s
            self.two_history.append({
                "time_difference_sec": time_diff_seconds,
                "round_difference": round_diff,
                "timestamp": timestamp
            })
            
        # Reset trackers for the next 2
        self.last_two_time = timestamp
        self.last_two_round = self.absolute_round

    def _update_patterns(self):
        """Updates the 3, 4, and 5 length sliding windows."""
        # Keep buffer small to save memory
        if len(self.recent_history) > 5:
            self.recent_history.pop(0)
            
        current_str = "".join(self.recent_history)
        
        # Check sizes 3, 4, and 5
        for size in [3, 4, 5]:
            if len(current_str) >= size:
                pattern = current_str[-size:]
                if pattern not in self.patterns[size]:
                    self.patterns[size][pattern] = 0
                self.patterns[size][pattern] += 1

    def get_formatted_patterns(self, size):
        """Returns sorted patterns format: '000 10', '010 7'."""
        if size not in self.patterns:
            return []
        
        # Sort by frequency (highest first)
        sorted_patterns = sorted(self.patterns[size].items(), key=lambda x: x[1], reverse=True)
        
        # Format as strings
        return [f"{pat} {count}" for pat, count in sorted_patterns]

    def _handle_difference_logic(self, result, timestamp):
        """Handles the 5 round cooldown and difference tracking."""
        if self.cooldown_rounds_remaining > 0:
            self.cooldown_rounds_remaining -= 1
            if self.cooldown_rounds_remaining == 0:
                # Cooldown finished, prep for new tracking phase
                self.relative_round = 0
                self.current_event_counts = {0: 0, 1: 0, 2: 0}
            return

        # Tracking is active
        self.relative_round += 1
        self.current_event_counts[result] += 1
        
        c0 = self.current_event_counts[0]
        c1 = self.current_event_counts[1]
        c2 = self.current_event_counts[2]
        
        current_difference = (c1 + c2) - c0
        
        # Event Lifecycle Management
        if self.active_event is None and current_difference != 0:
            # Start a new event
            self.active_event = {
                "start_time": timestamp,
                "start_round": self.absolute_round,
                "max_positive": current_difference if current_difference > 0 else 0,
                "max_negative": current_difference if current_difference < 0 else 0
            }
        elif self.active_event is not None:
            # Update max differences
            if current_difference > self.active_event["max_positive"]:
                self.active_event["max_positive"] = current_difference
            if current_difference < self.active_event["max_negative"]:
                self.active_event["max_negative"] = current_difference
                
            # Check for convergence
            if current_difference == 0:
                self.active_event["end_time"] = timestamp
                self.active_event["end_round"] = self.absolute_round
                self.active_event["rounds_to_converge"] = self.relative_round
                
                # Save and reset
                self.event_history.append(self.active_event)
                self.active_event = None
                self.cooldown_rounds_remaining = 5 # Start 5 round cooldown
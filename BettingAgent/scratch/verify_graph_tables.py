import mysql.connector
import sys
import os
from datetime import date, datetime

# Add parent directory to sys.path so we can import new8
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from new8 import db_config, GRAPH_CONFIGS, initialize_graph_tables, repopulate_all_graphs
except ImportError as e:
    print("Could not import new8:", e)
    sys.exit(1)

def verify_tables():
    print("Connecting to MySQL...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # 1. Initialize tables
    print("Running initialize_graph_tables...")
    initialize_graph_tables(conn)
    
    # 2. Check if tables actually exist
    print("Verifying table existence...")
    cursor.execute("SHOW TABLES")
    existing_tables = [t[0] for t in cursor.fetchall()]
    
    missing_tables = []
    for cfg in GRAPH_CONFIGS:
        tname = cfg['table_name']
        if tname not in existing_tables:
            missing_tables.append(tname)
            
    if missing_tables:
        print(f"FAIL: The following tables are missing: {missing_tables}")
        conn.close()
        sys.exit(1)
    else:
        print("PASS: All 17 graph tables exist in database.")
        
    # 3. Check schema of a representative table (e.g., graph_p_odd_1_5)
    t_check = "graph_p_odd_1_5"
    cursor.execute(f"DESCRIBE {t_check}")
    columns = {col[0]: col[1] for col in cursor.fetchall()}
    
    expected_columns = [
        'id', 'game_id', 'timestamp', 'date', 'raw_value', 'balance', 
        'balance_change', 'is_bet', 'is_win', 'accumulated_wins', 
        'accumulated_losses', 'win_streak', 'loss_streak'
    ]
    
    missing_columns = [c for c in expected_columns if c not in columns]
    if missing_columns:
        print(f"FAIL: Table {t_check} is missing columns: {missing_columns}")
        conn.close()
        sys.exit(1)
    else:
        print(f"PASS: Table {t_check} has all expected columns.")
        
    # 4. Check if date column has an index
    cursor.execute(f"SHOW INDEX FROM {t_check}")
    indexes = [idx[2] for idx in cursor.fetchall()]
    if 'date' in indexes:
        print("PASS: Date column has an index.")
    else:
        print("FAIL: Date column does NOT have an index.")
        conn.close()
        sys.exit(1)
        
    # 5. Trigger manual repopulate to test sync and simulation logic
    print("Running history repopulate (repopulate_all_graphs)...")
    repopulate_all_graphs(conn)
    
    # 6. Verify mathematical consistency of simulation and validity of date
    cursor.execute("SELECT game_id, timestamp, date, raw_value, balance, balance_change, is_bet, is_win, accumulated_wins, accumulated_losses, win_streak, loss_streak FROM graph_p_odd_2_0 ORDER BY id ASC")
    rows = cursor.fetchall()
    
    if not rows:
        print("WARNING: No data in graph_p_odd_2_0. Let's insert a mock game to verify.")
        # Insert mock game into game_data
        cursor.execute("INSERT INTO game_data (timestamp, raw_value, category) VALUES (NOW(), 2.50, 1)")
        mock_game_id = cursor.lastrowid
        cursor.execute("INSERT INTO game_data (timestamp, raw_value, category) VALUES (NOW(), 1.50, 0)")
        mock_game_id_2 = cursor.lastrowid
        conn.commit()
        
        print("Re-running repopulation after mock insert...")
        repopulate_all_graphs(conn)
        
        cursor.execute("SELECT game_id, timestamp, date, raw_value, balance, balance_change, is_bet, is_win, accumulated_wins, accumulated_losses, win_streak, loss_streak FROM graph_p_odd_2_0 ORDER BY id ASC")
        rows = cursor.fetchall()
        
        # Clean up mock data afterwards
        cursor.execute(f"DELETE FROM game_data WHERE id IN ({mock_game_id}, {mock_game_id_2})")
        conn.commit()
        
    print(f"Verifying {len(rows)} simulated rows...")
    
    initial_balance = 20000.00
    bet_size = 0.2
    
    running_balance = initial_balance
    running_acc_wins = 0
    running_acc_losses = 0
    running_w_streak = 0
    running_l_streak = 0
    
    math_failures = 0
    for idx, r in enumerate(rows):
        game_id, timestamp, dt_val, raw_value, balance, balance_change, is_bet, is_win, acc_wins, acc_losses, w_streak, l_streak = r
        raw_value = float(raw_value)
        balance = float(balance)
        balance_change = float(balance_change)
        
        # Verify date matches timestamp
        expected_date = timestamp.date() if isinstance(timestamp, datetime) else timestamp
        if dt_val != expected_date:
            print(f"Row {idx}: date mismatch. Got {dt_val} (type {type(dt_val)}), expected {expected_date}")
            math_failures += 1
        
        # graph_p_odd_2_0 has odd=2.0 and skip_every=0 (continuous betting)
        expected_is_bet = 1
        expected_is_win = 1 if raw_value >= 2.0 else 0
        expected_change = round(bet_size * (2.0 - 1), 4) if expected_is_win else -bet_size
        running_balance = round(running_balance + expected_change, 4)
        
        if expected_is_win:
            running_acc_wins += 1
            running_w_streak += 1
            running_l_streak = 0
        else:
            running_acc_losses += 1
            running_l_streak += 1
            running_w_streak = 0
            
        # Compare
        if is_bet != expected_is_bet:
            print(f"Row {idx}: is_bet mismatch. Got {is_bet}, expected {expected_is_bet}")
            math_failures += 1
        if is_win != expected_is_win:
            print(f"Row {idx}: is_win mismatch. Got {is_win}, expected {expected_is_win}")
            math_failures += 1
        if abs(balance_change - expected_change) > 1e-4:
            print(f"Row {idx}: change mismatch. Got {balance_change}, expected {expected_change}")
            math_failures += 1
        if abs(balance - running_balance) > 1e-4:
            print(f"Row {idx}: balance mismatch. Got {balance}, expected {running_balance}")
            math_failures += 1
        if acc_wins != running_acc_wins:
            print(f"Row {idx}: acc_wins mismatch. Got {acc_wins}, expected {running_acc_wins}")
            math_failures += 1
        if acc_losses != running_acc_losses:
            print(f"Row {idx}: acc_losses mismatch. Got {acc_losses}, expected {running_acc_losses}")
            math_failures += 1
        if w_streak != running_w_streak:
            print(f"Row {idx}: w_streak mismatch. Got {w_streak}, expected {running_w_streak}")
            math_failures += 1
        if l_streak != running_l_streak:
            print(f"Row {idx}: l_streak mismatch. Got {l_streak}, expected {running_l_streak}")
            math_failures += 1
            
    if math_failures == 0:
        print("PASS: Mathematical simulation and date checks are completely correct!")
    else:
        print(f"FAIL: Simulation/date checks found {math_failures} errors.")
        conn.close()
        sys.exit(1)
        
    # Since they want to start fresh from 0, clear tables again
    print("Clearing graph tables after validation to start fresh from 0...")
    for cfg in GRAPH_CONFIGS:
        cursor.execute(f"DELETE FROM {cfg['table_name']}")
    conn.commit()
    print("Graph tables cleared successfully.")
    
    conn.close()
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_tables()

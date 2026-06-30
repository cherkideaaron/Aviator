"""
=============================================================
  Real-Time Balance Predictor — MySQL + Random Forest
=============================================================
  1. Connects to your MySQL database
  2. Loads historical data & trains Random Forest
  3. Watches for new rows every few seconds
  4. Predicts WIN/LOSS for the NEXT round
  5. Fine-tunes (retrains) the model as new results come in

  HOW TO RUN:
    pip install scikit-learn pandas numpy pymysql sqlalchemy
    python realtime_predictor.py
=============================================================
"""

import time
from collections import deque
import warnings
import numpy as np
import pandas as pd
import pymysql
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score
import joblib
import os

warnings.filterwarnings('ignore')

# ── Bet action (pyautogui click + martingale state) ───────────────────
try:
    from bet_action import BetAction
    _BET_ACTION_AVAILABLE = True
except ImportError as _e:
    _BET_ACTION_AVAILABLE = False
    print(f'⚠️  bet_action.py not found — running in prediction-only mode ({_e})')

# ─────────────────────────────────────────────────────────────
#  ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     '127.0.0.1',
    'port':     3306,
    'user':     'root',
    'password': 'Aaron@123',
    'database': 'aviator_db',
}

# Which graph table to predict for.
# Options: graph_p_odd_1_5, graph_p_odd_2_0, graph_p_odd_3_0,
#          graph_p_odd_4_0, graph_p_odd_5_0,
#          graph_s0_odd_1_5, graph_s1_odd_2_0 ... etc.
# Recommendation: start with graph_p_odd_2_0 (2x threshold, every round)
TABLE_NAME      = 'graph_p_odd_2_0'
ODD_THRESHOLD   = 2.0    # must match the table you picked above

POLL_INTERVAL   = 0.2    # seconds between checks for new rows (fast, event-driven)
RETRAIN_EVERY   = 30     # retrain after every N new rows
MODEL_PATH      = 'rf_model.joblib'
PREDICTIONS_LOG = 'predictions_log.csv'
MIN_ROWS_TRAIN  = 100    # minimum rows needed before first training

# ─────────────────────────────────────────────────────────────
#  Columns to DROP from features (outcomes / identifiers)
# ─────────────────────────────────────────────────────────────
DROP_COLS = [
    'id', 'game_id', 'timestamp', 'date',
    'is_win',          # this is the TARGET — never use as feature
    'balance',         # cumulative — leaks future
    'balance_change',  # same as is_win signal — leaks target
    'accumulated_wins', 'accumulated_losses',
    'win_streak', 'loss_streak',
    'raw_value',       # current round result — use only as lagged feature
    # game_data joined columns:
    'gd_id', 'gd_timestamp', 'gd_raw_value', 'gd_category',
    'pzs_source',
]


# ─────────────────────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────────────────────
def get_connection():
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def fetch_all_data():
    """
    Fetch graph table joined with game_data for richer features.
    game_data carries tracker signals (current_diff, p3zs_diff, etc.)
    that are computed BEFORE the round result — no leakage.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    g.id, g.game_id, g.timestamp, g.date,
                    g.raw_value, g.is_bet, g.is_win,
                    g.balance, g.balance_change,
                    g.accumulated_wins, g.accumulated_losses,
                    g.win_streak, g.loss_streak,
                    -- richer signals from game_data (computed pre-round)
                    COALESCE(gd.current_diff,   0) AS current_diff,
                    COALESCE(gd.max_diff,       0) AS max_diff,
                    COALESCE(gd.pzs_diff,       0) AS pzs_diff,
                    COALESCE(gd.pzs_0012_diff,  0) AS pzs_0012_diff,
                    COALESCE(gd.pzs_12012_diff, 0) AS pzs_12012_diff,
                    COALESCE(gd.good_distance,  0) AS good_distance,
                    COALESCE(gd.p3zs_diff,      0) AS p3zs_diff,
                    gd.category AS gd_category
                FROM `{TABLE_NAME}` g
                LEFT JOIN game_data gd ON gd.id = g.game_id
                WHERE g.is_bet = 1
                ORDER BY g.timestamp ASC
            """)
            rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()


def fetch_rows_since(last_id):
    """Fetch all rows added after last_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    g.id, g.game_id, g.timestamp, g.date,
                    g.raw_value, g.is_bet, g.is_win,
                    g.balance, g.balance_change,
                    g.accumulated_wins, g.accumulated_losses,
                    g.win_streak, g.loss_streak,
                    COALESCE(gd.current_diff,   0) AS current_diff,
                    COALESCE(gd.max_diff,       0) AS max_diff,
                    COALESCE(gd.pzs_diff,       0) AS pzs_diff,
                    COALESCE(gd.pzs_0012_diff,  0) AS pzs_0012_diff,
                    COALESCE(gd.pzs_12012_diff, 0) AS pzs_12012_diff,
                    COALESCE(gd.good_distance,  0) AS good_distance,
                    COALESCE(gd.p3zs_diff,      0) AS p3zs_diff,
                    gd.category AS gd_category
                FROM `{TABLE_NAME}` g
                LEFT JOIN game_data gd ON gd.id = g.game_id
                WHERE g.id > %s AND g.is_bet = 1
                ORDER BY g.timestamp ASC
            """, (last_id,))
            rows = cursor.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
#  Feature Engineering (leak-free)
# ─────────────────────────────────────────────────────────────
def engineer_features(df):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # ── Time features ─────────────────────────────────────────
    df['hour']        = df['timestamp'].dt.hour
    df['minute']      = df['timestamp'].dt.minute
    df['time_of_day'] = df['hour'] + df['minute'] / 60
    df['day_of_week'] = df['timestamp'].dt.dayofweek

    # ── Lag features on the multiplier value (past rounds only) ──
    for lag in [1, 2, 3, 5, 10]:
        df[f'raw_lag{lag}']    = df['raw_value'].shift(lag)
        df[f'is_win_lag{lag}'] = df['is_win'].shift(lag)

    # ── Rolling stats on raw_value (all shifted by 1 to avoid leak) ──
    for window in [3, 5, 10, 20]:
        shifted = df['raw_value'].shift(1)
        df[f'roll_mean_{window}']    = shifted.rolling(window).mean()
        df[f'roll_std_{window}']     = shifted.rolling(window).std()
        df[f'roll_max_{window}']     = shifted.rolling(window).max()
        df[f'roll_min_{window}']     = shifted.rolling(window).min()
        # win rate at this specific threshold
        win_shifted = df['is_win'].shift(1)
        df[f'roll_wr_{window}']      = win_shifted.rolling(window).mean()

    # ── Tracker signals as-is (already computed pre-round, no shift needed) ──
    # current_diff, max_diff, pzs_diff, p3zs_diff, good_distance, gd_category
    # These come from game_data and represent state BEFORE the outcome.

    # ── Lag on tracker signals ────────────────────────────────
    for sig in ['current_diff', 'p3zs_diff', 'good_distance', 'gd_category']:
        for lag in [1, 2, 3]:
            df[f'{sig}_lag{lag}'] = df[sig].shift(lag)

    df = df.dropna().reset_index(drop=True)
    return df


def get_feature_cols(df):
    return [c for c in df.columns if c not in DROP_COLS]


# ─────────────────────────────────────────────────────────────
#  Model Training
# ─────────────────────────────────────────────────────────────
def train_model(df, verbose=True):
    df_feat = engineer_features(df)
    feature_cols = get_feature_cols(df_feat)

    X = df_feat[feature_cols].values
    y = df_feat['is_win'].values.astype(int)

    if len(np.unique(y)) < 2:
        print('   ⚠️  Only one class in data — skipping training.')
        return None, feature_cols

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,          # keep shallow to avoid overfitting
        min_samples_leaf=8,
        class_weight='balanced',  # handle imbalance at high odds
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)

    if verbose:
        # Time-based validation split — use last 20% as test
        split = int(len(X) * 0.8)
        if split < len(X) - 5:
            acc = accuracy_score(y[split:], model.predict(X[split:]))
            baseline = max(y[split:].mean(), 1 - y[split:].mean())
            print(f'   📊 Holdout accuracy: {acc:.2%}  (baseline: {baseline:.2%})')

            # Feature importances — top 8
            importances = sorted(
                zip(feature_cols, model.feature_importances_),
                key=lambda x: x[1], reverse=True
            )[:8]
            print('   🔍 Top features:')
            for name, imp in importances:
                bar = '█' * int(imp * 100)
                print(f'      {name:<30} {imp:.3f}  {bar}')

    return model, feature_cols


# ─────────────────────────────────────────────────────────────
#  Prediction for the NEXT round
# ─────────────────────────────────────────────────────────────
def predict_next(model, feature_cols, history_df):
    """
    Given recent history, predict whether the NEXT round wins.
    Needs at least 20 rows for rolling features to stabilize.
    """
    df_feat = engineer_features(history_df)
    if df_feat.empty:
        return None, None, None

    # Use available features only (some may not be in this window)
    available = [c for c in feature_cols if c in df_feat.columns]
    last_row  = df_feat[available].iloc[-1:]
    prob_win  = model.predict_proba(last_row)[0][1]
    pred      = 'WIN' if prob_win >= 0.5 else 'LOSS'

    distance = abs(prob_win - 0.5)
    if distance >= 0.20:
        conf = '🔥 Very High'
    elif distance >= 0.12:
        conf = '✅ High'
    elif distance >= 0.06:
        conf = '🟡 Medium'
    else:
        conf = '🔴 Low (skip this one)'

    return pred, prob_win, conf


# ─────────────────────────────────────────────────────────────
#  Display helpers
# ─────────────────────────────────────────────────────────────
def print_header():
    print()
    print('=' * 65)
    print('   🤖  REAL-TIME BALANCE PREDICTOR')
    print('=' * 65)
    print(f'   Table     : {TABLE_NAME}')
    print(f'   Threshold : {ODD_THRESHOLD}x  (WIN = result >= {ODD_THRESHOLD})')
    print(f'   Poll      : every {POLL_INTERVAL}s (near-instant)')
    print(f'   Retrain   : every {RETRAIN_EVERY} new rounds')
    print('=' * 65)
    print()


def print_prediction(row_id, pred, prob, conf, actual=None, actual_raw=None, recent_snap=None):
    ts      = datetime.now().strftime('%H:%M:%S')
    bar_len = int(prob * 20)
    bar     = '█' * bar_len + '░' * (20 - bar_len)

    print(f'\n[{ts}] Round #{row_id}')
    print(f'  Prediction : {"🟢 WIN" if pred == "WIN" else "🔴 LOSS"}')
    print(f'  Win Prob   : {prob:.1%}  [{bar}]')
    print(f'  Confidence : {conf}')

    pct_5 = pct_10 = pct_20 = 0
    bits = ""
    wins_in_10 = 0

    if recent_snap is not None:
        last5_snap  = recent_snap[-5:]  if len(recent_snap) >= 5 else recent_snap
        last10_snap = recent_snap[-10:] if len(recent_snap) >= 10 else recent_snap
        last20_snap = recent_snap[-20:] if len(recent_snap) >= 20 else recent_snap
        
        pct_5  = (sum(last5_snap)  / len(last5_snap) * 100)  if last5_snap  else 0
        pct_10 = (sum(last10_snap) / len(last10_snap) * 100) if last10_snap else 0
        pct_20 = (sum(last20_snap) / len(last20_snap) * 100) if last20_snap else 0
        
        bits = ''.join(str(b) for b in last10_snap)
        wins_in_10 = sum(last10_snap)
        
        print(f'  Recent     : {pct_5:.0f}% (last 5), {pct_10:.0f}% (last 10), {pct_20:.0f}% (last 20)')
        print(f'  Last 10    : {bits}  ({wins_in_10}/10 wins)')

    if actual is not None:
        actual_str = 'WIN' if actual == 1 else 'LOSS'
        correct    = (pred == actual_str)
        print(f'  Actual     : {"🟢" if actual == 1 else "🔴"} {actual_str}  {"✅ CORRECT" if correct else "❌ WRONG"}')

        # Log to CSV file
        log_exists = os.path.exists(PREDICTIONS_LOG)
        with open(PREDICTIONS_LOG, 'a', encoding='utf-8') as f:
            if not log_exists:
                f.write('timestamp,row_id,prediction,probability,confidence,actual,is_correct,last10,wins_in_last10\n')

            conf_text = " ".join(conf.split(" ")[1:])
            f.write(f'{ts},{row_id},{pred},{prob:.4f},{conf_text},{actual_str},{correct},{bits},{wins_in_10}\n')

        # Log WIN predictions to text file
        if pred == 'WIN' and actual_raw is not None:
            actual_20  = 'win' if actual_raw >= 2.0 else 'lose'
            conf_text  = " ".join(conf.split(" ")[1:])
            with open('win_predictions_detail.txt', 'a', encoding='utf-8') as wf:
                wf.write(
                    f"Predicted (win) | Raw Value: {actual_raw:.2f} | Actual: {actual_str.lower()} "
                    f"| Actual 2.0: {actual_20} | Prob: {prob:.1%} | Conf: {conf_text} "
                    f"| Last 5: {pct_5:.0f}% | Last 10: {pct_10:.0f}% | Last 20: {pct_20:.0f}%\n"
                )


# ─────────────────────────────────────────────────────────────
#  Main Loop
# ─────────────────────────────────────────────────────────────
def main():
    print_header()

    # ── Step 1: Wait for enough historical data ──────────────────
    print('📂 Loading historical data...')
    
    while True:
        try:
            df_all = fetch_all_data()
            current_rows = len(df_all)
            
            if current_rows >= MIN_ROWS_TRAIN:
                print(f'\n   ✅ Reached {current_rows}/{MIN_ROWS_TRAIN} bet rows! Proceeding to train...')
                break
                
            print(f'   ⏳ Waiting for data ({current_rows}/{MIN_ROWS_TRAIN} rows)... Make sure new8.py is running.', end='\r')
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print('\n🛑 Stopped waiting.')
            return
        except Exception as e:
            print(f'\n⚠️  Database error: {e}')
            time.sleep(POLL_INTERVAL)

    print(f'   ✅ Loaded {len(df_all)} bet rows')
    win_pct = df_all['is_win'].mean()
    print(f'   📈 Historical win rate: {win_pct:.1%}  (baseline to beat)')
    print()
    print('🏋️  Training model...')
    model, feature_cols = train_model(df_all, verbose=True)

    if model is None:
        print('   ❌ Training failed — not enough class variety yet.')
        return

    joblib.dump(model,        MODEL_PATH)
    joblib.dump(feature_cols, 'feature_cols.joblib')
    print(f'   💾 Model saved to {MODEL_PATH}')
    print()

    # ── Step 2: Set state ─────────────────────────────────────
    last_id        = int(df_all['id'].max())
    new_rows_count = 0
    history_df     = df_all.copy()
    pending        = {}      # row_id → (pred, prob, conf, last10_snapshot)
    correct_count  = 0
    total_judged   = 0

    # Rolling window of last 20 actual is_win results (1=win, 0=loss)
    # Seed from the tail of historical data
    recent_results = deque(
        [int(v) for v in df_all['is_win'].tail(20).tolist()],
        maxlen=20
    )

    # ── Bet action (martingale + pyautogui click) ──────────────────
    bet_agent = BetAction() if _BET_ACTION_AVAILABLE else None
    # Track which pending row_ids had a bet placed so we can record result
    # Maps  next_id → True  (a bet was placed for that round)
    bet_pending = {}   # row_id → True

    if bet_agent:
        print(f'🎰 Bet agent active — current bet: {bet_agent.current_bet}')
    else:
        print('⚠️  Running WITHOUT bet agent (prediction-only mode)')
    # ──────────────────────────────────────────────────────────────

    print(f'👀 Watching {TABLE_NAME} (last ID: {last_id})...')
    print('   Press Ctrl+C to stop.\n')
    print('-' * 65)

    # ── Step 3: Real-time loop ────────────────────────────────
    while True:
        try:
            new_df = fetch_rows_since(last_id)

            if not new_df.empty:
                for _, row in new_df.iterrows():
                    row_id = int(row['id'])

                    if row_id in pending:
                        pred, prob, conf, recent_snap = pending[row_id]
                        actual     = int(row['is_win'])
                        actual_raw = float(row['raw_value'])
                        print_prediction(row_id, pred, prob, conf, actual, actual_raw, recent_snap)
                        correct_count += int(pred == ('WIN' if actual == 1 else 'LOSS'))
                        total_judged  += 1
                        if total_judged > 0:
                            running_acc = correct_count / total_judged
                            print(f'  Running Acc: {running_acc:.1%}  ({correct_count}/{total_judged})')
                        # Update recent_results AFTER the result is known
                        recent_results.append(actual)

                        # ── Martingale: record result if a bet was placed ───
                        if bet_agent and bet_pending.pop(row_id, False):
                            is_win = (actual == 1)
                            print(
                                f'  💰 Bet result for #{row_id}: {"WIN ✅" if is_win else "LOSS ❌"} '
                                f'(raw={actual_raw:.2f}x) — updating martingale state',
                                flush=True
                            )
                            bet_agent.record_result(
                                is_win=is_win,
                                odd_threshold=ODD_THRESHOLD   # 2.0x — used to calc win payout
                            )
                            print(
                                f'  💰 Next bet → real: {bet_agent.current_bet}  '
                                f'sim: {bet_agent.current_sim_bet}',
                                flush=True
                            )
                        # ──────────────────────────────────────────────────

                        del pending[row_id]
                    else:
                        history_df = pd.concat(
                            [history_df, pd.DataFrame([row])],
                            ignore_index=True
                        )
                        if len(history_df) >= 25:
                            result = predict_next(model, feature_cols, history_df)
                            if result[0] is not None:
                                pred, prob, conf = result
                                next_id = row_id + 1
                                # Snapshot recent_results at the moment prediction is made
                                recent_snap = list(recent_results)
                                pending[next_id] = (pred, prob, conf, recent_snap)
                                print_prediction(
                                    f'{row_id} → predicting #{next_id}',
                                    pred, prob, conf, recent_snap=recent_snap
                                )

                                # ── Click bet NOW if prediction is WIN ────────
                                if bet_agent and pred == 'WIN':
                                    print(
                                        f'  🎰 WIN predicted for round #{next_id} '
                                        f'(prob={prob:.1%}) — placing bet!',
                                        flush=True
                                    )
                                    bet_agent.place_bet()
                                    bet_pending[next_id] = True
                                # ─────────────────────────────────────────────

                    new_rows_count += 1
                    last_id = max(last_id, row_id)

                # ── Retrain ───────────────────────────────────
                if new_rows_count >= RETRAIN_EVERY:
                    print(f'\n🔄 Retraining on {len(history_df)} total rows...')
                    model, feature_cols = train_model(history_df, verbose=True)
                    if model:
                        joblib.dump(model, MODEL_PATH)
                        print(f'   ✅ Model updated!\n')
                    new_rows_count = 0

            else:
                print(
                    f'   ⏳ [{datetime.now().strftime("%H:%M:%S")}] '
                    f'Waiting for new rounds in {TABLE_NAME}...',
                    end='\r'
                )

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print('\n\n🛑 Stopped.')
            if total_judged > 0:
                print(f'   Final accuracy: {correct_count/total_judged:.1%}  ({correct_count}/{total_judged})')
            break

        except Exception as e:
            print(f'\n⚠️  Error: {e}')
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()

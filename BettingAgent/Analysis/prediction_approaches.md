# 10 Rule-Based Approaches to Predict Results > 1.21

> **Context**: All approaches operate on a stream of incoming multiplier results.
> Thresholds used: `< 1.21` (hard low / hit), `< 2.0` (soft low), `>= 1.21` (target / good result).
> The goal is to decide **when to click** (predict next result will be >= 1.21).

---

## Approach 1 — Gap Rhythm Tracker (Your Current Baseline)
**Concept**: Measure the round-gap between consecutive `< 1.21` results.
If the gap is >= 3, schedule a click N rounds after the last hit.

**Enhancement**:
- Instead of using a fixed gap, **track a rolling average of the last 5 gaps**.
- Use the average as the predicted next interval.
- Only fire if the predicted interval has been consistent (low variance across last 5 gaps).

**State to track**: `last_hit_id`, `gap_history[]` (last 5 gaps), `gap_mean`, `gap_variance`

**Click condition**:
```
rounds_since_last_hit == round(gap_mean)
AND gap_variance < THRESHOLD (e.g. 2.0)
```

---

## Approach 2 — Consecutive Low Streak Cooldown
**Concept**: When you detect a long streak of results all `< 2.0`, the system is in a "cold cluster."
After the cluster breaks (first result `>= 2.0`), a "warm window" opens.

**Observation**: After N consecutive lows, the market tends to produce a good result soon after.

**State to track**: `consecutive_low_count`, `in_warm_window`, `warm_window_rounds_left`

**Click condition**:
```
consecutive_low_count >= 5
AND current result breaks the streak (>= 2.0)
→ open warm window for next 3 rounds, click on each
```

**Avoid**: clicking if `consecutive_low_count` is still rising (cold streak hasn't ended).

---

## Approach 3 — Density Inversion Window
**Concept**: Calculate the density of `< 1.21` results in a rolling window of W rounds.
When density drops below a threshold, it signals a "safe" period.

**Logic**:
- High density → too many lows → dangerous, skip.
- Low density → few recent lows → likely safe to click.

**State to track**: `rolling_window[]` (last 20 results), `hit_density = count(< 1.21) / W`

**Click condition**:
```
hit_density < 0.20   (fewer than 20% of last 20 rounds were < 1.21)
```

**Bonus**: Use two windows (short=10, long=30) and only click when BOTH are below threshold.

---

## Approach 4 — Dual Zone Score (Soft + Hard Lows)
**Concept**: Distinguish between two danger zones:
- `< 1.21` = hard hit (dangerous)
- `1.21 – 2.0` = soft zone (marginal)
- `>= 2.0` = good outcome

Assign a weighted danger score to recent history:
```
score = (count of hard hits × 2) + (count of soft zone × 1)
```
Higher score = more dangerous. Only click when score is low enough.

**State to track**: `danger_score` (rolling window of last 15 results)

**Click condition**:
```
danger_score < 8   (out of max 30 for window of 15)
```

---

## Approach 5 — Periodicity Detector (Cycle Length Estimation)
**Concept**: `< 1.21` results don't appear randomly — they tend to cluster in cycles.
Estimate the **period** of the cycle by tracking timestamps (or round IDs) of all hits.

**Method**:
- Collect last 10 hit round IDs.
- Compute differences (gaps) between them.
- Find the **modal gap** (most common gap value) — this is your estimated period.
- Predict the next hit at `last_hit_id + modal_gap`.
- Click at `last_hit_id + modal_gap - 1` (one round before predicted next hit).

**State to track**: `hit_id_history[]`, `modal_gap`

**Click condition**:
```
current_round_id == last_hit_id + modal_gap - 1
AND modal_gap appeared >= 3 times in history
```

---

## Approach 6 — Momentum Score (Exponential Recency Weighting)
**Concept**: Recent results matter more than older ones.
Apply exponential decay to each result and compute a weighted "danger momentum."

**Formula**:
```
momentum = Σ (is_hit[i] × decay^i)   for i in [0, N]
decay = 0.7 (configurable)
is_hit = 1 if result < 1.21 else 0
```
A low momentum means the recent past is clean → safe to bet.

**State to track**: `momentum` (recalculated every round)

**Click condition**:
```
momentum < 0.3
```

**Benefit**: Automatically reacts faster to recent clusters without needing manual window sizes.

---

## Approach 7 — Regime Detection (Cold vs. Warm State Machine)
**Concept**: Define two regimes: **COLD** and **WARM**.
The system starts NEUTRAL and transitions based on observed density.

```
NEUTRAL → COLD   : if 4 out of last 6 results are < 2.0
COLD    → NEUTRAL: if 3 consecutive results are >= 2.0
NEUTRAL → WARM   : if last 5 results are >= 2.0 (or gap >= 6)
WARM    → NEUTRAL: as soon as a < 1.21 result appears
```

**Click condition**:
```
current_regime == WARM
```

**Benefit**: Prevents clicking during cold streaks entirely. The state machine gives you a clear qualitative picture of what the market is doing.

---

## Approach 8 — Pattern Sequence Voting
**Concept**: Track sequences of binary results (0 = bad, 1 = good) for the last N rounds.
Look up that sequence in a historical frequency table to see how often it was followed by a `1`.

**Implementation**:
- This is exactly what your `all_patterns` table already does!
- But instead of using it for display only, use it as a live click signal.
- Query probabilities for pattern lengths 3, 4, and 5.
- Each match casts a "vote": 1 vote if P(next=good) > 60%.

**Click condition**:
```
votes >= 2   (at least 2 out of 3 pattern lengths predict a good result)
AND each agreeing pattern has P > 60%
```

---

## Approach 9 — Drought Timer (Time Since Last Good Result)
**Concept**: After a long drought (many consecutive rounds without a `>= 2.0` result),
statistically the next good result becomes "overdue."

**State to track**: `rounds_since_last_good` (you already have this as `good_distance`!)

**Click condition**:
```
rounds_since_last_good >= DROUGHT_THRESHOLD (e.g. 6)
AND current result is NOT < 1.21  (don't click immediately after a bad hit)
```

**Enhancement**: Combine with Approach 3 (density check) — only click if drought is long AND density is low. A long drought during high density could mean a very cold streak; wait for the density to improve first.

---

## Approach 10 — Multi-Signal Consensus Gate
**Concept**: Don't rely on any single rule. Instead, define 4–5 individual signals and only
click when a **minimum number of them agree**.

| Signal | Description | Vote = YES if... |
|--------|-------------|-----------------|
| Gap Signal | Round gap >= modal gap | On schedule |
| Density Signal | Rolling density of hits | < 20% in last 20 |
| Streak Signal | Consecutive lows broken | Streak ended AND was >= 4 |
| Drought Signal | Rounds since last good result | >= 5 |
| Momentum Signal | Exponential momentum score | < 0.35 |

**Click condition**:
```
consensus_votes >= 3   (3 out of 5 signals say YES)
```

**Benefit**: Very robust. Individual noisy signals cancel each other out. You can tune each
threshold independently without breaking the whole system.

---

## Summary Table

| # | Name | Key Variable | Best When |
|---|------|-------------|-----------|
| 1 | Gap Rhythm | Gap mean + variance | Gaps are consistent |
| 2 | Consecutive Low Cooldown | Streak count | Clear cold/warm bursts exist |
| 3 | Density Inversion Window | Hit density % | Smooth density changes |
| 4 | Dual Zone Score | Weighted danger score | You want soft-zone awareness |
| 5 | Periodicity Detector | Modal gap | Results have cyclic pattern |
| 6 | Momentum Score | Exponential decay | Rapid reaction needed |
| 7 | Regime Detection | State machine | Market has clear regimes |
| 8 | Pattern Sequence Voting | DB pattern lookup | Large historical pattern DB |
| 9 | Drought Timer | `good_distance` | After low-high streaks |
| 10 | Multi-Signal Consensus | Vote count | Maximum robustness |

---

> **Recommended starting point**: Implement **Approach 10** as a wrapper around approaches
> **3, 6, 7, and 9** — these four are independent enough to provide good coverage without
> being redundant. Start with `consensus >= 2` and tune from there.

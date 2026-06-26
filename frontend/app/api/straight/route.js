export const dynamic = 'force-dynamic';

/** Low-to-high transitions in the last `lookback` raw results */
function countLowToHighTransitions(history, lookback = 10) {
  const slice = history.slice(-lookback);
  let count = 0;
  for (let i = 1; i < slice.length; i++) {
    if (slice[i - 1] < 2.0 && slice[i] >= 2.0) count++;
  }
  return count;
}

/** Win rate (results >= 2.0) in the last `lookback` raw results */
function recentWinRate(history, lookback = 20) {
  const slice = history.slice(-lookback);
  if (slice.length === 0) return 0;
  const wins = slice.filter(v => v >= 2.0).length;
  return wins / slice.length; // 0.0 – 1.0
}

function computeStrategies(results) {
  const BASE_BET           = 0.2;
  const PAUSE_TRIGGER_LOSSES = 3;    // consecutive losses before pause
  const MIN_COOLDOWN       = 10;    // mandatory rounds to sit out after pause
  const FREQ_THRESHOLD     = 3;     // low→high transitions needed in last 10
  const WIN_RATE_LOOKBACK  = 20;    // window for win-rate check
  const WIN_RATE_MIN       = 0.60;  // 60 % win rate required

  // ── Plain unlimited Martingale ──
  let plainBalance = 0;
  let plainBet = BASE_BET;
  const plainBets = results.map((r, idx) => {
    const isWin     = r.value >= 2.0;
    const betPlaced = plainBet;
    const change    = isWin ? plainBet : -plainBet;
    plainBalance   += change;
    plainBet        = isWin ? BASE_BET : plainBet * 2;
    return {
      index: idx + 1,
      timestamp: `Round ${r.id}`,
      isWin,
      betPlaced: Math.round(betPlaced * 100) / 100,
      change:    Math.round(change    * 100) / 100,
      balance:   Math.round(plainBalance * 100) / 100,
      skipped:   false,
    };
  });

  // ── Smart Martingale — mandatory 10-round cooldown, 2-phase resume ──
  //
  //  Phase 1 (rounds 10+):  freq check   — ≥ 3 low→high in last 10
  //  Phase 2 (rounds 20+):  win-rate     — ≥ 60 % of last 20 are ≥ 2.0x
  //  Rolling after round 20: re-check both every round until one is met.
  //
  let smartBalance     = 0;
  let smartBet         = BASE_BET;
  let consecutiveLosses = 0;
  let isPaused         = false;
  let pausedCount      = 0;   // rounds observed while in cooldown
  const rawHistory     = [];
  const smartBets      = [];

  results.forEach((r, idx) => {
    const isWin = r.value >= 2.0;
    rawHistory.push(r.value);

    if (isPaused) {
      pausedCount++;   // count every round spent in cooldown

      let canResume = false;

      // Phase 1: mandatory 10-round wait has passed → check freq
      if (pausedCount >= MIN_COOLDOWN) {
        const freq = countLowToHighTransitions(rawHistory, 10);
        if (freq >= FREQ_THRESHOLD) canResume = true;
      }

      // Phase 2: 20-round wait has passed → also allow win-rate check
      if (!canResume && pausedCount >= WIN_RATE_LOOKBACK) {
        const winRate = recentWinRate(rawHistory, WIN_RATE_LOOKBACK);
        if (winRate >= WIN_RATE_MIN) canResume = true;
      }

      if (canResume) {
        // Resume: carry forward bet amount, reset streak & counter
        isPaused          = false;
        consecutiveLosses = 0;
        pausedCount       = 0;
        // smartBet intentionally NOT reset — continues from paused level
      } else {
        // Still in cooldown — record as skipped round
        const freq    = countLowToHighTransitions(rawHistory, 10);
        const winRate = recentWinRate(rawHistory, WIN_RATE_LOOKBACK);
        smartBets.push({
          index:       idx + 1,
          timestamp:   `Round ${r.id}`,
          isWin,
          betPlaced:   0,
          change:      0,
          balance:     Math.round(smartBalance * 100) / 100,
          isPaused:    true,
          pausedCount,               // how many rounds into the cooldown we are
          frequency:   freq,
          winRate:     Math.round(winRate * 100),
          skipped:     true,
        });
        return;
      }
    }

    // ── Place bet ──
    const betPlaced = smartBet;
    const freq    = countLowToHighTransitions(rawHistory, 10);
    const winRate = recentWinRate(rawHistory, WIN_RATE_LOOKBACK);
    let change;

    if (isWin) {
      change         = smartBet;
      smartBalance  += change;
      smartBet       = BASE_BET;
      consecutiveLosses = 0;
    } else {
      change         = -smartBet;
      smartBalance  += change;
      smartBet      *= 2;
      consecutiveLosses++;
      if (consecutiveLosses >= PAUSE_TRIGGER_LOSSES) {
        isPaused    = true;
        pausedCount = 0;   // reset cooldown counter fresh on each new pause
      }
    }

    smartBets.push({
      index:             idx + 1,
      timestamp:         `Round ${r.id}`,
      isWin,
      betPlaced:         Math.round(betPlaced * 100) / 100,
      change:            Math.round(change    * 100) / 100,
      balance:           Math.round(smartBalance * 100) / 100,
      isPaused:          false,
      paused:            isPaused,    // true if THIS round triggered the pause
      consecutiveLosses,
      frequency:         freq,
      winRate:           Math.round(winRate * 100),
      skipped:           false,
    });
  });

  return { plainBets, smartBets };
}


export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let lastCount = -1;
      let closed = false;

      const send = (payload) => {
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        } catch (_) {
          closed = true;
        }
      };

      const check = async () => {
        try {
          const res = await fetch('http://127.0.0.1:5000/summary-data', { cache: 'no-store' });
          const data = await res.json();
          const count = data.count ?? 0;

          if (count !== lastCount) {
            lastCount = count;
            if (data.status === 'success' && data.results?.length > 0) {
              const { plainBets, smartBets } = computeStrategies(data.results);
              send({ status: 'success', count, plainBets, smartBets });
            } else {
              send({ status: 'empty', count: 0, plainBets: [], smartBets: [] });
            }
          }
        } catch (_) {
          // Flask not available yet — silently skip
        }
      };

      // First check immediately
      await check();

      // Poll every 1 second — only emits when count changes
      const interval = setInterval(async () => {
        if (closed) {
          clearInterval(interval);
          return;
        }
        await check();
      }, 1000);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

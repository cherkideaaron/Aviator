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

/** Returns true if EITHER resume condition is met */
function shouldResume(history) {
  const FREQ_THRESHOLD    = 3;    // low-to-high transitions in last 10
  const WIN_RATE_LOOKBACK = 20;   // window for win-rate check
  const WIN_RATE_MIN      = 0.60; // 60%
  const freq    = countLowToHighTransitions(history, 10);
  const winRate = recentWinRate(history, WIN_RATE_LOOKBACK);
  return freq >= FREQ_THRESHOLD || winRate >= WIN_RATE_MIN;
}

function computeStrategies(results) {
  const BASE_BET = 0.2;
  const PAUSE_TRIGGER_LOSSES = 3;

  // ── Plain unlimited Martingale ──
  let plainBalance = 0;
  let plainBet = BASE_BET;
  const plainBets = results.map((r, idx) => {
    const isWin = r.value >= 2.0;
    const betPlaced = plainBet;
    const change = isWin ? plainBet : -plainBet;
    plainBalance += change;
    plainBet = isWin ? BASE_BET : plainBet * 2;
    return {
      index: idx + 1,
      timestamp: `Round ${r.id}`,
      isWin,
      betPlaced: Math.round(betPlaced * 100) / 100,
      change: Math.round(change * 100) / 100,
      balance: Math.round(plainBalance * 100) / 100,
      skipped: false,
    };
  });

  // ── Frequency-gated smart Martingale ──
  let smartBalance = 0;
  let smartBet = BASE_BET;
  let consecutiveLosses = 0;
  let isPaused = false;
  const rawHistory = [];
  const smartBets = [];

  results.forEach((r, idx) => {
    const isWin = r.value >= 2.0;
    rawHistory.push(r.value);

    if (isPaused) {
      if (shouldResume(rawHistory)) {
        isPaused = false;
        consecutiveLosses = 0;
        // smartBet intentionally NOT reset — continues from current value
      } else {
        const freq    = countLowToHighTransitions(rawHistory, 10);
        const winRate = recentWinRate(rawHistory, 20);
        smartBets.push({
          index: idx + 1,
          timestamp: `Round ${r.id}`,
          isWin,
          betPlaced: 0,
          change: 0,
          balance: Math.round(smartBalance * 100) / 100,
          isPaused: true,
          frequency: freq,
          winRate: Math.round(winRate * 100),
          skipped: true,
        });
        return;
      }
    }

    const betPlaced = smartBet;
    const freq    = countLowToHighTransitions(rawHistory, 10);
    const winRate = recentWinRate(rawHistory, 20);
    let change;

    if (isWin) {
      change = smartBet;
      smartBalance += change;
      smartBet = BASE_BET;
      consecutiveLosses = 0;
    } else {
      change = -smartBet;
      smartBalance += change;
      smartBet *= 2;
      consecutiveLosses++;
      if (consecutiveLosses >= PAUSE_TRIGGER_LOSSES) isPaused = true;
    }

    smartBets.push({
      index: idx + 1,
      timestamp: `Round ${r.id}`,
      isWin,
      betPlaced: Math.round(betPlaced * 100) / 100,
      change: Math.round(change * 100) / 100,
      balance: Math.round(smartBalance * 100) / 100,
      isPaused: false,
      paused: isPaused,
      consecutiveLosses,
      frequency: freq,
      winRate: Math.round(winRate * 100),
      skipped: false,
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

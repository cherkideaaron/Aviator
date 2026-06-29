export const dynamic = 'force-dynamic';

global.forceResumeRoundIds = global.forceResumeRoundIds || new Set();

// ─────────────────────────────────────────────────────────────────────────────
//  Smart Martingale — new entry-gating logic
//
//  STATE MACHINE:
//    BETTING   → normal; place bets, double on loss, reset on win.
//                After 3+ consecutive bad results → enter WATCHING.
//
//    WATCHING  → sit out; observe a 10-round window from the first good result
//                after the bad streak ends.
//                  • If another 3+ consecutive bad streak occurs within the window
//                    → reset the 10-round counter (start over from the next good).
//                  • Once a clean 10-round window completes with no 3+ streak
//                    → enter AWAITING state.
//
//    AWAITING  → still sitting out; wait for the very next bad result.
//                When a bad result occurs → immediately enter BETTING again.
// ─────────────────────────────────────────────────────────────────────────────

function computeStrategies(results) {
  const BASE_BET              = 0.2;
  const PAUSE_TRIGGER_LOSSES  = 3;   // consecutive bad results that trigger WATCHING
  const CLEAN_WINDOW          = 10;  // rounds that must pass without a 3+ streak

  // ── Plain unlimited Martingale ──────────────────────────────────────────────
  let plainBalance = 0;
  let plainBet     = BASE_BET;

  const plainBets = results.map((r, idx) => {
    const isWin     = r.value >= 2.0;
    const betPlaced = plainBet;
    const change    = isWin ? plainBet : -plainBet;
    plainBalance   += change;
    plainBet        = isWin ? BASE_BET : plainBet * 2;
    return {
      index:     idx + 1,
      timestamp: `Round ${r.id}`,
      isWin,
      betPlaced: Math.round(betPlaced   * 100) / 100,
      change:    Math.round(change      * 100) / 100,
      balance:   Math.round(plainBalance * 100) / 100,
      skipped:   false,
    };
  });

  // ── Smart Martingale ────────────────────────────────────────────────────────
  let smartBalance      = 0;
  let smartBet          = BASE_BET;

  // State: 'BETTING' | 'WATCHING' | 'AWAITING'
  let mode              = 'BETTING';

  let consecutiveLosses = 0;   // streak while BETTING

  // WATCHING state bookkeeping
  let watchWindow       = [];  // raw values seen in the current 10-round window
  let watchBadStreak    = 0;   // consecutive bad results inside watch window
  let watchingBadStreak = 0;   // bad streak accumulator during watching
  // We start the 10-round window from the first GOOD result after the bad streak
  let awaitingGoodStart = false; // true when inside a bad streak, waiting for good

  const smartBets = [];

  results.forEach((r, idx) => {
    const isBad = r.value < 2.0;   // "bad" = below 2.0x
    const isGood = !isBad;

    const pushSkipped = (extraFields = {}) => {
      smartBets.push({
        index:     idx + 1,
        timestamp: `Round ${r.id}`,
        isWin:     isGood,
        betPlaced: 0,
        change:    0,
        balance:   Math.round(smartBalance * 100) / 100,
        skipped:   true,
        mode,
        ...extraFields,
      });
      // Force resume check: if user pressed ^ on this skipped round
      if (global.forceResumeRoundIds && global.forceResumeRoundIds.has(r.id)) {
        mode = 'BETTING';
        consecutiveLosses = 0;
        smartBets[smartBets.length - 1].forcedResume = true;
      }
    };

    // ── BETTING mode ──────────────────────────────────────────────────────────
    if (mode === 'BETTING') {
      const betPlaced = smartBet;
      let change;

      if (isGood) {
        change             = smartBet;
        smartBalance      += change;
        smartBet           = BASE_BET;
        consecutiveLosses  = 0;
      } else {
        change             = -smartBet;
        smartBalance      += change;
        smartBet          *= 2;
        consecutiveLosses++;
      }

      const triggeredPause = consecutiveLosses >= PAUSE_TRIGGER_LOSSES;
      if (triggeredPause) {
        // Transition to WATCHING: bad streak just ended on THIS round.
        // We need to wait for the next good result to START the 10-round window.
        mode               = 'WATCHING';
        watchWindow        = [];
        watchBadStreak     = 0;
        watchingBadStreak  = 0;
        awaitingGoodStart  = true;   // don't count rounds until a good result appears
        consecutiveLosses  = 0;
      }

      smartBets.push({
        index:              idx + 1,
        timestamp:          `Round ${r.id}`,
        isWin:              isGood,
        betPlaced:          Math.round(betPlaced     * 100) / 100,
        change:             Math.round(change        * 100) / 100,
        balance:            Math.round(smartBalance  * 100) / 100,
        skipped:            false,
        mode:               'BETTING',
        consecutiveLosses,
        triggeredPause,
      });
      return;
    }

    // ── WATCHING mode ─────────────────────────────────────────────────────────
    if (mode === 'WATCHING') {
      if (awaitingGoodStart) {
        // Still inside (or just after) the triggering bad streak.
        // Wait for the first good result to open the 10-round window.
        if (isBad) {
          // More bad results — still waiting for good; bad streak continues
          watchingBadStreak++;
          pushSkipped({ watchProgress: 0, watchWindow: watchWindow.length, watchBadStreak: watchingBadStreak, awaitingGood: true });
          return;
        } else {
          // First good result → open the window, include this round
          awaitingGoodStart  = false;
          watchingBadStreak  = 0;
          watchWindow        = [r.value];
          watchBadStreak     = 0;
        }
      } else {
        // Add round to the watch window
        watchWindow.push(r.value);

        if (isBad) {
          watchBadStreak++;
          if (watchBadStreak >= PAUSE_TRIGGER_LOSSES) {
            // New bad streak within window → RESET window; wait for next good
            watchWindow       = [];
            watchBadStreak    = 0;
            awaitingGoodStart = true;
            pushSkipped({ watchProgress: 0, windowReset: true, watchBadStreak: PAUSE_TRIGGER_LOSSES });
            return;
          }
        } else {
          watchBadStreak = 0;
        }
      }

      // Check if window is complete (reached CLEAN_WINDOW rounds)
      if (watchWindow.length >= CLEAN_WINDOW) {
        // Clean window achieved → transition to AWAITING
        mode = 'AWAITING';
        pushSkipped({ watchProgress: watchWindow.length, windowComplete: true });
        return;
      }

      // Still building the window
      pushSkipped({ watchProgress: watchWindow.length, watchBadStreak });
      return;
    }

    // ── AWAITING mode ─────────────────────────────────────────────────────────
    if (mode === 'AWAITING') {
      if (isBad) {
        // The trigger bad result arrived.
        // Do NOT bet on this round — it is just the entry signal.
        // Record it as a trigger/skipped round, then start BETTING fresh
        // on the very next round (e.g. bad on round 12 → bet starts round 13).
        pushSkipped({ awaitingTrigger: true });   // mode is still 'AWAITING' here
        mode              = 'BETTING';
        consecutiveLosses = 0;
        // smartBet intentionally NOT reset — resumes from where it stopped
        // e.g. after 3 losses (0.2→0.4→0.8→1.6) it continues at 1.6
      } else {
        // Good result while awaiting — keep waiting for the bad trigger
        pushSkipped({ awaitingEntry: true });
      }
      return;
    }
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

export async function POST(req) {
  try {
    const body = await req.json();
    if (body.roundId) {
      global.forceResumeRoundIds = global.forceResumeRoundIds || new Set();
      global.forceResumeRoundIds.add(body.roundId);
      return new Response(JSON.stringify({ success: true, roundId: body.roundId }), { status: 200 });
    }
  } catch (e) {}
  return new Response(JSON.stringify({ success: false }), { status: 400 });
}

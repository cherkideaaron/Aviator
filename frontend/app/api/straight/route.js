export const dynamic = 'force-dynamic';

global.forceResumeRoundIds = global.forceResumeRoundIds || new Set();

// ─────────────────────────────────────────────────────────────────────────────
//  Smart Martingale — 2-phase resume logic
//
//  STATE MACHINE:
//    BETTING   → normal; place bets, double on loss, reset on win.
//                After 3+ consecutive bad results → enter COOLING.
//
//    COOLING   → Phase 1. Sit out.
//                Wait for the first GOOD result after the bad streak ends.
//                Then count a 10-round window (that good result = round 1).
//                If a NEW 3+ consecutive bad streak occurs inside the window:
//                  → reset window; wait for next good; restart 10-round count.
//                Once 10 clean rounds complete → enter AWAITING.
//
//    AWAITING  → Phase 2. Sit out.
//                Watch for 2 consecutive bad results.
//                On the 2nd consecutive bad → start BETTING on the very NEXT round.
//                Phase 2 NEVER loops back to Phase 1.
//                Phase 1 (COOLING) is only re-entered from BETTING.
// ─────────────────────────────────────────────────────────────────────────────

function computeStrategies(results) {
  const BASE_BET             = 0.2;
  const PAUSE_TRIGGER_LOSSES = 3;
  const CLEAN_WINDOW         = 10;

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
      betPlaced: Math.round(betPlaced    * 100) / 100,
      change:    Math.round(change       * 100) / 100,
      balance:   Math.round(plainBalance * 100) / 100,
      skipped:   false,
    };
  });

  // ── Smart Martingale ────────────────────────────────────────────────────────
  let smartBalance = 0;
  let smartBet     = BASE_BET;

  let mode = 'BETTING';
  let consecutiveLosses = 0;

  // COOLING (Phase 1)
  let coolingWindowStarted = false;
  let cleanRounds          = 0;
  let coolBadStreak        = 0;

  // AWAITING (Phase 2)
  let awaitBadStreak = 0;

  // ── Pause/Resume history ───────────────────────────────────────────────────
  const pauseResumeHistory = [];
  let currentPause = null;
  // currentPause = {
  //   pauseRound, pauseTimestamp,
  //   phase1Seq: [],   phase1Resets: 0,
  //   phase2Seq: [],
  //   resumeRound: null, resumeTimestamp: null
  // }

  // ── Bad Streak Tracker ─────────────────────────────────────────────────────
  const badStreakHistory = [];
  let trackerBadStreak   = 0;
  let lastStreakRound     = null;
  let lastStreakTime      = null;

  const smartBets = [];

  results.forEach((r, idx) => {
    const isBad  = r.value < 2.0;
    const isGood = !isBad;

    // ── Bad Streak tracker (independent of strategy) ─────────────────────────
    if (isBad) {
      trackerBadStreak++;
      if (trackerBadStreak === 3) {
        const currentRound = idx + 1;
        const currentTs    = r.timestamp ? new Date(r.timestamp) : null;
        let roundsSinceLast = null;
        let timeSinceLastMs = null;
        if (lastStreakRound !== null) {
          roundsSinceLast = currentRound - lastStreakRound;
          if (currentTs && lastStreakTime) timeSinceLastMs = currentTs.getTime() - lastStreakTime.getTime();
        }
        badStreakHistory.push({ roundId: currentRound, timestamp: r.timestamp, roundsSinceLast, timeSinceLastMs });
        lastStreakRound = currentRound;
        lastStreakTime  = currentTs;
      }
    } else {
      trackerBadStreak = 0;
    }

    // ── pushSkipped helper ────────────────────────────────────────────────────
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
      // Manual force-resume (^ key)
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
        change            = smartBet;
        smartBalance     += change;
        smartBet          = BASE_BET;
        consecutiveLosses = 0;
      } else {
        change            = -smartBet;
        smartBalance     += change;
        smartBet         *= 2;
        consecutiveLosses++;
      }

      const triggeredPause = consecutiveLosses >= PAUSE_TRIGGER_LOSSES;
      if (triggeredPause) {
        mode                 = 'COOLING';
        coolingWindowStarted = false;
        cleanRounds          = 0;
        coolBadStreak        = 0;
        consecutiveLosses    = 0;
        // Start recording this pause
        currentPause = {
          pauseRound:     idx + 1,
          pauseTimestamp: r.timestamp,
          phase1Seq:      [],
          phase1Resets:   0,
          phase2Seq:      [],
          resumeRound:    null,
          resumeTimestamp: null,
        };
      }

      smartBets.push({
        index:             idx + 1,
        timestamp:         `Round ${r.id}`,
        isWin:             isGood,
        betPlaced:         Math.round(betPlaced    * 100) / 100,
        change:            Math.round(change       * 100) / 100,
        balance:           Math.round(smartBalance * 100) / 100,
        skipped:           false,
        mode:              'BETTING',
        consecutiveLosses,
        triggeredPause,
      });
      return;
    }

    // ── COOLING mode (Phase 1) ────────────────────────────────────────────────
    if (mode === 'COOLING') {
      if (currentPause) currentPause.phase1Seq.push(isBad ? 0 : 1);

      if (!coolingWindowStarted) {
        if (isBad) {
          pushSkipped({ phase: 1, waitingForGood: true, cleanRounds });
          return;
        } else {
          // First good → open window; this is Round 1
          coolingWindowStarted = true;
          cleanRounds          = 1;
          coolBadStreak        = 0;
          pushSkipped({ phase: 1, cleanRounds, windowStarted: true });
          return;
        }
      }

      // Window is open
      cleanRounds++;

      if (isBad) {
        coolBadStreak++;
        if (coolBadStreak >= PAUSE_TRIGGER_LOSSES) {
          // New 3+ bad streak → reset
          coolingWindowStarted = false;
          cleanRounds          = 0;
          coolBadStreak        = 0;
          if (currentPause) currentPause.phase1Resets++;
          pushSkipped({ phase: 1, windowReset: true, cleanRounds: 0 });
          return;
        }
      } else {
        coolBadStreak = 0;
      }

      if (cleanRounds >= CLEAN_WINDOW) {
        // 10 clean rounds done → enter AWAITING
        mode           = 'AWAITING';
        awaitBadStreak = 0;
        pushSkipped({ phase: 1, cleanRounds, windowComplete: true });
        return;
      }

      pushSkipped({ phase: 1, cleanRounds, coolBadStreak });
      return;
    }

    // ── AWAITING mode (Phase 2) ───────────────────────────────────────────────
    if (mode === 'AWAITING') {
      if (currentPause) currentPause.phase2Seq.push(isBad ? 0 : 1);

      if (isBad) {
        awaitBadStreak++;
        if (awaitBadStreak >= 2) {
          // 2 consecutive bad results → resume BETTING on the NEXT round
          if (currentPause) {
            currentPause.resumeRound     = idx + 2; // next round index
            currentPause.resumeTimestamp = r.timestamp;
            const totalWaited = (idx + 1) - currentPause.pauseRound;
            pauseResumeHistory.push({ ...currentPause, totalRoundsWaited: totalWaited });
            currentPause = null;
          }
          pushSkipped({ phase: 2, awaitBadStreak, triggerFired: true });
          mode              = 'BETTING';
          consecutiveLosses = 0;
          return;
        }
        pushSkipped({ phase: 2, awaitBadStreak });
      } else {
        awaitBadStreak = 0;
        pushSkipped({ phase: 2, awaitBadStreak });
      }
      return;
    }
  });

  // If still paused at the end of the data, save the incomplete pause
  if (currentPause) {
    const totalWaited = results.length - currentPause.pauseRound;
    pauseResumeHistory.push({ ...currentPause, resumeRound: null, resumeTimestamp: null, totalRoundsWaited: totalWaited, incomplete: true });
  }

  const latestTimestamp = results.length > 0 ? results[results.length - 1].timestamp : null;
  const latestRoundId   = results.length > 0 ? results[results.length - 1].id        : null;

  return { plainBets, smartBets, badStreakHistory, pauseResumeHistory, latestTimestamp, latestRoundId };
}


export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let lastCount = -1;
      let closed    = false;

      const send = (payload) => {
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        } catch (_) {
          closed = true;
        }
      };

      const check = async () => {
        try {
          const res   = await fetch('http://127.0.0.1:5000/summary-data', { cache: 'no-store' });
          const data  = await res.json();
          const count = data.count ?? 0;

          if (count !== lastCount || global.forceRefresh) {
            lastCount           = count;
            global.forceRefresh = false;
            if (data.status === 'success' && data.results?.length > 0) {
              const { plainBets, smartBets, badStreakHistory, pauseResumeHistory, latestTimestamp, latestRoundId } = computeStrategies(data.results);
              send({ status: 'success', count, plainBets, smartBets, badStreakHistory, pauseResumeHistory, latestTimestamp, latestRoundId });
            } else {
              send({ status: 'empty', count: 0, plainBets: [], smartBets: [], badStreakHistory: [], pauseResumeHistory: [], latestTimestamp: null, latestRoundId: null });
            }
          }
        } catch (_) {
          // Flask not available yet — silently skip
        }
      };

      await check();

      const interval = setInterval(async () => {
        if (closed) { clearInterval(interval); return; }
        await check();
      }, 1000);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type':      'text/event-stream',
      'Cache-Control':     'no-cache, no-transform',
      'Connection':        'keep-alive',
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
      global.forceRefresh = true;
      return new Response(JSON.stringify({ success: true, roundId: body.roundId }), { status: 200 });
    }
  } catch (e) {}
  return new Response(JSON.stringify({ success: false }), { status: 400 });
}

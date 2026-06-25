import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const csvPath = path.join(process.cwd(), '..', 'ML', 'predictions_log.csv');

    if (!fs.existsSync(csvPath)) {
      return Response.json({ status: 'empty', rows: [], summary: null });
    }

    const content = fs.readFileSync(csvPath, 'utf-8');
    const lines = content.trim().split('\n').filter((l) => l.trim());

    if (lines.length <= 1) {
      return Response.json({ status: 'empty', rows: [], summary: null });
    }

    // CSV header: timestamp,row_id,prediction,probability,confidence,actual,is_correct,last10,wins_in_last10
    const allRows = lines.slice(1).map((line) => {
      const parts = line.split(',');
      return {
        timestamp:      parts[0]?.trim() ?? '',
        row_id:         parts[1]?.trim() ?? '',
        prediction:     parts[2]?.trim() ?? '',
        probability:    parseFloat(parts[3]) || 0,
        confidence:     parts[4]?.trim() ?? '',
        actual:         parts[5]?.trim() ?? '',
        is_correct:     parts[6]?.trim() === 'True',
        last10:         parts[7]?.trim() ?? '',
        wins_in_last10: parseInt(parts[8]) || 0,
      };
    }).filter((r) => r.timestamp && r.prediction);

    // ── Build rolling accuracy over WIN predictions only ─────────────────────
    // Extract WIN predictions in chronological order
    const winRows = allRows.filter((r) => r.prediction === 'WIN');

    const rollingPct = (arr, upToIdx, n) => {
      const slice = arr.slice(Math.max(0, upToIdx - n + 1), upToIdx + 1);
      if (slice.length === 0) return null;
      const correct = slice.filter((r) => r.is_correct).length;
      return Math.round((correct / slice.length) * 100);
    };

    const enrichedWin = winRows.map((row, i) => ({
      ...row,
      pct_last5:  rollingPct(winRows, i, 5),
      pct_last10: rollingPct(winRows, i, 10),
      pct_last20: rollingPct(winRows, i, 20),
    }));

    // ── Summary stats ────────────────────────────────────────────────────────
    const totalAll     = allRows.length;
    const totalCorrect = allRows.filter((r) => r.is_correct).length;

    const totalWin        = winRows.length;
    const winCorrect      = winRows.filter((r) => r.is_correct).length;

    const recentWinPct = (n) => {
      const slice = winRows.slice(-n);
      return slice.length > 0
        ? Math.round(slice.filter((r) => r.is_correct).length / slice.length * 100)
        : null;
    };

    const summary = {
      totalAll,
      totalCorrect,
      overallAccuracy:  totalAll  > 0 ? (totalCorrect / totalAll  * 100).toFixed(1) : '0.0',
      totalWin,
      winCorrect,
      winAccuracy:      totalWin  > 0 ? (winCorrect  / totalWin  * 100).toFixed(1) : '0.0',
      last5Pct:  recentWinPct(5),
      last10Pct: recentWinPct(10),
      last20Pct: recentWinPct(20),
    };

    // ── Build Martingale simulation from win_predictions_detail.txt ───────────
    const detailPath = path.join(process.cwd(), '..', 'ML', 'win_predictions_detail.txt');
    let detailBets = [];

    if (fs.existsSync(detailPath)) {
      const detailContent = fs.readFileSync(detailPath, 'utf-8');
      const detailLines = detailContent.trim().split('\n').filter((l) => l.trim());

      let balance = 5.0;
      let maxBalance = 5.0;   // highest balance ever reached
      let minBalance = 5.0;   // lowest balance ever reached (can go negative)
      let consecutiveLosses = 0;
      const BASE_BET = 1.0;
      let currentBet = BASE_BET;

      detailBets = detailLines.map((line, idx) => {
        const parts = line.split('|').map((p) => p.trim());
        const rowData = {};
        parts.forEach((part) => {
          if (part.includes(':')) {
            const colonIdx = part.indexOf(':');
            const key = part.slice(0, colonIdx).trim();
            const value = part.slice(colonIdx + 1).trim();
            rowData[key] = value;
          }
        });

        const rawValue = parseFloat(rowData['Raw Value']) || 0;
        const actual = rowData['Actual'] || '';

        // Win = the multiplier reached 2.00x or above
        const isWin = rawValue >= 2.0;

        let change = 0;
        let betPlaced = currentBet;

        if (isWin) {
          change = +(currentBet * 1.0).toFixed(2); // profit at 2.0x cashout (100% of bet)
          balance += change;
          consecutiveLosses = 0;

          balance = Math.round(balance * 100) / 100;

          if (balance >= maxBalance) {
            // ✅ Reached or exceeded peak — always reset bet to $0.20
            maxBalance = balance;
            currentBet = BASE_BET;
          }
          // else: won but still below peak — hold the bet (keep recovering at same amount)
        } else {
          change = -currentBet;
          balance += change;
          consecutiveLosses += 1;

          balance = Math.round(balance * 100) / 100;

          // 🎲 Martingale: DOUBLE the bet on every loss
          currentBet = Math.round((currentBet * 2) * 100) / 100;
        }

        // Track peak and floor balances
        if (balance > maxBalance) maxBalance = balance;
        if (balance < minBalance) minBalance = balance;

        change = Math.round(change * 100) / 100;

        return {
          index: idx + 1,
          rawValue,
          actual,
          isWin,
          betPlaced,
          change,
          balance,
          maxBalance,
          minBalance,
          consecutiveLosses,
        };
      });
    }

    // Return last 200 WIN rows newest-first
    const displayRows = enrichedWin.slice(-200).reverse();

    return Response.json({ status: 'success', rows: displayRows, summary, detailBets });
  } catch (err) {
    return Response.json({ status: 'error', message: err.message }, { status: 500 });
  }
}

'use client';

import { useState, useEffect, useRef } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

// ── Shared tooltip for plain graph ─────────────────────────────────────────
const PlainTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const color = d.isWin ? 'var(--accent-green)' : 'var(--accent-red)';
  return (
    <div className="custom-tooltip" style={{ minWidth: '155px' }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Round #{d.index}</p>
      <p style={{ margin: 0 }}>Bet: <strong style={{ color: 'var(--text-primary)' }}>${d.betPlaced.toFixed(2)}</strong></p>
      <p style={{ margin: 0 }}>
        Outcome: <strong style={{ color }}>{d.isWin ? '▲ WIN' : '▼ LOSS'} ({d.isWin ? '+' : ''}${d.change.toFixed(2)})</strong>
      </p>
      <p style={{ margin: 0, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '3px', marginTop: '3px' }}>
        Balance: <strong style={{ color: 'var(--text-primary)' }}>${d.balance.toFixed(2)}</strong>
      </p>
    </div>
  );
};

// ── Tooltip for smart (3-state gated) graph ────────────────────────────────
const SmartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;

  if (d.skipped) {
    return (
      <div className="custom-tooltip" style={{ minWidth: '220px' }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Round #{d.index}</p>

        {d.mode === 'COOLING' ? (
          <>
            {d.windowReset ? (
              <>
                <p style={{ margin: 0, color: '#ef4444', fontSize: '12px', fontWeight: 600 }}>🔄 WINDOW RESET</p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  New 3+ bad streak hit. Waiting for next good result to restart 10-round window.
                </p>
              </>
            ) : d.windowComplete ? (
              <>
                <p style={{ margin: 0, color: 'var(--accent-green)', fontSize: '12px', fontWeight: 600 }}>✅ PHASE 1 COMPLETE</p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  10 clean rounds done. Moving to Phase 2: hunt for 2 consecutive 0s.
                </p>
              </>
            ) : d.waitingForGood ? (
              <>
                <p style={{ margin: 0, color: '#f59e0b', fontSize: '12px', fontWeight: 600 }}>⏳ PHASE 1 — Waiting for first 1</p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Sitting out. Window starts on the next good result.
                </p>
              </>
            ) : (
              <>
                <p style={{ margin: 0, color: '#f59e0b', fontSize: '12px', fontWeight: 600 }}>📊 PHASE 1 — Clean Window</p>
                <p style={{ margin: '5px 0 3px', fontSize: '11px', color: 'var(--text-muted)' }}>
                  Progress: <strong style={{ color: (d.cleanRounds >= 10) ? 'var(--accent-green)' : 'var(--text-primary)' }}>{d.cleanRounds || 0} / 10</strong> clean rounds
                </p>
                <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 3, marginBottom: '6px' }}>
                  <div style={{ height: '100%', width: `${Math.min(((d.cleanRounds || 0) / 10) * 100, 100)}%`, background: '#f59e0b', borderRadius: 3 }} />
                </div>
                {(d.coolBadStreak > 0) && (
                  <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#ef4444' }}>
                    ⚠️ Bad streak inside window: {d.coolBadStreak}/3
                  </p>
                )}
                {d.windowStarted && (
                  <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--accent-green)', fontStyle: 'italic' }}>
                    Window just opened!
                  </p>
                )}
              </>
            )}
          </>
        ) : d.mode === 'AWAITING' ? (
          <>
            {d.triggerFired ? (
              <>
                <p style={{ margin: 0, color: 'var(--accent-cyan)', fontSize: '12px', fontWeight: 600 }}>🎯 TRIGGER FIRED — 2 consecutive 0s!</p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Betting resumes on the very next round.
                </p>
              </>
            ) : (
              <>
                <p style={{ margin: 0, color: 'var(--accent-green)', fontSize: '12px', fontWeight: 600 }}>🔍 PHASE 2 — Hunting for 2x 0s</p>
                <p style={{ margin: '5px 0 3px', fontSize: '11px', color: 'var(--text-muted)' }}>
                  Consecutive 0s so far: <strong style={{ color: (d.awaitBadStreak >= 1) ? '#f59e0b' : 'var(--text-muted)' }}>{d.awaitBadStreak || 0} / 2</strong>
                </p>
                <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
                  <div style={{ height: '100%', width: `${(d.awaitBadStreak || 0) * 50}%`, background: 'var(--accent-cyan)', borderRadius: 3 }} />
                </div>
              </>
            )}
          </>
        ) : (
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '12px' }}>Skipped round.</p>
        )}

        <p style={{ margin: '6px 0 0', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '4px' }}>
          Balance: <strong style={{ color: 'var(--text-primary)' }}>${d.balance.toFixed(2)}</strong>
        </p>
      </div>
    );
  }

  const color = d.isWin ? 'var(--accent-green)' : 'var(--accent-red)';
  return (
    <div className="custom-tooltip" style={{ minWidth: '175px' }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Round #{d.index}</p>
      <p style={{ margin: 0 }}>Bet: <strong style={{ color: 'var(--text-primary)' }}>${d.betPlaced.toFixed(2)}</strong></p>
      <p style={{ margin: 0 }}>
        Outcome: <strong style={{ color }}>{d.isWin ? '▲ WIN' : '▼ LOSS'} ({d.isWin ? '+' : ''}${d.change.toFixed(2)})</strong>
      </p>
      {d.triggeredPause && (
        <p style={{ margin: 0, color: '#f59e0b', fontSize: '11px', fontWeight: 600 }}>⏸ 3+ bad streak → now WATCHING</p>
      )}
      {d.forcedResume && (
        <p style={{ margin: 0, color: 'var(--accent-cyan)', fontSize: '11px', fontWeight: 600 }}>🚀 FORCE RESUMED</p>
      )}
      <p style={{ margin: 0, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '3px', marginTop: '3px' }}>
        Balance: <strong style={{ color: 'var(--text-primary)' }}>${d.balance.toFixed(2)}</strong>
      </p>
    </div>
  );
};


// ── Reusable chart card ────────────────────────────────────────────────────
function BankrollChart({ data, label, description, TooltipComponent, accentColor, gradientId, showPauseDots }) {
  const lastPoint = data[data.length - 1];
  const endingBalance = lastPoint ? lastPoint.balance : 0;
  const activePts = data.filter(b => !b.skipped);
  const maxBal = activePts.length > 0 ? Math.max(...activePts.map(b => b.balance)) : 0;
  const minBal = activePts.length > 0 ? Math.min(...activePts.map(b => b.balance)) : 0;
  const maxBet = activePts.length > 0 ? Math.max(...activePts.map(b => b.betPlaced)) : 0;
  const pausedCount = data.filter(b => b.skipped).length;

  const stroke = endingBalance >= 0 ? accentColor : 'var(--accent-red)';

  return (
    <div className="chart-card-large" style={{ marginBottom: '2rem' }}>
      {/* Header */}
      <div className="chart-card-large-header" style={{ marginBottom: '1rem' }}>
        <div>
          <h3 className="chart-title">{label}</h3>
          <span className="chart-meta">{description}</span>
        </div>
        <div style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>BALANCE</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.1rem', fontWeight: 700, color: endingBalance >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              ${endingBalance.toFixed(2)}
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>PEAK</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-green)' }}>${maxBal.toFixed(2)}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>DRAWDOWN</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-red)' }}>${minBal.toFixed(2)}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>MAX BET</div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-orange)' }}>${maxBet.toFixed(2)}</div>
          </div>
          {showPauseDots && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>PAUSED</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '1.1rem', fontWeight: 700, color: '#f59e0b' }}>{pausedCount}</div>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div style={{ width: '100%', height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={stroke} stopOpacity={0.3} />
                <stop offset="95%" stopColor={stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="index" tickLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
            <YAxis domain={['auto', 'auto']} tickLine={false} axisLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
            <Tooltip content={<TooltipComponent />} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.18)" strokeDasharray="5 4" />
            <Area
              type="monotone"
              dataKey="balance"
              stroke={stroke}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#${gradientId})`}
              dot={showPauseDots
                ? (props) => {
                    const { cx, cy, payload } = props;
                    if (!payload.skipped) return null;
                    return (
                      <circle
                        key={`pd-${payload.index}`}
                        cx={cx} cy={cy} r={3}
                        fill="#f59e0b"
                        stroke="rgba(0,0,0,0.5)"
                        strokeWidth={1}
                      />
                    );
                  }
                : false
              }
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function StraightPage() {
  const [plainBets, setPlainBets] = useState([]);
  const [smartBets, setSmartBets] = useState([]);
  const [badStreakHistory, setBadStreakHistory] = useState([]);
  const [pauseResumeHistory, setPauseResumeHistory] = useState([]);
  const [latestTimestamp, setLatestTimestamp] = useState(null);
  const [loading, setLoading] = useState(true);

  const smartBetsRef = useRef(smartBets);
  useEffect(() => {
    smartBetsRef.current = smartBets;
  }, [smartBets]);

  useEffect(() => {
    const handleKeyDown = async (e) => {
      if (e.key === '^') {
        const bets = smartBetsRef.current;
        if (bets.length > 0) {
          const lastBet = bets[bets.length - 1];
          const match = lastBet.timestamp.match(/Round (\d+)/);
          if (match) {
            const roundId = parseInt(match[1], 10);
            await fetch('/api/straight', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ roundId })
            });
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    // SSE — server pushes only when a new round result arrives
    const es = new EventSource('/api/straight');

    es.onmessage = (event) => {
      try {
        const json = JSON.parse(event.data);
        if (json.status === 'success') {
          setPlainBets(json.plainBets || []);
          setSmartBets(json.smartBets || []);
          setBadStreakHistory(json.badStreakHistory || []);
          setPauseResumeHistory(json.pauseResumeHistory || []);
          setLatestTimestamp(json.latestTimestamp || null);
        }
      } catch (_) {}
      setLoading(false);
    };

    es.onerror = () => {
      setLoading(false);
    };

    return () => es.close();
  }, []);

  const lastStreak = badStreakHistory.length > 0 ? badStreakHistory[badStreakHistory.length - 1] : null;
  const currentRoundTotal = plainBets.length;
  
  let liveRoundsDiff = null;
  let liveTimeDiffMs = null;
  
  if (lastStreak) {
    liveRoundsDiff = currentRoundTotal - lastStreak.roundId;
    if (latestTimestamp && lastStreak.timestamp) {
      liveTimeDiffMs = new Date(latestTimestamp).getTime() - new Date(lastStreak.timestamp).getTime();
    }
  }

  const formatTime = (ms) => {
    if (ms === null || isNaN(ms)) return 'N/A';
    const totalSec = Math.floor(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m}m ${s}s`;
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Straight Strategy — Comparison</h1>
        <p className="page-subtitle">
          Two simulations side by side: unlimited Martingale vs. Smart Martingale.
          Base bet <strong>$0.20</strong> · Doubles on loss · After <strong>3 consecutive losses</strong> →
          enters <strong>WATCHING</strong>: waits until EITHER <strong>3+ L2H transitions</strong> (checked after 10+ rounds) OR <strong>≥9 wins in last 15 rounds</strong> are found. (<em>Note: A new 3+ loss streak resets the wait timer</em>). Then enters <strong>AWAITING</strong> until the next loss triggers a resume.
        </p>
      </div>


      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Simulating games...
        </div>
      ) : plainBets.length === 0 ? (
        <div className="empty-state" style={{ height: 300, marginTop: '2rem' }}>
          <span className="empty-state-icon">◌</span>
          <span>No historical games found. Make sure new8.py is running.</span>
        </div>
      ) : (
        <>
          {/* ── Stats Box ── */}
          <div style={{
            display: 'flex', gap: '2rem', padding: '1rem 1.5rem', 
            background: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.05)', marginBottom: '2rem',
            alignItems: 'center', justifyContent: 'center'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>TOTAL 1s (WINS)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-green)', fontFamily: 'JetBrains Mono' }}>
                {plainBets.filter(b => b.isWin).length}
              </div>
            </div>
            
            <div style={{ width: '1px', height: '40px', background: 'rgba(255, 255, 255, 0.1)' }} />
            
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>TOTAL 0s (LOSSES)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-red)', fontFamily: 'JetBrains Mono' }}>
                {plainBets.filter(b => !b.isWin).length}
              </div>
            </div>

            <div style={{ width: '1px', height: '40px', background: 'rgba(255, 255, 255, 0.1)' }} />

            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>DIFFERENCE (1s - 0s)</div>
              <div style={{ 
                fontSize: '1.4rem', fontWeight: 700, fontFamily: 'JetBrains Mono',
                color: (plainBets.filter(b => b.isWin).length - plainBets.filter(b => !b.isWin).length) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
              }}>
                {plainBets.filter(b => b.isWin).length - plainBets.filter(b => !b.isWin).length}
              </div>
            </div>
          </div>

          {/* ── Bad Streak History Box ── */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.05)', marginBottom: '2rem', padding: '1.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>3+ Bad Streak Tracker</h3>
                <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>Tracks consecutive losses and the gap between them.</p>
              </div>
              <div style={{ textAlign: 'right', background: 'rgba(245, 158, 11, 0.1)', padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                <div style={{ fontSize: '10px', color: '#f59e0b', fontWeight: 600, marginBottom: '2px', textTransform: 'uppercase' }}>Since Last 3+ Streak</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono' }}>
                  {liveRoundsDiff !== null ? `${liveRoundsDiff} rounds` : 'N/A'} <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0 6px' }}>/</span> {liveTimeDiffMs !== null ? formatTime(liveTimeDiffMs) : 'N/A'}
                </div>
              </div>
            </div>

            {badStreakHistory.length > 0 ? (
              <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', background: 'rgba(0,0,0,0.2)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#1c1c1c' }}>
                    <tr>
                      <th style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 500 }}>Time</th>
                      <th style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 500 }}>Round</th>
                      <th style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 500 }}>Rounds Since Prev</th>
                      <th style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 500 }}>Time Since Prev</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...badStreakHistory].reverse().map((streak, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'JetBrains Mono' }}>{streak.timestamp ? new Date(streak.timestamp).toLocaleTimeString() : 'N/A'}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'JetBrains Mono' }}>#{streak.roundId}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'JetBrains Mono', color: 'var(--accent-cyan)' }}>
                          {streak.roundsSinceLast !== null ? `+${streak.roundsSinceLast}` : '-'}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'JetBrains Mono', color: 'var(--accent-cyan)' }}>
                          {streak.timeSinceLastMs !== null ? `+${formatTime(streak.timeSinceLastMs)}` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                No 3+ bad streaks recorded yet.
              </div>
            )}
          </div>

          {/* ── Pause / Resume Log ── */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  ⏸ Pause / Resume Log
                </h3>
                <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>
                  Each time the strategy paused — how long it waited, the result sequence, and where it resumed.
                </p>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '10px' }}>
                {pauseResumeHistory.length} pause{pauseResumeHistory.length !== 1 ? 's' : ''}
              </span>
            </div>

            {pauseResumeHistory.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '360px', overflowY: 'auto' }}>
                {[...pauseResumeHistory].reverse().map((p, i) => {
                  const seq1 = p.phase1Seq || [];
                  const seq2 = p.phase2Seq || [];
                  return (
                    <div key={i} style={{
                      background: p.incomplete ? 'rgba(245,158,11,0.07)' : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${p.incomplete ? 'rgba(245,158,11,0.25)' : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: '8px', padding: '10px 14px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, color: '#ef4444' }}>
                            ⏸ Paused @ Round {p.pauseRound}
                          </span>
                          {p.incomplete && (
                            <span style={{ fontSize: '10px', background: 'rgba(245,158,11,0.2)', color: '#f59e0b', padding: '1px 6px', borderRadius: '8px', fontWeight: 600 }}>
                              STILL PAUSED
                            </span>
                          )}
                          {p.resumeRound && (
                            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-green)' }}>
                              → Resumed @ Round {p.resumeRound}
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {p.totalRoundsWaited} rounds waited
                        </span>
                      </div>

                      {/* Phase 1 sequence */}
                      <div style={{ marginBottom: '6px' }}>
                        <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: 600, marginRight: '6px' }}>
                          PHASE 1 ({seq1.length}r, {p.phase1Resets} reset{p.phase1Resets !== 1 ? 's' : ''}):
                        </span>
                        <span style={{ fontFamily: 'monospace', fontSize: '11px', letterSpacing: '2px' }}>
                          {seq1.map((v, j) => (
                            <span key={j} style={{ color: v === 0 ? '#ef4444' : 'var(--accent-green)', fontWeight: 700 }}>
                              {v === 0 ? '0' : '1'}
                            </span>
                          ))}
                          {seq1.length === 0 && <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                        </span>
                      </div>

                      {/* Phase 2 sequence */}
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--accent-cyan)', fontWeight: 600, marginRight: '6px' }}>
                          PHASE 2 ({seq2.length}r):
                        </span>
                        <span style={{ fontFamily: 'monospace', fontSize: '11px', letterSpacing: '2px' }}>
                          {seq2.map((v, j) => (
                            <span key={j} style={{ color: v === 0 ? '#ef4444' : 'var(--accent-green)', fontWeight: 700 }}>
                              {v === 0 ? '0' : '1'}
                            </span>
                          ))}
                          {seq2.length === 0 && <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                        </span>
                        {seq2.length >= 2 && !p.incomplete && (
                          <span style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--accent-cyan)' }}>← 2 consecutive 0s triggered resume</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                No pause events recorded yet.
              </div>
            )}
          </div>

          {/* ── Graph 1: Plain unlimited ── */}
          <BankrollChart
            data={plainBets}
            label="Graph 1 — Plain Martingale (No Limits)"
            description="Bets every round. Doubles on every loss with no pause. Unlimited upside and downside."
            TooltipComponent={PlainTooltip}
            accentColor="var(--accent-green)"
            gradientId="plainGrad"
            showPauseDots={false}
          />

          {/* Divider */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '1rem',
            margin: '0.5rem 0 1.5rem', color: 'var(--text-muted)', fontSize: '12px'
          }}>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
            <span>vs</span>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
          </div>

          {/* ── Graph 2: Smart gated ── */}
          <BankrollChart
            data={smartBets}
            label="Graph 2 — Smart Martingale (2-Phase Resume)"
            description="BETTING → 3 consecutive 0s → PHASE 1: wait for 10 clean rounds (resets on new 3+ streak) → PHASE 2: hunt for 2 consecutive 0s → resume BETTING on the next round."
            TooltipComponent={SmartTooltip}
            accentColor="var(--accent-blue, #5b8dee)"
            gradientId="smartGrad"
            showPauseDots={true}
          />

          {/* Legend */}
          <div style={{ display: 'flex', gap: '1.5rem', fontSize: '11px', color: 'var(--text-muted)', flexWrap: 'wrap', marginTop: '-0.5rem', marginBottom: '2rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
              Amber dots = WATCHING or AWAITING round (no bet, balance flat)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 22, height: 2, background: 'rgba(255,255,255,0.2)', display: 'inline-block', borderRadius: 2 }} />
              Dashed line = zero baseline
            </span>
          </div>
        </>
      )}
    </>
  );
}

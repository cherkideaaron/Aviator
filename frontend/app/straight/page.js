'use client';

import { useState, useEffect } from 'react';
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

// ── Tooltip for smart (frequency-gated) graph ──────────────────────────────
const SmartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;

  if (d.skipped) {
    return (
      <div className="custom-tooltip" style={{ minWidth: '170px' }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Round #{d.index}</p>
        <p style={{ margin: 0, color: '#f59e0b', fontSize: '12px', fontWeight: 600 }}>⏸ PAUSED</p>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '11px', marginTop: '4px' }}>Waiting for either condition…</p>
        <p style={{ margin: 0, fontSize: '11px', marginTop: '4px' }}>
          <span style={{ color: d.frequency >= 3 ? 'var(--accent-green)' : '#f59e0b' }}>
            Low→High freq: {d.frequency}/3
          </span>
        </p>
        <p style={{ margin: 0, fontSize: '11px' }}>
          <span style={{ color: d.winRate >= 60 ? 'var(--accent-green)' : '#f59e0b' }}>
            Win rate (last 20): {d.winRate ?? 0}%
          </span>
        </p>
        <p style={{ margin: 0, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '3px', marginTop: '3px' }}>
          Balance: <strong style={{ color: 'var(--text-primary)' }}>${d.balance.toFixed(2)}</strong>
        </p>
      </div>
    );
  }

  const color = d.isWin ? 'var(--accent-green)' : 'var(--accent-red)';
  return (
    <div className="custom-tooltip" style={{ minWidth: '170px' }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Round #{d.index}</p>
      <p style={{ margin: 0 }}>Bet: <strong style={{ color: 'var(--text-primary)' }}>${d.betPlaced.toFixed(2)}</strong></p>
      <p style={{ margin: 0 }}>
        Outcome: <strong style={{ color }}>{d.isWin ? '▲ WIN' : '▼ LOSS'} ({d.isWin ? '+' : ''}${d.change.toFixed(2)})</strong>
      </p>
      <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '11px' }}>
        Low→High freq: <strong style={{ color: d.frequency >= 3 ? 'var(--accent-green)' : '#f59e0b' }}>{d.frequency}/3</strong>
        {' | '}WR(20): <strong style={{ color: d.winRate >= 60 ? 'var(--accent-green)' : '#f59e0b' }}>{d.winRate ?? 0}%</strong>
      </p>
      {d.paused && (
        <p style={{ margin: 0, color: '#f59e0b', fontSize: '11px', fontWeight: 600 }}>⏸ Pause triggered this round</p>
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // SSE — server pushes only when a new round result arrives
    const es = new EventSource('/api/straight');

    es.onmessage = (event) => {
      try {
        const json = JSON.parse(event.data);
        if (json.status === 'success') {
          setPlainBets(json.plainBets || []);
          setSmartBets(json.smartBets || []);
        }
      } catch (_) {}
      setLoading(false);
    };

    es.onerror = () => {
      setLoading(false);
    };

    return () => es.close();
  }, []);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Straight Strategy — Comparison</h1>
        <p className="page-subtitle">
          Two simulations side by side: unlimited Martingale vs. frequency-gated smart pause.
          Base bet <strong>$0.20</strong> · Odds <strong>2.0x</strong> · Doubles on loss · Pauses after <strong>3 consecutive losses</strong> until Low→High transitions ≥ <strong>4</strong>
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

          {/* ── Graph 2: Smart frequency-gated ── */}
          <BankrollChart
            data={smartBets}
            label="Graph 2 — Smart Martingale (Frequency Gate)"
            description="Pauses after 3 consecutive losses. Resumes (same bet amount) once Low→High transitions ≥ 4 in last 10 rounds."
            TooltipComponent={SmartTooltip}
            accentColor="var(--accent-blue, #5b8dee)"
            gradientId="smartGrad"
            showPauseDots={true}
          />

          {/* Legend */}
          <div style={{ display: 'flex', gap: '1.5rem', fontSize: '11px', color: 'var(--text-muted)', flexWrap: 'wrap', marginTop: '-0.5rem', marginBottom: '2rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
              Amber dots = paused round (no bet placed, balance flat)
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

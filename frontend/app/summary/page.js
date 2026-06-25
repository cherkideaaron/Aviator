'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';

// ─── Constants ─────────────────────────────────────────────────────────────
const INITIAL_BALANCE = 20000;
const BET_SIZE = 0.2;
const POLL_MS = 5000;

const TYPE1_ODDS = [1.5, 2, 3, 4, 5];
const TYPE2_ODDS = [1.5, 2];
const SKIP_VALUES = [0, 1, 2, 3, 4, 5];

const ODD_COLORS = {
  1.5: '#5b8dee',
  2:   '#00d4ff',
  3:   '#a78bfa',
  4:   '#ff9a3c',
  5:   '#ff4d6d',
};

const SKIP_ODD_COLORS = {
  1.5: '#5b8dee',
  2:   '#00e5a0',
};

// ─── Pure computation ───────────────────────────────────────────────────────
/**
 * computeBalanceSeries
 *
 * Pure function intentionally separated from UI so a future ML prediction
 * layer can call it on predicted result arrays without any React coupling.
 * The returned point shape {round, gameId, rawValue, balance, change, isBet,
 * isWin} has a stable structure — add `predictedBalance` or `predictedValue`
 * to each point later and just render a second <Area> on the same chart.
 *
 * @param {Array<{id:number, value:number}>} results
 * @param {number} odd       - threshold odd (win if result >= odd)
 * @param {number} skipEvery - skip N rounds between bets (0 = every round)
 * @param {number} betSize   - fixed stake per bet
 */
export function computeBalanceSeries(results, odd, skipEvery = 0, betSize = BET_SIZE) {
  const series = [];
  let balance = INITIAL_BALANCE;
  let roundCounter = 0; // 0 = bet this round, else skip

  for (let i = 0; i < results.length; i++) {
    const { id, value } = results[i];
    const isBet = roundCounter === 0;
    let change = 0;
    let isWin = false;

    if (isBet) {
      if (value >= odd) {
        // WIN: net profit = bet × (odd − 1)
        change = +(betSize * (odd - 1)).toFixed(4);
        isWin = true;
      } else {
        // LOSE: lose the stake
        change = -betSize;
      }
      balance = +(balance + change).toFixed(4);
    }
    // Skipped round: balance stays exactly as it was — no point update needed

    series.push({
      round: i + 1,
      gameId: id,
      rawValue: value,
      balance,          // stays flat during skipped rounds
      change,
      isBet,
      isWin,
      // ML hook: add predictedBalance / predictedValue here in future
    });

    roundCounter = (roundCounter + 1) % (skipEvery + 1);
  }

  return series;
}

// ─── Tooltip ────────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  return (
    <div style={{
      background: 'rgba(8,12,28,0.97)',
      border: '1px solid rgba(99,120,255,0.35)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
      minWidth: 170,
    }}>
      <div style={{ color: '#8b9cc8', marginBottom: 6, fontSize: 10 }}>
        Round #{d.round} · ID {d.gameId}
      </div>
      <div style={{ color: '#e8eaf6', marginBottom: 4 }}>
        Result:{' '}
        <span style={{ color: '#ff9a3c', fontWeight: 700 }}>
          {d.rawValue?.toFixed(2)}x
        </span>
      </div>
      <div style={{ color: '#e8eaf6', marginBottom: 4 }}>
        Balance:{' '}
        <span style={{ color: '#00d4ff', fontWeight: 700 }}>
          {d.balance?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
      {d.isBet ? (
        <div style={{
          color: d.isWin ? '#00e5a0' : '#ff4d6d',
          fontWeight: 700,
          fontSize: 12,
        }}>
          {d.isWin ? '▲' : '▼'}{' '}
          {d.isWin ? '+' : ''}{d.change?.toFixed(4)}
        </div>
      ) : (
        <div style={{ color: '#4a5580', fontSize: 10 }}>⏸ skipped this round</div>
      )}
    </div>
  );
}

// ─── Individual balance chart ─────────────────────────────────────────────
function BalanceChart({ series, title, accentColor, chartId }) {
  if (!series || series.length === 0) {
    return (
      <div className="balance-chart-card">
        <div className="balance-chart-header">
          <div className="balance-chart-title">{title}</div>
        </div>
        <div className="empty-state" style={{ height: 280 }}>
          <span className="empty-state-icon">◌</span>
          <span>No session data yet</span>
        </div>
      </div>
    );
  }

  const currentBalance = series[series.length - 1]?.balance ?? INITIAL_BALANCE;
  const pnl = +(currentBalance - INITIAL_BALANCE).toFixed(4);
  const betRounds  = series.filter(d => d.isBet);
  const winRounds  = betRounds.filter(d => d.isWin);
  const lossRounds = betRounds.length - winRounds.length;
  const winRate    = betRounds.length > 0
    ? ((winRounds.length / betRounds.length) * 100).toFixed(1)
    : '0.0';
  const pnlPos = pnl >= 0;

  // Gradient stop position: where 20,000 sits between min and max balance
  const balances = series.map(d => d.balance);
  const minB  = Math.min(...balances);
  const maxB  = Math.max(...balances);
  const range = maxB - minB;

  // Tight Y-axis domain: zoom into actual range + a small buffer so changes are visible
  const padding = Math.max(range * 0.25, 0.5); // at least ±0.5 buffer
  const yMin = +(minB - padding).toFixed(4);
  const yMax = +(maxB + padding).toFixed(4);

  let baselinePct = 50;
  if (range > 0) {
    // 0% = top of chart (maxB), 100% = bottom (minB)
    baselinePct = ((maxB - INITIAL_BALANCE) / range) * 100;
    baselinePct = Math.max(0, Math.min(100, baselinePct));
  }

  const gradFillId = `fill-${chartId}`;
  const gradLineId = `line-${chartId}`;

  return (
    <div
      className="balance-chart-card"
      style={{ borderTop: `2px solid ${accentColor}60` }}
    >
      {/* Header row */}
      <div className="balance-chart-header">
        <div>
          <div className="balance-chart-title" style={{ color: accentColor }}>
            {title}
          </div>
          <div className="balance-chart-meta">
            {betRounds.length} bets · {series.length} rounds
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 20,
            fontWeight: 800,
            lineHeight: 1,
            color: pnlPos ? '#00e5a0' : '#ff4d6d',
            textShadow: pnlPos
              ? '0 0 14px rgba(0,229,160,0.4)'
              : '0 0 14px rgba(255,77,109,0.4)',
          }}>
            {pnlPos ? '+' : ''}{pnl.toFixed(2)}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>
            P &amp; L
          </div>
        </div>
      </div>

      {/* Balance + stats row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 0 8px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        marginBottom: 8,
      }}>
        <div>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 2 }}>
            CURRENT BALANCE
          </div>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 14,
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}>
            {currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="stat-pills">
          <span className="stat-pill ones">✓ {winRounds.length}W</span>
          <span className="stat-pill zeros">✗ {lossRounds}L</span>
          <span className="stat-pill total">{winRate}% WR</span>
        </div>
      </div>

      {/* Area Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart
          data={series}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            {/* Fill gradient: green above baseline, red below */}
            <linearGradient id={gradFillId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"           stopColor="#00e5a0" stopOpacity={0.45} />
              <stop offset={`${baselinePct}%`} stopColor="#00e5a0" stopOpacity={0.10} />
              <stop offset={`${baselinePct}%`} stopColor="#ff4d6d" stopOpacity={0.10} />
              <stop offset="100%"         stopColor="#ff4d6d" stopOpacity={0.45} />
            </linearGradient>
            {/* Stroke gradient: green above baseline, red below */}
            <linearGradient id={gradLineId} x1="0" y1="0" x2="0" y2="1">
              <stop offset={`${baselinePct}%`} stopColor="#00e5a0" stopOpacity={1} />
              <stop offset={`${baselinePct}%`} stopColor="#ff4d6d" stopOpacity={1} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.03)"
            vertical={false}
          />
          <XAxis
            dataKey="round"
            tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
            axisLine={false}
            tickLine={false}
            width={88}
            domain={[yMin, yMax]}
            tickFormatter={v => v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            allowDataOverflow
          />
          <Tooltip content={<ChartTooltip />} />
          <ReferenceLine
            y={INITIAL_BALANCE}
            stroke="rgba(255,255,255,0.2)"
            strokeDasharray="6 3"
            label={{
              value: '20,000',
              position: 'insideTopRight',
              fontSize: 9,
              fill: '#4a5580',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke={`url(#${gradLineId})`}
            strokeWidth={2.5}
            fill={`url(#${gradFillId})`}
            dot={(props) => {
              const { cx, cy, payload } = props;
              if (!payload.isBet) return null;
              return (
                <circle
                  key={payload.round}
                  cx={cx}
                  cy={cy}
                  r={3}
                  fill={payload.isWin ? '#00e5a0' : '#ff4d6d'}
                  stroke="rgba(0,0,0,0.5)"
                  strokeWidth={1}
                />
              );
            }}
            activeDot={{
              r: 6,
              fill: accentColor,
              stroke: 'rgba(0,0,0,0.7)',
              strokeWidth: 2,
            }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────
export default function SummaryPage() {
  const [rawResults, setRawResults] = useState([]);
  const [count, setCount]           = useState(0);
  const [loading, setLoading]       = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    try {
      const res  = await fetch('/api/summary-data', { cache: 'no-store' });
      const json = await res.json();
      if (json.status === 'success') {
        setRawResults(json.results ?? []);
        setCount(json.count ?? 0);
      }
      setLastUpdate(new Date().toLocaleTimeString('en-US', { hour12: false }));
    } catch (e) {
      console.error('summary-data fetch error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  // Pre-compute all 17 series only when raw data changes
  const type1Series = useMemo(
    () => TYPE1_ODDS.map(odd => ({ odd, series: computeBalanceSeries(rawResults, odd, 0) })),
    [rawResults],
  );

  const type2Series = useMemo(
    () =>
      SKIP_VALUES.map(skip => ({
        skip,
        perOdd: TYPE2_ODDS.map(odd => ({
          odd,
          series: computeBalanceSeries(rawResults, odd, skip),
        })),
      })),
    [rawResults],
  );

  return (
    <>
      {/* ── Page header ── */}
      <div className="page-header">
        <h1 className="page-title">Balance Simulation — 17 Graphs</h1>
        <p className="page-subtitle">
          Simulated balance from session start · Fixed bet 0.20 per round · Initial balance 20,000
        </p>
      </div>

      {/* ── Status bar ── */}
      <div className="status-bar">
        <div className="status-item">🎰 {count} rounds in session</div>
        <div className="status-item">📊 17 simulated balance graphs</div>
        <div className="status-item">💰 Bet size: <strong>0.20</strong></div>
        {lastUpdate && (
          <div className="status-item" style={{ marginLeft: 'auto' }}>
            {refreshing ? (
              <span className="refresh-indicator">
                <span className="refresh-spinner" /> syncing…
              </span>
            ) : (
              <span className="refresh-indicator">✓ {lastUpdate}</span>
            )}
          </div>
        )}
      </div>

      {/* ── Rules ── */}
      <div className="rules-card">
        <div className="rule-item">
          <span className="rule-chip up">Win</span>
          <span className="rule-arrow">→</span>
          <span style={{ color: 'var(--accent-green)', fontSize: 12, fontWeight: 600 }}>
            balance += 0.2 × (odd − 1)
          </span>
        </div>
        <div className="rule-item">
          <span className="rule-chip down">Loss</span>
          <span className="rule-arrow">→</span>
          <span style={{ color: 'var(--accent-red)', fontSize: 12, fontWeight: 600 }}>
            balance −= 0.2
          </span>
        </div>
        <div className="rule-item" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          Skipped rounds: balance stays flat until the next bet round.
          Green fill = above 20,000 baseline · Red fill = below baseline.
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-muted)' }}>
          Loading session data…
        </div>
      )}

      {!loading && (
        <>
          {/* ═══════════════════════════════════════════════
              SECTION 1 — Parallel Betting (5 graphs)
          ════════════════════════════════════════════════ */}
          <div className="summary-section">
            <div className="summary-section-header">
              <div className="summary-section-title">📊 Parallel Betting</div>
              <div className="summary-section-sub">
                One graph per odd threshold — bet placed every round simultaneously across all odds
              </div>
            </div>

            <div className="summary-grid-type1">
              {type1Series.map(({ odd, series }) => (
                <BalanceChart
                  key={`t1-${odd}`}
                  chartId={`t1-o${String(odd).replace('.', '_')}`}
                  series={series}
                  title={`Odd ${odd}x`}
                  accentColor={ODD_COLORS[odd]}
                />
              ))}
            </div>
          </div>

          {/* ═══════════════════════════════════════════════
              SECTION 2 — Skip-Interval Betting (12 graphs)
          ════════════════════════════════════════════════ */}
          <div className="summary-section">
            <div className="summary-section-header">
              <div className="summary-section-title">⏱ Skip-Interval Betting</div>
              <div className="summary-section-sub">
                Betting every N+1 rounds — tracking odd 1.5x and 2x across 6 skip depths
              </div>
            </div>

            {type2Series.map(({ skip, perOdd }) => (
              <div key={`skip-${skip}`} className="summary-skip-group">
                {/* Skip group label */}
                <div className="summary-skip-label">
                  <span className="summary-skip-badge">
                    {skip === 0 ? 'Diff 0' : `Diff ${skip}`}
                  </span>
                  <span className="summary-skip-desc">
                    {skip === 0
                      ? 'Continuous — bet every single round'
                      : `Skip ${skip} round${skip > 1 ? 's' : ''} between each bet (bet every ${skip + 1} rounds)`}
                  </span>
                </div>

                {/* 2 charts side by side for this skip value */}
                <div className="summary-grid-type2">
                  {perOdd.map(({ odd, series }) => (
                    <BalanceChart
                      key={`t2-s${skip}-o${odd}`}
                      chartId={`t2-s${skip}-o${String(odd).replace('.', '_')}`}
                      series={series}
                      title={`Odd ${odd}x`}
                      accentColor={SKIP_ODD_COLORS[odd]}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

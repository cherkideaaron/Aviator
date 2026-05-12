'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts';

const FILE_LABELS = ['post_bad_tracking.txt', 'post_bad_tracking2.txt', 'post_bad_tracking3.txt'];
const THRESHOLDS = ['1.21', '1.34', '1.51'];
const FILE_BADGE_CLASS = ['file-badge file-badge-1', 'file-badge file-badge-2', 'file-badge file-badge-3'];
const FILE_ACCENT = ['#5b8dee', '#a78bfa', '#00d4ff'];

const LIST_COLORS = ['#5b8dee', '#a78bfa', '#00d4ff', '#00e5a0', '#ff9a3c', '#ff4d6d'];
const LIST_NAMES = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5'];

const POLL_MS = 3000;

function valueClass(v) {
  if (v > 0) return 'pos';
  if (v < 0) return 'neg';
  return 'neu';
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(13,18,36,0.97)',
      border: '1px solid rgba(99,120,255,0.35)',
      borderRadius: 8,
      padding: '6px 10px',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
      minWidth: 120,
    }}>
      <div style={{ color: '#8b9cc8', marginBottom: 4 }}>Step {label}</div>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.value >= 0 ? '#00e5a0' : '#ff4d6d', fontWeight: 600 }}>
          <span style={{ color: entry.color }}>{entry.name}</span>
          {' '}{entry.value >= 0 ? '+' : ''}{entry.value?.toFixed(2)}
        </div>
      ))}
    </div>
  );
}

function TrackingChart({ fileData, fileIdx }) {
  const accent = FILE_ACCENT[fileIdx];
  const { combinedSeries, stats, lists } = fileData;
  const empty = !combinedSeries || combinedSeries.length <= 1;

  // Build a merged dataset for overlay: one point per step across all lists
  // We display the COMBINED series as the primary line + each list as a faint secondary
  const maxLen = Math.max(
    combinedSeries?.length || 0,
    ...Object.values(lists).map((l) => l.series?.length || 0)
  );

  // For combined chart
  const combinedCurrentY = combinedSeries?.at(-1)?.value ?? 0;

  return (
    <div className="chart-card-large" style={{ borderTop: `2px solid ${accent}33` }}>
      {/* Header */}
      <div className="chart-card-large-header">
        <div>
          <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className={FILE_BADGE_CLASS[fileIdx]}>{THRESHOLDS[fileIdx]}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>{FILE_LABELS[fileIdx]}</span>
          </div>
          <div className="chart-meta" style={{ marginTop: 6 }}>
            Combined view across all 6 tracking lists · {stats.total} values
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div className={`current-value ${valueClass(combinedCurrentY)}`}>
            {combinedCurrentY >= 0 ? '+' : ''}{combinedCurrentY.toFixed(2)}
          </div>
          <div className="stat-pills" style={{ justifyContent: 'flex-end', marginTop: 6 }}>
            <span className="stat-pill ones">✓ {stats.ones}</span>
            <span className="stat-pill zeros">✗ {stats.zeros}</span>
            <span className="stat-pill total">{stats.total} total</span>
          </div>
        </div>
      </div>

      {/* Combined Line Chart */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4 }}>
          COMBINED SEQUENCE (all lists)
        </div>
        {empty ? (
          <div className="empty-state" style={{ height: 140 }}>
            <span className="empty-state-icon">◌</span>
            <span>No tracking data yet</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={combinedSeries} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="index"
                tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
                tickLine={false}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis
                tickCount={6}
                tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
                width={38}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.18)" strokeDasharray="5 3" />
              <Line
                type="monotone"
                dataKey="value"
                stroke={accent}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: accent, stroke: 'rgba(0,0,0,0.5)', strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Per-list overlay chart */}
      <div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4 }}>
          PER LIST BREAKDOWN (overlay)
        </div>

        {/* Legend */}
        <div className="legend" style={{ marginBottom: 6 }}>
          {LIST_COLORS.map((c, i) => (
            <div key={i} className="legend-item">
              <span className="legend-dot" style={{ background: c }} />
              <span>List {i}</span>
              <span style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: (lists[i]?.currentY ?? 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                marginLeft: 2,
              }}>
                ({((lists[i]?.currentY ?? 0) >= 0 ? '+' : '')}{(lists[i]?.currentY ?? 0).toFixed(2)})
              </span>
            </div>
          ))}
        </div>

        {/* Overlay chart — all 6 lists on one chart */}
        {Object.values(lists).every((l) => l.series.length <= 1) ? (
          <div className="empty-state" style={{ height: 100 }}>
            <span className="empty-state-icon">◌</span>
            <span>No individual list data yet</span>
          </div>
        ) : (() => {
          // Merge all list series into a single dataset by index
          const mergedMap = {};
          for (let li = 0; li < 6; li++) {
            const s = lists[li]?.series || [];
            s.forEach(({ index, value }) => {
              if (!mergedMap[index]) mergedMap[index] = { index };
              mergedMap[index][`L${li}`] = value;
            });
          }
          const mergedData = Object.values(mergedMap).sort((a, b) => a.index - b.index);

          return (
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={mergedData} margin={{ top: 4, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="index" hide />
                <YAxis
                  tickCount={5}
                  tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
                  width={38}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 2" />
                {LIST_COLORS.map((c, i) => (
                  <Line
                    key={i}
                    type="monotone"
                    dataKey={`L${i}`}
                    stroke={c}
                    strokeWidth={1.2}
                    dot={false}
                    activeDot={{ r: 3 }}
                    isAnimationActive={false}
                    connectNulls
                    name={`L${i}`}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          );
        })()}
      </div>
    </div>
  );
}

export default function TrackingPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/post-tracking', { cache: 'no-store' });
      const json = await res.json();
      setData(json.data);
      setLastUpdate(new Date().toLocaleTimeString('en-US', { hour12: false }));
    } catch (e) {
      console.error('fetch error:', e);
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

  const totalValues = data?.reduce((acc, f) => acc + f.stats.total, 0) ?? 0;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Post-Bad Tracking — 3 Graphs</h1>
        <p className="page-subtitle">
          Combined cumulative view per file + per-list overlay for comparison
        </p>
      </div>

      {/* Rules */}
      <div className="rules-card">
        <div className="rule-item">
          <span className="rule-chip up">Win</span>
          <span className="rule-arrow">→</span>
          <span style={{ color: 'var(--accent-green)', fontSize: 12, fontWeight: 600 }}>+0.20 (1.21) · +0.33 (1.34) · +0.50 (1.51)</span>
        </div>
        <div className="rule-item">
          <span className="rule-chip down">Loss</span>
          <span className="rule-arrow">→</span>
          <span style={{ color: 'var(--accent-red)', fontSize: 12, fontWeight: 600 }}>−1.00</span>
        </div>
        <div className="rule-item" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          Cumulative profit based on the specific multiplier threshold for each file.
        </div>
      </div>

      {/* Status bar */}
      <div className="status-bar">
        <div className="status-item">
          📁 3 files · 6 lists each
        </div>
        <div className="status-item">
          📊 Total values tracked: <strong>{totalValues}</strong>
        </div>
        {lastUpdate && (
          <div className="status-item" style={{ marginLeft: 'auto' }}>
            {refreshing ? (
              <span className="refresh-indicator">
                <span className="refresh-spinner" /> syncing…
              </span>
            ) : (
              <span className="refresh-indicator">✓ updated {lastUpdate}</span>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading tracking data…
        </div>
      )}

      {!loading && data && (
        <div className="tracking-grid">
          {data.map((fileData, fi) => (
            <TrackingChart key={fi} fileData={fileData} fileIdx={fi} />
          ))}
        </div>
      )}
    </>
  );
}

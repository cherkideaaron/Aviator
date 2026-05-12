'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';

const FILE_LABELS = ['pattern_events.txt', 'pattern_events2.txt', 'pattern_events3.txt'];
const THRESHOLDS = ['1.21', '1.34', '1.51'];
const FILE_BADGE_CLASS = ['file-badge file-badge-1', 'file-badge file-badge-2', 'file-badge file-badge-3'];

// One color per list (0–5)
const LIST_COLORS = ['#5b8dee', '#a78bfa', '#00d4ff', '#00e5a0', '#ff9a3c', '#ff4d6d'];

const POLL_MS = 3000;

function valueClass(v) {
  if (v > 0) return 'pos';
  if (v < 0) return 'neg';
  return 'neu';
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: 'rgba(13,18,36,0.97)',
      border: '1px solid rgba(99,120,255,0.35)',
      borderRadius: 8,
      padding: '6px 10px',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
    }}>
      <div style={{ color: '#8b9cc8' }}>Step <strong style={{ color: '#e8eaf6' }}>{d.index}</strong></div>
      <div style={{ color: d.value >= 0 ? '#00e5a0' : '#ff4d6d', fontWeight: 700 }}>
        {d.value >= 0 ? '+' : ''}{d.value.toFixed(2)}
      </div>
    </div>
  );
}

function MiniChart({ series, color, listIdx }) {
  const currentY = series?.at(-1)?.value ?? 0;
  const empty = !series || series.length <= 1;

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <span className="chart-label" style={{ color }}>List {listIdx}</span>
        {!empty && (
          <span className={`chart-value-badge ${valueClass(currentY)}`}>
            {currentY >= 0 ? '+' : ''}{currentY.toFixed(2)}
          </span>
        )}
      </div>

      {empty ? (
        <div className="empty-state">
          <span className="empty-state-icon">◌</span>
          <span>No data yet</span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={series} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="index" hide />
            <YAxis
              tickCount={5}
              tick={{ fontSize: 9, fill: '#4a5580', fontFamily: 'JetBrains Mono, monospace' }}
              width={32}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 2" />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3, fill: color }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function PatternsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/pattern-events', { cache: 'no-store' });
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

  const totalEventsAll = data?.reduce((acc, f) =>
    acc + Object.values(f.lists).reduce((a, l) => a + (l.eventCount || 0), 0), 0) ?? 0;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Individual List Tracking — 18 Graphs</h1>
        <p className="page-subtitle">
          Live real-time view of all 6 tracking lists for each threshold
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
          Graphs update instantly as results are recorded in the post-bad sequences.
        </div>
      </div>

      {/* Status bar */}
      <div className="status-bar">
        <div className="status-item">
          📁 <strong>3 files</strong> · 6 lists each · 18 graphs total
        </div>
        <div className="status-item">
          📊 Events detected: <strong>{totalEventsAll}</strong>
        </div>
        {lastUpdate && (
          <div className="status-item" style={{ marginLeft: 'auto' }}>
            {refreshing ? (
              <span className="refresh-indicator">
                <span className="refresh-spinner" /> syncing…
              </span>
            ) : (
              <span className="refresh-indicator">
                ✓ updated {lastUpdate}
              </span>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading pattern data…
        </div>
      )}

      {!loading && data && data.map((fileData, fi) => (
        <div key={fi} className="file-group">
          <div className="file-group-header">
            <span className={FILE_BADGE_CLASS[fi]}>{THRESHOLDS[fi]}</span>
            <span className="file-group-title">{FILE_LABELS[fi]}</span>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
              {fileData.totalEvents} results tracked
            </span>
          </div>

          <div className="charts-grid">
            {[0, 1, 2, 3, 4, 5].map((listIdx) => {
              const listData = fileData.lists[listIdx];
              return (
                <MiniChart
                  key={listIdx}
                  series={listData?.series}
                  color={LIST_COLORS[listIdx]}
                  listIdx={listIdx}
                />
              );
            })}
          </div>
        </div>
      ))}
    </>
  );
}

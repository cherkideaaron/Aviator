'use client';

import { useState, useEffect, useCallback } from 'react';

const POLL_MS = 3000;

function PredictionRow({ row }) {
  const isWin = row.prediction === 'WIN';
  const confidenceColor = row.confidence.includes('Very High') ? '#ff9a3c' :
                          row.confidence.includes('High') ? '#00e5a0' :
                          row.confidence.includes('Medium') ? '#00d4ff' : '#ff4d6d';

  const formatPct = (val) => val === null ? '-' : `${val}%`;

  const getPctColor = (val) => {
    if (val === null) return 'var(--text-muted)';
    if (val >= 60) return '#00e5a0';
    if (val >= 50) return '#00d4ff';
    return '#ff4d6d';
  };

  return (
    <tr style={{ 
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      backgroundColor: isWin ? 'rgba(0, 229, 160, 0.05)' : 'transparent'
    }}>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>
        {row.timestamp.split(' ')[1] || row.timestamp}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: '#e8eaf6' }}>
        #{row.row_id}
      </td>
      <td style={{ padding: '12px 16px', fontWeight: 700, color: isWin ? '#00e5a0' : '#ff4d6d' }}>
        {row.prediction}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: '#e8eaf6' }}>
        {(row.probability * 100).toFixed(1)}%
      </td>
      <td style={{ padding: '12px 16px', fontWeight: 600, color: confidenceColor }}>
        {row.confidence}
      </td>
      
      {/* Rolling stats columns */}
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: getPctColor(row.pct_last5) }}>
        {formatPct(row.pct_last5)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: getPctColor(row.pct_last10) }}>
        {formatPct(row.pct_last10)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: getPctColor(row.pct_last20) }}>
        {formatPct(row.pct_last20)}
      </td>

      <td style={{ padding: '12px 16px', fontWeight: 700 }}>
        {row.actual ? (
           row.is_correct ? <span style={{ color: '#00e5a0' }}>✓ {row.actual}</span> : <span style={{ color: '#ff4d6d' }}>✗ {row.actual}</span>
        ) : (
          <span style={{ color: 'var(--text-muted)' }}>Pending...</span>
        )}
      </td>
    </tr>
  );
}

export default function PredictionsPage() {
  const [data, setData] = useState({ rows: [], summary: null });
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/ml-predictions', { cache: 'no-store' });
      const json = await res.json();
      if (json.status === 'success') {
        setData({ rows: json.rows || [], summary: json.summary });
      } else if (json.status === 'empty') {
        setData({ rows: [], summary: null });
      }
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

  const { rows, summary } = data;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">ML Predictions Dashboard</h1>
        <p className="page-subtitle">
          Real-time predictions with probability, confidence, and rolling accuracy stats
        </p>
      </div>

      <div className="status-bar">
        <div className="status-item">
          🤖 Predictions tracked: <strong>{summary ? summary.totalAll : 0}</strong>
        </div>
        {summary && (
          <>
             <div className="status-item">
               WIN Accuracy: <strong style={{ color: 'var(--accent-green)' }}>{summary.winAccuracy}%</strong> ({summary.winCorrect}/{summary.totalWin})
             </div>
             <div className="status-item">
               Overall Acc: <strong>{summary.overallAccuracy}%</strong>
             </div>
          </>
        )}
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

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading predictions data…
        </div>
      ) : rows.length === 0 ? (
        <div className="empty-state" style={{ height: 300, marginTop: '2rem' }}>
          <span className="empty-state-icon">◌</span>
          <span>No predictions data found yet. Run realtime_predictor.py</span>
        </div>
      ) : (
        <div className="table-container" style={{ marginTop: '2rem', background: 'rgba(8,12,28,0.5)', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Time</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>ID</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Prediction</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Probability</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Confidence</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Last 5% Good</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Last 10% Good</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Last 20% Good</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Actual Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <PredictionRow key={idx} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

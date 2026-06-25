'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts';

const POLL_MS = 3000;

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isWin = data.isWin;
    const outcomeColor = isWin ? 'var(--accent-green)' : 'var(--accent-red)';
    return (
      <div className="custom-tooltip" style={{ minWidth: '150px' }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '11px' }}>Bet #{data.index}</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <p style={{ margin: 0 }}>
            Bet Amount: <strong style={{ color: 'var(--text-primary)' }}>${data.betPlaced.toFixed(2)}</strong>
          </p>
          <p style={{ margin: 0 }}>
            Outcome: <strong style={{ color: outcomeColor }}>{isWin ? 'WIN' : 'LOSS'} ({isWin ? '+' : ''}${data.change.toFixed(2)})</strong>
          </p>
          <p style={{ margin: 0 }}>
            Multiplier: <strong style={{ color: 'var(--accent-cyan)' }}>{data.rawValue.toFixed(2)}x</strong>
          </p>
          <p style={{ margin: 0, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '3px', marginTop: '3px' }}>
            Balance: <strong style={{ color: 'var(--text-primary)' }}>${data.balance.toFixed(2)}</strong>
          </p>
          <p style={{ margin: 0 }}>
            Peak: <strong style={{ color: 'var(--accent-cyan)' }}>${(data.maxBalance ?? data.balance).toFixed(2)}</strong>
          </p>
          <p style={{ margin: 0 }}>
            Floor: <strong style={{ color: 'var(--accent-red)' }}>${(data.minBalance ?? data.balance).toFixed(2)}</strong>
          </p>
          <p style={{ margin: 0 }}>
            Consec. Losses: <strong style={{ color: 'var(--accent-orange)' }}>{data.consecutiveLosses}</strong>
          </p>
        </div>
      </div>
    );
  }
  return null;
};

function BetRow({ bet }) {
  const isWin = bet.isWin;
  const rowBg = isWin ? 'rgba(0, 229, 160, 0.05)' : 'rgba(255, 77, 109, 0.03)';
  const outcomeColor = isWin ? '#00e5a0' : '#ff4d6d';

  return (
    <tr style={{ 
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      backgroundColor: rowBg
    }}>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>
        #{bet.index}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: '#e8eaf6', fontWeight: 600 }}>
        ${bet.betPlaced.toFixed(2)}
      </td>
      <td style={{ padding: '12px 16px', fontWeight: 700, color: outcomeColor }}>
        {isWin ? 'WIN' : 'LOSS'}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-cyan)' }}>
        {bet.rawValue.toFixed(2)}x
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, color: outcomeColor }}>
        {isWin ? '+' : ''}${bet.change.toFixed(2)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: '#e8eaf6', fontWeight: 700 }}>
        ${bet.balance.toFixed(2)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: bet.balance < (bet.maxBalance ?? bet.balance) ? 'var(--accent-orange)' : 'var(--accent-green)' }}>
        ${(bet.maxBalance ?? bet.balance).toFixed(2)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-red)' }}>
        ${(bet.minBalance ?? bet.balance).toFixed(2)}
      </td>
      <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: bet.consecutiveLosses > 0 ? 'var(--accent-orange)' : 'var(--text-muted)' }}>
        {bet.consecutiveLosses}
      </td>
    </tr>
  );
}

export default function MartingalePage() {
  const [detailBets, setDetailBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/ml-predictions', { cache: 'no-store' });
      const json = await res.json();
      if (json.status === 'success') {
        setDetailBets(json.detailBets || []);
      } else if (json.status === 'empty') {
        setDetailBets([]);
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

  // Statistics calculation
  const lastBet = detailBets[detailBets.length - 1];
  const endingBalance = lastBet ? lastBet.balance : 5.00;
  const peakBalance = lastBet ? (lastBet.maxBalance ?? endingBalance) : 5.00;
  const floorBalance = lastBet ? (lastBet.minBalance ?? endingBalance) : 5.00;
  const netProfit = endingBalance - 5.00;
  const totalBets = detailBets.length;
  const currentLossStreak = lastBet ? lastBet.consecutiveLosses : 0;
  const peakLossStreak = detailBets.length > 0 ? Math.max(...detailBets.map(b => b.consecutiveLosses)) : 0;
  const roi = ((endingBalance - 5.00) / 5.00) * 100;
  const isRecovering = endingBalance < peakBalance;

  // Show newest bets first in the table
  const displayBets = [...detailBets].reverse();

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Martingale Strategy Dashboard</h1>
        <p className="page-subtitle">
          Real-time simulation of Martingale progression over predicted WIN rounds
        </p>
      </div>

      <div className="status-bar">
        <div className="status-item">
          🎲 Strategy Type: <strong>Martingale (Double on Loss)</strong>
        </div>
        <div className="status-item">
          💰 Base Bet: <strong>$1.00</strong> (resets on peak, doubles on loss)
        </div>
        <div className="status-item">
          📈 Cash out: <strong>2.00x multiplier</strong>
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

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading Martingale logs…
        </div>
      ) : detailBets.length === 0 ? (
        <div className="empty-state" style={{ height: 300, marginTop: '2rem' }}>
          <span className="empty-state-icon">◌</span>
          <span>No betting logs found. Run realtime_predictor.py to log win details.</span>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Simulated Balance</span>
              <span className={`current-value ${netProfit >= 0 ? 'pos' : 'neg'}`} style={{ fontSize: '1.6rem', marginTop: '4px' }}>
                ${endingBalance.toFixed(2)}
              </span>
              <span style={{ fontSize: '10px', color: netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 600, marginTop: '2px' }}>
                {netProfit >= 0 ? '+' : ''}{roi.toFixed(1)}% ROI
              </span>
            </div>
            
            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Net Profit / Loss</span>
              <span className={`current-value ${netProfit >= 0 ? 'pos' : 'neg'}`} style={{ fontSize: '1.6rem', marginTop: '4px' }}>
                {netProfit >= 0 ? '+' : ''}${netProfit.toFixed(2)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                From $5.00 starting
              </span>
            </div>

            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Peak Balance</span>
              <span className="current-value neu" style={{ fontSize: '1.6rem', marginTop: '4px', color: 'var(--accent-cyan)' }}>
                ${peakBalance.toFixed(2)}
              </span>
              <span style={{ fontSize: '10px', color: isRecovering ? 'var(--accent-orange)' : 'var(--accent-green)', fontWeight: 600, marginTop: '2px' }}>
                {isRecovering ? `↓ Recovering (${(endingBalance - peakBalance).toFixed(2)})` : '✓ At Peak'}
              </span>
            </div>

            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Floor Balance</span>
              <span className="current-value neg" style={{ fontSize: '1.6rem', marginTop: '4px' }}>
                ${floorBalance.toFixed(2)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Lowest ever reached
              </span>
            </div>

            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Total Bets Placed</span>
              <span className="current-value neu" style={{ fontSize: '1.6rem', marginTop: '4px', color: 'var(--accent-cyan)' }}>
                {totalBets}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                From win_predictions_detail.txt
              </span>
            </div>

            <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '90px' }}>
              <span className="chart-label">Consecutive Losses</span>
              <span className="current-value neu" style={{ 
                fontSize: '1.6rem', 
                marginTop: '4px', 
                color: currentLossStreak > 0 ? 'var(--accent-orange)' : 'var(--accent-green)' 
              }}>
                {currentLossStreak}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Peak Streak: {peakLossStreak} losses
              </span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
            {/* Balance Trend Chart */}
            <div className="chart-card-large" style={{ minHeight: '350px' }}>
              <div className="chart-card-large-header">
                <div>
                  <h3 className="chart-title">Simulated Balance Trend</h3>
                  <span className="chart-meta">Balance progression starting at $5.00</span>
                </div>
              </div>
              <div style={{ width: '100%', height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={detailBets} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="balanceGlow" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} stopOpacity={0.2}/>
                        <stop offset="95%" stopColor={netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis dataKey="index" tickLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
                    <YAxis domain={['auto', 'auto']} tickLine={false} axisLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="balance"
                      name="Balance ($)"
                      stroke={netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#balanceGlow)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Consecutive Losses Chart */}
            <div className="chart-card-large" style={{ minHeight: '350px' }}>
              <div className="chart-card-large-header">
                <div>
                  <h3 className="chart-title">Consecutive Losses History</h3>
                  <span className="chart-meta">Track of loss streak (resets to 0 immediately on win)</span>
                </div>
              </div>
              <div style={{ width: '100%', height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={detailBets} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis dataKey="index" tickLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} stroke="var(--text-muted)" style={{ fontSize: '11px', fontFamily: 'JetBrains Mono' }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="consecutiveLosses"
                      name="Consecutive Losses"
                      fill="var(--accent-orange)"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="summary-section-header" style={{ marginTop: '1rem' }}>
            <h2 className="summary-section-title">Martingale Bets Log</h2>
            <p className="summary-section-sub">Chronological details of bets executed under simulated strategy</p>
          </div>

          <div className="table-container" style={{ marginTop: '1rem', background: 'rgba(8,12,28,0.5)', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '2rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Bet Index</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Bet Amount</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Outcome</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Raw Multiplier</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Change</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Balance</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Peak</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Floor</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Loss Streak</th>
                </tr>
              </thead>
              <tbody>
                {displayBets.map((bet, idx) => (
                  <BetRow key={idx} bet={bet} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

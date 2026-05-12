'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, ReferenceLine
} from 'recharts';

const INITIAL_BALANCE = 20000;
const POLL_MS = 5000;

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  const balance = data.balance;
  const change = balance - INITIAL_BALANCE;

  return (
    <div style={{
      background: 'rgba(13,18,36,0.97)',
      border: '1px solid rgba(99,120,255,0.35)',
      borderRadius: 12,
      padding: '12px',
      fontSize: 12,
      fontFamily: 'Outfit, sans-serif',
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 8 }}>{data.time}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', marginBottom: 4 }}>
        ${balance.toLocaleString()}
      </div>
      <div style={{ 
        color: change >= 0 ? '#10b981' : '#ef4444', 
        fontWeight: 600,
        display: 'flex',
        alignItems: 'center',
        gap: 4
      }}>
        {change >= 0 ? '▲' : '▼'} ${Math.abs(change).toLocaleString()}
      </div>
      <div style={{ color: '#64748b', fontSize: 11, marginTop: 8 }}>
        Held for {data.rounds_held} rounds
      </div>
    </div>
  );
}

export default function SpecialPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ current: 0, change: 0, latest: 0, high: 0, low: 0, baseline: INITIAL_BALANCE });

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/balance-history', { cache: 'no-store' });
      const json = await res.json();
      
      if (json.status === 'success' && json.data.length > 0) {
        const formattedData = json.data.map((d, i) => ({
          ...d,
          index: i,
          time: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        }));
        
        setData(formattedData);
        
        const latest = formattedData[formattedData.length - 1];
        const firstBalance = formattedData[0].balance;
        const prev = formattedData.length > 1 ? formattedData[formattedData.length - 2] : { balance: firstBalance };
        
        setStats({
          current: latest.balance,
          change: latest.balance - firstBalance,
          latest: latest.balance - prev.balance,
          high: Math.max(...formattedData.map(d => d.balance)),
          low: Math.min(...formattedData.map(d => d.balance)),
          baseline: firstBalance
        });
      }
    } catch (e) {
      console.error('fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8" style={{ minHeight: '100vh' }}>
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-extrabold" style={{ 
            background: 'linear-gradient(135deg, var(--text-primary) 0%, var(--accent-cyan) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            Balance Dynamics
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>Relative to ${stats.baseline.toLocaleString()} session start</p>
        </div>
        <div className="text-right">
            <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Live Updates Every 5s
            </span>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="chart-card-large" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Current Balance</div>
          <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--text-primary)' }}>${stats.current.toLocaleString()}</div>
        </div>

        <div className="chart-card-large" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Total Profit / Loss</div>
          <div style={{ fontSize: '2rem', fontWeight: '700', color: stats.change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {stats.change >= 0 ? '+' : ''}{stats.change.toFixed(2)}
          </div>
        </div>

        <div className="chart-card-large" style={{ padding: '24px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Session High / Low</div>
          <div className="flex items-baseline gap-4">
            <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--accent-green)' }}>${stats.high.toFixed(2)}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>/</span>
            <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--accent-red)' }}>${stats.low.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Main Chart */}
      <div className="chart-card-large" style={{ height: '500px', minHeight: '400px', padding: '32px' }}>
        {loading ? (
          <div className="h-full flex items-center justify-center" style={{ color: 'var(--text-muted)' }}>Loading dynamic data...</div>
        ) : data.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center space-y-4" style={{ color: 'var(--text-muted)' }}>
             <span style={{ fontSize: '2rem' }}>◌</span>
             <span>No balance changes recorded yet</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis 
                dataKey="time" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                minTickGap={30}
              />
              <YAxis 
                domain={['dataMin - 0.1', 'dataMax + 0.1']}
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                tickFormatter={(val) => `$${val.toFixed(2)}`}
                width={70}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={INITIAL_BALANCE} stroke="var(--border-bright)" strokeDasharray="5 5" />
              <Area 
                type="stepAfter" 
                dataKey="balance" 
                stroke="var(--accent-cyan)" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorBalance)" 
                isAnimationActive={false}
                dot={{ r: 2, fill: 'var(--accent-cyan)', strokeWidth: 0 }}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';

export default function NavBar() {
  const pathname = usePathname();
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () =>
      setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <nav className="nav">
      <Link href="/" className="nav-brand">
        <span className="nav-brand-dot" />
        Aviator Analytics
      </Link>

      <ul className="nav-links">
        <li>
          <Link
            href="/patterns"
            className={`nav-link${pathname === '/patterns' ? ' active' : ''}`}
          >
            📊 Pattern Events
          </Link>
        </li>
        <li>
          <Link
            href="/tracking"
            className={`nav-link${pathname === '/tracking' ? ' active' : ''}`}
          >
            📈 Post-Bad Tracking
          </Link>
        </li>
      </ul>

      <div className="nav-status">
        <span className="nav-status-dot" />
        <span>Live</span>
        <span style={{ color: 'var(--text-muted)', margin: '0 0.25rem' }}>|</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{time}</span>
      </div>
    </nav>
  );
}

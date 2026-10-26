import type { FC } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Compass, ArrowLeft, Activity, TrendingUp, AlertTriangle, Wrench, ToggleLeft, Building, ScrollText } from 'lucide-react';

export const NotFound: FC = () => {
  const location = useLocation();

  const quickRoutes = [
    { path: '/live', label: 'Live Monitor', icon: Activity },
    { path: '/history', label: 'History & Trends', icon: TrendingUp },
    { path: '/faults', label: 'Fault Registry', icon: AlertTriangle },
    { path: '/maintenance', label: 'Work Orders', icon: Wrench },
    { path: '/relays', label: 'Relay Control', icon: ToggleLeft },
    { path: '/campus', label: 'Campus Hierarchy', icon: Building },
    { path: '/audit', label: 'Audit Trail', icon: ScrollText },
  ];

  return (
    <div style={{ maxWidth: 760, margin: '2rem auto', padding: '1rem' }}>
      <div className="glass-panel" style={{ padding: '2.5rem 2rem', textAlign: 'center' }}>
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem',
            color: '#ef4444',
          }}
        >
          <Compass size={32} />
        </div>

        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            padding: '3px 10px',
            borderRadius: 9999,
            background: 'rgba(239, 68, 68, 0.15)',
            color: '#f87171',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            fontWeight: 600,
          }}
        >
          404 &bull; Route Not Found
        </span>

        <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#fff', marginTop: '1rem', marginBottom: '0.5rem' }}>
          Unrecognized Substation Console Route
        </h1>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 520, margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
          The path <code style={{ color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: 4 }}>{location.pathname}</code> does not match any active telemetry, diagnostics, or administration endpoints in this monitoring station.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
          <Link
            to="/live"
            className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none', padding: '0.6rem 1.25rem' }}
          >
            <ArrowLeft size={16} />
            Return to Live Telemetry
          </Link>
        </div>

        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem', textAlign: 'left' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
            Valid Monitoring Station Routes
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {quickRoutes.map((r) => {
              const Icon = r.icon;
              return (
                <Link
                  key={r.path}
                  to={r.path}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.4rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                    textDecoration: 'none',
                    fontSize: '0.78rem',
                    transition: 'all var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = '#38bdf8';
                    e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                    e.currentTarget.style.background = 'rgba(56, 189, 248, 0.08)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--text-secondary)';
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                  }}
                >
                  <Icon size={14} />
                  <span>{r.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

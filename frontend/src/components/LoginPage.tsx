import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Shield,
  Lock,
  User,
  ArrowRight,
  AlertCircle,
  Loader2,
  CheckCircle,
  KeyRound,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/useAuth';

interface DemoAccount {
  username: string;
  roleLabel: string;
  roleName: string;
  description: string;
  color: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    username: 'operator1',
    roleLabel: 'Operator',
    roleName: 'operator',
    description: 'Read-only live electrical telemetry and phase status (Block 1 scope)',
    color: '#10b981',
  },
  {
    username: 'shift_incharge1',
    roleLabel: 'Shift In-Charge',
    roleName: 'shift_incharge',
    description: 'Alarm acknowledgment & work order dispatch coordination',
    color: '#0ea5e9',
  },
  {
    username: 'engineer1',
    roleLabel: 'Electrical Engineer',
    roleName: 'electrical_engineer',
    description: 'In-depth diagnostics, fault rectification & trend analysis',
    color: '#8b5cf6',
  },
  {
    username: 'mgmt1',
    roleLabel: 'Management',
    roleName: 'management',
    description: 'Executive campus KPI summary & aggregate energy trends',
    color: '#ec4899',
  },
  {
    username: 'technician1',
    roleLabel: 'Technician',
    roleName: 'technician',
    description: 'Assigned maintenance work orders & repair attempt progress',
    color: '#f59e0b',
  },
  {
    username: 'admin',
    roleLabel: 'Administrator',
    roleName: 'admin',
    description: 'Substation relays, user privileges & security audit trail',
    color: '#3b82f6',
  },
];

export const LoginPage: FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successUser, setSuccessUser] = useState<string | null>(null);

  const fromPath = (location.state as { from?: { pathname: string } })?.from?.pathname || '/live';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanUsername = username.trim();
    if (!cleanUsername) {
      setErrorMessage('Please enter your username.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      const user = await login(cleanUsername, password);
      setSuccessUser(user.username);
      setTimeout(() => {
        // Direct role-based redirection if coming from root or default
        if (fromPath === '/live' || fromPath === '/') {
          if (user.role === 'management') {
            navigate('/management', { replace: true });
            return;
          }
          if (user.role === 'technician') {
            navigate('/maintenance', { replace: true });
            return;
          }
        }
        navigate(fromPath, { replace: true });
      }, 350);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      if (axiosErr.response?.status === 401) {
        setErrorMessage('Invalid username or password. Please verify your credentials.');
      } else if (axiosErr.response?.status === 403) {
        setErrorMessage('This user account is inactive or disabled. Contact system administration.');
      } else if (axiosErr.response?.data?.detail) {
        setErrorMessage(`Authentication failed: ${axiosErr.response.data.detail}`);
      } else {
        setErrorMessage('Unable to connect to authentication server. Please verify FastAPI backend is active.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectDemoAccount = (demoUser: string) => {
    setUsername(demoUser);
    setPassword('demo123');
    setErrorMessage(null);
  };

  return (
    <div style={{ maxWidth: 840, margin: '2rem auto', padding: '1rem' }}>
      <div className="glass-panel" style={{ padding: '2.5rem 2rem' }}>
        {/* System Title and Branding Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
              flexShrink: 0,
            }}
          >
            <Zap size={30} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
              <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff', margin: 0, letterSpacing: '-0.01em' }}>
                IoT-Based Power Monitoring and Fault Identification System
              </h1>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 4 }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.68rem',
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  fontWeight: 600,
                }}
              >
                ROLE-BASED CONTROL ROOM
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                3-Phase 4-Wire Substation Monitoring Interface
              </span>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: '#fca5a5',
              fontSize: '0.85rem',
            }}
            role="alert"
          >
            <AlertCircle size={18} style={{ flexShrink: 0, color: '#ef4444' }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Alert */}
        {successUser && (
          <div
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: '#6ee7b7',
              fontSize: '0.85rem',
            }}
          >
            <CheckCircle size={18} style={{ flexShrink: 0, color: '#10b981' }} />
            <span>Authenticated as <strong>{successUser}</strong>. Initializing secure session...</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label
                htmlFor="username-input"
                style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}
              >
                Account Username
              </label>
              <div style={{ position: 'relative' }}>
                <User
                  size={16}
                  style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                />
                <input
                  id="username-input"
                  type="text"
                  autoComplete="username"
                  required
                  disabled={isSubmitting}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. operator1, engineer1, admin"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.75rem 0.65rem 2.25rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.9rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password-input"
                style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={16}
                  style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                />
                <input
                  id="password-input"
                  type="password"
                  autoComplete="current-password"
                  required
                  disabled={isSubmitting}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter account credentials"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.75rem 0.65rem 2.25rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.9rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary"
              style={{
                marginTop: '0.5rem',
                padding: '0.75rem 1.25rem',
                fontSize: '0.92rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Control Room</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Demo Credentials Switcher */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
              Operational Role Testing Profiles (Click to Load)
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Password: demo123
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() => handleSelectDemoAccount(account.username)}
                style={{
                  padding: '0.75rem 0.85rem',
                  borderRadius: 'var(--radius-md)',
                  background: username === account.username ? `${account.color}18` : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${username === account.username ? `${account.color}60` : 'var(--border-subtle)'}`,
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 3,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <KeyRound size={13} style={{ color: account.color }} />
                    <strong style={{ fontSize: '0.84rem', color: '#fff' }}>{account.username}</strong>
                  </div>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      textTransform: 'uppercase',
                      padding: '1px 5px',
                      borderRadius: 3,
                      color: account.color,
                      background: `${account.color}15`,
                    }}
                  >
                    {account.roleLabel}
                  </span>
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  {account.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Security & Access Boundary Notice */}
        <div
          style={{
            padding: '0.85rem 1rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: '0.76rem',
            color: 'var(--text-muted)',
          }}
        >
          <Shield size={16} style={{ color: '#38bdf8', flexShrink: 0 }} />
          <span>
            Access to telemetry, alarm lifecycle, SSR contactor states, and campus topology is strictly restricted to authenticated personnel. All administrative mutations and relay commands are recorded in the system audit trail.
          </span>
        </div>
      </div>
    </div>
  );
};

import type { ReactNode } from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Loader2 } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import type { UserRole } from '../types/api';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh', gap: '0.75rem', color: '#38bdf8' }}>
        <Loader2 className="animate-spin" size={24} />
        <span style={{ fontSize: '0.9rem' }}>Verifying authentication session...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

interface RoleRouteProps {
  children: ReactNode;
  allowedRoles: UserRole[];
  pageTitle?: string;
}

export function RoleRoute({ children, allowedRoles, pageTitle = 'Restricted View' }: RoleRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh', gap: '0.75rem', color: '#38bdf8' }}>
        <Loader2 className="animate-spin" size={24} />
        <span style={{ fontSize: '0.9rem' }}>Checking authorization credentials...</span>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return (
      <div style={{ maxWidth: 640, margin: '3rem auto', padding: '1rem' }}>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444',
              margin: '0 auto 1.25rem',
            }}
          >
            <ShieldAlert size={30} />
          </div>

          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
            Access Denied: Role Unauthorized
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
            Access to <strong>{pageTitle}</strong> requires{' '}
            <strong style={{ color: '#38bdf8' }}>{allowedRoles.join(' or ')}</strong> privileges.
            Your current authenticated role is{' '}
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase',
                padding: '2px 8px',
                borderRadius: 4,
                background: 'rgba(255, 255, 255, 0.1)',
                color: '#fff',
                fontSize: '0.8rem',
              }}
            >
              {user.role}
            </span>.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
            <Link
              to="/live"
              className="btn btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}
            >
              <ArrowLeft size={16} />
              Return to Live Monitor
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

interface PublicOnlyRouteProps {
  children: ReactNode;
}

export function PublicOnlyRoute({ children }: PublicOnlyRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    const fromPath = (location.state as { from?: { pathname: string } })?.from?.pathname || '/live';
    return <Navigate to={fromPath} replace />;
  }

  return <>{children}</>;
}

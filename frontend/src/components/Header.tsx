import { useState } from 'react';
import type { FC } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  Zap,
  Activity,
  TrendingUp,
  AlertTriangle,
  Wrench,
  ToggleLeft,
  Building,
  ScrollText,
  Bell,
  Radio,
  Play,
  Menu,
  X,
  LogOut,
  LogIn,
  UserCheck,
  BarChart3,
  Users,
} from 'lucide-react';
import { useAuth } from '../context/useAuth';
import type { Device, SystemStatus, NotificationItem } from '../types/api';

interface HeaderProps {
  devices: Device[];
  selectedDeviceId: number;
  onSelectDevice: (id: number) => void;
  systemStatus: SystemStatus;
  notifications: NotificationItem[];
  onMarkNotificationRead: (id: number) => void;
  onMarkAllNotificationsRead: () => void;
  onOpenSimulate: () => void;
  isLiveBackend: boolean;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export const Header: FC<HeaderProps> = ({
  devices,
  selectedDeviceId,
  onSelectDevice,
  systemStatus,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
  onOpenSimulate,
  isLiveBackend,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const getStatusClass = (status: SystemStatus) => {
    switch (status) {
      case 'Normal':
        return 'normal';
      case 'Warning':
        return 'warning';
      case 'Fault':
        return 'fault';
      case 'Sensor/Communication Error':
        return 'sensor';
      case 'Offline':
      default:
        return 'offline';
    }
  };

  const getRoleTheme = (role: string) => {
    switch (role) {
      case 'admin':
        return { color: '#60a5fa', bg: 'rgba(59, 130, 246, 0.2)', border: 'rgba(59, 130, 246, 0.4)', label: 'Admin' };
      case 'shift_incharge':
        return { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.2)', border: 'rgba(56, 189, 248, 0.4)', label: 'Shift In-Charge' };
      case 'electrical_engineer':
        return { color: '#a78bfa', bg: 'rgba(167, 139, 250, 0.2)', border: 'rgba(167, 139, 250, 0.4)', label: 'Engineer' };
      case 'management':
        return { color: '#f472b6', bg: 'rgba(244, 114, 182, 0.2)', border: 'rgba(244, 114, 182, 0.4)', label: 'Management' };
      case 'technician':
        return { color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 0.4)', label: 'Technician' };
      case 'operator':
      default:
        return { color: '#34d399', bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 0.4)', label: 'Operator' };
    }
  };

  const getNavLinks = () => {
    if (!isAuthenticated || !user) {
      return [];
    }

    const role = user.role;
    if (role === 'management') {
      return [
        { to: '/management', label: 'Management KPIs', icon: BarChart3 },
        { to: '/live', label: 'Live Monitor', icon: Activity },
        { to: '/history', label: 'History', icon: TrendingUp },
        { to: '/campus', label: 'Campus', icon: Building },
      ];
    }

    if (role === 'technician') {
      return [
        { to: '/maintenance', label: 'My Work Orders', icon: Wrench },
        { to: '/live', label: 'Live Monitor', icon: Activity },
        { to: '/history', label: 'History', icon: TrendingUp },
        { to: '/faults', label: 'Faults', icon: AlertTriangle },
      ];
    }

    if (role === 'operator') {
      return [
        { to: '/live', label: 'Live Monitor', icon: Activity },
        { to: '/history', label: 'History', icon: TrendingUp },
        { to: '/faults', label: 'Faults (Read-Only)', icon: AlertTriangle },
        { to: '/campus', label: 'Campus', icon: Building },
      ];
    }

    if (role === 'admin') {
      return [
        { to: '/live', label: 'Live Monitor', icon: Activity },
        { to: '/history', label: 'History', icon: TrendingUp },
        { to: '/faults', label: 'Faults', icon: AlertTriangle },
        { to: '/maintenance', label: 'Work Orders', icon: Wrench },
        { to: '/relays', label: 'Relays', icon: ToggleLeft },
        { to: '/management', label: 'KPIs', icon: BarChart3 },
        { to: '/campus', label: 'Campus', icon: Building },
        { to: '/users', label: 'Users', icon: Users },
        { to: '/audit', label: 'Audit', icon: ScrollText },
      ];
    }

    // shift_incharge & electrical_engineer
    return [
      { to: '/live', label: 'Live Monitor', icon: Activity },
      { to: '/history', label: 'History', icon: TrendingUp },
      { to: '/faults', label: 'Faults', icon: AlertTriangle },
      { to: '/maintenance', label: 'Work Orders', icon: Wrench },
      { to: '/relays', label: 'Relays', icon: ToggleLeft },
      { to: '/campus', label: 'Campus', icon: Building },
    ];
  };

  const navLinks = getNavLinks();

  return (
    <header className="header">
      {/* Brand */}
      <Link to="/live" className="header-brand" style={{ textDecoration: 'none' }} onClick={() => setMobileMenuOpen(false)}>
        <div className="brand-icon-wrapper">
          <Zap size={22} className="text-white" />
        </div>
        <div className="brand-titles">
          <span className="brand-title">
            GridSense
            <span className="brand-badge-pill">
              3-PHASE 4-WIRE
            </span>
          </span>
          <span className="brand-subtitle">POWER MONITORING &amp; FAULT IDENTIFICATION SYSTEM</span>
        </div>
      </Link>

      {/* Desktop Center Controls: Device Switcher & Route NavLinks */}
      <div className="header-center desktop-nav">
        {/* Device Switcher */}
        <div className="device-select-box" title="Select Monitoring Device">
          <Radio size={16} style={{ color: isLiveBackend ? '#10b981' : '#f59e0b' }} />
          <select
            value={selectedDeviceId}
            onChange={(e) => onSelectDevice(Number(e.target.value))}
            aria-label="Select Monitoring Device"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.device_id})
              </option>
            ))}
          </select>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="nav-tabs" aria-label="Main Navigation">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-tab-btn ${isActive ? 'active' : ''}`}
              >
                <Icon size={15} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Header Actions: Simulation, Badges, Notifications, Mobile Hamburger */}
      <div className="header-actions">
        {/* Simulation / Injection Trigger (Desktop) */}
        <button
          type="button"
          className="btn btn-secondary desktop-action-btn"
          onClick={onOpenSimulate}
          title="Inject Test Conditions to evaluate Rule Engine"
          style={{ fontSize: '0.78rem', padding: '0.4rem 0.75rem' }}
        >
          <Play size={13} style={{ color: '#06b6d4' }} />
          <span>Simulate Fault</span>
        </button>

        {/* System Status Badge */}
        <div className={`status-badge ${getStatusClass(systemStatus)}`}>
          <span className="status-dot"></span>
          <span className="status-badge-text">{systemStatus}</span>
        </div>

        {/* Backend Connectivity Indicator (Desktop) */}
        <div
          className="desktop-action-btn"
          title={isLiveBackend ? 'Connected to FastAPI Backend (PostgreSQL)' : 'FastAPI Backend Disconnected or Unreachable'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            fontSize: '0.72rem',
            padding: '4px 8px',
            borderRadius: 6,
            background: isLiveBackend ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            border: `1px solid ${isLiveBackend ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
            color: isLiveBackend ? '#34d399' : '#fbbf24',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }}></span>
          <span>{isLiveBackend ? 'API LIVE' : 'API OFFLINE'}</span>
        </div>

        {/* Notification Bell */}
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.45rem', position: 'relative' }}
            onClick={() => setShowNotifications(!showNotifications)}
            aria-label="View notifications"
          >
            <Bell size={17} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: -4,
                  right: -4,
                  background: '#ef4444',
                  color: '#fff',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  width: 17,
                  height: 17,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 8px rgba(239, 68, 68, 0.6)',
                }}
              >
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Flyout Drawer */}
          {showNotifications && (
            <div
              style={{
                position: 'absolute',
                top: '120%',
                right: 0,
                width: 340,
                maxWidth: '90vw',
                background: 'var(--bg-card-elevated)',
                border: '1px solid var(--border-highlight)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 100,
                padding: '1rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>System Alerts</span>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={onMarkAllNotificationsRead}
                    style={{ background: 'none', border: 'none', color: '#38bdf8', fontSize: '0.72rem', cursor: 'pointer' }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 300, overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    No alerts logged
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      style={{
                        padding: '0.65rem',
                        borderRadius: 'var(--radius-sm)',
                        background: n.is_read ? 'rgba(255, 255, 255, 0.02)' : 'rgba(56, 189, 248, 0.06)',
                        border: `1px solid ${n.is_read ? 'var(--border-subtle)' : 'rgba(56, 189, 248, 0.25)'}`,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 3,
                        cursor: 'pointer',
                      }}
                      onClick={() => onMarkNotificationRead(n.id)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.78rem', color: n.severity === 'warning' ? '#fbbf24' : n.severity === 'fault' ? '#f87171' : '#60a5fa' }}>
                          {n.title}
                        </span>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                          {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', margin: 0 }}>
                        {n.message}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Authentication State & Actions */}
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div
              className="user-profile-badge"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '0.78rem',
                padding: '4px 8px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-subtle)',
              }}
              title={`Logged in as ${user.username} (${user.role})${user.assigned_block_id ? ` - Scoped to Block #${user.assigned_block_id}` : ''}`}
            >
              <UserCheck
                size={14}
                style={{
                  color: getRoleTheme(user.role).color,
                }}
              />
              <span style={{ fontWeight: 600, color: '#fff' }}>{user.username}</span>
              <span
                style={{
                  fontSize: '0.65rem',
                  textTransform: 'uppercase',
                  fontFamily: 'var(--font-mono)',
                  padding: '1px 5px',
                  borderRadius: 3,
                  fontWeight: 700,
                  background: getRoleTheme(user.role).bg,
                  color: getRoleTheme(user.role).color,
                  border: `1px solid ${getRoleTheme(user.role).border}`,
                }}
              >
                {getRoleTheme(user.role).label}
              </span>
              {user.assigned_block_id && (
                <span
                  style={{
                    fontSize: '0.62rem',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 4px',
                    borderRadius: 2,
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: 'var(--text-secondary)',
                  }}
                  title={`Restricted to Block #${user.assigned_block_id}`}
                >
                  BLK {user.assigned_block_id}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={logout}
              className="btn btn-secondary auth-gate-btn"
              title="Sign out of control room session"
              style={{ padding: '0.45rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <NavLink
            to="/login"
            className={({ isActive }) => `btn btn-secondary auth-gate-btn ${isActive ? 'active' : ''}`}
            title="Sign in with credentials"
            style={{ padding: '0.45rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.78rem' }}
          >
            <LogIn size={15} />
            <span>Sign In</span>
          </NavLink>
        )}

        {/* Mobile / Tablet Menu Toggle */}
        <button
          type="button"
          className="btn btn-secondary mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="mobile-nav-drawer" role="dialog" aria-modal="true">
          <div className="mobile-nav-section">
            <div className="mobile-nav-section-title">Active Monitoring Substation</div>
            <div className="device-select-box" style={{ width: '100%' }}>
              <Radio size={16} style={{ color: isLiveBackend ? '#10b981' : '#f59e0b' }} />
              <select
                value={selectedDeviceId}
                onChange={(e) => {
                  onSelectDevice(Number(e.target.value));
                  setMobileMenuOpen(false);
                }}
                style={{ width: '100%' }}
                aria-label="Select Monitoring Device"
              >
                {devices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.device_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mobile-nav-section">
            <div className="mobile-nav-section-title">Navigation Views</div>
            <nav className="mobile-nav-links">
              {navLinks.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
              {isAuthenticated && user ? (
                <button
                  type="button"
                  className="mobile-nav-link"
                  style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', color: '#f87171' }}
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                >
                  <LogOut size={18} />
                  <span>Sign Out ({user.username})</span>
                </button>
              ) : (
                <NavLink
                  to="/login"
                  className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <LogIn size={18} />
                  <span>Sign In</span>
                </NavLink>
              )}
            </nav>
          </div>

          <div className="mobile-nav-section" style={{ borderBottom: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                onOpenSimulate();
                setMobileMenuOpen(false);
              }}
              style={{ width: '100%', justifyContent: 'center', padding: '0.65rem' }}
            >
              <Play size={14} style={{ color: '#06b6d4' }} />
              <span>Simulate Electrical Fault</span>
            </button>

            <div
              title={isLiveBackend ? 'Connected to FastAPI Backend (PostgreSQL)' : 'FastAPI Backend Disconnected or Unreachable'}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                fontSize: '0.75rem',
                padding: '6px',
                borderRadius: 6,
                background: isLiveBackend ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                border: `1px solid ${isLiveBackend ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                color: isLiveBackend ? '#34d399' : '#fbbf24',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor' }}></span>
              <span>{isLiveBackend ? 'BACKEND CONNECTED: POSTGRESQL LIVE' : 'BACKEND DISCONNECTED: FASTAPI OFFLINE'}</span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

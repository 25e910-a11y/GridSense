import { useState, useEffect } from 'react';
import type { FC, FormEvent } from 'react';
import {
  Users,
  Shield,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Edit2,
  X,
  Lock,
} from 'lucide-react';
import { api } from '../services/api';
import type { UserItem, UserRole, Block, Floor } from '../types/api';

interface UserManagementViewProps {
  blocks: Block[];
  floors: Floor[];
}

const AVAILABLE_ROLES: { role: UserRole; label: string; desc: string; color: string }[] = [
  { role: 'operator', label: 'Operator', desc: 'Read-only live electrical monitoring & phase alarms', color: '#10b981' },
  { role: 'shift_incharge', label: 'Shift In-Charge', desc: 'Fault acknowledgement & maintenance dispatch', color: '#0ea5e9' },
  { role: 'electrical_engineer', label: 'Electrical Engineer', desc: 'In-depth diagnostics & fault rectification', color: '#8b5cf6' },
  { role: 'management', label: 'Management', desc: 'Campus-wide KPI summaries & executive trends', color: '#ec4899' },
  { role: 'technician', label: 'Technician', desc: 'Assigned work orders, repair logs & progress', color: '#f59e0b' },
  { role: 'admin', label: 'Administrator', desc: 'Full system control, SSR actuation & RBAC configuration', color: '#3b82f6' },
];

export const UserManagementView: FC<UserManagementViewProps> = ({ blocks, floors }) => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Edit modal state
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [editRole, setEditRole] = useState<UserRole>('operator');
  const [editIsActive, setEditIsActive] = useState<boolean>(true);
  const [editBlockId, setEditBlockId] = useState<string>('');
  const [editFloorId, setEditFloorId] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch {
      setError('Failed to fetch user accounts. Ensure you are authenticated as an Administrator.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const data = await api.getUsers();
        if (!ignore) {
          setUsers(data);
        }
      } catch {
        if (!ignore) {
          setError('Failed to fetch user accounts. Ensure you are authenticated as an Administrator.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, []);

  const handleOpenEdit = (user: UserItem) => {
    setEditingUser(user);
    setEditRole(user.role);
    setEditIsActive(user.is_active);
    setEditBlockId(user.assigned_block_id != null ? String(user.assigned_block_id) : '');
    setEditFloorId(user.assigned_floor_id != null ? String(user.assigned_floor_id) : '');
    setModalError(null);
  };

  const handleCloseEdit = () => {
    setEditingUser(null);
    setModalError(null);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;

    setIsSaving(true);
    setModalError(null);
    try {
      const updated = await api.updateUser(editingUser.id, {
        role: editRole,
        is_active: editIsActive,
        assigned_block_id: editBlockId ? Number(editBlockId) : null,
        assigned_floor_id: editFloorId ? Number(editFloorId) : null,
      });

      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setSuccessMessage(`User "${updated.username}" privileges successfully updated to ${updated.role.toUpperCase()}.`);
      handleCloseEdit();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setModalError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to update user privileges.');
    } finally {
      setIsSaving(false);
    }
  };

  const getRoleBadge = (role: UserRole) => {
    const roleInfo = AVAILABLE_ROLES.find((r) => r.role === role);
    const color = roleInfo?.color || '#94a3b8';
    return (
      <span
        style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          padding: '2px 8px',
          borderRadius: 4,
          background: `${color}20`,
          color: color,
          border: `1px solid ${color}40`,
        }}
      >
        {roleInfo?.label || role}
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header Banner */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--radius-md)',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#60a5fa',
              }}
            >
              <Users size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                  User &amp; Operational Role Administration
                </h1>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(59, 130, 246, 0.15)',
                    color: '#60a5fa',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    fontWeight: 600,
                  }}
                >
                  ADMIN PRIVILEGED
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
                Manage campus role assignments, operational permissions, and facility location scoping
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchUsers}
            disabled={isLoading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh Users</span>
          </button>
        </div>
      </div>

      {successMessage && (
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            color: '#6ee7b7',
            fontSize: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <CheckCircle size={18} style={{ color: '#10b981', flexShrink: 0 }} />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.72rem', padding: '2px 8px' }}
            onClick={() => setSuccessMessage(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div
          style={{
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#fca5a5',
            fontSize: '0.85rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
          Registered Personnel &amp; Scopes
        </h2>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Every role update is verified server-side and recorded in the immutable security audit log
        </p>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Assigned Role</th>
                <th>Status</th>
                <th>Location Scope</th>
                <th>Registration Date</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No users found or loading user registry...
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const assignedBlock = blocks.find((b) => b.id === u.assigned_block_id);
                  const assignedFloor = floors.find((f) => f.id === u.assigned_floor_id);

                  return (
                    <tr key={u.id}>
                      <td>
                        <strong style={{ color: '#fff', fontSize: '0.88rem' }}>{u.username}</strong>
                      </td>
                      <td>{getRoleBadge(u.role)}</td>
                      <td>
                        <span
                          style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: u.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: u.is_active ? '#34d399' : '#f87171',
                            border: `1px solid ${u.is_active ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                          }}
                        >
                          {u.is_active ? 'ACTIVE' : 'SUSPENDED'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          {assignedBlock ? assignedBlock.name : 'Campus Wide'}
                          {assignedFloor ? ` • Floor ${assignedFloor.floor_number}` : ''}
                        </span>
                      </td>
                      <td>
                        <span className="mono-val" style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                          {u.created_at ? new Date(u.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : 'Seeded Account'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem' }}
                          onClick={() => handleOpenEdit(u)}
                        >
                          <Edit2 size={12} />
                          <span>Edit Privileges</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit User Modal */}
      {editingUser && (
        <div className="modal-overlay" onClick={handleCloseEdit}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <h3 className="modal-title">
                Modify Privileges for {editingUser.username}
              </h3>
              <button type="button" className="modal-close-btn" onClick={handleCloseEdit}>
                <X size={18} />
              </button>
            </div>

            {modalError && (
              <div
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: 6,
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  color: '#fca5a5',
                  fontSize: '0.82rem',
                }}
              >
                <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0 }} />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                  System Role
                </label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value as UserRole)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.88rem',
                  }}
                >
                  {AVAILABLE_ROLES.map((r) => (
                    <option key={r.role} value={r.role}>
                      {r.label} ({r.role})
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                  {AVAILABLE_ROLES.find((r) => r.role === editRole)?.desc}
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                  Assigned Campus Block (Location Scope)
                </label>
                <select
                  value={editBlockId}
                  onChange={(e) => setEditBlockId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.88rem',
                  }}
                >
                  <option value="">Campus-Wide (All Blocks Permitted)</option>
                  {blocks.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code || `BLK-${b.id}`})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                  Assigned Floor (Optional Floor Scope)
                </label>
                <select
                  value={editFloorId}
                  onChange={(e) => setEditFloorId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.88rem',
                  }}
                >
                  <option value="">All Floors in Block</option>
                  {floors
                    .filter((f) => !editBlockId || f.block_id === Number(editBlockId))
                    .map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} (Floor {f.floor_number})
                      </option>
                    ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: '0.5rem' }}>
                <input
                  type="checkbox"
                  id="user-active-checkbox"
                  checked={editIsActive}
                  onChange={(e) => setEditIsActive(e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: '#38bdf8' }}
                />
                <label htmlFor="user-active-checkbox" style={{ fontSize: '0.84rem', color: '#fff', cursor: 'pointer' }}>
                  Account Active (Uncheck to suspend session login)
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={handleCloseEdit} disabled={isSaving}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSaving}>
                  {isSaving ? 'Saving Changes...' : 'Save Privileges'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role and Permissions Reference Guide */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <Shield size={18} style={{ color: '#60a5fa' }} />
          <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff', margin: 0 }}>
            Operational Role Definitions &amp; Security Boundaries
          </h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
          {AVAILABLE_ROLES.map((r) => (
            <div
              key={r.role}
              style={{
                padding: '0.75rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <Lock size={12} style={{ color: r.color }} />
                <strong style={{ fontSize: '0.82rem', color: '#fff' }}>{r.label}</strong>
              </div>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                {r.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

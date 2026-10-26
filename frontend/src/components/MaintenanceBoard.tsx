import { useState } from 'react';
import type { FC } from 'react';
import {
  Wrench,
  CheckCircle2,
  Send,
  User,
  CheckSquare,
  ArrowRight,
} from 'lucide-react';
import type { WorkOrder } from '../types/api';

interface MaintenanceBoardProps {
  workOrders: WorkOrder[];
  onAddAttempt: (workOrderId: number, note: string) => Promise<void>;
  onUpdateStatus: (
    workOrderId: number,
    status: 'in_progress' | 'restored' | 'closed',
    diagnosis?: string
  ) => Promise<void>;
}

export const MaintenanceBoard: FC<MaintenanceBoardProps> = ({
  workOrders,
  onAddAttempt,
  onUpdateStatus,
}) => {
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(
    workOrders.length > 0 ? workOrders[0].id : null
  );
  const [newNote, setNewNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedOrder = workOrders.find((o) => o.id === selectedOrderId) || workOrders[0];

  const handleSendAttempt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder || !newNote.trim()) return;
    setIsSubmitting(true);
    try {
      await onAddAttempt(selectedOrder.id, newNote.trim());
      setNewNote('');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'assigned':
        return '#3b82f6';
      case 'in_progress':
        return '#f59e0b';
      case 'restored':
        return '#10b981';
      case 'closed':
        return '#64748b';
      default:
        return '#94a3b8';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Wrench size={20} style={{ color: '#0ea5e9' }} />
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
              Maintenance Dispatch &amp; Work Order Tracker
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Phase E standard lifecycle: Assigned → In Progress → Restored → Closed
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 2fr', gap: '1.5rem' }}>
        {/* Work Orders List / Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
            Work Orders ({workOrders.length})
          </span>

          {workOrders.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No active work orders. Dispatched faults will appear here.
            </div>
          ) : (
            workOrders.map((order) => {
              const isSelected = selectedOrder?.id === order.id;
              return (
                <div
                  key={order.id}
                  onClick={() => setSelectedOrderId(order.id)}
                  style={{
                    padding: '0.85rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'rgba(56, 189, 248, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.35)' : 'var(--border-subtle)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                      WO #{order.id}
                    </span>
                    <span
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: getStatusColor(order.status),
                        background: `${getStatusColor(order.status)}1a`,
                        border: `1px solid ${getStatusColor(order.status)}40`,
                      }}
                    >
                      {order.status.replace('_', ' ')}
                    </span>
                  </div>

                  <strong style={{ fontSize: '0.88rem', color: '#fff', display: 'block', marginBottom: 4 }}>
                    {order.fault_type || 'Electrical Maintenance Order'}
                  </strong>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <User size={12} />
                      {order.assigned_to}
                    </span>
                    <span>{new Date(order.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Order Detail & Timeline */}
        {selectedOrder ? (
          <div
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {/* Order Header & Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <h3 style={{ fontSize: '1.15rem', color: '#fff', fontWeight: 700 }}>
                    Work Order #{selectedOrder.id}: {selectedOrder.fault_type || 'Maintenance Incident'}
                  </h3>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '3px 8px',
                      borderRadius: 4,
                      color: getStatusColor(selectedOrder.status),
                      background: `${getStatusColor(selectedOrder.status)}20`,
                      border: `1px solid ${getStatusColor(selectedOrder.status)}40`,
                    }}
                  >
                    {selectedOrder.status.replace('_', ' ')}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', gap: 14 }}>
                  <span>Assigned To: <strong style={{ color: '#fff' }}>{selectedOrder.assigned_to}</strong></span>
                  <span>Dispatched: <strong style={{ color: '#fff' }}>{new Date(selectedOrder.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</strong></span>
                </div>
              </div>

              {/* Status Action Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {selectedOrder.status === 'assigned' && (
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '0.75rem' }}
                    onClick={() => onUpdateStatus(selectedOrder.id, 'in_progress')}
                  >
                    <ArrowRight size={13} />
                    Begin Work
                  </button>
                )}
                {selectedOrder.status === 'in_progress' && (
                  <button
                    type="button"
                    className="btn btn-success"
                    style={{ fontSize: '0.75rem' }}
                    onClick={() => onUpdateStatus(selectedOrder.id, 'restored', 'Load balanced and restored to nominal operating parameters.')}
                  >
                    <CheckSquare size={13} />
                    Mark Restored
                  </button>
                )}
                {selectedOrder.status === 'restored' && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', borderColor: '#10b981', color: '#34d399' }}
                    onClick={() => onUpdateStatus(selectedOrder.id, 'closed', selectedOrder.diagnosis || 'Restored and verified.')}
                  >
                    <CheckCircle2 size={13} />
                    Close Order &amp; Rectify
                  </button>
                )}
              </div>
            </div>

            {/* Diagnosis / Initial Findings */}
            {selectedOrder.diagnosis && (
              <div style={{ padding: '0.85rem', borderRadius: 8, background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600, display: 'block', marginBottom: 2 }}>
                  Diagnosis &amp; Inspection Plan
                </span>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', margin: 0 }}>
                  {selectedOrder.diagnosis}
                </p>
              </div>
            )}

            {/* Timeline of Work Attempts */}
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em', display: 'block', marginBottom: '0.75rem' }}>
                Chronological Activity &amp; Field Attempts ({(selectedOrder.attempts || []).length})
              </span>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: 220, overflowY: 'auto', paddingRight: 4 }}>
                {(!selectedOrder.attempts || selectedOrder.attempts.length === 0) ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                    No work attempts logged yet. Post an attempt note below.
                  </div>
                ) : (
                  selectedOrder.attempts.map((attempt, idx) => (
                    <div
                      key={attempt.id || idx}
                      style={{
                        padding: '0.75rem 0.9rem',
                        borderRadius: 6,
                        background: 'rgba(255, 255, 255, 0.03)',
                        borderLeft: '3px solid #0ea5e9',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 3,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                        <strong style={{ color: '#fff' }}>{attempt.created_by || 'Technician'}</strong>
                        <span style={{ color: 'var(--text-muted)' }}>
                          {new Date(attempt.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                        {attempt.note}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Add Attempt Form */}
            {selectedOrder.status !== 'closed' && (
              <form onSubmit={handleSendAttempt} style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ padding: '0.5rem 0.85rem', fontSize: '0.82rem' }}
                  placeholder="Log field measurement, test note, or action taken..."
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  disabled={isSubmitting}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ whiteSpace: 'nowrap', padding: '0.5rem 1rem' }}
                  disabled={isSubmitting || !newNote.trim()}
                >
                  <Send size={14} />
                  Add Note
                </button>
              </form>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};

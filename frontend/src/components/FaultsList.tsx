import { useState } from 'react';
import type { FC } from 'react';
import {
  CheckCircle,
  Clock,
  Wrench,
  X,
  ShieldAlert,
  Cpu,
  Layers,
  AlertCircle,
} from 'lucide-react';
import type { FaultItem } from '../types/api';

interface FaultsListProps {
  faults: FaultItem[];
  onAcknowledge: (faultId: number, technician: string) => Promise<void>;
  onRectify: (faultId: number, resolution: string) => Promise<void>;
  onCreateWorkOrder: (faultId: number, assignedTo: string, diagnosis: string) => Promise<void>;
  userRole?: string;
}

export const FaultsList: FC<FaultsListProps> = ({
  faults,
  onAcknowledge,
  onRectify,
  onCreateWorkOrder,
  userRole = 'operator',
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [activeModal, setActiveModal] = useState<{
    type: 'ack' | 'rectify' | 'work_order';
    fault: FaultItem;
  } | null>(null);

  const [inputName, setInputName] = useState('');
  const [inputNote, setInputNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const canAcknowledge = ['shift_incharge', 'electrical_engineer', 'admin'].includes(userRole);
  const canRectify = ['electrical_engineer', 'technician', 'admin'].includes(userRole);
  const canDispatch = ['shift_incharge', 'electrical_engineer', 'admin'].includes(userRole);
  const isReadOnlyRole = userRole === 'operator' || userRole === 'management';

  const filteredFaults = faults.filter((f) => {
    if (filterStatus === 'all') return true;
    return f.status === filterStatus;
  });

  const handleOpenModal = (type: 'ack' | 'rectify' | 'work_order', fault: FaultItem) => {
    setActiveModal({ type, fault });
    setModalError(null);
    setInputName('');
    setInputNote(fault.description || '');
  };

  const handleCloseModal = () => {
    setActiveModal(null);
    setModalError(null);
    setInputName('');
    setInputNote('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeModal) return;
    setIsSubmitting(true);
    setModalError(null);
    try {
      if (activeModal.type === 'ack') {
        await onAcknowledge(activeModal.fault.id, inputName.trim() || 'Duty Engineer');
        setSuccessMessage(`Fault #${activeModal.fault.id} (${activeModal.fault.fault_type}) successfully acknowledged.`);
      } else if (activeModal.type === 'rectify') {
        await onRectify(activeModal.fault.id, inputNote.trim() || 'Fault resolved and restored to nominal bounds');
        setSuccessMessage(`Fault #${activeModal.fault.id} successfully marked as rectified.`);
      } else if (activeModal.type === 'work_order') {
        await onCreateWorkOrder(
          activeModal.fault.id,
          inputName.trim() || 'Alex Kumar',
          inputNote.trim() || activeModal.fault.description || 'Dispatched for physical check'
        );
        setSuccessMessage(`Work order successfully dispatched for Fault #${activeModal.fault.id} to ${inputName.trim() || 'Alex Kumar'}.`);
      }
      handleCloseModal();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      const detail = axiosErr.response?.data?.detail || axiosErr.message || 'Operation failed';
      setModalError(`Action Failed: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      {/* In-place Action Confirmation Banner */}
      {successMessage && (
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            marginBottom: '1.25rem',
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

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <ShieldAlert size={20} style={{ color: '#ef4444' }} />
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
              Fault Lifecycle &amp; Alarm Registry
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Strict isolation of genuine electrical anomalies vs sensor communication errors
            </span>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="pill-group">
          {(['all', 'detected', 'acknowledged', 'rectified'] as const).map((st) => (
            <button
              key={st}
              type="button"
              className={`pill-btn ${filterStatus === st ? 'active' : ''}`}
              onClick={() => setFilterStatus(st)}
              style={{ textTransform: 'capitalize' }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Category</th>
              <th>Phase</th>
              <th>Fault Type & Description</th>
              <th>Measured / Expected</th>
              <th>Status</th>
              <th>Detected At</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredFaults.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                  No faults matching status &quot;{filterStatus}&quot;
                </td>
              </tr>
            ) : (
              filteredFaults.map((f) => {
                const isElectrical = f.category === 'electrical';
                return (
                  <tr key={f.id}>
                    <td>
                      <span className={`severity-pill ${f.severity}`}>
                        {f.severity}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.72rem',
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: isElectrical ? 'rgba(59, 130, 246, 0.1)' : 'rgba(249, 115, 22, 0.1)',
                          color: isElectrical ? '#60a5fa' : '#fb923c',
                          border: `1px solid ${isElectrical ? 'rgba(59, 130, 246, 0.25)' : 'rgba(249, 115, 22, 0.25)'}`,
                        }}
                      >
                        {isElectrical ? <Layers size={11} /> : <Cpu size={11} />}
                        {f.category}
                      </span>
                    </td>
                    <td>
                      {f.phase ? (
                        <span
                          style={{
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            color: f.phase === 'R' ? '#f43f5e' : f.phase === 'Y' ? '#fbbf24' : '#38bdf8',
                          }}
                        >
                          Phase {f.phase}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>3-Phase</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <strong style={{ color: '#fff', fontSize: '0.85rem' }}>{f.fault_type}</strong>
                        {f.description && (
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                            {f.description}
                          </span>
                        )}
                        {f.resolution && (
                          <span style={{ fontSize: '0.72rem', color: '#34d399', marginTop: 2 }}>
                            Resolution: {f.resolution}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="mono-val" style={{ fontSize: '0.82rem' }}>
                        {f.measured_value != null ? `${f.measured_value}${f.unit || ''}` : '--'}
                        {f.expected_value != null && (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                            {' '}
                            (exp: {f.expected_value}{f.unit || ''})
                          </span>
                        )}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          textTransform: 'capitalize',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color:
                            f.status === 'detected'
                              ? '#ef4444'
                              : f.status === 'acknowledged'
                              ? '#f59e0b'
                              : '#10b981',
                        }}
                      >
                        {f.status}
                      </span>
                    </td>
                    <td>
                      <span className="mono-val" style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                        {new Date(f.detected_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                        {isReadOnlyRole ? (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Read-Only Scope
                          </span>
                        ) : (
                          <>
                            {f.status === 'detected' && canAcknowledge && (
                              <button
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}
                                onClick={() => handleOpenModal('ack', f)}
                              >
                                <Clock size={12} />
                                Acknowledge
                              </button>
                            )}
                            {f.status === 'acknowledged' && canRectify && (
                              <button
                                type="button"
                                className="btn btn-success"
                                style={{
                                  padding: '0.3rem 0.6rem',
                                  fontSize: '0.72rem',
                                }}
                                onClick={() => handleOpenModal('rectify', f)}
                                title="Rectify acknowledged fault"
                              >
                                <CheckCircle size={12} />
                                Rectify
                              </button>
                            )}
                            {f.status !== 'rectified' && canDispatch && (
                              <button
                                type="button"
                                className="btn btn-primary"
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}
                                onClick={() => handleOpenModal('work_order', f)}
                                title="Dispatch maintenance technician"
                              >
                                <Wrench size={12} />
                                Dispatch
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Modal Dialog */}
      {activeModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                {activeModal.type === 'ack' && 'Acknowledge Fault Alarm'}
                {activeModal.type === 'rectify' && 'Confirm Fault Rectification'}
                {activeModal.type === 'work_order' && 'Dispatch Maintenance Work Order'}
              </h3>
              <button type="button" className="modal-close-btn" onClick={handleCloseModal}>
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
                role="alert"
              >
                <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0 }} />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div style={{ padding: '0.75rem', borderRadius: 8, background: 'rgba(255, 255, 255, 0.03)', marginBottom: '1rem', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#fff' }}>
                  {activeModal.fault.fault_type}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Phase {activeModal.fault.phase || 'All'} • Severity: {activeModal.fault.severity} • Detected: {new Date(activeModal.fault.detected_at).toLocaleTimeString()}
                </div>
              </div>

              {(activeModal.type === 'ack' || activeModal.type === 'work_order') && (
                <div className="form-group">
                  <label className="form-label">
                    {activeModal.type === 'ack' ? 'Acknowledged By (Technician / Operator Name)' : 'Assign Technician'}
                  </label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. Alex Kumar (Shift In-charge)"
                    value={inputName}
                    onChange={(e) => setInputName(e.target.value)}
                  />
                </div>
              )}

              {(activeModal.type === 'rectify' || activeModal.type === 'work_order') && (
                <div className="form-group">
                  <label className="form-label">
                    {activeModal.type === 'rectify' ? 'Rectification / Resolution Note' : 'Diagnosis & Action Plan'}
                  </label>
                  <textarea
                    rows={3}
                    required
                    className="form-textarea"
                    placeholder={
                      activeModal.type === 'rectify'
                        ? 'Describe how the condition was inspected and brought back to safe operating limits...'
                        : 'Provide preliminary details for the technician...'
                    }
                    value={inputNote}
                    onChange={(e) => setInputNote(e.target.value)}
                  />
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={handleCloseModal}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Processing...' : 'Submit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

import type { FC } from 'react';
import { ScrollText, UserCheck } from 'lucide-react';
import type { AuditLog } from '../types/api';

interface AuditLogViewProps {
  logs: AuditLog[];
}

export const AuditLogView: FC<AuditLogViewProps> = ({ logs }) => {
  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
        <ScrollText size={22} style={{ color: '#0ea5e9' }} />
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
            System Audit Trail &amp; Operational Security Log
          </h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Tamper-evident record of administrative actions, technician attempts, relay actuations, and rule engine telemetry evaluations
          </span>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Actor</th>
              <th>Action Executed</th>
              <th>Target Entity</th>
              <th>Details / Payload</th>
              <th>Timestamp (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No audit log entries recorded.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>
                    <span className="mono-val" style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      #{log.id}
                    </span>
                  </td>
                  <td>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontWeight: 600, fontSize: '0.8rem', color: '#fff' }}>
                      <UserCheck size={13} style={{ color: '#38bdf8' }} />
                      {log.actor}
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: '0.72rem',
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        fontFamily: 'var(--font-mono)',
                        color: '#f8fafc',
                      }}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td>
                    <span style={{ textTransform: 'capitalize', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-primary)' }}>
                      {log.detail || '--'}
                    </span>
                  </td>
                  <td>
                    <span className="mono-val" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

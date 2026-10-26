import { useState } from 'react';
import type { FC } from 'react';
import {
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
  Power,
} from 'lucide-react';
import type { Relay } from '../types/api';

interface RelayControlsProps {
  relays: Relay[];
  onToggleRelay: (relayId: number, targetState: boolean) => Promise<void>;
  isAdmin?: boolean;
  userRole?: string;
}

export const RelayControls: FC<RelayControlsProps> = ({
  relays,
  onToggleRelay,
  isAdmin = false,
  userRole = 'operator',
}) => {
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleToggle = async (relay: Relay) => {
    if (!isAdmin) {
      setErrorMessage(`Unauthorized: Relay switching requires Administrator role. Current role is '${userRole}'.`);
      return;
    }

    setTogglingId(relay.id);
    setErrorMessage(null);
    try {
      await onToggleRelay(relay.id, !relay.is_on);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      const detail = axiosErr?.response?.data?.detail || axiosErr?.message || 'Relay command was rejected by server.';
      setErrorMessage(`Relay Command Failed: ${detail}`);
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Error Banner when authorization or API call fails */}
      {errorMessage && (
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <ShieldAlert size={20} style={{ color: '#ef4444' }} />
            <span style={{ fontSize: '0.84rem', color: '#fca5a5', fontWeight: 600 }}>
              {errorMessage}
            </span>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.72rem', padding: '2px 8px' }}
            onClick={() => setErrorMessage(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Mandatory Safety Notice based on RULES.md Rule 6 */}
      <div
        style={{
          padding: '1rem 1.25rem',
          borderRadius: 'var(--radius-lg)',
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
        }}
      >
        <ShieldAlert size={24} style={{ color: '#ef4444', flexShrink: 0, marginTop: 2 }} />
        <div>
          <strong style={{ color: '#fca5a5', fontSize: '0.88rem', display: 'block', marginBottom: 2 }}>
            Engineering Safety Notice: Solid-State Relay Layer
          </strong>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            SSR-40DA solid-state relays operate as a remote programmatic switching and load shedding control interface.
            Per project architecture standards (<code>docs/RULES.md</code>), SSRs are <strong>never</strong> a substitute for properly rated physical fuses, MCBs, MCCBs, thermal overloads, or mechanical earthing isolation.
          </p>
        </div>
      </div>

      {/* Relays Grid */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ToggleRight size={22} style={{ color: '#0ea5e9' }} />
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                Phase Solid-State Relay (SSR) Actuation
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Command state management with hardware truthfulness verification
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {relays.map((relay) => {
            const isProcessing = togglingId === relay.id;
            const isOn = relay.is_on;

            return (
              <div
                key={relay.id}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md)',
                  background: isOn ? 'rgba(56, 189, 248, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${isOn ? 'rgba(56, 189, 248, 0.3)' : 'var(--border-subtle)'}`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                  transition: 'all 0.25s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 'var(--radius-sm)',
                        background: isOn ? 'rgba(56, 189, 248, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                        color: isOn ? '#38bdf8' : '#64748b',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Power size={18} />
                    </div>
                    <div>
                      <strong style={{ color: '#fff', fontSize: '0.9rem', display: 'block' }}>
                        {relay.name}
                      </strong>
                      <span className="mono-val" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Relay #{relay.relay_number} • GPIO {relay.gpio_pin ?? 'N/A'}
                      </span>
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: '0.70rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '3px 8px',
                      borderRadius: 4,
                      color: isOn ? '#38bdf8' : '#94a3b8',
                      background: isOn ? 'rgba(56, 189, 248, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                      border: `1px solid ${isOn ? 'rgba(56, 189, 248, 0.35)' : 'rgba(100, 116, 139, 0.3)'}`,
                    }}
                  >
                    {isOn ? 'COMMANDED: ON (Pending Telemetry)' : 'COMMANDED: OFF (Open Request)'}
                  </span>
                </div>

                {/* State metrics */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 8,
                    fontSize: '0.74rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 6,
                    background: 'rgba(0, 0, 0, 0.2)',
                  }}
                >
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Command State</span>
                    <strong style={{ color: relay.commanded_state ? '#38bdf8' : '#94a3b8' }}>
                      {relay.commanded_state ? 'HIGH (1 - Signal Sent)' : 'LOW (0 - Signal Cut)'}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Hardware Feedback</span>
                    <strong style={{ color: relay.actual_state ? '#34d399' : '#f59e0b' }}>
                      {relay.actual_state == null ? 'UNVERIFIED (Pending Telemetry)' : relay.actual_state ? 'VERIFIED CLOSED' : 'VERIFIED OPEN'}
                    </strong>
                  </div>
                </div>


                {/* Action button */}
                <button
                  type="button"
                  className={`btn ${isOn ? 'btn-danger' : 'btn-success'}`}
                  style={{
                    width: '100%',
                    justifyContent: 'center',
                    fontSize: '0.82rem',
                    padding: '0.55rem',
                    opacity: !isAdmin ? 0.6 : 1,
                    cursor: !isAdmin ? 'not-allowed' : undefined,
                  }}
                  onClick={() => handleToggle(relay)}
                  disabled={!isAdmin || isProcessing}
                  title={!isAdmin ? `Relay switching requires Administrator role (Current: ${userRole})` : undefined}
                >
                  {isProcessing ? (
                    'Transmitting Signal...'
                  ) : !isAdmin ? (
                    `Restricted to Admin (Role: ${userRole})`
                  ) : isOn ? (
                    <>
                      <ToggleRight size={16} />
                      Command OFF (Open Circuit)
                    </>
                  ) : (
                    <>
                      <ToggleLeft size={16} />
                      Command ON (Close Circuit)
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

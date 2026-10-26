import { useState } from 'react';
import type { FC } from 'react';
import { Play, X, Zap, AlertTriangle, ShieldCheck, Cpu, Flame, BarChart2, AlertCircle, CheckCircle } from 'lucide-react';

interface SimulateModalProps {
  isOpen: boolean;
  onClose: () => void;
  deviceId: number;
  onInject: (scenario: {
    name: string;
    phase: string;
    voltage: number;
    current: number;
    power: number;
    energy: number;
    power_factor: number;
    frequency: number;
    temperature: number;
    data_quality: string;
  }) => Promise<void>;
}

export const SimulateModal: FC<SimulateModalProps> = ({
  isOpen,
  onClose,
  deviceId,
  onInject,
}) => {
  const [injecting, setInjecting] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const scenarios = [
    {
      id: 'nominal',
      name: '1. Nominal Balanced 3-Phase State',
      desc: 'All 3 phases within normal bands (230V, 4.2A, 50.0Hz, PF 0.98, 34°C). Evaluates to Normal status.',
      icon: <ShieldCheck size={20} style={{ color: '#10b981' }} />,
      color: '#10b981',
      payload: {
        name: 'Nominal 3-Phase',
        phase: 'R',
        voltage: 230.2,
        current: 4.2,
        power: 946.0,
        energy: 145.2,
        power_factor: 0.98,
        frequency: 50.02,
        temperature: 34.5,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'overvoltage',
      name: '2. Phase R Overvoltage Condition',
      desc: 'Line voltage surges to 258.5V (exceeds 110% of nominal 230V = 253V). Rule engine detects Overvoltage.',
      icon: <Zap size={20} style={{ color: '#ef4444' }} />,
      color: '#ef4444',
      payload: {
        name: 'Overvoltage Trip',
        phase: 'R',
        voltage: 258.5,
        current: 4.6,
        power: 1160.0,
        energy: 146.0,
        power_factor: 0.97,
        frequency: 50.03,
        temperature: 36.2,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'undervoltage',
      name: '3. Phase B Undervoltage Condition',
      desc: 'Line voltage drops to 184.0V (below 85% of nominal 230V = 195.5V). Rule engine detects Undervoltage.',
      icon: <AlertTriangle size={20} style={{ color: '#f59e0b' }} />,
      color: '#f59e0b',
      payload: {
        name: 'Undervoltage Trip',
        phase: 'B',
        voltage: 184.0,
        current: 3.8,
        power: 680.0,
        energy: 140.5,
        power_factor: 0.96,
        frequency: 49.85,
        temperature: 35.0,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'overcurrent',
      name: '4. Phase Y Overcurrent Overload',
      desc: 'Current spikes to 38.4A (exceeds configured 32A trip threshold). Rule engine triggers Overcurrent Fault.',
      icon: <Zap size={20} style={{ color: '#f43f5e' }} />,
      color: '#f43f5e',
      payload: {
        name: 'Overcurrent Overload',
        phase: 'Y',
        voltage: 228.0,
        current: 38.4,
        power: 8350.0,
        energy: 155.0,
        power_factor: 0.95,
        frequency: 49.95,
        temperature: 42.0,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'imbalance',
      name: '5. Severe 3-Phase Imbalance (> 10%)',
      desc: 'Phase Y loaded to 16.5A while R & B are at 4.2A. Exceeds 10% maximum percentage deviation.',
      icon: <BarChart2 size={20} style={{ color: '#fbbf24' }} />,
      color: '#fbbf24',
      payload: {
        name: 'Phase Imbalance Alert',
        phase: 'Y',
        voltage: 229.0,
        current: 16.5,
        power: 3650.0,
        energy: 154.0,
        power_factor: 0.96,
        frequency: 50.01,
        temperature: 38.5,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'thermal',
      name: '6. High Temperature Thermal Alert',
      desc: 'DS18B20 digital thermal probe logs 68.5°C on enclosure. Triggers High Temperature Alarm.',
      icon: <Flame size={20} style={{ color: '#f97316' }} />,
      color: '#f97316',
      payload: {
        name: 'High Enclosure Temperature',
        phase: 'R',
        voltage: 230.0,
        current: 4.3,
        power: 970.0,
        energy: 145.5,
        power_factor: 0.98,
        frequency: 50.02,
        temperature: 68.5,
        data_quality: 'GOOD',
      },
    },
    {
      id: 'sensor_comm',
      name: '7. Sensor / PZEM Communication Error',
      desc: 'PZEM UART timeout or CRC failure with data_quality="SENSOR_ERROR". Must NOT misclassify as phase loss!',
      icon: <Cpu size={20} style={{ color: '#a855f7' }} />,
      color: '#a855f7',
      payload: {
        name: 'Sensor Comm Error',
        phase: 'B',
        voltage: 0.0,
        current: 0.0,
        power: 0.0,
        energy: 139.8,
        power_factor: 0.0,
        frequency: 0.0,
        temperature: 34.2,
        data_quality: 'SENSOR_COMM_TIMEOUT',
      },
    },
  ];

  const handleSelect = async (sc: typeof scenarios[0]) => {
    setInjecting(sc.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await onInject(sc.payload);
      setSuccessMessage(`Simulation scenario "${sc.name}" successfully processed by backend.`);
      setTimeout(() => {
        onClose();
        setSuccessMessage(null);
      }, 750);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      if (axiosErr.response?.status === 401) {
        setErrorMessage(
          'Telemetry Ingestion Rejected (HTTP 401 Unauthorized): Valid device ingestion key (X-Ingest-Key) or authenticated operator/technician/admin session required.'
        );
      } else if (axiosErr.response?.status === 403) {
        setErrorMessage('Telemetry Ingestion Forbidden (HTTP 403): User lacks permission to inject telemetry.');
      } else if (axiosErr.response?.data?.detail) {
        setErrorMessage(`Simulation Rejected: ${axiosErr.response.data.detail}`);
      } else {
        setErrorMessage('Simulation Failed: Unable to connect to backend telemetry service.');
      }
    } finally {
      setInjecting(null);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: 620 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Play size={20} style={{ color: '#0ea5e9' }} />
            <h3 className="modal-title">Engineering Scenario &amp; Fault Simulator</h3>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Select a test scenario to inject simulated telemetry into Device #{deviceId}. Genuine sensor telemetry is captured exclusively via physical PZEM-004T hardware.
        </p>

        {/* Error Alert */}
        {errorMessage && (
          <div
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              color: '#fca5a5',
              fontSize: '0.82rem',
              lineHeight: 1.4,
            }}
            role="alert"
          >
            <AlertCircle size={18} style={{ flexShrink: 0, color: '#ef4444', marginTop: 1 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Alert */}
        {successMessage && (
          <div
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: '#6ee7b7',
              fontSize: '0.82rem',
            }}
          >
            <CheckCircle size={18} style={{ flexShrink: 0, color: '#10b981' }} />
            <span>{successMessage}</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: 420, overflowY: 'auto' }}>
          {scenarios.map((sc) => (
            <div
              key={sc.id}
              onClick={() => handleSelect(sc)}
              style={{
                padding: '0.85rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = sc.color;
                e.currentTarget.style.background = `${sc.color}10`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
              }}
            >
              <div style={{ flexShrink: 0 }}>{sc.icon}</div>
              <div style={{ flex: 1 }}>
                <strong style={{ color: '#fff', fontSize: '0.86rem', display: 'block', marginBottom: 2 }}>
                  {sc.name}
                </strong>
                <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', margin: 0 }}>
                  {sc.desc}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem', whiteSpace: 'nowrap' }}
              >
                {injecting === sc.id ? 'Injecting...' : 'Inject'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

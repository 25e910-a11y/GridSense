import type { FC } from 'react';
import {
  Zap,
  Gauge,
  Thermometer,
  TrendingUp,
  Activity,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import type { LiveDashboardResponse, PhaseTelemetry } from '../types/api';

interface LiveMetricsProps {
  data: LiveDashboardResponse | null;
  onSelectPhase?: (phase: string) => void;
  isLiveBackend?: boolean;
}

export const LiveMetrics: FC<LiveMetricsProps> = ({ data, isLiveBackend = true }) => {
  if (!data) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        {!isLiveBackend ? (
          <div style={{ maxWidth: 480, margin: '0 auto' }}>
            <AlertTriangle size={36} style={{ color: '#f59e0b', margin: '0 auto 1rem', display: 'block' }} />
            <h3 style={{ color: '#fff', fontSize: '1.15rem', marginBottom: '0.5rem', fontWeight: 700 }}>
              Backend disconnected: no live readings
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.5 }}>
              The FastAPI backend server is currently unreachable. Connect the backend to observe live 3-phase telemetry streams.
            </p>
          </div>
        ) : (
          <div style={{ maxWidth: 480, margin: '0 auto', color: 'var(--text-muted)' }}>
            <Activity size={32} className="animate-spin" style={{ margin: '0 auto 1rem', display: 'block', color: 'var(--accent-blue)' }} />
            <span>Synchronizing 3-phase telemetry stream from device...</span>
          </div>
        )}
      </div>
    );
  }

  const { phases, open_faults } = data;
  const pr = phases?.R;
  const py = phases?.Y;
  const pb = phases?.B;

  // A reading is usable only when its data_quality is one the backend rule engine
  // accepts (backend/app/rules/engine.py USABLE_QUALITY_TOKENS). Anything else is a
  // sensor or communication error, so its numbers are left out instead of being
  // shown as 0 V (which would look like a lost phase).
  const USABLE_QUALITY = ['good', 'ok', 'valid', 'estimated'];
  const isUsable = (p?: PhaseTelemetry): p is PhaseTelemetry =>
    Boolean(p) && (p?.data_quality == null || USABLE_QUALITY.includes(p.data_quality.trim().toLowerCase()));
  const usable = [pr, py, pb].filter(isUsable);
  const sumOf = (values: (number | null | undefined)[]) =>
    values.reduce<number>((total, v) => total + (typeof v === 'number' ? v : 0), 0);

  // Aggregate computations (usable phases only)
  const totalPowerKW = usable.length ? (sumOf(usable.map((p) => p.power)) / 1000).toFixed(2) : '--';
  const usableVoltages = usable.map((p) => p.voltage).filter((v): v is number => typeof v === 'number');
  const avgVoltage = usableVoltages.length
    ? (sumOf(usableVoltages) / usableVoltages.length).toFixed(1)
    : '--';
  const totalCurrent = usable.length ? sumOf(usable.map((p) => p.current)).toFixed(2) : '--';
  // One DS18B20 per enclosure; its value rides along with every phase reading.
  const temps = [pr, py, pb]
    .map((p) => p?.temperature)
    .filter((t): t is number => typeof t === 'number');
  const maxTemp = temps.length ? Math.max(...temps).toFixed(1) : '--';

  // 3-phase imbalance needs all three phases usable
  const currents = usable.length === 3 ? usable.map((p) => p.current || 0).filter((c) => c > 0) : [];
  let currentImbalancePct = '--';
  if (currents.length === 3) {
    const meanI = currents.reduce((a, b) => a + b, 0) / 3;
    if (meanI > 0) {
      const maxDev = Math.max(...currents.map(c => Math.abs(c - meanI)));
      currentImbalancePct = ((maxDev / meanI) * 100).toFixed(1);
    }
  }

  const voltages = usable.length === 3 ? usable.map((p) => p.voltage || 0).filter((v) => v > 0) : [];
  let voltageImbalancePct = '--';
  if (voltages.length === 3) {
    const meanV = voltages.reduce((a, b) => a + b, 0) / 3;
    if (meanV > 0) {
      const maxDev = Math.max(...voltages.map(v => Math.abs(v - meanV)));
      voltageImbalancePct = ((maxDev / meanV) * 100).toFixed(1);
    }
  }

  const renderPhaseCard = (phaseKey: 'R' | 'Y' | 'B', pData?: PhaseTelemetry, colorClass: string = 'phase-r') => {
    const isSensorError = Boolean(pData) && !isUsable(pData);
    const isNoVoltage = isUsable(pData) && typeof pData.voltage === 'number' && pData.voltage <= 15;
    const isOffline = !pData || isNoVoltage;
    const isQualityDegraded = isSensorError;
    // Numbers from a sensor error are not real readings, so show "--".
    const shown = isSensorError ? undefined : pData;

    return (
      <div className={`phase-card ${colorClass}`}>
        <div className="phase-header">
          <div className="phase-pill">
            <span
              style={{
                display: 'inline-block',
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: phaseKey === 'R' ? '#f43f5e' : phaseKey === 'Y' ? '#fbbf24' : '#38bdf8',
                boxShadow: `0 0 10px currentColor`,
              }}
            ></span>
            PHASE {phaseKey}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {pData?.source === 'SIMULATION' && (
              <span
                style={{
                  fontSize: '0.68rem',
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#c084fc',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                }}
              >
                DEMO DATA
              </span>
            )}
            <span
              style={{
                fontSize: '0.72rem',
                padding: '2px 8px',
                borderRadius: 9999,
                background: isOffline
                  ? 'rgba(100, 116, 139, 0.2)'
                  : isQualityDegraded
                  ? 'rgba(245, 158, 11, 0.15)'
                  : 'rgba(16, 185, 129, 0.15)',
                color: isOffline
                  ? '#94a3b8'
                  : isQualityDegraded
                  ? '#fbbf24'
                  : '#34d399',
                border: `1px solid ${
                  isOffline
                    ? 'rgba(100, 116, 139, 0.3)'
                    : isQualityDegraded
                    ? 'rgba(245, 158, 11, 0.35)'
                    : 'rgba(16, 185, 129, 0.3)'
                }`,
                fontFamily: 'var(--font-mono)',
              }}
            >
              {!pData ? 'NO DATA' : isSensorError ? 'SENSOR ERROR' : isNoVoltage ? 'NO VOLTAGE' : 'GOOD'}
            </span>
          </div>
        </div>

        <div className="phase-metrics-list">
          {/* Voltage */}
          <div className="metric-item">
            <span className="metric-label">
              <Zap size={13} style={{ color: '#38bdf8' }} />
              RMS Voltage
            </span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.voltage?.toFixed(1) ?? '--'}</span>
              <span className="metric-unit">V</span>
            </div>
          </div>

          {/* Current */}
          <div className="metric-item">
            <span className="metric-label">
              <Gauge size={13} style={{ color: '#fbbf24' }} />
              Current
            </span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.current?.toFixed(2) ?? '--'}</span>
              <span className="metric-unit">A</span>
            </div>
          </div>

          {/* Active Power */}
          <div className="metric-item">
            <span className="metric-label">
              <TrendingUp size={13} style={{ color: '#10b981' }} />
              Active Power
            </span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.power?.toFixed(1) ?? '--'}</span>
              <span className="metric-unit">W</span>
            </div>
          </div>

          {/* Energy */}
          <div className="metric-item">
            <span className="metric-label">
              <Layers size={13} style={{ color: '#a855f7' }} />
              Cumulative Energy
            </span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.energy?.toFixed(2) ?? '--'}</span>
              <span className="metric-unit">kWh</span>
            </div>
          </div>

          {/* Power Factor */}
          <div className="metric-item">
            <span className="metric-label">Power Factor (cos φ)</span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.power_factor?.toFixed(2) ?? '--'}</span>
              <span className="metric-unit">PF</span>
            </div>
          </div>

          {/* Frequency */}
          <div className="metric-item">
            <span className="metric-label">Frequency</span>
            <div className="metric-value-row">
              <span className="metric-value">{shown?.frequency?.toFixed(2) ?? '--'}</span>
              <span className="metric-unit">Hz</span>
            </div>
          </div>
        </div>

        {/* Phase Footer details */}
        <div
          style={{
            marginTop: '1rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Thermometer size={13} style={{ color: '#f97316' }} />
            Enclosure Temp: <strong style={{ color: '#fff' }}>{pData?.temperature?.toFixed(1) ?? '--'}°C</strong>
          </span>
          <span className="mono-val" style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            {pData?.sampled_at ? new Date(pData.sampled_at).toLocaleTimeString() : 'N/A'}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div>
      {/* Notice if device has no phase readings yet */}
      {!pr && !py && !pb && (
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            color: '#fbbf24',
            fontSize: '0.84rem',
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span>
            <strong>Device Offline / Awaiting Telemetry:</strong> No active 3-phase telemetry records have been logged for this device. Awaiting transmission from hardware sensors.
          </span>
        </div>
      )}

      {/* Simulated Telemetry Banner */}
      {(pr?.source === 'SIMULATION' || py?.source === 'SIMULATION' || pb?.source === 'SIMULATION') && (
        <div
          style={{
            padding: '0.75rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            color: '#c084fc',
            fontSize: '0.84rem',
          }}
        >
          <Activity size={18} style={{ flexShrink: 0 }} />
          <span>
            <strong>DEMO DATA (SIMULATED):</strong> Active telemetry scenario injected for rule engine demonstration. Values are synthetic and do not reflect physical grid sensors.
          </span>
        </div>
      )}

      {/* Stored / Offline Telemetry Notice */}
      {data.system_status === 'Offline' && (pr || py || pb) && (
        <div
          style={{
            padding: '0.75rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            color: '#38bdf8',
            fontSize: '0.84rem',
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0, color: '#f59e0b' }} />
          <span>
            <strong>DEMO DATA / STORED BENCHMARK:</strong> Hardware device is currently offline (no live transmission received in &gt;120s). Displaying stored benchmark telemetry with recorded timestamps. Not live hardware streaming.
          </span>
        </div>
      )}

      {/* Big KPI Summary Strip */}
      <div className="summary-strip">
        <div className="summary-card">
          <div className="summary-icon-box" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
            <Zap size={24} />
          </div>
          <div className="summary-details">
            <span className="summary-label">Total 3-Phase Power</span>
            <span className="summary-val">{totalPowerKW} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>kW</span></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon-box" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
            <Gauge size={24} />
          </div>
          <div className="summary-details">
            <span className="summary-label">Mean Phase Voltage</span>
            <span className="summary-val">{avgVoltage} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>V</span></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon-box" style={{ background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' }}>
            <Activity size={24} />
          </div>
          <div className="summary-details">
            <span className="summary-label">Sum Total Current</span>
            <span className="summary-val">{totalCurrent} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>A</span></span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon-box" style={{ background: 'rgba(249, 115, 22, 0.15)', color: '#f97316' }}>
            <Thermometer size={24} />
          </div>
          <div className="summary-details">
            <span className="summary-label">Enclosure Temperature</span>
            <span className="summary-val">{maxTemp} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>°C</span></span>
          </div>
        </div>
      </div>

      {/* 3-Phase Main Cards Grid */}
      <div className="phase-grid">
        {renderPhaseCard('R', pr, 'phase-r')}
        {renderPhaseCard('Y', py, 'phase-y')}
        {renderPhaseCard('B', pb, 'phase-b')}
      </div>

      {/* 3-Phase Diagnostics & Imbalance Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '1.25rem 1.5rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1.5rem',
          marginBottom: '1.5rem',
          alignItems: 'center',
        }}
      >
        {/* Current Imbalance */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Layers size={15} style={{ color: '#06b6d4' }} />
              3-Phase Current Imbalance
            </span>
            <strong style={{ color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
              {currentImbalancePct}%
            </strong>
          </div>
          <div style={{ height: 6, width: '100%', background: 'rgba(255, 255, 255, 0.08)', borderRadius: 3, overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min((+currentImbalancePct || 0) * 5, 100)}%`,
                background: '#06b6d4',
                transition: 'width 0.4s ease',
              }}
            ></div>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            For reference only. No alarm is set on current imbalance.
          </span>
        </div>

        {/* Voltage Imbalance */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Zap size={15} style={{ color: '#3b82f6' }} />
              3-Phase Voltage Imbalance
            </span>
            <strong style={{ color: +voltageImbalancePct > 10 ? '#ef4444' : '#10b981', fontFamily: 'var(--font-mono)' }}>
              {voltageImbalancePct}%
            </strong>
          </div>
          <div style={{ height: 6, width: '100%', background: 'rgba(255, 255, 255, 0.08)', borderRadius: 3, overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min((+voltageImbalancePct || 0) * 5, 100)}%`,
                background: +voltageImbalancePct > 10 ? '#ef4444' : '#3b82f6',
                transition: 'width 0.4s ease',
              }}
            ></div>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Alarm above 10% from the 3-phase mean (default limit).
          </span>
        </div>

        {/* Status indicator note */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-md)',
            background: open_faults.length > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
            border: `1px solid ${open_faults.length > 0 ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)'}`,
          }}
        >
          {open_faults.length > 0 ? (
            <AlertTriangle size={22} style={{ color: '#ef4444', flexShrink: 0 }} />
          ) : (
            <CheckCircle2 size={22} style={{ color: '#10b981', flexShrink: 0 }} />
          )}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: open_faults.length > 0 ? '#fca5a5' : '#6ee7b7' }}>
              {open_faults.length > 0 ? `${open_faults.length} Active System Fault(s)` : 'Grid Symmetrical & Stable'}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {open_faults.length > 0
                ? 'Review open faults and dispatch work order'
                : data.system_status === 'Offline'
                ? 'Hardware node offline: displaying recorded demo dataset'
                : '3-Phase telemetry received and validated within thresholds'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

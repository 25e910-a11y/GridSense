import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  BarChart3,
  Zap,
  Activity,
  AlertTriangle,
  RefreshCw,
  Building2,
  Clock,
} from 'lucide-react';
import { api } from '../services/api';
import type { ManagementSummary, College, Block, Floor, Device } from '../types/api';

interface ManagementDashboardProps {
  campusHierarchy: { colleges: College[]; blocks: Block[]; floors: Floor[] };
  devices: Device[];
}

export const ManagementDashboard: FC<ManagementDashboardProps> = ({ campusHierarchy, devices }) => {
  const [summary, setSummary] = useState<ManagementSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getManagementSummary();
      if (data) {
        setSummary(data);
      } else {
        setError('Unable to load management summary metrics from backend.');
      }
    } catch {
      setError('Communication failure with management telemetry aggregator.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const data = await api.getManagementSummary();
        if (!ignore) {
          if (data) {
            setSummary(data);
          } else {
            setError('Unable to load management summary metrics from backend.');
          }
        }
      } catch {
        if (!ignore) {
          setError('Communication failure with management telemetry aggregator.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    load();
    const interval = setInterval(fetchSummary, 10000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, []);

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
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <BarChart3 size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                  Campus Energy &amp; Executive Operational KPI Summary
                </h1>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    fontWeight: 600,
                  }}
                >
                  EXECUTIVE VIEW
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
                Aggregated 3-phase power trends, incident volumes, and infrastructure health across campus blocks
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchSummary}
            disabled={isLoading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh KPIs</span>
          </button>
        </div>
      </div>

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

      {/* Primary KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        {/* Total Active Power */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Campus Active Power
            </span>
            <Zap size={18} style={{ color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
            {summary ? summary.total_active_power_kw.toFixed(2) : '--'}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: 4 }}>kW</span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
            Instantaneous 3-phase demand
          </span>
        </div>

        {/* Total Energy */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Cumulative Energy
            </span>
            <Activity size={18} style={{ color: '#34d399' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
            {summary ? summary.total_energy_kwh.toFixed(1) : '--'}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: 4 }}>kWh</span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
            Total metered campus consumption
          </span>
        </div>

        {/* Monitored Substations */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Active Substations
            </span>
            <Building2 size={18} style={{ color: '#a78bfa' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
            {summary ? summary.active_devices : devices.filter((d) => d.is_active).length}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: 6 }}>
              / {summary ? summary.total_devices : devices.length} Units
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
            {campusHierarchy.blocks.length} Blocks Monitored
          </span>
        </div>

        {/* Unresolved Incidents */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Unresolved Incidents
            </span>
            <AlertTriangle size={18} style={{ color: (summary?.open_faults_count || 0) > 0 ? '#ef4444' : '#10b981' }} />
          </div>
          <div
            style={{
              fontSize: '1.8rem',
              fontWeight: 700,
              color: (summary?.open_faults_count || 0) > 0 ? '#f87171' : '#34d399',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {summary ? summary.open_faults_count : '--'}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: 6 }}>Alarms</span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
            {summary?.open_work_orders_count ?? 0} Active Work Orders
          </span>
        </div>
      </div>

      {/* Block-Wise Infrastructure Summary Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
          Campus Block Infrastructure Status
        </h2>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Distribution breakdown by college facilities, feeder panels, and physical monitoring hardware
        </p>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Block Name</th>
                <th>Block Code</th>
                <th>Monitored Floors</th>
                <th>Assigned Hardware</th>
                <th>Operating State</th>
              </tr>
            </thead>
            <tbody>
              {campusHierarchy.blocks.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No campus blocks registered in database.
                  </td>
                </tr>
              ) : (
                campusHierarchy.blocks.map((block) => {
                  const blockFloors = campusHierarchy.floors.filter((f) => f.block_id === block.id);
                  const floorIds = new Set(blockFloors.map((f) => f.id));
                  const blockDevices = devices.filter((d) => d.floor_id != null && floorIds.has(d.floor_id));
                  const hasActive = blockDevices.some((d) => d.is_active);

                  return (
                    <tr key={block.id}>
                      <td>
                        <strong style={{ color: '#fff' }}>{block.name}</strong>
                        {block.description && (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>
                            {block.description}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className="mono-val" style={{ fontSize: '0.78rem' }}>
                          {block.code || `BLK-${block.id}`}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {blockFloors.length} Floors
                        </span>
                      </td>
                      <td>
                        <span className="mono-val" style={{ fontSize: '0.8rem' }}>
                          {blockDevices.length} Device{blockDevices.length === 1 ? '' : 's'}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: 4,
                            textTransform: 'uppercase',
                            background: hasActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                            color: hasActive ? '#34d399' : '#94a3b8',
                            border: `1px solid ${hasActive ? 'rgba(16, 185, 129, 0.35)' : 'rgba(100, 116, 139, 0.3)'}`,
                          }}
                        >
                          {hasActive ? 'ONLINE' : 'STANDBY'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Governance & Compliance Notice */}
      <div
        style={{
          padding: '1rem 1.25rem',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          fontSize: '0.78rem',
          color: 'var(--text-secondary)',
        }}
      >
        <Clock size={18} style={{ color: '#38bdf8', flexShrink: 0 }} />
        <span>
          Management Telemetry is calculated in real time across authorized monitoring points using calibrated PZEM-004T V4 energy transducers. Physical relay actuation and engineering thresholds are restricted to certified operations personnel.
        </span>
      </div>
    </div>
  );
};

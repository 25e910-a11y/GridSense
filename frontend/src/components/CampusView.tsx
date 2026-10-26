import type { FC } from 'react';
import {
  Building,
  Layers,
  MapPin,
  Radio,
} from 'lucide-react';
import type { College, Block, Floor, Device } from '../types/api';

interface CampusViewProps {
  colleges: College[];
  blocks: Block[];
  floors: Floor[];
  devices: Device[];
  selectedDeviceId: number;
  onSelectDevice: (id: number) => void;
}

export const CampusView: FC<CampusViewProps> = ({
  colleges,
  blocks,
  floors,
  devices,
  selectedDeviceId,
  onSelectDevice,
}) => {
  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.5rem' }}>
        <Building size={22} style={{ color: '#0ea5e9' }} />
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
            Campus Physical Distribution &amp; Substation Hierarchy
          </h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Physical mapping: College &rarr; Building Block &rarr; Floor &rarr; Monitoring Node
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {colleges.map((col) => (
          <div
            key={col.id}
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-lg)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1rem' }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Building size={18} />
              </div>
              <div>
                <strong style={{ color: '#fff', fontSize: '1rem' }}>{col.name}</strong>
                {col.code && (
                  <span className="mono-val" style={{ marginLeft: 8, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    [{col.code}]
                  </span>
                )}
              </div>
            </div>

            {/* Blocks in College */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
              {blocks
                .filter((b) => b.college_id === col.id)
                .map((block) => (
                  <div
                    key={block.id}
                    style={{
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem' }}>
                      <Layers size={16} style={{ color: '#fbbf24' }} />
                      <strong style={{ color: '#f8fafc', fontSize: '0.9rem' }}>{block.name}</strong>
                      {block.code && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          ({block.code})
                        </span>
                      )}
                    </div>

                    {/* Floors in Block */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {floors
                        .filter((f) => f.block_id === block.id)
                        .map((floor) => {
                          const floorDevices = devices.filter((d) => d.floor_id === floor.id || !d.floor_id);

                          return (
                            <div
                              key={floor.id}
                              style={{
                                padding: '0.65rem 0.85rem',
                                borderRadius: 6,
                                background: 'rgba(255, 255, 255, 0.03)',
                                border: '1px solid rgba(255, 255, 255, 0.05)',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', color: '#94a3b8', marginBottom: 4 }}>
                                <MapPin size={13} style={{ color: '#a855f7' }} />
                                <span>{floor.name} (Floor {floor.floor_number})</span>
                              </div>

                              {/* Devices installed on this floor */}
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                                {floorDevices.map((dev) => {
                                  const isSelected = selectedDeviceId === dev.id;
                                  return (
                                    <button
                                      key={dev.id}
                                      type="button"
                                      onClick={() => onSelectDevice(dev.id)}
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: 6,
                                        padding: '4px 10px',
                                        borderRadius: 6,
                                        fontSize: '0.74rem',
                                        cursor: 'pointer',
                                        border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.5)' : 'var(--border-subtle)'}`,
                                        background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                                        color: isSelected ? '#38bdf8' : 'var(--text-primary)',
                                      }}
                                    >
                                      <Radio size={12} style={{ color: dev.is_active ? '#10b981' : '#64748b' }} />
                                      <strong>{dev.name}</strong>
                                      <span className="mono-val" style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                                        {dev.device_id}
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

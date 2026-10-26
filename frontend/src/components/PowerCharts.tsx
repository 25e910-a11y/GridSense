import { useState } from 'react';
import type { FC } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Activity, AlertTriangle } from 'lucide-react';
import type { TelemetryHistoryItem } from '../types/api';

interface PowerChartsProps {
  history: TelemetryHistoryItem[];
  isLoading?: boolean;
  error?: string | null;
}

type MetricType = 'voltage' | 'current' | 'power' | 'temperature';

export const PowerCharts: FC<PowerChartsProps> = ({ history, isLoading = false, error = null }) => {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('voltage');

  // Pivot telemetry items by sampled_at timestamp so R, Y, B are combined into one object per timestamp
  const chartDataMap = new Map<string, { time: string; timestamp: number; R?: number; Y?: number; B?: number }>();

  history.forEach((item) => {
    const timeKey = new Date(item.sampled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const ts = new Date(item.sampled_at).getTime();

    if (!chartDataMap.has(timeKey)) {
      chartDataMap.set(timeKey, {
        time: timeKey,
        timestamp: ts,
      });
    }

    const entry = chartDataMap.get(timeKey)!;
    const val = item[selectedMetric];
    if (item.phase === 'R') entry.R = val;
    if (item.phase === 'Y') entry.Y = val;
    if (item.phase === 'B') entry.B = val;
  });

  const chartData = Array.from(chartDataMap.values()).sort((a, b) => a.timestamp - b.timestamp);

  const metricUnits: Record<MetricType, string> = {
    voltage: 'V',
    current: 'A',
    power: 'W',
    temperature: '°C',
  };

  const metricTitles: Record<MetricType, string> = {
    voltage: '3-Phase Line Voltage (V RMS)',
    current: '3-Phase Line Current (A RMS)',
    power: '3-Phase Active Power (Watts)',
    temperature: 'Sensor Temperature (°C)',
  };

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="chart-title-area">
          <TrendingUp size={20} style={{ color: '#0ea5e9' }} />
          <div>
            <h2 className="chart-title">{metricTitles[selectedMetric]}</h2>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              Phase-wise trend synchronization (R: Red, Y: Yellow, B: Blue)
            </span>
          </div>
        </div>

        {/* Metric Selector Pills */}
        <div className="chart-controls">
          <div className="pill-group">
            <button
              type="button"
              className={`pill-btn ${selectedMetric === 'voltage' ? 'active' : ''}`}
              onClick={() => setSelectedMetric('voltage')}
            >
              Voltage (V)
            </button>
            <button
              type="button"
              className={`pill-btn ${selectedMetric === 'current' ? 'active' : ''}`}
              onClick={() => setSelectedMetric('current')}
            >
              Current (A)
            </button>
            <button
              type="button"
              className={`pill-btn ${selectedMetric === 'power' ? 'active' : ''}`}
              onClick={() => setSelectedMetric('power')}
            >
              Power (W)
            </button>
            <button
              type="button"
              className={`pill-btn ${selectedMetric === 'temperature' ? 'active' : ''}`}
              onClick={() => setSelectedMetric('temperature')}
            >
              Temp (°C)
            </button>
          </div>
        </div>
      </div>

      {/* Chart container */}
      <div style={{ width: '100%', height: 320 }}>
        {isLoading ? (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Activity size={20} className="animate-spin" style={{ marginRight: 8, color: '#0ea5e9' }} />
            <span>Loading time-series telemetry...</span>
          </div>
        ) : error ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#f59e0b',
              fontSize: '0.85rem',
              gap: 8,
              padding: '1rem',
              textAlign: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
              <span style={{ fontWeight: 600 }}>Historical Telemetry Unavailable</span>
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', maxWidth: 440 }}>
              {error}
            </span>
          </div>
        ) : chartData.length === 0 ? (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Activity size={20} style={{ marginRight: 8, color: 'var(--text-muted)' }} />
            <span>No time-series telemetry recorded for this device</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
              <XAxis
                dataKey="time"
                stroke="var(--text-muted)"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                stroke="var(--text-muted)"
                fontSize={11}
                tickLine={false}
                domain={['auto', 'auto']}
                unit={` ${metricUnits[selectedMetric]}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 21, 35, 0.95)',
                  borderColor: 'rgba(255, 255, 255, 0.15)',
                  borderRadius: 8,
                  boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(8px)',
                  color: '#fff',
                  fontSize: '0.8rem',
                }}
                formatter={(val: any) => [`${val} ${metricUnits[selectedMetric]}`]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                wrapperStyle={{ fontSize: '0.8rem', paddingBottom: 10 }}
              />
              <Line
                type="monotone"
                dataKey="R"
                name="Phase R"
                stroke="#f43f5e"
                strokeWidth={2.2}
                dot={false}
                activeDot={{ r: 5, fill: '#f43f5e' }}
              />
              <Line
                type="monotone"
                dataKey="Y"
                name="Phase Y"
                stroke="#fbbf24"
                strokeWidth={2.2}
                dot={false}
                activeDot={{ r: 5, fill: '#fbbf24' }}
              />
              <Line
                type="monotone"
                dataKey="B"
                name="Phase B"
                stroke="#38bdf8"
                strokeWidth={2.2}
                dot={false}
                activeDot={{ r: 5, fill: '#38bdf8' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

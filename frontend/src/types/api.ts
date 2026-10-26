export type SystemStatus = 'Normal' | 'Warning' | 'Fault' | 'Sensor/Communication Error' | 'Offline';

export interface PhaseTelemetry {
  voltage: number;
  current: number;
  power: number;
  energy: number;
  power_factor: number;
  frequency: number;
  temperature: number;
  data_quality?: string;
  sampled_at: string;
  sampling_interval_ms?: number;
  transmission_reason?: string;
  source?: string;
}

export interface FaultItem {
  id: number;
  device_id?: number;
  fault_type: string;
  category: 'electrical' | 'sensor_communication' | string;
  severity: 'warning' | 'fault' | 'info';
  phase?: string | null;
  status: 'detected' | 'acknowledged' | 'rectified';
  measured_value?: number | null;
  expected_value?: number | null;
  unit?: string | null;
  description?: string | null;
  detected_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  rectified_at?: string | null;
  resolution?: string | null;
}

export interface LiveDashboardResponse {
  device_id: number;
  device_name: string;
  is_active: boolean;
  system_status: SystemStatus;
  phases: {
    R?: PhaseTelemetry;
    Y?: PhaseTelemetry;
    B?: PhaseTelemetry;
  };
  open_faults: FaultItem[];
}

export interface Device {
  id: number;
  device_id: string; // Hardware ID e.g. "XIAO-PM-001"
  name: string;
  floor_id?: number | null;
  location?: string | null;
  firmware_version?: string | null;
  is_active: boolean;
  last_seen_at?: string | null;
}

export interface College {
  id: number;
  name: string;
  code?: string | null;
}

export interface Block {
  id: number;
  college_id: number;
  name: string;
  code?: string | null;
  description?: string | null;
}

export interface Floor {
  id: number;
  block_id: number;
  floor_number: number;
  name: string;
  description?: string | null;
}

export interface WorkOrder {
  id: number;
  fault_id: number;
  fault_type?: string | null;
  phase?: string | null;
  assigned_to: string;
  status: 'assigned' | 'in_progress' | 'restored' | 'closed';
  diagnosis?: string | null;
  created_at: string;
  started_at?: string | null;
  restored_at?: string | null;
  closed_at?: string | null;
  created_by?: string | null;
  attempts_count?: number;
  attempts?: WorkAttempt[];
  fault?: FaultItem | null;
}

export interface WorkAttempt {
  id: number;
  work_order_id?: number;
  note: string;
  created_by?: string | null;
  created_at: string;
}

export interface Relay {
  id: number;
  device_id: number;
  relay_number: number;
  name: string;
  gpio_pin?: number | null;
  commanded_state: boolean;
  actual_state?: boolean | null;
  is_on: boolean;
  is_active: boolean;
}

export interface NotificationItem {
  id: number;
  fault_id?: number | null;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id?: number | null;
  detail?: string | null;
  created_at: string;
}

export interface TelemetryHistoryItem {
  id: number;
  device_id: number;
  phase: string;
  voltage: number;
  current: number;
  power: number;
  energy: number;
  power_factor: number;
  frequency: number;
  temperature: number;
  data_quality?: string;
  sampled_at: string;
  received_at?: string;
}

export type UserRole =
  | 'operator'
  | 'shift_incharge'
  | 'electrical_engineer'
  | 'management'
  | 'technician'
  | 'admin';

export interface AuthUser {
  username: string;
  role: UserRole;
  assigned_block_id?: number | null;
  assigned_floor_id?: number | null;
  permissions?: string[];
  authenticated?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  username: string;
  assigned_block_id?: number | null;
  assigned_floor_id?: number | null;
  permissions: string[];
}

export interface UserProfileResponse {
  authenticated: boolean;
  username: string;
  role: UserRole;
  assigned_block_id?: number | null;
  assigned_floor_id?: number | null;
  permissions: string[];
}

export interface UserItem {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  assigned_block_id?: number | null;
  assigned_floor_id?: number | null;
  created_at?: string;
}

export interface ManagementSummary {
  system_status: SystemStatus;
  total_devices: number;
  active_devices: number;
  total_energy_kwh: number;
  total_active_power_kw: number;
  open_faults_count: number;
  open_work_orders_count: number;
  blocks_count: number;
  timestamp: string;
}

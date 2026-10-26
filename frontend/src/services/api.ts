import axios from 'axios';
import type {
  Device,
  LiveDashboardResponse,
  FaultItem,
  WorkOrder,
  Relay,
  NotificationItem,
  AuditLog,
  TelemetryHistoryItem,
  College,
  Block,
  Floor,
  LoginResponse,
  UserProfileResponse,
  UserItem,
  ManagementSummary,
} from '../types/api';

const TOKEN_KEY = 'power_monitoring_access_token';

let onUnauthorizedCallback: (() => void) | null = null;

export const setOnUnauthorizedCallback = (callback: (() => void) | null) => {
  onUnauthorizedCallback = callback;
};

const apiClient = axios.create({
  baseURL: '',
  timeout: 4000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header if session token exists
apiClient.interceptors.request.use((config) => {
  try {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Gracefully handle environments where sessionStorage is restricted
  }
  return config;
});

// Intercept 401s to clear session and trigger logout handler (excluding login requests)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error?.config?.url || '';
    const isLoginRequest = url.includes('/auth/login');

    if (error.response && error.response.status === 401 && !isLoginRequest) {
      try {
        sessionStorage.removeItem(TOKEN_KEY);
      } catch {
        // Ignore
      }
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Check backend health
  async checkHealth(): Promise<{ status: string; database?: string; is_live: boolean }> {
    try {
      const res = await apiClient.get('/health');
      const isUnhealthy = res.data?.status === 'unhealthy' || res.data?.status === 'offline';
      const isLive = res.data?.is_live !== undefined ? Boolean(res.data.is_live) : !isUnhealthy;
      return { ...res.data, is_live: isLive };
    } catch {
      return { status: 'offline', is_live: false };
    }
  },

  // Devices
  async getDevices(): Promise<Device[]> {
    try {
      const res = await apiClient.get<Device[]>('/devices/');
      if (Array.isArray(res.data)) {
        return res.data;
      }
      return [];
    } catch {
      return [];
    }
  },

  // Live Dashboard
  async getLiveDashboard(deviceId: number): Promise<LiveDashboardResponse | null> {
    const res = await apiClient.get<LiveDashboardResponse>(`/dashboard/live?device_id=${deviceId}`);
    return res.data;
  },

  // Telemetry History
  async getTelemetryHistory(deviceId: number, phase?: string): Promise<TelemetryHistoryItem[]> {
    const url = phase ? `/telemetry/?device_id=${deviceId}&phase=${phase}` : `/telemetry/?device_id=${deviceId}`;
    const res = await apiClient.get<TelemetryHistoryItem[]>(url);
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  // Send Telemetry (Explicit Test Injection - Real Backend Request)
  async ingestTelemetry(payload: {
    device_id: number;
    phase: string;
    voltage: number;
    current: number;
    power: number;
    energy: number;
    power_factor: number;
    frequency: number;
    temperature: number;
    transmission_reason?: string;
    source?: string;
    data_quality?: string;
    sampled_at?: string;
  }) {
    const res = await apiClient.post('/telemetry/', {
      ...payload,
      sampled_at: payload.sampled_at || new Date().toISOString(),
    });
    return res.data;
  },

  // Faults
  async getFaults(deviceId?: number, status?: string): Promise<FaultItem[]> {
    let url = '/faults/';
    const params = new URLSearchParams();
    if (deviceId) params.append('device_id', String(deviceId));
    if (status) params.append('status', status);
    if (params.toString()) url += `?${params.toString()}`;
    const res = await apiClient.get<FaultItem[]>(url);
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  async acknowledgeFault(faultId: number, acknowledgedBy: string) {
    const res = await apiClient.put(`/faults/${faultId}/acknowledge?acknowledged_by=${encodeURIComponent(acknowledgedBy)}`);
    return res.data;
  },

  async rectifyFault(faultId: number, resolution: string) {
    const res = await apiClient.put(`/faults/${faultId}/rectify?resolution=${encodeURIComponent(resolution)}`);
    return res.data;
  },

  // Work Orders / Maintenance
  async getWorkOrders(faultId?: number): Promise<WorkOrder[]> {
    const url = faultId ? `/maintenance/work-orders?fault_id=${faultId}` : '/maintenance/work-orders';
    const res = await apiClient.get<WorkOrder[]>(url);
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  async createWorkOrder(payload: { fault_id: number; assigned_to: string; diagnosis?: string; created_by?: string }) {
    const res = await apiClient.post('/maintenance/work-orders', payload);
    return res.data;
  },

  async addWorkAttempt(workOrderId: number, note: string, createdBy?: string) {
    const res = await apiClient.post(`/maintenance/work-orders/${workOrderId}/attempts`, {
      note,
      ...(createdBy ? { created_by: createdBy } : {}),
    });
    return res.data;
  },

  async updateWorkOrderStatus(workOrderId: number, status: 'in_progress' | 'restored' | 'closed', diagnosis?: string, actor?: string) {
    const res = await apiClient.put(`/maintenance/work-orders/${workOrderId}/status`, {
      status,
      ...(diagnosis ? { diagnosis } : {}),
      ...(actor ? { actor } : {}),
    });
    return res.data;
  },

  // Relays
  async getRelays(deviceId: number): Promise<Relay[]> {
    const res = await apiClient.get<Relay[]>(`/relays/?device_id=${deviceId}`);
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  async toggleRelay(relayId: number, targetState: boolean): Promise<Relay> {
    const endpoint = targetState ? `/relays/${relayId}/on` : `/relays/${relayId}/off`;
    const res = await apiClient.post(endpoint);
    return res.data;
  },

  // Notifications
  async getNotifications(): Promise<NotificationItem[]> {
    const res = await apiClient.get<NotificationItem[]>('/notifications/');
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  async markNotificationRead(id: number) {
    const res = await apiClient.put(`/notifications/${id}/read`);
    return res.data;
  },

  async markAllNotificationsRead() {
    const res = await apiClient.put('/notifications/read-all');
    return res.data;
  },

  // Audit Logs (strictly admin)
  async getAuditLogs(): Promise<AuditLog[]> {
    const res = await apiClient.get<AuditLog[]>('/audit/?limit=25');
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  // Management Dashboard Summary
  async getManagementSummary(): Promise<ManagementSummary | null> {
    try {
      const res = await apiClient.get<ManagementSummary>('/dashboard/summary');
      return res.data;
    } catch {
      return null;
    }
  },

  // User Administration (Admin Only)
  async getUsers(): Promise<UserItem[]> {
    try {
      const res = await apiClient.get<UserItem[]>('/auth/users');
      if (Array.isArray(res.data)) {
        return res.data;
      }
      return [];
    } catch {
      return [];
    }
  },

  async updateUser(
    userId: number,
    payload: {
      role?: string;
      is_active?: boolean;
      assigned_block_id?: number | null;
      assigned_floor_id?: number | null;
    }
  ): Promise<UserItem> {
    const res = await apiClient.put<UserItem>(`/auth/users/${userId}`, payload);
    return res.data;
  },

  // Campus Hierarchy
  async getCampusHierarchy(): Promise<{ colleges: College[]; blocks: Block[]; floors: Floor[] }> {
    try {
      const [collegesRes, blocksRes, floorsRes] = await Promise.all([
        apiClient.get('/locations/colleges'),
        apiClient.get('/locations/blocks'),
        apiClient.get('/locations/floors'),
      ]);
      return {
        colleges: Array.isArray(collegesRes.data) ? collegesRes.data : [],
        blocks: Array.isArray(blocksRes.data) ? blocksRes.data : [],
        floors: Array.isArray(floorsRes.data) ? floorsRes.data : [],
      };
    } catch {
      return { colleges: [], blocks: [], floors: [] };
    }
  },

  // Authentication & Session Management
  async login(username: string, password: string): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>('/auth/login', { username, password });
    if (res.data && res.data.access_token) {
      try {
        sessionStorage.setItem(TOKEN_KEY, res.data.access_token);
      } catch {
        // Fallback for restricted storage environments
      }
    }
    return res.data;
  },

  async getMe(): Promise<UserProfileResponse> {
    const res = await apiClient.get<UserProfileResponse>('/auth/me');
    return res.data;
  },

  logout(): void {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // Ignore
    }
  },

  getToken(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setToken(token: string | null): void {
    try {
      if (token) {
        sessionStorage.setItem(TOKEN_KEY, token);
      } else {
        sessionStorage.removeItem(TOKEN_KEY);
      }
    } catch {
      // Ignore
    }
  },
};

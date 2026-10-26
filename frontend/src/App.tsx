import { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate, Link } from 'react-router-dom';
import { TrendingUp } from 'lucide-react';
import { Header } from './components/Header';
import { LiveMetrics } from './components/LiveMetrics';
import { PowerCharts } from './components/PowerCharts';
import { FaultsList } from './components/FaultsList';
import { MaintenanceBoard } from './components/MaintenanceBoard';
import { RelayControls } from './components/RelayControls';
import { CampusView } from './components/CampusView';
import { AuditLogView } from './components/AuditLogView';
import { ManagementDashboard } from './components/ManagementDashboard';
import { UserManagementView } from './components/UserManagementView';
import { SimulateModal } from './components/SimulateModal';
import { NotFound } from './components/NotFound';
import { LoginPage } from './components/LoginPage';
import { ProtectedRoute, RoleRoute, PublicOnlyRoute } from './components/ProtectedRoute';
import { useAuth } from './context/useAuth';
import { api } from './services/api';
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
  SystemStatus,
} from './types/api';

export function App() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [selectedDeviceId, setSelectedDeviceId] = useState<number>(1);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
  const [isSimulateOpen, setIsSimulateOpen] = useState<boolean>(false);

  // Lifecycle & race-condition guard refs
  const isMountedRef = useRef<boolean>(true);
  const activeDeviceIdRef = useRef<number>(1);
  const telemetryReqGenRef = useRef<number>(0);
  const auxReqGenRef = useRef<number>(0);

  // Data states
  const [devices, setDevices] = useState<Device[]>([]);
  const [liveData, setLiveData] = useState<LiveDashboardResponse | null>(null);
  const [history, setHistory] = useState<TelemetryHistoryItem[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [faults, setFaults] = useState<FaultItem[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [relays, setRelays] = useState<Relay[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [campusHierarchy, setCampusHierarchy] = useState<{
    colleges: College[];
    blocks: Block[];
    floors: Floor[];
  }>({ colleges: [], blocks: [], floors: [] });

  // Initial load: devices, health, campus (authenticated)
  useEffect(() => {
    isMountedRef.current = true;
    async function init() {
      const health = await api.checkHealth();
      if (!isMountedRef.current) return;
      setIsLiveBackend(health.is_live);

      if (!isAuthenticated) {
        setDevices([]);
        setCampusHierarchy({ colleges: [], blocks: [], floors: [] });
        return;
      }

      const [devs, camp] = await Promise.all([
        api.getDevices(),
        api.getCampusHierarchy(),
      ]);
      if (!isMountedRef.current) return;

      setDevices(devs);
      setCampusHierarchy(camp);
      if (devs.length > 0) {
        activeDeviceIdRef.current = devs[0].id;
        setSelectedDeviceId(devs[0].id);
      }
    }
    init();

    return () => {
      isMountedRef.current = false;
    };
  }, [isAuthenticated]);

  // Reset history and track loading state on device change to avoid stale waveform display
  const handleSelectDevice = useCallback((deviceId: number) => {
    if (deviceId === activeDeviceIdRef.current) return;
    activeDeviceIdRef.current = deviceId;
    telemetryReqGenRef.current++;
    auxReqGenRef.current++;
    setSelectedDeviceId(deviceId);
    setLiveData(null);
    setHistory([]);
    setHistoryError(null);
    setIsHistoryLoading(true);
  }, []);

  // Poll live dashboard & history for current device
  const refreshLiveTelemetry = useCallback(async () => {
    if (!isAuthenticated || !selectedDeviceId) return;
    const reqGen = ++telemetryReqGenRef.current;
    const targetDeviceId = selectedDeviceId;

    try {
      const dashPromise = api.getLiveDashboard(selectedDeviceId).catch(() => null);
      const histPromise = api.getTelemetryHistory(selectedDeviceId).then(
        (data) => ({ ok: true as const, data }),
        (err) => {
          const isOffline = !isLiveBackend || err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error');
          const msg = isOffline
            ? 'FastAPI backend is disconnected or unreachable. Reconnect backend to load historical records.'
            : (err?.response?.data?.detail || err?.message || 'Historical telemetry request failed.');
          return { ok: false as const, error: msg };
        }
      );

      const [dash, histResult] = await Promise.all([dashPromise, histPromise]);

      // Guard against race conditions: drop obsolete responses if device changed, newer request dispatched, or unmounted
      if (!isMountedRef.current || telemetryReqGenRef.current !== reqGen || activeDeviceIdRef.current !== targetDeviceId) {
        return;
      }

      if (dash) {
        setIsLiveBackend(true);
      }
      setLiveData(dash);

      if (histResult.ok) {
        setHistory(histResult.data);
        setHistoryError(null);
      } else {
        setHistory([]);
        setHistoryError(histResult.error);
      }
    } catch (err) {
      if (!isMountedRef.current || telemetryReqGenRef.current !== reqGen || activeDeviceIdRef.current !== targetDeviceId) {
        return;
      }
      console.error('Error refreshing telemetry:', err);
      setHistory([]);
      setHistoryError('Historical telemetry request failed unexpectedly.');
    } finally {
      if (isMountedRef.current && telemetryReqGenRef.current === reqGen && activeDeviceIdRef.current === targetDeviceId) {
        setIsHistoryLoading(false);
      }
    }
  }, [selectedDeviceId, isLiveBackend, isAuthenticated]);

  // Secondary data refresh: faults, work orders, relays, notifications, audit (role-aware)
  const refreshAuxiliaryData = useCallback(async () => {
    if (!selectedDeviceId) return;
    const auxReqGen = ++auxReqGenRef.current;
    const targetDeviceId = selectedDeviceId;

    // Check backend health status dynamically during poll
    api.checkHealth()
      .then((h) => {
        if (isMountedRef.current) setIsLiveBackend(h.is_live);
      })
      .catch(() => {
        if (isMountedRef.current) setIsLiveBackend(false);
      });

    // Do not poll protected endpoints when anonymous (preserves clean kiosk mode)
    if (!isAuthenticated) {
      return;
    }

    const currentRole = user?.role;
    try {
      const canViewWorkOrders = ['technician', 'electrical_engineer', 'shift_incharge', 'admin'].includes(currentRole || '');
      const canViewRelays = ['shift_incharge', 'electrical_engineer', 'admin'].includes(currentRole || '');

      const promises: [
        Promise<FaultItem[]>,
        Promise<Relay[]>,
        Promise<NotificationItem[]>,
        Promise<WorkOrder[]>,
        Promise<AuditLog[]>
      ] = [
        api.getFaults(targetDeviceId).catch(() => []),
        canViewRelays ? api.getRelays(targetDeviceId).catch(() => []) : Promise.resolve([]),
        api.getNotifications().catch(() => []),
        canViewWorkOrders ? api.getWorkOrders().catch(() => []) : Promise.resolve([]),
        currentRole === 'admin' ? api.getAuditLogs().catch(() => []) : Promise.resolve([]),
      ];

      const [fList, rList, nList, wList, aList] = await Promise.all(promises);
      if (!isMountedRef.current || auxReqGenRef.current !== auxReqGen || activeDeviceIdRef.current !== targetDeviceId) {
        return;
      }
      setFaults(fList);
      setRelays(rList);
      setNotifications(nList);
      setWorkOrders(wList);
      setAuditLogs(aList);
    } catch (err) {
      console.error('Error refreshing aux data:', err);
    }
  }, [selectedDeviceId, isAuthenticated, user?.role]);

  // Polling loop: dynamic settlement-based polling for live telemetry (2.5s post-settle), 6s for aux
  useEffect(() => {
    let isCancelled = false;
    let telemetryTimer: ReturnType<typeof setTimeout> | null = null;
    let auxTimer: ReturnType<typeof setInterval> | null = null;

    const pollTelemetry = async () => {
      if (isCancelled || !isMountedRef.current) return;
      try {
        await refreshLiveTelemetry();
      } catch (err) {
        console.error('Unhandled telemetry poll error:', err);
      } finally {
        if (!isCancelled && isMountedRef.current) {
          telemetryTimer = setTimeout(pollTelemetry, 2500);
        }
      }
    };

    const pollAuxiliary = async () => {
      if (isCancelled || !isMountedRef.current) return;
      try {
        await refreshAuxiliaryData();
      } catch (err) {
        console.error('Unhandled aux poll error:', err);
      }
    };

    // Immediate initial poll on mount or device switch
    pollTelemetry();
    pollAuxiliary();

    auxTimer = setInterval(() => {
      pollAuxiliary();
    }, 6000);

    return () => {
      isCancelled = true;
      if (telemetryTimer) clearTimeout(telemetryTimer);
      if (auxTimer) clearInterval(auxTimer);
    };
  }, [refreshLiveTelemetry, refreshAuxiliaryData]);

  // Action handlers
  const handleAcknowledgeFault = async (faultId: number, technician: string) => {
    await api.acknowledgeFault(faultId, technician);
    await refreshAuxiliaryData();
    await refreshLiveTelemetry();
  };

  const handleRectifyFault = async (faultId: number, resolution: string) => {
    await api.rectifyFault(faultId, resolution);
    await refreshAuxiliaryData();
    await refreshLiveTelemetry();
  };

  const handleCreateWorkOrder = async (faultId: number, assignedTo: string, diagnosis: string) => {
    await api.createWorkOrder({
      fault_id: faultId,
      assigned_to: assignedTo,
      diagnosis,
    });
    await refreshAuxiliaryData();
    // Only navigate to /maintenance for authorized technician and admin roles; operators remain on /faults
    if (user?.role === 'technician' || user?.role === 'admin') {
      navigate('/maintenance');
    }
  };

  const handleAddWorkAttempt = async (workOrderId: number, note: string) => {
    await api.addWorkAttempt(workOrderId, note);
    await refreshAuxiliaryData();
  };

  const handleUpdateWorkOrderStatus = async (
    workOrderId: number,
    status: 'in_progress' | 'restored' | 'closed',
    diagnosis?: string
  ) => {
    await api.updateWorkOrderStatus(workOrderId, status, diagnosis);
    await refreshAuxiliaryData();
    await refreshLiveTelemetry();
  };

  const handleToggleRelay = async (relayId: number, targetState: boolean) => {
    await api.toggleRelay(relayId, targetState);
    await refreshAuxiliaryData();
  };

  const handleMarkNotificationRead = async (id: number) => {
    await api.markNotificationRead(id);
    await refreshAuxiliaryData();
  };

  const handleMarkAllNotificationsRead = async () => {
    await api.markAllNotificationsRead();
    await refreshAuxiliaryData();
  };

  const handleInjectScenario = async (sc: {
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
  }) => {
    await api.ingestTelemetry({
      device_id: selectedDeviceId,
      phase: sc.phase,
      voltage: sc.voltage,
      current: sc.current,
      power: sc.power,
      energy: sc.energy,
      power_factor: sc.power_factor,
      frequency: sc.frequency,
      temperature: sc.temperature,
      data_quality: sc.data_quality,
      transmission_reason: 'FAULT_EVENT',
      source: 'SIMULATION',
    });
    await refreshLiveTelemetry();
    await refreshAuxiliaryData();
  };

  const currentSystemStatus: SystemStatus = liveData?.system_status || 'Normal';

  return (
    <div className="app-container">
      {/* Universal Header with Real Routing & Responsive Drawer */}
      <Header
        devices={devices}
        selectedDeviceId={selectedDeviceId}
        onSelectDevice={handleSelectDevice}
        systemStatus={currentSystemStatus}
        notifications={notifications}
        onMarkNotificationRead={handleMarkNotificationRead}
        onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
        onOpenSimulate={() => setIsSimulateOpen(true)}
        isLiveBackend={isLiveBackend}
      />

      {/* Main Content Area Driven by Real Browser Routes */}
      <main className="main-content">
        <Routes>
          {/* Default redirect: based on role or fallback */}
          <Route
            path="/"
            element={
              user?.role === 'management' ? (
                <Navigate to="/management" replace />
              ) : user?.role === 'technician' ? (
                <Navigate to="/maintenance" replace />
              ) : (
                <Navigate to="/live" replace />
              )
            }
          />

          {/* Route: /live -> 3-Phase Live Telemetry Stream (Protected) */}
          <Route
            path="/live"
            element={
              <ProtectedRoute>
                <div>
                  <LiveMetrics data={liveData} isLiveBackend={isLiveBackend} />
                  <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <Link
                      to="/history"
                      className="btn btn-secondary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        textDecoration: 'none',
                        fontSize: '0.8rem',
                        padding: '0.5rem 1rem',
                      }}
                    >
                      <TrendingUp size={15} style={{ color: '#0ea5e9' }} />
                      <span>View Historical Trends &amp; Waveforms</span>
                    </Link>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Route: /history -> Power & Harmonic Waveforms (Protected) */}
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <PowerCharts
                  history={history}
                  isLoading={isHistoryLoading}
                  error={historyError}
                />
              </ProtectedRoute>
            }
          />

          {/* Route: /faults -> Fault Lifecycle Registry (Authenticated Staff) */}
          <Route
            path="/faults"
            element={
              <ProtectedRoute>
                <FaultsList
                  faults={faults}
                  onAcknowledge={handleAcknowledgeFault}
                  onRectify={handleRectifyFault}
                  onCreateWorkOrder={handleCreateWorkOrder}
                  userRole={user?.role}
                />
              </ProtectedRoute>
            }
          />

          {/* Route: /maintenance -> Work Orders & Repair Attempts */}
          <Route
            path="/maintenance"
            element={
              <RoleRoute
                allowedRoles={['technician', 'electrical_engineer', 'shift_incharge', 'admin']}
                pageTitle="Maintenance Work Orders"
              >
                <MaintenanceBoard
                  workOrders={workOrders}
                  onAddAttempt={handleAddWorkAttempt}
                  onUpdateStatus={handleUpdateWorkOrderStatus}
                />
              </RoleRoute>
            }
          />

          {/* Route: /relays -> SSR Relay Contactors (Shift In-Charge, Electrical Engineer, Admin) */}
          <Route
            path="/relays"
            element={
              <RoleRoute
                allowedRoles={['shift_incharge', 'electrical_engineer', 'admin']}
                pageTitle="Phase Relay Contactors"
              >
                <RelayControls
                  relays={relays}
                  onToggleRelay={handleToggleRelay}
                  isAdmin={user?.role === 'admin'}
                  userRole={user?.role}
                />
              </RoleRoute>
            }
          />

          {/* Route: /management -> Executive KPI Summary & Trends */}
          <Route
            path="/management"
            element={
              <RoleRoute
                allowedRoles={['management', 'admin']}
                pageTitle="Executive Management KPI Summary"
              >
                <ManagementDashboard
                  campusHierarchy={campusHierarchy}
                  devices={devices}
                />
              </RoleRoute>
            }
          />

          {/* Route: /campus -> Campus Distribution Hierarchy (Protected) */}
          <Route
            path="/campus"
            element={
              <ProtectedRoute>
                <CampusView
                  colleges={campusHierarchy.colleges}
                  blocks={campusHierarchy.blocks}
                  floors={campusHierarchy.floors}
                  devices={devices}
                  selectedDeviceId={selectedDeviceId}
                  onSelectDevice={handleSelectDevice}
                />
              </ProtectedRoute>
            }
          />

          {/* Route: /users -> User & Role Administration (Administrator Only) */}
          <Route
            path="/users"
            element={
              <RoleRoute allowedRoles={['admin']} pageTitle="User & Role Administration">
                <UserManagementView
                  blocks={campusHierarchy.blocks}
                  floors={campusHierarchy.floors}
                />
              </RoleRoute>
            }
          />

          {/* Route: /audit -> Security & Operations Audit Trail (Administrator Only) */}
          <Route
            path="/audit"
            element={
              <RoleRoute allowedRoles={['admin']} pageTitle="Security & Operations Audit Trail">
                <AuditLogView logs={auditLogs} />
              </RoleRoute>
            }
          />

          {/* Route: /login -> Clean Stage 3 Authentication Gate */}
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />

          {/* Route: 404 Not Found Page */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      {/* Fault & Scenario Simulation Modal */}
      <SimulateModal
        isOpen={isSimulateOpen}
        onClose={() => setIsSimulateOpen(false)}
        deviceId={selectedDeviceId}
        onInject={handleInjectScenario}
      />
    </div>
  );
}

export default App;

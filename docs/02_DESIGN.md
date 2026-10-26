# System Design Document

**Document Reference:** `docs/02_DESIGN.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Design Philosophy

The user interface and system architecture are designed as an **engineering-grade supervisory control and monitoring system**, prioritizing:
1. **Immediate Comprehension:** The instantaneous operating state of the electrical feed is legible within 3 seconds of viewing.
2. **Phase-Wise Parity:** R, Y, and B phases are presented side-by-side with identical scales and metric groupings to allow effortless visual unbalance detection.
3. **Deterministic State Modeling:** Unambiguous status indicators that differentiate sensor telemetry loss from true electrical blackouts.
4. **Structured Incident Management:** Direct links between an electrical fault, automated operator alerts, dispatch work orders, and technician resolution notes.

---

## 2. User Personas & Core Journeys

```
PERSONA: Electrical Operator (Control Room)
Journey:
  1. Observes Live Dashboard banner showing "Warning" or "Fault".
  2. Inspects R/Y/B Phase cards; identifies Phase Y Overcurrent (38.2 A vs 32.0 A threshold).
  3. Navigates to Faults tab; clicks "Acknowledge" to log operational awareness.
  4. Clicks "Dispatch Work Order", assigning task to on-duty Field Technician.

PERSONA: Field Technician (Substation Panel)
Journey:
  1. Opens Maintenance tab on tablet; locates newly assigned Work Order.
  2. Updates status to "In Progress".
  3. Inspects physical switchgear, measures branch currents, and logs chronological attempt note.
  4. Rebalances branch load; verifies current normalization on dashboard.
  5. Transitions Work Order to "Closed" with diagnostic notes; fault auto-rectifies.

PERSONA: System Administrator (Engineering Dept)
Journey:
  1. Configures campus hierarchy (College → Block → Floor → Device).
  2. Provisions device hardware and monitors system-wide audit logs.
  3. Controls authorized relay testing under strict safety interlocks.
```

---

## 3. Web Dashboard Layout & Components

The frontend application (`frontend/src/`) is implemented in React 19 + TypeScript with a dark-mode industrial aesthetic.

### 3.1 Global Header (`Header.tsx`)
- **Device Selector Dropdown:** Allows rapid switching between monitored feeder units (e.g., Unit 01 Main Substation, Unit 02 ECE Lab).
- **Universal Status Badge:** High-visibility indicator displaying the overall system status (`Normal`, `Warning`, `Fault`, `Sensor/Communication Error`, `Offline`).
- **Tab Navigation Bar:**
  - `Live`: Real-time phase metrics and telemetry trend charts.
  - `Faults`: Active and historical fault log with acknowledgment triggers.
  - `Maintenance`: Work order dispatch, status board, and diagnostic attempt logging.
  - `Relays`: Solid-state contactor control board with fail-safe interlocks.
  - `Campus`: Campus $\rightarrow$ Block $\rightarrow$ Floor topology drill-down view.
  - `Audit`: Immutable audit trail viewer for security and operational events.
- **Notification Dropdown Bell:** Real-time badge counter and drop-down drawer displaying unread fault notifications.
- **Simulation Launcher:** Quick-action button opening the fault injection modal.
- **Backend Connectivity Pill:** Indicates live FastAPI connection (`Online`) vs standalone demonstration mode (`Simulated`).

### 3.2 Live Metrics Grid (`LiveMetrics.tsx`)
Presents three synchronized Phase Cards (**Phase R**, **Phase Y**, **Phase B**) exposing:
- RMS Voltage ($V$) with nominal baseline gauge ($230\text{ V}$).
- RMS Current ($A$) with load indicator.
- Active Power ($W$) and Power Factor ($\cos \phi$).
- Cumulative Energy ($kWh$) and Frequency ($Hz$).
- Monitored Busbar / Ambient Temperature ($^\circ\text{C}$).
- Phase Data Quality indicator (`GOOD`, `ESTIMATED`, `COMM_ERROR`).
- Aggregate Summary Banner: Total 3-Phase Power ($W$), Total Energy ($kWh$), and Phase Imbalance Index ($\%$).

### 3.3 Power Trend Waveforms (`PowerCharts.tsx`)
- Rendered via `recharts` responsive SVG components.
- Exposes time-series historical tracking for:
  - Voltage Trends across R, Y, B (nominal $230\text{ V}$ baseline overlay).
  - Current Trends across R, Y, B.
  - Active Power and Busbar Thermal Profile over time.

### 3.4 Fault Log & Action Center (`FaultsList.tsx`)
- Tabbed filtering: `All Faults`, `Active (Detected/Acknowledged)`, `Rectified`.
- Categorization Badges: `Electrical Abnormality` (Red) vs `Sensor / Communication Issue` (Amber).
- Detailed metadata: Phase, Severity, Measured Value, Threshold/Expected Value, Unit, Timestamp.
- Interactive Actions:
  - `Acknowledge Fault` (prompts technician name, updates state).
  - `Dispatch Work Order` (opens assignment modal with prefilled fault data).
  - `Rectify Fault` (allows immediate resolution with closing notes).

### 3.5 Maintenance Board (`MaintenanceBoard.tsx`)
- Kanban/Card style grouping of Work Orders by state:
  `Assigned` $\longrightarrow$ `In Progress` $\longrightarrow$ `Restored` $\longrightarrow$ `Closed`
- Expandable timeline drawer showing chronological technician work attempts.
- "Add Attempt" action capturing detailed diagnostic field notes.
- "Update Status" action enforcing sequential lifecycle progression.

### 3.6 Relay & Actuator Controls (`RelayControls.tsx`)
- Dedicated phase-wise cards for SSR-R (GPIO 7), SSR-Y (GPIO 8), and SSR-B (GPIO 9).
- Shows:
  - `Commanded State`: Requested state by user/system.
  - `Actual State`: Confirmed hardware feedback from device.
  - Physical GPIO pin mapping.
- Safety Confirmation Modal: Requires explicit confirmation before toggling high-current contactors.

### 3.7 Campus Hierarchy Viewer (`CampusView.tsx`)
- Visual tree explorer navigating:
  `College` $\longrightarrow$ `Block` $\longrightarrow$ `Floor` $\longrightarrow$ `Device`
- Displays location-specific metadata, device firmware versions, and last-seen timestamps.

### 3.8 Audit Log Explorer (`AuditLogView.tsx`)
- Searchable, chronological log of all security, maintenance, and administrative actions.
- Tracks: Actor, Action, Entity Type, Entity ID, Timestamp, and Detail payload.

### 3.9 Fault Injection Simulator (`SimulateModal.tsx`)
- Interactive testing modal allowing instant injection of realistic fault scenarios into the running system:
  1. Phase Loss (Phase R voltage drop to $0\text{ V}$ while Y/B remain $230\text{ V}$).
  2. Severe Overcurrent ($42.5\text{ A}$ spike on Phase Y).
  3. Voltage Swell / Overvoltage ($268\text{ V}$ on Phase B).
  4. Undervoltage Sag ($172\text{ V}$ on Phase R).
  5. Severe Phase Imbalance ($18.4\%$ deviation).
  6. High Busbar Temperature ($78.5^\circ\text{C}$).
  7. Sensor Communication Error (`data_quality="comm_error"`).

---

## 4. System Status Hierarchy & Color Palette

Status is computed hierarchically according to strict operational precedence:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Any Active Fault with severity="fault"  ──> [ FAULT ]    │
│ 2. Any Sensor/Comm issue                   ──> [ SENSOR ERR]│
│ 3. Any Active Fault with severity="warning"──> [ WARNING ]  │
│ 4. Device last_seen_at > 120s              ──> [ OFFLINE ]  │
│ 5. All 3 phases present & nominal          ──> [ NORMAL ]   │
└─────────────────────────────────────────────────────────────┘
```

### Color Tokens & Accessibility

| Status State | Color Token | Hex Code | Icon Representation | Accessibility Note |
|---|---|---|---|---|
| **Normal** | Emerald Green | `#10B981` | CheckCircle | Backed by clear text label |
| **Warning** | Amber Yellow | `#F59E0B` | AlertTriangle | Backed by clear text label |
| **Fault** | Crimson Red | `#EF4444` | AlertOctagon | High-contrast white text |
| **Sensor/Comm Error** | Electric Violet | `#8B5CF6` | WifiOff | Distinct icon and color |
| **Offline** | Slate Gray | `#6B7280` | Slash / CircleSlash | Muted styling |

---

## 5. UI Improvements & Hardening Recommendations

1. **Role-Based Tab Visibility:** Hide the `Relays` and `Audit` tabs for users logged in with the `technician` role; restrict relay actuation strictly to `admin`.
2. **WebSocket Push Integration:** Upgrade polling (`setInterval` at 2.5s) to real-time WebSockets or Server-Sent Events (SSE) to eliminate polling latency during rapid fault trips.
3. **Environment-Driven Base URL:** Ensure API client uses `import.meta.env.VITE_API_BASE_URL` rather than hardcoded empty strings to guarantee production multi-host compatibility.

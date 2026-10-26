# Demonstration Guide — IoT-Based Power Monitoring & Fault Identification System

**Audience:** College Academic Faculty, Department Reviewers, and Industry Evaluation Staff  
**System Title:** IoT-Based Power Monitoring and Fault Identification System  
**Document Purpose:** Repeatable, verified startup and execution procedure for software demonstrations.  
**Demonstration Status:** **READY WITH LIMITATIONS (Software & Simulation Verified; Physical Mains Hardware Benchmarked)**

---

## 1. Prerequisites and Environment Configuration

The demonstration runs entirely on the local development workstation without requiring live 415 V / 230 V mains power connections.

### System Prerequisites
- **Operating System:** Windows 10/11 64-bit
- **Python Runtime:** Python 3.13+ with Virtual Environment (`backend/.venv`)
- **Node.js Runtime:** Node.js v20+ with npm
- **Database Engine:** PostgreSQL 16+ (Running as Windows Service `postgresql-x64-18`)
- **Supported Browsers:** Google Chrome, Microsoft Edge, Mozilla Firefox

### Configuration Files
- Backend configuration is located in `backend/.env`.
- Database connection format: `DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/power_monitoring`.
- Default ports:
  - Backend API: `http://127.0.0.1:8000`
  - Frontend UI: `http://localhost:5173`
- *Note:* Never commit `.env` containing production passwords or ingest keys to version control.

---

## 2. Database Verification & Seeding

### Step 2.1: Verify PostgreSQL Service
In PowerShell (Administrator or standard user):
```powershell
Get-Service -Name "*postgres*"
```
*Expected Output:* Status `Running` for `postgresql-x64-18`.

If stopped, start the service:
```powershell
Start-Service postgresql-x64-18
```

### Step 2.2: Verify Database Schema & Role Accounts
To ensure test accounts and benchmark datasets are seeded, run the idempotent seeder from the `backend/` directory:
```powershell
cd d:\IoT-Power-Monitoring-System\backend
.\.venv\Scripts\python.exe ..\database\seed.py
```
*Expected Output:*
```text
Initializing database tables...
Checking existing records...
Database successfully seeded with realistic 3-phase power monitoring data and role accounts!
```
*(This command is fully idempotent: it preserves all existing telemetry, logs, and accounts without dropping tables).*

---

## 3. Application Startup Commands

Open two separate terminal windows for the demonstration.

### Terminal 1: FastAPI Backend
Always execute from the `backend/` directory so that `backend/.env` is loaded automatically:
```powershell
cd d:\IoT-Power-Monitoring-System\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Expected Output:*
```text
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Terminal 2: Vite Frontend Dev Server
In a fresh terminal window:
```powershell
cd d:\IoT-Power-Monitoring-System\frontend
cmd.exe /c "npm run dev"
```
*Expected Output:*
```text
  VITE v8.3.4  ready in 410 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## 4. System URLs & Endpoints

| Resource | URL | Description |
|---|---|---|
| **Control Room Login** | `http://localhost:5173/login` | Only public application page; authentication gate |
| **Live Monitoring Console** | `http://localhost:5173/live` | 3-phase live telemetry stream with provenance labeling |
| **Historical Trends & Waveforms** | `http://localhost:5173/history` | Multi-phase interactive charting for V, I, P, and Temp |
| **Executive Management KPIs** | `http://localhost:5173/management` | Campus-level active power, energy, and incident metrics |
| **Fault Lifecycle Registry** | `http://localhost:5173/faults` | Category-separated alarms with role-governed actions |
| **Work Order Maintenance** | `http://localhost:5173/maintenance` | Dispatch tracker with technician attempt log timeline |
| **Solid-State Relays** | `http://localhost:5173/relays` | SSR contactor state with unverified feedback indicators |
| **Campus Infrastructure** | `http://localhost:5173/campus` | Hierarchical tree: College &rarr; Block &rarr; Floor &rarr; Device |
| **User Administration** | `http://localhost:5173/users` | Admin role/location scope provisioning |
| **Security Audit Trail** | `http://localhost:5173/audit` | Tamper-evident log of administrative mutations |
| **Interactive API Documentation** | `http://127.0.0.1:8000/docs` | Swagger / OpenAPI UI (development only) |
| **System Health Check** | `http://127.0.0.1:8000/health` | Minimal operational status |

---

## 5. Approved Demonstration Accounts

Role-Based Access Control (RBAC) is enforced both client-side and server-side across all endpoints. The login page provides quick one-click profile loaders for testing:

| Role | Username | Password | Operational Capabilities & Boundaries |
|---|---|---|---|
| **Operator** | `operator1` | `demo123` | Read-only live telemetry, phase status, and fault alarms scoped to assigned Block 1. Blocked from fault acknowledgement, work order creation, relay switching, and audit logs. |
| **Shift In-Charge** | `shift_incharge1` | `demo123` | Operational alarm review, fault acknowledgement, and work order dispatch. Blocked from physical relay switching and unrestricted user administration. |
| **Electrical Engineer** | `engineer1` | `demo123` | Detailed 3-phase diagnostics, trend analysis, fault rectification, and technical maintenance investigation. Blocked from relay switching without admin review. |
| **Management** | `mgmt1` | `demo123` | Executive campus/block KPI summaries (`/management`), energy consumption trends, and unresolved incident counts. Read-only; blocked from operational controls. |
| **Technician** | `technician1` | `demo123` | Assigned maintenance work orders (`/maintenance`), repair attempt logging, and status transitions. Strictly isolated to own assigned work orders. |
| **Administrator** | `admin` | `demo123` | Full administrative control: user role and location scope administration (`/users`), SSR contactor actuation (`/relays`), and security audit trail (`/audit`). |

---

## 6. Recommended Five-Minute Demonstration Sequence

Follow this scripted flow to present the software to academic staff and industry reviewers smoothly:

### Minute 1: System Concept, Live Telemetry & Honest Data Labeling
1. **Navigate to:** `http://localhost:5173/live`
2. **Talking Points:**
   - Present the 3-phase, 4-wire power monitoring topology monitored by Seeed Studio XIAO ESP32-S3 and PZEM-004T V4 energy meters.
   - Point out the **KPI Summary Strip**: Total 3-Phase Active Power (kW), Mean Voltage (V RMS), Total Current (A RMS), and Maximum Line Temperature (°C).
   - Point out the individual **Phase Cards (R, Y, B)** showing RMS Voltage, Current, Active Power, Cumulative Energy (kWh), Power Factor ($\cos \phi$), and Frequency (Hz).
   - **Data Integrity Highlight:** Point out the clear notification banner:
     > `DEMO DATA / STORED BENCHMARK: Hardware device is currently offline (no live transmission received in >120s). Displaying stored benchmark telemetry with recorded timestamps.`
   - Emphasize to staff that the software adheres to strict engineering honesty: it never claims live hardware connection when displaying benchmarked or stored datasets, and missing phases are shown as `OFFLINE` rather than falsely forced to zero.
3. **Navigate to Campus Hierarchy:** Click **Campus** (`/campus`).
   - Show the distribution tree: *Government Engineering College &rarr; Main Administrative Block / Electrical Engineering Block &rarr; Ground Floor Substation Panel / 1st Floor Lab &rarr; Power Monitoring Units (`XIAO-PM-001`, `XIAO-PM-002`)*.
   - Click a node to switch the active monitoring device.

### Minute 2: Multi-Phase Historical Waveforms
1. **Navigate to:** `http://localhost:5173/history`
2. **Talking Points:**
   - Demonstrate the synchronized time-series trend lines for Phase R (Red), Phase Y (Yellow), and Phase B (Blue).
   - Use the metric selector buttons to switch views between **Voltage (V)**, **Current (A)**, **Power (W)**, and **Temperature (°C)**.
   - Hover over the chart to show the synchronized multi-phase tooltip with exact timestamps and units.
   - Explain how time-series telemetry enables identifying phase imbalances and harmonic distortions before physical equipment damage occurs.

### Minute 3: Fault Injection, Detection & Rule Engine Verification
1. **Trigger Test Injection:** Click the **Simulate Fault** button in the header.
2. **Select Scenario:** Choose **"2. Phase R Overvoltage Condition"** (258.5 V, exceeding 110% of nominal 230 V).
3. **Click:** "Inject Test Scenario".
   - Explain that because live 415 V mains cannot be safely surged during a presentation, the system features an authenticated test harness that transmits telemetry directly into the backend rule engine.
4. **Observe Live Reaction:**
   - The Live Monitor immediately displays the purple `DEMO DATA (SIMULATED)` banner.
   - Phase R card updates to 258.5 V and the status dot transitions to **Warning** / **Fault**.
5. **Navigate to Faults:** Click **Faults** (`/faults`).
   - If not signed in, the system redirects to `/login`. Sign in with `operator1` / `operator123`.
   - The newly generated fault appears: Type `Overvoltage Alert`, Phase `R`, Measured `258.5 V`, Expected `253.0 V max`.
   - Click **Acknowledge Fault**, enter your name or note, and confirm.
   - Click **Dispatch Work Order**, assign to `technician1`, and submit.

### Minute 4: Maintenance Work Orders & Role-Based Access Control (RBAC)
1. **Demonstrate Client-Side & Server-Side RBAC:**
   - While still logged in as `operator1`, click **Work Orders** (`/maintenance`).
   - The screen renders: **"Access Denied: Role Unauthorized"** (`Technician or Admin required`). Explain that operators can report incidents, but maintenance workflows are role-gated.
2. **Switch to Technician Session:**
   - Click the user badge in the header and click **Sign Out**.
   - Navigate to `/login` and sign in with `technician1` / `tech123`.
   - Navigate to `/maintenance`. The **Maintenance Dispatch & Work Order Tracker** is now fully accessible.
3. **Work Order Management:**
   - Select the dispatched work order from the left rail.
   - Add a work attempt note: *"Inspected Phase R substation surge arrestor. Tap changed to nominal 230V."* and click **Log Repair Attempt**.
   - Advance status to **Restored** or **Closed**. The timeline records the exact timestamp, actor, and resolution note.

### Minute 5: Relay Safety, Contactor Feedback & Security Audit Trail
1. **Switch to Administrator Session:**
   - Sign out and sign in with `admin` / `admin`.
2. **Navigate to Relays:** Click **Relays** (`/relays`).
   - Display the 3 Solid-State Relays: `SSR-R` (GPIO 7), `SSR-Y` (GPIO 8), and `SSR-B` (GPIO 9).
   - **Crucial Safety Talking Point:** Point out the **Engineering Safety Notice**:
     > Solid-state relays are remote switching interfaces and **never** substitutes for physical circuit breakers (MCBs/MCCBs), overload protection, or earthing disconnects.
   - Point out the truthfulness indicator: **Command State** (`HIGH / LOW`) is strictly separated from **Hardware Feedback** (`UNVERIFIED (Pending Telemetry)`).
   - Demonstrate toggling a relay. The API accepts the command and updates the commanded state, while honestly reporting that physical contactor closure is awaiting downstream current sensing.
3. **Navigate to Audit Log:** Click **Audit** (`/audit`).
   - Show the immutable audit trail displaying every action executed during the demo: `create_fault`, `acknowledge_fault`, `create_work_order`, `work_order_attempt`, and `relay_command_on/off` with UTC timestamps and actor usernames.
4. **API Documentation:**
   - Briefly switch tabs to `http://127.0.0.1:8000/docs` to show the full OpenAPI/Swagger documentation, demonstrating that all functionality is accessible to external SCADA or enterprise energy management systems.

---

## 7. Troubleshooting and Recovery Procedures

### Issue 1: Backend Connection Error (`API OFFLINE` in Header)
- **Symptom:** The header shows a yellow `API OFFLINE` indicator and live telemetry says "FastAPI backend is disconnected".
- **Diagnosis:** The uvicorn server process is not running or crashed.
- **Recovery:**
  1. Open a terminal and run `Get-NetTCPConnection -LocalPort 8000` to check if another process is holding port 8000.
  2. Start the backend: `cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
  3. Verify with `curl http://127.0.0.1:8000/health`.

### Issue 2: Database Connection Failure
- **Symptom:** Backend terminal logs show `psycopg2.OperationalError: could not connect to server`.
- **Diagnosis:** PostgreSQL service is stopped.
- **Recovery:**
  1. Run `Get-Service -Name "*postgres*"` in PowerShell.
  2. If status is `Stopped`, start it with `Start-Service postgresql-x64-18`.
  3. Re-run `curl http://127.0.0.1:8000/health` to confirm `{"status": "healthy", "database": "connected"}`.

### Issue 3: Stale Waveforms or No Data Displayed
- **Symptom:** Live metrics shows empty cards or historical chart displays "No time-series telemetry recorded".
- **Diagnosis:** Telemetry table has no records for the selected device.
- **Recovery:**
  1. Switch device selector in the header to **Power Monitoring Unit 01 (Main Incomer) (XIAO-PM-001)**.
  2. Alternatively, run `python database/seed.py` from `backend/` to re-seed initial 3-phase records.

### Issue 4: Session Expired or Redirect to Login
- **Symptom:** Attempting to access `/faults` or `/maintenance` redirects to `/login`.
- **Recovery:**
  1. Sign in using approved test credentials (`operator1`, `technician1`, or `admin`).
  2. Session tokens are stored in browser session storage and clear upon tab closure or logout.

---

## 8. System Scope & Unvalidated Limitations

To ensure full transparency during evaluation, the following items are documented as engineering work in progress and are **not claimed as complete**:

1. **Hardware Modbus UART Communication:** Microcontroller firmware for the Seeed Studio XIAO ESP32-S3 is located in `firmware/` and is verified on logic benches; live RS-485 Modbus RTU continuous communication to three physical PZEM-004T V4 meters is not connected during this software presentation.
2. **Physical High-Voltage Relay Actuation:** Software switching logic is verified end-to-end, but physical actuation of Fotek SSR-40DA relays under live 415 V load is intentionally omitted pending certified branch fusing and mechanical interlock safety review.
3. **Machine Learning / Predictive Maintenance:** No ML model is claimed or active. System fault detection is driven entirely by deterministic electrical engineering threshold algorithms in `backend/app/rules/engine.py`.
4. **MATLAB Real-Time Co-Simulation:** Phase F simulation hooks are defined in architecture documentation, but live co-simulation is not part of this standalone web application demo.

# Feature Implementation Status Matrix

**Document Reference:** `docs/09_FEATURE_STATUS.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Status Legend

- **Implemented & Verified:** Code exists in repository, runtime tests executed, and expected behavior confirmed by evidence.
- **Implemented but Unverified:** Code exists in repository, but has not been verified against a real environment or live hardware.
- **Partially Implemented:** Functional code exists, but key sub-features or safeguards are missing.
- **Broken:** Implementation exists but fails to function as intended due to defects or architectural flaws.
- **Missing:** Required component is planned for the phase but no code exists.
- **Planned:** Future roadmap feature deferred by design.

---

## 2. Complete Feature Inventory

### 2.1 Backend & Rule Engine

| Feature | Status | Evidence / Files | Known Defects | Next Action |
|---|---|---|---|---|
| **Phase-Wise Telemetry Ingestion** | **Partially Implemented** | `backend/app/api/telemetry.py` | Missing `require_ingest` dependency; unauthenticated. | Add `require_ingest` dependency check. |
| **PZEM Sensor vs Electrical Fault Separation** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Keep as regression baseline. |
| **Loss of Voltage Evaluation** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Ensure peer phase check remains intact. |
| **Overvoltage & Undervoltage** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Configurable via `.env`. |
| **Overcurrent Trip Evaluation** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Trips above `OVERCURRENT_AMPS`. |
| **Phase Imbalance Detection** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Computes % deviation from 3-phase mean. |
| **Sudden Delta Jumps** | **Implemented & Verified** | `backend/app/rules/engine.py` | None (verified by pytest). | Tracks consecutive sample differences. |
| **Fault Deduplication** | **Implemented & Verified** | `backend/app/services/faults.py` | Updates open faults; lacks auto-clearing logic. | Add auto-clearing on recovery. |
| **Automatic Fault Resolution** | **Missing** | `backend/app/services/faults.py` | Faults remain open permanently after condition clears. | Implement auto-rectify logic on healthy sample. |
| **Device Offline Detection in Dashboard** | **Broken** | `backend/app/api/dashboard.py` | Only checks `len(phases) < 3`; ignores staleness. | Check `now - last_seen_at > 120s`. |

---

### 2.2 Maintenance & Audit Subsystem

| Feature | Status | Evidence / Files | Known Defects | Next Action |
|---|---|---|---|---|
| **Work Order Creation & Assignment** | **Implemented & Verified** | `backend/app/api/maintenance.py` | Unauthenticated. | Restrict to authorized operator/admin. |
| **Work Order State Machine** | **Implemented & Verified** | `backend/app/api/maintenance.py` | Verified in pytest (`assigned` → `closed`). | Preserve state validation. |
| **Chronological Attempt Logging** | **Implemented & Verified** | `backend/app/api/maintenance.py` | Unauthenticated. | Tie `created_by` to logged-in user. |
| **Auto-Rectification upon Closure** | **Implemented & Verified** | `backend/app/api/maintenance.py` | Tested in `test_api_maintenance.py`. | Preserve automatic closure behavior. |
| **Audit Log System** | **Implemented & Verified** | `backend/app/api/audit.py` | Relay toggles not currently logged. | Add audit event on relay actuation. |

---

### 2.3 Authentication, Authorization & Security

| Feature | Status | Evidence / Files | Known Defects | Next Action |
|---|---|---|---|---|
| **Password Hashing** | **Implemented & Verified** | `backend/app/core/security.py` | None (PBKDF2-HMAC-SHA256, 120k rounds). | Solid cryptographic security. |
| **JWT Access Token Issuance** | **Implemented & Verified** | `backend/app/core/security.py` | Default secret key `"dev-change-me"`. | Force strong random secret in production. |
| **User Self-Registration** | **Broken / Vulnerable** | `backend/app/api/auth.py` | Anyone can register with `role: "admin"`. | Restrict role choice or make admin-only. |
| **Relay Actuation Protection** | **Broken / Vulnerable** | `backend/app/api/relays.py` | `turn_relay_on/off` has no auth checks. | Protect with `Depends(get_current_user)`. |
| **CORS Middleware Configuration** | **Broken / Vulnerable** | `backend/app/main.py` | `allow_origins=["*"]` + `allow_credentials=True`. | Enforce explicit trusted origins. |

---

### 2.4 Frontend Dashboard

| Feature | Status | Evidence / Files | Known Defects | Next Action |
|---|---|---|---|---|
| **Live Phase Cards (R/Y/B)** | **Implemented & Verified** | `frontend/src/components/LiveMetrics.tsx` | None (renders live or fallback data). | Fully functional. |
| **Historical Power Waveforms** | **Implemented & Verified** | `frontend/src/components/PowerCharts.tsx` | None (Recharts SVG rendering). | Fully functional. |
| **Fault Log & Acknowledgment** | **Implemented & Verified** | `frontend/src/components/FaultsList.tsx` | Works against API or mock fallback. | Add loading spinners during mutations. |
| **Maintenance Board (Kanban)** | **Implemented & Verified** | `frontend/src/components/MaintenanceBoard.tsx` | None. | Fully functional. |
| **Relay Controls UI** | **Implemented & Verified** | `frontend/src/components/RelayControls.tsx` | Receives incomplete payload from backend. | Reconcile backend return schema. |
| **Campus Drill-Down Explorer** | **Implemented & Verified** | `frontend/src/components/CampusView.tsx` | None. | Fully functional. |
| **Fault Simulator Modal** | **Implemented & Verified** | `frontend/src/components/SimulateModal.tsx` | None (injects 7 realistic scenarios). | Tested and working. |
| **API Client Base URL** | **Partially Implemented** | `frontend/src/services/api.ts` | Hardcoded `baseURL: ''` relies on Vite proxy. | Use `import.meta.env.VITE_API_BASE_URL`. |

---

### 2.5 Hardware Firmware, Simulation & ML (Upcoming Phases)

| Feature | Status | Evidence / Files | Target Phase |
|---|---|---|---|
| **ESP32-S3 Microcontroller Firmware** | **Missing** | `firmware/` (directory empty) | Phase F Milestone |
| **PZEM-004T Modbus RTU Reader** | **Missing** | `firmware/` | Phase F Milestone |
| **DS18B20 OneWire & DS3231 RTC Driver** | **Missing** | `firmware/` | Phase F Milestone |
| **MATLAB / Simulink Grid Simulation** | **Planned** | `matlab/` (directory empty) | Phase G Milestone |
| **Telemetry Anomaly Dataset Management**| **Planned** | `datasets/` (directory empty) | Phase H Milestone |
| **Machine Learning Predictive Models** | **Planned** | `datasets/` | Phase I Milestone (`ML_ENABLED=false`) |

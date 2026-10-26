# Implementation & Verification Plan

**Document Reference:** `docs/07_IMPLEMENTATION_PLAN.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Plan Structure & Priority Phases

```
[ Phase 1: Critical Security & Authorization Hardening ] (Immediate Blocker)
                           │
                           ▼
[ Phase 2: Core Functional & Telemetry Bug Remediation ]
                           │
                           ▼
[ Phase 3: Database & Migration Baseline Reconstruction ]
                           │
                           ▼
[ Phase 4: Automated Testing & Test Suite Expansion ]
                           │
                           ▼
[ Phase 5: ESP32-S3 Microcontroller Firmware Engineering ]
                           │
                           ▼
[ Phase 6: Frontend Production Hardening & Config ]
                           │
                           ▼
[ Phase 7: Real-Time Streaming (WebSockets / SSE) ]
                           │
                           ▼
[ Phase 8: Deployment, Backup & Operation Readiness ]
                           │
                           ▼
[ Phase 9: MATLAB Simulation & Machine Learning (Future) ]
```

---

## 2. Detailed Task Breakdown

### Phase 1: Critical Security & Authorization Hardening (Priority: Critical)

#### Task 1.1: Lock Down Relay & Contactor Actuation Endpoints
- **Rationale:** Unauthenticated endpoints `POST /relays/{id}/on` and `/off` allow anyone on the network to switch 40 A high-voltage physical contactors.
- **Dependencies:** None.
- **Implementation:**
  - Add `Depends(get_current_user)` to all relay mutating endpoints.
  - Require role `admin` or authorized `operator`.
  - Update both `relay.is_on` and `relay.commanded_state`.
  - Append an immutable entry to `audit_logs` capturing actor username, target relay, and commanded state.
- **Acceptance Criteria:** Unauthenticated requests return `401 Unauthorized`; non-admin/operator users return `403 Forbidden`; audit record is generated.
- **Testing Method:** Automated pytest testing anonymous access, technician access, and admin access.
- **Risks:** Frontend must pass JWT token when toggling relays.

#### Task 1.2: Restrict Self-Registration & Privilege Escalation
- **Rationale:** `/auth/register` allows an anonymous caller to register with `role: "admin"`.
- **Dependencies:** None.
- **Implementation:**
  - Enforce that `/auth/register` only allows registration if called by an authenticated `admin`, OR automatically defaults public self-registration to `operator` / `technician` without accepting privileged overrides.
- **Acceptance Criteria:** A user cannot register with role `admin` unless authorized by an existing admin.
- **Testing Method:** Pytest verifying registration payloads requesting `role: "admin"` result in standard `operator` role or `403 Forbidden`.

#### Task 1.3: Repair & Enforce `require_ingest` for Hardware Telemetry
- **Rationale:** `require_ingest` currently fails when an IoT device sends only `X-Ingest-Key` without a Bearer JWT because `get_current_user` raises an unhandled `401`. Furthermore, `/telemetry/` does not currently invoke `require_ingest`.
- **Dependencies:** None.
- **Implementation:**
  - Refactor `require_ingest` in `security.py` to evaluate `X-Ingest-Key` first. If valid, allow ingestion immediately. If missing, fall back to checking optional user Bearer token.
  - Mount `require_ingest` as a dependency on `POST /telemetry/`.
- **Acceptance Criteria:** Requests with valid `X-Ingest-Key` succeed with `200 OK`; requests without key or valid token return `401 Unauthorized`.
- **Testing Method:** Pytest testing telemetry ingestion with valid key, invalid key, and missing key.

---

### Phase 2: Core Functional & Telemetry Bug Remediation (Priority: High)

#### Task 2.1: Integrate Device Staleness & Offline Status in Dashboard
- **Rationale:** `/dashboard/live` currently returns `Normal` even if a device has been unplugged for days, because it only checks `len(phases) < 3` against historical records.
- **Dependencies:** None.
- **Implementation:**
  - Inspect `device.last_seen_at` in `/dashboard/live`.
  - If `now - last_seen_at > settings.DEVICE_OFFLINE_SECONDS` (120s), set `system_status = "Offline"`.
- **Acceptance Criteria:** Disconnected devices display `Offline` status in both API response and UI banner.
- **Testing Method:** Unit test asserting a device with `last_seen_at = now - 300s` returns `system_status = "Offline"`.

#### Task 2.2: Implement Automatic Fault Recovery & Clear Logic
- **Rationale:** Transient faults (e.g. voltage sag, temporary current spike) remain open in the database permanently once detected, even after electrical values normalize.
- **Dependencies:** None.
- **Implementation:**
  - In `services/faults.py`, after recording active findings, inspect currently open faults for the device/phase.
  - If a previously active fault type is no longer present in the new findings and the electrical sample is healthy, transition fault status to `rectified` with resolution note `"Auto-resolved: electrical parameters returned to nominal band"`.
- **Acceptance Criteria:** Open faults clear automatically when telemetry confirms normal conditions.
- **Testing Method:** Pytest sending an overcurrent sample followed by a normal sample, asserting fault transitions to rectified.

#### Task 2.3: Reconcile Relay State Response Contract
- **Rationale:** `/relays/{id}/on` returns `{ status, message, relay_id, is_on }` while frontend expects the full `Relay` object.
- **Dependencies:** Task 1.1.
- **Implementation:** Return the full updated `Relay` ORM model serialized via Pydantic response schema.
- **Acceptance Criteria:** Frontend receives full `Relay` schema upon actuation without falling back to mock state.

---

### Phase 3: Database & Migration Baseline Reconstruction (Priority: High)

#### Task 3.1: Generate Clean Alembic Baseline Migration
- **Rationale:** Initial migration `53f1a59aca1d` references `floors.id` before `floors` exists, causing clean database migrations to crash.
- **Dependencies:** None.
- **Implementation:**
  - Create a consolidated baseline Alembic revision that creates all 12 tables in topological order: `colleges` $\rightarrow$ `blocks` $\rightarrow$ `floors` $\rightarrow$ `devices` $\rightarrow$ `telemetry` $\rightarrow$ `relays` $\rightarrow$ `faults` $\rightarrow$ `notifications` $\rightarrow$ `work_orders` $\rightarrow$ `work_attempts` $\rightarrow$ `users` $\rightarrow$ `audit_logs`.
- **Acceptance Criteria:** `alembic upgrade head` runs cleanly on an empty PostgreSQL database without errors.
- **Testing Method:** Run `alembic downgrade base` and `alembic upgrade head` in a clean test SQLite/PostgreSQL instance.

---

### Phase 4: Automated Testing & Test Suite Expansion (Priority: Medium)

#### Task 4.1: Expand Pytest Coverage
- **Rationale:** Existing 13 tests cover happy paths for rule engine, but need security boundary checks and regression coverage.
- **Dependencies:** Phases 1–3.
- **Implementation:**
  - Add tests for: unauthorized relay toggling, self-escalation prevention, invalid ingest keys, offline device timeout detection, and auto-clearing faults.
- **Acceptance Criteria:** Full pytest suite passes with >85% service code coverage.
- **Testing Method:** Run `pytest -v --cov=app`.

---

### Phase 5: ESP32-S3 Microcontroller Firmware (Priority: Core Roadmap)

#### Task 5.1: Implement PZEM-004T Modbus RTU Reader
- **Rationale:** `firmware/` directory is currently empty.
- **Dependencies:** Hardware wiring verification.
- **Implementation:**
  - Use ESP-IDF or Arduino-ESP32 with HardwareSerial on GPIO 43 (TX) and GPIO 44 (RX).
  - Query Phase R (`0x01`), Phase Y (`0x02`), and Phase B (`0x03`).
- **Acceptance Criteria:** Microcontroller reads RMS voltage, current, power, energy, PF, frequency from all 3 modules reliably.
- **Testing Method:** Safe bench testing with low-voltage AC transformer signal or calibrated signal generator before mains exposure.

#### Task 5.2: Integrate DS18B20 & DS3231 RTC
- **Implementation:**
  - Read DS18B20 on GPIO 2 (OneWire).
  - Sync system time from DS3231 RTC on GPIO 5/6 (I2C) to attach UTC timestamps to every sample.

#### Task 5.3: Wi-Fi Telemetry Transmitter & Ingestion Client
- **Implementation:**
  - Connect to Wi-Fi with auto-reconnect logic.
  - Transmit HTTP POST payloads to `/telemetry/` with `X-Ingest-Key` header.

---

### Phase 6: Frontend Production Hardening (Priority: Medium)

#### Task 6.1: Configurable API Base URL
- **Rationale:** Hardcoded empty `baseURL: ''` fails in static production deployments.
- **Implementation:** Update `frontend/src/services/api.ts` to use `import.meta.env.VITE_API_BASE_URL || ''`.

---

### Phase 7: Real-Time Communication (Priority: Low / Enhancement)
- Implement FastAPI Server-Sent Events (SSE) or WebSockets at `/ws/telemetry` to push live samples directly to the frontend without 2.5s polling.

---

### Phase 8: Deployment, Backup & Operation Readiness (Priority: Pre-Production)
- Configure Docker Compose with Nginx reverse proxy, PostgreSQL, and Uvicorn.
- Script automated database backups (`pg_dump`) to secure offsite storage.

---

### Phase 9: Simulation & Machine Learning (Future Roadmap)
- Integrate MATLAB / Simulink 3-phase grid simulation bridge.
- Log clean dataset of labeled electrical anomalies before training any predictive ML model.

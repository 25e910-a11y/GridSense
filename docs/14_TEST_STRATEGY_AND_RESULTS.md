# Test Strategy & Execution Results

**Document Reference:** `docs/14_TEST_STRATEGY_AND_RESULTS.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Test Strategy Overview

The testing strategy is designed to ensure electrical accuracy, system reliability, and software security without requiring live mains connection during software verification:
- **Level 1: Rule Engine Unit Tests:** Boundary testing of electrical threshold algorithms with synthetic and edge-case samples.
- **Level 2: API & Integration Tests:** In-memory database integration testing across authentication, telemetry persistence, fault deduplication, maintenance state transitions, and audit records.
- **Level 3: Frontend Compilation & Static Analysis:** TypeScript strict type checking and production Vite bundling.
- **Level 4: Hardware-in-the-Loop Bench Tests:** Bench testing microcontroller firmware with signal generators before any field deployment.

---

## 2. Actual Executed Test Results (Empirical Evidence)

### 2.1 Backend Pytest Execution
- **Command:** `.\.venv\Scripts\pytest -v`
- **Environment:** Windows 11, Python 3.13.15, Pytest 9.1.1, In-Memory SQLite (`sqlite:///:memory:`)
- **Execution Date:** 19 October 2026
- **Results:** **13 PASSED in 1.13 seconds** (0 Failures, 1 Deprecation Warning)

#### Detailed Test Inventory:
```text
tests/test_api_auth.py::test_register_and_login ....................... [  7%] PASSED
tests/test_api_maintenance.py::test_work_order_workflow ............... [ 15%] PASSED
tests/test_api_notifications_and_audit.py::test_notifications_and_audit [ 23%] PASSED
tests/test_api_telemetry_and_faults.py::test_device_telemetry_and_fault [ 30%] PASSED
tests/test_rule_engine.py::test_normal_sample_creates_no_findings ..... [ 38%] PASSED
tests/test_rule_engine.py::test_comm_quality_is_not_phase_loss ........ [ 46%] PASSED
tests/test_rule_engine.py::test_missing_values_are_not_phase_loss ..... [ 53%] PASSED
tests/test_rule_engine.py::test_loss_of_voltage_requires_other_phases . [ 61%] PASSED
tests/test_rule_engine.py::test_near_zero_without_peers_not_loss ...... [ 69%] PASSED
tests/test_rule_engine.py::test_overvoltage_and_undervoltage .......... [ 76%] PASSED
tests/test_rule_engine.py::test_overcurrent_skipped_when_unconfigured . [ 84%] PASSED
tests/test_rule_engine.py::test_invalid_power_factor_is_sensor_issue .. [ 92%] PASSED
tests/test_rule_engine.py::test_phase_imbalance ....................... [100%] PASSED
```

---

### 2.2 Frontend Build & Compilation Execution
- **Command:** `cmd /c npm run build` (executes `tsc -b && vite build`)
- **Environment:** Node.js v20.x, Vite 8.3.4, TypeScript 5.7+
- **Execution Date:** 19 October 2026
- **Results:** **SUCCESS (Built in 8.85 seconds)**
- **Output Artifacts:**
  - `dist/index.html` (0.92 kB)
  - `dist/assets/index-lqMgQhTb.css` (12.34 kB)
  - `dist/assets/index-CMBcnI1S.js` (708.17 kB)
- **Verdict:** **PASSED.** Strict TypeScript compilation passed without any type errors across all 9 React components.

---

### 2.3 Database Migration Execution
- **Command:** `.\.venv\Scripts\alembic upgrade head`
- **Environment:** Clean SQLite/PostgreSQL Database
- **Results:** **FAILED**
- **Error Observed:**
  `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: floors [SQL: CREATE TABLE devices ... FOREIGN KEY(floor_id) REFERENCES floors (id)]`
- **Status:** **IDENTIFIED DEFECT.** Documented in Defect Log (`docs/15_DEBUGGING_AND_ROOT_CAUSE.md`).

---

## 3. Unverified Tests (What Could Not Be Executed)

To adhere strictly to truth-in-engineering standards, the following tests were **NOT executed** and remain unverified:

1. **Hardware Modbus UART Communication:** Physical ESP32-S3 communicating with 3 live PZEM-004T V4 modules over GPIO 43/44 has not been run because microcontroller code in `firmware/` has not yet been authored.
2. **Physical Relay Switching under Load:** Actuation of Fotek SSR-40DA relays under 230 V AC mains load has not been executed and **must not be run** until full electrical safety review, branch fusing, and protective interlocks are complete.
3. **High-Concurrency Telemetry Load:** Stress testing the FastAPI backend with 100+ concurrent simulated IoT devices has not been run.
4. **PostgreSQL Multi-Day Data Retention Partitioning:** Production table partitioning for millions of historical telemetry rows has not been benchmarked.

---

## 4. Test Suite Expansion Plan (Required New Tests)

The following tests will be added during Phase 4 of the implementation plan:
1. `test_security_relay_unauthenticated_forbidden`: Asserts `POST /relays/1/on` fails with 401/403 for anonymous and technician callers.
2. `test_security_self_escalation_rejected`: Asserts `/auth/register` with `role: "admin"` is rejected or downgraded.
3. `test_dashboard_stale_device_offline`: Asserts a device without telemetry for >120s returns status `"Offline"`.
4. `test_fault_auto_clearing_on_recovery`: Asserts an open fault is marked `rectified` when subsequent telemetry samples return to normal.
5. `test_require_ingest_hardware_header`: Asserts IoT ingestion succeeds with valid `X-Ingest-Key` alone.

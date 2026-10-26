# Product Requirements Document (PRD)

**Document Reference:** `docs/01_PRD.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)
**Target Domain:** Institutional 3-Phase 4-Wire Electrical Distribution Networks

---

## 1. Problem Statement

Electrical distribution networks in educational and institutional campuses (laboratories, lecture halls, administrative blocks, and substations) frequently experience power quality anomalies and electrical faults, including:
- Phase voltage unbalance from uneven single-phase load distribution.
- Overcurrent and feeder overloading from concurrent equipment startup.
- Voltage sags, swells, and transient overvoltage conditions.
- Equipment overheating and loose terminal connection thermal runaway.
- Accidental phase interruption (loss of phase voltage).

Traditional power monitoring relies on periodic manual inspections or basic analog panel meters that lack:
1. Continuous, synchronized multi-phase digital telemetry.
2. Intelligent discrimination between genuine electrical abnormalities and sensor/communication dropouts.
3. Automated fault logging with sub-second timestamps and exact threshold comparisons.
4. Structured dispatch and maintenance tracking linking identified faults to technician remediation.

---

## 2. Target Users & Stakeholders

| User Role | Responsibilities | Key Capabilities Required |
|---|---|---|
| **System Administrator** | System configuration, user provisioning, campus topology setup, device registration, and security auditing. | Full system access, threshold configuration, user management, audit log inspection, device commissioning. |
| **Operations Engineer / Moderator** | Continuous grid observation, live anomaly review, alarm acknowledgment, and maintenance dispatching. | Real-time 3-phase dashboard, live alerts, fault acknowledgment, work order creation. |
| **Maintenance Technician** | Physical inspection, fault diagnosis, component replacement, work order execution, and service restoration. | Mobile-accessible work order list, chronological attempt logging, fault rectification sign-off. |
| **Department Head / Management** | High-level facility overview, energy consumption tracking, power quality auditing, and reliability reporting. | Executive campus overview, historical trend graphs, incident frequency metrics. |

---

## 3. Product Vision & Core Workflow

The operational paradigm of the system is strictly ordered as:

```
[MONITOR]  --> Continuous 3-phase electrical sampling via PZEM-004T V4 & DS18B20
     │
     ▼
[ANALYSE]  --> Multi-phase validation, sanity checking, and baseline comparison
     │
     ▼
[IDENTIFY] --> Deterministic rule engine classifies anomaly vs sensor/comm fault
     │
     ▼
  [LOG]    --> UTC-timestamped telemetry, fault records, and deduplication
     │
     ▼
 [ALERT]   --> Real-time in-app notification dispatch with measured vs expected values
     │
     ▼
[MAINTAIN] --> Work order lifecycle (assigned → in_progress → restored → closed)
```

---

## 4. Hardware Scope & Constraints

### 4.1 Microcontroller & Peripherals
- **Main Processing Unit:** Seeed Studio XIAO ESP32-S3 (Dual-core Xtensa LX7, 240 MHz, Wi-Fi 2.4 GHz, BLE 5.0).
- **Power Monitoring Modules:** Three (3) Peacefair PZEM-004T V4 modules operating over Modbus RTU / UART (one dedicated per phase: R, Y, B).
- **Current Transformers:** 3 × split-core CTs (up to 100 A RMS rating).
- **Temperature Sensing:** 1 × Maxim Integrated DS18B20 digital thermal sensor (OneWire interface).
- **Real-Time Clock:** 1 × DS3231 high-precision I2C RTC with coin-cell backup for local sample timestamping.
- **Switching Actuators:** 3 × Fotek SSR-40DA solid-state relays (3–32 V DC input, 24–380 V AC output, 40 A max rating).
- **Power Supply:** Hi-Link 5 V / 5 W AC-DC step-down isolated converter with LiPo battery backup.

### 4.2 Strict Hardware Safety Invariants
- **Non-reintroduction of MQ-135:** Smoke/air quality sensing has been explicitly removed from scope.
- **SSRs Are Not Circuit Protection:** SSR-40DA units are control actuators, **never** replacements for circuit breakers (MCBs), molded-case circuit breakers (MCCBs), thermal overloads, proper branch fusing, or galvanic isolators.
- **Galvanic Isolation:** Mains-side AC line voltages must remain isolated from the 3.3 V / 5 V low-voltage microcontroller logic lines at all times.

---

## 5. Functional Requirements

### 5.1 Telemetry Ingestion & Validation
- **FR-01:** System shall ingest phase-wise electrical telemetry: RMS Voltage ($V$), RMS Current ($A$), Active Power ($W$), Cumulative Energy ($kWh$), Power Factor ($-$), and Grid Frequency ($Hz$).
- **FR-02:** System shall ingest ambient/busbar temperature ($^\circ C$) from DS18B20.
- **FR-03:** Incoming payloads must identify sending device, phase (`R`, `Y`, `B`), transmission reason, data source (`REAL`, `SIMULATION`, `TEST`), and measurement timestamp (`sampled_at`).
- **FR-04:** Backend shall validate numerical boundaries (non-negative power, power factor between 0.0 and 1.0, finite float values).

### 5.2 Deterministic Rule Engine
- **FR-05:** **Sensor/Communication Distinction:** If `data_quality` is flagged with error tokens or values are non-physical, the system must trigger a `SENSOR_COMMUNICATION` alert and **must not** classify it as an electrical fault.
- **FR-06:** **Loss of Voltage:** Voltage below $15.0\text{ V}$ is classified as `LOSS_OF_VOLTAGE` **only** if one or more companion phases show healthy voltage ($>15.0\text{ V}$). If all phases drop simultaneously without telemetry flags, it is treated as a supply dropout or sensor outage, not phase loss.
- **FR-07:** **Undervoltage & Overvoltage:** Detect voltage deviations outside configurable thresholds (Nominal $230\text{ V}$; Undervoltage $<195.5\text{ V}$ [0.85 ratio]; Overvoltage $>253.0\text{ V}$ [1.10 ratio]).
- **FR-08:** **Overcurrent:** Flag current exceeding configured threshold (default $32.0\text{ A}$).
- **FR-09:** **Phase Imbalance:** Compute percentage deviation from 3-phase voltage mean. Flag `PHASE_IMBALANCE` if max deviation exceeds $10.0\%$.
- **FR-10:** **Sudden Delta Jumps:** Compare current sample against immediate prior sample on the same phase. Flag abrupt spikes in voltage, current, power, PF, or frequency.
- **FR-11:** **High Temperature:** Flag thermal readings exceeding the thermal limit ($>60^\circ\text{C}$).

### 5.3 Fault Deduplication & Lifecycle
- **FR-12:** Multiple consecutive abnormal samples of the same fault type on the same phase and device must update the existing open fault (`detected` or `acknowledged`), rather than inserting duplicate database rows.
- **FR-13:** System shall transition faults through: `detected` $\rightarrow$ `acknowledged` $\rightarrow$ `rectified`.
- **FR-14:** Every new fault detection must automatically generate an unread system notification.

### 5.4 Maintenance Work Orders
- **FR-15:** Operators can create a Work Order assigned to a technician linked to an active fault.
- **FR-16:** Work Order state machine: `assigned` $\rightarrow$ `in_progress` $\rightarrow$ `restored` $\rightarrow$ `closed`.
- **FR-17:** Technicians can record chronological attempt logs with diagnostic notes.
- **FR-18:** Transitioning a work order to `closed` must automatically rectify the associated fault and record closure diagnosis.

### 5.5 Campus Topology
- **FR-19:** 4-tier hierarchical representation: College $\rightarrow$ Block $\rightarrow$ Floor $\rightarrow$ Monitoring Device.

### 5.6 Web Dashboard & Operator UI
- **FR-20:** Display real-time 3-phase metric cards (Voltage, Current, Power, Energy, PF, Frequency, Temp).
- **FR-21:** Compute and display high-level system status: `Normal`, `Warning`, `Fault`, `Sensor/Communication Error`, `Offline`.
- **FR-22:** Render phase-wise historical trend charts over time.
- **FR-23:** Provide interactive fault simulation modal for controlled scenario injection.

---

## 6. Non-Functional Requirements

- **NFR-01 (Safety & Actuation):** Relay actuation APIs must be restricted to authenticated administrative roles and require device round-trip physical acknowledgement before confirming state.
- **NFR-02 (Latency):** Backend telemetry ingestion and rule evaluation shall execute in under $50\text{ ms}$ on standard server hardware.
- **NFR-03 (Data Integrity):** Telemetry persistence must record separate device sample time (`sampled_at`) and server receipt time (`received_at`).
- **NFR-04 (Auditability):** All administrative, maintenance, user registration, and relay operations must append immutable audit log records.
- **NFR-05 (Accessibility):** Status colors must be backed by distinct textual labels and iconography.

---

## 7. Current V1 Implemented Features vs. Future Roadmap

| Capability | Current V1 Status | Notes / Next Phase |
|---|---|---|
| 3-Phase Telemetry Ingestion API | **Implemented** | Needs authentication hardening (`X-Ingest-Key`). |
| Deterministic Rule Engine | **Implemented & Verified** | 13 automated tests passing. |
| Fault Deduplication & Notification | **Implemented** | Working; auto-clear on recovery to be added. |
| Maintenance Work Order Workflow | **Implemented & Verified** | Full state machine & attempt logging. |
| Campus Location Hierarchy | **Implemented** | College/Block/Floor data models. |
| React 19 Web Dashboard | **Implemented & Verified** | Live metrics, charts, fault boards, demo fallback. |
| ESP32-S3 Microcontroller Firmware | **Missing** | Phase F milestone (Modbus UART, DS18B20, RTC). |
| MATLAB / Simulink Grid Integration | **Planned / Future** | Phase G milestone. |
| Machine Learning Predictive Models | **Planned / Future** | Phase I milestone (disabled until verified). |

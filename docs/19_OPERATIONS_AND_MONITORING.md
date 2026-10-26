# Operations & Monitoring Guide

**Document Reference:** `docs/19_OPERATIONS_AND_MONITORING.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Monitoring Scope: Operational Health vs. Electrical Faults

A clear architectural boundary must be maintained between two distinct monitoring domains:

```
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│  OPERATIONAL INFRASTRUCTURE HEALTH   │  │    ELECTRICAL GRID MONITORING        │
├──────────────────────────────────────┤  ├──────────────────────────────────────┤
│ • Backend API process uptime         │  │ • 3-Phase Voltage / Current RMS      │
│ • Database connection pool usage     │  │ • Phase Imbalance (>10%)             │
│ • IoT device heartbeat staleness     │  │ • Overcurrent / Under/Overvoltage    │
│ • Ingestion latency and dropped pkts │  │ • Busbar thermal runaway (>60°C)     │
│ • Disk storage consumption rate      │  │ • Loss of Voltage on Phase R/Y/B     │
│ • Audit log write integrity          │  │ • Frequency deviation (50 ± 1.5 Hz)  │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
```

---

## 2. Infrastructure Health Probes & Metrics

### 2.1 Backend Health Endpoint (`GET /health`)
- **Probe Interval:** Every 30 seconds by load balancer / monitoring agent.
- **Verification:** Executes `SELECT 1` on the active database connection pool.
- **Healthy Response:** HTTP 200 `{"status": "healthy", "database": "connected"}`.
- **Degraded/Unhealthy:** HTTP 500 or 503 `{"status": "unhealthy", "database": "disconnected"}`.

### 2.2 Device Heartbeat & Freshness Tracking
- **Metric:** `now - device.last_seen_at`.
- **Threshold:** Configured via `DEVICE_OFFLINE_SECONDS` (default $120\text{ seconds}$).
- **Behavior:**
  - If gap $< 120\text{ s}$: Device is marked `Online`.
  - If gap $\ge 120\text{ s}$: Device is marked `Offline`.
  - A notification is generated flagging loss of telemetry, distinct from an electrical outage.

### 2.3 Database Growth & Capacity Management
- **Sampling Volume Calculation:**
  - 1 Device $\times$ 3 Phases $\times$ 1 Sample/second = 3 rows/second.
  - Per Day: $3 \times 86,400 = 259,200\text{ rows/day}$.
  - Estimated Storage: $\approx 50\text{ MB/day}$ per 3-phase device.
- **Retention Strategy:**
  - Raw high-frequency telemetry retained for **30 days**.
  - Hourly aggregated summaries (min, max, mean, cumulative energy) retained indefinitely.

---

## 3. Operational Logging & Alert Escalation Matrix

### 3.1 Logging Standards
- All application events must log in structured JSON format with:
  `timestamp` (ISO-8601 UTC), `level` (`INFO`, `WARNING`, `ERROR`, `CRITICAL`), `module`, `event_type`, and `request_id`.
- **Strict Redaction:** Passwords, JWT secrets, Bearer authorization headers, and device ingest keys must be masked or excluded from logs.

### 3.2 Escalation Matrix

| Incident Type | Category | Severity | Initial Action | Escalation (15 min) |
|---|---|:---:|---|---|
| **PZEM Modbus Timeout** | Operational | Warning | Log sensor warning; flag Phase card as `COMM_ERROR`. | Notify electrical lab staff to check RS485 wiring. |
| **Device Offline (>2 min)** | Operational | Warning | Flag device as `Offline` on dashboard. | Ping facility technician to inspect Wi-Fi router. |
| **Severe Overcurrent (>32A)** | Electrical | **CRITICAL** | Trigger high-priority in-app alarm; deduplicate fault. | Auto-dispatch emergency maintenance work order. |
| **Loss of Phase Voltage** | Electrical | **CRITICAL** | Verify companion phases; flag `LOSS_OF_VOLTAGE`. | Dispatch maintenance team; alert building manager. |
| **Database Disconnect** | Operational | **CRITICAL** | Automated systemd service restart; alert sysadmin. | Failover to standby database cluster. |

---

## 4. Backup & Disaster Recovery Schedule

- **Frequency:** Daily automated backup at 02:00 AM UTC via `pg_dump`.
- **Retention:** Keep daily backups for 14 days; weekly backups for 8 weeks; monthly backups for 1 year.
- **Verification Drill:** Monthly automated restore into an isolated staging container asserting table row counts match production snapshots.

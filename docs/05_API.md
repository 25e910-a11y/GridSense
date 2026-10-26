# API Documentation & Contract

**Document Reference:** `docs/05_API.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. API Architecture & Standards

- **Protocol:** HTTP/1.1 REST (JSON request and response bodies).
- **Default Base URL:** `http://127.0.0.1:8000` (FastAPI).
- **Interactive Documentation:**
  - Swagger UI: `http://127.0.0.1:8000/docs`
  - ReDoc: `http://127.0.0.1:8000/redoc`
- **Authentication Schemes:**
  1. `Bearer <jwt_token>` via `Authorization` header for human users (`admin`, `operator`, `technician`).
  2. `X-Ingest-Key: <secret>` header for hardware edge devices (ESP32-S3).

---

## 2. API Endpoint Inventory

### 2.1 Authentication (`/auth`)

| Method | Path | Auth Required | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/auth/register` | **None (Vulnerability V-02)** | `{ username, password, role }` | Register new user. *(Requires admin lockdown)* |
| `POST` | `/auth/login` | None | `{ username, password }` | Authenticate user; returns JWT access token. |
| `GET` | `/auth/me` | `Bearer <token>` | None | Returns authenticated user details and role. |

#### Request Example (`POST /auth/login`):
```json
{
  "username": "admin",
  "password": "adminpassword"
}
```

#### Response Example (`POST /auth/login`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin",
  "username": "admin"
}
```

---

### 2.2 Telemetry Ingestion & History (`/telemetry`)

| Method | Path | Auth Required | Parameters / Body | Description |
|---|---|---|---|---|
| `POST` | `/telemetry/` | **None (Vulnerability V-03)** | `TelemetryCreate` JSON | Ingest phase reading, evaluate rules, update faults. |
| `GET` | `/telemetry/` | None | `device_id` (opt), `phase` (opt) | Query bounded recent telemetry (limit 100). |
| `GET` | `/telemetry/latest` | None | `device_id` (req) | Fetch absolute latest reading for device. |
| `GET` | `/telemetry/latest-by-phase` | None | `device_id` (req) | Return map of latest readings for R, Y, and B. |

#### Request Example (`POST /telemetry/`):
```json
{
  "device_id": 1,
  "phase": "R",
  "voltage": 230.4,
  "current": 4.35,
  "power": 982.0,
  "energy": 142.68,
  "power_factor": 0.98,
  "frequency": 50.02,
  "temperature": 34.6,
  "sampled_at": "2026-10-19T10:30:00Z",
  "sampling_interval_ms": 1000,
  "transmission_reason": "SCHEDULED",
  "source": "REAL",
  "data_quality": "good"
}
```

#### Response Example (`POST /telemetry/`):
```json
{
  "status": "success",
  "message": "Telemetry stored",
  "telemetry_id": 412,
  "device_id": 1,
  "phase": "R",
  "sampled_at": "2026-10-19T10:30:00Z",
  "received_at": "2026-10-19T10:30:00.142Z",
  "findings": [],
  "faults_created": 0
}
```

---

### 2.3 Live Dashboard (`/dashboard`)

| Method | Path | Auth Required | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/dashboard/live` | None | `device_id` (req) | Aggregates latest R/Y/B readings, open faults, and computes overall system status. |

#### Response Example (`GET /dashboard/live?device_id=1`):
```json
{
  "device_id": 1,
  "device_name": "Power Monitoring Unit 01 (Main Incomer)",
  "is_active": true,
  "system_status": "Normal",
  "phases": {
    "R": {
      "voltage": 230.4,
      "current": 4.35,
      "power": 982.0,
      "energy": 142.68,
      "power_factor": 0.98,
      "frequency": 50.02,
      "temperature": 34.6,
      "data_quality": "good",
      "sampled_at": "2026-10-19T10:30:00Z"
    },
    "Y": { ... },
    "B": { ... }
  },
  "open_faults": []
}
```

---

### 2.4 Faults Management (`/faults`)

| Method | Path | Auth Required | Parameters / Body | Description |
|---|---|---|---|---|
| `POST` | `/faults/` | **None (Vulnerability V-04)** | Query parameters | Manually insert a fault record. |
| `GET` | `/faults/` | None | `device_id` (opt), `status` (opt) | List faults sorted descending by detection time. |
| `GET` | `/faults/{fault_id}` | None | Path `fault_id` | Retrieve single fault record. |
| `PUT` | `/faults/{fault_id}/acknowledge` | **None (Vulnerability V-04)** | `acknowledged_by` (query) | Mark fault as acknowledged. |
| `PUT` | `/faults/{fault_id}/rectify` | **None (Vulnerability V-04)** | `resolution` (query) | Mark fault as rectified. |

---

### 2.5 Maintenance & Work Orders (`/maintenance`)

| Method | Path | Auth Required | Body | Description |
|---|---|---|---|---|
| `POST` | `/maintenance/work-orders` | **None (Vulnerability V-04)** | `{ fault_id, assigned_to, diagnosis }` | Dispatch work order ticket for a fault. |
| `GET` | `/maintenance/work-orders` | None | Filters: `fault_id`, `assigned_to`, `status` | Query active/closed work orders. |
| `GET` | `/maintenance/work-orders/{id}` | None | Path `id` | Detail view with attempt logs & fault data. |
| `POST` | `/maintenance/work-orders/{id}/attempts` | **None (Vulnerability V-04)** | `{ note, created_by }` | Append field diagnostic attempt note. |
| `PUT` | `/maintenance/work-orders/{id}/status` | **None (Vulnerability V-04)** | `{ status, diagnosis, actor }` | Transition status (`in_progress`, `restored`, `closed`). |

---

### 2.6 Relays & Contactor Actuation (`/relays`)

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/relays/` | **None (Vulnerability V-01)** | Register a new relay channel. |
| `GET` | `/relays/` | None | List relays, optionally filtered by `device_id`. |
| `GET` | `/relays/{relay_id}` | None | Retrieve relay status and GPIO mapping. |
| `POST` | `/relays/{relay_id}/on` | **CRITICAL: None (V-01)** | Turn relay ON. *(Requires immediate admin protection)* |
| `POST` | `/relays/{relay_id}/off`| **CRITICAL: None (V-01)** | Turn relay OFF. *(Requires immediate admin protection)* |

---

### 2.7 Campus Topology (`/locations`)

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/locations/colleges` | None | Create a new College record. |
| `GET` | `/locations/colleges` | None | List all Colleges. |
| `POST` | `/locations/blocks` | None | Create a new Block linked to a College. |
| `GET` | `/locations/blocks` | None | List Blocks (optional `college_id` filter). |
| `POST` | `/locations/floors` | None | Create a new Floor linked to a Block. |
| `GET` | `/locations/floors` | None | List Floors (optional `block_id` filter). |

---

### 2.8 Devices (`/devices`), Notifications (`/notifications`), Audit (`/audit`), Health (`/health`)

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/devices/` | None | Provision new device hardware. |
| `GET` | `/devices/` | None | List all registered devices. |
| `GET` | `/devices/{id}` | None | Retrieve device specifications and status. |
| `PUT` | `/devices/{id}` | None | Update device metadata. |
| `GET` | `/notifications/` | None | List system notifications (filter: `is_read`, `severity`). |
| `GET` | `/notifications/unread-count` | None | Count of unread alerts for badge counter. |
| `PUT` | `/notifications/{id}/read` | None | Mark single notification as read. |
| `PUT` | `/notifications/read-all` | None | Mark all notifications as read. |
| `GET` | `/audit/` | None | Query immutable audit trail logs. |
| `GET` | `/health` | None | Verify database connection and API liveness. |

---

## 3. Discrepancies & Audit Findings

1. **Missing Authentication on State-Changing Endpoints:**
   - With the exception of `/auth/me`, **none** of the state-changing endpoints enforce `Depends(get_current_user)` or check caller roles.
   - Anyone can call `POST /relays/1/off` or `POST /faults/` anonymously.
2. **`require_ingest` Header Bug:**
   - In `backend/app/core/security.py`, `require_ingest` combines `Depends(get_current_user)` which rejects requests without a Bearer token before verifying `X-Ingest-Key`.
3. **Relay Actuation Response Mismatch:**
   - `POST /relays/{id}/on` returns `{ "status": "success", "message": "...", "relay_id": 1, "is_on": true }`, but frontend `api.toggleRelay` expects the complete `Relay` entity.

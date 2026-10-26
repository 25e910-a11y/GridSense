# API Contract

**Status:** Contract for implementation and review. Existing route names are based on the current FastAPI routers; inspect `backend/app/main.py` for the mounted prefix before assuming `/api` is present. Request fields must match the Pydantic schemas and service behavior in the repository. This document does not claim every endpoint is currently secure or production-ready.

## 1. Conventions

- JSON request/response bodies except where documented otherwise.
- Use ISO-8601 timestamps with timezone offsets; normalize stored timestamps to UTC.
- Human-user endpoints require `Authorization: Bearer <access_token>` except login and a guarded bootstrap/provisioning path.
- Device telemetry uses a separate device credential, never a human JWT. Credential mechanism is an approval item.
- All IDs are database IDs unless named `device_id` in the device payload, which is the stable external identifier.
- Apply server-side authorization to every read/write route; frontend hiding is not security.
- Use bounded pagination/history windows before exposing large datasets. Existing telemetry currently returns at most 100 records in one list path; standardize pagination without breaking the current UI.
- Responses must not expose password hashes, ingest keys, signing secrets or internal stack traces.

## 2. Error format

Use a consistent envelope such as:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be validated.",
    "request_id": "optional-correlation-id",
    "details": []
  }
}
```

Keep compatibility with FastAPI's current error shape during a deliberate frontend/backend migration. Do not change all errors in an unrelated feature patch.

Expected status codes:
- `200` successful read/update; `201` resource created.
- `400` invalid operation/state; `401` unauthenticated/invalid token; `403` forbidden/inactive account.
- `404` resource not found; `409` duplicate/conflict; `422` schema or field validation.
- `429` rate limit; `500` unexpected server error; `503` required dependency unavailable.

## 3. Human authentication & User Administration

### `POST /auth/login`
Purpose: authenticate a human user.
Request: `username`, `password`.
Response: `access_token`, `token_type: "bearer"`, `role`, `username`, `assigned_block_id`, `assigned_floor_id`, `permissions`.
Rules: generic invalid-credentials response; token must expire. Never log credentials.

### `GET /auth/me`
Purpose: return authenticated identity, role, location scope, and granular permissions list.
Response: `authenticated`, `username`, `role`, `assigned_block_id`, `assigned_floor_id`, `permissions`.
Rules: missing/invalid/expired token returns 401 unauthenticated.

### `POST /auth/register`
Purpose: user self-registration.
Rules: strictly restricted to base `operator` role only. Callers cannot elevate privileges during registration.

### `GET /auth/users`
Purpose: list registered users, roles, active status, and location scopes (Admin only).
Requires: `manage_users` permission.

### `PUT /auth/users/{user_id}`
Purpose: update user operational role, activation status, and location scopes (Admin only).
Requires: `manage_users` permission. Automatically logs action to security audit trail.

### Logout
Frontend clears session token from storage. Interceptor clears on 401.

## 4. Telemetry

### `POST /telemetry/`
Purpose: ingest one phase sample and run rule evaluation.

Request concept:
- `device_id`: stable device identifier or existing schema's device reference, per actual `schemas/telemetry.py`.
- `phase`: `R`, `Y` or `B`.
- nullable measurements: `voltage`, `current`, `power`, `energy`, `power_factor`, `frequency`, `temperature`.
- `sampled_at`: device measurement timestamp.
- `sampling_interval_ms`, `transmission_reason`, `source`, `data_quality` where supported by the schema.

Response concept: success, stored telemetry ID, device/phase, sample and receipt timestamps, findings, and number of created/deduplicated faults. Never return credentials.

Rules:
- Authenticate the sending device independently from human users.
- Validate phase, timestamp, finite values, enums and device status.
- Record backend receipt time server-side.
- Distinguish communication/sensor errors from electrical anomalies.
- Commit telemetry and associated fault updates transactionally.
- Retry policy: device may retry transient network/5xx failures with bounded exponential backoff and jitter. Do not blindly retry permanent 4xx errors. Consider an idempotency/sample key before enabling retries that can duplicate records.

### `GET /telemetry/`
Purpose: recent telemetry with optional `device_id` and `phase` filters.
Target: bounded page size, stable ordering, date filters and authorization. Existing implementation returns a bounded recent set.

### `GET /telemetry/latest`
Purpose: latest reading for a device.
Current implementation requires a `device_id` query parameter. Target response must expose phase/quality/time clearly and not fabricate missing phases.

### `GET /telemetry/latest-by-phase`
Purpose: latest phase-specific values for a device.
Confirm exact query parameters and response shape from the current implementation before frontend contract changes.

## 5. Dashboard

### `GET /dashboard/live`
Purpose: aggregate current R/Y/B values, device health, open faults and overall status for a device.
Security: requires authenticated user and validates location scope for the requested device.
Target states: `Normal`, `Warning`, `Fault`, `Sensor/Communication Error`, `Offline`.

### `GET /dashboard/summary`
Purpose: aggregate executive-level KPI summary across campus infrastructure.
Security: requires `view_management_summary` permission (Management, Administrator, Electrical Engineer).
Response: `system_status`, `total_devices`, `active_devices`, `total_energy_kwh`, `total_active_power_kw`, `open_faults_count`, `open_work_orders_count`, `blocks_count`, `timestamp`.

## 6. Locations and devices

### Locations
- `POST /locations/colleges` — create a college; admin only.
- `GET /locations/colleges` — list permitted colleges.
- `POST /locations/blocks` — create a block under a valid college; admin only.
- `GET /locations/blocks` — list/filter blocks.
- `POST /locations/floors` — create a floor under a valid block; admin only.
- `GET /locations/floors` — list/filter floors.

Confirm query parameters from the current router before relying on specific filters.

### Devices
- `POST /devices/` — register/provision a device; admin only.
- `GET /devices/` — list permitted devices.
- `GET /devices/{device_id}` — device detail.
- `PUT /devices/{device_id}` — update allowed metadata; admin only.
- Device credentials must be provisioned/rotated through a secure flow and never returned in list/detail responses.

## 7. Faults and notifications

### Faults
- `POST /faults/` — internal/admin-controlled fault creation if retained; public device clients must not be allowed to fabricate trusted faults.
- `GET /faults/` — list faults with bounded filters/pagination.
- `GET /faults/{fault_id}` — detail.
- `PUT /faults/{fault_id}/acknowledge` — acknowledge with actor and timestamp.
- `PUT /faults/{fault_id}/rectify` — rectify with resolution and timestamp.
- Validate allowed status transitions and audit all lifecycle changes.

### Notifications
- `GET /notifications/` — list notifications for the authorized user/scope.
- `GET /notifications/unread-count` — unread count.
- `PUT /notifications/{notification_id}/read` — mark one read.
- `PUT /notifications/read-all` — mark all visible notifications read.
- Do not add email/SMS delivery until provider and consent/configuration are approved.

## 8. Maintenance

- `POST /maintenance/work-orders` — create/assign a work order with valid fault and assignee.
- `GET /maintenance/work-orders` — list permitted work orders with filters/pagination.
- `GET /maintenance/work-orders/{work_order_id}` — detail and timeline.
- `POST /maintenance/work-orders/{work_order_id}/attempts` — append a chronological attempt note.
- `PUT /maintenance/work-orders/{work_order_id}/status` — change status through allowed transitions only.
- Server must enforce role, assignment and state-transition rules; UI cannot be trusted to do so.
- State model documented by current project: `assigned` → `in_progress` → `restored` → `closed`. Confirm whether direct transitions are allowed before implementation.

## 9. Relays (disabled until approved)

Current route names:
- `POST /relays/` — create relay record.
- `GET /relays/` — list relays, optional device filter.
- `GET /relays/{relay_id}` — detail.
- `POST /relays/{relay_id}/on` and `/off` — currently mutate backend state.

**Security blocker:** these current endpoints must not be exposed to ordinary or unauthenticated users. Before enabling physical operation, require admin/authorized operator permission, explicit audit, durable command delivery, device acknowledgement, timeout handling, and confirmation that the hardware is safe and correctly rated. A successful API response must distinguish “command accepted” from “physical state confirmed.”

## 10. Audit and health

- `GET /audit/` — admin-only audit query with bounded pagination and safe filters.
- `GET /health/live` and `/health/ready` are recommended; check current routes before adding. Liveness confirms process is running; readiness checks required dependencies such as PostgreSQL.

## 11. Rate limits and timeouts

- Rate-limit login, account provisioning and telemetry ingestion.
- Use request timeouts for database and future external-service calls.
- Apply retries only to transient failures and idempotent operations.
- Do not add webhooks, external notification APIs or MATLAB endpoints until the service is approved and documented.

## 12. Environment variables

Use the names already established in settings where present. The deployment configuration must include, at minimum:
- `DATABASE_URL`
- `JWT_SECRET_KEY` (or the exact existing setting name; never rename silently)
- access-token expiry configuration
- production CORS allowed origins
- device credential configuration/rotation mechanism
- nominal voltage and fault thresholds used by the rule engine
- environment name / debug flag

The `.env.example` must contain placeholders only. Never expose secrets to Vite client variables or commit them to Git.

## 13. Privacy and failure handling

- Return only fields required by the client.
- Do not include secrets in logs, errors or audit details.
- A database failure must not produce a success response.
- If telemetry validation fails, do not create a genuine electrical fault from that invalid sample.
- Preserve server receipt time and device sample time separately.
- Use request IDs for support/debugging without exposing stack traces.

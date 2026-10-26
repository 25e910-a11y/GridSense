# Debugging & Root-Cause Analysis (Defect Log)

**Document Reference:** `docs/15_DEBUGGING_AND_ROOT_CAUSE.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## Defect Inventory Overview

| Defect ID | Severity | Subsystem | Title | Status |
|---|---|---|---|---|
| **DEF-01** | High | Backend Dashboard | Disconnected device erroneously reports status "Normal" | Identified / Fix Ready |
| **DEF-02** | High | Security / Telemetry | `require_ingest` raises 401 when IoT device sends `X-Ingest-Key` | Identified / Fix Ready |
| **DEF-03** | Critical | Relays API | Unauthenticated relay actuation & missing `commanded_state` update | Identified / Fix Ready |
| **DEF-04** | High | Database Migrations | `alembic upgrade head` fails on fresh database (missing `floors`) | Identified / Fix Ready |
| **DEF-05** | Medium | Rule Engine / Faults | Open faults never auto-resolve when electrical values return to normal | Identified / Fix Ready |
| **DEF-06** | Medium | Frontend Client | API client defaults `baseURL` to empty string, breaking static builds | Identified / Fix Ready |

---

## Detailed Root Cause Analysis (RCA)

### DEF-01: Disconnected Device Erroneously Reports Status "Normal"

- **Symptoms:** When an IoT monitoring unit loses power or Wi-Fi, the web dashboard continues to display status as `"Normal"` with historical metrics rather than `"Offline"`.
- **Reproduction Steps:**
  1. Insert telemetry for Phases R, Y, B with timestamp `2026-10-01 12:00:00`.
  2. Query `GET /dashboard/live?device_id=1` at current time (`2026-10-19`).
- **Expected Behavior:** System status should report `"Offline"`.
- **Actual Behavior:** System status reports `"Normal"`.
- **Code Evidence (`backend/app/api/dashboard.py:L101-L104`):**
  ```python
  if len(phases) < 3:
      return "Offline"
  return "Normal"
  ```
- **Root Cause:** The query fetches the most recent row for each phase (`.order_by(Telemetry.sampled_at.desc()).first()`). Since 3 historical rows exist in the database from weeks ago, `len(phases)` evaluates to 3 and returns `"Normal"`. The endpoint never compares `device.last_seen_at` against `settings.DEVICE_OFFLINE_SECONDS` (120s), unlike `services/health.py`.
- **Remediation:**
  In `dashboard.py`, inspect `device.last_seen_at`. If `now - last_seen_at > timedelta(seconds=settings.DEVICE_OFFLINE_SECONDS)`, immediately return `"Offline"`.
- **Regression Test:** Create unit test asserting device with stale `last_seen_at` returns `Offline`.

---

### DEF-02: `require_ingest` Raises 401 When IoT Device Sends `X-Ingest-Key`

- **Symptoms:** An ESP32 sending valid telemetry with header `X-Ingest-Key: <key>` receives HTTP 401 Unauthorized.
- **Reproduction Steps:**
  1. Set `INGEST_API_KEY=dev-secret` in `.env`.
  2. Send `POST /telemetry/` with header `X-Ingest-Key: dev-secret` without an `Authorization: Bearer` header.
- **Expected Behavior:** HTTP 200 OK with telemetry stored.
- **Actual Behavior:** HTTP 401 Unauthorized (`"Not authenticated"`).
- **Code Evidence (`backend/app/core/security.py:L94-L110`):**
  ```python
  def require_ingest(
      x_ingest_key: str | None = Header(default=None, alias="X-Ingest-Key"),
      user: User | None = Depends(get_current_user),  # <--- CRITICAL BUG
  ) -> None:
  ```
- **Root Cause:** FastAPI executes parameter dependencies before function entry. When `Depends(get_current_user)` runs, it checks for a Bearer token. Finding none, `get_current_user` raises an unhandled `HTTPException(401)`. The function body containing the ingest key check is never reached!
- **Remediation:**
  Decouple the dependency. Make `require_ingest` accept `creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)`. Check `x_ingest_key == settings.INGEST_API_KEY` first. If valid, return immediately. If not valid, check `creds` for a valid user token.
- **Regression Test:** Test `require_ingest` with only `X-Ingest-Key` header present.

---

### DEF-03: Unauthenticated Relay Actuation & Incomplete State Mutation

- **Symptoms:** Relays can be triggered by anyone; `relay.commanded_state` is never updated.
- **Reproduction Steps:**
  1. Send `POST /relays/1/on` with no authentication headers.
- **Expected Behavior:** HTTP 401 Unauthorized; relay state unchanged.
- **Actual Behavior:** HTTP 200 OK (`"Relay turned ON"`).
- **Code Evidence (`backend/app/api/relays.py:L115-L144`):**
  ```python
  @router.post("/{relay_id}/on")
  def turn_relay_on(relay_id: int, db: Session = Depends(get_db)):
      ...
      relay.is_on = True # commanded_state is NOT updated!
      db.commit()
  ```
- **Root Cause:** Missing authentication dependency and incomplete model mutation.
- **Remediation:**
  1. Add `user: User = Depends(require_admin)` to `/relays/{id}/on` and `/off`.
  2. Update both `relay.is_on = True/False` and `relay.commanded_state = True/False`.
  3. Call `write_audit(db, actor=user.username, action="relay_on", ...)` on every toggle.
  4. Return full `Relay` schema to align with frontend `api.ts`.
- **Regression Test:** Assert anonymous POST to `/relays/1/on` returns 401; assert admin POST updates both `is_on` and `commanded_state` and logs audit entry.

---

### DEF-04: Alembic Migration Crash on Clean Database

- **Symptoms:** `alembic upgrade head` fails on a fresh database.
- **Reproduction Steps:**
  1. Delete local `.db` file or point to clean PostgreSQL database.
  2. Run `alembic upgrade head`.
- **Expected Behavior:** All tables created smoothly.
- **Actual Behavior:** `no such table: floors` error during creation of `devices`.
- **Code Evidence (`backend/alembic/versions/53f1a59aca1d_create_devices_table.py:L32`):**
  `sa.ForeignKeyConstraint(['floor_id'], ['floors.id'])`
- **Root Cause:** Migration was generated without including parent tables (`colleges`, `blocks`, `floors`).
- **Remediation:** Consolidate migrations into a single baseline migration creating all tables in topological order.
- **Regression Test:** Run `alembic upgrade head` in CI on a completely clean SQLite and PostgreSQL database.

---

### DEF-05: Missing Automatic Fault Resolution on Recovery

- **Symptoms:** A transient fault (e.g. temporary load spike) stays permanently active in the `faults` table.
- **Reproduction Steps:**
  1. Post telemetry sample with $I = 45.0\text{ A}$ (Overcurrent detected).
  2. Post telemetry sample with $I = 4.2\text{ A}$ (Normal condition).
- **Expected Behavior:** Overcurrent fault transitions to `rectified` or clears.
- **Actual Behavior:** Overcurrent fault remains `status = "detected"` indefinitely.
- **Code Evidence (`backend/app/services/faults.py:L12-L38`):**
  `record_findings()` only inserts or updates open faults for current findings; it never inspects whether previously active faults have cleared.
- **Remediation:** In `record_findings()`, query open faults for that phase. If an open fault's `fault_type` is not present in the new findings and the new sample is valid, transition it to `status = "rectified"` with resolution `"Auto-cleared: values returned to nominal range"`.
- **Regression Test:** Send abnormal sample followed by normal sample; assert fault status is `rectified`.

---

### DEF-06: Frontend API Base URL Broken in Static Production Builds

- **Symptoms:** When frontend is built (`npm run build`) and hosted statically, API calls fail.
- **Reproduction Steps:**
  1. Build frontend with `npm run build`.
  2. Serve `dist/` from an independent static server on port 3000 with backend on port 8000.
- **Expected Behavior:** Frontend sends requests to `http://127.0.0.1:8000/telemetry/`.
- **Actual Behavior:** Frontend sends requests to `http://127.0.0.1:3000/telemetry/` (HTTP 404).
- **Code Evidence (`frontend/src/services/api.ts:L16-L22`):**
  `baseURL: ''`
- **Root Cause:** Client relies solely on Vite development proxy.
- **Remediation:** Change to `baseURL: import.meta.env.VITE_API_BASE_URL || ''`.

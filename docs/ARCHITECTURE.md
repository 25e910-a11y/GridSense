# Architecture

## 1. Architecture decision

Use a modular monolith: React + TypeScript frontend, FastAPI backend, SQLAlchemy ORM, PostgreSQL and Alembic migrations. This matches the existing repository and is simpler to operate than microservices.

## 2. Current stack found in repository

- Frontend: React 19, TypeScript 6, Vite 8, React Router, Axios, Recharts, lucide-react, Oxlint.
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy 2, PostgreSQL driver, Alembic, python-jose and pytest.
- Database: PostgreSQL.
- Existing backend modules include API routers for auth, telemetry, dashboard, devices, locations, faults, notifications, maintenance, relays and audit; models for users, locations, devices, telemetry, faults, notifications, work orders, relays and audit.
- Firmware, MATLAB and ML capabilities are not assumed complete simply because directories or documentation mention them.

Do not replace this stack without a measured need and owner approval.

## 3. Logical components

1. **Firmware:** reads three PZEM devices, DS18B20 and RTC; validates measurements and sends telemetry. Must not embed database credentials or human-user tokens.
2. **HTTP API:** FastAPI routes, request/response schemas, authentication dependencies and error mapping.
3. **Domain services:** telemetry validation, device health, rule evaluation, fault deduplication, notifications, maintenance state transitions and audit logging.
4. **Persistence:** SQLAlchemy models/session and Alembic migrations over PostgreSQL.
5. **Frontend:** route/page components, reusable UI components, API service modules, typed DTOs and role-aware navigation.
6. **Rule engine:** deterministic and testable rules. No ML claims or model dependency in MVP.
7. **Integrations:** device HTTP telemetry now; MATLAB and ML later, behind explicit interfaces.

## 4. Data flow

### Telemetry
Device → device authentication → schema validation → timestamp/quality validation → telemetry insert → update device last-seen → evaluate rules using current sample and relevant prior/peer-phase data → create/update fault records and notifications → commit transaction → dashboard reads persisted state.

Fault creation and telemetry persistence should be transactionally consistent where practical. A failed database transaction must not return success.

### Dashboard
Browser → FastAPI authenticated read endpoint → bounded/indexed PostgreSQL query → response DTO → UI with loading/stale/error state. Do not let the browser connect directly to PostgreSQL.

### Maintenance
User action → authentication and role check → service validates current work-order state and assignment → transaction updates work order/fault and writes audit/timeline → response.

### Relay commands (conditional)
User → server permission check and confirmation → durable command record → device command channel → device acknowledgement/timeout → actual state updated only from verified device feedback. Until this exists, DB relay state is not evidence of physical switching.

## 5. Folder structure

Follow the existing layout and avoid broad reorganization:

```text
/
  PRD.md
  DESIGN.md
  ARCHITECTURE.md
  DATABASE.md
  API.md
  AGENTS.md
  IMPLEMENTATION_PLAN.md
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      rules/
      auth/            # use only if already established; avoid duplicate security implementations
    alembic/
    tests/
    requirements.txt
  frontend/
    src/
      app/              # routing and app shell
      components/
      pages/
      services/         # API client
      hooks/
      types/
      styles/
    package.json
  firmware/
  matlab/
  database/
  docs/
```

The actual frontend may use a different existing source layout; inspect it and preserve current conventions rather than forcing this illustrative tree.

## 6. Database interaction

- Use SQLAlchemy sessions through the existing dependency.
- Keep query logic in service/repository functions when reuse or transaction boundaries justify it; do not create abstractions for every trivial query.
- Use Alembic for all schema changes. Never manually alter production schema without a migration.
- Use UTC-aware timestamps. Store sampled time and received time separately.
- Use bounded time ranges for telemetry endpoints.
- Add indexes based on actual filters/orderings: device + phase + sampled time; fault status/detected time; work-order status/assignee; hierarchy foreign keys.
- Use database transactions for telemetry plus fault creation and for maintenance transitions.
- Do not enable PostgreSQL row-level security for the single-site MVP unless a real tenant/row ownership boundary is approved. Enforce role/resource access in API services.

## 7. Authentication and authorization

- Keep password hashes only; use a modern password hashing algorithm and adequate work factor. The repository currently uses PBKDF2; review and document parameters before production.
- Access tokens must expire. Validate signature, expiry and subject on every protected request.
- Do not permit public callers to choose privileged roles during registration. Use admin provisioning or a guarded bootstrap.
- Human users use JWT bearer tokens; devices use separate device credentials or request signatures.
- Every state-changing endpoint must have a server-side permission dependency and audit where material.
- Suggested MVP matrix:
  - `admin`: all application administration and operational actions.
  - `operator`: read monitoring/fault data; acknowledge/triage if allowed; no user/threshold administration.
  - `technician`: read relevant monitoring/faults and update assigned work orders.
- Scope for assigned technicians and site-specific access requires implementation and tests; current schema does not yet show a user-to-site scope model.
- CORS must allow only configured frontend origins in production.

## 8. API architecture

- REST JSON under `/api` only if the existing app is configured that way; inspect `main.py` before changing route prefixes.
- Keep request/response schemas explicit and version-compatible.
- Use consistent HTTP status codes and structured error responses.
- Validate payloads at the boundary and domain invariants in services.
- Keep generated OpenAPI docs available in development; restrict or disable them in production if the deployment requires it.
- Device ingestion and human APIs must use distinct authentication dependencies.

## 9. AI/ML

No AI/ML model is required for the MVP. Use transparent rule-based detection first. Future ML work requires real labeled data, a documented evaluation set, baseline comparison, versioned model metadata and a safe disabled-by-default feature flag. ML predictions must not directly actuate relays.

## 10. Environment configuration

- Read configuration from environment variables/Pydantic Settings.
- Maintain `.env.example` with placeholders only; exclude `.env` from Git.
- Required configuration includes database URL, JWT signing secret, token expiry, device credential strategy, CORS origins, and rule thresholds/nominal values.
- Fail fast on missing production secrets; do not silently use development defaults in production.
- Never log secrets or full authorization headers.

## 11. Error handling and observability

- Translate expected validation/domain errors to clear 4xx responses.
- Return 401 for missing/invalid authentication, 403 for insufficient permission, 404 for absent resources, 409 for conflicts, 422 for schema/validation failures, and 5xx for unexpected server failures.
- Do not expose stack traces or SQL details to clients.
- Log structured event context: request ID, route, status, actor/device ID when safe, and failure category.
- Separate device offline, sensor communication failure, invalid sample and electrical fault states.
- Health checks should distinguish process liveness from database readiness.

## 12. Security boundaries and safety

- Browser is untrusted; client-side role checks are UX only.
- Device IDs are not secrets. Require device authentication and rotate credentials.
- Rate-limit login and device ingestion at the application/reverse-proxy layer appropriate to deployment.
- Protect against injection through ORM/parameterized queries; avoid rendering untrusted strings as HTML.
- Relay operations require command authorization, audit, acknowledgement and electrical engineering safety review.
- SSRs are not substitutes for rated protective devices. Do not implement automatic disconnection as a protection claim.

## 13. Testing

- Backend unit tests: rules, validation, fault deduplication and state transitions.
- Backend integration tests: API + test database, auth and role matrix.
- Frontend: build/typecheck/lint plus component or browser tests for critical flows as the existing test setup permits.
- Contract tests: firmware payload examples against Pydantic schema.
- Safety-critical relay tests are not a substitute for hardware-in-the-loop validation and qualified electrical review.
- Use deterministic fixtures; never rely on live mains or production data in automated tests.

## 14. Deployment

MVP deployment can be one backend service, one static frontend deployment and one PostgreSQL instance, or a single local-network host if institutional constraints require local operation. The final target is unconfirmed.

- Use HTTPS when traffic crosses untrusted networks.
- Run migrations as a controlled deployment step.
- Configure backups and test restoration.
- Use a non-root runtime and least-privilege database account.
- Verify production build, health checks, auth, CORS and environment variables before release.

## 15. MVP vs future scale

**MVP:** modular monolith, one PostgreSQL database, REST, simple polling dashboard, rule engine, basic audit and maintenance.

**Future only when justified:** WebSockets/MQTT broker, background queue, partitioned telemetry tables, separate analytics service, multi-site tenant isolation, model serving, MATLAB simulation pipeline. Do not add these before a measured requirement.

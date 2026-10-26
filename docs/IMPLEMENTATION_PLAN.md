# Implementation Plan

This plan is based on the repository snapshot and project documents. It is a plan, not a claim that the listed work has already been verified. Start by auditing current behavior and Git status before modifying anything.

## Phase 0 — Baseline and decisions

**Goal:** establish a reliable baseline and resolve blockers before adding features.

Tasks:
1. Inspect Git status/diff, frontend source, backend routes/models/services, Alembic history, `.env.example`, `.gitignore` and test configuration.
2. Run existing backend tests and frontend lint/build; record failures without changing behavior.
3. Compare mounted route prefixes, Pydantic telemetry schema, model fields and current migrations against API/DATABASE docs.
4. Decide account provisioning, role matrix, device authentication, relay MVP status, threshold ownership, retention/backups and deployment target.

Likely files: `README.md`, `docs/*`, `backend/app/main.py`, `backend/app/core/*`, `backend/alembic/*`, `frontend/package.json`.

Dependencies: none.
Database/API changes: none.
Tests: baseline pytest, frontend build and lint.
Completion criteria: baseline report exists; decisions are recorded; no user changes overwritten.

## Phase 1 — Authentication and authorization hardening

**Goal:** prevent unauthenticated or low-privilege callers from changing protected data.

Tasks:
1. Inventory every route and mark public, human-authenticated or device-authenticated.
2. Restrict user provisioning; remove caller-selected privileged roles from public registration.
3. Enforce token expiry, active-user checks and role dependencies on all protected endpoints.
4. Add separate device credential verification for telemetry ingestion; do not expose ingest secrets.
5. Protect device, location, fault, maintenance, audit, notification and relay routes according to the approved matrix.
6. Add rate limiting for login and account provisioning at the simplest supported layer.
7. Add security audit records for sensitive actions.

Likely files: `backend/app/api/auth.py`, route modules, `backend/app/core/security.py`, schemas, audit service, tests.
Dependencies: Phase 0 decisions.
Database/API changes: potentially device credential storage/migration and auth response behavior.
Tests: unauthenticated access, each role per endpoint, inactive users, invalid/expired token, self-escalation attempt, device credential rejection.
Completion criteria: all state-changing routes have explicit server-side permission checks; tests prove forbidden actions fail.

## Phase 2 — Schema and migration integrity

**Goal:** ensure database constraints and query paths match real data behavior.

Tasks:
1. Compare models to Alembic migration history and actual development schema.
2. Add migrations for phase/source/status checks and confirmed uniqueness constraints.
3. Add composite indexes only where queries require them.
4. Resolve relay state duplication (`is_on`, `commanded_state`, `actual_state`) without losing data.
5. Confirm notification, work-order, work-attempt and audit model fields and relationships.
6. Document safe local seed strategy and migration rollback limitations.

Likely files: `backend/app/models/*`, `backend/alembic/versions/*`, `database/*`, `docs/data_dictionary.md`.
Dependencies: Phase 0 and authorization decisions.
Database/API changes: Alembic migrations; avoid destructive schema changes.
Tests: migrations on empty DB; upgrade existing fixture DB; constraint violation tests; FK integrity.
Completion criteria: clean migration to head and no destructive change without approval.

## Phase 3 — Telemetry contract and ingestion reliability

**Goal:** reliably accept valid device samples and reject bad data.

Tasks:
1. Align telemetry Pydantic schema, API.md and firmware payload contract.
2. Validate phase, finite numeric values, enum values, timestamps, sampling interval and data quality.
3. Implement device authentication and credential rotation approach.
4. Set `received_at` on the server; update `last_seen_at` only for authenticated valid contact.
5. Ensure telemetry insert and rule/fault updates have consistent transaction behavior.
6. Add idempotency protection if the firmware retries samples.
7. Standardize API errors and bounded telemetry query filters.

Likely files: `backend/app/api/telemetry.py`, `schemas/telemetry.py`, `services/validation.py`, device/auth service, models, tests, firmware docs.
Dependencies: Phases 1–2.
Database/API changes: credential/idempotency fields only if approved.
Tests: valid R/Y/B payloads, invalid phase, missing/NaN values, bad timestamps, unknown/inactive device, duplicate retry, DB rollback.
Completion criteria: payload contract documented and tests verify persistence plus safe failures.

## Phase 4 — Rule engine and fault lifecycle

**Goal:** make fault detection deterministic, explainable and non-spammy.

Tasks:
1. Review current rule engine and threshold configuration units/defaults.
2. Define canonical categories, severities and lifecycle states.
3. Verify under/over-voltage, overcurrent, imbalance, sudden changes, high temperature and loss-of-voltage logic against approved thresholds.
4. Confirm communication failure never becomes phase-loss without corroborating evidence.
5. Verify open-fault deduplication and clear/rectification behavior.
6. Ensure fault/notification updates and audit events are consistent.

Likely files: `backend/app/rules/*`, `backend/app/services/faults.py`, notification/audit services, fault models and tests.
Dependencies: Phase 3.
Database/API changes: status/category constraints if confirmed.
Tests: boundary values, no-data/invalid-data cases, peer-phase comparison, repeated fault deduplication, fault recovery and transaction rollback.
Completion criteria: each rule has documented rationale and deterministic tests; thresholds remain configurable.

## Phase 5 — Dashboard and history API

**Goal:** expose correct, bounded and clear monitoring data.

Tasks:
1. Validate `/dashboard/live` aggregation and system status precedence.
2. Ensure latest-by-phase returns R/Y/B independently with quality and timestamps.
3. Add bounded history filters and stable ordering/pagination where needed.
4. Verify device online/offline/stale classification from last-seen and configured timeout.
5. Align frontend types and service functions to actual API response schemas.

Likely files: `backend/app/api/dashboard.py`, `telemetry.py`, health service, frontend services/types/pages.
Dependencies: Phases 1–4.
Database/API changes: optional query parameters and response DTO alignment.
Tests: no telemetry, partial phases, stale data, offline device, open fault, mixed quality, large date range.
Completion criteria: dashboard never fabricates zero/normal values for missing data and clearly reports stale data.

## Phase 6 — Frontend UX and design system alignment

**Goal:** make the monitoring UI consistent, responsive and accessible.

Tasks:
1. Inspect existing page/routes and preserve working components.
2. Implement shared status badge, phase card, metric, chart panel, fault row, loading/empty/error patterns.
3. Wire login and protected routes to the secured API.
4. Implement overview, location/device detail, fault list/detail, maintenance and notifications.
5. Show sampled time, freshness and quality with all readings.
6. Verify desktop/tablet/mobile layouts and keyboard operation.

Likely files: existing `frontend/src` pages/components/services/types/styles; do not force a new folder structure if current conventions differ.
Dependencies: Phase 5 API contract.
Database/API changes: none unless an API gap is found and approved.
Tests: TypeScript build, lint, component/flow tests where available, manual responsive/accessibility check.
Completion criteria: all critical user journeys have real API wiring and explicit loading/empty/error/forbidden states.

## Phase 7 — Fault maintenance workflow

**Goal:** make investigation and restoration traceable.

Tasks:
1. Verify work-order assignment and permitted transitions.
2. Enforce assignment/role checks on detail, attempts and status changes.
3. Record attempts chronologically with actor and timestamp.
4. Tie restoration/closure to the associated fault consistently.
5. Display work timeline and current state in the frontend.

Likely files: `backend/app/api/maintenance.py`, work-order model/service, fault service, audit, frontend maintenance pages and tests.
Dependencies: Phases 1, 2, 4 and 6.
Database/API changes: only if current work-attempt representation cannot support requirements; approve migration first.
Tests: transition matrix, unauthorized assignee, invalid fault, repeated close, attempt ordering, transaction failure.
Completion criteria: every transition is enforced and auditable.

## Phase 8 — Relay decision and safe command path (only if approved)

**Goal:** avoid confusing a stored command with physical switching.

Tasks:
1. Decide whether relays are in MVP; default recommendation is to defer physical control.
2. Review SSR-40DA ratings, load type, wiring, isolation, protective devices and qualified electrical safety review.
3. Specify firmware command protocol, acknowledgement, timeout, retry/idempotency and safe fallback.
4. Implement durable command/acknowledgement state and strict role checks only after approval.
5. Add confirmation UI and audit trail.

Likely files: relay model/API/service, device firmware, frontend control UI, tests and safety documentation.
Dependencies: Phases 1–2 and explicit owner/electrical approval.
Database/API changes: command state/ID/timestamps and device acknowledgement if needed.
Tests: permission, command accepted, acknowledged, timeout, device offline, duplicate command, hardware-in-loop testing by qualified personnel.
Completion criteria: no command is described as physically successful until the device confirms it. If not approved, mark relay controls disabled.

## Phase 9 — Audit, operations, backup and deployment

**Goal:** prepare a controlled pilot deployment.

Tasks:
1. Verify audit events and redact sensitive values.
2. Add/verify liveness and readiness checks.
3. Document environment variables and safe production defaults.
4. Configure CORS, HTTPS, non-root service, database least privilege and production docs policy.
5. Define backup retention and restore procedure with owner approval.
6. Run migrations in deployment pipeline and verify production build.
7. Perform a staging restore test and smoke test critical user journeys.

Likely files: app config, `main.py`, deployment files if present, `.env.example`, README, CI configuration and docs.
Dependencies: Phases 1–7; Phase 8 only if relay control is approved.
Database/API changes: health endpoints or audit metadata if needed.
Tests: readiness with DB up/down, production frontend build, auth/API smoke tests, backup restore drill.
Completion criteria: repeatable deployment, tested recovery and no secrets in repository.

## Phase 10 — Simulation and ML (future, not MVP)

**Goal:** add simulation/ML only when core monitoring is reliable and there is a validated need.

Tasks: implement MATLAB API and simulation devices/scenarios; manage dataset quality and labels; establish baseline rule metrics; train/evaluate model; store model/prediction metadata; keep ML disabled until validation.
Dependencies: stable telemetry, data quality, labels and approved evaluation criteria.
Completion criteria: reproducible evaluation against real labeled data; no ML-based actuation; `ML_ENABLED` remains false until approval.

## Recommended first task

**Phase 0, Task 1: perform a read-only baseline audit of the existing repository**—Git status, current routes and permissions, database migrations/models, frontend pages, environment/configuration files, and test/build results. Do not start new features until this baseline exposes the real gaps and the owner approves the key decisions.

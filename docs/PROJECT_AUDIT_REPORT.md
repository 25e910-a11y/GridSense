# Project Audit Report — IoT-Based Power Monitoring & Fault Identification System

**Audit type:** Static repository/document review of the uploaded ZIP and project context.
**Date:** 19 October 2026.
**Important limitation:** This review inspected files and source snippets from the archive; it did not run the application, connect to PostgreSQL, run tests/builds, verify the live schema, inspect the physical circuit, or exercise real hardware. Findings below are not a production certification.

## 1. Executive summary

The repository already has a substantial software foundation: a React/TypeScript/Vite frontend, FastAPI backend, SQLAlchemy models, PostgreSQL/Alembic structure, rule engine, telemetry endpoints, fault lifecycle, maintenance endpoints, notifications, audit and relay records. Existing project documentation lists foundation, monitoring, fault and maintenance tasks as completed, while MATLAB simulation, data export/backup, dataset management and ML phases remain unfinished.

**Current launch verdict: NOT READY for production or physical relay control based on static review.** The largest blockers are route-level authorization, unsafe role provisioning, device authentication not yet established from the inspected code, and the distinction between database relay state and actual hardware acknowledgement. Tests/build and deployment were not executed, so readiness cannot be upgraded based on documentation claims alone.

## 2. What exists in the repository

- Frontend package manifest uses React, TypeScript, Vite, React Router, Axios, Recharts and lucide-react.
- Backend requirements include FastAPI, Uvicorn, SQLAlchemy, Pydantic Settings, PostgreSQL driver, Alembic, JWT library, HTTPX and pytest.
- API router modules exist for authentication, telemetry, dashboard, devices, locations, faults, notifications, maintenance, relays and audit.
- Models exist for users, college/block/floor hierarchy, devices, telemetry, faults, notifications, work orders, relays and audit.
- Rule-engine files exist under `backend/app/rules/`.
- Current documentation specifies XIAO ESP32-S3, three PZEM-004T V4 units for R/Y/B, CTs, DS3231, DS18B20 and associated hardware. MQ-135 is explicitly removed.
- Current docs list the following as unfinished: MATLAB API integration, simulation devices/scenarios/demo data, export, backup automation, dataset management, ML settings/demo/prediction storage/evaluation/model registry and actual ML training/evaluation.

## 3. Findings by severity

### Critical — must fix before any production exposure

1. **Authorization is not consistently enforced in inspected routes.** The inspected relay router functions do not show authentication/authorization dependencies. The authentication router's registration endpoint accepts a role field and currently maps allowed values including `admin`; an untrusted caller may be able to self-register with a privileged role unless route exposure is otherwise restricted. Several other routers must be checked systematically.
   - **Risk:** unauthorized relay state changes, data mutation or privilege escalation.
   - **Required fix:** add explicit server-side role dependencies to every protected route; make user provisioning admin-only or use a protected first-admin bootstrap; add a role-by-endpoint test matrix.

2. **Physical relay control is not proven end-to-end.** Current `/relays/{relay_id}/on` and `/off` handlers change database fields. The inspected implementation does not demonstrate a command sent to firmware or a device acknowledgement.
   - **Risk:** UI/API may claim the relay changed when only the database row changed; unsafe operational assumptions.
   - **Required fix:** disable physical control until a durable command/acknowledgement path, authorization, timeout/error handling, audit and qualified electrical safety review are complete.

3. **Device authentication is not established by the inspected telemetry path.** The device model has an `ingest_key` field, but the inspected telemetry snippet did not demonstrate a device credential dependency.
   - **Risk:** an exposed ingestion endpoint may accept forged telemetry or fabricated fault evidence.
   - **Required fix:** verify complete telemetry route dependencies; implement separate per-device credentials/signatures, rotation/revocation and tests before exposing ingestion beyond a trusted local development network.

### High — resolve before pilot deployment

4. **Current documented roles and earlier project discussions differ.** Repository code uses `admin`, `operator`, `technician`; other project context mentioned developer/admin/moderator/maintenance/management.
   - **Risk:** inconsistent permission expectations and UI/backend mismatch.
   - **Required fix:** approve one role matrix and map real user responsibilities before implementation.

5. **Relay state has overlapping fields.** The current relay model contains `commanded_state`, `actual_state`, and `is_on`.
   - **Risk:** unclear source of truth; frontend may read a field that is not physical feedback.
   - **Required fix:** define canonical commanded vs confirmed state and migrate safely after inspecting existing data.

6. **Telemetry query contract needs verification.** Telemetry model includes sampled/received timestamps, quality/source/transmission metadata; endpoint schemas and query behavior must be checked against firmware payloads and UI consumers.
   - **Risk:** incorrect phase/time interpretation, stale values presented as current, duplicate records on retries.
   - **Required fix:** contract tests, timestamp validation, quality handling, bounded date filters and idempotency strategy.

7. **Thresholds are configuration-sensitive.** README gives example threshold bands, but those are not verified installation settings.
   - **Risk:** false positives/negatives if example defaults are treated as commissioned limits.
   - **Required fix:** obtain owner/qualified engineer approval for nominal voltage, overcurrent limits, imbalance definition, temperature limit and sudden-change rules.

8. **Production deployment/recovery has not been verified.** Current task document leaves backup automation unfinished; deployment target is unconfirmed.
   - **Risk:** data loss or insecure exposure.
   - **Required fix:** select hosting/local-network target, configure HTTPS/CORS/secrets, least-privilege DB access, backups and a tested restore procedure.

### Medium — improve before stable pilot

9. **Test claims need execution evidence.** README states 13 tests pass, but this audit did not execute pytest or the frontend build.
   - **Fix:** run `pytest -v`, frontend build and lint; report actual output and address failures.

10. **API errors and pagination need consistent contracts.** Several list endpoints appear bounded or unpaginated in the inspected code.
    - **Fix:** standardize error envelopes gradually; add bounded filtering/pagination where query volume requires it.

11. **Audit completeness and secret redaction need review.** An audit service/model exists, but completeness and redaction were not fully verified.
    - **Fix:** test sensitive operations and assert no passwords, tokens or ingest secrets enter audit/log records.

12. **Generated/vendor content in the ZIP increases size.** The archive contains a `.git` directory, a large frontend `node_modules` tree and Python `__pycache__` entries.
    - **Fix:** exclude dependency folders, caches, build outputs and local secrets from future source handover archives; retain lockfiles and source.

## 4. Recommended next actions (ordered)

1. Read-only baseline: inspect Git status/diff, all route dependencies, config, migrations and frontend API usage.
2. Run existing backend tests, frontend build and lint; save logs.
3. Fix public role escalation and apply authorization to every route.
4. Establish separate device authentication and test telemetry ingestion security.
5. Decide role matrix, relay MVP status and approved electrical thresholds.
6. Reconcile relay commanded/actual state semantics.
7. Verify migrations and add constraints/indexes without destructive changes.
8. Align telemetry contract and dashboard freshness/error behavior.
9. Test maintenance transitions, fault deduplication and audit coverage.
10. Prepare deployment, backups and recovery only after the above passes.

## 5. Decisions requiring project-owner approval

- Final user roles and permissions.
- Account provisioning strategy.
- Device authentication mechanism and credential rotation.
- Whether relay control is MVP; recommendation is to defer physical switching until verified end-to-end.
- Approved fault thresholds and their units.
- Deployment target: local network, institutional server or cloud.
- Telemetry retention and backup/recovery objectives.
- Whether MATLAB simulation and ML should be pursued after MVP.

## 6. Verification status

| Area | Static review status | Runtime verified? |
|---|---|---|
| Frontend/backend stack | Identified in manifests | No |
| API modules/models | Present in archive | No |
| PostgreSQL/Alembic | Referenced by project | No |
| Authentication/authorization | Critical gaps identified in inspected routes | No |
| Rule engine | Files and documentation exist | No |
| Telemetry end-to-end | Not verified against physical firmware | No |
| Relay physical control | Not demonstrated; current handlers mutate database state | No |
| Tests | README claims tests exist | Not run |
| Frontend build/lint | Scripts exist | Not run |
| Deployment/backup/restore | Not verified; backup task listed unfinished | No |
| Electrical safety/hardware | Project docs reviewed only | No |

## 7. Conclusion

The project is a promising prototype codebase with much of the expected modular structure already present. The next step should be a verification and security-hardening pass, not another large feature build. Do not expose it to a production network or rely on it to switch mains loads until authentication, authorization, device acknowledgement, deployment recovery and physical safety are independently verified.

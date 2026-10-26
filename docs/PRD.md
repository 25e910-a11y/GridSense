# Product Requirements Document (PRD)

**Product:** IoT-Based Power Monitoring and Fault Identification System
**Status:** Draft for approval; describes the intended MVP and distinguishes existing code from unverified behavior.
**Primary source:** Current project repository, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/data_dictionary.md`, `docs/RULES.md`, `docs/TASKS.md`, and project context supplied by the owner.

## 1. Problem

Electrical distribution teams need a way to see phase-wise operating conditions, identify abnormal readings, review historical measurements, and coordinate fault investigation. Manual inspection and isolated meter readings make it harder to see trends and trace incidents.

## 2. Value proposition

Provide one dashboard and backend for collecting validated 3-phase measurements, showing current and historical status, detecting rule-based abnormalities, recording timestamped events, and supporting maintenance follow-up. The system is an engineering monitoring and fault-identification aid, not a certified protective relay or replacement for electrical protection.

## 3. Target users & Operational Roles

- **Operator:** monitors live electrical measurements and phase summaries within authorized location scope; read-only access (no fault ack, no work-order dispatch, no relay switching, no audit access).
- **Shift In-Charge:** operational area lead; reviews alarms, acknowledges faults, and coordinates/dispatches maintenance work orders within authorized scope.
- **Electrical Engineer:** technical lead; accesses detailed 3-phase diagnostics, trend comparisons, rectifies faults, and manages technical maintenance investigations.
- **Management:** executive viewer; monitors high-level campus/block/floor summaries, energy consumption trends, KPIs, and incident counts across authorized locations (strictly read-only).
- **Technician / Maintenance:** field staff; accesses work orders assigned directly to them, records repair attempts, observations, and updates progress transitions.
- **Administrator:** manages system configuration, user accounts, role provisioning, device registration, SSR relay actuation, and security audit trail.
- **Device / Firmware Client:** sends authenticated telemetry from the XIAO ESP32-S3 over dedicated ingest credentials.

## 4. Product scope and system boundary

### Core hardware and measurements
- Seeed Studio XIAO ESP32-S3.
- Three PZEM-004T V4 meters, one assigned to each R/Y/B phase, with CTs as specified by the current project context.
- DS3231 RTC and DS18B20 temperature sensor.
- Existing supply, wiring, fuses, terminals, connectors and switching components must be verified against the actual build and datasheets before commissioning.
- Measurements: voltage (V), current (A), active power (W), energy (kWh), frequency (Hz), power factor where available, and temperature (°C).

MQ-135 is explicitly removed and must not be reintroduced.

### Core flow
**Monitor → Validate → Analyse → Identify → Log → Display/Alert → Maintain**

### MVP boundaries
MVP is a single pilot installation with a College → Block → Floor → Device hierarchy, three phase readings per device, live/historical dashboard views, rule-based fault events, and basic maintenance workflow. Do not assume a multi-campus SaaS tenancy model.

## 5. Core user journeys

1. **Sign in:** user submits credentials; backend validates them and returns a token; protected pages and APIs enforce permissions.
2. **Check system status:** user opens the dashboard, sees device online/offline/communication status, latest phase readings, system status and open faults.
3. **Drill down:** user selects a college/block/floor/device and inspects phase-specific values and trends.
4. **Investigate an event:** operator opens a fault, sees type, severity, phase, timestamp, measured value and threshold/expected value, and acknowledges it if authorized.
5. **Complete maintenance:** technician opens an assigned work order, records attempts and diagnosis, marks restoration, and closes the incident according to the allowed state transitions.
6. **Ingest telemetry:** device sends a payload; backend authenticates the device, validates units/phase/time/quality, persists it, updates device health, evaluates rules, and creates/deduplicates fault records.
7. **Operate a relay (guarded/approval-dependent):** authorized user requests a relay state change; backend records a command and reports commanded state separately from device-confirmed actual state. **Do not expose physical switching as operational until firmware acknowledgement, authorization, interlocks and electrical safety review are verified.**

## 6. User stories and acceptance criteria

- As an operator, I can see the latest R/Y/B readings for a device so I can compare phases quickly.
  - Each value shows its unit, sample timestamp and quality/staleness state.
- As an operator, I can view historical voltage/current/power/energy/temperature trends over a selected time range.
  - Empty ranges show an informative empty state; query failures show a retryable error.
- As an operator, I can distinguish an electrical abnormality from a sensor/communication failure.
  - A missing or invalid PZEM response is not automatically classified as phase loss.
- As an operator, I can review fault details and lifecycle status.
  - Fault entries include timestamp, category/type, severity, affected phase where known, values and status.
- As a technician, I can document attempts and diagnosis and update a work order through permitted transitions.
  - Invalid transitions are rejected by the server.
- As an administrator, I can manage devices and their locations.
  - Device identifiers are unique; references to nonexistent locations are rejected.
- As a device, I can submit telemetry without gaining access to user-facing administrative APIs.
  - Device credentials are separate from human-user credentials and secrets are never returned in telemetry responses.
- As an authorized operator, I can request relay state changes only if relay control is approved and implemented end-to-end.
  - A database state change alone must not be presented as proof that a physical relay changed.

## 7. Functional requirements

### FR-1 Authentication and access
- Authentication is mandatory for all telemetry, metrics, history, faults, work orders, relays, locations, and audit APIs. The login endpoint (`/login`) is the only public page.
- Operational roles: `operator`, `shift_incharge`, `electrical_engineer`, `management`, `technician`, `admin`.
- Centralized permission policy: explicit granular permissions (`view_live_metrics`, `view_history`, `view_faults`, `acknowledge_faults`, `rectify_faults`, `create_work_orders`, `view_work_orders`, `update_work_orders`, `switch_relays`, `view_campus`, `view_audit_logs`, `manage_users`, `manage_devices`, `view_management_summary`).
- Location-scoping: user accounts can be scoped to specific blocks (`assigned_block_id`) or floors (`assigned_floor_id`), enforced server-side.
- Technicians are isolated strictly to their own assigned work orders.
- Self-registration is restricted to the base `operator` role only. User promotion is restricted to administrators.
- Fail closed if a user role is missing or unverified. Zero data leakage in unauthenticated states.

### FR-2 Device and location management
- Maintain college/block/floor/device relationships.
- Store unique device identifier, name, active status, firmware version, location and last-seen timestamp.
- A device may be unassigned from a floor only if allowed by policy.

### FR-3 Telemetry ingestion and validation
- Accept phase-specific readings and metadata: device ID, phase, sampled timestamp, received timestamp, transmission reason, source, data quality and sampling interval where available.
- Validate phase values (`R`, `Y`, `B`), finite numeric values, allowed ranges, timestamp timezone, required fields and device identity.
- Reject or quarantine invalid samples rather than interpreting them as genuine electrical conditions.
- Track backend receipt time independently from device sample time.
- Update device health/last-seen only from valid authenticated contact.

### FR-4 Monitoring
- Show latest readings by phase, total power and energy where aggregation is valid, temperature, device health and system status.
- Show historical charts and fault/event history.
- Make stale data visibly different from a live normal state.

### FR-5 Rule-based fault identification
- Support configurable rules for under/over-voltage, overcurrent, phase imbalance, sudden parameter changes, high temperature and loss of voltage/power only when supported by reliable evidence.
- Keep electrical findings separate from sensor/communication faults.
- Avoid duplicate open faults for repeated samples of the same ongoing condition.
- Thresholds must be configurable and approved for the actual installation; documented example values are not commissioning settings.
- Rule outcomes must include category, type, severity, phase if known, measured/expected values, unit, timestamp and description.

### FR-6 Fault and notification lifecycle
- Create fault/event records and notifications for new findings.
- Support viewing, acknowledging and rectifying faults with actor and timestamp.
- Prevent unauthorized state changes and invalid lifecycle transitions.

### FR-7 Maintenance
- Support work-order assignment, chronological attempts, diagnosis, restoration and closure.
- Preserve the event/work timeline.
- Closure should rectify the associated fault only after required workflow checks pass.

### FR-8 Relay control (conditional)
- The current code has relay records and on/off endpoints, but a persisted boolean is not physical-device confirmation.
- Before enabling in the MVP, implement authenticated authorization, durable command IDs, device polling/acknowledgement, timeout/failure status, audit entries, safe default behavior and an installation-level safety review.
- Until approved, expose relay management as disabled or clearly labelled simulated/uncommissioned control.

### FR-9 Audit and health
- Record security-sensitive and administrative actions without storing passwords, tokens or other secrets.
- Expose a health endpoint for application/database readiness and report device health separately.

## 8. Screens/pages

1. Login.
2. Main dashboard: system status, R/Y/B phase cards, total power/energy, temperature, recent faults.
3. Location explorer: college → block → floor → device.
4. Device detail: current values, history, device metadata and health.
5. Fault list and fault detail.
6. Maintenance work-order list/detail, attempts and timeline.
7. Notifications.
8. Device/relay administration (relay commands gated as above).
9. User administration (admin only; account provisioning approach approval required).
10. Audit log (admin/authorized management).
11. Configuration/settings for thresholds only if safely editable and audited.

## 9. Non-functional requirements

- **Safety:** never present this system as certified electrical protection. No switching feature may bypass rated protective devices or physical safety review.
- **Security:** password hashing, short-lived/expiring signed access tokens, server-side role checks, device authentication, least privilege, secret-safe logs, input validation and production HTTPS.
- **Reliability:** failures of a sensor, network or database must be visible and must not silently become a normal status.
- **Data integrity:** UTC-aware timestamps, independent sampled/received times, validated values, durable fault/maintenance history and migrations.
- **Performance:** dashboard reads should use indexed queries and bounded history windows; API requests should return useful errors instead of hanging.
- **Maintainability:** modular FastAPI backend, React/TypeScript frontend, migrations and documented rules.
- **Accessibility:** keyboard operation, clear labels/units, contrast, and status indicators not relying on color alone.
- **Responsive design:** desktop/laptop first for engineering monitoring; tablet/mobile must remain usable for status and fault review.
- **Budget:** reuse owned hardware and existing dependencies; justify purchases and new services.

## 10. Loading, empty and error states

- **Loading:** skeleton/placeholder with the section title; avoid fabricated zero readings.
- **No telemetry yet:** “No measurements received yet” plus device/setup status.
- **No history in range:** explain that no records match the selected period.
- **Offline/stale:** show last successful timestamp and a distinct offline/stale label.
- **Sensor/communication failure:** identify the affected meter/phase communication path; do not claim the electrical phase is absent without corroboration.
- **No faults:** explicit “No active faults” with last evaluation/update time.
- **API/database failure:** preserve the last known data only if labelled stale; provide retry action and correlation/request ID where available.
- **Unauthorized/forbidden:** redirect to login or show permission explanation; do not reveal protected resource details.
- **Relay command pending/failed:** show pending, confirmed, timed out or failed separately; never imply physical state is confirmed without acknowledgement.

## 11. Data requirements

Primary entities: users, colleges, blocks, floors, devices, telemetry, faults, notifications, relays, work orders, audit events. Preserve source (`REAL`, `SIMULATION`, `TEST`), data quality and transmission reason. ML prediction/configuration tables are future scope until the ML interface is approved.

## 12. Integrations

- XIAO ESP32-S3 firmware via authenticated HTTP REST API.
- PostgreSQL via SQLAlchemy and Alembic.
- Browser dashboard via the internal FastAPI API.
- DS3231 RTC and DS18B20 are firmware-level inputs.
- MATLAB simulation API and ML services are future integrations; do not treat them as operational until implemented and tested.
- No cloud provider or external notification provider is assumed to be selected.

## 13. MVP scope

**Included:** login/role enforcement; location and device records; authenticated telemetry ingestion; validated time-series storage; latest dashboard and history; device health; rule-based findings; fault list/detail and lifecycle; basic notifications; maintenance work orders; audit trail; tests and deployment configuration.

**Conditional:** relay control remains disabled/uncommissioned until end-to-end device acknowledgement and safety requirements are met.

**Out of scope:** validated ML/predictive maintenance, automatic electrical protection, multi-tenant SaaS, advanced forecasting, public signup, paid cloud services not approved, MATLAB simulation, model registry, dataset management/export/backup automation beyond basic operational backups.

## 14. Success criteria

- Three phases can be ingested and displayed with correct phase association and timestamps.
- Invalid/malformed data is rejected or marked invalid and does not create misleading electrical faults.
- Latest measurements and bounded historical trends are visible.
- Rule tests cover each configured fault and communication failure distinction.
- Duplicate samples do not create unbounded duplicate open faults.
- Role/permission tests prove unauthorized users cannot administer devices, users, maintenance or relay commands.
- Maintenance state transitions are validated and auditable.
- Database migrations apply cleanly to an empty test database.
- No production launch until electrical installation, device authentication, authorization, backups and relay safety gates are verified.

## 15. Assumptions and decisions requiring owner approval

1. **Roles:** current code uses `admin`, `operator`, `technician`; confirm whether the earlier proposed `developer`, `moderator`, `maintenance`, and `management` roles are needed.
2. **Pilot hierarchy:** assume one college/site and its block/floor hierarchy for MVP.
3. **Thresholds:** installation-specific values must be approved by a qualified person; defaults are not safety settings.
4. **Relay operation:** approve whether relay control belongs in MVP; recommendation is to keep it disabled until end-to-end acknowledgement and safety review.
5. **Telemetry auth:** choose per-device secret/API key or signed device credentials; human JWTs must not be reused for firmware.
6. **Account provisioning:** choose admin-created users versus a protected first-admin bootstrap.
7. **Retention/backups:** approve history retention and backup schedule based on storage and institutional policy.
8. **Time authority:** use device RTC for sampled time and backend UTC receipt time; define handling for clock drift.
9. **Hosting:** deployment target/domain and whether data must remain on a local network are not confirmed.

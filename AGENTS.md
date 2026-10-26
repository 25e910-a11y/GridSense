# AGENTS.md — Coding Agent Rules

These rules apply to every coding agent and contributor working in this repository.

## 1. Source of truth and first steps

1. Read `PRD.md`, `DESIGN.md`, `ARCHITECTURE.md`, `DATABASE.md`, `API.md`, and this file before implementing features.
2. Also inspect `README.md`, `docs/RULES.md`, `docs/TASKS.md`, `docs/data_dictionary.md`, relevant source files, migrations and tests.
3. Inspect the current Git status and diff before changing files. Never overwrite user work or discard uncommitted changes.
4. Verify what exists in code; documentation checkboxes and README claims are not proof of functionality.
5. If requirements conflict, stop and identify the conflict. Do not silently reconcile roles, endpoints, thresholds, hardware or product scope.

## 2. Keep changes focused

- Implement only the approved task.
- Reuse existing modules, schemas, components, service patterns and dependencies.
- Avoid unrelated refactors, broad rewrites, renaming and formatting churn.
- Do not introduce a dependency when the standard library or existing stack is sufficient.
- Do not implement future ML, MATLAB, external notifications or physical relay control unless specifically approved.

## 3. Code quality and naming

- Use clear, descriptive names and consistent project conventions.
- Python: follow existing style, type hints and Pydantic/SQLAlchemy patterns.
- TypeScript: preserve strict type checking; avoid `any` unless justified and contained.
- Keep domain logic in testable services, not duplicated across routes/UI.
- Avoid magic numbers; thresholds belong in validated configuration with documented units.
- Do not swallow exceptions or use broad catch blocks without logging and a clear recovery policy.

## 4. Structure and reuse

- Follow the existing `backend/app/api`, `models`, `schemas`, `services`, `rules`, `core` and `db` structure.
- Follow the actual frontend structure and use shared components/API services.
- Do not create parallel implementations of auth, database sessions, API clients, fault rules or design tokens.
- Add a new abstraction only when it removes meaningful duplication or establishes a real boundary.

## 5. Dependencies and configuration

- Check whether a dependency already exists before adding it.
- Pin or constrain versions consistently with the existing project strategy.
- Update lockfiles/manifests and document why a dependency is needed.
- Keep secrets in environment variables or an approved secret manager.
- Never hardcode credentials, JWT secrets, API keys, device ingest keys or production URLs containing secrets.
- Keep `.env` and local credentials out of Git; `.env.example` uses safe placeholders only.
- Fail safely when required production configuration is missing.

## 6. Security and permissions

- Treat all client input and frontend role state as untrusted.
- Enforce authentication, role permissions, resource ownership and state transitions server-side.
- Do not allow public users to choose privileged roles during registration.
- Keep device credentials separate from human-user credentials.
- Never return password hashes, ingest keys or internal secrets.
- Use parameterized ORM/database access; do not build SQL from untrusted strings.
- Avoid rendering untrusted HTML; validate and escape user-generated text appropriately.
- Do not log passwords, tokens, authorization headers or secrets.
- Every sensitive administrative, maintenance and relay action must be auditable.
- Relay APIs are security-sensitive and must remain disabled/unexposed until end-to-end device acknowledgement and electrical safety review are complete.

## 7. Electrical and project-specific rules

- The project monitors a 3-phase, 4-wire system using XIAO ESP32-S3 and three PZEM-004T V4 modules.
- MQ-135 has been removed; never reintroduce it.
- Do not invent pin assignments, electrical ratings, PZEM logic levels, thresholds or protection ratings.
- A PZEM communication failure is not proof of phase loss.
- Distinguish sensor/communication errors from electrical abnormalities.
- SSRs are not replacements for fuses, MCBs, MCCBs, overload protection, rated contactors, isolation or earthing.
- Never claim certified electrical protection or automatic isolation unless engineered, validated and approved.
- Never make AI/ML or predictive-maintenance claims unless an actual model is trained/evaluated and documented.
- All mains-related advice and testing must prioritize qualified review, isolation, enclosure, creepage/clearance, fusing and safe test procedures.

## 8. Database and API discipline

- Use Alembic migrations for schema changes.
- Inspect existing migrations, schema and data before altering constraints or columns.
- Never drop/replace data to make a migration pass.
- Use transactions where a workflow spans telemetry/fault records or maintenance/fault state.
- Use UTC-aware timestamps and keep device sample time separate from server receipt time.
- Keep API request/response schemas explicit and update relevant frontend types.
- Maintain backwards compatibility unless an approved contract change includes coordinated frontend updates.

## 9. Error handling

- Validate at API boundaries and domain invariants in services.
- Use consistent status codes and useful messages.
- Do not expose stack traces, SQL statements or secrets to clients.
- Do not turn failures into successful empty responses.
- Distinguish missing data, stale data, invalid samples, device offline, communication failure and actual electrical faults.
- Relay command acceptance must not be presented as confirmed physical state.

## 10. Testing

- Add/update tests for every changed behavior.
- Test happy paths, invalid input, permission failures, missing resources, state transitions and dependency failures as relevant.
- Test fault rules for both true anomalies and communication/data-quality failures.
- Use test databases and deterministic fixtures; never use production data or live mains in automated tests.
- Run targeted tests first, then the broader suite when practical.
- Run frontend build/typecheck/lint for frontend changes.
- Report exactly which commands ran and their results. Do not claim tests passed if they were not executed.

## 11. Documentation

- Update API/database/design documentation when behavior or contracts change.
- Label assumptions and unimplemented/future features.
- Keep examples consistent with actual schemas and routes.
- Do not claim deployment, backup, physical relay operation, MATLAB integration or ML is complete without verification.

## 12. Git and change discipline

- Review `git status` and diffs before and after work.
- Never force-push, reset, clean, or delete user files unless explicitly authorized.
- Keep commits focused when asked to commit.
- Do not include `.env`, generated secrets, local databases, node_modules, virtual environments, compiled caches or build outputs in commits.
- Report changed files, tests, known risks and manual steps.

## 13. Completion checklist

A task is complete only when:
- The requested behavior is implemented and fits the approved documents.
- Relevant validation, authorization and error states are covered.
- Tests have been run and results reported honestly.
- Database migrations/docs/types are updated if needed.
- No unrelated changes or secrets are included.
- Any unresolved ambiguity or safety gate is clearly identified.

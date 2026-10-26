# GridSense

IoT-based 3-phase power monitoring and fault identification system.

For the **IoT-Based Power Monitoring & Fault Identification System**.

## Files
- `PRD.md` — product requirements and MVP scope.
- `DESIGN.md` — visual/UX design system.
- `ARCHITECTURE.md` — implementation architecture and stack.
- `DATABASE.md` — database model and migration guidance.
- `API.md` — API contract and security requirements.
- `AGENTS.md` — persistent rules for coding agents.
- `IMPLEMENTATION_PLAN.md` — phased development plan and recommended first task.
- `PROJECT_AUDIT_REPORT.md` — static review of the uploaded repository and priority risks.

## Recommended use
1. Review `PROJECT_AUDIT_REPORT.md` and approve the decisions listed in it.
2. Review `PRD.md`, especially roles, relay control, thresholds and hosting assumptions.
3. Treat the approved PRD as product scope, then approve the design, architecture, database and API contracts.
4. Put the six source-of-truth documents and `AGENTS.md` at the repository root (or update your coding agent's instructions to point to their chosen location).
5. Start with Phase 0 of `IMPLEMENTATION_PLAN.md`: read-only baseline and actual test/build execution.

## Important
These documents were generated from the uploaded repository snapshot and project notes. The audit is static; no tests, build, database connection, deployment or hardware test was run. Some choices are explicitly marked for approval. Do not treat documentation as proof that a feature is implemented or electrically safe.

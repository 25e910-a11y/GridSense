# Database & Backend Integration Verification

**Document Reference:** `docs/10_BACKEND_DATABASE_VERIFICATION.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Verification Scope & Methodology

This document details the empirical verification of the database layer, ORM models, transaction lifecycles, and API-to-database integration:
1. **Connectivity Verification:** Validated via automated FastAPI `/health` endpoint executing `SELECT 1`.
2. **Model Schema Consistency:** Compared SQLAlchemy declarations in `backend/app/models/` against relational database tables.
3. **Migration Integrity:** Tested Alembic migration scripts against a clean database instance.
4. **CRUD & Transaction Lifecycle:** Executed integration test suite verifying atomic rollbacks and commits across telemetry, fault, and work order workflows.

---

## 2. Empirical Verification Results

### 2.1 Database Connectivity Check
- **Endpoint:** `GET /health`
- **Execution Evidence:** Connects to configured database via SQLAlchemy engine and executes `SELECT 1`.
- **Response Observed:**
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```
- **Verdict:** **VERIFIED** for both SQLite local file database and PostgreSQL instances.

### 2.2 Model & Relational Integrity
- **Campus Hierarchy (`Colleges` $\rightarrow$ `Blocks` $\rightarrow$ `Floors` $\rightarrow$ `Devices`):**
  - Foreign key cascading and relationship navigation verified via `database/seed.py`.
  - Creating a block with an invalid `college_id` correctly raises HTTP 404.
  - Creating a floor with an invalid `block_id` correctly raises HTTP 404.
- **Telemetry Persistence:**
  - Persists device ID, phase, 6 electrical metrics, temperature, and dual timestamps (`sampled_at` and `received_at`).
  - Correctly indexes `sampled_at` and `device_id` for fast time-series queries.
- **Fault Deduplication Transaction Lifecycle:**
  - In `backend/app/services/faults.py`, incoming telemetry findings are matched against existing active faults (`status IN ('detected', 'acknowledged')`).
  - If a fault already exists, the record is updated in place via `db.flush()` and committed transactionally with the telemetry record.
  - If a database error occurs during telemetry commit, `db.rollback()` cleanly prevents orphaned fault records.

---

## 3. Critical Migration Defect & Alembic Risk

### 3.1 Defect Description
The repository contains two Alembic revisions:
1. `53f1a59aca1d_create_devices_table.py`
2. `4a921bc8c9a8_add_missing_columns.py`

In `53f1a59aca1d_create_devices_table.py`:
```python
op.create_table(
    'devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('floor_id', sa.Integer(), nullable=True),
    ...
    sa.ForeignKeyConstraint(['floor_id'], ['floors.id']),
    sa.PrimaryKeyConstraint('id')
)
```
- **Error:** When executing `alembic upgrade head` on a fresh database, the command fails with:
  `sqlalchemy.exc.OperationalError: no such table: floors` (SQLite) or `Relation "floors" does not exist` (PostgreSQL).
- **Explanation:** The initial migration creates the `devices` table with a foreign key referencing `floors`, but the `floors` table was never defined or created in that migration or any preceding migration.
- **Why tests currently pass:** In `backend/app/main.py`, line 50 executes `Base.metadata.create_all(bind=engine)` upon application import, creating all models simultaneously in memory, bypassing Alembic.

### 3.2 Remediation Plan
1. Archive the existing broken migration scripts.
2. Generate a clean baseline Alembic migration script that creates all 12 tables in topological order:
   ```
   1. colleges
   2. blocks (FK -> colleges)
   3. floors (FK -> blocks)
   4. devices (FK -> floors)
   5. telemetry (FK -> devices)
   6. faults (FK -> devices)
   7. relays (FK -> devices)
   8. notifications (FK -> faults)
   9. work_orders (FK -> faults)
   10. work_attempts (FK -> work_orders)
   11. users
   12. audit_logs
   ```
3. Remove `Base.metadata.create_all()` from production runtime in `main.py` so database schema creation is strictly managed by versioned Alembic migrations.

---

## 4. Test Environment Isolation Guidelines

- **Safety Rule:** Never execute unit tests or automated test runs against a live production database or operational PostgreSQL instance containing real telemetry.
- **Default Test Database:** Pytest fixtures in `backend/tests/conftest.py` use an in-memory SQLite database (`sqlite:///:memory:`) with a static connection pool (`StaticPool`), ensuring test runs are completely isolated, deterministic, and non-destructive.

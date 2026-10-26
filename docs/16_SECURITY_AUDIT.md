# Comprehensive Security Audit Report

**Document Reference:** `docs/16_SECURITY_AUDIT.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)
**Classification:** Defensive Assessment & Remediation Guide

---

## 1. Executive Summary & Threat Profile

The IoT Power Monitoring System interfaces low-voltage digital microcontrollers with three-phase 4-wire $230\text{ V} / 400\text{ V}$ AC electrical distribution panels. In this operational domain, software vulnerabilities carry **direct physical risks**:
- **Electrical Safety & Disruption:** Unauthorized actuation of solid-state relays can abruptly drop critical laboratory loads or energize unmonitored feeders.
- **Data Tampering & Spoofing:** Forged telemetry injection can conceal real electrical overcurrent or trigger false facility evacuations.
- **Administrative Compromise:** Privilege escalation enables rogue modification of safety thresholds or complete audit log tampering.

---

## 2. Vulnerability Findings & Risk Matrix

| Finding ID | Severity | OWASP Top 10 Category | Vulnerability Title | Likelihood | Impact |
|---|---|---|---|:---:|:---:|
| **V-01** | **CRITICAL** | A01:2021-Broken Access Control | Unauthenticated High-Voltage Relay Actuation | High | Critical |
| **V-02** | **HIGH** | A01:2021-Broken Access Control | Privilege Escalation via Open Self-Registration | High | High |
| **V-03** | **HIGH** | A07:2021-Identification & Auth Failures | Unauthenticated Telemetry Ingestion (Spoofing/DoS) | High | High |
| **V-04** | **MEDIUM** | A01:2021-Broken Access Control | Unauthenticated Fault & Maintenance Tampering | Medium | Medium |
| **V-05** | **MEDIUM** | A05:2021-Security Misconfiguration | Insecure CORS Origin Wildcard with Credentials | High | Medium |
| **V-06** | **MEDIUM** | A02:2021-Cryptographic Failures | Default JWT Secret & Committed Database Password | High | Medium |
| **V-07** | **LOW** | A04:2021-Insecure Design | Missing Rate Limiting on Login & Ingestion Endpoints | High | Low |

---

## 3. Detailed Vulnerability Analyses

### 3.1 Vulnerability V-01 (CRITICAL): Unauthenticated Relay / SSR Actuation
- **Affected Route:** `POST /relays/{relay_id}/on` and `POST /relays/{relay_id}/off` in `backend/app/api/relays.py`.
- **Mechanics:** The endpoint definitions do not declare any FastAPI dependency on `get_current_user` or check caller permissions. Any HTTP client on the network can transmit `curl -X POST http://<server-ip>:8000/relays/1/off` to trip an electrical contactor.
- **Physical Impact:** Threatens personnel safety during panel maintenance; causes unexpected outages for sensitive laboratory equipment.
- **Remediation:**
  ```python
  def require_admin(user: User = Depends(get_current_user)) -> User:
      if user.role != "admin":
          raise HTTPException(status_code=403, detail="Admin role required for relay actuation")
      return user

  @router.post("/{relay_id}/on")
  def turn_relay_on(relay_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
      ...
  ```

---

### 3.2 Vulnerability V-02 (HIGH): Privilege Escalation via Self-Registration
- **Affected Route:** `POST /auth/register` in `backend/app/api/auth.py`.
- **Mechanics:** The Pydantic request model accepts a `role` field from the client. The registration function directly maps this input:
  `role = payload.role if payload.role in {"admin", "operator", "technician"} else "operator"`
  An unauthenticated attacker can supply `role: "admin"` in the JSON payload and instantly create a superuser account.
- **Remediation:** Remove public role selection. Either:
  1. Restrict `/auth/register` so only authenticated administrators can create accounts (`user: User = Depends(require_admin)`).
  2. Or hardcode all public registrations to the default role `operator`, ignoring any client-supplied role parameters.

---

### 3.3 Vulnerability V-03 (HIGH): Unauthenticated Telemetry Ingestion
- **Affected Route:** `POST /telemetry/` in `backend/app/api/telemetry.py`.
- **Mechanics:** In `telemetry.py`, `create_telemetry` does not enforce the `require_ingest` dependency. Any network host can inject fabricated voltage and current data, spoof false phase loss events, or spam telemetry records to consume database disk space.
- **Remediation:**
  1. Fix the bug in `require_ingest` in `security.py` so it validates `X-Ingest-Key` without crashing on missing Bearer tokens.
  2. Add `Depends(require_ingest)` to `POST /telemetry/`.

---

### 3.4 Vulnerability V-04 (MEDIUM): Unauthenticated Fault & Maintenance Tampering
- **Affected Routes:**
  - `POST /faults/`
  - `PUT /faults/{id}/acknowledge`
  - `PUT /faults/{id}/rectify`
  - `POST /maintenance/work-orders`
  - `POST /maintenance/work-orders/{id}/attempts`
  - `PUT /maintenance/work-orders/{id}/status`
- **Mechanics:** All fault and maintenance endpoints lack authentication checks. Any user can falsify maintenance records, acknowledge faults under fake names, or arbitrarily mark work orders as closed.
- **Remediation:** Enforce `Depends(get_current_user)` on all mutating maintenance and fault endpoints, assigning `acknowledged_by` and `created_by` directly from `user.username`.

---

### 3.5 Vulnerability V-05 (MEDIUM): Insecure CORS Middleware Misconfiguration
- **Affected File:** `backend/app/main.py:L41-L47`.
- **Mechanics:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  Combining `allow_origins=["*"]` with `allow_credentials=True` violates W3C CORS specifications. Modern browsers reject credentialed requests under this configuration. Furthermore, if a browser accepted it, any malicious website visited by an authenticated operator could issue authenticated cross-origin requests to the internal monitoring system.
- **Remediation:** Enforce explicit allowed origins from environment settings:
  ```python
  allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]
  ```

---

### 3.6 Vulnerability V-06 (MEDIUM): Default Signing Secret & Plaintext DB Credentials
- **Affected Files:** `backend/app/core/config.py:L8` and `backend/.env`.
- **Mechanics:**
  - `JWT_SECRET: str = "dev-change-me"` allows attackers to forge valid administrative JWTs if left unconfigured.
  - `backend/.env` currently contains the full local PostgreSQL connection string with password (`Subu%402011`).
- **Remediation:**
  - In production, validate that `JWT_SECRET` is not equal to `"dev-change-me"`.
  - Ensure `.env` is excluded via `.gitignore` (verified: `.gitignore` contains `.env`).
  - Advise user to rotate their local PostgreSQL database password.

---

## 4. Input Validation & Injection Resistance

- **SQL Injection:** **IMMUNE.** The application strictly utilizes SQLAlchemy 2.0 ORM query structures and parameterized queries (`db.query()`, `filter()`). No raw SQL string formatting was discovered.
- **Stored XSS:** **LOW RISK.** React escapes all interpolated variables in JSX by default. No instances of `dangerouslySetInnerHTML` were found in `frontend/src/`.
- **Mass Assignment:** **LOW RISK.** Pydantic schemas explicitly whitelist allowed input attributes for telemetry and work orders.

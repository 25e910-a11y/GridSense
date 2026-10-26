# Authentication & Authorization Verification

**Document Reference:** `docs/11_AUTH_SECURITY_VERIFICATION.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Authentication Architecture Audit

### 1.1 Password Security & Storage
- **Algorithm:** PBKDF2 with HMAC-SHA256.
- **Salt Generation:** `secrets.token_hex(16)` (cryptographically secure 16-byte random salt).
- **Work Factor:** 120,000 iterations.
- **Comparison Function:** `secrets.compare_digest` (constant-time comparison preventing timing attacks).
- **Verdict:** **EXCELLENT / CRYPTOGRAPHICALLY SOUND.** Conforms to modern OWASP authentication standards.

### 1.2 JWT Token Lifecycle
- **Algorithm:** HMAC-SHA256 (`HS256`).
- **Secret Key:** Driven by `settings.JWT_SECRET` (default `"dev-change-me"` in `config.py`).
- **Token Claims:** Subject (`sub`: username), Role (`role`), Expiration (`exp`).
- **Default Lifetime:** 1,440 minutes (24 hours).
- **Verdict:** Mechanism is standard and functional; however, the default secret key must be changed to a cryptographically strong random string in production.

---

## 2. Vulnerability Findings & Authorization Deficiencies

### Finding 1: Unauthenticated Privilege Escalation via Self-Registration (Vulnerability V-02)
- **Location:** `backend/app/api/auth.py:L31-L49`
- **Current Code:**
  ```python
  @router.post("/register")
  def register(payload: RegisterRequest, db: Session = Depends(get_db)):
      ...
      role = payload.role if payload.role in {"admin", "operator", "technician"} else "operator"
      user = User(
          username=payload.username,
          password_hash=hash_password(payload.password),
          role=role,
          ...
      )
  ```
- **Vulnerability Impact:** Any anonymous visitor on the network can send `POST /auth/register` with `{"username": "attacker", "password": "secret", "role": "admin"}` and immediately obtain full administrative privileges.
- **Required Fix:** Restrict `/auth/register` so that only existing users with the `admin` role can provision accounts, OR remove the `role` field from public registration and default all self-registered accounts to `operator`.

---

### Finding 2: Missing Route Authorization on Critical Operations
An audit of all FastAPI route definitions reveals that with the exception of `/auth/me`, **zero endpoints enforce caller authentication or role restrictions**:

| Endpoint | Sensitive Operation | Current Security State | Required Role |
|---|---|---|---|
| `POST /relays/{id}/on` | Switches high-voltage physical contactor ON | **Completely Unauthenticated** | `admin` |
| `POST /relays/{id}/off` | Switches high-voltage physical contactor OFF | **Completely Unauthenticated** | `admin` |
| `POST /telemetry/` | Ingests sensor data & triggers fault alarms | **Completely Unauthenticated** | Valid `X-Ingest-Key` |
| `POST /faults/` | Injects manual electrical fault records | **Completely Unauthenticated** | `admin`, `operator` |
| `PUT /faults/{id}/acknowledge` | Acknowledges fault with arbitrary name | **Completely Unauthenticated** | `operator`, `technician` |
| `PUT /faults/{id}/rectify` | Closes active fault | **Completely Unauthenticated** | `operator`, `technician` |
| `POST /maintenance/work-orders` | Dispatches work order tickets | **Completely Unauthenticated** | `operator`, `admin` |
| `PUT /maintenance/work-orders/{id}/status` | Updates work order lifecycle | **Completely Unauthenticated** | `technician`, `admin` |
| `POST /devices/` | Provisions new monitoring hardware | **Completely Unauthenticated** | `admin` |
| `POST /locations/*` | Creates colleges, blocks, floors | **Completely Unauthenticated** | `admin` |

---

## 3. Proposed Role-Based Access Control (RBAC) Matrix

To achieve enterprise-grade security and maintain electrical safety, the following role/permission matrix is proposed:

| System Operation | Anonymous | Technician | Operator | Administrator |
|---|:---:|:---:|:---:|:---:|
| **View Live Dashboard (`/dashboard/live`)** | Yes* | Yes | Yes | Yes |
| **View Historical Telemetry (`/telemetry`)** | Yes* | Yes | Yes | Yes |
| **Ingest Telemetry (`POST /telemetry/`)** | Hardware Key | Hardware Key | Hardware Key | Hardware Key |
| **Acknowledge Active Fault** | No | Yes | Yes | Yes |
| **Dispatch Work Order Ticket** | No | No | Yes | Yes |
| **Log Work Attempt Note** | No | Yes | Yes | Yes |
| **Close Work Order Ticket** | No | Yes (Assigned) | Yes | Yes |
| **Toggle Relays / Actuators (`/relays/*`)**| **NO** | **NO** | **NO** | **YES (Admin Only)** |
| **Provision Devices & Locations** | No | No | No | Yes |
| **View Immutable Audit Logs (`/audit`)** | No | No | No | Yes |
| **User Provisioning & Role Assignment** | No | No | No | Yes |

*\*Note: Public viewing of live telemetry can be restricted behind login in high-security production environments.*

---

## 4. Decision Required from Project Owner

> [!IMPORTANT]
> **Owner Approval Required:**
> Please review and approve the proposed 3-role matrix (`admin`, `operator`, `technician`). Once approved, we will apply these dependencies across all endpoints and update the frontend navigation without breaking existing technician and operator workflows.

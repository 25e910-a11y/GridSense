# Deployment Plan & Release Strategy

**Document Reference:** `docs/18_DEPLOYMENT_PLAN.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Deployment Topology & Environments

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOCAL DEVELOPMENT ENVIRONMENT                            │
│ - Host: Developer Workstation (Windows 11)                   │
│ - Database: Local SQLite file (`power_monitoring.db`)        │
│ - Backend: Uvicorn dev server (`--reload` on port 8000)      │
│ - Frontend: Vite dev server (`http://localhost:5173`)        │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTROLLED STAGING / TESTBENCH ENVIRONMENT                │
│ - Host: Dedicated Lab Workstation / Mini PC (Ubuntu 22.04)   │
│ - Database: Local PostgreSQL 15 on port 5432                 │
│ - Networking: Isolated private switchgear test bench LAN    │
│ - Hardware: Xiao ESP32-S3 + PZEM modules on 24V AC bench rig │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. INSTITUTIONAL PRODUCTION ENVIRONMENT                     │
│ - Host: Campus Data Center Linux Server / Containerized      │
│ - Reverse Proxy: Nginx (TLS 1.3, Rate Limiting, Static SPA) │
│ - Application: Gunicorn + Uvicorn Workers (Systemd service)  │
│ - Database: Dedicated PostgreSQL Cluster with daily backup   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Server System Requirements (Institutional Pilot)

- **CPU:** 4 Cores (x86_64 or ARM64).
- **RAM:** 8 GB minimum (16 GB recommended for telemetry buffering).
- **Disk:** 100 GB SSD (NVMe preferred for fast time-series write throughput).
- **Operating System:** Ubuntu 22.04 / 24.04 LTS Server.
- **Python:** Python 3.11 or 3.12.
- **Node.js:** Node.js v20 LTS.
- **Database:** PostgreSQL 15 or 16.

---

## 3. Production Configuration & Hardening

### 3.1 Reverse Proxy (Nginx) Architecture
Nginx serves the pre-compiled React single-page application (`dist/`) directly and reverse-proxies API calls to the local Uvicorn process on `127.0.0.1:8000`:
- Enforces HTTPS with TLS 1.3 certificates (Let's Encrypt or institutional CA).
- Drops HTTP connections and redirects to HTTPS port 443.
- Rate-limits authentication endpoints (`POST /auth/login`) to 5 requests per second per IP to prevent brute-force attacks.
- Enforces strict security headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`.

### 3.2 Secret Management Guidelines
- In production, **never** commit `.env` or secrets to version control.
- Generate high-entropy random keys for production:
  ```bash
  # Generate cryptographically secure JWT Secret:
  openssl rand -hex 32

  # Generate random Device Ingest Key:
  openssl rand -hex 24
  ```
- Store secrets using environment files with `chmod 600` permissions accessible only by the service account.

---

## 4. Production Deployment Procedure (Step-by-Step)

```bash
# 1. Update source code
git pull origin main

# 2. Build production frontend assets
cd frontend
npm ci
npm run build
# (Assets output to dist/)

# 3. Upgrade Python dependencies
cd ../backend
source .venv/bin/activate
pip install -r requirements.txt

# 4. Apply database migrations
alembic upgrade head

# 5. Restart application service
sudo systemctl restart iot-backend.service
sudo systemctl reload nginx

# 6. Verify health probe
curl -f http://127.0.0.1:8000/health || exit 1
```

---

## 5. Rollback & Disaster Recovery Procedures

1. **Database Schema Rollback:**
   ```bash
   alembic downgrade -1
   ```
2. **Application Rollback:**
   Checkout previous known-good Git release tag, rebuild frontend, and restart service.
3. **Database Restore:**
   ```bash
   pg_restore -U postgres -d power_monitoring /var/backups/power_monitoring_latest.dump
   ```

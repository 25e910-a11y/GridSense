# Project Setup & Reproducibility Guide

**Document Reference:** `docs/08_SETUP_AND_REPRODUCIBILITY.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Prerequisites & Environment Requirements

| Component | Minimum Version | Verified Version on Host |
|---|---|---|
| **Operating System** | Windows 10/11, Ubuntu 22.04 LTS, macOS 13+ | Windows 11 (tested on host) |
| **Python** | Python 3.11+ | Python 3.13.15 |
| **Node.js & npm** | Node 18+, npm 9+ | Node.js v20+ / npm |
| **Database** | SQLite 3 (Dev/Test) or PostgreSQL 15+ | SQLite & PostgreSQL |
| **Git** | Git 2.35+ | Git installed |

---

## 2. Step-by-Step Backend Setup (Windows & Linux)

### Step 2.1: Clone and Navigate to Backend
```powershell
cd d:\IoT-Power-Monitoring-System\backend
```

### Step 2.2: Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If script execution is disabled on PowerShell, use: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or activate via CMD `.\.venv\Scripts\activate.bat`)*

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2.3: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2.4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Default `.env` configuration for local SQLite development:
```ini
DATABASE_URL=sqlite:///./power_monitoring.db
AUTH_ENABLED=true
JWT_SECRET=dev-change-me-generate-random-secret
JWT_EXPIRE_MINUTES=1440
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
INGEST_API_KEY=dev-esp32-ingest-key-12345
DEVICE_OFFLINE_SECONDS=120
NOMINAL_PHASE_VOLTAGE=230.0
UNDERVOLTAGE_RATIO=0.85
OVERVOLTAGE_RATIO=1.10
VOLTAGE_ABSENT_MAX=15.0
OVERCURRENT_AMPS=32.0
HIGH_TEMPERATURE_C=60.0
IMBALANCE_PERCENT=10.0
```

---

## 3. Database Initialization & Seeding

### Step 3.1: Seed Database with Realistic Telemetry & Hierarchy
From the project root:
```powershell
python database/seed.py
```
This script:
1. Provisions all database tables using SQLAlchemy models.
2. Seeds College (`Government Engineering College`), Blocks, and Floors.
3. Registers Devices:
   - `XIAO-PM-001` (Main Incomer Substation Panel)
   - `XIAO-PM-002` (ECE Power Systems Lab Feeder)
4. Configures 3-Phase Solid-State Relays on GPIO 7, 8, 9.
5. Injects balanced 3-phase nominal telemetry across Phases R, Y, and B.
6. Writes initial system audit logs.

---

## 4. Running the Backend Server

Start the Uvicorn development server:
```powershell
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```
- API Base: `http://127.0.0.1:8000`
- Swagger Interactive Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

---

## 5. Step-by-Step Frontend Setup

### Step 5.1: Navigate to Frontend Directory
```powershell
cd d:\IoT-Power-Monitoring-System\frontend
```

### Step 5.2: Install NPM Dependencies
*(On Windows, run via CMD if PowerShell blocks script execution)*:
```cmd
npm install
```

### Step 5.3: Run Frontend Development Server
```cmd
npm run dev
```
- Local URL: `http://localhost:5173`
- The Vite dev server automatically proxies `/telemetry`, `/dashboard`, `/faults`, `/maintenance`, `/relays`, `/auth`, `/devices`, `/locations`, and `/health` to the backend on `http://127.0.0.1:8000`.

### Step 5.4: Production Build Verification
To verify TypeScript compilation and production bundling:
```cmd
npm run build
```
*(Verified: compiles 2558 modules into `dist/` cleanly).*

---

## 6. Running Automated Tests

Run the complete test suite using the virtual environment pytest:
```powershell
cd d:\IoT-Power-Monitoring-System\backend
.\.venv\Scripts\pytest -v
```
*(Verified: 13 passed in < 1.2s covering rule engine, auth, maintenance, telemetry, and notifications).*

---

## 7. Execution Evidence: Tested vs. Untested Commands

| Command | Environment | Status / Result | Notes |
|---|---|---|---|
| `.\.venv\Scripts\pytest -v` | Windows 11 PowerShell | **TESTED: PASSED** | 13/13 tests pass in 1.13s |
| `cmd /c npm run build` | Windows 11 CMD | **TESTED: PASSED** | `tsc -b && vite build` built in 8.85s |
| `python database/seed.py` | Python 3.13 | **TESTED: PASSED** | Database created and populated |
| `alembic upgrade head` | Clean database | **TESTED: FAILED** | Known bug: missing `floors` table in migration `53f1a59aca1d` |
| Live ESP32 Wi-Fi Ingestion | Hardware Testbench | **UNTESTED** | Microcontroller firmware in `firmware/` not yet written |
| Live 40 A Relay Switching | Physical Hardware | **UNTESTED** | Restricted pending electrical safety review |

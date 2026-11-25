# GridSense

GridSense watches a 3-phase, 4-wire supply (415/230 V, 50 Hz) and tells maintenance staff which panel and which phase has a problem, before someone has to go looking for it.

Each panel gets a small node that reads voltage, current, power, energy, frequency and power factor on all three phases, plus the enclosure temperature. The node sends every reading to a backend. The backend checks the readings, logs an event with the panel, phase, value and time, raises a work order, and only closes it once the readings are back to normal.

This is our entry for the Vishwakarma Awards 2026-27 (Sustainable Energy theme). Stage 1 and Stage 2 are cleared. Stage 3 is the working prototype.

## What is built so far

| Part | State |
|---|---|
| Backend (FastAPI, rule engine, database) | Working. Backend tests pass. |
| Dashboard (React + TypeScript) | Working. Builds with no TypeScript errors. |
| Database seed with sample campus, panels and readings | Working |
| Built-in simulator | Working. Simulated readings are stored and shown as simulated. |
| Node firmware (XIAO ESP32-S3) | Not in this repo yet |
| Hand-drawn schematic scan | Not in this repo yet |
| KiCad schematic | Planned, will be added as the schematic is redrawn |
| SSR switching | In the design, kept off. The relay API is not wired to hardware. |

## Hardware

| Part | Used for |
|---|---|
| Seeed XIAO ESP32-S3 | Node controller, Wi-Fi |
| 3 x PZEM-004T V4 with CTs | One per phase. Modbus-RTU on one serial bus, addresses 01 to 03. Separate UARTs during bring-up. |
| DS18B20 on GPIO2 (D1) | Enclosure temperature |
| DS3231 on I2C, GPIO5/6 (D4/D5) | Keeps time when the network drops |
| Serial bus on D6/D7 (GPIO43/44) | ESP TX to PZEM RX, PZEM TX to ESP RX |
| 3 x SSR-40DA on GPIO7/8/9 | In the design, kept off until a safety review |
| Hi-Link HLK-5M05 + LiPo cell | 5 V supply with battery backup |

## Alarm rules (defaults)

All limits live in `backend/.env` and can be changed per device.

| Check | Default |
|---|---|
| Undervoltage | Below 195.5 V (15% under 230 V) |
| Overvoltage | Above 253 V (10% over 230 V) |
| Phase imbalance | Above 10% |
| Loss of voltage | 15 V or less, and only when another phase still has healthy voltage |
| Enclosure temperature | 65 °C, warning only |
| Device offline | No reading for 120 s |
| Clock skew allowed | 60 s |

A PZEM that stops answering, or sends a bad reading, is logged as a sensor fault. It is never treated as a lost phase.

Each device can also be put in log-only mode. Events are still logged, but nobody is alerted. This is meant for the first days on a new panel, while the limits are checked against a reference meter.

## How a fault moves

1. A reading goes outside its limits.
2. The backend checks that it is not just a sensor fault.
3. An event is logged with the panel, phase, value and time.
4. Maintenance is alerted and a work order is assigned.
5. The repair is logged and marked restored.
6. The work order closes only after a new reading from that phase is back to normal.

## How the node talks to the backend

The node sends each reading as JSON over HTTP POST to `/telemetry/`. Every device has its own key, sent in the `X-Ingest-Key` header. An admin creates the key with `POST /devices/{id}/ingest-key`. It is shown once and only a hash is stored. Sample time from the node is stored apart from the time the backend received it.

Campus layout in the database: campus, block, floor, panel, phase.

## Run it on your laptop

You need Python and Node.js. We last tested with Python 3.13 and Node.js 22.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # then fill in ADMIN_USERNAME, ADMIN_PASSWORD, INGEST_API_KEY
alembic upgrade head
cd .. && python database/seed.py && cd backend
uvicorn app.main:app --reload --port 8000
```

API docs open at http://127.0.0.1:8000/docs.

Dashboard:

```bash
cd frontend
npm install
npm run dev
```

The dashboard opens at http://localhost:5173.

Tests:

```bash
cd backend
ADMIN_USERNAME=sysadmin ADMIN_PASSWORD=testadminpassword123 pytest -q

cd ../frontend
npm run build
npm run lint
```

## Folders

| Folder | What is in it |
|---|---|
| `backend/app/rules` | The alarm rules |
| `backend/app/api` | API routes |
| `backend/app/services` | Fault logging, device settings, return-to-normal check |
| `backend/alembic` | Database migrations |
| `backend/tests` | Backend tests |
| `frontend/src` | Dashboard |
| `database/seed.py` | Sample data |
| `docs` | Design notes, API and database reference |

## Safety

This is a monitoring system, not a protection device. It does not replace fuses, MCBs, MCCBs, earthing or proper isolation. All mains work is done under qualified supervision, low voltage first, with no panel trial before a safety review. The SSRs stay off until that review is done.

## Team

The GridSense team, PSG College of Technology, Coimbatore. Vishwakarma Awards team ID VK26-IITH-SE-0093.

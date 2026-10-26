# Project Memory

## Identity
**Project:** IoT-Based Power Monitoring & Fault Identification System

## Core hardware
- XIAO ESP32-S3
- 3 × PZEM-004T V4
- 3 × CTs
- DS18B20
- DS3231
- Hi-Link 5V/5W PSU
- LiPo battery
- Relay module
- 3 × SSR-40DA
- Fuses/fuse holders
- Terminal blocks
- 2.5 mm² wire
- GX16/JST connectors
- Dot/perfboards
- Header/Berg strips
- DIP switch
- Heat sinks/thermal paste

## Removed component
- MQ-135 — removed from the project.

## Phase mapping
- PZEM-R → R
- PZEM-Y → Y
- PZEM-B → B

## Pin map
- D1/GPIO2 → DS18B20
- D4/GPIO5 → DS3231 SDA
- D5/GPIO6 → DS3231 SCL
- D6/GPIO43 → PZEM TX
- D7/GPIO44 → PZEM RX
- D8/GPIO7 → SSR-R
- D9/GPIO8 → SSR-Y
- D10/GPIO9 → SSR-B

## Core software concept
```text
Monitor
  ↓
Validate
  ↓
Analyse
  ↓
Identify
  ↓
Log
  ↓
Alert
```

## Backend/project structure
```text
frontend/
  app/
  components/
  services/
  hooks/
  types/

backend/
  app/
    api/
    models/
    schemas/
    services/
    rules/
    auth/
    ml/
  tests/

matlab/
  simulations/
  api/

database/
  migrations/
  seeds/

docs/
README.md
```

## Important state
Treat this file as project memory, not proof that every listed feature is already implemented.

Implemented status must be confirmed from the actual code/project state before describing a feature as complete.

## Long-term direction
The project may evolve from threshold/rule-based fault identification toward historical analytics and ML, but predictive/AI claims require an implemented and validated method.

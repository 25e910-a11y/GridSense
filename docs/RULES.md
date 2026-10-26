# Project Rules

## 1. Source of truth
Treat the current project files and confirmed implementation as the source of truth. Do not assume proposed features are implemented.

## 2. No invented hardware
Do not invent:
- Pin assignments
- Component specifications
- PZEM electrical characteristics
- Threshold values
- Communication details
- Protection ratings

Verify them from the actual datasheet or confirmed project configuration.

## 3. Scope
The project is primarily:
**Power monitoring + fault identification + logging + dashboard**

It is not automatically a complete electrical protection system.

## 4. MQ-135
MQ-135 has been removed. Do not add it to architecture, BOM, firmware or documentation.

## 5. Safety
This project interfaces with 3-phase mains electricity. Every mains-related recommendation must consider:
- Isolation
- Creepage and clearance
- Fusing
- Component ratings
- Conductor sizing
- Terminal ratings
- Enclosure
- Earthing
- Safe testing procedures

Never recommend treating mains wiring like low-voltage breadboard wiring.

## 6. SSR rule
SSR-40DA devices must not be described as replacements for:
- Fuses
- MCBs
- MCCBs
- Overload relays
- Proper isolation
- Properly rated contactors

Any automatic switching must be treated as a separate control layer.

## 7. Fault logic
Never classify a PZEM communication failure as phase loss without additional evidence.

Distinguish:
- Sensor/communication fault
- Genuine electrical abnormality

## 8. Data integrity
Telemetry should be timestamped, validated and associated with:
- device_id
- phase
- measurement values
- timestamp
- quality/status information where applicable

## 9. AI/ML claims
Do not claim AI/ML or predictive maintenance unless a real model/method has been implemented, evaluated and documented.

## 10. Development discipline
Build incrementally. Keep firmware, backend, database and frontend changes understandable and testable.

## 11. Budget
Prefer components already owned. Clearly identify anything that must be purchased.

## 12. Documentation
Every implemented feature should be documented. Proposed features must be labelled as proposed/future work.

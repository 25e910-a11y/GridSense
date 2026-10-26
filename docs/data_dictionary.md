# Data Dictionary

## 1. Electrical Measurements

| Field | Unit | Description |
|---|---|---|
| voltage | V | RMS voltage |
| current | A | RMS current |
| power | W | Active power |
| energy | kWh | Cumulative electrical energy |
| power_factor | - | Power factor |
| frequency | Hz | Supply frequency |

## 2. Environment

| Field | Unit | Description |
|---|---|---|
| temperature | °C | Temperature measured by DS18B20 |

## 3. Device

| Field | Description |
|---|---|
| device_id | Unique monitoring device identifier |
| device_status | Online/offline/error status |
| firmware_version | Firmware version running on ESP32 |

## 4. Relay

| Field | Description |
|---|---|
| relay_state | Current relay state |
| commanded_state | State requested by authorized user/system |
| actual_state | State confirmed by device |

## 5. Time

| Field | Description |
|---|---|
| measurement_timestamp | Timestamp generated/reported by device RTC |
| server_received_at | Timestamp when backend receives data |

## 6. Metadata

| Field | Description |
|---|---|
| source | REAL / SIMULATION / TEST |
| data_quality | Quality/validity status of measurement |
| transmission_reason | Reason for transmission |

## 7. Transmission Reasons

- SCHEDULED
- PARAMETER_CHANGE
- FAULT_EVENT
- RELAY_EVENT
- DEVICE_EVENT

## 8. Change Detection

Change detection applies to:

- Voltage
- Current
- Power
- Power Factor
- Frequency
- Temperature
- Relay state

Energy is stored but is NOT used as a change-trigger parameter.

## 9. Location Hierarchy

College
→ Block
→ Floor
→ Monitoring Device

## 10. Data Sources

REAL = Physical ESP32 hardware

SIMULATION = MATLAB or other simulation

TEST = Development/testing data

## 11. ML Configuration

ML_ENABLED = false

ML_DEMO = false
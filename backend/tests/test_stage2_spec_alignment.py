"""Checks that the backend matches the Stage 2 (Vishwakarma Awards) design.

- Enclosure temperature warning at 65 °C by default, adjustable, warning only
- Phase imbalance alarm only when imbalance is above 10% (not at exactly 10%)
- One ingest key per device
- Per-device alarm limits and a log-only mode before alerting
- Work order closes only after readings are back to normal
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.models.notification import Notification
from app.rules.engine import PhaseSample, evaluate_telemetry
from app.rules.thresholds import thresholds_from_settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reading(device_id: int, phase: str = "R", **overrides) -> dict:
    payload = {
        "device_id": device_id,
        "phase": phase,
        "voltage": 230.0,
        "current": 5.0,
        "power": 1100.0,
        "energy": 1.0,
        "power_factor": 0.96,
        "frequency": 50.0,
        "temperature": 35.0,
        "sampled_at": _now(),
    }
    payload.update(overrides)
    return payload


def _make_device(client, admin_headers, code: str) -> int:
    res = client.post("/devices/", params={"device_id": code, "name": code}, headers=admin_headers)
    assert res.status_code == 200
    return res.json()["device_id"]


# --- Temperature -----------------------------------------------------------

def test_enclosure_temperature_defaults_to_65c_warning():
    thresholds = thresholds_from_settings(settings)
    assert thresholds.high_temperature_c == 65.0

    below = PhaseSample(phase="R", voltage=230, current=5, frequency=50, temperature=64.9, data_quality="good")
    assert not [f for f in evaluate_telemetry(below, thresholds) if f.fault_type == "HIGH_TEMPERATURE"]

    at_limit = PhaseSample(phase="R", voltage=230, current=5, frequency=50, temperature=65.0, data_quality="good")
    hot = [f for f in evaluate_telemetry(at_limit, thresholds) if f.fault_type == "HIGH_TEMPERATURE"]
    assert len(hot) == 1
    assert hot[0].severity == "warning"
    # One sensor per enclosure: a node-level event, not one per phase.
    assert hot[0].phase is None


# --- Imbalance -------------------------------------------------------------

def test_imbalance_at_exactly_10_percent_does_not_alarm():
    thresholds = thresholds_from_settings(settings)
    sample = PhaseSample(phase="R", voltage=207.0, data_quality="good")
    others = [
        PhaseSample(phase="Y", voltage=230.0, data_quality="good"),
        PhaseSample(phase="B", voltage=253.0, data_quality="good"),
    ]
    findings = evaluate_telemetry(sample, thresholds, other_phases=others)
    assert "PHASE_IMBALANCE" not in {f.fault_type for f in findings}


def test_imbalance_above_10_percent_alarms():
    thresholds = thresholds_from_settings(settings)
    sample = PhaseSample(phase="R", voltage=200.0, data_quality="good")
    others = [
        PhaseSample(phase="Y", voltage=230.0, data_quality="good"),
        PhaseSample(phase="B", voltage=252.0, data_quality="good"),
    ]
    findings = evaluate_telemetry(sample, thresholds, other_phases=others)
    assert "PHASE_IMBALANCE" in {f.fault_type for f in findings}


# --- One key per device ----------------------------------------------------

def test_each_device_has_its_own_ingest_key(client, admin_headers, ingest_headers, operator_headers):
    dev_a = _make_device(client, admin_headers, "KEY-DEV-A")
    dev_b = _make_device(client, admin_headers, "KEY-DEV-B")

    key_res = client.post(f"/devices/{dev_a}/ingest-key", headers=admin_headers)
    assert key_res.status_code == 200
    key_a = key_res.json()["ingest_key"]

    # Only admins can create keys
    assert client.post(f"/devices/{dev_a}/ingest-key", headers=operator_headers).status_code == 403

    # The key (or its hash) is never returned by the device endpoints
    detail = client.get(f"/devices/{dev_a}", headers=admin_headers).json()
    assert "ingest_key" not in detail
    assert detail["has_own_ingest_key"] is True
    assert key_a not in str(client.get("/devices/", headers=admin_headers).json())

    # Device A with its own key: accepted
    ok = client.post("/telemetry/", json=_reading(dev_a), headers={"X-Ingest-Key": key_a})
    assert ok.status_code == 200
    assert key_a not in str(ok.json())

    # Device A with the shared key: refused, because it has its own key now
    shared = client.post("/telemetry/", json=_reading(dev_a), headers=ingest_headers)
    assert shared.status_code == 401

    # Device B cannot use device A's key
    wrong_device = client.post("/telemetry/", json=_reading(dev_b), headers={"X-Ingest-Key": key_a})
    assert wrong_device.status_code == 401

    # Device B has no key of its own yet, so the shared key still works for it
    assert client.post("/telemetry/", json=_reading(dev_b), headers=ingest_headers).status_code == 200

    # Rotating the key revokes the old one
    key_a2 = client.post(f"/devices/{dev_a}/ingest-key", headers=admin_headers).json()["ingest_key"]
    assert client.post("/telemetry/", json=_reading(dev_a), headers={"X-Ingest-Key": key_a}).status_code == 401
    assert client.post("/telemetry/", json=_reading(dev_a), headers={"X-Ingest-Key": key_a2}).status_code == 200


# --- Per-device limits and log-only mode ----------------------------------

def test_per_device_limits_override_site_defaults(client, admin_headers, ingest_headers):
    dev_custom = _make_device(client, admin_headers, "LIMIT-DEV-1")
    dev_default = _make_device(client, admin_headers, "LIMIT-DEV-2")

    res = client.put(
        f"/devices/{dev_custom}/limits",
        json={"limits": {"high_temperature_c": 50}},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["effective"]["high_temperature_c"] == 50.0

    hot_custom = client.post("/telemetry/", json=_reading(dev_custom, temperature=55.0), headers=ingest_headers)
    assert "HIGH_TEMPERATURE" in {f["fault_type"] for f in hot_custom.json()["findings"]}

    hot_default = client.post("/telemetry/", json=_reading(dev_default, temperature=55.0), headers=ingest_headers)
    assert "HIGH_TEMPERATURE" not in {f["fault_type"] for f in hot_default.json()["findings"]}

    # Removing the override goes back to the site default
    cleared = client.put(
        f"/devices/{dev_custom}/limits",
        json={"limits": {"high_temperature_c": None}},
        headers=admin_headers,
    )
    assert cleared.json()["effective"]["high_temperature_c"] == 65.0

    # Unknown names and bad values are rejected
    assert client.put(
        f"/devices/{dev_custom}/limits", json={"limits": {"made_up": 1}}, headers=admin_headers
    ).status_code == 400
    assert client.put(
        f"/devices/{dev_custom}/limits", json={"limits": {"imbalance_percent": 0}}, headers=admin_headers
    ).status_code == 400


def test_log_only_mode_logs_faults_without_notifying(client, admin_headers, ingest_headers, db):
    dev = _make_device(client, admin_headers, "LOGONLY-DEV")
    res = client.put(f"/devices/{dev}/limits", json={"alert_mode": "log_only"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["alert_mode"] == "log_only"

    before = db.query(Notification).count()
    high = client.post("/telemetry/", json=_reading(dev, voltage=260.0), headers=ingest_headers)
    assert high.status_code == 200
    assert high.json()["faults_created"] == 1
    assert high.json()["alert_mode"] == "log_only"
    assert db.query(Notification).count() == before

    # Switch to alert mode: the next new fault notifies
    client.put(f"/devices/{dev}/limits", json={"alert_mode": "alert"}, headers=admin_headers)
    low = client.post("/telemetry/", json=_reading(dev, phase="Y", voltage=180.0), headers=ingest_headers)
    assert low.json()["faults_created"] == 1
    assert db.query(Notification).count() == before + 1

    assert client.put(
        f"/devices/{dev}/limits", json={"alert_mode": "silent"}, headers=admin_headers
    ).status_code == 400


# --- Return-to-normal check ------------------------------------------------

def test_work_order_closes_only_after_readings_are_normal(client, admin_headers, ingest_headers, technician_user):
    dev = _make_device(client, admin_headers, "RTN-DEV")

    fault_reading = client.post("/telemetry/", json=_reading(dev, phase="B", voltage=262.0), headers=ingest_headers)
    assert fault_reading.json()["faults_created"] == 1

    faults = client.get("/faults/", params={"device_id": dev}, headers=admin_headers).json()
    fault_id = next(f["id"] for f in faults if f["fault_type"] == "OVERVOLTAGE")

    wo = client.post(
        "/maintenance/work-orders",
        json={"fault_id": fault_id, "assigned_to": technician_user.username},
        headers=admin_headers,
    )
    assert wo.status_code == 200
    wo_id = wo.json()["work_order_id"]

    def set_status(value: str):
        return client.put(
            f"/maintenance/work-orders/{wo_id}/status",
            json={"status": value},
            headers=admin_headers,
        )

    # Cannot close before the repair is marked restored
    not_restored = set_status("closed")
    assert not_restored.status_code == 409

    assert set_status("restored").status_code == 200

    # Still high after the repair: refused
    client.post("/telemetry/", json=_reading(dev, phase="B", voltage=262.0), headers=ingest_headers)
    still_bad = set_status("closed")
    assert still_bad.status_code == 409
    assert "still shows OVERVOLTAGE" in still_bad.json()["detail"]

    # Sensor error after the repair: refused, nothing to confirm with
    client.post(
        "/telemetry/",
        json=_reading(dev, phase="B", voltage=0.0, data_quality="SENSOR_COMM_TIMEOUT"),
        headers=ingest_headers,
    )
    sensor_err = set_status("closed")
    assert sensor_err.status_code == 409
    assert "sensor" in sensor_err.json()["detail"].lower()

    # Normal reading: closes, fault rectified
    client.post("/telemetry/", json=_reading(dev, phase="B", voltage=231.0), headers=ingest_headers)
    closed = set_status("closed")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert client.get(f"/faults/{fault_id}", headers=admin_headers).json()["status"] == "rectified"


# --- KPI summary -------------------------------------------------------------

def test_summary_adds_energy_across_phases_and_counts_open_work_orders(
    client, admin_headers, ingest_headers, technician_user
):
    dev = _make_device(client, admin_headers, "KPI-DEV")
    for phase, energy in (("R", 10.0), ("Y", 20.0), ("B", 30.0)):
        res = client.post("/telemetry/", json=_reading(dev, phase=phase, energy=energy, power=1000.0), headers=ingest_headers)
        assert res.status_code == 200

    summary = client.get("/dashboard/summary", headers=admin_headers).json()
    # Each PZEM has its own energy counter: total is the sum, not the largest one.
    assert summary["total_energy_kwh"] == 60.0
    assert summary["total_active_power_watts"] == 3000.0
    assert summary["open_work_orders_count"] == 0

    client.post("/telemetry/", json=_reading(dev, phase="R", voltage=262.0, energy=10.0), headers=ingest_headers)
    fault_id = next(
        f["id"] for f in client.get("/faults/", params={"device_id": dev}, headers=admin_headers).json()
        if f["fault_type"] == "OVERVOLTAGE"
    )
    wo = client.post(
        "/maintenance/work-orders",
        json={"fault_id": fault_id, "assigned_to": technician_user.username},
        headers=admin_headers,
    )
    assert wo.status_code == 200
    assert client.get("/dashboard/summary", headers=admin_headers).json()["open_work_orders_count"] == 1

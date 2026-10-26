from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.device import Device
from app.models.relay import Relay
from app.models.telemetry import Telemetry


def test_telemetry_future_clock_skew_rejection(client, admin_headers, ingest_headers, db):
    """
    Verify that telemetry samples with timestamps exceeding CLOCK_SKEW_TOLERANCE_SECONDS
    are strictly rejected with HTTP 400 to preserve telemetry integrity.
    """
    dev = Device(device_id="CLOCK-TEST-01", name="Clock Skew Feeder", is_active=True)
    db.add(dev)
    db.commit()

    # 1. Timestamp in distant future (e.g. 1 hour ahead) -> 400
    future_time = datetime.now(timezone.utc) + timedelta(seconds=settings.CLOCK_SKEW_TOLERANCE_SECONDS + 120)
    res_future = client.post(
        "/telemetry/",
        json={
            "device_id": dev.id,
            "phase": "R",
            "voltage": 230.0,
            "current": 5.0,
            "power": 1150.0,
            "energy": 10.0,
            "frequency": 50.0,
            "power_factor": 0.95,
            "temperature": 32.0,
            "sampled_at": future_time.isoformat(),
            "source": "REAL",
            "transmission_reason": "SCHEDULED",
            "data_quality": "good",
        },
        headers=ingest_headers,
    )
    assert res_future.status_code == 400
    assert "future beyond allowable clock skew" in res_future.json()["detail"]

    # 2. Timestamp within tolerance -> 200
    valid_time = datetime.now(timezone.utc)
    res_valid = client.post(
        "/telemetry/",
        json={
            "device_id": dev.id,
            "phase": "R",
            "voltage": 230.0,
            "current": 5.0,
            "power": 1150.0,
            "energy": 10.0,
            "frequency": 50.0,
            "power_factor": 0.95,
            "temperature": 32.0,
            "sampled_at": valid_time.isoformat(),
            "source": "REAL",
            "transmission_reason": "SCHEDULED",
            "data_quality": "good",
        },
        headers=ingest_headers,
    )
    assert res_valid.status_code == 200


def test_live_dashboard_stale_and_partial_phase_truthfulness(client, ingest_headers, admin_headers, db):
    """
    Verify that live dashboard enforces complete, fresh 3-phase telemetry.
    Missing phases or stale readings must report system_status 'Offline',
    never falsely declaring 'Normal' when measurements are incomplete.
    """
    dev = Device(device_id="PARTIAL-DEV-01", name="Partial Phase Monitor", is_active=True)
    db.add(dev)
    db.commit()

    now_utc = datetime.now(timezone.utc)

    # 1. Post only Phase R and Phase Y (Phase B missing)
    for p in ("R", "Y"):
        client.post(
            "/telemetry/",
            json={
                "device_id": dev.id,
                "phase": p,
                "voltage": 230.0,
                "current": 5.0,
                "power": 1150.0,
                "energy": 1.0,
                "frequency": 50.0,
                "power_factor": 0.95,
                "temperature": 30.0,
                "sampled_at": now_utc.isoformat(),
                "data_quality": "good",
            },
            headers=ingest_headers,
        )

    # Unauthenticated request rejected
    assert client.get(f"/dashboard/live?device_id={dev.id}").status_code == 401

    dash_partial = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert dash_partial.status_code == 200
    data_partial = dash_partial.json()
    assert data_partial["system_status"] == "Offline"
    assert "R" in data_partial["phases"]
    assert "Y" in data_partial["phases"]
    assert "B" not in data_partial["phases"]

    # 2. Add Phase B with an expired/stale timestamp (> DEVICE_OFFLINE_SECONDS)
    stale_time = now_utc - timedelta(seconds=settings.DEVICE_OFFLINE_SECONDS + 60)
    db.add(Telemetry(
        device_id=dev.id,
        phase="B",
        voltage=230.0,
        current=5.0,
        power=1150.0,
        energy=1.0,
        frequency=50.0,
        power_factor=0.95,
        temperature=30.0,
        sampled_at=stale_time,
        received_at=stale_time,
        data_quality="GOOD",
        transmission_reason="SCHEDULED",
        source="REAL",
    ))
    db.commit()

    dash_stale = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert dash_stale.status_code == 200
    assert dash_stale.json()["system_status"] == "Offline"

    # 3. Update Phase B with a fresh timestamp -> status transitions to 'Normal'
    fresh_time = datetime.now(timezone.utc)
    db.add(Telemetry(
        device_id=dev.id,
        phase="B",
        voltage=230.0,
        current=5.0,
        power=1150.0,
        energy=1.0,
        frequency=50.0,
        power_factor=0.95,
        temperature=30.0,
        sampled_at=fresh_time,
        received_at=fresh_time,
        data_quality="GOOD",
        transmission_reason="SCHEDULED",
        source="REAL",
    ))
    dev.last_seen_at = fresh_time
    db.commit()

    dash_fresh = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert dash_fresh.status_code == 200
    assert dash_fresh.json()["system_status"] == "Normal"
    assert all(p in dash_fresh.json()["phases"] for p in ("R", "Y", "B"))


def test_relay_command_never_falsely_claims_physical_actuation(client, admin_headers, operator_headers, db):
    """
    Verify that issuing a relay toggle command:
    - Sets commanded_state to target value
    - Explicitly returns hardware_verified = False
    - Retains actual_state = None (or prior verified state)
    - Rejects inactive relays with 400
    """
    dev = Device(device_id="RELAY-TEST-DEV", name="SSR Feeder", is_active=True)
    db.add(dev)
    db.commit()

    relay = Relay(
        device_id=dev.id,
        relay_number=1,
        name="Main 3-Phase Contactor",
        gpio_pin=22,
        commanded_state=False,
        actual_state=None,
        is_on=False,
        is_active=True,
    )
    db.add(relay)
    db.commit()

    # 1. Admin turns relay ON -> returns acceptance, but NOT verified actuation
    res_on = client.post(f"/relays/{relay.id}/on", headers=admin_headers)
    assert res_on.status_code == 200
    data_on = res_on.json()
    assert data_on["status"] == "success"
    assert "awaiting physical contactor feedback" in data_on["message"]
    assert data_on["commanded_state"] is True
    assert data_on["is_on"] is True
    assert data_on["actual_state"] is None
    assert data_on["hardware_verified"] is False

    # 2. Inactive relay rejection
    relay.is_active = False
    db.commit()

    res_inactive = client.post(f"/relays/{relay.id}/off", headers=admin_headers)
    assert res_inactive.status_code == 400
    assert "Relay is inactive" in res_inactive.json()["detail"]

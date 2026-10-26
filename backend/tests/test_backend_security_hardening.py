from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import create_access_token
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.fault import Fault
from app.models.relay import Relay
from app.models.telemetry import Telemetry


def test_public_registration_cannot_create_admin(client, admin_headers):
    # 1. Unauthenticated public registration requesting 'admin' role must fail with 403
    pub_res = client.post(
        "/auth/register",
        json={"username": "fake_admin", "password": "password123", "role": "admin"},
    )
    assert pub_res.status_code == 403
    assert "Public registration cannot grant administrative privileges" in pub_res.json()["detail"]

    # 2. Public registration requesting 'operator' succeeds
    op_res = client.post(
        "/auth/register",
        json={"username": "valid_operator", "password": "password123", "role": "operator"},
    )
    assert op_res.status_code == 200
    assert op_res.json()["role"] == "operator"

    # 3. Authenticated admin CAN provision another admin
    admin_create_res = client.post(
        "/auth/register",
        json={"username": "second_admin", "password": "password123", "role": "admin"},
        headers=admin_headers,
    )
    assert admin_create_res.status_code == 200
    assert admin_create_res.json()["role"] == "admin"


def test_login_and_auth_me(client):
    # Register an operator
    client.post(
        "/auth/register",
        json={"username": "login_user", "password": "correct_password", "role": "operator"},
    )

    # 1. Correct credentials -> 200 with JWT
    login_res = client.post(
        "/auth/login",
        json={"username": "login_user", "password": "correct_password"},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["role"] == "operator"

    # 2. Access /auth/me with token
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["authenticated"] is True
    assert me_res.json()["username"] == "login_user"

    # 3. Incorrect credentials -> 401
    bad_login = client.post(
        "/auth/login",
        json={"username": "login_user", "password": "wrong_password"},
    )
    assert bad_login.status_code == 401


def test_bearer_token_validation(client):
    # 1. Missing token on protected endpoint -> 401
    res_missing = client.get("/auth/me")
    assert res_missing.status_code == 401
    assert "Not authenticated" in res_missing.json()["detail"]

    # 2. Invalid / malformed token -> 401
    res_invalid = client.get("/auth/me", headers={"Authorization": "Bearer gibberish_token_string"})
    assert res_invalid.status_code == 401
    assert "Invalid token" in res_invalid.json()["detail"]

    # 3. Expired token -> 401
    expired_token = create_access_token(
        username="admin_tester",
        role="admin",
        expires_delta=timedelta(seconds=-60),
    )
    res_expired = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401
    assert "Token has expired" in res_expired.json()["detail"]


def test_server_side_rbac_matrix(
    client,
    admin_headers,
    technician_headers,
    operator_headers,
    db,
):
    # Setup test device and relay
    dev = Device(device_id="RBAC-DEV-01", name="RBAC Test PMU", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="SSR-R", gpio_pin=7, is_active=True, is_on=False)
    db.add(relay)

    fault = Fault(device_id=dev.id, fault_type="OVERCURRENT", severity="fault", status="detected", detected_at=datetime.now(timezone.utc))
    db.add(fault)
    db.commit()

    # 1. Relay ON/OFF commands: Admin only
    # Unauthenticated -> 401
    assert client.post(f"/relays/{relay.id}/on").status_code == 401
    # Operator -> 403 Forbidden
    op_relay_res = client.post(f"/relays/{relay.id}/on", headers=operator_headers)
    assert op_relay_res.status_code == 403
    assert "Operation not permitted" in op_relay_res.json()["detail"]
    # Technician -> 403 Forbidden
    tech_relay_res = client.post(f"/relays/{relay.id}/on", headers=technician_headers)
    assert tech_relay_res.status_code == 403
    # Admin -> 200 OK
    admin_relay_res = client.post(f"/relays/{relay.id}/on", headers=admin_headers)
    assert admin_relay_res.status_code == 200

    # 2. Fault Acknowledgment: Operator forbidden (read-only), Admin permitted
    op_ack_res = client.put(f"/faults/{fault.id}/acknowledge", headers=operator_headers)
    assert op_ack_res.status_code == 403
    admin_ack_res = client.put(f"/faults/{fault.id}/acknowledge", headers=admin_headers)
    assert admin_ack_res.status_code == 200

    # 3. Fault Rectification: Technician and Admin permitted, Operator forbidden
    op_rect_res = client.put(f"/faults/{fault.id}/rectify", params={"resolution": "Reset"}, headers=operator_headers)
    assert op_rect_res.status_code == 403
    assert any(msg in op_rect_res.json()["detail"] for msg in ("Operation not permitted", "Permission denied"))

    tech_rect_res = client.put(f"/faults/{fault.id}/rectify", params={"resolution": "Reset breaker"}, headers=technician_headers)
    assert tech_rect_res.status_code == 200

    # 4. Location and Device creation: Admin only
    assert client.post("/locations/colleges", params={"name": "New College"}, headers=operator_headers).status_code == 403
    assert client.post("/locations/colleges", params={"name": "New College"}, headers=technician_headers).status_code == 403
    assert client.post("/locations/colleges", params={"name": "New College"}, headers=admin_headers).status_code == 200

    assert client.post("/devices/", params={"device_id": "DEV-NO-AUTH", "name": "Device"}, headers=operator_headers).status_code == 403
    assert client.post("/devices/", params={"device_id": "DEV-AUTH", "name": "Device"}, headers=admin_headers).status_code == 200


def test_telemetry_ingestion_authentication(
    client,
    ingest_headers,
    operator_headers,
    db,
):
    dev = Device(device_id="INGEST-DEV-01", name="Ingest Test Unit", is_active=True)
    db.add(dev)
    db.commit()

    sample_payload = {
        "device_id": dev.id,
        "phase": "R",
        "voltage": 230.0,
        "current": 4.5,
        "power": 1035.0,
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "data_quality": "good",
    }

    # 1. Valid X-Ingest-Key with NO Bearer token -> 200 OK
    res_valid_key = client.post("/telemetry/", json=sample_payload, headers=ingest_headers)
    assert res_valid_key.status_code == 200
    assert res_valid_key.json()["status"] == "success"

    # 2. Invalid X-Ingest-Key -> 401 Unauthorized
    res_invalid_key = client.post("/telemetry/", json=sample_payload, headers={"X-Ingest-Key": "wrong-key-value"})
    assert res_invalid_key.status_code == 401
    assert "Invalid device ingestion key" in res_invalid_key.json()["detail"]

    # 3. Missing credentials entirely -> 401 Unauthorized
    res_missing = client.post("/telemetry/", json=sample_payload)
    assert res_missing.status_code == 401

    # 4. Authenticated user token (without X-Ingest-Key) -> 200 OK (for manual testing / simulation)
    res_user = client.post("/telemetry/", json=sample_payload, headers=operator_headers)
    assert res_user.status_code == 200

    # 5. Ingest API key is NOT exposed in response payload
    assert settings.INGEST_API_KEY not in str(res_valid_key.json())


def test_relay_command_persistence_and_audit(client, admin_headers, db):
    dev = Device(device_id="RELAY-TEST-DEV", name="Substation Relay Device", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(
        device_id=dev.id,
        relay_number=1,
        name="Main 3-Phase Contactor",
        gpio_pin=7,
        commanded_state=False,
        is_on=False,
        is_active=True,
    )
    db.add(relay)
    db.commit()

    # 1. Turn relay ON
    on_res = client.post(f"/relays/{relay.id}/on", headers=admin_headers)
    assert on_res.status_code == 200
    on_data = on_res.json()
    assert on_data["commanded_state"] is True
    assert on_data["is_on"] is True
    assert on_data["hardware_verified"] is False
    assert "awaiting physical contactor feedback" in on_data["message"]

    # Verify DB persistence
    db.refresh(relay)
    assert relay.commanded_state is True
    assert relay.is_on is True

    # Verify audit log entry
    audit_on = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "relay", AuditLog.action == "relay_command_on")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit_on is not None
    assert audit_on.actor == "admin_tester"
    assert audit_on.entity_id == relay.id

    # 2. Turn relay OFF
    off_res = client.post(f"/relays/{relay.id}/off", headers=admin_headers)
    assert off_res.status_code == 200
    off_data = off_res.json()
    assert off_data["commanded_state"] is False
    assert off_data["is_on"] is False

    db.refresh(relay)
    assert relay.commanded_state is False
    assert relay.is_on is False

    audit_off = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "relay", AuditLog.action == "relay_command_off")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit_off is not None
    assert audit_off.actor == "admin_tester"


def test_stale_telemetry_and_offline_status(client, admin_headers, ingest_headers, db):
    dev = Device(device_id="STALE-DEV-01", name="Stale Detection Device", is_active=True)
    db.add(dev)
    db.commit()

    # 1. Unauthenticated -> 401; Device with no telemetry -> Offline
    assert client.get(f"/dashboard/live?device_id={dev.id}").status_code == 401
    res_no_data = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_no_data.status_code == 200
    assert res_no_data.json()["system_status"] == "Offline"

    # 2. Stale telemetry older than settings.DEVICE_OFFLINE_SECONDS (120s default) -> Offline
    old_time = datetime.now(timezone.utc) - timedelta(seconds=settings.DEVICE_OFFLINE_SECONDS + 30)
    for phase in ("R", "Y", "B"):
        db.add(Telemetry(
            device_id=dev.id,
            phase=phase,
            voltage=230.0,
            current=4.0,
            power=920.0,
            energy=1.0,
            frequency=50.0,
            power_factor=0.98,
            temperature=30.0,
            sampled_at=old_time,
            received_at=old_time,
            data_quality="GOOD",
            transmission_reason="SCHEDULED",
            source="REAL",
        ))
    dev.last_seen_at = old_time
    db.commit()

    res_stale = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_stale.status_code == 200
    assert res_stale.json()["system_status"] == "Offline"

    # 3. Incomplete phases (only R and Y, missing B) -> Offline
    fresh_time = datetime.now(timezone.utc)
    db.query(Telemetry).filter(Telemetry.device_id == dev.id).delete()
    for phase in ("R", "Y"):
        db.add(Telemetry(
            device_id=dev.id,
            phase=phase,
            voltage=230.0,
            current=4.0,
            power=920.0,
            energy=1.0,
            frequency=50.0,
            power_factor=0.98,
            temperature=30.0,
            sampled_at=fresh_time,
            received_at=fresh_time,
            data_quality="GOOD",
            transmission_reason="SCHEDULED",
            source="REAL",
        ))
    dev.last_seen_at = fresh_time
    db.commit()

    res_incomplete = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_incomplete.status_code == 200
    assert res_incomplete.json()["system_status"] == "Offline"

    # 4. Fresh complete 3-phase telemetry -> Normal
    db.add(Telemetry(
        device_id=dev.id,
        phase="B",
        voltage=230.0,
        current=4.0,
        power=920.0,
        energy=1.0,
        frequency=50.0,
        power_factor=0.98,
        temperature=30.0,
        sampled_at=fresh_time,
        received_at=fresh_time,
        data_quality="GOOD",
        transmission_reason="SCHEDULED",
        source="REAL",
    ))
    db.commit()

    res_fresh = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_fresh.status_code == 200
    assert res_fresh.json()["system_status"] == "Normal"

    # 5. Device is_active = False -> Offline
    dev.is_active = False
    db.commit()
    res_inactive = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_inactive.status_code == 200
    assert res_inactive.json()["system_status"] == "Offline"


def test_unknown_resource_ids(client, admin_headers, technician_headers, operator_headers):
    # Unknown device on telemetry -> 404
    telem_res = client.post(
        "/telemetry/",
        json={"device_id": 99999, "phase": "R", "voltage": 230.0, "current": 4.0, "power": 920.0, "sampled_at": datetime.now(timezone.utc).isoformat(), "data_quality": "good"},
        headers=admin_headers,
    )
    assert telem_res.status_code == 404
    assert "Device not found" in telem_res.json()["detail"]

    # Unknown relay -> 404
    relay_res = client.post("/relays/99999/on", headers=admin_headers)
    assert relay_res.status_code == 404
    assert "Relay not found" in relay_res.json()["detail"]

    # Unknown fault -> 404 (Admin/Shift Lead permitted to acknowledge)
    fault_res = client.put("/faults/99999/acknowledge", headers=admin_headers)
    assert fault_res.status_code == 404
    assert "Fault not found" in fault_res.json()["detail"]

    # Unknown work order -> 404 (requires technician or admin)
    wo_res = client.get("/maintenance/work-orders/99999", headers=technician_headers)
    assert wo_res.status_code == 404
    assert "Work order not found" in wo_res.json()["detail"]

    # Unknown device on live dashboard -> 404 (Authenticated)
    dash_res = client.get("/dashboard/live?device_id=99999", headers=admin_headers)
    assert dash_res.status_code == 404
    assert "Device not found" in dash_res.json()["detail"]

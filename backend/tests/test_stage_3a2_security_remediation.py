from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import ensure_initial_admin, hash_password, verify_password
from app.models.device import Device
from app.models.fault import Fault
from app.models.notification import Notification
from app.models.relay import Relay
from app.models.telemetry import Telemetry
from app.models.user import User
from app.models.work_order import WorkOrder


# ======================================================================
# 1. REGISTRATION AND ROLE ESCALATION
# ======================================================================

def test_anonymous_registration_cannot_escalate_roles(client):
    # 1. Anonymous requesting 'technician' must be blocked with 403
    tech_res = client.post(
        "/auth/register",
        json={"username": "anon_tech", "password": "password123", "role": "technician"},
    )
    assert tech_res.status_code == 403
    assert "technician" in tech_res.json()["detail"].lower()

    # 2. Anonymous requesting 'admin' must be blocked with 403
    admin_res = client.post(
        "/auth/register",
        json={"username": "anon_admin", "password": "password123", "role": "admin"},
    )
    assert admin_res.status_code == 403
    assert "administrative privileges" in admin_res.json()["detail"].lower()

    # 3. Anonymous requesting 'operator' succeeds
    op_res = client.post(
        "/auth/register",
        json={"username": "anon_op", "password": "password123", "role": "operator"},
    )
    assert op_res.status_code == 200
    assert op_res.json()["role"] == "operator"


def test_authenticated_role_provisioning_hierarchy(
    client,
    operator_headers,
    technician_headers,
    admin_headers,
):
    # Operator cannot provision technician or admin
    op_tech = client.post(
        "/auth/register",
        json={"username": "op_created_tech", "password": "password123", "role": "technician"},
        headers=operator_headers,
    )
    assert op_tech.status_code == 403

    op_admin = client.post(
        "/auth/register",
        json={"username": "op_created_admin", "password": "password123", "role": "admin"},
        headers=operator_headers,
    )
    assert op_admin.status_code == 403

    # Technician cannot provision technician or admin
    tech_tech = client.post(
        "/auth/register",
        json={"username": "tech_created_tech", "password": "password123", "role": "technician"},
        headers=technician_headers,
    )
    assert tech_tech.status_code == 403

    # Admin CAN provision technician, admin, and operator
    adm_tech = client.post(
        "/auth/register",
        json={"username": "admin_created_tech", "password": "password123", "role": "technician"},
        headers=admin_headers,
    )
    assert adm_tech.status_code == 200
    assert adm_tech.json()["role"] == "technician"

    adm_adm = client.post(
        "/auth/register",
        json={"username": "admin_created_admin", "password": "password123", "role": "admin"},
        headers=admin_headers,
    )
    assert adm_adm.status_code == 200
    assert adm_adm.json()["role"] == "admin"


# ======================================================================
# 2. SECURE ADMINISTRATOR PROVISIONING
# ======================================================================

def test_initial_admin_provisioning_validation(db, monkeypatch):
    # Ensure no admin exists
    db.query(User).filter(User.role == "admin").delete()
    db.commit()

    # 1. Missing username or password -> raises ValueError
    monkeypatch.setattr("app.core.security.settings.ADMIN_USERNAME", None)
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", None)
    with pytest.raises(ValueError, match="ADMIN_USERNAME is missing"):
        ensure_initial_admin(db)

    # 2. Missing password -> raises ValueError
    monkeypatch.setattr("app.core.security.settings.ADMIN_USERNAME", "sysadmin")
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "")
    with pytest.raises(ValueError, match="ADMIN_PASSWORD is missing"):
        ensure_initial_admin(db)

    # 3. Known insecure password ('admin', 'password', '123456') -> raises ValueError
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "admin")
    with pytest.raises(ValueError, match="at least 8 characters"):
        ensure_initial_admin(db)

    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "password")
    with pytest.raises(ValueError, match="known insecure or default credential"):
        ensure_initial_admin(db)

    # 4. Username equals password -> raises ValueError
    monkeypatch.setattr("app.core.security.settings.ADMIN_USERNAME", "supersecret12")
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "supersecret12")
    with pytest.raises(ValueError, match="cannot be identical"):
        ensure_initial_admin(db)

    # 5. Strong non-default credentials -> successfully provisions admin
    monkeypatch.setattr("app.core.security.settings.ADMIN_USERNAME", "root_admin")
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "ValidStrongPass2026!")
    new_admin = ensure_initial_admin(db)
    assert new_admin is not None
    assert new_admin.username == "root_admin"
    assert new_admin.role == "admin"
    assert verify_password("ValidStrongPass2026!", new_admin.password_hash)

    # 6. Existing administrator password is NOT overwritten on subsequent runs
    original_hash = new_admin.password_hash
    monkeypatch.setattr("app.core.security.settings.ADMIN_PASSWORD", "AnotherPassword999!")
    same_admin = ensure_initial_admin(db)
    assert same_admin.id == new_admin.id
    assert same_admin.password_hash == original_hash
    assert not verify_password("AnotherPassword999!", same_admin.password_hash)


# ======================================================================
# 3. JWT SECRET VALIDATION AND ENVIRONMENT FAIL-SAFES
# ======================================================================

def test_production_jwt_secret_validation():
    # Production with missing secret -> fails validation
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET=None)

    # Production with insecure default secret -> fails validation
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET="dev-change-me")

    # Production with secret shorter than 32 chars -> fails validation
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET="short-secret-key-too-brief")

    # Production with strong 32+ character secret -> succeeds
    prod_settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="a" * 32,
    )
    assert prod_settings.JWT_SECRET == "a" * 32

    # Development mode without JWT_SECRET provides safe fallback without crashing
    dev_settings = Settings(ENVIRONMENT="development", JWT_SECRET=None)
    assert dev_settings.JWT_SECRET is not None
    assert len(dev_settings.JWT_SECRET) >= 32


# ======================================================================
# 4. AUDIT ENDPOINT AUTHORIZATION
# ======================================================================

def test_audit_endpoint_strict_admin_authorization(
    client,
    operator_headers,
    technician_headers,
    admin_headers,
):
    # 1. Anonymous -> 401 Unauthorized
    res_anon = client.get("/audit/")
    assert res_anon.status_code == 401
    assert "Not authenticated" in res_anon.json()["detail"]

    # 2. Operator -> 403 Forbidden
    res_op = client.get("/audit/", headers=operator_headers)
    assert res_op.status_code == 403
    assert "Operation not permitted" in res_op.json()["detail"]

    # 3. Technician -> 403 Forbidden
    res_tech = client.get("/audit/", headers=technician_headers)
    assert res_tech.status_code == 403
    assert "Operation not permitted" in res_tech.json()["detail"]

    # 4. Admin -> 200 OK
    res_admin = client.get("/audit/", headers=admin_headers)
    assert res_admin.status_code == 200
    assert isinstance(res_admin.json(), list)


# ======================================================================
# 5. MULTI-PHASE TELEMETRY FRESHNESS AND CLOCK SKEW TOLERANCE
# ======================================================================

def test_one_fresh_phase_cannot_mask_stale_phases(client, admin_headers, db):
    dev = Device(device_id="FRESH-STALE-DEV", name="Multi-Phase Test Unit", is_active=True)
    db.add(dev)
    db.commit()

    now = datetime.now(timezone.utc)
    fresh_time = now - timedelta(seconds=5)
    stale_time = now - timedelta(seconds=180)  # > 120s default offline window

    # Phase R is fresh (5s ago), but Phases Y and B are stale (180s ago)
    db.add(Telemetry(
        device_id=dev.id, phase="R", voltage=230.0, current=4.0, power=920.0,
        sampled_at=fresh_time, received_at=fresh_time, data_quality="GOOD",
        transmission_reason="SCHEDULED", source="REAL",
    ))
    db.add(Telemetry(
        device_id=dev.id, phase="Y", voltage=230.0, current=4.0, power=920.0,
        sampled_at=stale_time, received_at=stale_time, data_quality="GOOD",
        transmission_reason="SCHEDULED", source="REAL",
    ))
    db.add(Telemetry(
        device_id=dev.id, phase="B", voltage=230.0, current=4.0, power=920.0,
        sampled_at=stale_time, received_at=stale_time, data_quality="GOOD",
        transmission_reason="SCHEDULED", source="REAL",
    ))
    dev.last_seen_at = fresh_time
    db.commit()

    res = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res.status_code == 200
    # Must be Offline because Phases Y and B are stale!
    assert res.json()["system_status"] == "Offline"


def test_future_dated_telemetry_rejection_and_exclusion(client, admin_headers, ingest_headers, db):
    dev = Device(device_id="FUTURE-DEV", name="Future Skew Unit", is_active=True)
    db.add(dev)
    db.commit()

    # 1. Telemetry with timestamp far into the future (+300s > 60s tolerance) is rejected at ingestion
    far_future = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
    res_skew = client.post(
        "/telemetry/",
        json={
            "device_id": dev.id,
            "phase": "R",
            "voltage": 230.0,
            "current": 4.0,
            "power": 920.0,
            "sampled_at": far_future,
            "data_quality": "good",
        },
        headers=ingest_headers,
    )
    assert res_skew.status_code == 400
    assert "clock skew" in res_skew.json()["detail"].lower()

    # 2. Even if a future record exists in the DB, the live dashboard excludes it
    now = datetime.now(timezone.utc)
    future_db_time = now + timedelta(days=1)
    db.add(Telemetry(
        device_id=dev.id, phase="R", voltage=250.0, current=5.0, power=1250.0,
        sampled_at=future_db_time, received_at=now, data_quality="GOOD",
        transmission_reason="SCHEDULED", source="REAL",
    ))
    db.commit()

    # The future sample is excluded, so phase R is not considered populated from future
    res_dash = client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers)
    assert res_dash.status_code == 200
    assert "R" not in res_dash.json()["phases"]
    assert res_dash.json()["system_status"] == "Offline"


# ======================================================================
# 6. RELAY TRUTHFULNESS AND AUTHORIZATION ERROR PROPAGATION
# ======================================================================

def test_relay_command_rejection_and_hardware_truthfulness(
    client,
    operator_headers,
    admin_headers,
    db,
):
    dev = Device(device_id="RELAY-TRUTH-DEV", name="Relay Truth PMU", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(
        device_id=dev.id,
        relay_number=1,
        name="Phase R Feeder Contactor",
        gpio_pin=7,
        commanded_state=False,
        actual_state=None,
        is_on=False,
        is_active=True,
    )
    db.add(relay)
    db.commit()

    # 1. Operator attempts to toggle relay ON -> rejected with 403 Forbidden
    op_res = client.post(f"/relays/{relay.id}/on", headers=operator_headers)
    assert op_res.status_code == 403
    assert "Operation not permitted" in op_res.json()["detail"]

    # Verify state in DB remains untouched
    db.refresh(relay)
    assert relay.commanded_state is False
    assert relay.actual_state is None
    assert relay.is_on is False

    # 2. Administrator issues ON command -> accepted as command, but hardware_verified is False
    adm_res = client.post(f"/relays/{relay.id}/on", headers=admin_headers)
    assert adm_res.status_code == 200
    data = adm_res.json()
    assert data["status"] == "success"
    assert data["commanded_state"] is True
    assert data["is_on"] is True
    assert data["actual_state"] is None
    assert data["hardware_verified"] is False
    assert "awaiting physical contactor feedback" in data["message"]


# ======================================================================
# 7. ENDPOINT READ AUTHORIZATION MATRIX (STAGE 3A.2.2)
# ======================================================================

def test_read_endpoints_authorization_matrix(
    client,
    operator_headers,
    technician_headers,
    admin_headers,
    db,
):
    dev = Device(device_id="READ-AUTH-DEV", name="Read Auth PMU", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="Test Relay", gpio_pin=12, is_active=True)
    fault = Fault(
        device_id=dev.id,
        fault_type="OVERVOLTAGE",
        severity="warning",
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )
    db.add_all([relay, fault])
    db.flush()

    notif = Notification(
        fault_id=fault.id,
        title="Test Alert",
        message="Overvoltage alert",
        severity="warning",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    wo = WorkOrder(
        fault_id=fault.id,
        assigned_to="tech_tester",
        status="assigned",
        created_by="admin",
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([notif, wo])
    db.commit()

    # 1. Unauthenticated requests to sensitive read endpoints return 401 Unauthorized
    assert client.get("/relays/").status_code == 401
    assert client.get(f"/relays/{relay.id}").status_code == 401
    assert client.get("/faults/").status_code == 401
    assert client.get(f"/faults/{fault.id}").status_code == 401
    assert client.get("/notifications/").status_code == 401
    assert client.get("/notifications/unread-count").status_code == 401
    assert client.get("/maintenance/work-orders").status_code == 401
    assert client.get(f"/maintenance/work-orders/{wo.id}").status_code == 401

    # 2. Operator role:
    # - Permitted on relays, faults, notifications (returns 200)
    assert client.get("/relays/", headers=operator_headers).status_code == 200
    assert client.get(f"/relays/{relay.id}", headers=operator_headers).status_code == 200
    assert client.get("/faults/", headers=operator_headers).status_code == 200
    assert client.get(f"/faults/{fault.id}", headers=operator_headers).status_code == 200
    assert client.get("/notifications/", headers=operator_headers).status_code == 200
    assert client.get("/notifications/unread-count", headers=operator_headers).status_code == 200

    # - Forbidden on maintenance work orders (returns 403)
    wo_op_list = client.get("/maintenance/work-orders", headers=operator_headers)
    assert wo_op_list.status_code == 403
    assert any(msg in wo_op_list.json()["detail"] for msg in ("Operation not permitted", "Permission denied"))

    wo_op_detail = client.get(f"/maintenance/work-orders/{wo.id}", headers=operator_headers)
    assert wo_op_detail.status_code == 403
    assert any(msg in wo_op_detail.json()["detail"] for msg in ("Operation not permitted", "Permission denied"))

    # 3. Technician role:
    # - Permitted on relays, faults, notifications, and maintenance work orders (returns 200)
    assert client.get("/relays/", headers=technician_headers).status_code == 200
    assert client.get(f"/relays/{relay.id}", headers=technician_headers).status_code == 200
    assert client.get("/faults/", headers=technician_headers).status_code == 200
    assert client.get(f"/faults/{fault.id}", headers=technician_headers).status_code == 200
    assert client.get("/notifications/", headers=technician_headers).status_code == 200
    assert client.get("/notifications/unread-count", headers=technician_headers).status_code == 200
    assert client.get("/maintenance/work-orders", headers=technician_headers).status_code == 200
    assert client.get(f"/maintenance/work-orders/{wo.id}", headers=technician_headers).status_code == 200

    # 4. Admin role:
    # - Permitted on all endpoints (returns 200)
    assert client.get("/relays/", headers=admin_headers).status_code == 200
    assert client.get(f"/relays/{relay.id}", headers=admin_headers).status_code == 200
    assert client.get("/faults/", headers=admin_headers).status_code == 200
    assert client.get(f"/faults/{fault.id}", headers=admin_headers).status_code == 200
    assert client.get("/notifications/", headers=admin_headers).status_code == 200
    assert client.get("/notifications/unread-count", headers=admin_headers).status_code == 200
    assert client.get("/maintenance/work-orders", headers=admin_headers).status_code == 200
    assert client.get(f"/maintenance/work-orders/{wo.id}", headers=admin_headers).status_code == 200
    assert client.get("/audit/", headers=admin_headers).status_code == 200

    # 5. Telemetry & dashboard endpoints require authentication
    assert client.get(f"/dashboard/live?device_id={dev.id}").status_code == 401
    assert client.get(f"/telemetry/?device_id={dev.id}").status_code == 401
    assert client.get(f"/telemetry/latest?device_id={dev.id}").status_code == 401

    assert client.get(f"/dashboard/live?device_id={dev.id}", headers=admin_headers).status_code == 200
    assert client.get(f"/telemetry/?device_id={dev.id}", headers=admin_headers).status_code == 200
    assert client.get(f"/telemetry/latest?device_id={dev.id}", headers=admin_headers).status_code == 404

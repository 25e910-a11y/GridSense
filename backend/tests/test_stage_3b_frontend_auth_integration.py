from datetime import datetime, timedelta, timezone
from app.core.security import create_access_token, hash_password
from app.models.device import Device
from app.models.fault import Fault
from app.models.notification import Notification
from app.models.relay import Relay
from app.models.user import User
from app.models.work_order import WorkOrder


# ======================================================================
# 1. AUTH LOGIN CONTRACT & CREDENTIAL VALIDATION
# ======================================================================

def test_auth_login_contract_and_credential_validation(client, db):
    # Setup users for each role
    db.query(User).filter(User.username.in_(["stage3b_op", "stage3b_inactive"])).delete()
    db.commit()

    op_user = User(
        username="stage3b_op",
        password_hash=hash_password("ValidPassword123!"),
        role="operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    inactive_user = User(
        username="stage3b_inactive",
        password_hash=hash_password("ValidPassword123!"),
        role="operator",
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([op_user, inactive_user])
    db.commit()

    # 1. Successful login matching frontend LoginResponse schema
    res_ok = client.post(
        "/auth/login",
        json={"username": "stage3b_op", "password": "ValidPassword123!"},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["role"] == "operator"
    assert data["username"] == "stage3b_op"
    assert len(data["access_token"]) > 20

    # 2. Invalid password -> 401
    res_bad_pw = client.post(
        "/auth/login",
        json={"username": "stage3b_op", "password": "WrongPassword999!"},
    )
    assert res_bad_pw.status_code == 401
    assert "invalid credentials" in res_bad_pw.json()["detail"].lower()

    # 3. Non-existent username -> 401 (not 404, preventing account enumeration)
    res_bad_user = client.post(
        "/auth/login",
        json={"username": "non_existent_account_123", "password": "AnyPassword"},
    )
    assert res_bad_user.status_code == 401
    assert "invalid credentials" in res_bad_user.json()["detail"].lower()

    # 4. Inactive user -> 403 Forbidden
    res_inactive = client.post(
        "/auth/login",
        json={"username": "stage3b_inactive", "password": "ValidPassword123!"},
    )
    assert res_inactive.status_code == 403
    assert "inactive" in res_inactive.json()["detail"].lower()


# ======================================================================
# 2. SESSION RESTORATION & TOKEN INVALIDATION CONTRACT (/auth/me)
# ======================================================================

def test_auth_me_session_restoration_and_token_invalidation(client, operator_headers):
    # 1. Valid token returns UserProfileResponse
    res_me = client.get("/auth/me", headers=operator_headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["authenticated"] is True
    assert me_data["role"] == "operator"
    assert "username" in me_data

    # 2. Expired token -> 401
    expired_token = create_access_token(
        username="operator_tester",
        role="operator",
        expires_delta=timedelta(seconds=-30),
    )
    res_expired = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401
    assert "expired" in res_expired.json()["detail"].lower()

    # 3. Invalid / corrupted signature -> 401
    res_corrupted = client.get("/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert res_corrupted.status_code == 401
    assert "invalid token" in res_corrupted.json()["detail"].lower()

    # 4. Anonymous request -> 401
    res_anon = client.get("/auth/me")
    assert res_anon.status_code == 401
    assert "not authenticated" in res_anon.json()["detail"].lower()


# ======================================================================
# 3. COMPLETE ROLE-TO-ROUTE & ACTION RBAC MATRIX (STAGE 3B)
# ======================================================================

def test_stage_3b_complete_role_to_action_matrix(
    client,
    operator_headers,
    technician_headers,
    admin_headers,
    db,
):
    dev = Device(device_id="STAGE3B-RBAC-DEV", name="Stage 3B PMU", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="Feeder Contactor", gpio_pin=18, is_active=True, is_on=False)
    fault = Fault(
        device_id=dev.id,
        fault_type="UNDERVOLTAGE",
        severity="warning",
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )
    db.add_all([relay, fault])
    db.flush()

    wo = WorkOrder(
        fault_id=fault.id,
        assigned_to="tech_tester",
        status="assigned",
        created_by="Supervisor",
        created_at=datetime.now(timezone.utc),
    )
    notif = Notification(
        fault_id=fault.id,
        title="Undervoltage Warning",
        message="Phase R voltage low",
        severity="warning",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([wo, notif])
    db.commit()

    # --- ANONYMOUS VISITOR (All data endpoints protected) ---
    assert client.get(f"/dashboard/live?device_id={dev.id}").status_code == 401
    assert client.get(f"/telemetry/?device_id={dev.id}").status_code == 401
    assert client.get("/locations/colleges").status_code == 401
    assert client.get("/devices/").status_code == 401
    assert client.get("/relays/").status_code == 401
    assert client.get("/faults/").status_code == 401
    assert client.get("/notifications/").status_code == 401
    assert client.get("/maintenance/work-orders").status_code == 401
    assert client.get("/audit/").status_code == 401
    assert client.post(f"/relays/{relay.id}/on").status_code == 401

    # --- OPERATOR ROLE (Read-Only Monitoring) ---
    # Permitted reads
    assert client.get(f"/dashboard/live?device_id={dev.id}", headers=operator_headers).status_code == 200
    assert client.get(f"/telemetry/?device_id={dev.id}", headers=operator_headers).status_code == 200
    assert client.get("/locations/colleges", headers=operator_headers).status_code == 200
    assert client.get("/devices/", headers=operator_headers).status_code == 200
    assert client.get("/relays/", headers=operator_headers).status_code == 200
    assert client.get("/faults/", headers=operator_headers).status_code == 200
    assert client.get("/notifications/", headers=operator_headers).status_code == 200
    assert client.put(f"/notifications/{notif.id}/read", headers=operator_headers).status_code == 200

    # Forbidden actions for Operator (Strictly Read-Only)
    assert client.put(f"/faults/{fault.id}/acknowledge", headers=operator_headers).status_code == 403
    assert client.post(f"/relays/{relay.id}/on", headers=operator_headers).status_code == 403
    assert client.put(f"/faults/{fault.id}/rectify", params={"resolution": "Fixed"}, headers=operator_headers).status_code == 403
    assert client.get("/maintenance/work-orders", headers=operator_headers).status_code == 403
    assert client.post(f"/maintenance/work-orders/{wo.id}/attempts", json={"note": "Test attempt"}, headers=operator_headers).status_code == 403
    assert client.get("/audit/", headers=operator_headers).status_code == 403

    # --- TECHNICIAN ROLE ---
    # Fault must be acknowledged by Shift Lead or Admin before rectification
    adm_ack = client.put(f"/faults/{fault.id}/acknowledge", headers=admin_headers)
    assert adm_ack.status_code == 200

    # Permitted reads & actions
    assert client.get("/relays/", headers=technician_headers).status_code == 200
    assert client.get("/faults/", headers=technician_headers).status_code == 200
    assert client.get("/notifications/", headers=technician_headers).status_code == 200
    assert client.get("/maintenance/work-orders", headers=technician_headers).status_code == 200
    assert client.get(f"/maintenance/work-orders/{wo.id}", headers=technician_headers).status_code == 200
    assert client.post(f"/maintenance/work-orders/{wo.id}/attempts", json={"note": "Attempt by tech"}, headers=technician_headers).status_code == 200
    assert client.put(f"/faults/{fault.id}/rectify", params={"resolution": "Inspected transformer taps"}, headers=technician_headers).status_code == 200

    # Forbidden actions (Relay control and audit remain Admin only)
    assert client.post(f"/relays/{relay.id}/on", headers=technician_headers).status_code == 403
    assert client.get("/audit/", headers=technician_headers).status_code == 403

    # --- ADMINISTRATOR ROLE ---
    # Permitted on everything
    assert client.get("/audit/", headers=admin_headers).status_code == 200
    adm_relay = client.post(f"/relays/{relay.id}/on", headers=admin_headers)
    assert adm_relay.status_code == 200
    assert adm_relay.json()["hardware_verified"] is False  # truthful reporting


# ======================================================================
# 4. STAGE 3B.2 REMEDIATION CONTRACTS & TRUTHFULNESS
# ======================================================================

def test_stage_3b2_remediation_contracts(
    client,
    operator_headers,
    technician_headers,
    admin_headers,
    shift_incharge_headers,
    db,
):
    # 1. Device ingestion rejection & authentication truthfulness
    dev = Device(device_id="STAGE3B2-TEST-DEV", name="Stage 3B.2 Dev", is_active=True)
    db.add(dev)
    db.flush()

    telemetry_payload = {
        "device_id": dev.id,
        "phase": "R",
        "voltage": 230.5,
        "current": 4.1,
        "power": 945.0,
        "energy": 100.0,
        "power_factor": 0.98,
        "frequency": 50.0,
        "temperature": 34.0,
        "sampled_at": datetime.now(timezone.utc).isoformat(),
    }

    # Anonymous telemetry ingestion must reject with 401 (never simulate success)
    res_anon_ingest = client.post("/telemetry/", json=telemetry_payload)
    assert res_anon_ingest.status_code == 401

    # Authenticated operator ingestion succeeds
    res_auth_ingest = client.post("/telemetry/", json=telemetry_payload, headers=operator_headers)
    assert res_auth_ingest.status_code == 200
    assert res_auth_ingest.json()["status"] == "success"

    # 2. Operator work-order creation contract vs maintenance route restriction
    fault = Fault(
        device_id=dev.id,
        fault_type="OVERVOLTAGE",
        severity="fault",
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )
    db.add(fault)
    db.commit()

    # Operator is denied dispatching work order (read-only)
    res_op_wo = client.post(
        "/maintenance/work-orders",
        json={"fault_id": fault.id, "assigned_to": "tech_tester", "diagnosis": "Field inspection"},
        headers=operator_headers,
    )
    assert res_op_wo.status_code == 403

    # Shift In-Charge IS permitted to dispatch a work order on backend
    res_create_wo = client.post(
        "/maintenance/work-orders",
        json={"fault_id": fault.id, "assigned_to": "tech_tester", "diagnosis": "Field inspection"},
        headers=shift_incharge_headers,
    )
    assert res_create_wo.status_code == 200
    assert "work_order_id" in res_create_wo.json()

    # Operator is strictly forbidden from accessing /maintenance/work-orders (HTTP 403)
    res_op_list_wo = client.get("/maintenance/work-orders", headers=operator_headers)
    assert res_op_list_wo.status_code == 403

    # Technician is permitted to access /maintenance/work-orders (HTTP 200)
    res_tech_list_wo = client.get("/maintenance/work-orders", headers=technician_headers)
    assert res_tech_list_wo.status_code == 200

    # 3. Truthful empty telemetry state on newly registered device
    new_dev = Device(device_id="STAGE3B2-EMPTY-DEV", name="Empty Dev", is_active=True)
    db.add(new_dev)
    db.commit()

    # Unauthenticated request is rejected
    assert client.get(f"/telemetry/?device_id={new_dev.id}").status_code == 401
    assert client.get(f"/dashboard/live?device_id={new_dev.id}").status_code == 401

    # Empty telemetry listing returns empty list (does not synthesize points)
    res_hist = client.get(f"/telemetry/?device_id={new_dev.id}", headers=operator_headers)
    assert res_hist.status_code == 200
    assert res_hist.json() == []

    # Live dashboard for empty device returns Offline status and empty phases
    res_dash = client.get(f"/dashboard/live?device_id={new_dev.id}", headers=operator_headers)
    assert res_dash.status_code == 200
    assert res_dash.json()["system_status"] == "Offline"
    assert res_dash.json()["phases"] == {}


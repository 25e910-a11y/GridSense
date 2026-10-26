from datetime import datetime, timezone

from app.core.security import create_access_token, hash_password
from app.models.block import Block
from app.models.college import College
from app.models.device import Device
from app.models.fault import Fault
from app.models.floor import Floor
from app.models.relay import Relay
from app.models.telemetry import Telemetry
from app.models.user import User
from app.models.work_order import WorkOrder


def test_unauthenticated_requests_fail_on_all_data_endpoints(client, db):
    """
    Phase 2 A Requirement:
    Authentication is mandatory for all data access.
    All telemetry, history, fault, maintenance, relay, campus/device, audit endpoints
    must enforce authentication on the server and return 401 Unauthorized.
    """
    endpoints_401 = [
        "/dashboard/live?device_id=1",
        "/dashboard/summary",
        "/telemetry/",
        "/telemetry/latest?device_id=1",
        "/telemetry/latest-by-phase?device_id=1",
        "/locations/colleges",
        "/locations/blocks",
        "/locations/floors",
        "/devices/",
        "/devices/1",
        "/relays/",
        "/relays/1",
        "/faults/",
        "/faults/1",
        "/maintenance/work-orders",
        "/maintenance/work-orders/1",
        "/notifications/",
        "/notifications/unread-count",
        "/audit/",
        "/auth/users",
    ]
    for ep in endpoints_401:
        res = client.get(ep)
        assert res.status_code == 401, f"Expected 401 for unauthenticated GET {ep}, got {res.status_code}"


def test_shift_incharge_role_permissions(
    client,
    shift_incharge_headers,
    db,
):
    """
    Phase 2 B: Shift In-Charge
    - View monitoring and faults
    - Review alarms, acknowledge faults (200)
    - Coordinate and assign response work / work orders (200)
    - Denied relay controls (403) and user administration (403)
    """
    dev = Device(device_id="SHIFT-TEST-DEV", name="Substation Feeder", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="SSR-R", gpio_pin=7, is_active=True)
    fault = Fault(
        device_id=dev.id,
        fault_type="OVERCURRENT",
        severity="fault",
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )
    db.add_all([relay, fault])
    db.commit()

    # 1. Permitted reads
    assert client.get(f"/dashboard/live?device_id={dev.id}", headers=shift_incharge_headers).status_code == 200
    assert client.get("/faults/", headers=shift_incharge_headers).status_code == 200
    assert client.get("/devices/", headers=shift_incharge_headers).status_code == 200

    # 2. Permitted actions: Acknowledge alarm
    ack_res = client.put(f"/faults/{fault.id}/acknowledge", headers=shift_incharge_headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "success"

    # 3. Permitted actions: Create & assign work order to technician
    wo_res = client.post(
        "/maintenance/work-orders",
        json={
            "fault_id": fault.id,
            "assigned_to": "tech_tester",
            "diagnosis": "Check breaker contacts",
        },
        headers=shift_incharge_headers,
    )
    assert wo_res.status_code == 200
    assert "work_order_id" in wo_res.json()

    # 4. Denied actions: Relay command (403)
    relay_res = client.post(f"/relays/{relay.id}/on", headers=shift_incharge_headers)
    assert relay_res.status_code == 403

    # 5. Denied actions: User administration (403)
    user_res = client.get("/auth/users", headers=shift_incharge_headers)
    assert user_res.status_code == 403


def test_electrical_engineer_role_permissions(
    client,
    engineer_headers,
    db,
):
    """
    Phase 2 B: Electrical Engineer
    - Access detailed measurements, diagnostics, fault history
    - Manage technical fault-resolution workflow (rectify faults)
    - View and coordinate maintenance
    - Denied physical relay control (403) and user management (403)
    """
    dev = Device(device_id="ENG-TEST-DEV", name="Power Lab PMU", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="SSR-B", gpio_pin=9, is_active=True)
    fault = Fault(
        device_id=dev.id,
        fault_type="VOLTAGE_IMBALANCE",
        severity="fault",
        status="acknowledged",
        detected_at=datetime.now(timezone.utc),
    )
    db.add_all([relay, fault])
    db.flush()

    wo = WorkOrder(
        fault_id=fault.id,
        assigned_to="tech_tester",
        status="in_progress",
        created_by="engineer_tester",
        created_at=datetime.now(timezone.utc),
    )
    db.add(wo)
    db.commit()

    # 1. Permitted reads
    assert client.get(f"/dashboard/live?device_id={dev.id}", headers=engineer_headers).status_code == 200
    assert client.get("/faults/", headers=engineer_headers).status_code == 200
    assert client.get("/maintenance/work-orders", headers=engineer_headers).status_code == 200

    # 2. Permitted actions: Rectify fault with technical notes
    rect_res = client.put(
        f"/faults/{fault.id}/rectify",
        params={"resolution": "Phase balance restored by re-routing single-phase loads on feeder 2B."},
        headers=engineer_headers,
    )
    assert rect_res.status_code == 200

    # 3. Permitted actions: Update work order
    wo_update = client.put(
        f"/maintenance/work-orders/{wo.id}/status",
        json={"status": "restored", "diagnosis": "Loads rebalanced"},
        headers=engineer_headers,
    )
    assert wo_update.status_code == 200

    # 4. Denied actions: Relay actuation (403)
    assert client.post(f"/relays/{relay.id}/on", headers=engineer_headers).status_code == 403


def test_management_role_permissions(
    client,
    management_headers,
    db,
):
    """
    Phase 2 B: Management
    - High-level KPIs and summaries (GET /dashboard/summary)
    - Read-only across authorised locations
    - Denied relay commands (403), fault mutation (403), user admin (403)
    """
    dev = Device(device_id="MGMT-TEST-DEV", name="Main Feeder", is_active=True)
    db.add(dev)
    db.flush()

    relay = Relay(device_id=dev.id, relay_number=1, name="SSR-Y", gpio_pin=8, is_active=True)
    fault = Fault(
        device_id=dev.id,
        fault_type="OVERVOLTAGE",
        severity="fault",
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )
    db.add_all([relay, fault])
    db.commit()

    # 1. Permitted aggregate KPI summary
    summary_res = client.get("/dashboard/summary", headers=management_headers)
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert "total_devices" in data
    assert "open_faults_count" in data

    # 2. Permitted read-only monitoring
    assert client.get(f"/dashboard/live?device_id={dev.id}", headers=management_headers).status_code == 200
    assert client.get("/faults/", headers=management_headers).status_code == 200

    # 3. Denied mutations: Acknowledge fault (403)
    assert client.put(f"/faults/{fault.id}/acknowledge", headers=management_headers).status_code == 403

    # 4. Denied mutations: Rectify fault (403)
    assert client.put(f"/faults/{fault.id}/rectify", params={"resolution": "Management fix"}, headers=management_headers).status_code == 403

    # 5. Denied mutations: Create work order (403)
    assert client.post(
        "/maintenance/work-orders",
        json={"fault_id": fault.id, "assigned_to": "tech_tester"},
        headers=management_headers,
    ).status_code == 403

    # 6. Denied mutations: Relay commands (403)
    assert client.post(f"/relays/{relay.id}/on", headers=management_headers).status_code == 403


def test_technician_work_order_isolation(
    client,
    technician_headers,
    technician_user,
    admin_headers,
    db,
):
    """
    Phase 2 B & Phase 5 (Item 4):
    Users cannot change URL or resource ID to access another technician's work order.
    Technicians can only access and update work orders assigned to them.
    """
    dev = Device(device_id="TECH-ISO-DEV", name="Isolation Test Unit", is_active=True)
    db.add(dev)
    db.flush()

    fault1 = Fault(device_id=dev.id, fault_type="OVERCURRENT", severity="fault", status="detected", detected_at=datetime.now(timezone.utc))
    fault2 = Fault(device_id=dev.id, fault_type="UNDERVOLTAGE", severity="warning", status="detected", detected_at=datetime.now(timezone.utc))
    db.add_all([fault1, fault2])
    db.flush()

    # WO 1 is assigned to tech_tester (the current technician fixture)
    my_wo = WorkOrder(
        fault_id=fault1.id,
        assigned_to=technician_user.username,
        status="assigned",
        created_by="admin",
        created_at=datetime.now(timezone.utc),
    )
    # WO 2 is assigned to another technician (tech_other)
    other_wo = WorkOrder(
        fault_id=fault2.id,
        assigned_to="tech_other",
        status="assigned",
        created_by="admin",
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([my_wo, other_wo])
    db.commit()

    # 1. Listing work orders automatically filters to only my assigned work orders
    list_res = client.get("/maintenance/work-orders", headers=technician_headers)
    assert list_res.status_code == 200
    listed_ids = [order["id"] for order in list_res.json()]
    assert my_wo.id in listed_ids
    assert other_wo.id not in listed_ids

    # 2. Directly querying my own work order -> 200 OK
    assert client.get(f"/maintenance/work-orders/{my_wo.id}", headers=technician_headers).status_code == 200

    # 3. Directly querying another technician's work order by ID -> 403 Forbidden!
    other_get = client.get(f"/maintenance/work-orders/{other_wo.id}", headers=technician_headers)
    assert other_get.status_code == 403
    assert "Technicians may only view work orders assigned to their account" in other_get.json()["detail"]

    # 4. Attempting to add attempt note to another technician's work order -> 403 Forbidden!
    attempt_res = client.post(
        f"/maintenance/work-orders/{other_wo.id}/attempts",
        json={"note": "Hacked attempt"},
        headers=technician_headers,
    )
    assert attempt_res.status_code == 403

    # 5. Attempting to update status on another technician's work order -> 403 Forbidden!
    status_res = client.put(
        f"/maintenance/work-orders/{other_wo.id}/status",
        json={"status": "restored"},
        headers=technician_headers,
    )
    assert status_res.status_code == 403


def test_location_scoping_enforcement(
    client,
    db,
):
    """
    Phase 2 B & Phase 5 (Item 4):
    Users cannot access buildings/floors/devices outside account's authorized scope.
    """
    col = College(name="Tech Campus", code="TC-01")
    db.add(col)
    db.flush()

    block_a = Block(college_id=col.id, name="Block A - Administration", code="BLK-A")
    block_b = Block(college_id=col.id, name="Block B - Laboratories", code="BLK-B")
    db.add_all([block_a, block_b])
    db.flush()

    floor_a = Floor(block_id=block_a.id, floor_number=1, name="Admin Floor 1")
    floor_b = Floor(block_id=block_b.id, floor_number=1, name="Lab Floor 1")
    db.add_all([floor_a, floor_b])
    db.flush()

    dev_in_a = Device(device_id="DEV-A", name="Admin PMU", floor_id=floor_a.id, is_active=True)
    dev_in_b = Device(device_id="DEV-B", name="Lab PMU", floor_id=floor_b.id, is_active=True)
    db.add_all([dev_in_a, dev_in_b])
    db.flush()

    # User scoped to Block A only
    scoped_user = User(
        username="scoped_op_block_a",
        password_hash=hash_password("pw123"),
        role="operator",
        assigned_block_id=block_a.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(scoped_user)
    db.commit()

    token = create_access_token(scoped_user.username, scoped_user.role)
    scoped_headers = {"Authorization": f"Bearer {token}"}

    # 1. Access to device in assigned Block A -> 200 OK
    res_a = client.get(f"/dashboard/live?device_id={dev_in_a.id}", headers=scoped_headers)
    assert res_a.status_code == 200

    # 2. Access to device in Block B -> 403 Forbidden!
    res_b = client.get(f"/dashboard/live?device_id={dev_in_b.id}", headers=scoped_headers)
    assert res_b.status_code == 403
    assert "outside authorized operational location scope" in res_b.json()["detail"]

    # 3. Querying devices list returns only devices in Block A
    dev_list = client.get("/devices/", headers=scoped_headers).json()
    dev_ids = [d["id"] for d in dev_list]
    assert dev_in_a.id in dev_ids
    assert dev_in_b.id not in dev_ids


def test_unknown_role_fails_closed(client, db):
    """
    Phase 2 C: Fail closed if a user's role or permissions are missing, invalid or unknown.
    """
    bad_user = User(
        username="hacker_unknown_role",
        password_hash=hash_password("pw123"),
        role="nonexistent_alien_role",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(bad_user)
    db.commit()

    token = create_access_token(bad_user.username, bad_user.role)
    bad_headers = {"Authorization": f"Bearer {token}"}

    # Any permission-guarded endpoint fails closed with 403
    assert client.get("/maintenance/work-orders", headers=bad_headers).status_code == 403
    assert client.get("/audit/", headers=bad_headers).status_code == 403
    assert client.put("/faults/1/acknowledge", headers=bad_headers).status_code == 403

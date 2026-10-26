def test_work_order_workflow(
    client,
    admin_headers,
    technician_headers,
    technician_user,
    operator_headers,
    shift_incharge_headers,
):
    # 1. Setup a device (requires admin) and fault (requires technician/admin)
    dev_res = client.post(
        "/devices/",
        params={"device_id": "MAINT-DEV-01", "name": "Pump PMU"},
        headers=admin_headers,
    )
    assert dev_res.status_code == 200
    device_id = dev_res.json()["device_id"]

    fault_res = client.post(
        "/faults/",
        params={
            "device_id": device_id,
            "fault_type": "OVERCURRENT",
            "severity": "fault",
            "phase": "Y",
            "description": "Current spiked to 45A",
            "measured_value": 45.0,
            "expected_value": 32.0,
            "unit": "A",
        },
        headers=technician_headers,
    )
    assert fault_res.status_code == 200
    fault_id = fault_res.json()["fault_id"]

    # 2. Operator is DENIED work order creation (Read-only role invariant)
    op_denied = client.post(
        "/maintenance/work-orders",
        json={
            "fault_id": fault_id,
            "assigned_to": technician_user.username,
            "diagnosis": "Possible short in motor winding",
            "created_by": "Operator Dave",
        },
        headers=operator_headers,
    )
    assert op_denied.status_code == 403

    # Shift In-Charge / Admin IS PERMITTED to coordinate and assign work orders
    wo_res = client.post(
        "/maintenance/work-orders",
        json={
            "fault_id": fault_id,
            "assigned_to": technician_user.username,
            "diagnosis": "Possible short in motor winding",
            "created_by": "Shift Lead Sarah",
        },
        headers=shift_incharge_headers,
    )
    assert wo_res.status_code == 200
    wo_id = wo_res.json()["work_order_id"]

    # 3. List work orders (Technician gets their assigned work orders)
    list_res = client.get("/maintenance/work-orders", headers=technician_headers)
    assert list_res.status_code == 200
    orders = list_res.json()
    assert len(orders) >= 1
    assert orders[0]["id"] == wo_id
    assert orders[0]["assigned_to"] == technician_user.username
    assert orders[0]["status"] == "assigned"

    # 4. Add attempt (Assigned technician permitted; transitions status to in_progress)
    attempt_res = client.post(
        f"/maintenance/work-orders/{wo_id}/attempts",
        json={"note": "Inspected motor enclosure and tested insulation resistance.", "created_by": technician_user.username},
        headers=technician_headers,
    )
    assert attempt_res.status_code == 200
    assert attempt_res.json()["order_status"] == "in_progress"

    # 5. Get work order details (Assigned technician permitted)
    detail_res = client.get(f"/maintenance/work-orders/{wo_id}", headers=technician_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "in_progress"
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["note"] == "Inspected motor enclosure and tested insulation resistance."

    # 6. Mark restored (Assigned technician permitted)
    status_res = client.put(
        f"/maintenance/work-orders/{wo_id}/status",
        json={"status": "restored", "diagnosis": "Replaced corroded terminal connector.", "actor": technician_user.username},
        headers=technician_headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "restored"

    # 7. Close work order (Admin or Shift In-Charge permitted)
    close_res = client.put(
        f"/maintenance/work-orders/{wo_id}/status",
        json={"status": "closed", "actor": "Supervisor Dave"},
        headers=admin_headers,
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "closed"

    # 8. Check that fault status is now rectified (Authenticated permitted)
    fault_check = client.get(f"/faults/{fault_id}", headers=technician_headers)
    assert fault_check.status_code == 200
    assert fault_check.json()["status"] == "rectified"

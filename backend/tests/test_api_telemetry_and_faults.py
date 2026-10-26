from datetime import datetime, timezone


def test_device_telemetry_and_fault_lifecycle(
    client,
    admin_headers,
    ingest_headers,
    operator_headers,
    technician_headers,
):
    # 1. Create College, Block, Floor (requires Admin)
    college_res = client.post(
        "/locations/colleges",
        params={"name": "Engineering College", "code": "ENG"},
        headers=admin_headers,
    )
    assert college_res.status_code == 200
    college_id = college_res.json()["college_id"]

    block_res = client.post(
        "/locations/blocks",
        params={"college_id": college_id, "name": "Electrical Block"},
        headers=admin_headers,
    )
    assert block_res.status_code == 200
    block_id = block_res.json()["block_id"]

    floor_res = client.post(
        "/locations/floors",
        params={"block_id": block_id, "floor_number": 1, "name": "Ground Floor"},
        headers=admin_headers,
    )
    assert floor_res.status_code == 200
    floor_id = floor_res.json()["floor_id"]

    # 2. Register a Device (requires Admin)
    dev_res = client.post(
        "/devices/",
        params={
            "device_id": "TEST-DEVICE-01",
            "name": "Main Incomer PMU",
            "floor_id": floor_id,
            "location": "Substation Panel",
            "firmware_version": "1.0.0",
        },
        headers=admin_headers,
    )
    assert dev_res.status_code == 200
    device_db_id = dev_res.json()["device_id"]

    # 3. Post Normal Telemetry for 3 Phases (requires Ingest Key)
    now_iso = datetime.now(timezone.utc).isoformat()
    for phase in ("R", "Y", "B"):
        res = client.post(
            "/telemetry/",
            json={
                "device_id": device_db_id,
                "phase": phase,
                "voltage": 230.0,
                "current": 5.0,
                "power": 1150.0,
                "energy": 10.0,
                "frequency": 50.0,
                "power_factor": 0.95,
                "temperature": 32.0,
                "sampled_at": now_iso,
                "source": "REAL",
                "transmission_reason": "SCHEDULED",
                "data_quality": "good",
            },
            headers=ingest_headers,
        )
        assert res.status_code == 200
        assert res.json()["faults_created"] == 0

    # 4. Check Live Dashboard: Unauthenticated returns 401; Authenticated returns 200
    unauth_dash = client.get(f"/dashboard/live?device_id={device_db_id}")
    assert unauth_dash.status_code == 401

    dash_res = client.get(f"/dashboard/live?device_id={device_db_id}", headers=operator_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["system_status"] == "Normal"
    assert "R" in dash_data["phases"]
    assert "Y" in dash_data["phases"]
    assert "B" in dash_data["phases"]
    assert len(dash_data["open_faults"]) == 0

    # 5. Send an Overvoltage anomaly on phase R (280V > 230 * 1.10 = 253V)
    fault_res = client.post(
        "/telemetry/",
        json={
            "device_id": device_db_id,
            "phase": "R",
            "voltage": 280.0,
            "current": 5.0,
            "power": 1400.0,
            "frequency": 50.0,
            "power_factor": 0.95,
            "temperature": 35.0,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "source": "REAL",
            "transmission_reason": "SCHEDULED",
            "data_quality": "good",
        },
        headers=ingest_headers,
    )
    assert fault_res.status_code == 200
    assert fault_res.json()["faults_created"] >= 1
    finding_types = [f["fault_type"] for f in fault_res.json()["findings"]]
    assert "OVERVOLTAGE" in finding_types

    # 6. Check Dashboard -> Status should now reflect warning/fault
    dash_res2 = client.get(f"/dashboard/live?device_id={device_db_id}", headers=operator_headers)
    assert dash_res2.status_code == 200
    dash_data2 = dash_res2.json()
    assert dash_data2["system_status"] in {"Warning", "Fault"}
    assert len(dash_data2["open_faults"]) >= 1
    fault_item = dash_data2["open_faults"][0]
    fault_id = fault_item["id"]

    # 7. Acknowledge fault: Operator is read-only (403); Admin/Shift In-Charge permitted (200)
    op_ack = client.put(
        f"/faults/{fault_id}/acknowledge",
        headers=operator_headers,
    )
    assert op_ack.status_code == 403

    ack_res = client.put(
        f"/faults/{fault_id}/acknowledge",
        params={"acknowledged_by": "Shift Lead Dave"},
        headers=admin_headers,
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "success"

    # 8. Rectify fault (Technician permitted)
    rect_res = client.put(
        f"/faults/{fault_id}/rectify",
        params={"resolution": "Tap changer adjusted on transformer"},
        headers=technician_headers,
    )
    assert rect_res.status_code == 200
    assert rect_res.json()["status"] == "success"

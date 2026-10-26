def test_notifications_and_audit_lifecycle(
    client,
    admin_headers,
    ingest_headers,
    operator_headers,
):
    # 1. Trigger an event that writes notifications and audit (register a technician via admin)
    reg = client.post(
        "/auth/register",
        json={"username": "audituser", "password": "password123", "role": "technician"},
        headers=admin_headers,
    )
    assert reg.status_code == 200

    # Verify audit log was created (Admin authorized)
    audit_res = client.get("/audit/", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert any(log["action"] == "register" for log in logs)


    # 2. Trigger a telemetry fault to generate a notification (requires admin for device, ingest for telemetry)
    dev_res = client.post(
        "/devices/",
        params={"device_id": "NOTIF-DEV-01", "name": "Compressor Panel"},
        headers=admin_headers,
    )
    assert dev_res.status_code == 200
    device_id = dev_res.json()["device_id"]

    # Post an overvoltage sample (280V)
    res = client.post(
        "/telemetry/",
        json={
            "device_id": device_id,
            "phase": "B",
            "voltage": 280.0,
            "current": 4.0,
            "power": 1120.0,
            "sampled_at": "2026-09-30T17:30:00Z",
            "data_quality": "good",
        },
        headers=ingest_headers,
    )
    assert res.status_code == 200

    # 3. Check notifications (Authenticated permitted)
    notif_res = client.get("/notifications/", headers=operator_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]
    assert notifs[0]["is_read"] is False

    # 4. Check unread count (Authenticated permitted)
    count_res = client.get("/notifications/unread-count", headers=operator_headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] >= 1

    # 5. Mark single notification as read (Authenticated)
    read_res = client.put(f"/notifications/{notif_id}/read", headers=operator_headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 6. Mark all as read (Authenticated)
    read_all_res = client.put("/notifications/read-all", headers=operator_headers)
    assert read_all_res.status_code == 200

    count_res2 = client.get("/notifications/unread-count", headers=operator_headers)
    assert count_res2.status_code == 200
    assert count_res2.json()["unread_count"] == 0

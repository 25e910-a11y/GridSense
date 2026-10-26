from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.device import Device
from app.models.fault import Fault
from app.models.telemetry import Telemetry

OPEN_STATUSES = ("detected", "acknowledged")


def touch_device(device: Device) -> None:
    device.last_seen_at = datetime.now(timezone.utc)


def device_health(db: Session, device: Device) -> dict:
    now = datetime.now(timezone.utc)
    latest = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device.id)
        .order_by(Telemetry.sampled_at.desc())
        .first()
    )
    open_faults = (
        db.query(Fault)
        .filter(
            Fault.device_id == device.id,
            Fault.status.in_(OPEN_STATUSES),
        )
        .all()
    )

    sensor_fault = any(fault.category == "sensor_communication" for fault in open_faults)
    electrical_fault = any(
        fault.category == "electrical" and fault.severity == "fault"
        for fault in open_faults
    )
    warning = bool(open_faults)

    last_seen = device.last_seen_at
    stale = True
    if last_seen is not None:
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        stale = now - last_seen > timedelta(seconds=settings.DEVICE_OFFLINE_SECONDS)

    if not device.is_active:
        status = "offline"
    elif stale and latest is None:
        status = "offline"
    elif stale:
        status = "offline"
    elif sensor_fault:
        status = "error"
    elif electrical_fault:
        status = "error"
    elif warning:
        status = "warning"
    else:
        status = "online"

    return {
        "device_id": device.id,
        "name": device.name,
        "is_active": device.is_active,
        "status": status,
        "last_seen_at": device.last_seen_at,
        "latest_sampled_at": latest.sampled_at if latest else None,
        "open_fault_count": len(open_faults),
    }

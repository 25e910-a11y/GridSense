from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    Permission,
    get_current_user,
    has_permission,
    normalize_role,
    require_any_authenticated,
    validate_device_access,
)
from app.db.database import get_db
from app.models.device import Device
from app.models.fault import Fault
from app.models.floor import Floor
from app.models.telemetry import Telemetry
from app.models.user import User

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

OPEN_STATUSES = ("detected", "acknowledged")


@router.get("/live")
def get_live_dashboard(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = validate_device_access(device_id, user=current_user, db=db)

    now_utc = datetime.now(timezone.utc)
    max_allowed_time = now_utc + timedelta(seconds=settings.CLOCK_SKEW_TOLERANCE_SECONDS)

    phases = {}
    for phase in ("R", "Y", "B"):
        row = (
            db.query(Telemetry)
            .filter(
                Telemetry.device_id == device_id,
                Telemetry.phase == phase,
                Telemetry.sampled_at <= max_allowed_time,
            )
            .order_by(Telemetry.sampled_at.desc())
            .first()
        )
        if row is not None:
            phases[phase] = {
                "voltage": row.voltage,
                "current": row.current,
                "power": row.power,
                "energy": row.energy,
                "power_factor": row.power_factor,
                "frequency": row.frequency,
                "temperature": row.temperature,
                "data_quality": row.data_quality,
                "sampled_at": row.sampled_at,
                "source": row.source,
            }

    open_faults = (
        db.query(Fault)
        .filter(
            Fault.device_id == device_id,
            Fault.status.in_(OPEN_STATUSES),
        )
        .order_by(Fault.detected_at.desc())
        .all()
    )

    system_status = _calculate_system_status(device, phases, open_faults)

    return {
        "device_id": device.id,
        "device_name": device.name,
        "is_active": device.is_active,
        "system_status": system_status,
        "phases": phases,
        "open_faults": [
            {
                "id": fault.id,
                "fault_type": fault.fault_type,
                "category": fault.category,
                "severity": fault.severity,
                "phase": fault.phase,
                "status": fault.status,
                "measured_value": fault.measured_value,
                "expected_value": fault.expected_value,
                "unit": fault.unit,
                "description": fault.description,
                "detected_at": fault.detected_at,
            }
            for fault in open_faults
        ],
    }


@router.get("/summary")
def get_management_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    High-level operational overview & KPI metrics for Management, Engineers, and Administrators.
    Strictly scoped to the requesting user's assigned location permissions.
    """
    dev_query = db.query(Device)
    if current_user.assigned_block_id is not None:
        valid_floor_ids = [f.id for f in db.query(Floor.id).filter(Floor.block_id == current_user.assigned_block_id).all()]
        dev_query = dev_query.filter(Device.floor_id.in_(valid_floor_ids))
    elif current_user.assigned_floor_id is not None:
        dev_query = dev_query.filter(Device.floor_id == current_user.assigned_floor_id)

    devices = dev_query.all()
    device_ids = [d.id for d in devices]

    total_devices = len(devices)
    active_devices = sum(1 for d in devices if d.is_active)

    now_utc = datetime.now(timezone.utc)
    online_devices = 0
    for d in devices:
        if d.is_active and d.last_seen_at:
            ts = d.last_seen_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (now_utc - ts).total_seconds() <= settings.DEVICE_OFFLINE_SECONDS:
                online_devices += 1

    # Unresolved faults across scoped devices
    faults_query = db.query(Fault).filter(Fault.status.in_(OPEN_STATUSES))
    if device_ids:
        faults_query = faults_query.filter(Fault.device_id.in_(device_ids))
    else:
        faults_query = faults_query.filter(False)

    all_open_faults = faults_query.all()
    critical_faults = sum(1 for f in all_open_faults if f.severity == "fault")
    warning_faults = sum(1 for f in all_open_faults if f.severity == "warning")

    # Aggregate telemetry metrics across scoped devices
    total_active_power = 0.0
    total_energy_kwh = 0.0
    for d_id in device_ids:
        for phase in ("R", "Y", "B"):
            latest = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == d_id, Telemetry.phase == phase)
                .order_by(Telemetry.sampled_at.desc())
                .first()
            )
            if latest:
                total_active_power += (latest.power or 0.0)
                if latest.energy and latest.energy > total_energy_kwh:
                    total_energy_kwh = max(total_energy_kwh, latest.energy)

    return {
        "timestamp": now_utc,
        "scoped_block_id": current_user.assigned_block_id,
        "scoped_floor_id": current_user.assigned_floor_id,
        "total_devices": total_devices,
        "active_devices": active_devices,
        "online_devices": online_devices,
        "offline_devices": total_devices - online_devices,
        "open_faults_count": len(all_open_faults),
        "critical_faults_count": critical_faults,
        "warning_faults_count": warning_faults,
        "total_active_power_watts": round(total_active_power, 2),
        "total_energy_kwh": round(total_energy_kwh, 2),
    }


def _calculate_system_status(
    device: Device,
    phases: dict,
    open_faults: list[Fault],
) -> str:
    # 1. Device must be active
    if not device.is_active:
        return "Offline"

    # 2. Check complete 3-phase telemetry presence (R, Y, and B)
    if len(phases) < 3 or not all(p in phases for p in ("R", "Y", "B")):
        return "Offline"

    # 3. Check for stale or future-skewed telemetry on each phase individually
    now_utc = datetime.now(timezone.utc)
    max_allowed_future = now_utc + timedelta(seconds=settings.CLOCK_SKEW_TOLERANCE_SECONDS)

    for phase_key in ("R", "Y", "B"):
        p_data = phases.get(phase_key)
        if not p_data:
            return "Offline"
        ts = p_data.get("sampled_at")
        if ts is None:
            return "Offline"
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Reject any sample exceeding future skew tolerance
        if ts > max_allowed_future:
            return "Offline"

        # Check freshness: each phase must be within DEVICE_OFFLINE_SECONDS
        age_seconds = (now_utc - ts).total_seconds()
        if age_seconds > settings.DEVICE_OFFLINE_SECONDS:
            return "Offline"

    # Also verify device last_seen_at
    if device.last_seen_at:
        dev_ts = device.last_seen_at
        if dev_ts.tzinfo is None:
            dev_ts = dev_ts.replace(tzinfo=timezone.utc)
        if (now_utc - dev_ts).total_seconds() > settings.DEVICE_OFFLINE_SECONDS:
            return "Offline"

    # 4. Device is online and streaming fresh data across all phases: evaluate faults
    if any(fault.category == "sensor_communication" for fault in open_faults):
        if any(fault.severity == "fault" for fault in open_faults):
            return "Fault"
        return "Sensor/Communication Error"

    if any(fault.severity == "fault" for fault in open_faults):
        return "Fault"

    if open_faults:
        return "Warning"

    return "Normal"

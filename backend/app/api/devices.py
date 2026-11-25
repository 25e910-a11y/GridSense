from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin, validate_device_access
from app.db.database import get_db
from app.models.device import Device
from app.models.floor import Floor
from app.models.user import User
from app.core.config import settings
from app.services.audit import write_audit
from app.services.device_config import (
    ALERT_MODES,
    OVERRIDABLE_LIMITS,
    clean_limits,
    hash_ingest_key,
    new_ingest_key,
    thresholds_for_device,
)

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)


def device_out(device: Device) -> dict[str, Any]:
    """Device fields for API responses. The ingest key hash is never returned."""
    return {
        "id": device.id,
        "device_id": device.device_id,
        "name": device.name,
        "floor_id": device.floor_id,
        "location": device.location,
        "firmware_version": device.firmware_version,
        "is_active": device.is_active,
        "last_seen_at": device.last_seen_at,
        "alert_mode": device.alert_mode,
        "alarm_limits": clean_limits(device.alarm_limits),
        "has_own_ingest_key": bool(device.ingest_key),
    }


class DeviceLimitsUpdate(BaseModel):
    # Limit name -> value. A value of null removes that override.
    limits: dict[str, float | None] = Field(default_factory=dict)
    alert_mode: str | None = None


@router.post("/")
def create_device(
    device_id: str,
    name: str,
    floor_id: int | None = None,
    location: str | None = None,
    firmware_version: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(Device).filter(
        Device.device_id == device_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already exists",
        )

    if floor_id is not None:
        floor = db.get(Floor, floor_id)
        if floor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Floor not found",
            )

    device = Device(
        device_id=device_id,
        name=name,
        floor_id=floor_id,
        location=location,
        firmware_version=firmware_version,
        is_active=True,
    )

    db.add(device)
    db.flush()

    write_audit(
        db,
        actor=current_user.username,
        action="create_device",
        entity_type="device",
        entity_id=device.id,
        detail=f"Created device '{device.name}' ({device.device_id}) at floor {floor_id}",
    )

    db.commit()
    db.refresh(device)

    return {
        "status": "success",
        "message": "Device created",
        "device_id": device.id,
    }


@router.get("/")
def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Device)

    if current_user.assigned_block_id is not None:
        valid_floor_ids = [f.id for f in db.query(Floor.id).filter(Floor.block_id == current_user.assigned_block_id).all()]
        query = query.filter(Device.floor_id.in_(valid_floor_ids))
    elif current_user.assigned_floor_id is not None:
        query = query.filter(Device.floor_id == current_user.assigned_floor_id)

    return [
        device_out(device)
        for device in query.order_by(Device.id).all()
    ]


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = validate_device_access(device_id, user=current_user, db=db)
    return device_out(device)


@router.put("/{device_id}")
def update_device(
    device_id: int,
    name: str | None = None,
    floor_id: int | None = None,
    location: str | None = None,
    firmware_version: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.get(Device, device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if floor_id is not None:
        floor = db.get(Floor, floor_id)
        if floor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Floor not found",
            )
        device.floor_id = floor_id

    if name is not None:
        device.name = name

    if location is not None:
        device.location = location

    if firmware_version is not None:
        device.firmware_version = firmware_version

    if is_active is not None:
        device.is_active = is_active

    write_audit(
        db,
        actor=current_user.username,
        action="update_device",
        entity_type="device",
        entity_id=device.id,
        detail=f"Updated device {device.id} properties",
    )

    db.commit()
    db.refresh(device)

    return {
        "status": "success",
        "message": "Device updated",
        "device_id": device.id,
    }


@router.get("/{device_id}/limits")
def get_device_limits(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = validate_device_access(device_id, user=current_user, db=db)
    return {
        "device_id": device.id,
        "alert_mode": device.alert_mode,
        "overrides": clean_limits(device.alarm_limits),
        "effective": asdict(thresholds_for_device(settings, device)),
    }


@router.put("/{device_id}/limits")
def update_device_limits(
    device_id: int,
    payload: DeviceLimitsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    unknown = sorted(set(payload.limits) - set(OVERRIDABLE_LIMITS))
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown limit(s): {', '.join(unknown)}. Allowed: {', '.join(OVERRIDABLE_LIMITS)}",
        )

    bad = sorted(name for name, value in payload.limits.items() if value is not None and value <= 0)
    if bad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limits must be greater than zero: {', '.join(bad)}",
        )

    if payload.alert_mode is not None:
        mode = payload.alert_mode.strip().lower()
        if mode not in ALERT_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"alert_mode must be one of: {', '.join(ALERT_MODES)}",
            )
        device.alert_mode = mode

    merged = clean_limits(device.alarm_limits)
    for name, value in payload.limits.items():
        if value is None:
            merged.pop(name, None)
        else:
            merged[name] = float(value)
    device.alarm_limits = merged or None

    write_audit(
        db,
        actor=current_user.username,
        action="update_device_limits",
        entity_type="device",
        entity_id=device.id,
        detail=f"Alert mode {device.alert_mode}; overrides {merged or 'none'}",
    )

    db.commit()
    db.refresh(device)

    return {
        "status": "success",
        "device_id": device.id,
        "alert_mode": device.alert_mode,
        "overrides": clean_limits(device.alarm_limits),
        "effective": asdict(thresholds_for_device(settings, device)),
    }


@router.post("/{device_id}/ingest-key")
def rotate_device_ingest_key(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create (or replace) this device's own ingest key.

    The plain key is returned once, here, to be flashed into the node.
    Only its hash is stored. Calling this again revokes the old key.
    """
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    key = new_ingest_key()
    replaced = bool(device.ingest_key)
    device.ingest_key = hash_ingest_key(key)

    write_audit(
        db,
        actor=current_user.username,
        action="rotate_device_ingest_key",
        entity_type="device",
        entity_id=device.id,
        detail=("Replaced" if replaced else "Created") + " device ingest key",
    )

    db.commit()

    return {
        "status": "success",
        "device_id": device.id,
        "ingest_key": key,
        "message": "Store this key in the node now. It will not be shown again.",
    }

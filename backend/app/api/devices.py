from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin, validate_device_access
from app.db.database import get_db
from app.models.device import Device
from app.models.floor import Floor
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)


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

    return (
        query
        .order_by(Device.id)
        .all()
    )


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = validate_device_access(device_id, user=current_user, db=db)
    return device


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

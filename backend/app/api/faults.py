from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    Permission,
    get_current_user,
    require_permission,
    require_technician_or_admin,
    validate_device_access,
)
from app.db.database import get_db
from app.models.device import Device
from app.models.fault import Fault
from app.models.floor import Floor
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(
    prefix="/faults",
    tags=["Faults"],
)


@router.post("/")
def create_fault(
    device_id: int,
    fault_type: str,
    severity: str = "warning",
    phase: str | None = None,
    description: str | None = None,
    category: str = "electrical",
    measured_value: float | None = None,
    expected_value: float | None = None,
    unit: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_technician_or_admin),
):
    device = validate_device_access(device_id, user=current_user, db=db)

    fault = Fault(
        device_id=device.id,
        phase=phase,
        fault_type=fault_type,
        severity=severity,
        description=description,
        category=category,
        measured_value=measured_value,
        expected_value=expected_value,
        unit=unit,
        status="detected",
        detected_at=datetime.now(timezone.utc),
    )

    db.add(fault)
    db.flush()

    write_audit(
        db,
        actor=current_user.username,
        action="create_fault",
        entity_type="fault",
        entity_id=fault.id,
        detail=f"Recorded fault '{fault_type}' ({severity}) on device {device_id}",
    )

    db.commit()
    db.refresh(fault)

    return {
        "status": "success",
        "message": "Fault recorded",
        "fault_id": fault.id,
    }


@router.get("/")
def get_faults(
    device_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Fault)

    if device_id is not None:
        validate_device_access(device_id, user=current_user, db=db)
        query = query.filter(Fault.device_id == device_id)
    else:
        # Filter faults by user's assigned location scope
        if current_user.assigned_block_id is not None:
            valid_floor_ids = [f.id for f in db.query(Floor.id).filter(Floor.block_id == current_user.assigned_block_id).all()]
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id.in_(valid_floor_ids)).all()]
            query = query.filter(Fault.device_id.in_(valid_dev_ids))
        elif current_user.assigned_floor_id is not None:
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id == current_user.assigned_floor_id).all()]
            query = query.filter(Fault.device_id.in_(valid_dev_ids))

    if status_filter is not None:
        query = query.filter(Fault.status == status_filter)

    return (
        query
        .order_by(Fault.detected_at.desc())
        .all()
    )


@router.get("/{fault_id}")
def get_fault(
    fault_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fault = db.get(Fault, fault_id)

    if fault is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fault not found",
        )

    validate_device_access(fault.device_id, user=current_user, db=db)
    return fault


@router.put("/{fault_id}/acknowledge")
def acknowledge_fault(
    fault_id: int,
    acknowledged_by: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ACKNOWLEDGE_FAULTS)),
):
    fault = db.get(Fault, fault_id)

    if fault is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fault not found",
        )

    validate_device_access(fault.device_id, user=current_user, db=db)

    if fault.status != "detected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fault is not in detected state",
        )

    actor_str = acknowledged_by.strip() if acknowledged_by and acknowledged_by.strip() else current_user.username
    fault.status = "acknowledged"
    fault.acknowledged_at = datetime.now(timezone.utc)
    fault.acknowledged_by = actor_str

    write_audit(
        db,
        actor=current_user.username,
        action="acknowledge_fault",
        entity_type="fault",
        entity_id=fault.id,
        detail=f"Acknowledged fault {fault.id} ({fault.fault_type}) by {actor_str}",
    )

    db.commit()
    db.refresh(fault)

    return {
        "status": "success",
        "message": "Fault acknowledged",
        "fault_id": fault.id,
    }


@router.put("/{fault_id}/rectify")
def rectify_fault(
    fault_id: int,
    resolution: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RECTIFY_FAULTS)),
):
    fault = db.get(Fault, fault_id)

    if fault is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fault not found",
        )

    validate_device_access(fault.device_id, user=current_user, db=db)

    if fault.status != "acknowledged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fault must be acknowledged before rectification",
        )

    fault.status = "rectified"
    fault.rectified_at = datetime.now(timezone.utc)
    fault.resolution = resolution

    write_audit(
        db,
        actor=current_user.username,
        action="rectify_fault",
        entity_type="fault",
        entity_id=fault.id,
        detail=f"Rectified fault {fault.id}: {resolution}",
    )

    db.commit()
    db.refresh(fault)

    return {
        "status": "success",
        "message": "Fault rectified",
        "fault_id": fault.id,
    }

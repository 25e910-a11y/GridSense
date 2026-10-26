from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import (
    Permission,
    Role,
    get_current_user,
    normalize_role,
    require_permission,
    validate_device_access,
)
from app.db.database import get_db
from app.models.fault import Fault
from app.models.user import User
from app.models.work_order import WorkAttempt, WorkOrder
from app.services.audit import write_audit

router = APIRouter(
    prefix="/maintenance",
    tags=["Maintenance"],
)

VALID_STATUSES = {"assigned", "in_progress", "restored", "closed"}


class WorkOrderCreate(BaseModel):
    fault_id: int
    assigned_to: str = Field(min_length=1, max_length=100)
    diagnosis: str | None = None
    created_by: str | None = Field(default=None, max_length=100)


class WorkAttemptCreate(BaseModel):
    note: str = Field(min_length=1)
    created_by: str | None = Field(default=None, max_length=100)


class WorkOrderStatusUpdate(BaseModel):
    status: str
    diagnosis: str | None = None
    actor: str | None = Field(default=None, max_length=100)


@router.post("/work-orders")
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CREATE_WORK_ORDERS)),
):
    fault = db.get(Fault, payload.fault_id)
    if fault is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fault not found",
        )

    validate_device_access(fault.device_id, user=current_user, db=db)

    now = datetime.now(timezone.utc)
    creator = payload.created_by or current_user.username
    work_order = WorkOrder(
        fault_id=payload.fault_id,
        assigned_to=payload.assigned_to,
        status="assigned",
        diagnosis=payload.diagnosis,
        created_by=creator,
        created_at=now,
    )
    db.add(work_order)

    # If the fault is in detected state, acknowledge it as it is now assigned
    if fault.status == "detected":
        fault.status = "acknowledged"
        fault.acknowledged_at = now
        fault.acknowledged_by = payload.assigned_to

    write_audit(
        db,
        actor=current_user.username,
        action="create_work_order",
        entity_type="work_order",
        detail=f"Assigned fault {payload.fault_id} to {payload.assigned_to}",
    )

    db.commit()
    db.refresh(work_order)

    return {
        "status": "success",
        "message": "Work order created",
        "work_order_id": work_order.id,
    }


@router.get("/work-orders")
def list_work_orders(
    fault_id: int | None = None,
    assigned_to: str | None = None,
    status_filter: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_WORK_ORDERS)),
):
    query = db.query(WorkOrder)

    # Strict isolation: Technicians may only list work orders assigned to them
    norm_role = normalize_role(current_user.role)
    if norm_role == Role.TECHNICIAN:
        query = query.filter(WorkOrder.assigned_to == current_user.username)
    elif assigned_to is not None:
        query = query.filter(WorkOrder.assigned_to == assigned_to)

    if fault_id is not None:
        query = query.filter(WorkOrder.fault_id == fault_id)
    if status_filter is not None:
        query = query.filter(WorkOrder.status == status_filter)

    orders = query.order_by(WorkOrder.created_at.desc()).limit(limit).all()

    return [
        {
            "id": order.id,
            "fault_id": order.fault_id,
            "fault_type": order.fault.fault_type if order.fault else None,
            "phase": order.fault.phase if order.fault else None,
            "assigned_to": order.assigned_to,
            "status": order.status,
            "diagnosis": order.diagnosis,
            "created_at": order.created_at,
            "started_at": order.started_at,
            "restored_at": order.restored_at,
            "closed_at": order.closed_at,
            "created_by": order.created_by,
            "attempts_count": len(order.attempts),
        }
        for order in orders
    ]


@router.get("/work-orders/{work_order_id}")
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_WORK_ORDERS)),
):
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Technicians can only view their own assigned work order
    norm_role = normalize_role(current_user.role)
    if norm_role == Role.TECHNICIAN and order.assigned_to != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Technicians may only view work orders assigned to their account.",
        )

    return {
        "id": order.id,
        "fault_id": order.fault_id,
        "fault": {
            "id": order.fault.id,
            "fault_type": order.fault.fault_type,
            "phase": order.fault.phase,
            "severity": order.fault.severity,
            "status": order.fault.status,
            "description": order.fault.description,
            "detected_at": order.fault.detected_at,
        } if order.fault else None,
        "assigned_to": order.assigned_to,
        "status": order.status,
        "diagnosis": order.diagnosis,
        "created_at": order.created_at,
        "started_at": order.started_at,
        "restored_at": order.restored_at,
        "closed_at": order.closed_at,
        "created_by": order.created_by,
        "attempts": [
            {
                "id": a.id,
                "note": a.note,
                "created_by": a.created_by,
                "created_at": a.created_at,
            }
            for a in order.attempts
        ],
    }


@router.post("/work-orders/{work_order_id}/attempts")
def add_work_attempt(
    work_order_id: int,
    payload: WorkAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.LOG_WORK_ATTEMPTS)),
):
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    norm_role = normalize_role(current_user.role)
    if norm_role == Role.TECHNICIAN and order.assigned_to != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Technicians may only log repair attempts on work orders assigned to their account.",
        )

    now = datetime.now(timezone.utc)
    if order.status == "assigned":
        order.status = "in_progress"
        order.started_at = now

    creator = payload.created_by or current_user.username
    attempt = WorkAttempt(
        work_order_id=order.id,
        note=payload.note,
        created_by=creator,
        created_at=now,
    )
    db.add(attempt)

    write_audit(
        db,
        actor=current_user.username,
        action="add_work_attempt",
        entity_type="work_order",
        entity_id=order.id,
        detail=f"Added attempt note for work order {order.id}",
    )

    db.commit()
    db.refresh(attempt)

    return {
        "status": "success",
        "message": "Work attempt logged",
        "attempt_id": attempt.id,
        "order_status": order.status,
    }


@router.put("/work-orders/{work_order_id}/status")
def update_work_order_status(
    work_order_id: int,
    payload: WorkOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.UPDATE_WORK_ORDER_STATUS)),
):
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    norm_role = normalize_role(current_user.role)
    if norm_role == Role.TECHNICIAN and order.assigned_to != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Technicians may only update status on work orders assigned to their account.",
        )

    target_status = payload.status.lower()
    if target_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    now = datetime.now(timezone.utc)
    order.status = target_status

    if payload.diagnosis is not None:
        order.diagnosis = payload.diagnosis

    if target_status == "in_progress" and order.started_at is None:
        order.started_at = now
    elif target_status == "restored":
        if order.started_at is None:
            order.started_at = now
        order.restored_at = now
    elif target_status == "closed":
        if order.started_at is None:
            order.started_at = now
        if order.restored_at is None:
            order.restored_at = now
        order.closed_at = now

        # Update associated fault if not already rectified
        if order.fault and order.fault.status != "rectified":
            order.fault.status = "rectified"
            order.fault.rectified_at = now
            order.fault.resolution = order.diagnosis or "Restored and closed via work order"

    write_audit(
        db,
        actor=current_user.username,
        action="update_work_order_status",
        entity_type="work_order",
        entity_id=order.id,
        detail=f"Status set to {target_status}",
    )

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": f"Work order transitioned to {target_status}",
        "work_order_id": order.id,
        "status": order.status,
        "diagnosis": order.diagnosis,
    }

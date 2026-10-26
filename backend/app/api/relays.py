from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin, validate_device_access
from app.db.database import get_db
from app.models.device import Device
from app.models.floor import Floor
from app.models.relay import Relay
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(
    prefix="/relays",
    tags=["Relays"],
)


# --------------------------------------------------
# CREATE RELAY (Admin Only)
# --------------------------------------------------

@router.post("/")
def create_relay(
    device_id: int,
    relay_number: int,
    name: str,
    gpio_pin: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Prevent duplicate relay number on same device
    existing = (
        db.query(Relay)
        .filter(
            Relay.device_id == device_id,
            Relay.relay_number == relay_number,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relay number already exists for this device",
        )

    relay = Relay(
        device_id=device_id,
        relay_number=relay_number,
        name=name,
        gpio_pin=gpio_pin,
        commanded_state=False,
        actual_state=None,
        is_on=False,
        is_active=True,
    )

    db.add(relay)
    db.flush()

    write_audit(
        db=db,
        actor=current_user.username,
        action="create_relay",
        entity_type="relay",
        entity_id=relay.id,
        detail=f"Created relay '{relay.name}' (relay #{relay.relay_number}, GPIO {gpio_pin}) on device {device_id}",
    )

    db.commit()
    db.refresh(relay)

    return {
        "status": "success",
        "message": "Relay created",
        "relay_id": relay.id,
        "name": relay.name,
        "commanded_state": relay.commanded_state,
        "is_on": relay.is_on,
    }


# --------------------------------------------------
# GET ALL RELAYS (Read operation)
# --------------------------------------------------

@router.get("/")
def get_relays(
    device_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Relay)

    if device_id is not None:
        validate_device_access(device_id, user=current_user, db=db)
        query = query.filter(Relay.device_id == device_id)
    else:
        # Scoped by user's assigned location
        if current_user.assigned_block_id is not None:
            valid_floor_ids = [f.id for f in db.query(Floor.id).filter(Floor.block_id == current_user.assigned_block_id).all()]
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id.in_(valid_floor_ids)).all()]
            query = query.filter(Relay.device_id.in_(valid_dev_ids))
        elif current_user.assigned_floor_id is not None:
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id == current_user.assigned_floor_id).all()]
            query = query.filter(Relay.device_id.in_(valid_dev_ids))

    return query.all()


# --------------------------------------------------
# GET SINGLE RELAY (Read operation)
# --------------------------------------------------

@router.get("/{relay_id}")
def get_relay(
    relay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    relay = db.get(Relay, relay_id)

    if relay is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relay not found",
        )

    validate_device_access(relay.device_id, user=current_user, db=db)
    return relay


# --------------------------------------------------
# TURN RELAY ON (Admin Only)
# --------------------------------------------------

@router.post("/{relay_id}/on")
def turn_relay_on(
    relay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    relay = db.get(Relay, relay_id)

    if relay is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relay not found",
        )

    if not relay.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Relay is inactive",
        )

    # Update commanded_state; physical feedback remains unverified
    relay.commanded_state = True
    relay.is_on = True

    write_audit(
        db=db,
        actor=current_user.username,
        action="relay_command_on",
        entity_type="relay",
        entity_id=relay.id,
        detail=f"Commanded relay '{relay.name}' (GPIO {relay.gpio_pin}) ON on device {relay.device_id}",
    )

    db.commit()
    db.refresh(relay)

    return {
        "status": "success",
        "message": "Relay ON command accepted; awaiting physical contactor feedback",
        "relay_id": relay.id,
        "commanded_state": relay.commanded_state,
        "is_on": relay.is_on,
        "actual_state": relay.actual_state,
        "hardware_verified": False,
    }


# --------------------------------------------------
# TURN RELAY OFF (Admin Only)
# --------------------------------------------------

@router.post("/{relay_id}/off")
def turn_relay_off(
    relay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    relay = db.get(Relay, relay_id)

    if relay is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relay not found",
        )

    if not relay.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Relay is inactive",
        )

    # Update commanded_state; physical feedback remains unverified
    relay.commanded_state = False
    relay.is_on = False

    write_audit(
        db=db,
        actor=current_user.username,
        action="relay_command_off",
        entity_type="relay",
        entity_id=relay.id,
        detail=f"Commanded relay '{relay.name}' (GPIO {relay.gpio_pin}) OFF on device {relay.device_id}",
    )

    db.commit()
    db.refresh(relay)

    return {
        "status": "success",
        "message": "Relay OFF command accepted; awaiting physical contactor feedback",
        "relay_id": relay.id,
        "commanded_state": relay.commanded_state,
        "is_on": relay.is_on,
        "actual_state": relay.actual_state,
        "hardware_verified": False,
    }

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    get_current_user,
    require_ingest,
    validate_device_access,
)
from app.db.database import get_db
from app.models.device import Device
from app.models.floor import Floor
from app.models.telemetry import Telemetry
from app.models.user import User
from app.rules.engine import PhaseSample, evaluate_telemetry
from app.rules.thresholds import thresholds_from_settings
from app.schemas.telemetry import TelemetryCreate
from app.services.faults import record_findings

router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)


@router.post("/")
def create_telemetry(
    data: TelemetryCreate,
    db: Session = Depends(get_db),
    caller: str = Depends(require_ingest),
):
    device = db.get(Device, data.device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    received_at = datetime.now(timezone.utc)
    sample_time = data.sampled_at
    if sample_time.tzinfo is None:
        sample_time = sample_time.replace(tzinfo=timezone.utc)

    # Clock skew policy: Reject samples with timestamps in the future beyond tolerance
    future_skew = (sample_time - received_at).total_seconds()
    if future_skew > settings.CLOCK_SKEW_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Telemetry timestamp is in the future beyond allowable clock skew "
                f"({int(future_skew)}s > {settings.CLOCK_SKEW_TOLERANCE_SECONDS}s)"
            ),
        )

    device.last_seen_at = received_at

    telemetry = Telemetry(
        device_id=data.device_id,
        phase=data.phase,
        voltage=data.voltage,
        current=data.current,
        power=data.power,
        energy=data.energy,
        power_factor=data.power_factor,
        frequency=data.frequency,
        temperature=data.temperature,
        sampled_at=sample_time,
        received_at=received_at,
        sampling_interval_ms=data.sampling_interval_ms,
        transmission_reason=data.transmission_reason,
        source=data.source,
        data_quality=data.data_quality,
    )

    db.add(telemetry)
    db.flush()

    previous = (
        db.query(Telemetry)
        .filter(
            Telemetry.device_id == data.device_id,
            Telemetry.phase == data.phase,
            Telemetry.id != telemetry.id,
        )
        .order_by(Telemetry.sampled_at.desc())
        .first()
    )

    other_rows = _latest_other_phases(
        db,
        device_id=data.device_id,
        current_phase=data.phase,
        current_id=telemetry.id,
    )

    findings = evaluate_telemetry(
        sample=_to_sample(telemetry),
        thresholds=thresholds_from_settings(settings),
        previous=_to_sample(previous) if previous is not None else None,
        other_phases=[_to_sample(row) for row in other_rows],
    )
    created_faults = record_findings(db, data.device_id, findings)

    db.commit()
    db.refresh(telemetry)

    return {
        "status": "success",
        "message": "Telemetry stored",
        "telemetry_id": telemetry.id,
        "device_id": data.device_id,
        "phase": data.phase,
        "sampled_at": data.sampled_at,
        "received_at": received_at,
        "findings": [
            {
                "fault_type": finding.fault_type,
                "category": finding.category,
                "severity": finding.severity,
                "phase": finding.phase,
                "measured_value": finding.measured_value,
                "expected_value": finding.expected_value,
                "unit": finding.unit,
                "description": finding.description,
            }
            for finding in findings
        ],
        "faults_created": len(created_faults),
    }


@router.get("/")
def get_telemetry(
    device_id: int | None = None,
    phase: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Telemetry)

    if device_id is not None:
        validate_device_access(device_id, user=current_user, db=db)
        query = query.filter(Telemetry.device_id == device_id)
    else:
        # Scope by user's assigned location if constrained
        if current_user.assigned_block_id is not None:
            valid_floor_ids = [f.id for f in db.query(Floor.id).filter(Floor.block_id == current_user.assigned_block_id).all()]
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id.in_(valid_floor_ids)).all()]
            query = query.filter(Telemetry.device_id.in_(valid_dev_ids))
        elif current_user.assigned_floor_id is not None:
            valid_dev_ids = [d.id for d in db.query(Device.id).filter(Device.floor_id == current_user.assigned_floor_id).all()]
            query = query.filter(Telemetry.device_id.in_(valid_dev_ids))

    if phase is not None:
        query = query.filter(Telemetry.phase == phase.strip().upper())

    return (
        query
        .order_by(Telemetry.sampled_at.desc())
        .limit(100)
        .all()
    )


@router.get("/latest")
def get_latest_telemetry(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_device_access(device_id, user=current_user, db=db)

    telemetry = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.sampled_at.desc())
        .first()
    )

    if telemetry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry found for this device",
        )

    return telemetry


@router.get("/latest-by-phase")
def get_latest_telemetry_by_phase(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_device_access(device_id, user=current_user, db=db)

    phases = {}

    for phase in ("R", "Y", "B"):
        row = (
            db.query(Telemetry)
            .filter(
                Telemetry.device_id == device_id,
                Telemetry.phase == phase,
            )
            .order_by(Telemetry.sampled_at.desc())
            .first()
        )
        if row is not None:
            phases[phase] = row

    if not phases:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry found for this device",
        )

    return phases


def _latest_other_phases(
    db: Session,
    device_id: int,
    current_phase: str,
    current_id: int,
) -> list[Telemetry]:
    others: list[Telemetry] = []
    all_phases = ["R", "Y", "B"]
    if current_phase in all_phases:
        all_phases.remove(current_phase)

    for p in all_phases:
        row = (
            db.query(Telemetry)
            .filter(
                Telemetry.device_id == device_id,
                Telemetry.phase == p,
                Telemetry.id != current_id,
            )
            .order_by(Telemetry.sampled_at.desc())
            .first()
        )
        if row is not None:
            others.append(row)

    return others


def _to_sample(row: Telemetry) -> PhaseSample:
    return PhaseSample(
        phase=row.phase,
        voltage=row.voltage,
        current=row.current,
        power=row.power,
        frequency=row.frequency,
        power_factor=row.power_factor,
        temperature=row.temperature,
        data_quality=row.data_quality,
    )

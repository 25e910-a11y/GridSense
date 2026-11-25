"""Return-to-normal check before a fault's work order is closed.

Stage 2 lifecycle: alert -> work order -> repair -> readings normal -> closed.
A work order can only close once the device has sent a fresh reading, after the
repair was marked restored, that no longer shows the same fault.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.device import Device
from app.models.fault import Fault
from app.models.telemetry import Telemetry
from app.rules.engine import CATEGORY_SENSOR, PhaseSample, evaluate_telemetry
from app.services.device_config import thresholds_for_device


@dataclass
class NormalCheck:
    ok: bool
    reason: str
    telemetry_id: int | None = None
    source: str | None = None


def _sample(row: Telemetry) -> PhaseSample:
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


def check_back_to_normal(db: Session, fault: Fault, since: datetime | None) -> NormalCheck:
    if since is None:
        return NormalCheck(
            ok=False,
            reason="Mark the work order restored first, then wait for a new reading from the device.",
        )

    query = db.query(Telemetry).filter(
        Telemetry.device_id == fault.device_id,
        Telemetry.received_at > since,
    )
    if fault.phase:
        query = query.filter(Telemetry.phase == fault.phase)
    latest = query.order_by(Telemetry.received_at.desc(), Telemetry.id.desc()).first()

    if latest is None:
        where = f"phase {fault.phase}" if fault.phase else "this device"
        return NormalCheck(
            ok=False,
            reason=f"No new reading from {where} since the repair was marked restored. Wait for the next reading.",
        )

    others: list[PhaseSample] = []
    for phase in ("R", "Y", "B"):
        if phase == latest.phase:
            continue
        row = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == fault.device_id, Telemetry.phase == phase)
            .order_by(Telemetry.received_at.desc(), Telemetry.id.desc())
            .first()
        )
        if row is not None:
            others.append(_sample(row))

    device = db.get(Device, fault.device_id)
    findings = evaluate_telemetry(
        sample=_sample(latest),
        thresholds=thresholds_for_device(settings, device),
        previous=None,
        other_phases=others,
    )

    for finding in findings:
        if finding.category == CATEGORY_SENSOR or finding.fault_type == "INVALID_MEASUREMENT":
            return NormalCheck(
                ok=False,
                reason="The latest reading is a sensor or communication error, so normal readings cannot be confirmed yet.",
                telemetry_id=latest.id,
                source=latest.source,
            )
        if finding.fault_type == fault.fault_type:
            return NormalCheck(
                ok=False,
                reason=f"The latest reading still shows {fault.fault_type}. Readings are not back to normal yet.",
                telemetry_id=latest.id,
                source=latest.source,
            )

    return NormalCheck(
        ok=True,
        reason="Latest reading after repair is back to normal.",
        telemetry_id=latest.id,
        source=latest.source,
    )

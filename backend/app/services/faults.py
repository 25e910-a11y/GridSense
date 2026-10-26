from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.fault import Fault
from app.rules.engine import Finding
from app.services.notifications import notify_new_faults

OPEN_STATUSES = ("detected", "acknowledged")


def record_findings(
    db: Session,
    device_id: int,
    findings: list[Finding],
) -> list[Fault]:
    created: list[Fault] = []

    for finding in findings:
        existing = (
            db.query(Fault)
            .filter(
                Fault.device_id == device_id,
                Fault.fault_type == finding.fault_type,
                Fault.phase == finding.phase,
                Fault.status.in_(OPEN_STATUSES),
            )
            .first()
        )

        if existing is not None:
            existing.description = finding.description
            existing.severity = finding.severity
            existing.category = finding.category
            existing.measured_value = finding.measured_value
            existing.expected_value = finding.expected_value
            existing.unit = finding.unit
            continue

        fault = Fault(
            device_id=device_id,
            phase=finding.phase,
            fault_type=finding.fault_type,
            severity=finding.severity,
            description=finding.description,
            category=finding.category,
            measured_value=finding.measured_value,
            expected_value=finding.expected_value,
            unit=finding.unit,
            status="detected",
            detected_at=datetime.now(timezone.utc),
        )
        db.add(fault)
        db.flush()
        created.append(fault)

    if created:
        notify_new_faults(db, created, findings)

    return created

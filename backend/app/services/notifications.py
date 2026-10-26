from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.fault import Fault
from app.models.notification import Notification
from app.rules.engine import Finding


def notify_new_faults(
    db: Session,
    faults: list[Fault],
    findings: list[Finding],
) -> list[Notification]:
    created: list[Notification] = []
    finding_by_type = {
        (item.fault_type, item.phase): item
        for item in findings
    }

    for fault in faults:
        finding = finding_by_type.get((fault.fault_type, fault.phase))
        description = fault.description or ""
        if finding is not None:
            description = finding.description

        notification = Notification(
            fault_id=fault.id,
            title=f"{fault.fault_type} on {fault.phase or 'system'}",
            message=description,
            severity=fault.severity,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notification)
        created.append(notification)

    return created

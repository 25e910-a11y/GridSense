from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    detail: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    return entry

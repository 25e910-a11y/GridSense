from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)


@router.get("/")
def list_audit_logs(
    actor: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):

    query = db.query(AuditLog)

    if actor is not None:
        query = query.filter(AuditLog.actor == actor)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)

    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    return [
        {
            "id": log.id,
            "actor": log.actor,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in rows
    ]

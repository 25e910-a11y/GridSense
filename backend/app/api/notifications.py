from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import require_any_authenticated
from app.db.database import get_db
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("/")
def list_notifications(
    is_read: bool | None = None,
    severity: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    query = db.query(Notification)

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if severity is not None:
        query = query.filter(Notification.severity == severity)

    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()

    return [
        {
            "id": n.id,
            "fault_id": n.fault_id,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in rows
    ]


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    count = db.query(Notification).filter(Notification.is_read == False).count()
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    item = db.get(Notification, notification_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    item.is_read = True
    db.commit()
    db.refresh(item)

    return {
        "status": "success",
        "notification_id": item.id,
        "is_read": item.is_read,
    }


@router.put("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    count = (
        db.query(Notification)
        .filter(Notification.is_read == False)
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()

    return {
        "status": "success",
        "updated_count": count,
    }

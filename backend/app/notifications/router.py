"""The caller's notifications (FR-INT-5, FR-MOD-9)."""

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import or_, select, update

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.db import emit, now
from app.errors import errors
from app.models import Notification, Post
from app.realtime.hub import LiveEvent
from app.schemas import ApiModel

router = APIRouter(tags=["notifications"], prefix="/notifications")


class NotificationOut(ApiModel):
    """A notification. System notices come from Connect Moderation and cannot be answered."""

    id: int
    type: str
    text: str
    post_id: int | None
    action_id: int | None
    created_at: datetime
    read_at: datetime | None


@router.get("", response_model=list[NotificationOut], responses=errors())
def list_notifications(user: CurrentUser, db: Db):
    """Return the newest 50 notifications; those about posts no longer visible are left out.

    **Role:** signed in.
    """
    visible = select(Post.id).where(policy.visible_posts(user))
    return db.scalars(
        select(Notification)
        .where(
            Notification.user_id == user.id,
            or_(Notification.post_id.is_(None), Notification.post_id.in_(visible)),
        )
        .order_by(Notification.id.desc())
        .limit(50)
    ).all()


@router.post("/read", status_code=204, responses=errors())
def mark_read(user: CurrentUser, db: Db):
    """Mark all notifications as read.

    **Role:** signed in.
    """
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=now())
    )
    emit(db, LiveEvent(f"user:{user.id}", "notification.read"))
    db.commit()

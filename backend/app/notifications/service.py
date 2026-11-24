"""Creating notifications without telling anyone about content they may not see."""

import re

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app import policy
from app.db import emit
from app.models import CommunityMute, Notification, Post, User
from app.realtime.hub import LiveEvent


def notify(
    db: Session, user_id: int, kind: str, text: str, post: Post | None = None, action_id: int | None = None
) -> None:
    """Notify one user, unless the post is outside their audience or they muted its community.

    System notices carry no post, so neither rule can suppress them.
    """
    if post is not None:
        recipient = db.get(User, user_id)
        muted = db.scalar(
            select(
                exists().where(
                    CommunityMute.user_id == user_id, CommunityMute.community_id == post.community_id
                )
            )
        )
        if muted or not policy.can_view_post(db, recipient, post.id):
            return
    db.add(Notification(user_id=user_id, type=kind, text=text, post_id=post and post.id, action_id=action_id))
    emit(db, LiveEvent(f"user:{user_id}", "notification.created"))


def notify_mentions(db: Session, author: User, text: str, post: Post) -> None:
    """Notify users mentioned as @handle who can see the post (FR-AUD-6)."""
    handles = {handle.lower() for handle in re.findall(r"@([A-Za-z0-9_]+)", text)}
    mentioned = select(User.id).where(
        User.handle.in_(handles), User.id != author.id, User.id.not_in(policy.blocked_ids(author.id))
    )
    for user_id in db.scalars(mentioned).all():
        notify(db, user_id, "mention", f"{author.display_name} mentioned you.", post)

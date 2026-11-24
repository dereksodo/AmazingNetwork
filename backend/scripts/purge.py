"""Erase removed content and deleted accounts after 30 days. Run from backend/: python -m scripts.purge"""

from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.db import SessionLocal, now
from app.models import Comment, Message, Post, PostImage, PostVersion, User

ERASED = "[erased]"


def purge(db: Session) -> None:
    """Overwrite personal content; rows stay so that the audit log keeps its targets."""
    limit = now() - timedelta(days=30)
    accounts = select(User.id).where(User.deleted_at < limit)
    posts = select(Post.id).where((Post.removed_at < limit) | Post.author_id.in_(accounts))
    db.execute(delete(PostImage).where(PostImage.post_id.in_(posts)))
    db.execute(delete(PostVersion).where(PostVersion.post_id.in_(posts)))
    db.execute(
        update(Comment)
        .where((Comment.removed_at < limit) | Comment.author_id.in_(accounts))
        .values(body=ERASED, status="deleted")
    )
    db.execute(update(Message).where(Message.sender_id.in_(accounts)).values(body=ERASED))
    db.execute(
        update(Post).where(Post.id.in_(posts)).values(title=ERASED, body_html=ERASED, status="deleted")
    )
    for user in db.scalars(select(User).where(User.deleted_at < limit)).all():
        user.email = user.handle = f"erased-{user.id}"
        user.display_name, user.bio, user.programme_id, user.password_hash = ERASED, "", None, ERASED
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        purge(session)

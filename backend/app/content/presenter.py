"""Building post responses."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import policy
from app.content.schemas import EventOut, ImageOut, PostOut, PostSummary
from app.models import Comment, Event, Post, Reaction, Rsvp, User
from app.schemas import UserRef


def rsvp_count(db: Session, event: Event, status: str) -> int:
    """Number of RSVPs with a status."""
    return db.scalar(
        select(func.count()).select_from(Rsvp).where(Rsvp.event_id == event.post_id, Rsvp.status == status)
    )


def event_out(db: Session, user: User, event: Event) -> EventOut:
    """Event details with the caller's RSVP."""
    mine = db.get(Rsvp, (event.post_id, user.id))
    return EventOut(
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        capacity=event.capacity,
        rsvp_deadline=event.rsvp_deadline,
        cancelled=event.cancelled,
        going=rsvp_count(db, event, "going"),
        waitlisted=rsvp_count(db, event, "waitlisted"),
        my_rsvp=mine and mine.status,
    )


def post_out(db: Session, user: User, post: Post) -> PostOut:
    """A post as the caller sees it. The caller's access was checked before."""
    reactions = db.execute(
        select(Reaction.kind, func.count()).where(Reaction.post_id == post.id).group_by(Reaction.kind)
    )
    mine = db.scalars(select(Reaction.kind).where(Reaction.post_id == post.id, Reaction.user_id == user.id))
    original = post.reshare_of_id and db.get(Post, post.reshare_of_id)
    return PostOut(
        id=post.id,
        type=post.type,
        author=UserRef.model_validate(post.author),
        community_id=post.community_id,
        community_name=post.community and post.community.name,
        visibility=post.visibility,
        title=post.title,
        body_html=post.body_html,
        status=post.status,
        comments_enabled=post.comments_enabled,
        locked=post.locked,
        pinned=post.pinned,
        version=post.version,
        created_at=post.created_at,
        edited_at=post.edited_at,
        images=[ImageOut.model_validate(image) for image in post.images],
        event=post.event and event_out(db, user, post.event),
        reshare_of=original and PostSummary.model_validate(original),
        reactions={kind: count for kind, count in reactions},
        my_reactions=mine.all(),
        comment_count=db.scalar(
            select(func.count())
            .select_from(Comment)
            .where(Comment.post_id == post.id, policy.visible_comments(user))
        ),
    )

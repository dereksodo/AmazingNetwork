"""Events: changing details, RSVPs and the waitlist (FR-PUB-4)."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.content.posts import emit_post
from app.content.presenter import post_out, rsvp_count
from app.content.schemas import EventUpdate, PostOut, RsvpInput, RsvpOut
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import Event, Post, Rsvp, User
from app.notifications.service import notify
from app.realtime.hub import LiveEvent

router = APIRouter(tags=["events"], prefix="/events")


def get_event_post(db: Session, user: User, post_id: int) -> Post:
    """Load an event post the caller may interact with."""
    post = policy.get_interactive_post(db, user, post_id)
    if post.event is None:
        raise ApiError("POST_NOT_FOUND")
    return post


def promote(db: Session, event: Event) -> None:
    """Move waitlisted users to going, in order, while places are free.

    Runs after a flush: the pending write holds SQLite's write lock, so counts cannot change underneath.
    """
    db.flush()
    free = event.capacity - rsvp_count(db, event, "going")
    waiting = db.scalars(
        select(Rsvp)
        .where(Rsvp.event_id == event.post_id, Rsvp.status == "waitlisted")
        .order_by(Rsvp.created_at)
        .limit(max(free, 0))
    )
    for rsvp in waiting.all():
        rsvp.status = "going"
        notify(db, rsvp.user_id, "event_change", "You have a place at an event you RSVPed to.", event.post)
    db.flush()


@router.put(
    "/{post_id}/rsvp",
    response_model=RsvpOut,
    responses=errors("MUTED", "POST_NOT_FOUND", "CONTENT_FROZEN", "RSVP_CLOSED"),
)
def set_rsvp(post_id: int, body: RsvpInput, user: CurrentUser, db: Db):
    """Answer an event. `going` beyond capacity is waitlisted; null withdraws the answer.

    **Role:** in the audience, not muted, before the RSVP deadline.
    """
    event = get_event_post(db, user, post_id).event
    if event.cancelled or now() > event.rsvp_deadline:
        raise ApiError("RSVP_CLOSED")
    rsvp = db.get(Rsvp, (post_id, user.id))
    if body.status is None:
        if rsvp is not None:
            db.delete(rsvp)
        rsvp = None
    else:
        # Going starts on the waitlist and is promoted below, so order and capacity use one rule.
        wanted = "waitlisted" if body.status == "going" else "interested"
        if rsvp is None:
            rsvp = Rsvp(event_id=post_id, user_id=user.id, status=wanted)
            db.add(rsvp)
        elif not (wanted == "waitlisted" and rsvp.status in ("going", "waitlisted")):
            rsvp.status = wanted
            rsvp.created_at = now()
    promote(db, event)
    emit(db, LiveEvent(f"post:{post_id}", "rsvp.changed", {"post_id": post_id}))
    db.commit()
    return RsvpOut(status=rsvp and rsvp.status)


@router.put(
    "/{post_id}",
    response_model=PostOut,
    responses=errors("MUTED", "NOT_AN_OFFICER", "POST_NOT_FOUND", "CONTENT_FROZEN"),
)
def update_event(post_id: int, body: EventUpdate, user: CurrentUser, db: Db):
    """Change or cancel an event; everyone who RSVPed is notified.

    **Role:** officer of the community; school admin for campus-wide events.
    """
    post = get_event_post(db, user, post_id)
    if not policy.may_write_drafts(db, user, post.community_id):
        raise ApiError("NOT_AN_OFFICER")
    for name, value in body.model_dump().items():
        setattr(post.event, name, value)
    promote(db, post.event)
    wording = "was cancelled" if body.cancelled else "has changed"
    for user_id in db.scalars(select(Rsvp.user_id).where(Rsvp.event_id == post_id)).all():
        notify(db, user_id, "event_change", f"“{post.title}” {wording}.", post)
    emit_post(db, post, "post.updated")
    db.commit()
    return post_out(db, user, post)

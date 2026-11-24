"""Drafts: create, list, read, invite and publish (FR-COL)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.collab import rooms, ydoc
from app.content.posts import check_audience, check_pin_limit, emit_post
from app.content.presenter import post_out
from app.content.sanitize import clean_body, plain_text
from app.content.schemas import EventInput, PostOut
from app.errors import ApiError, errors
from app.models import Draft, DraftCollaborator, Event, Membership, Post, User
from app.notifications.service import notify, notify_mentions
from app.schemas import ApiInput, ApiModel, UserRef

router = APIRouter(tags=["drafts"], prefix="/drafts")


class DraftInput(ApiInput):
    """A new draft. Without a community it is campus-wide (admins only)."""

    community_id: int | None = Field(default=None, examples=[1])
    kind: Literal["announcement", "event"]
    title: str = Field(min_length=1, max_length=120, examples=["Open day"])
    collaborator_ids: list[int] = Field(default=[], examples=[[3]])


class Invitation(ApiInput):
    """Another officer (or admin) to write with."""

    user_id: int


class DraftOut(ApiModel):
    """A draft. Its text is edited over /ws/drafts/{id}."""

    id: int
    community_id: int | None
    community_name: str | None
    kind: Literal["announcement", "event"]
    title: str
    version: int
    status: Literal["editing", "published"]
    published_post_id: int | None
    collaborators: list[UserRef]


class PublishInput(ApiInput):
    """Publish exactly the version the officer has on screen."""

    expected_version: int = Field(examples=[17])
    title: str = Field(min_length=1, max_length=120)
    visibility: Literal["campus", "community"]
    pinned: bool = False
    event: EventInput | None = Field(default=None, description="Required if the draft is an event")


def draft_out(draft: Draft) -> DraftOut:
    """Describe a draft to a collaborator."""
    return DraftOut(
        id=draft.id,
        community_id=draft.community_id,
        community_name=draft.community and draft.community.name,
        kind=draft.kind,
        title=draft.title,
        version=draft.version,
        status=draft.status,
        published_post_id=draft.published_post_id,
        collaborators=[UserRef.model_validate(c.user) for c in draft.collaborators],
    )


def _add_collaborator(db: Session, draft: Draft, user_id: int, inviter: User) -> None:
    """Invite a user who has the role needed to write this draft."""
    invited = policy.get_visible_user(db, inviter, user_id)
    if not policy.may_write_drafts(db, invited, draft.community_id):
        raise ApiError("NOT_AN_OFFICER")
    db.merge(DraftCollaborator(draft_id=draft.id, user_id=user_id))
    if user_id != inviter.id:
        notify(db, user_id, "draft", f"{inviter.display_name} invited you to write “{draft.title}”.")


@router.post(
    "",
    status_code=201,
    response_model=DraftOut,
    responses=errors("MUTED", "NOT_AN_OFFICER", "USER_NOT_FOUND"),
)
def create_draft(body: DraftInput, user: CurrentUser, db: Db):
    """Create an announcement or event draft and invite other officers.

    **Role:** officer of the community, or admin for campus-wide drafts; not muted.
    """
    policy.require_not_muted(db, user)
    if not policy.may_write_drafts(db, user, body.community_id):
        raise ApiError("NOT_AN_OFFICER")
    draft = Draft(
        community_id=body.community_id,
        creator_id=user.id,
        kind=body.kind,
        title=body.title,
        ydoc=ydoc.empty_state(),
    )
    db.add(draft)
    db.flush()
    for user_id in {user.id, *body.collaborator_ids}:
        _add_collaborator(db, draft, user_id, user)
    db.commit()
    return draft_out(draft)


@router.get("", response_model=list[DraftOut], responses=errors())
def list_drafts(user: CurrentUser, db: Db):
    """List the drafts the caller collaborates on.

    **Role:** collaborator who still is an officer (or admin for campus-wide drafts).
    """
    found = db.scalars(
        select(Draft)
        .join(DraftCollaborator)
        .where(DraftCollaborator.user_id == user.id)
        .order_by(Draft.id.desc())
    )
    return [draft_out(d) for d in found.all() if policy.may_write_drafts(db, user, d.community_id)]


@router.get("/{draft_id}", response_model=DraftOut, responses=errors("DRAFT_NOT_FOUND"))
def get_draft(draft_id: int, user: CurrentUser, db: Db):
    """Return one draft. Everyone else gets the same 404 as for a missing draft.

    **Role:** collaborator.
    """
    return draft_out(policy.get_editable_draft(db, user, draft_id))


@router.post(
    "/{draft_id}/collaborators",
    response_model=DraftOut,
    responses=errors("NOT_AN_OFFICER", "DRAFT_NOT_FOUND", "USER_NOT_FOUND"),
)
def invite(draft_id: int, body: Invitation, user: CurrentUser, db: Db):
    """Invite another officer of the community (or admin for campus-wide drafts).

    **Role:** collaborator.
    """
    draft = policy.get_editable_draft(db, user, draft_id)
    _add_collaborator(db, draft, body.user_id, user)
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.post(
    "/{draft_id}/publish",
    status_code=201,
    response_model=PostOut,
    responses=errors(
        "VALIDATION_ERROR", "EMPTY_CONTENT", "CONTENT_TOO_LONG", "INVALID_AUDIENCE", "MUTED",
        "DRAFT_NOT_FOUND", "ALREADY_PUBLISHED", "VERSION_CONFLICT", "TOO_MANY_PINS",
    ),
)  # fmt: skip
def publish(draft_id: int, body: PublishInput, user: CurrentUser, db: Db):
    """Publish the draft as an announcement or event and notify the audience.

    **Role:** collaborator, not muted. The update below succeeds for exactly one of several
    simultaneous requests; the others get `ALREADY_PUBLISHED` with the id of the published post.
    """
    draft = policy.get_editable_draft(db, user, draft_id)
    policy.require_not_muted(db, user)
    check_audience(body.visibility, draft.community_id)
    if (body.event is None) == (draft.kind == "event"):
        raise ApiError("VALIDATION_ERROR")
    won = db.execute(
        update(Draft)
        .where(Draft.id == draft_id, Draft.version == body.expected_version, Draft.status == "editing")
        .values(status="published")
    )
    if won.rowcount == 0:
        db.refresh(draft)
        if draft.status == "published":
            raise ApiError("ALREADY_PUBLISHED", {"post_id": draft.published_post_id})
        raise ApiError("VERSION_CONFLICT", {"version": draft.version})
    db.refresh(draft)
    post = Post(
        author_id=user.id,
        community_id=draft.community_id,
        type=draft.kind,
        visibility=body.visibility,
        title=body.title,
        body_html=clean_body(ydoc.to_html(draft.ydoc)),
        pinned=body.pinned,
    )
    db.add(post)
    db.flush()
    if body.event is not None:
        db.add(Event(post_id=post.id, **body.event.model_dump()))
    draft.published_post_id = post.id
    db.flush()
    check_pin_limit(db, post)
    _notify_audience(db, user, post)
    emit_post(db, post, "post.created")
    db.commit()
    rooms.announce_published(draft_id, post.id)
    return post_out(db, user, post)


def _notify_audience(db: Session, author: User, post: Post) -> None:
    """Announce to the members of the community, or to everyone for campus-wide items."""
    recipients = select(User.id).where(User.deleted_at.is_(None), User.id != author.id)
    if post.community_id is not None:
        members = select(Membership.user_id).where(
            Membership.community_id == post.community_id, Membership.status == "active"
        )
        recipients = recipients.where(User.id.in_(members))
    place = post.community.name if post.community else "Campus"
    for user_id in db.scalars(recipients).all():
        notify(db, user_id, "announcement", f"{place}: {post.title}", post)
    notify_mentions(db, author, plain_text(post.body_html), post)

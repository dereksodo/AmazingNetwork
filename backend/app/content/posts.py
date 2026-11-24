"""Posts: create, read, edit, delete, reshare, react, pin and lock (FR-PUB, FR-INT)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, Response
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.content.presenter import post_out
from app.content.sanitize import clean_body, plain_text
from app.content.schemas import (
    OfficerControls,
    PostCreate,
    PostOut,
    PostPage,
    PostUpdate,
    PostVersionOut,
    ReactionKind,
    ReshareInput,
)
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import CommunityFollow, Follow, Membership, Post, PostVersion, Reaction, User
from app.notifications.service import notify_mentions
from app.realtime.hub import LiveEvent

router = APIRouter(tags=["posts"], prefix="/posts")
MAX_PINNED = 3


def check_audience(visibility: str, community_id: int | None) -> None:
    """Community visibility needs a community; follower visibility needs a profile post."""
    if (visibility == "community" and community_id is None) or (
        visibility == "followers" and community_id is not None
    ):
        raise ApiError("INVALID_AUDIENCE")


def check_pin_limit(db: Session, post: Post) -> None:
    """At most three pinned posts per community (or campus-wide). Call after flushing the pin."""
    pinned = db.scalar(
        select(func.count())
        .select_from(Post)
        .where(
            Post.community_id.is_(None)
            if post.community_id is None
            else Post.community_id == post.community_id,
            Post.pinned,
            Post.status == "visible",
        )
    )
    if pinned > MAX_PINNED:
        raise ApiError("TOO_MANY_PINS")


def emit_post(db: Session, post: Post, name: str) -> None:
    """Announce a change of a post to its audience."""
    data = {"post_id": post.id, "community_id": post.community_id}
    emit(db, LiveEvent("feed", name, data, post_id=post.id))
    emit(db, LiveEvent(f"post:{post.id}", name, data))


@router.post(
    "",
    status_code=201,
    response_model=PostOut,
    responses=errors(
        "EMPTY_CONTENT", "CONTENT_TOO_LONG", "INVALID_AUDIENCE", "ROLE_NOT_ALLOWED", "NOT_A_MEMBER",
        "MUTED", "COMMUNITY_NOT_FOUND",
    ),
)  # fmt: skip
def create_post(body: PostCreate, response: Response, user: CurrentUser, db: Db):
    """Publish a post or discussion.

    **Role:** user or moderator; member of the community for community posts; not muted.
    """
    check_audience(body.visibility, body.community_id)
    policy.require_can_publish(db, user, body.community_id)
    post = Post(
        **body.model_dump(exclude={"body_html"}), body_html=clean_body(body.body_html), author_id=user.id
    )
    db.add(post)
    db.flush()
    notify_mentions(db, user, plain_text(post.body_html), post)
    emit_post(db, post, "post.created")
    db.commit()
    response.headers["Location"] = f"/api/v1/posts/{post.id}"
    return post_out(db, user, post)


@router.get("", response_model=PostPage, responses=errors("COMMUNITY_NOT_FOUND"))
def list_posts(
    user: CurrentUser,
    db: Db,
    scope: Annotated[
        Literal["feed", "campus"],
        Query(description="feed: followed users and communities, own posts; campus: everything visible"),
    ] = "feed",
    community_id: int | None = None,
    author_id: int | None = None,
    before: Annotated[int | None, Query(description="Return posts older than this post id")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    """List visible posts, newest first. `community_id` or `author_id` replaces the scope.

    **Role:** signed in; only posts whose audience includes the caller are returned.
    """
    query = select(Post).where(policy.visible_posts(user))
    if community_id is not None:
        policy.get_visible_community(db, user, community_id)
        query = query.where(Post.community_id == community_id)
    elif author_id is not None:
        query = query.where(Post.author_id == author_id, Post.community_id.is_(None))
    elif scope == "feed":
        followed = select(Follow.followed_id).where(Follow.follower_id == user.id, Follow.status == "active")
        joined = select(Membership.community_id).where(
            Membership.user_id == user.id, Membership.status == "active"
        )
        followed_communities = select(CommunityFollow.community_id).where(CommunityFollow.user_id == user.id)
        query = query.where(
            or_(
                Post.author_id == user.id,
                Post.author_id.in_(followed),
                Post.community_id.in_(joined),
                Post.community_id.in_(followed_communities),
                and_(Post.community_id.is_(None), Post.type.in_(("announcement", "event"))),
            )
        )
    if before is not None:
        query = query.where(Post.id < before)
    found = db.scalars(query.order_by(Post.id.desc()).limit(limit + 1)).all()
    page = found[:limit]
    return PostPage(
        items=[post_out(db, user, post) for post in page],
        next_before=page[-1].id if len(found) > limit else None,
    )


@router.get("/pinned", response_model=list[PostOut], responses=errors())
def list_pinned(user: CurrentUser, db: Db, community_id: int | None = None):
    """List pinned posts of a community, or campus-wide ones if no community is given.

    **Role:** signed in; only posts whose audience includes the caller are returned.
    """
    place = Post.community_id.is_(None) if community_id is None else Post.community_id == community_id
    found = db.scalars(
        select(Post).where(policy.visible_posts(user), Post.pinned, place).order_by(Post.id.desc())
    )
    return [post_out(db, user, post) for post in found.all()]


@router.get("/{post_id}", response_model=PostOut, responses=errors("POST_NOT_FOUND"))
def get_post(post_id: int, user: CurrentUser, db: Db):
    """Return one post. A post outside the caller's audience looks like a missing post.

    **Role:** in the audience.
    """
    return post_out(db, user, policy.get_visible_post(db, user, post_id))


@router.patch(
    "/{post_id}",
    response_model=PostOut,
    responses=errors(
        "EMPTY_CONTENT", "CONTENT_TOO_LONG", "INVALID_AUDIENCE", "NOT_AUTHOR", "MUTED", "POST_NOT_FOUND",
        "CONTENT_FROZEN", "VERSION_CONFLICT",
    ),
)  # fmt: skip
def update_post(
    post_id: int,
    body: PostUpdate,
    user: CurrentUser,
    db: Db,
    if_match: Annotated[int, Header(description="The version the edit is based on", examples=[1])],
):
    """Replace the content of a post and keep the old version.

    **Role:** author, not muted. Refused with 409 if the post changed since version `If-Match`.
    """
    post = policy.get_own_post(db, user, post_id)
    check_audience(body.visibility, post.community_id)
    if post.reshare_of_id is not None and body.visibility != "campus":
        raise ApiError("INVALID_AUDIENCE")
    if post.type != "post" and body.title is None:
        raise ApiError("VALIDATION_ERROR")
    previous = PostVersion(
        post_id=post.id,
        version=if_match,
        title=post.title,
        body_html=post.body_html,
        visibility=post.visibility,
    )
    changed = db.execute(
        update(Post)
        .where(Post.id == post_id, Post.version == if_match)
        .values(
            **body.model_dump(exclude={"body_html"}),
            body_html=clean_body(body.body_html),
            version=Post.version + 1,
            edited_at=now(),
        )
    )
    if changed.rowcount == 0:
        raise ApiError("VERSION_CONFLICT")
    db.add(previous)
    emit_post(db, post, "post.updated")
    db.commit()
    db.refresh(post)
    return post_out(db, user, post)


@router.delete(
    "/{post_id}", status_code=204, responses=errors("NOT_AUTHOR", "MUTED", "POST_NOT_FOUND", "CONTENT_FROZEN")
)
def delete_post(post_id: int, user: CurrentUser, db: Db):
    """Delete a post; it and its comments disappear for everyone.

    **Role:** author, not muted.
    """
    post = policy.get_own_post(db, user, post_id)
    post.status = "deleted"
    post.removed_at = now()
    emit_post(db, post, "post.removed")
    db.commit()


@router.get(
    "/{post_id}/versions",
    response_model=list[PostVersionOut],
    responses=errors("POST_NOT_FOUND", "NOT_AUTHOR"),
)
def list_versions(post_id: int, user: CurrentUser, db: Db):
    """List earlier versions, newest first.

    **Role:** author or moderator (an earlier version may have had a narrower audience).
    """
    post = policy.get_visible_post(db, user, post_id)
    if user.id != post.author_id and user.role != "moderator":
        raise ApiError("NOT_AUTHOR")
    return db.scalars(
        select(PostVersion).where(PostVersion.post_id == post_id).order_by(PostVersion.version.desc())
    ).all()


@router.post(
    "/{post_id}/reshare",
    status_code=201,
    response_model=PostOut,
    responses=errors(
        "EMPTY_CONTENT", "CONTENT_TOO_LONG", "ROLE_NOT_ALLOWED", "MUTED", "POST_NOT_FOUND", "CONTENT_FROZEN",
        "NOT_RESHAREABLE",
    ),
)  # fmt: skip
def reshare_post(post_id: int, body: ReshareInput, user: CurrentUser, db: Db):
    """Reshare a campus-visible post on the caller's profile (FR-AUD-5).

    **Role:** user or moderator in the audience, not muted. Resharing a reshare shares its original.
    """
    policy.require_can_publish(db, user, None)
    original = policy.get_interactive_post(db, user, post_id)
    if original.visibility != "campus":
        raise ApiError("NOT_RESHAREABLE")
    post = Post(
        author_id=user.id,
        visibility="campus",
        body_html=clean_body(body.body_html),
        reshare_of_id=original.reshare_of_id or original.id,
    )
    db.add(post)
    db.flush()
    notify_mentions(db, user, plain_text(post.body_html), post)
    emit_post(db, post, "post.created")
    db.commit()
    return post_out(db, user, post)


@router.put(
    "/{post_id}/officer-controls",
    response_model=PostOut,
    responses=errors("NOT_AN_OFFICER", "POST_NOT_FOUND", "TOO_MANY_PINS"),
)
def set_officer_controls(post_id: int, body: OfficerControls, user: CurrentUser, db: Db):
    """Lock or unlock comments and pin or unpin a post (at most 3 pins).

    **Role:** officer of the post's community; school admin for campus-wide announcements and events.
    """
    post = policy.get_visible_post(db, user, post_id)
    if post.community_id is not None:
        policy.require_officer(db, user, post.community_id)
    elif user.role != "admin" or post.type not in ("announcement", "event"):
        raise ApiError("NOT_AN_OFFICER")
    post.locked = body.locked
    post.pinned = body.pinned
    db.flush()
    check_pin_limit(db, post)
    emit_post(db, post, "post.updated")
    db.commit()
    return post_out(db, user, post)


def _interact(db: Session, user: User, post_id: int) -> Post:
    post = policy.get_interactive_post(db, user, post_id)
    emit(db, LiveEvent(f"post:{post_id}", "reaction.changed", {"post_id": post_id}))
    return post


@router.put(
    "/{post_id}/reactions/{kind}",
    status_code=204,
    responses=errors("MUTED", "POST_NOT_FOUND", "CONTENT_FROZEN"),
)
def add_reaction(post_id: int, kind: ReactionKind, user: CurrentUser, db: Db):
    """Add a reaction; one of each kind per user. Idempotent.

    **Role:** in the audience, not muted.
    """
    _interact(db, user, post_id)
    db.merge(Reaction(post_id=post_id, user_id=user.id, kind=kind))
    db.commit()


@router.delete(
    "/{post_id}/reactions/{kind}",
    status_code=204,
    responses=errors("MUTED", "POST_NOT_FOUND", "CONTENT_FROZEN"),
)
def remove_reaction(post_id: int, kind: ReactionKind, user: CurrentUser, db: Db):
    """Remove the caller's reaction. Idempotent.

    **Role:** in the audience, not muted.
    """
    _interact(db, user, post_id)
    db.execute(
        delete(Reaction).where(
            Reaction.post_id == post_id, Reaction.user_id == user.id, Reaction.kind == kind
        )
    )
    db.commit()

"""Audience Policy (K-POLICY, ADR-003): the only place that decides who may see or do what.

The visibility rule exists once, as a SQL condition. Lists, single reads, notifications
and live events all use it, so they cannot disagree.
"""

from sqlalchemy import ColumnElement, and_, exists, or_, select
from sqlalchemy.orm import Session, aliased

from app.db import now
from app.errors import ApiError
from app.models import (
    Block,
    Comment,
    Community,
    Conversation,
    Draft,
    DraftCollaborator,
    Follow,
    Membership,
    Post,
    Sanction,
    User,
)

# --- relationships -------------------------------------------------------------


def blocked_ids(user_id: int):
    """Subquery: everyone who blocked this user or was blocked by them."""
    return (
        select(Block.blocked_id)
        .where(Block.blocker_id == user_id)
        .union(select(Block.blocker_id).where(Block.blocked_id == user_id))
    )


def is_blocked(db: Session, a: int, b: int) -> bool:
    """True if either user blocked the other."""
    return db.scalar(select(select(User.id).where(User.id == b, User.id.in_(blocked_ids(a))).exists()))


def membership(db: Session, user: User, community_id: int | None) -> Membership | None:
    """The user's active membership in a community, if any."""
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.community_id == community_id,
            Membership.status == "active",
        )
    )


def is_officer(db: Session, user: User, community_id: int | None) -> bool:
    """True for officers and owners of the community."""
    found = membership(db, user, community_id)
    return found is not None and found.role in ("officer", "owner")


def require_officer(db: Session, user: User, community_id: int | None) -> None:
    """Refuse users who are not officers of the community."""
    if not is_officer(db, user, community_id):
        raise ApiError("NOT_AN_OFFICER")


def require_not_muted(db: Session, user: User) -> None:
    """Refuse every write by a user with an active timed mute (P4)."""
    if db.scalar(select(exists().where(Sanction.user_id == user.id, Sanction.ends_at > now()))):
        raise ApiError("MUTED")


# --- users and communities -------------------------------------------------------


def visible_users(user: User) -> ColumnElement[bool]:
    """Accounts this user can see: not deleted and not in a block relationship."""
    return and_(User.deleted_at.is_(None), User.id.not_in(blocked_ids(user.id)))


def get_visible_user(db: Session, user: User, user_id: int) -> User:
    """Load a user or answer 404."""
    found = db.scalar(select(User).where(User.id == user_id, visible_users(user)))
    if found is None:
        raise ApiError("USER_NOT_FOUND")
    return found


def visible_communities(user: User) -> ColumnElement[bool]:
    """Approved communities, plus the user's own requests; admins see all."""
    if user.role == "admin":
        return Community.id.is_not(None)
    return or_(Community.status == "approved", Community.created_by_id == user.id)


def get_visible_community(db: Session, user: User, community_id: int) -> Community:
    """Load a community or answer 404."""
    found = db.scalar(select(Community).where(Community.id == community_id, visible_communities(user)))
    if found is None:
        raise ApiError("COMMUNITY_NOT_FOUND")
    return found


def get_open_community(db: Session, user: User, community_id: int) -> Community:
    """Load an approved community or answer 404."""
    found = get_visible_community(db, user, community_id)
    if found.status != "approved":
        raise ApiError("COMMUNITY_NOT_FOUND")
    return found


# --- posts -----------------------------------------------------------------------


def _visible(user: User, post) -> ColumnElement[bool]:
    """The audience rule for one post table or alias."""
    not_deleted = post.author_id.in_(select(User.id).where(User.deleted_at.is_(None)))
    own = and_(post.author_id == user.id, post.status.in_(("visible", "hidden")))
    if user.role == "moderator":
        return or_(own, and_(not_deleted, post.status != "deleted"))
    my_communities = select(Membership.community_id).where(
        Membership.user_id == user.id, Membership.status == "active"
    )
    my_followed = select(Follow.followed_id).where(Follow.follower_id == user.id, Follow.status == "active")
    in_audience = or_(
        post.visibility == "campus",
        and_(post.visibility == "community", post.community_id.in_(my_communities)),
        and_(post.visibility == "followers", post.author_id.in_(my_followed)),
    )
    others = and_(
        not_deleted, post.status == "visible", post.author_id.not_in(blocked_ids(user.id)), in_audience
    )
    return or_(own, others)


def visible_posts(user: User) -> ColumnElement[bool]:
    """SQL condition on Post: the user is in the audience. A reshare needs its original visible too."""
    original = aliased(Post)
    original_visible = exists().where(original.id == Post.reshare_of_id, _visible(user, original))
    return and_(_visible(user, Post), or_(Post.reshare_of_id.is_(None), original_visible))


def can_view_post(db: Session, user: User, post_id: int) -> bool:
    """True if the user is in the audience of the post."""
    return db.scalar(select(exists().where(Post.id == post_id, visible_posts(user))))


def get_visible_post(db: Session, user: User, post_id: int) -> Post:
    """Load a post; the same 404 for missing and not allowed, so hidden posts cannot be probed."""
    post = db.scalar(select(Post).where(Post.id == post_id, visible_posts(user)))
    if post is None:
        raise ApiError("POST_NOT_FOUND")
    return post


def get_interactive_post(db: Session, user: User, post_id: int) -> Post:
    """Load a post the user may comment on, react to, reshare or RSVP to (view before interact)."""
    post = get_visible_post(db, user, post_id)
    require_not_muted(db, user)
    if post.status != "visible":
        raise ApiError("CONTENT_FROZEN")
    return post


def get_own_post(db: Session, user: User, post_id: int) -> Post:
    """Load a post the user may edit."""
    post = get_interactive_post(db, user, post_id)
    if post.author_id != user.id:
        raise ApiError("NOT_AUTHOR")
    return post


def require_can_publish(db: Session, user: User, community_id: int | None) -> None:
    """Who may create posts and discussions, and where."""
    if user.role == "admin":
        raise ApiError("ROLE_NOT_ALLOWED")
    require_not_muted(db, user)
    if community_id is not None:
        get_open_community(db, user, community_id)
        if membership(db, user, community_id) is None:
            raise ApiError("NOT_A_MEMBER")


# --- comments --------------------------------------------------------------------


def visible_comments(user: User) -> ColumnElement[bool]:
    """SQL condition on Comment, to be combined with visibility of the parent post."""
    own = and_(Comment.author_id == user.id, Comment.status.in_(("visible", "hidden")))
    if user.role == "moderator":
        return or_(own, Comment.status != "deleted")
    return or_(
        own,
        and_(
            Comment.status == "visible",
            Comment.author_id.not_in(blocked_ids(user.id)),
            Comment.author_id.in_(select(User.id).where(User.deleted_at.is_(None))),
        ),
    )


def get_visible_comment(db: Session, user: User, comment_id: int) -> Comment:
    """Load a comment whose post is visible, or answer 404."""
    comment = db.scalar(select(Comment).where(Comment.id == comment_id, visible_comments(user)))
    if comment is None or not can_view_post(db, user, comment.post_id):
        raise ApiError("COMMENT_NOT_FOUND")
    return comment


# --- drafts ----------------------------------------------------------------------


def may_write_drafts(db: Session, user: User, community_id: int | None) -> bool:
    """Officers write for their community, admins for the whole campus (community_id null)."""
    if community_id is None:
        return user.role == "admin"
    return is_officer(db, user, community_id)


def get_editable_draft(db: Session, user: User, draft_id: int) -> Draft:
    """Load a draft for a collaborator who still has the required role, or answer 404."""
    draft = db.scalar(
        select(Draft)
        .join(DraftCollaborator)
        .where(Draft.id == draft_id, DraftCollaborator.user_id == user.id)
    )
    if draft is None or not may_write_drafts(db, user, draft.community_id):
        raise ApiError("DRAFT_NOT_FOUND")
    return draft


# --- direct messages -------------------------------------------------------------


def get_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    """Load a conversation for one of its two participants; nobody else, moderators included."""
    found = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            or_(Conversation.user_a_id == user.id, Conversation.user_b_id == user.id),
        )
    )
    if found is None:
        raise ApiError("CONVERSATION_NOT_FOUND")
    return found


def require_can_message(db: Session, user: User, other: User) -> None:
    """Students and officers only, not blocked, not muted."""
    if user.role != "user" or other.role != "user":
        raise ApiError("ROLE_NOT_ALLOWED")
    require_not_muted(db, user)
    if is_blocked(db, user.id, other.id) or other.deleted_at is not None:
        raise ApiError("BLOCKED")


# --- live channels ---------------------------------------------------------------


def can_subscribe(db: Session, user: User, channel: str) -> bool:
    """May this user listen to the channel? Checked on subscribe and before every event."""
    kind, _, ident = channel.partition(":")
    if kind == "feed":
        return True
    if kind == "moderation":
        return user.role == "moderator"
    if kind == "user":
        return ident == str(user.id)
    if kind == "community" and ident.isdecimal():
        return membership(db, user, int(ident)) is not None
    if kind == "post" and ident.isdecimal():
        return can_view_post(db, user, int(ident))
    return False

"""Comments and replies (FR-INT-1, FR-MOD-7)."""

from datetime import timedelta

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import policy
from app.audit import log
from app.auth.sessions import CurrentUser, Db
from app.content.schemas import CommentInput, CommentOut, CommentUpdate
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import Comment, ModerationAction, Post, Report, User
from app.notifications.service import notify, notify_mentions
from app.realtime.hub import LiveEvent
from app.schemas import ApiInput, ReportReason

router = APIRouter(tags=["comments"])
EDIT_WINDOW = timedelta(minutes=15)


class OfficerHide(ApiInput):
    """Why an officer hides a comment and whether campus moderators should look at it."""

    reason: ReportReason
    explanation: str = Field(min_length=1, max_length=500)
    escalate: bool = False


def emit_comment(db: Session, comment: Comment, name: str) -> None:
    """Announce a change of a comment on its post's channel."""
    emit(
        db, LiveEvent(f"post:{comment.post_id}", name, {"post_id": comment.post_id, "comment_id": comment.id})
    )


def _check_open(post: Post) -> None:
    if not post.comments_enabled:
        raise ApiError("COMMENTS_DISABLED")
    if post.locked:
        raise ApiError("LOCKED")


def _own_comment(db: Session, user: User, comment_id: int) -> Comment:
    comment = policy.get_visible_comment(db, user, comment_id)
    policy.require_not_muted(db, user)
    if comment.author_id != user.id:
        raise ApiError("NOT_AUTHOR")
    if comment.status != "visible":
        raise ApiError("CONTENT_FROZEN")
    return comment


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut], responses=errors("POST_NOT_FOUND"))
def list_comments(post_id: int, user: CurrentUser, db: Db):
    """List comments, oldest first. Comments by blocked users are left out.

    **Role:** in the audience of the post.
    """
    policy.get_visible_post(db, user, post_id)
    return db.scalars(
        select(Comment).where(Comment.post_id == post_id, policy.visible_comments(user)).order_by(Comment.id)
    ).all()


@router.post(
    "/posts/{post_id}/comments",
    status_code=201,
    response_model=CommentOut,
    responses=errors(
        "MUTED", "COMMENTS_DISABLED", "POST_NOT_FOUND", "COMMENT_NOT_FOUND", "CONTENT_FROZEN", "LOCKED"
    ),
)
def create_comment(post_id: int, body: CommentInput, user: CurrentUser, db: Db):
    """Comment on a post, or reply to a top-level comment (one level of replies).

    **Role:** in the audience, not muted.
    """
    post = policy.get_interactive_post(db, user, post_id)
    _check_open(post)
    recipients = {post.author_id}
    if body.parent_id is not None:
        parent = policy.get_visible_comment(db, user, body.parent_id)
        if parent.post_id != post_id or parent.parent_id is not None:
            raise ApiError("COMMENT_NOT_FOUND")
        recipients.add(parent.author_id)
    comment = Comment(post_id=post_id, author_id=user.id, body=body.body, parent_id=body.parent_id)
    db.add(comment)
    db.flush()
    for user_id in recipients - {user.id}:
        if not policy.is_blocked(db, user.id, user_id):
            notify(db, user_id, "reply", f"{user.display_name} replied to you.", post)
    notify_mentions(db, user, comment.body, post)
    emit_comment(db, comment, "comment.created")
    db.commit()
    return comment


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentOut,
    responses=errors(
        "MUTED", "NOT_AUTHOR", "COMMENTS_DISABLED", "COMMENT_NOT_FOUND", "CONTENT_FROZEN",
        "EDIT_WINDOW_CLOSED", "LOCKED",
    ),
)  # fmt: skip
def update_comment(comment_id: int, body: CommentUpdate, user: CurrentUser, db: Db):
    """Edit a comment within 15 minutes of writing it.

    **Role:** author, not muted.
    """
    comment = _own_comment(db, user, comment_id)
    _check_open(policy.get_interactive_post(db, user, comment.post_id))
    if now() - comment.created_at > EDIT_WINDOW:
        raise ApiError("EDIT_WINDOW_CLOSED")
    comment.body = body.body
    comment.edited_at = now()
    emit_comment(db, comment, "comment.updated")
    db.commit()
    return comment


@router.delete(
    "/comments/{comment_id}",
    status_code=204,
    responses=errors("MUTED", "NOT_AUTHOR", "COMMENT_NOT_FOUND", "CONTENT_FROZEN"),
)
def delete_comment(comment_id: int, user: CurrentUser, db: Db):
    """Delete a comment.

    **Role:** author, not muted.
    """
    comment = _own_comment(db, user, comment_id)
    comment.status = "deleted"
    comment.removed_at = now()
    emit_comment(db, comment, "comment.removed")
    db.commit()


@router.post(
    "/comments/{comment_id}/officer-hide",
    status_code=204,
    responses=errors("NOT_AN_OFFICER", "NOT_YOURSELF", "COMMENT_NOT_FOUND", "CONTENT_FROZEN"),
)
def officer_hide_comment(comment_id: int, body: OfficerHide, user: CurrentUser, db: Db):
    """Hide a comment in the officer's own community and optionally escalate it to moderators.

    **Role:** officer of the community the post belongs to. The author is told and may appeal.
    """
    comment = policy.get_visible_comment(db, user, comment_id)
    policy.require_officer(db, user, comment.post.community_id)
    if comment.author_id == user.id:
        raise ApiError("NOT_YOURSELF")
    if comment.status != "visible":
        raise ApiError("CONTENT_FROZEN")
    comment.status = "hidden"
    action = ModerationAction(
        actor_id=user.id,
        target_type="comment",
        target_id=comment.id,
        target_user_id=comment.author_id,
        action="hide",
        reason=body.reason,
        explanation=body.explanation,
    )
    db.add(action)
    db.flush()
    if body.escalate:
        db.merge(_escalation(db, comment, body, user))
        emit(db, LiveEvent("moderation", "report.created"))
    notify(
        db,
        comment.author_id,
        "system_notice",
        f"An officer hid your comment ({body.reason}): {body.explanation}",
        action_id=action.id,
    )
    log.record(db, user, "officer.hide", f"comment:{comment.id}", body.explanation, escalated=body.escalate)
    emit_comment(db, comment, "comment.removed")
    db.commit()


def _escalation(db: Session, comment: Comment, body: OfficerHide, user: User) -> Report:
    """A report by the officer; reuses the officer's earlier report about the same comment."""
    key = {"reporter_id": user.id, "target_type": "comment", "target_id": comment.id}
    existing = db.scalar(select(Report).filter_by(**key))
    return existing or Report(
        **key, target_user_id=comment.author_id, reason=body.reason, note=body.explanation, triage="unscored"
    )

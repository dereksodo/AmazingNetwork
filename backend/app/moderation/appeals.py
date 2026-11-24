"""Appeals against moderation actions (FR-MOD-5)."""

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit import log
from app.auth.sessions import CurrentUser, Db, Moderator
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import Appeal, Comment, ModerationAction, Post, Report, Sanction
from app.moderation.actions import STATUS_FOR, action_out, set_target_status
from app.moderation.schemas import ActionOut, AppealDecision, AppealInput, AppealOut
from app.notifications.service import notify
from app.realtime.hub import LiveEvent
from app.schemas import UserRef

router = APIRouter(tags=["moderation"])
APPEAL_WINDOW = timedelta(days=7)


def _target_text(db: Session, action: ModerationAction) -> str:
    """What the action was about."""
    if action.target_type == "post":
        return db.get(Post, action.target_id).body_html
    if action.target_type == "comment":
        return db.get(Comment, action.target_id).body
    report = db.get(Report, action.report_id)
    return "\n".join(message.body_copy for message in report.messages) or report.note


def appeal_out(db: Session, appeal: Appeal) -> AppealOut:
    """Describe an appeal."""
    return AppealOut(
        id=appeal.id,
        statement=appeal.statement,
        status=appeal.status,
        created_at=appeal.created_at,
        action=action_out(appeal.action),
        appellant=UserRef.model_validate(appeal.action.target_user),
        target_text=_target_text(db, appeal.action),
    )


@router.get("/me/moderation-actions", response_model=list[ActionOut], responses=errors())
def list_my_actions(user: CurrentUser, db: Db):
    """List actions taken against the caller, newest first, with the state of their appeal.

    **Role:** signed in.
    """
    found = db.scalars(
        select(ModerationAction)
        .where(ModerationAction.target_user_id == user.id, ModerationAction.action != "dismiss")
        .order_by(ModerationAction.id.desc())
    )
    return [action_out(action) for action in found.all()]


@router.post(
    "/appeals",
    status_code=201,
    response_model=AppealOut,
    responses=errors("ACTION_NOT_FOUND", "ALREADY_APPEALED", "APPEAL_WINDOW_CLOSED"),
)
def file_appeal(body: AppealInput, user: CurrentUser, db: Db):
    """Appeal an action once within 7 days.

    **Role:** the affected user.
    """
    action = db.get(ModerationAction, body.action_id)
    if action is None or action.target_user_id != user.id or action.action == "dismiss":
        raise ApiError("ACTION_NOT_FOUND")
    if action.appeal is not None:
        raise ApiError("ALREADY_APPEALED")
    if now() - action.created_at > APPEAL_WINDOW:
        raise ApiError("APPEAL_WINDOW_CLOSED")
    appeal = Appeal(action=action, statement=body.statement)
    db.add(appeal)
    emit(db, LiveEvent("moderation", "appeal.created"))
    db.commit()
    return appeal_out(db, appeal)


@router.get("/moderation/appeals", response_model=list[AppealOut], responses=errors("NOT_MODERATOR"))
def list_appeals(moderator: Moderator, db: Db):
    """List pending appeals the caller may decide, oldest first.

    **Role:** moderator; appeals against their own actions or by themselves are left out.
    """
    found = db.scalars(
        select(Appeal)
        .join(ModerationAction)
        .where(
            Appeal.status == "pending",
            ModerationAction.actor_id != moderator.id,
            ModerationAction.target_user_id != moderator.id,
        )
        .order_by(Appeal.id)
    )
    return [appeal_out(db, appeal) for appeal in found.all()]


@router.post(
    "/moderation/appeals/{appeal_id}/decision",
    response_model=AppealOut,
    responses=errors(
        "NOT_YOURSELF", "NOT_MODERATOR", "SAME_MODERATOR", "APPEAL_NOT_FOUND", "ALREADY_DECIDED"
    ),
)
def decide_appeal(appeal_id: int, body: AppealDecision, moderator: Moderator, db: Db):
    """Uphold or overturn. Overturning restores the content or lifts the mute; the decision is final.

    **Role:** moderator other than the one who acted, and not the appellant.
    """
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise ApiError("APPEAL_NOT_FOUND")
    action = appeal.action
    if action.actor_id == moderator.id:
        raise ApiError("SAME_MODERATOR")
    if action.target_user_id == moderator.id:
        raise ApiError("NOT_YOURSELF")
    won = db.execute(
        update(Appeal)
        .where(Appeal.id == appeal_id, Appeal.status == "pending")
        .values(status=body.outcome, reviewer_id=moderator.id)
    )
    if won.rowcount == 0:
        raise ApiError("ALREADY_DECIDED")
    if body.outcome == "overturned":
        if action.action in STATUS_FOR:
            set_target_status(db, action, "visible")
        db.execute(update(Sanction).where(Sanction.action_id == action.id).values(ends_at=now()))
    notify(
        db,
        action.target_user_id,
        "appeal_result",
        f"Your appeal was decided: {body.outcome}. {body.reason}",
        action_id=action.id,
    )
    log.record(db, moderator, f"appeal.{body.outcome}", f"action:{action.id}", body.reason)
    emit(db, LiveEvent("moderation", "appeal.decided", {"appeal_id": appeal_id}))
    db.commit()
    return appeal_out(db, appeal)

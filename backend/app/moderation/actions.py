"""The moderation queue and decisions about reports (FR-MOD-2, 3, 4, FR-AI-2, 5)."""

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.ai.provider import Provider
from app.ai.triage import run_triage, target_text
from app.audit import log
from app.auth.sessions import Db, Moderator
from app.content.comments import emit_comment
from app.content.posts import emit_post
from app.db import emit, now
from app.errors import ApiError, errors
from app.models import AiSuggestion, Comment, ModerationAction, Post, Report, Sanction
from app.moderation.schemas import ActionInput, ActionOut, ReportOut, ReportReceipt, SuggestionOut
from app.notifications.service import notify
from app.realtime.hub import LiveEvent
from app.schemas import UserRef

router = APIRouter(tags=["moderation"], prefix="/moderation")
STATUS_FOR = {"hide": "hidden", "remove": "removed"}
NOTICE_FOR = {
    "hide": "Your {target} was hidden",
    "remove": "Your {target} was removed",
    "notice": "Notice from Connect Moderation",
    "mute": "You are muted for {hours} hours",
}


def report_out(db: Session, report: Report) -> ReportOut:
    """Describe a report to a moderator."""
    return ReportOut(
        id=report.id,
        target_type=report.target_type,
        target_id=report.target_id,
        target_user=UserRef.model_validate(report.target_user),
        target_text=target_text(db, report),
        reason=report.reason,
        note=report.note,
        status=report.status,
        triage=report.triage,
        suggestion=report.suggestion and SuggestionOut.model_validate(report.suggestion),
        report_count=db.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.target_type == report.target_type, Report.target_id == report.target_id)
        ),
        created_at=report.created_at,
    )


def action_out(action: ModerationAction) -> ActionOut:
    """Describe an action."""
    return ActionOut(
        id=action.id,
        action=action.action,
        target_type=action.target_type,
        target_id=action.target_id,
        reason=action.reason,
        explanation=action.explanation,
        created_at=action.created_at,
        appeal_status=action.appeal.status if action.appeal else "none",
    )


def set_target_status(db: Session, action: ModerationAction, status: str) -> None:
    """Hide, remove or restore the post or comment of an action and tell open browsers."""
    if action.target_type == "post":
        post = db.get(Post, action.target_id)
        post.status = status
        post.removed_at = now() if status == "removed" else None
        db.flush()
        emit_post(db, post, "post.created" if status == "visible" else "post.removed")
    else:
        comment = db.get(Comment, action.target_id)
        comment.status = status
        comment.removed_at = now() if status == "removed" else None
        emit_comment(db, comment, "comment.created" if status == "visible" else "comment.removed")


@router.get("/queue", response_model=list[ReportOut], responses=errors("NOT_MODERATOR"))
def list_queue(moderator: Moderator, db: Db):
    """List open reports: high severity first, then unscored, medium and low; oldest first within each.

    **Role:** moderator. Unscored reports come second because they might be urgent.
    """
    rank = case({"high": 0, "medium": 2, "low": 3}, value=AiSuggestion.severity, else_=1)
    found = db.scalars(
        select(Report)
        .outerjoin(AiSuggestion)
        .where(Report.status == "open")
        .order_by(rank, Report.created_at, Report.id)
    )
    return [report_out(db, report) for report in found.all()]


@router.post(
    "/reports/{report_id}/triage",
    status_code=202,
    response_model=ReportReceipt,
    responses=errors("NOT_MODERATOR", "REPORT_NOT_FOUND"),
)
def retry_triage(report_id: int, tasks: BackgroundTasks, moderator: Moderator, db: Db, provider: Provider):
    """Ask the AI again about an unscored report.

    **Role:** moderator.
    """
    started = db.execute(
        update(Report)
        .where(Report.id == report_id, Report.status == "open", Report.triage == "unscored")
        .values(triage="pending")
    )
    if started.rowcount == 0:
        raise ApiError("REPORT_NOT_FOUND")
    db.commit()
    tasks.add_task(run_triage, report_id, provider)
    return db.get(Report, report_id)


@router.post(
    "/reports/{report_id}/actions",
    status_code=201,
    response_model=ActionOut,
    responses=errors(
        "VALIDATION_ERROR", "ACTION_NOT_ALLOWED", "NOT_YOURSELF", "NOT_MODERATOR", "REPORT_NOT_FOUND",
        "ALREADY_DECIDED",
    ),
)  # fmt: skip
def decide(report_id: int, body: ActionInput, moderator: Moderator, db: Db):
    """Decide a report. Exactly one of several simultaneous decisions succeeds.

    **Role:** moderator, not the reported user. Writes the audit entry in the same transaction.
    """
    report = db.get(Report, report_id)
    if report is None:
        raise ApiError("REPORT_NOT_FOUND")
    if report.target_user_id == moderator.id:
        raise ApiError("NOT_YOURSELF")
    if body.action in STATUS_FOR and report.target_type not in ("post", "comment"):
        raise ApiError("ACTION_NOT_ALLOWED")
    if (body.mute_hours is None) == (body.action == "mute"):
        raise ApiError("VALIDATION_ERROR")
    if (body.ai_agreed is None) == (report.suggestion is not None):
        raise ApiError("VALIDATION_ERROR")
    won = db.execute(
        update(Report)
        .where(Report.id == report_id, Report.status == "open")
        .values(status="dismissed" if body.action == "dismiss" else "actioned")
    )
    if won.rowcount == 0:
        raise ApiError("ALREADY_DECIDED")
    action = ModerationAction(
        report_id=report_id,
        actor_id=moderator.id,
        target_type=report.target_type,
        target_id=report.target_id,
        target_user_id=report.target_user_id,
        action=body.action,
        reason=body.reason,
        explanation=body.explanation,
    )
    db.add(action)
    db.flush()
    if report.suggestion:
        report.suggestion.moderator_agreed = body.ai_agreed
    if body.action in STATUS_FOR:
        set_target_status(db, action, STATUS_FOR[body.action])
    if body.action == "mute":
        ends_at = now() + timedelta(hours=body.mute_hours)
        db.add(Sanction(user_id=report.target_user_id, action_id=action.id, ends_at=ends_at))
    if body.action in NOTICE_FOR:
        heading = NOTICE_FOR[body.action].format(target=report.target_type, hours=body.mute_hours)
        text = f"{heading} ({body.reason}): {body.explanation}"
        notify(db, report.target_user_id, "system_notice", text, action_id=action.id)
    target = f"{report.target_type}:{report.target_id}"
    log.record(db, moderator, f"report.{body.action}", target, body.explanation, report_id=report_id)
    emit(db, LiveEvent("moderation", "report.decided", {"report_id": report_id}))
    db.commit()
    return action_out(action)

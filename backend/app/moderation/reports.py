"""Filing reports (FR-MOD-1, FR-MOD-8, FR-AI-1)."""

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app import policy
from app.ai.provider import Provider
from app.ai.triage import run_triage
from app.auth.sessions import CurrentUser, Db
from app.db import emit
from app.errors import ApiError, errors
from app.models import Message, Report, ReportedMessage, User
from app.moderation.schemas import ReportInput, ReportReceipt
from app.realtime.hub import LiveEvent

router = APIRouter(tags=["moderation"])


def _selected_messages(db: Session, user: User, body: ReportInput) -> list[Message]:
    """The selected messages, all written by the other participant of the caller's conversation."""
    conversation = policy.get_conversation(db, user, body.target_id)
    found = db.scalars(
        select(Message).where(
            Message.conversation_id == conversation.id,
            Message.sender_id == conversation.other(user.id),
            Message.id.in_(body.message_ids),
        )
    ).all()
    if not found or len(found) != len(set(body.message_ids)):
        raise ApiError("TARGET_NOT_FOUND")
    return list(found)


@router.post(
    "/reports",
    status_code=202,
    response_model=ReportReceipt,
    responses=errors(
        "NOT_YOURSELF", "POST_NOT_FOUND", "COMMENT_NOT_FOUND", "USER_NOT_FOUND", "CONVERSATION_NOT_FOUND",
        "TARGET_NOT_FOUND", "DUPLICATE_REPORT",
    ),
)  # fmt: skip
def file_report(body: ReportInput, tasks: BackgroundTasks, user: CurrentUser, db: Db, provider: Provider):
    """Report something to the moderators. The AI suggestion is requested after the response.

    **Role:** anyone who can see the item, except its author. For direct messages only copies of the
    selected messages are attached.
    """
    target_id, messages = body.target_id, []
    if body.target_type == "post":
        target_user_id = policy.get_visible_post(db, user, body.target_id).author_id
    elif body.target_type == "comment":
        target_user_id = policy.get_visible_comment(db, user, body.target_id).author_id
    elif body.target_type == "user":
        target_user_id = policy.get_visible_user(db, user, body.target_id).id
    else:
        messages = _selected_messages(db, user, body)
        target_user_id, target_id = messages[0].sender_id, messages[0].id
    if target_user_id == user.id:
        raise ApiError("NOT_YOURSELF")
    key = {"reporter_id": user.id, "target_type": body.target_type, "target_id": target_id}
    if db.scalar(select(exists().where(*(getattr(Report, name) == value for name, value in key.items())))):
        raise ApiError("DUPLICATE_REPORT")
    report = Report(**key, target_user_id=target_user_id, reason=body.reason, note=body.note)
    report.messages = [ReportedMessage(message_id=m.id, body_copy=m.body) for m in messages]
    db.add(report)
    emit(db, LiveEvent("moderation", "report.created"))
    db.commit()
    tasks.add_task(run_triage, report.id, provider)
    return report

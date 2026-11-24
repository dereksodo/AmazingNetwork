"""One-to-one direct messages (FR-INT-6)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response
from pydantic import Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import policy
from app.auth.sessions import CurrentUser, Db
from app.db import emit
from app.errors import ApiError, errors
from app.models import Conversation, Message, User
from app.realtime.hub import LiveEvent
from app.schemas import ApiInput, ApiModel, UserRef

router = APIRouter(tags=["messages"], prefix="/conversations")


class ConversationInput(ApiInput):
    """The person to talk to."""

    user_id: int = Field(examples=[2])


class ConversationOut(ApiModel):
    """A conversation and the other participant."""

    id: int
    other: UserRef


class MessageInput(ApiInput):
    """Plain text."""

    body: str = Field(min_length=1, max_length=2000, examples=["Are you coming on Thursday?"])


class MessageOut(ApiModel):
    """A direct message."""

    id: int
    conversation_id: int
    sender_id: int
    body: str
    created_at: datetime


def _out(db: Session, user: User, conversation: Conversation) -> ConversationOut:
    other = db.get(User, conversation.other(user.id))
    return ConversationOut(id=conversation.id, other=UserRef.model_validate(other))


@router.get("", response_model=list[ConversationOut], responses=errors())
def list_conversations(user: CurrentUser, db: Db):
    """List the caller's conversations.

    **Role:** participant.
    """
    found = db.scalars(
        select(Conversation)
        .where(or_(Conversation.user_a_id == user.id, Conversation.user_b_id == user.id))
        .order_by(Conversation.id.desc())
    )
    return [_out(db, user, conversation) for conversation in found.all()]


@router.post(
    "",
    status_code=201,
    response_model=ConversationOut,
    responses={
        200: {"model": ConversationOut, "description": "The conversation existed already."},
        **errors("NOT_YOURSELF", "ROLE_NOT_ALLOWED", "MUTED", "BLOCKED", "USER_NOT_FOUND"),
    },
)
def open_conversation(body: ConversationInput, response: Response, user: CurrentUser, db: Db):
    """Open a conversation, or return the existing one (200).

    **Role:** user (students and officers), not muted, no block. Moderators and admins have no DMs.
    """
    if body.user_id == user.id:
        raise ApiError("NOT_YOURSELF")
    other = db.get(User, body.user_id)
    if other is None:
        raise ApiError("USER_NOT_FOUND")
    policy.require_can_message(db, user, other)
    pair = {"user_a_id": min(user.id, other.id), "user_b_id": max(user.id, other.id)}
    conversation = db.scalar(select(Conversation).filter_by(**pair))
    if conversation is None:
        conversation = Conversation(**pair)
        db.add(conversation)
        db.commit()
    else:
        response.status_code = 200
    return _out(db, user, conversation)


@router.get(
    "/{conversation_id}/messages", response_model=list[MessageOut], responses=errors("CONVERSATION_NOT_FOUND")
)
def list_messages(
    conversation_id: int,
    user: CurrentUser,
    db: Db,
    before: Annotated[int | None, Query(description="Return messages older than this message id")] = None,
):
    """Return up to 50 messages, oldest first.

    **Role:** participant. Moderators get 404 like everyone else (FR-MOD-8).
    """
    policy.get_conversation(db, user, conversation_id)
    query = select(Message).where(Message.conversation_id == conversation_id)
    if before is not None:
        query = query.where(Message.id < before)
    return list(reversed(db.scalars(query.order_by(Message.id.desc()).limit(50)).all()))


@router.post(
    "/{conversation_id}/messages",
    status_code=201,
    response_model=MessageOut,
    responses=errors("ROLE_NOT_ALLOWED", "MUTED", "BLOCKED", "CONVERSATION_NOT_FOUND"),
)
def send_message(conversation_id: int, body: MessageInput, user: CurrentUser, db: Db):
    """Send a message; both participants get a live event.

    **Role:** participant, not muted, no block in either direction.
    """
    conversation = policy.get_conversation(db, user, conversation_id)
    other = db.get(User, conversation.other(user.id))
    policy.require_can_message(db, user, other)
    message = Message(conversation_id=conversation_id, sender_id=user.id, body=body.body)
    db.add(message)
    for user_id in (user.id, other.id):
        emit(db, LiveEvent(f"user:{user_id}", "message.created", {"conversation_id": conversation_id}))
    db.commit()
    return message

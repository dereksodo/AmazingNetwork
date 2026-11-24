"""The /ws channel: authentication, subscriptions and live events (docs/websocket.md)."""

from typing import Annotated, Literal

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from app import policy
from app.auth.sessions import user_for_token
from app.db import SessionLocal
from app.realtime.hub import Client, hub

router = APIRouter()


class AuthFrame(BaseModel):
    """First frame of every connection."""

    type: Literal["auth"]
    token: str


class SubscribeFrame(BaseModel):
    """Start or stop listening to a channel."""

    type: Literal["subscribe", "unsubscribe"]
    channel: str


class PingFrame(BaseModel):
    """Keep-alive."""

    type: Literal["ping"]


ClientFrame = TypeAdapter(Annotated[SubscribeFrame | PingFrame, Field(discriminator="type")])


def authenticate(token: str) -> int | None:
    """User id for a session token."""
    with SessionLocal() as db:
        user = user_for_token(db, token)
        return user and user.id


async def accept_authenticated(socket: WebSocket) -> tuple[str, int] | None:
    """Accept the socket and read the auth frame; closes with 4401 if it is not valid."""
    await socket.accept()
    try:
        frame = AuthFrame.model_validate_json(await socket.receive_text())
    except ValidationError:
        await socket.close(4401, "UNAUTHENTICATED")
        return None
    user_id = await run_in_threadpool(authenticate, frame.token)
    if user_id is None:
        await socket.close(4401, "UNAUTHENTICATED")
        return None
    return frame.token, user_id


def subscribe_result(client: Client, channel: str) -> str:
    """Check a subscription and name the reply frame."""
    with SessionLocal() as db:
        user = user_for_token(db, client.token)
        if user is None:
            return "signed_out"
        return "subscribed" if policy.can_subscribe(db, user, channel) else "error"


async def handle_frame(client: Client, text: str) -> None:
    """Answer one client frame."""
    try:
        frame = ClientFrame.validate_json(text)
    except ValidationError:
        await client.socket.send_json({"type": "error", "code": "INVALID_FRAME"})
        return
    if frame.type == "ping":
        await client.socket.send_json({"type": "pong"})
    elif frame.type == "unsubscribe":
        client.channels.discard(frame.channel)
        await client.socket.send_json({"type": "unsubscribed", "channel": frame.channel})
    else:
        result = await run_in_threadpool(subscribe_result, client, frame.channel)
        if result == "signed_out":
            await hub.drop(client, 4401, "UNAUTHENTICATED")
        elif result == "subscribed":
            client.channels.add(frame.channel)
            await client.socket.send_json({"type": "subscribed", "channel": frame.channel})
        else:
            await client.socket.send_json({"type": "error", "code": "FORBIDDEN", "channel": frame.channel})


@router.websocket("/ws")
async def live_channel(socket: WebSocket) -> None:
    """Live events for one browser tab."""
    identity = await accept_authenticated(socket)
    if identity is None:
        return
    token, user_id = identity
    client = Client(socket, token, user_id, {"feed", f"user:{user_id}"})
    hub.clients.add(client)
    try:
        await socket.send_json({"type": "ready", "user_id": user_id})
        while True:
            await handle_frame(client, await socket.receive_text())
    finally:
        hub.clients.discard(client)

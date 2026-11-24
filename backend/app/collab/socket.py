"""The /ws/drafts/{id} channel: Yjs synchronisation between editors (docs/websocket.md)."""

from base64 import b64encode
from typing import Annotated, Literal

from fastapi import APIRouter, WebSocket
from pydantic import Base64Bytes, BaseModel, Field, TypeAdapter, ValidationError
from sqlalchemy import update
from starlette.concurrency import run_in_threadpool

from app.collab import rooms, ydoc
from app.collab.rooms import Editor
from app.db import SessionLocal
from app.models import Draft, User
from app.realtime.router import PingFrame, accept_authenticated

router = APIRouter()


class SyncFrame(BaseModel):
    """Ask for everything missing from the client's document."""

    type: Literal["sync"]
    state_vector: Base64Bytes


class UpdateFrame(BaseModel):
    """A change of the document."""

    type: Literal["update"]
    update: Base64Bytes


class AwarenessFrame(BaseModel):
    """Cursor position; relayed, never stored."""

    type: Literal["awareness"]
    update: str = Field(max_length=20000)


Frame = TypeAdapter(
    Annotated[SyncFrame | UpdateFrame | AwarenessFrame | PingFrame, Field(discriminator="type")]
)


def encode(data: bytes) -> str:
    """Base64 text for a JSON frame."""
    return b64encode(data).decode()


def sync_reply(draft_id: int, state_vector: bytes) -> dict:
    """What the client misses, and the server's own state vector so that it can answer likewise."""
    with SessionLocal() as db:
        draft = db.get(Draft, draft_id)
        doc = ydoc.load(draft.ydoc)
        return {
            "type": "sync",
            "update": encode(doc.get_update(state_vector)),
            "state_vector": encode(doc.get_state()),
            "version": draft.version,
        }


def store_update(draft_id: int, data: bytes) -> int | None:
    """Merge and save an update; returns the new version, or None if the draft was published."""
    with SessionLocal() as db:
        draft = db.get(Draft, draft_id)
        saved = db.execute(
            update(Draft)
            .where(Draft.id == draft_id, Draft.status == "editing")
            .values(ydoc=ydoc.merge(draft.ydoc, data), version=draft.version + 1)
        )
        db.commit()
        return draft.version if saved.rowcount else None


async def handle_frame(editor: Editor, text: str) -> None:
    """Answer one frame of an editor who was checked just before."""
    try:
        frame = Frame.validate_json(text)
    except ValidationError:
        await editor.socket.send_json({"type": "error", "code": "INVALID_FRAME"})
        return
    draft_id = editor.draft_id
    if frame.type == "ping":
        await editor.socket.send_json({"type": "pong"})
    elif frame.type == "sync":
        await editor.socket.send_json(await run_in_threadpool(sync_reply, draft_id, frame.state_vector))
    elif frame.type == "awareness":
        await rooms.broadcast(draft_id, {"type": "awareness", "update": frame.update}, editor)
    else:
        async with rooms.rooms[draft_id].lock:
            version = await run_in_threadpool(store_update, draft_id, frame.update)
            if version is None:
                await editor.socket.close(rooms.PUBLISHED, "ALREADY_PUBLISHED")
                return
            await editor.socket.send_json({"type": "ack", "version": version})
            change = {"type": "update", "update": encode(frame.update), "version": version}
            await rooms.broadcast(draft_id, change, editor)


def load_name(user_id: int) -> str:
    """Display name for the presence list."""
    with SessionLocal() as db:
        return db.get(User, user_id).display_name


@router.websocket("/ws/drafts/{draft_id}")
async def draft_channel(socket: WebSocket, draft_id: int) -> None:
    """Co-editing channel of one draft."""
    identity = await accept_authenticated(socket)
    if identity is None:
        return
    token, user_id = identity
    code = await run_in_threadpool(rooms.refusal, token, draft_id)
    if code is not None:
        await socket.close(code)
        return
    editor = Editor(socket, token, draft_id, user_id, await run_in_threadpool(load_name, user_id))
    rooms.rooms[draft_id].editors.add(editor)
    try:
        await rooms.broadcast_presence(draft_id)
        while True:
            text = await socket.receive_text()
            code = await run_in_threadpool(rooms.refusal, token, draft_id)
            if code is not None:
                await socket.close(code)
                break
            await handle_frame(editor, text)
    finally:
        rooms.leave(editor)

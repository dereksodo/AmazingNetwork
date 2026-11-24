"""Draft rooms: who is connected to which draft, and broadcasting between them."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.concurrency import run_in_threadpool

from app import policy
from app.auth.sessions import user_for_token
from app.db import SessionLocal
from app.errors import ApiError
from app.realtime.hub import hub

UNAUTHENTICATED, FORBIDDEN, PUBLISHED = 4401, 4403, 4409


@dataclass(eq=False)
class Editor:
    """One open editor."""

    socket: WebSocket
    token: str
    draft_id: int
    user_id: int
    name: str


@dataclass
class Room:
    """The editors of one draft. The lock puts their updates into one order."""

    editors: set[Editor] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


rooms: dict[int, Room] = defaultdict(Room)


def refusal(token: str, draft_id: int) -> int | None:
    """Close code if the holder of the token may not edit the draft now, else None."""
    with SessionLocal() as db:
        user = user_for_token(db, token)
        if user is None:
            return UNAUTHENTICATED
        try:
            draft = policy.get_editable_draft(db, user, draft_id)
        except ApiError:
            return FORBIDDEN
        return PUBLISHED if draft.status == "published" else None


def leave(editor: Editor) -> None:
    """Remove an editor and tell the others, also when this connection's own task is being cancelled."""
    rooms[editor.draft_id].editors.discard(editor)
    asyncio.run_coroutine_threadsafe(broadcast_presence(editor.draft_id), hub.loop)


async def broadcast(draft_id: int, frame: dict, sender: Editor | None = None) -> None:
    """Send a frame to every editor but the sender. A broken connection does not affect the others."""
    receivers = [e for e in rooms[draft_id].editors if e is not sender]
    await asyncio.gather(*(_send(e, frame) for e in receivers), return_exceptions=True)


async def _send(editor: Editor, frame: dict) -> None:
    """Send a frame to one editor, or disconnect them if they lost access."""
    code = await run_in_threadpool(refusal, editor.token, editor.draft_id)
    if code is None:
        await editor.socket.send_json(frame)
    else:
        rooms[editor.draft_id].editors.discard(editor)
        await editor.socket.close(code)


async def broadcast_presence(draft_id: int) -> None:
    """Tell everyone who is editing."""
    people = {e.user_id: e.name for e in rooms[draft_id].editors}
    users = [{"id": user_id, "display_name": name} for user_id, name in sorted(people.items())]
    await broadcast(draft_id, {"type": "presence", "users": users})


async def _close_published(draft_id: int, post_id: int) -> None:
    for editor in list(rooms[draft_id].editors):
        rooms[draft_id].editors.discard(editor)
        await editor.socket.send_json({"type": "published", "post_id": post_id})
        await editor.socket.close(PUBLISHED, "ALREADY_PUBLISHED")


def announce_published(draft_id: int, post_id: int) -> None:
    """Called from the publishing request: make every open editor read-only."""
    asyncio.run_coroutine_threadsafe(_close_published(draft_id, post_id), hub.loop)

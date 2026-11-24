"""In-process event bus (K-BUS): connected clients and delivery of live events.

Events carry identifiers only. Clients fetch the content through REST, so every
byte of content passes the REST access checks; the hub additionally checks each
recipient before announcing that something changed.
"""

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.concurrency import run_in_threadpool


@dataclass(frozen=True)
class LiveEvent:
    """Something happened on a channel. `post_id` limits delivery to that post's audience."""

    channel: str
    name: str
    data: dict = field(default_factory=dict)
    post_id: int | None = None


@dataclass(eq=False)
class Client:
    """One authenticated WebSocket connection."""

    socket: WebSocket
    token: str
    user_id: int
    channels: set[str] = field(default_factory=set)


class Hub:
    """Registry of connected clients. The loop is set when the application starts."""

    def __init__(self) -> None:
        self.clients: set[Client] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def dispatch(self, events: list[LiveEvent]) -> None:
        """Hand events from a request thread to the event loop."""
        for live_event in events:
            asyncio.run_coroutine_threadsafe(self.deliver(live_event), self.loop)

    async def deliver(self, live_event: LiveEvent) -> None:
        """Send one event to all subscribers. A connection that just broke does not affect the others."""
        subscribers = [c for c in self.clients if live_event.channel in c.channels]
        await asyncio.gather(*(self._send(c, live_event) for c in subscribers), return_exceptions=True)

    async def _send(self, client: Client, live_event: LiveEvent) -> None:
        """Send one event to one client if that client is allowed to see it right now."""
        from app.realtime.access import Verdict, check_delivery

        verdict = await run_in_threadpool(check_delivery, client, live_event)
        if verdict is Verdict.SIGNED_OUT:
            await self.drop(client, 4401, "UNAUTHENTICATED")
        elif verdict is Verdict.REVOKED:
            client.channels.discard(live_event.channel)
            await client.socket.send_json({"type": "revoked", "channel": live_event.channel})
        elif verdict is Verdict.ALLOWED:
            await client.socket.send_json(
                {
                    "type": "event",
                    "channel": live_event.channel,
                    "event": live_event.name,
                    "data": live_event.data,
                }
            )

    async def drop(self, client: Client, code: int, reason: str) -> None:
        """Close a connection from the server side."""
        self.clients.discard(client)
        await client.socket.close(code, reason)


async def client_left(_socket: WebSocket, _exc: Exception) -> None:
    """Handler for WebSocketDisconnect: closing a tab is normal, so it ends the endpoint quietly."""


hub = Hub()

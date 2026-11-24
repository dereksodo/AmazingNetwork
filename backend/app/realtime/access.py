"""Access check made for every recipient of every live event."""

from enum import Enum, auto

from app import policy
from app.auth.sessions import user_for_token
from app.db import SessionLocal
from app.realtime.hub import Client, LiveEvent


class Verdict(Enum):
    """Result of a delivery check."""

    ALLOWED = auto()
    SKIP = auto()
    REVOKED = auto()
    SIGNED_OUT = auto()


def check_delivery(client: Client, live_event: LiveEvent) -> Verdict:
    """Decide with the current database state, so lost access takes effect immediately."""
    with SessionLocal() as db:
        user = user_for_token(db, client.token)
        if user is None:
            return Verdict.SIGNED_OUT
        if not policy.can_subscribe(db, user, live_event.channel):
            return Verdict.REVOKED
        if live_event.post_id is not None and not policy.can_view_post(db, user, live_event.post_id):
            return Verdict.SKIP
        return Verdict.ALLOWED

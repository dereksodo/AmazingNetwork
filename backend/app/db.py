"""Database engine and session, plus the hook that sends live events after a commit."""

from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import DateTime, TypeDecorator, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config
from app.realtime.hub import LiveEvent, hub

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class of all tables."""


class UtcDateTime(TypeDecorator):
    """Stores aware UTC datetimes; SQLite drops the time zone, so it is restored on load."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Aware datetime to naive UTC."""
        return value and value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """Naive UTC to aware datetime."""
        return value and value.replace(tzinfo=UTC)


def now() -> datetime:
    """Current time in UTC."""
    return datetime.now(UTC)


@event.listens_for(engine, "connect")
def _configure_sqlite(connection, _record) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with SessionLocal() as db:
        yield db


def emit(db: Session, live_event: LiveEvent) -> None:
    """Queue a live event. It is sent only if the surrounding transaction commits."""
    db.info.setdefault("live_events", []).append(live_event)


@event.listens_for(SessionLocal, "after_commit")
def _send_live_events(db: Session) -> None:
    hub.dispatch(db.info.pop("live_events", []))

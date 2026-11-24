"""Session tokens and the dependencies that identify the caller of a request."""

import hashlib
import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config
from app.db import get_db, now
from app.errors import ApiError
from app.models import AuthSession, User

_bearer = HTTPBearer(auto_error=False, description="Token returned by POST /auth/login")
Db = Annotated[Session, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    """Start a session and return its token. The token itself is never stored."""
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_hash(token), user_id=user.id))
    return token


def user_for_token(db: Session, token: str) -> User | None:
    """The user of a live session; sessions end after 7 days without use (FR-ID-4)."""
    session = db.get(AuthSession, _hash(token))
    if session is None or session.last_used_at < now() - timedelta(days=config.SESSION_IDLE_DAYS):
        return None
    return db.get(User, session.user_id)


def end_session(db: Session, token: str) -> None:
    """Invalidate one session on all tabs that use it."""
    db.delete(db.get(AuthSession, _hash(token)))


def current_user(db: Db, credentials: Credentials) -> User:
    """Dependency: the signed-in caller, or 401."""
    user = credentials and user_for_token(db, credentials.credentials)
    if not user:
        raise ApiError("UNAUTHENTICATED")
    session = db.get(AuthSession, _hash(credentials.credentials))
    # Written at most once per hour: idle time is counted in days.
    if session.last_used_at < now() - timedelta(hours=1):
        session.last_used_at = now()
        db.commit()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_moderator(user: CurrentUser) -> User:
    """Dependency: the caller is a moderator."""
    if user.role != "moderator":
        raise ApiError("NOT_MODERATOR")
    return user


def require_admin(user: CurrentUser) -> User:
    """Dependency: the caller is a school admin."""
    if user.role != "admin":
        raise ApiError("NOT_ADMIN")
    return user


Moderator = Annotated[User, Depends(require_moderator)]
Admin = Annotated[User, Depends(require_admin)]

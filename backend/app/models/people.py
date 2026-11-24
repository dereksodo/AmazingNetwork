"""Users, study programmes, communities and the relationships between them."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UtcDateTime, now


class StudyProgramme(Base):
    """A degree programme a user can belong to (FR-ID-2)."""

    __tablename__ = "study_programme"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(Base):
    """A university member."""

    __tablename__ = "user"
    __table_args__ = (CheckConstraint("role IN ('user','moderator','admin')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    handle: Mapped[str] = mapped_column(String(30), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    bio: Mapped[str] = mapped_column(String(300), default="")
    programme_id: Mapped[int | None] = mapped_column(ForeignKey("study_programme.id"))
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="user")
    approve_followers: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    programme: Mapped[StudyProgramme | None] = relationship()


class AuthSession(Base):
    """A sign-in. Only the SHA-256 of the token is stored."""

    __tablename__ = "auth_session"
    token_hash: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    last_used_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)


class Community(Base):
    """A student group; visible to everyone once an admin has approved it."""

    __tablename__ = "community"
    __table_args__ = (
        CheckConstraint("join_policy IN ('open','closed')"),
        CheckConstraint("status IN ('pending','approved','rejected')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(500))
    join_policy: Mapped[str] = mapped_column(default="open")
    status: Mapped[str] = mapped_column(default="pending")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))


class Membership(Base):
    """A user's role in a community; pending until accepted for closed communities."""

    __tablename__ = "membership"
    __table_args__ = (
        CheckConstraint("role IN ('member','officer','owner')"),
        CheckConstraint("status IN ('pending','active')"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("community.id"), primary_key=True)
    role: Mapped[str] = mapped_column(default="member")
    status: Mapped[str] = mapped_column(default="active")
    user: Mapped[User] = relationship()
    community: Mapped[Community] = relationship()


class CommunityFollow(Base):
    """Following a community adds its campus posts to the feed; it grants no access."""

    __tablename__ = "community_follow"
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("community.id"), primary_key=True)


class CommunityMute(Base):
    """A muted community sends this user no notifications (FR-INT-5)."""

    __tablename__ = "community_mute"
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("community.id"), primary_key=True)


class Follow(Base):
    """One user follows another; pending if the followed user approves followers."""

    __tablename__ = "follow"
    __table_args__ = (
        CheckConstraint("status IN ('pending','active')"),
        CheckConstraint("follower_id <> followed_id"),
    )
    follower_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    status: Mapped[str] = mapped_column(default="active")


class Block(Base):
    """One user blocks another; the effect is mutual (FR-AUD-3)."""

    __tablename__ = "block"
    __table_args__ = (CheckConstraint("blocker_id <> blocked_id"),)
    blocker_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)

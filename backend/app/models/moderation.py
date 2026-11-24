"""Reports, AI suggestions, moderation actions, appeals, notifications and the audit log."""

from datetime import datetime

from sqlalchemy import DDL, JSON, CheckConstraint, ForeignKey, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UtcDateTime, now
from app.models.people import User

REASONS = "'harassment','hate','spam','sexual','violence','misinformation','other'"


class Report(Base):
    """A report about a post, comment, user or selected direct messages."""

    __tablename__ = "report"
    __table_args__ = (
        UniqueConstraint("reporter_id", "target_type", "target_id"),
        CheckConstraint("target_type IN ('post','comment','user','message')"),
        CheckConstraint(f"reason IN ({REASONS})"),
        CheckConstraint("status IN ('open','dismissed','actioned')"),
        CheckConstraint("triage IN ('pending','scored','unscored')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    target_type: Mapped[str]
    target_id: Mapped[int]
    target_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    reason: Mapped[str]
    note: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(default="open")
    triage: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    target_user: Mapped[User] = relationship(foreign_keys=target_user_id)
    messages: Mapped[list["ReportedMessage"]] = relationship()
    suggestion: Mapped["AiSuggestion | None"] = relationship()


class ReportedMessage(Base):
    """Frozen copy of a direct message the reporter chose to attach (FR-MOD-8)."""

    __tablename__ = "reported_message"
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"), primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("message.id"), primary_key=True)
    body_copy: Mapped[str] = mapped_column(String(2000))


class AiSuggestion(Base):
    """A validated suggestion of the model for one report."""

    __tablename__ = "ai_suggestion"
    __table_args__ = (
        CheckConstraint(f"category IN ({REASONS})"),
        CheckConstraint("severity IN ('low','medium','high')"),
    )
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"), primary_key=True)
    category: Mapped[str]
    severity: Mapped[str]
    rationale: Mapped[str] = mapped_column(String(300))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(20))
    moderator_agreed: Mapped[bool | None]


class ModerationAction(Base):
    """A decision by a moderator, or a comment hidden by an officer (report_id is null)."""

    __tablename__ = "moderation_action"
    __table_args__ = (CheckConstraint("action IN ('dismiss','hide','remove','notice','mute')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("report.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    target_type: Mapped[str]
    target_id: Mapped[int]
    target_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    action: Mapped[str]
    reason: Mapped[str]
    explanation: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    appeal: Mapped["Appeal | None"] = relationship(back_populates="action")
    target_user: Mapped[User] = relationship(foreign_keys=target_user_id)


class Appeal(Base):
    """The one appeal against an action, decided by a different moderator (FR-MOD-5)."""

    __tablename__ = "appeal"
    __table_args__ = (CheckConstraint("status IN ('pending','upheld','overturned')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("moderation_action.id"), unique=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    statement: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    action: Mapped[ModerationAction] = relationship(back_populates="appeal")


class Sanction(Base):
    """A timed mute created by an action (P4)."""

    __tablename__ = "sanction"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    action_id: Mapped[int] = mapped_column(ForeignKey("moderation_action.id"), unique=True)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime)


class Notification(Base):
    """A message in a user's notification list."""

    __tablename__ = "notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(String(600))
    post_id: Mapped[int | None] = mapped_column(ForeignKey("post.id"))
    action_id: Mapped[int | None] = mapped_column(ForeignKey("moderation_action.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class AuditLog(Base):
    """One moderation or admin action. Triggers refuse UPDATE and DELETE (FR-MOD-6)."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(600), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)


for _operation in ("UPDATE", "DELETE"):
    event.listen(
        AuditLog.__table__,
        "after_create",
        DDL(
            f"CREATE TRIGGER audit_log_no_{_operation.lower()} BEFORE {_operation} ON audit_log "
            "BEGIN SELECT RAISE(ABORT, 'audit_log is insert-only'); END"
        ),
    )

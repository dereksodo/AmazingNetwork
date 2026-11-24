"""Direct messages."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UtcDateTime, now


class Conversation(Base):
    """A conversation of exactly two people; the smaller user id is stored first."""

    __tablename__ = "conversation"
    __table_args__ = (UniqueConstraint("user_a_id", "user_b_id"), CheckConstraint("user_a_id < user_b_id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    def other(self, user_id: int) -> int:
        """Id of the other participant."""
        return self.user_b_id if user_id == self.user_a_id else self.user_a_id


class Message(Base):
    """One direct message."""

    __tablename__ = "message"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)

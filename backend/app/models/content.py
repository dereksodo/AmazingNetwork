"""Published content: posts with versions, images and reshares, events, comments, reactions."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UtcDateTime, now
from app.models.people import Community, User


class Post(Base):
    """A post, discussion, announcement or event."""

    __tablename__ = "post"
    __table_args__ = (
        CheckConstraint("type IN ('post','discussion','announcement','event')"),
        CheckConstraint("visibility IN ('campus','community','followers')"),
        CheckConstraint("status IN ('visible','hidden','removed','deleted')"),
        CheckConstraint("visibility <> 'community' OR community_id IS NOT NULL"),
        CheckConstraint("visibility <> 'followers' OR community_id IS NULL"),
        CheckConstraint("type = 'post' OR title IS NOT NULL"),
        CheckConstraint("reshare_of_id IS NULL OR visibility = 'campus'"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    community_id: Mapped[int | None] = mapped_column(ForeignKey("community.id"))
    reshare_of_id: Mapped[int | None] = mapped_column(ForeignKey("post.id"))
    type: Mapped[str] = mapped_column(default="post")
    visibility: Mapped[str]
    title: Mapped[str | None] = mapped_column(String(120))
    body_html: Mapped[str]
    status: Mapped[str] = mapped_column(default="visible")
    comments_enabled: Mapped[bool] = mapped_column(default=True)
    locked: Mapped[bool] = mapped_column(default=False)
    pinned: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    edited_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    removed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    author: Mapped[User] = relationship()
    community: Mapped[Community | None] = relationship()
    event: Mapped["Event | None"] = relationship(back_populates="post")
    images: Mapped[list["PostImage"]] = relationship(order_by="PostImage.id")


class PostVersion(Base):
    """The content of a post before an edit (FR-PUB-5)."""

    __tablename__ = "post_version"
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(120))
    body_html: Mapped[str]
    visibility: Mapped[str]
    replaced_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)


class PostImage(Base):
    """An uploaded image of a post (FR-PUB-1)."""

    __tablename__ = "post_image"
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"))
    content_type: Mapped[str] = mapped_column(String(20))
    alt_text: Mapped[str] = mapped_column(String(200))
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)


class Event(Base):
    """Event details of a post of type 'event'."""

    __tablename__ = "event"
    __table_args__ = (CheckConstraint("capacity > 0"), CheckConstraint("ends_at > starts_at"))
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime)
    location: Mapped[str] = mapped_column(String(120))
    capacity: Mapped[int]
    rsvp_deadline: Mapped[datetime] = mapped_column(UtcDateTime)
    cancelled: Mapped[bool] = mapped_column(default=False)
    post: Mapped[Post] = relationship(back_populates="event")


class Rsvp(Base):
    """A user's answer to an event; created_at orders the waitlist."""

    __tablename__ = "rsvp"
    __table_args__ = (CheckConstraint("status IN ('going','interested','waitlisted')"),)
    event_id: Mapped[int] = mapped_column(ForeignKey("event.post_id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)


class Comment(Base):
    """A comment or a reply to a comment."""

    __tablename__ = "comment"
    __table_args__ = (CheckConstraint("status IN ('visible','hidden','removed','deleted')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comment.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(default="visible")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now)
    edited_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    removed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    author: Mapped[User] = relationship()
    post: Mapped[Post] = relationship()


class Reaction(Base):
    """One reaction of each kind per user and post."""

    __tablename__ = "reaction"
    __table_args__ = (CheckConstraint("kind IN ('like','love','celebrate','think')"),)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(primary_key=True)

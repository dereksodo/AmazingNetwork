"""Co-edited drafts."""

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.people import Community, User


class Draft(Base):
    """An announcement or event being written; `ydoc` is the merged Yjs document state."""

    __tablename__ = "draft"
    __table_args__ = (
        CheckConstraint("kind IN ('announcement','event')"),
        CheckConstraint("status IN ('editing','published')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int | None] = mapped_column(ForeignKey("community.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    kind: Mapped[str]
    title: Mapped[str] = mapped_column(String(120))
    ydoc: Mapped[bytes] = mapped_column(LargeBinary)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(default="editing")
    published_post_id: Mapped[int | None] = mapped_column(ForeignKey("post.id"), unique=True)
    community: Mapped[Community | None] = relationship()
    collaborators: Mapped[list["DraftCollaborator"]] = relationship()


class DraftCollaborator(Base):
    """A user who may see and edit a draft."""

    __tablename__ = "draft_collaborator"
    draft_id: Mapped[int] = mapped_column(ForeignKey("draft.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    user: Mapped[User] = relationship()

"""Database tables, grouped like the ER diagrams in docs/diagrams/."""

from app.models.collaboration import Draft, DraftCollaborator
from app.models.content import Comment, Event, Post, PostImage, PostVersion, Reaction, Rsvp
from app.models.messaging import Conversation, Message
from app.models.moderation import (
    AiSuggestion,
    Appeal,
    AuditLog,
    ModerationAction,
    Notification,
    Report,
    ReportedMessage,
    Sanction,
)
from app.models.people import (
    AuthSession,
    Block,
    Community,
    CommunityFollow,
    CommunityMute,
    Follow,
    Membership,
    StudyProgramme,
    User,
)

__all__ = [
    "AiSuggestion",
    "Appeal",
    "AuditLog",
    "AuthSession",
    "Block",
    "Comment",
    "Community",
    "CommunityFollow",
    "CommunityMute",
    "Conversation",
    "Draft",
    "DraftCollaborator",
    "Event",
    "Follow",
    "Membership",
    "Message",
    "ModerationAction",
    "Notification",
    "Post",
    "PostImage",
    "PostVersion",
    "Reaction",
    "Report",
    "ReportedMessage",
    "Rsvp",
    "Sanction",
    "StudyProgramme",
    "User",
]

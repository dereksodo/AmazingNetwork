"""Bodies of the moderation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas import ApiInput, ApiModel, ReportReason, UserRef

TargetType = Literal["post", "comment", "user", "message"]


class ReportInput(ApiInput):
    """A report. For direct messages, `target_id` is the conversation and `message_ids` the selection."""

    target_type: TargetType
    target_id: int = Field(examples=[12])
    reason: ReportReason
    note: str = Field(default="", max_length=500)
    message_ids: list[int] = Field(default=[], max_length=20)


class ReportReceipt(ApiModel):
    """Confirmation for the reporter."""

    id: int
    status: Literal["open", "dismissed", "actioned"]


class SuggestionOut(ApiModel):
    """AI suggestion. It is advice; only a moderator can act."""

    category: ReportReason
    severity: Literal["low", "medium", "high"]
    rationale: str
    model: str
    moderator_agreed: bool | None


class ReportOut(ApiModel):
    """A report in the moderation queue. The reporter's identity is not shown."""

    id: int
    target_type: TargetType
    target_id: int
    target_user: UserRef
    target_text: str
    reason: ReportReason
    note: str
    status: Literal["open", "dismissed", "actioned"]
    triage: Literal["pending", "scored", "unscored"]
    suggestion: SuggestionOut | None
    report_count: int = Field(description="Reports about the same item")
    created_at: datetime


class ActionInput(ApiInput):
    """A moderator's decision."""

    action: Literal["dismiss", "hide", "remove", "notice", "mute"]
    reason: ReportReason
    explanation: str = Field(min_length=1, max_length=500, examples=["Insults another student."])
    mute_hours: Literal[24, 168, 720] | None = Field(default=None, description="Required for mute")
    ai_agreed: bool | None = Field(default=None, description="Required if there is a suggestion")


class ActionOut(ApiModel):
    """An action and its appeal, as its affected user or a moderator sees it."""

    id: int
    action: Literal["dismiss", "hide", "remove", "notice", "mute"]
    target_type: TargetType
    target_id: int
    reason: ReportReason
    explanation: str
    created_at: datetime
    appeal_status: Literal["none", "pending", "upheld", "overturned"]


class AppealInput(ApiInput):
    """An appeal by the affected user."""

    action_id: int
    statement: str = Field(min_length=1, max_length=1000)


class AppealOut(ApiModel):
    """An appeal with the action it is about."""

    id: int
    statement: str
    status: Literal["pending", "upheld", "overturned"]
    created_at: datetime
    action: ActionOut
    appellant: UserRef
    target_text: str


class AppealDecision(ApiInput):
    """Final decision."""

    outcome: Literal["upheld", "overturned"]
    reason: str = Field(min_length=1, max_length=500)

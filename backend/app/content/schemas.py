"""Bodies of the content endpoints."""

from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.schemas import ApiInput, ApiModel, UserRef

Visibility = Literal["campus", "community", "followers"]
PostType = Literal["post", "discussion", "announcement", "event"]
ReactionKind = Literal["like", "love", "celebrate", "think"]
RsvpStatus = Literal["going", "interested", "waitlisted"]
Status = Literal["visible", "hidden", "removed"]
BodyHtml = Field(
    min_length=1,
    max_length=40000,
    description="Rich text as HTML. Tags outside the allow-list are removed.",
    examples=["<h2>Meetup</h2><p>We moved to <strong>Room 204</strong>.</p>"],
)


class PostCreate(ApiInput):
    """A new post or discussion. Announcements and events are published from drafts."""

    type: Literal["post", "discussion"] = "post"
    community_id: int | None = Field(default=None, examples=[1])
    visibility: Visibility
    title: str | None = Field(default=None, min_length=1, max_length=120, examples=["CAD helper wanted"])
    body_html: str = BodyHtml
    comments_enabled: bool = True

    @model_validator(mode="after")
    def check_discussion(self) -> Self:
        """A discussion lives in a community and has a title."""
        if self.type == "discussion" and (self.community_id is None or self.title is None):
            raise ValueError("a discussion needs a community and a title")
        return self


class PostUpdate(ApiInput):
    """The new content of a post (whole content, not a partial change)."""

    visibility: Visibility
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body_html: str = BodyHtml
    comments_enabled: bool = True


class OfficerControls(ApiInput):
    """Officer settings of a community post."""

    locked: bool
    pinned: bool


class EventInput(ApiInput):
    """Event details."""

    starts_at: AwareDatetime = Field(examples=["2026-12-10T16:00:00Z"])
    ends_at: AwareDatetime = Field(examples=["2026-12-10T18:00:00Z"])
    location: str = Field(min_length=1, max_length=120, examples=["Lab 3"])
    capacity: int = Field(gt=0, examples=[40])
    rsvp_deadline: AwareDatetime = Field(examples=["2026-12-09T20:00:00Z"])

    @model_validator(mode="after")
    def check_times(self) -> Self:
        """An event ends after it starts."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventUpdate(EventInput):
    """Changed event details; `cancelled` calls the event off."""

    cancelled: bool = False


class EventOut(ApiModel):
    """Event details and the caller's RSVP."""

    starts_at: datetime
    ends_at: datetime
    location: str
    capacity: int
    rsvp_deadline: datetime
    cancelled: bool
    going: int
    waitlisted: int
    my_rsvp: RsvpStatus | None


class RsvpInput(ApiInput):
    """The caller's answer; null withdraws it."""

    status: Literal["going", "interested"] | None


class RsvpOut(ApiModel):
    """The stored answer; `going` becomes `waitlisted` when the event is full."""

    status: RsvpStatus | None


class ImageOut(ApiModel):
    """An image; fetch the bytes from /images/{id} with the bearer token."""

    id: int
    alt_text: str


class PostSummary(ApiModel):
    """The original of a reshare."""

    id: int
    author: UserRef
    title: str | None
    body_html: str
    created_at: datetime


class PostOut(ApiModel):
    """A post as the caller sees it."""

    id: int
    type: PostType
    author: UserRef
    community_id: int | None
    community_name: str | None
    visibility: Visibility
    title: str | None
    body_html: str
    status: Status
    comments_enabled: bool
    locked: bool
    pinned: bool
    version: int
    created_at: datetime
    edited_at: datetime | None
    images: list[ImageOut]
    event: EventOut | None
    reshare_of: PostSummary | None
    reactions: dict[ReactionKind, int] = Field(examples=[{"like": 3}])
    my_reactions: list[ReactionKind]
    comment_count: int


class PostPage(ApiModel):
    """One page, newest first. Pass `next_before` as `before` for the next page."""

    items: list[PostOut]
    next_before: int | None


class PostVersionOut(ApiModel):
    """Content of a post before an edit."""

    version: int
    title: str | None
    body_html: str
    visibility: Visibility
    replaced_at: datetime


class ReshareInput(ApiInput):
    """The text written above the reshared post."""

    body_html: str = BodyHtml


class CommentInput(ApiInput):
    """A comment or, with `parent_id`, a reply to a top-level comment."""

    body: str = Field(min_length=1, max_length=1000, examples=["I can help, see you there!"])
    parent_id: int | None = None


class CommentUpdate(ApiInput):
    """New text of a comment."""

    body: str = Field(min_length=1, max_length=1000)


class CommentOut(ApiModel):
    """A comment."""

    id: int
    post_id: int
    parent_id: int | None
    author: UserRef
    body: str
    status: Status
    created_at: datetime
    edited_at: datetime | None

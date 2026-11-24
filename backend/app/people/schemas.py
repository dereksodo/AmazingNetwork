"""Bodies of the identity and people endpoints."""

from typing import Literal

from pydantic import Field

from app.schemas import ApiInput, ApiModel, UserRef


class Programme(ApiModel):
    """A study programme."""

    id: int = Field(examples=[1])
    name: str = Field(examples=["BSc Computer Science"])


class Credentials(ApiInput):
    """Sign-in request."""

    email: str = Field(examples=["aisha@campus.example"])
    password: str = Field(examples=["demo-password"])


class Registration(Credentials):
    """New account."""

    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$", max_length=200, examples=["noor@campus.example"])
    password: str = Field(min_length=10, max_length=128, examples=["demo-password"])
    handle: str = Field(pattern=r"^[a-z0-9_]{3,30}$", examples=["noor"])
    display_name: str = Field(min_length=1, max_length=80, examples=["Noor Haddad"])
    programme_id: int | None = Field(default=None, examples=[1])


class Profile(UserRef):
    """A user's profile and the caller's relationship to them."""

    bio: str = Field(examples=["Second-year student."])
    role: Literal["user", "moderator", "admin"]
    programme: Programme | None
    approve_followers: bool
    follow_status: Literal["none", "pending", "active"]
    follower_count: int = Field(examples=[12])


class MyMembership(ApiModel):
    """One of the caller's communities."""

    community_id: int
    community_name: str
    role: Literal["member", "officer", "owner"]
    status: Literal["pending", "active"]


class Me(UserRef):
    """The caller."""

    email: str
    bio: str
    role: Literal["user", "moderator", "admin"]
    programme: Programme | None
    approve_followers: bool
    memberships: list[MyMembership]
    muted_until: str | None = Field(description="ISO time while a moderator's mute is active")


class SignedIn(ApiModel):
    """A new session."""

    token: str = Field(examples=["3q2-opaque-token"])
    user: Me


class ProfileUpdate(ApiInput):
    """Changed profile fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=300)
    programme_id: int | None = None
    approve_followers: bool | None = None


class FollowState(ApiModel):
    """The caller's follow relationship after the request."""

    status: Literal["pending", "active"]


class Decision(ApiInput):
    """Accept or reject a request."""

    accept: bool

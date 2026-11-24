"""Response models shared by several modules."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base of response models; reads attributes of database rows."""

    model_config = ConfigDict(from_attributes=True)


class ApiInput(BaseModel):
    """Base of request models; unknown fields are refused."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserRef(ApiModel):
    """The public identity of a user."""

    id: int = Field(examples=[1])
    handle: str = Field(examples=["aisha"])
    display_name: str = Field(examples=["Aisha Rahman"])


ReportReason = Literal["harassment", "hate", "spam", "sexual", "violence", "misinformation", "other"]

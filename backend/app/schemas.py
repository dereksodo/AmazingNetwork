"""Request/response models. Field names and limits mirror shared/contracts/openapi.yaml."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostType(str, Enum):
    post = "post"
    discussion = "discussion"


class Visibility(str, Enum):
    campus = "campus"
    community = "community"
    followers = "followers"


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PostType = PostType.post
    community_id: int | None = None
    visibility: Visibility
    title: str | None = Field(default=None, max_length=120)
    body_html: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def check_rules(self) -> "PostCreate":
        if self.visibility is Visibility.community and self.community_id is None:
            raise ValueError("community_id is required when visibility is 'community'")
        if self.visibility is Visibility.followers and self.community_id is not None:
            raise ValueError("followers-only posts are profile posts and cannot have a community_id")
        if self.type is PostType.discussion:
            if self.community_id is None:
                raise ValueError("a discussion must belong to a community")
            if not (self.title and self.title.strip()):
                raise ValueError("a discussion needs a title")
        return self


class Author(BaseModel):
    id: str
    display_name: str


class Post(BaseModel):
    id: int
    type: PostType
    author: Author
    community_id: int | None
    visibility: Visibility
    title: str | None
    body_html: str
    status: Literal["visible", "hidden", "removed"]
    version: int
    created_at: datetime


class PostList(BaseModel):
    items: list[Post]

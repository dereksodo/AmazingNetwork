"""Posts endpoints — implements contract C-POSTS (shared/contracts/openapi.yaml)."""

import nh3
from fastapi import APIRouter, Depends, Header, Query, Response

from app import policy
from app.errors import ApiError
from app.schemas import Author, Post, PostCreate, PostList
from app.store import PostRecord, Store, User

router = APIRouter(tags=["posts"])

ALLOWED_TAGS = {"p", "br", "b", "strong", "i", "em", "u", "ul", "ol", "li", "h2", "h3", "a", "blockquote", "code"}
ALLOWED_ATTRIBUTES = {"a": {"href"}}


def get_store() -> Store:
    # Replaced at startup by main.py; tests override it with a fresh store.
    raise RuntimeError("store not configured")


def current_user(
    x_demo_user: str | None = Header(default=None),
    store: Store = Depends(get_store),
) -> User:
    """PoC stand-in for SSO: the mock header names a fictional user."""
    user = store.get_user(x_demo_user) if x_demo_user else None
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in first (send X-Demo-User).")
    return user


def to_schema(store: Store, record: PostRecord) -> Post:
    author = store.get_user(record.author_id)
    return Post(
        id=record.id,
        type=record.type,
        author=Author(id=author.id, display_name=author.display_name),
        community_id=record.community_id,
        visibility=record.visibility,
        title=record.title,
        body_html=record.body_html,
        status=record.status,
        version=record.version,
        created_at=record.created_at,
    )


@router.post("/posts", status_code=201, response_model=Post)
def create_post(
    payload: PostCreate,
    response: Response,
    user: User = Depends(current_user),
    store: Store = Depends(get_store),
) -> Post:
    if payload.community_id is not None and store.get_community(payload.community_id) is None:
        raise ApiError(404, "COMMUNITY_NOT_FOUND", "That community does not exist.")
    if not policy.can_post_in(store, user, payload.community_id):
        raise ApiError(403, "NOT_A_MEMBER", "Only members can post in this community.")

    clean_html = nh3.clean(payload.body_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    if not nh3.clean(clean_html, tags=set()).strip():
        raise ApiError(400, "VALIDATION_ERROR", "The post has no text after removing unsupported content.")

    record = store.add_post(
        type=payload.type.value,
        author_id=user.id,
        community_id=payload.community_id,
        visibility=payload.visibility.value,
        title=payload.title.strip() if payload.title else None,
        body_html=clean_html,
    )
    response.headers["Location"] = f"/api/v1/posts/{record.id}"
    return to_schema(store, record)


@router.get("/posts", response_model=PostList)
def list_posts(
    community_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(current_user),
    store: Store = Depends(get_store),
) -> PostList:
    visible = [
        p
        for p in store.list_posts()
        if (community_id is None or p.community_id == community_id) and policy.can_view(store, user, p)
    ]
    return PostList(items=[to_schema(store, p) for p in visible[:limit]])


@router.get("/posts/{post_id}", response_model=Post)
def get_post(
    post_id: int,
    user: User = Depends(current_user),
    store: Store = Depends(get_store),
) -> Post:
    record = store.get_post(post_id)
    # Same 404 for "missing" and "not allowed" so hidden posts cannot be discovered.
    if record is None or not policy.can_view(store, user, record):
        raise ApiError(404, "POST_NOT_FOUND", "Post not found.")
    return to_schema(store, record)

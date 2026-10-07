"""Audience Policy component (ADR-003): the only place that decides who may see or post what.

Every endpoint (and, in the full system, the feed, search and WebSocket fan-out)
calls these functions instead of re-implementing the rules.
"""

from app.store import PostRecord, Store, User


def can_view(store: Store, user: User, post: PostRecord) -> bool:
    if post.author_id == user.id:
        return True
    if post.status != "visible":
        return user.role == "moderator"
    if store.is_blocked_between(user.id, post.author_id):
        return False
    if user.role == "moderator":
        return True
    if post.visibility == "campus":
        return True
    if post.visibility == "community":
        return post.community_id is not None and store.is_member(user.id, post.community_id)
    if post.visibility == "followers":
        return store.is_follower(user.id, post.author_id)
    return False


def can_post_in(store: Store, user: User, community_id: int | None) -> bool:
    if community_id is None:
        return True
    return store.is_member(user.id, community_id)

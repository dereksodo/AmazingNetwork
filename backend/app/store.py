"""In-memory repository with fictional seed data.

Simplification for the proof of concept: the planned system stores this in
PostgreSQL behind the same repository methods.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


@dataclass(frozen=True)
class User:
    id: str
    display_name: str
    role: str  # student | officer | moderator | admin (global role; officer is per community in the full design)


@dataclass(frozen=True)
class Community:
    id: int
    name: str


@dataclass
class PostRecord:
    id: int
    type: str
    author_id: str
    community_id: int | None
    visibility: str
    title: str | None
    body_html: str
    status: str = "visible"
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Store:
    def __init__(self) -> None:
        self._lock = Lock()
        self.users: dict[str, User] = {}
        self.communities: dict[int, Community] = {}
        self.memberships: set[tuple[str, int]] = set()  # (user_id, community_id)
        self.follows: set[tuple[str, str]] = set()  # (follower_id, followed_id)
        self.blocks: set[tuple[str, str]] = set()  # (blocker_id, blocked_id)
        self.posts: dict[int, PostRecord] = {}
        self._next_post_id = 1

    # --- reads -----------------------------------------------------------
    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_community(self, community_id: int) -> Community | None:
        return self.communities.get(community_id)

    def is_member(self, user_id: str, community_id: int) -> bool:
        return (user_id, community_id) in self.memberships

    def is_follower(self, follower_id: str, followed_id: str) -> bool:
        return (follower_id, followed_id) in self.follows

    def is_blocked_between(self, a: str, b: str) -> bool:
        return (a, b) in self.blocks or (b, a) in self.blocks

    def get_post(self, post_id: int) -> PostRecord | None:
        return self.posts.get(post_id)

    def list_posts(self) -> list[PostRecord]:
        return sorted(self.posts.values(), key=lambda p: (p.created_at, p.id), reverse=True)

    # --- writes ----------------------------------------------------------
    def add_post(self, **fields) -> PostRecord:
        with self._lock:
            record = PostRecord(id=self._next_post_id, **fields)
            self.posts[record.id] = record
            self._next_post_id += 1
            return record


def seeded_store() -> Store:
    """Fictional users and communities used by the demo and the tests."""
    s = Store()
    for user in [
        User("aisha", "Aisha (student)", "student"),
        User("omar", "Omar (student)", "student"),
        User("lina", "Lina (Robotics Club officer)", "officer"),
        User("sam", "Sam (moderator)", "moderator"),
    ]:
        s.users[user.id] = user
    s.communities[1] = Community(1, "Robotics Club")
    s.communities[2] = Community(2, "Chess Society")
    s.memberships |= {("aisha", 1), ("lina", 1), ("omar", 2)}
    s.follows |= {("omar", "aisha")}
    s.add_post(
        type="post",
        author_id="lina",
        community_id=1,
        visibility="community",
        title=None,
        body_html="<p>Welcome to the <b>Robotics Club</b> space on Connect!</p>",
    )
    return s

"""Table-driven unit tests for the Audience Policy component (ADR-003)."""

import pytest

from app import policy
from app.store import PostRecord, seeded_store


def post(visibility, community_id=None, author="aisha", status="visible"):
    return PostRecord(
        id=1, type="post", author_id=author, community_id=community_id,
        visibility=visibility, title=None, body_html="<p>x</p>", status=status,
    )


@pytest.mark.parametrize(
    "viewer, record, expected",
    [
        ("omar", post("campus"), True),
        ("omar", post("community", 1), False),  # not a member
        ("lina", post("community", 1), True),  # member
        ("omar", post("followers"), True),  # omar follows aisha
        ("lina", post("followers"), False),
        ("aisha", post("followers"), True),  # author always sees own post
        ("sam", post("community", 1), True),  # moderator
        ("omar", post("campus", status="hidden"), False),  # hidden by moderation
        ("aisha", post("campus", status="hidden"), True),  # author still sees it
    ],
)
def test_can_view(viewer, record, expected):
    store = seeded_store()
    assert policy.can_view(store, store.get_user(viewer), record) is expected


def test_can_post_in():
    store = seeded_store()
    assert policy.can_post_in(store, store.get_user("aisha"), 1)
    assert not policy.can_post_in(store, store.get_user("omar"), 1)
    assert policy.can_post_in(store, store.get_user("omar"), None)

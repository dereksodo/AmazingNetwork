"""FR-PUB and FR-INT."""

from datetime import timedelta

import pytest

from app.db import now
from app.models import Comment
from tests.conftest import code

ROBOTICS = 1
RICH = (
    "<h2>Title</h2><p><strong>bold</strong> <em>it</em> <u>under</u> <code>x</code></p>"
    "<ul><li>one</li></ul><blockquote><p>quote</p></blockquote>"
)


def test_formatting_survives_saving(api):
    post = api.new_post("aisha", RICH)
    assert api.get("omar", f"/posts/{post['id']}").json()["body_html"] == RICH


@pytest.mark.parametrize(
    "attack",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        '<a href="javascript:alert(1)">x</a>',
        '<p onclick="alert(1)">x</p>',
        "<svg/onload=alert(1)>",
        '<a href="data:text/html,<script>alert(1)</script>">x</a>',
        "<iframe src=//evil></iframe>",
    ],
)
def test_scripts_are_removed(api, attack):
    body = api.new_post("aisha", f"<p>safe</p>{attack}")["body_html"]
    for forbidden in ("script", "onerror", "onclick", "onload", "<svg", "<iframe", "<img", "data:"):
        assert forbidden not in body


@pytest.mark.parametrize("scheme", ["http://a.example", "https://a.example", "mailto:a@a.example"])
def test_allowed_links(api, scheme):
    assert f'href="{scheme}"' in api.new_post("aisha", f'<a href="{scheme}">x</a>')["body_html"]


def test_body_limits(api):
    body = {"body_html": "<script>x</script>", "visibility": "campus"}
    assert code(api.post("aisha", "/posts", body)) == (400, "EMPTY_CONTENT")
    body["body_html"] = f"<p>{'x' * 5001}</p>"
    assert code(api.post("aisha", "/posts", body)) == (400, "CONTENT_TOO_LONG")


def test_discussion_needs_title(api):
    body = {"type": "discussion", "body_html": "<p>x</p>", "visibility": "campus"}
    assert code(api.post("aisha", "/posts", body)) == (400, "VALIDATION_ERROR")


def test_edit_keeps_versions_and_refuses_stale_edits(api):
    post = api.new_post("aisha", "<p>one</p>")
    path, body = f"/posts/{post['id']}", {"body_html": "<p>two</p>", "visibility": "campus"}
    edited = api.patch("aisha", path, body, headers={"If-Match": "1"}).json()
    assert (edited["version"], edited["edited_at"] is not None) == (2, True)
    assert code(api.patch("aisha", path, body, headers={"If-Match": "1"})) == (409, "VERSION_CONFLICT")
    versions = api.get("aisha", path + "/versions").json()
    assert [(v["version"], v["body_html"]) for v in versions] == [(1, "<p>one</p>")]
    assert code(api.get("omar", path + "/versions")) == (403, "NOT_AUTHOR")


def test_deleted_post_disappears_with_its_comments(api):
    post = api.new_post("aisha")
    comment = api.post("omar", f"/posts/{post['id']}/comments", {"body": "hi"}).json()
    assert api.delete("aisha", f"/posts/{post['id']}").status_code == 204
    assert code(api.get("aisha", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")
    assert code(api.patch("omar", f"/comments/{comment['id']}", {"body": "x"})) == (404, "COMMENT_NOT_FOUND")


def test_image_limits(api):
    path = f"/posts/{api.new_post('aisha')['id']}/images"

    def upload(data):
        return api.call("POST", "aisha", path, files={"file": ("a.png", data)}, data={"alt_text": "A robot"})

    assert code(upload(b"<svg onload=alert(1)>")) == (415, "IMAGE_TYPE")
    png = b"\x89PNG\r\n\x1a\n"
    assert code(upload(png + b"0" * 5 * 1024 * 1024)) == (413, "IMAGE_TOO_LARGE")
    assert [upload(png).status_code for _ in range(4)] == [201] * 4
    assert code(upload(png)) == (409, "TOO_MANY_IMAGES")


def test_officer_locks_and_pins(api):
    posts = [api.new_post("aisha", visibility="community", community_id=ROBOTICS) for _ in range(3)]
    controls = {"locked": True, "pinned": True}
    path = f"/posts/{posts[0]['id']}"
    assert code(api.put("aisha", path + "/officer-controls", controls)) == (403, "NOT_AN_OFFICER")
    assert api.put("karim", path + "/officer-controls", controls).status_code == 200
    assert code(api.post("aisha", path + "/comments", {"body": "x"})) == (423, "LOCKED")
    api.put("karim", f"/posts/{posts[1]['id']}/officer-controls", controls)
    answer = api.put("karim", f"/posts/{posts[2]['id']}/officer-controls", controls)
    assert code(answer) == (409, "TOO_MANY_PINS")  # one post is pinned in the demo data
    assert len(api.get("aisha", f"/posts/pinned?community_id={ROBOTICS}").json()) == 3


def test_comment_rules(api, db):
    post = api.new_post("aisha")
    path = f"/posts/{post['id']}/comments"
    first = api.post("omar", path, {"body": "hi"}).json()
    reply = api.post("aisha", path, {"body": "hello", "parent_id": first["id"]}).json()
    answer = api.post("omar", path, {"body": "x", "parent_id": reply["id"]})
    assert code(answer) == (404, "COMMENT_NOT_FOUND")
    assert "Aisha Rahman replied to you." in api.notes("omar")
    edit = f"/comments/{first['id']}"
    assert code(api.patch("aisha", edit, {"body": "x"})) == (403, "NOT_AUTHOR")
    assert api.patch("omar", edit, {"body": "edited"}).json()["edited_at"]
    db.get(Comment, first["id"]).created_at = now() - timedelta(minutes=16)
    db.commit()
    assert code(api.patch("omar", edit, {"body": "late"})) == (410, "EDIT_WINDOW_CLOSED")


def test_comments_can_be_disabled(api):
    post = api.new_post("aisha", comments_enabled=False)
    answer = api.post("omar", f"/posts/{post['id']}/comments", {"body": "x"})
    assert code(answer) == (403, "COMMENTS_DISABLED")


def test_reactions_are_idempotent(api):
    path = f"/posts/{api.new_post('aisha')['id']}"
    for _ in range(2):
        api.put("omar", path + "/reactions/like")
    assert api.get("omar", path).json()["reactions"] == {"like": 1}
    api.delete("omar", path + "/reactions/like")
    assert api.get("omar", path).json()["reactions"] == {}


def test_waitlist_is_promoted_in_order(api):
    rsvp, going = "/events/6/rsvp", {"status": "going"}  # capacity 2, aisha is going
    assert api.put("omar", rsvp, going).json() == {"status": "going"}
    assert api.put("yusuf", rsvp, going).json() == {"status": "waitlisted"}
    assert api.put("karim", rsvp, going).json() == {"status": "waitlisted"}
    assert api.put("aisha", rsvp, {"status": None}).json() == {"status": None}
    assert api.get("yusuf", "/posts/6").json()["event"]["my_rsvp"] == "going"
    assert api.get("karim", "/posts/6").json()["event"]["my_rsvp"] == "waitlisted"
    assert "You have a place at an event you RSVPed to." in api.notes("yusuf")


def test_event_change_notifies_and_cancel_closes(api):
    event = api.get("karim", "/posts/6").json()["event"]
    body = {k: event[k] for k in ("starts_at", "ends_at", "location", "capacity", "rsvp_deadline")}
    assert code(api.put("aisha", "/events/6", body)) == (403, "NOT_AN_OFFICER")
    assert api.put("lina", "/events/6", {**body, "cancelled": True}).status_code == 200
    assert "“Robot open day” was cancelled." in api.notes("aisha")
    assert code(api.put("omar", "/events/6/rsvp", {"status": "going"})) == (410, "RSVP_CLOSED")


def test_feed_pages(api):
    for number in range(5):
        api.new_post("aisha", f"<p>{number}</p>")
    first = api.get("aisha", "/posts?limit=3").json()
    second = api.get("aisha", f"/posts?limit=3&before={first['next_before']}").json()
    ids = [p["id"] for p in first["items"] + second["items"]]
    assert ids == sorted(set(ids), reverse=True)


def test_direct_messages(api):
    conversation = api.get("aisha", "/conversations").json()[0]["id"]
    path = f"/conversations/{conversation}/messages"
    assert len(api.get("omar", path).json()) == 2
    for outsider in ("lina", "sam", "dean"):
        assert code(api.get(outsider, path)) == (404, "CONVERSATION_NOT_FOUND")
        assert code(api.post(outsider, path, {"body": "x"})) == (404, "CONVERSATION_NOT_FOUND")
    answer = api.post("sam", "/conversations", {"user_id": api.id("aisha")})
    assert code(answer) == (403, "ROLE_NOT_ALLOWED")
    api.put("aisha", f"/users/{api.id('omar')}/block")
    assert code(api.post("omar", path, {"body": "x"})) == (403, "BLOCKED")


def test_purge_erases_after_thirty_days(api, db):
    from app.models import Post
    from scripts.purge import purge

    post = api.new_post("aisha", "<p>gone</p>")
    api.delete("aisha", f"/posts/{post['id']}")
    purge(db)
    assert db.get(Post, post["id"]).body_html == "<p>gone</p>"
    db.get(Post, post["id"]).removed_at = now() - timedelta(days=31)
    db.commit()
    purge(db)
    db.expire_all()
    assert db.get(Post, post["id"]).body_html == "[erased]"

"""FR-AUD: the access rules, checked against every path that can leak content."""

import pytest

from app import policy
from app.models import Post, User
from tests.conftest import code

ROBOTICS = 1

# author aisha (member of Robotics); omar follows aisha; karim is an officer; yusuf has no relationship
RULES = [
    ("campus", None, {"omar", "karim", "yusuf", "dean", "sam"}),
    ("campus", ROBOTICS, {"omar", "karim", "yusuf", "dean", "sam"}),
    ("community", ROBOTICS, {"karim", "lina", "sam"}),
    ("followers", None, {"omar", "sam"}),
]


@pytest.mark.parametrize(("visibility", "community_id", "allowed"), RULES)
def test_visibility_matrix(api, visibility, community_id, allowed):
    post = api.new_post("aisha", "<p>secret</p>", visibility, community_id=community_id)
    for handle in ("aisha", "omar", "lina", "karim", "yusuf", "dean", "sam"):
        expected = handle == "aisha" or handle in allowed or visibility == "campus"
        listed = [p["id"] for p in api.get(handle, "/posts?scope=campus").json()["items"]]
        assert (api.get(handle, f"/posts/{post['id']}").status_code == 200) is expected, handle
        assert (post["id"] in listed) is expected, handle


def test_hidden_item_looks_like_missing_item(api):
    post = api.new_post("aisha", visibility="community", community_id=ROBOTICS)
    hidden, missing = api.get("omar", f"/posts/{post['id']}"), api.get("omar", "/posts/99999")
    assert (hidden.status_code, hidden.json()) == (missing.status_code, missing.json())


PROBES = [
    ("GET", "/posts/{id}"),
    ("GET", "/posts/{id}/comments"),
    ("GET", "/posts/{id}/versions"),
    ("POST", "/posts/{id}/comments", {"body": "x"}),
    ("PUT", "/posts/{id}/reactions/like"),
    ("DELETE", "/posts/{id}"),
    ("POST", "/posts/{id}/reshare", {"body_html": "<p>x</p>"}),
    ("PUT", "/posts/{id}/officer-controls", {"locked": True, "pinned": True}),
    ("PUT", "/events/{id}/rsvp", {"status": "going"}),
    ("POST", "/reports", {"target_type": "post", "target_id": "{id}", "reason": "spam"}),
]


@pytest.mark.parametrize("probe", PROBES, ids=lambda probe: probe[0] + probe[1])
def test_outsider_is_refused_on_every_path(api, probe):
    post = api.new_post("aisha", visibility="community", community_id=ROBOTICS)
    method, path, *body = probe
    json = body[0] if body else None
    if json and json.get("target_id"):
        json = {**json, "target_id": post["id"]}
    answer = api.call(method, "omar", path.format(id=post["id"]), json=json)
    assert code(answer) == (404, "POST_NOT_FOUND")


def test_image_follows_the_post(api):
    post = api.new_post("aisha", visibility="followers")
    png = b"\x89PNG\r\n\x1a\n0000"
    uploaded = api.call(
        "POST", "aisha", f"/posts/{post['id']}/images", files={"file": png}, data={"alt_text": "A robot"}
    ).json()
    assert api.get("omar", f"/images/{uploaded['id']}").content == png
    assert code(api.get("yusuf", f"/images/{uploaded['id']}")) == (404, "IMAGE_NOT_FOUND")


def test_only_the_author_changes_a_post(api):
    post = api.new_post("aisha")
    body = {"body_html": "<p>hacked</p>", "visibility": "campus"}
    for handle in ("omar", "sam", "dean"):
        answer = api.patch(handle, f"/posts/{post['id']}", body, headers={"If-Match": "1"})
        assert code(answer) == (403, "NOT_AUTHOR")
        assert code(api.delete(handle, f"/posts/{post['id']}")) == (403, "NOT_AUTHOR")


def test_changed_visibility_applies_to_post_and_comments(api):
    post = api.new_post("aisha")
    path = f"/posts/{post['id']}"
    assert api.get("yusuf", path + "/comments").status_code == 200
    body = {"body_html": "<p>x</p>", "visibility": "followers"}
    api.patch("aisha", path, body, headers={"If-Match": "1"})
    assert code(api.get("yusuf", path)) == (404, "POST_NOT_FOUND")
    assert code(api.get("yusuf", path + "/comments")) == (404, "POST_NOT_FOUND")


def test_blocking_is_mutual_invisibility(api):
    by_omar, by_aisha = api.new_post("omar"), api.new_post("aisha")
    public = api.new_post("lina")
    api.post("omar", f"/posts/{public['id']}/comments", {"body": "from omar"})
    omar, aisha = api.id("omar"), api.id("aisha")
    assert api.put("aisha", f"/users/{omar}/block").status_code == 204
    assert code(api.get("aisha", f"/posts/{by_omar['id']}")) == (404, "POST_NOT_FOUND")
    assert code(api.get("omar", f"/posts/{by_aisha['id']}")) == (404, "POST_NOT_FOUND")
    assert code(api.get("omar", f"/users/{aisha}")) == (404, "USER_NOT_FOUND")
    assert code(api.put("omar", f"/users/{aisha}/follow")) == (404, "USER_NOT_FOUND")
    assert code(api.post("omar", "/conversations", {"user_id": aisha})) == (403, "BLOCKED")
    assert api.get("aisha", f"/posts/{public['id']}/comments").json() == []
    assert [u["handle"] for u in api.get("aisha", "/blocks").json()] == ["omar"]
    api.post("omar", f"/posts/{public['id']}/comments", {"body": "hi @aisha"})
    assert "Omar Nasser mentioned you." not in api.notes("aisha")
    assert api.delete("aisha", f"/users/{omar}/block").status_code == 204
    assert api.get("omar", f"/posts/{by_aisha['id']}").status_code == 200


def test_block_ends_follows(api):
    post = api.new_post("aisha", visibility="followers")
    omar = api.id("omar")
    api.put("aisha", f"/users/{omar}/block")
    api.delete("aisha", f"/users/{omar}/block")
    assert code(api.get("omar", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")


def test_follow_gives_access_to_followers_posts(api):
    post = api.new_post("aisha", visibility="followers")
    aisha = api.id("aisha")
    assert api.put("yusuf", f"/users/{aisha}/follow").json() == {"status": "active"}
    assert api.get("yusuf", f"/posts/{post['id']}").status_code == 200
    api.delete("yusuf", f"/users/{aisha}/follow")
    assert code(api.get("yusuf", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")


def test_follow_request_needs_approval(api):
    post = api.new_post("karim", visibility="followers")
    assert api.get("omar", f"/users/{api.id('karim')}").json()["follow_status"] == "pending"
    assert code(api.get("omar", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")
    assert [u["handle"] for u in api.get("karim", "/follow-requests").json()] == ["omar"]
    accept = f"/follow-requests/{api.id('omar')}"
    assert api.post("karim", accept, {"accept": True}).status_code == 204
    assert code(api.post("karim", accept, {"accept": True})) == (404, "REQUEST_NOT_FOUND")
    assert api.get("omar", f"/posts/{post['id']}").status_code == 200
    api.delete("karim", f"/followers/{api.id('omar')}")
    assert code(api.get("omar", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")


def test_mention_outside_the_audience_is_silent(api):
    api.new_post("aisha", "<p>@omar @karim</p>", "community", community_id=ROBOTICS)
    assert "Aisha Rahman mentioned you." not in api.notes("omar")
    assert "Aisha Rahman mentioned you." in api.notes("karim")


def test_only_campus_posts_can_be_reshared(api):
    post = api.new_post("aisha", visibility="followers")
    body = {"body_html": "<p>look</p>"}
    assert code(api.post("omar", f"/posts/{post['id']}/reshare", body)) == (409, "NOT_RESHAREABLE")
    campus = api.new_post("aisha")
    reshare = api.post("omar", f"/posts/{campus['id']}/reshare", body).json()
    assert reshare["reshare_of"]["id"] == campus["id"]


def test_reshare_never_shows_an_original_that_became_private(api):
    campus = api.new_post("aisha")
    reshare = api.post("omar", f"/posts/{campus['id']}/reshare", {"body_html": "<p>look</p>"}).json()
    body = {"body_html": "<p>x</p>", "visibility": "followers"}
    api.patch("aisha", f"/posts/{campus['id']}", body, headers={"If-Match": "1"})
    assert code(api.get("yusuf", f"/posts/{reshare['id']}")) == (404, "POST_NOT_FOUND")


def test_admin_cannot_post_and_outsider_cannot_post_in_community(api):
    body = {"body_html": "<p>x</p>", "visibility": "community", "community_id": ROBOTICS}
    assert code(api.post("omar", "/posts", body)) == (403, "NOT_A_MEMBER")
    body = {"body_html": "<p>x</p>", "visibility": "campus"}
    assert code(api.post("dean", "/posts", body)) == (403, "ROLE_NOT_ALLOWED")


@pytest.mark.parametrize(("visibility", "community_id"), [("community", None), ("followers", ROBOTICS)])
def test_impossible_audiences(api, visibility, community_id):
    body = {"body_html": "<p>x</p>", "visibility": visibility, "community_id": community_id}
    assert code(api.post("aisha", "/posts", body)) == (400, "INVALID_AUDIENCE")


def test_policy_condition_equals_single_check(api, db):
    for user in db.query(User):
        listed = {p.id for p in db.query(Post).filter(policy.visible_posts(user))}
        assert listed == {p.id for p in db.query(Post) if policy.can_view_post(db, user, p.id)}

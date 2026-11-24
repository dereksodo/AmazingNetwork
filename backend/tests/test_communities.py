"""FR-COM, and following and muting communities (FR-INT-3, FR-INT-5)."""

import pytest

from tests.conftest import code

ROBOTICS, CHESS, FILM = 1, 2, 3


def test_community_needs_admin_approval(api):
    body = {"name": "Debate Union", "description": "We argue.", "join_policy": "open"}
    created = api.post("aisha", "/communities", body)
    assert (created.status_code, created.json()["my_role"]) == (202, "owner")
    path = f"/communities/{created.json()['id']}"
    assert code(api.get("omar", path)) == (404, "COMMUNITY_NOT_FOUND")
    decision = {"accept": True, "reason": "Fine"}
    admin_path = f"/admin{path}/decision"
    assert code(api.post("aisha", admin_path, decision)) == (403, "NOT_ADMIN")
    assert api.post("dean", admin_path, decision).status_code == 204
    assert code(api.post("dean", admin_path, decision)) == (409, "ALREADY_DECIDED")
    assert api.get("omar", path).json()["status"] == "approved"


def test_name_is_unique(api):
    body = {"name": "Robotics Club", "description": "", "join_policy": "open"}
    assert code(api.post("aisha", "/communities", body)) == (409, "NAME_TAKEN")


def test_join_open_and_closed(api):
    assert api.post("omar", f"/communities/{ROBOTICS}/join").status_code == 200
    assert code(api.post("omar", f"/communities/{ROBOTICS}/join")) == (409, "ALREADY_MEMBER")
    assert api.post("lina", f"/communities/{CHESS}/join").status_code == 202
    assert code(api.get("lina", f"/communities/{CHESS}/members")) == (403, "NOT_A_MEMBER")
    request = f"/communities/{CHESS}/requests/{api.id('lina')}"
    assert code(api.post("lina", request, {"accept": True})) == (403, "NOT_AN_OFFICER")
    assert api.post("omar", request, {"accept": True}).status_code == 204
    assert api.get("lina", f"/communities/{CHESS}/members").status_code == 200


def test_owner_manages_roles(api):
    path = f"/communities/{ROBOTICS}/members/{api.id('aisha')}"
    assert code(api.patch("karim", path, {"role": "officer"})) == (403, "NOT_OWNER")
    assert api.patch("lina", path, {"role": "officer"}).status_code == 204
    assert api.get("aisha", f"/communities/{ROBOTICS}").json()["my_role"] == "officer"
    assert code(api.delete("lina", f"/communities/{ROBOTICS}/members/me")) == (409, "OWNER_CANNOT_LEAVE")


@pytest.mark.parametrize("removed_by", ["lina", "aisha"])
def test_lost_membership_ends_access_at_once(api, removed_by):
    post = api.new_post("lina", visibility="community", community_id=ROBOTICS)
    assert api.get("aisha", f"/posts/{post['id']}").status_code == 200
    who = "me" if removed_by == "aisha" else api.id("aisha")
    assert api.delete(removed_by, f"/communities/{ROBOTICS}/members/{who}").status_code == 204
    assert code(api.get("aisha", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")


def test_following_a_community_adds_campus_posts_only(api):
    api.put("omar", f"/communities/{ROBOTICS}/follow")
    campus = api.new_post("lina", community_id=ROBOTICS)
    members_only = api.new_post("lina", visibility="community", community_id=ROBOTICS)
    feed = [p["id"] for p in api.get("omar", "/posts").json()["items"]]
    assert campus["id"] in feed
    assert members_only["id"] not in feed


def test_muted_community_sends_no_notifications(api):
    api.put("aisha", f"/communities/{ROBOTICS}/mute")
    api.new_post("lina", "<p>@aisha @karim look</p>", "community", community_id=ROBOTICS)
    assert "Lina Park mentioned you." not in api.notes("aisha")
    assert "Lina Park mentioned you." in api.notes("karim")
    api.delete("aisha", f"/communities/{ROBOTICS}/mute")
    api.new_post("lina", "<p>@aisha again</p>", "community", community_id=ROBOTICS)
    assert "Lina Park mentioned you." in api.notes("aisha")

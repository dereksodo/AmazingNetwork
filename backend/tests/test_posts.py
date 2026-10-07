"""API tests for contract C-POSTS. Test names reference requirement IDs from the report."""

from conftest import as_user


def make(client, user="aisha", **body):
    payload = {"visibility": "campus", "body_html": "<p>Hello campus</p>"} | body
    return client.post("/api/v1/posts", json=payload, headers=as_user(user))


def test_create_and_fetch_post_fr_pub_1(client):
    created = make(client, body_html="<p>Hello <b>campus</b></p>")
    assert created.status_code == 201
    post = created.json()
    assert created.headers["Location"] == f"/api/v1/posts/{post['id']}"
    assert post["author"] == {"id": "aisha", "display_name": "Aisha (student)"}
    assert post["status"] == "visible" and post["version"] == 1

    fetched = client.get(f"/api/v1/posts/{post['id']}", headers=as_user("omar"))
    assert fetched.status_code == 200
    assert fetched.json() == post


def test_unsafe_html_is_removed_nfr_sec(client):
    post = make(client, body_html='<p onclick="x()">Hi<script>alert(1)</script></p>').json()
    assert post["body_html"] == "<p>Hi</p>"


def test_missing_user_is_401(client):
    r = client.post("/api/v1/posts", json={"visibility": "campus", "body_html": "x"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def test_validation_errors_use_contract_format(client):
    r = make(client, visibility="everyone")
    assert r.status_code == 400
    body = r.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "visibility"


def test_community_visibility_needs_community(client):
    assert make(client, visibility="community").status_code == 400


def test_discussion_needs_title(client):
    assert make(client, type="discussion", community_id=1, visibility="community").status_code == 400


def test_unknown_field_rejected(client):
    assert make(client, author_id="lina").status_code == 400


def test_non_member_cannot_post_in_community_fr_com(client):
    r = make(client, user="omar", community_id=1, visibility="community")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "NOT_A_MEMBER"


def test_unknown_community_is_404(client):
    assert make(client, community_id=99, visibility="community").status_code == 404


def test_community_post_hidden_from_non_member_fr_aud_2(client):
    post_id = make(client, community_id=1, visibility="community").json()["id"]
    assert client.get(f"/api/v1/posts/{post_id}", headers=as_user("lina")).status_code == 200
    hidden = client.get(f"/api/v1/posts/{post_id}", headers=as_user("omar"))
    missing = client.get("/api/v1/posts/9999", headers=as_user("omar"))
    # Not-allowed and not-existing look identical (no existence leak).
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()


def test_followers_only_post(client):
    post_id = make(client, visibility="followers").json()["id"]
    assert client.get(f"/api/v1/posts/{post_id}", headers=as_user("omar")).status_code == 200
    assert client.get(f"/api/v1/posts/{post_id}", headers=as_user("lina")).status_code == 404


def test_feed_only_contains_visible_posts(client):
    make(client, community_id=1, visibility="community", body_html="<p>members only</p>")
    make(client, body_html="<p>for everyone</p>")
    omar_feed = client.get("/api/v1/posts", headers=as_user("omar")).json()["items"]
    bodies = [p["body_html"] for p in omar_feed]
    assert "<p>for everyone</p>" in bodies
    assert "<p>members only</p>" not in bodies


def test_moderator_can_view_community_post(client):
    post_id = make(client, community_id=1, visibility="community").json()["id"]
    assert client.get(f"/api/v1/posts/{post_id}", headers=as_user("sam")).status_code == 200


def test_blocked_user_cannot_view(client, store):
    store.blocks.add(("aisha", "omar"))
    post_id = make(client).json()["id"]
    assert client.get(f"/api/v1/posts/{post_id}", headers=as_user("omar")).status_code == 404

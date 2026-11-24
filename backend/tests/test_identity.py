"""FR-ID."""

from datetime import timedelta

from app.db import now
from app.models import AuthSession, User
from tests.conftest import code

NEW = {
    "email": "noor@campus.example", "password": "long-enough-pw", "handle": "noor",
    "display_name": "Noor", "programme_id": 1,
}  # fmt: skip


def test_register_creates_profile_with_programme(api, db):
    answer = api.client.post("/api/v1/auth/register", json=NEW)
    assert answer.status_code == 201
    assert answer.json()["user"]["programme"]["name"] == "BSc Computer Science"
    stored = db.get(User, answer.json()["user"]["id"]).password_hash
    assert "long-enough-pw" not in stored


def test_only_university_addresses(api):
    answer = api.client.post("/api/v1/auth/register", json={**NEW, "email": "noor@gmail.com"})
    assert code(answer) == (403, "DOMAIN_NOT_ALLOWED")


def test_email_is_unique(api):
    answer = api.client.post("/api/v1/auth/register", json={**NEW, "email": "Aisha@campus.example"})
    assert code(answer) == (409, "EMAIL_TAKEN")


def test_wrong_password_and_missing_token(api):
    body = {"email": "aisha@campus.example", "password": "wrong"}
    assert code(api.client.post("/api/v1/auth/login", json=body)) == (401, "BAD_CREDENTIALS")
    assert code(api.client.get("/api/v1/me")) == (401, "UNAUTHENTICATED")


def test_logout_invalidates_the_token(api):
    api.token("aisha")
    assert api.post("aisha", "/auth/logout").status_code == 204
    assert code(api.get("aisha", "/me")) == (401, "UNAUTHENTICATED")


def test_session_expires_after_seven_idle_days(api, db):
    api.token("aisha")
    db.query(AuthSession).update({"last_used_at": now() - timedelta(days=8)})
    db.commit()
    assert code(api.get("aisha", "/me")) == (401, "UNAUTHENTICATED")


def test_profile_update(api):
    answer = api.patch("aisha", "/me", {"display_name": "Aisha R.", "programme_id": 3})
    assert answer.json()["display_name"] == "Aisha R."
    assert answer.json()["programme"]["id"] == 3


def test_deleted_account_is_invisible(api):
    post = api.new_post("yusuf")
    assert api.delete("yusuf", "/me").status_code == 204
    assert code(api.get("aisha", f"/posts/{post['id']}")) == (404, "POST_NOT_FOUND")
    assert code(api.get("aisha", f"/users/{api.ids['yusuf']}")) == (404, "USER_NOT_FOUND")
    assert code(api.get("yusuf", "/me")) == (401, "UNAUTHENTICATED")


def test_only_admin_appoints_moderators(api):
    path, body = f"/admin/users/{api.id('lina')}/role", {"role": "moderator", "reason": "Trained"}
    assert code(api.put("aisha", path, body)) == (403, "NOT_ADMIN")
    assert api.put("dean", path, body).json()["role"] == "moderator"

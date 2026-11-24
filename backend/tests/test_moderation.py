"""FR-MOD."""

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db import now
from app.models import ModerationAction
from tests.conftest import code


def hidden_post(api):
    post = api.new_post("aisha")
    report = api.report("omar", post["id"])
    action = api.act("sam", report).json()
    return post, report, action


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/moderation/queue"),
        ("GET", "/moderation/appeals"),
        ("POST", "/moderation/reports/1/triage"),
    ],
)
def test_only_moderators(api, method, path):
    for handle in ("aisha", "lina", "dean"):
        assert code(api.call(method, handle, path)) == (403, "NOT_MODERATOR")


def test_report_rules(api):
    post = api.new_post("aisha")
    body = {"target_type": "post", "target_id": post["id"], "reason": "spam"}
    assert code(api.post("aisha", "/reports", body)) == (400, "NOT_YOURSELF")
    assert api.post("omar", "/reports", body).status_code == 202
    assert code(api.post("omar", "/reports", body)) == (409, "DUPLICATE_REPORT")


def test_queue_is_ordered_by_severity(api, provider):
    answer = '{"category": "spam", "severity": "%s", "rationale": "r"}'
    order = {}
    for severity in ("low", "high", "medium"):
        provider.answer = answer % severity
        order[severity] = api.report("omar", api.new_post("aisha")["id"])
    queue = [r["id"] for r in api.get("sam", "/moderation/queue").json()]
    assert queue == [order["high"], 1, order["medium"], order["low"]]  # report 1 is unscored


def test_hide_freezes_and_notifies(api):
    post, _, _ = hidden_post(api)
    path = f"/posts/{post['id']}"
    assert code(api.get("omar", path)) == (404, "POST_NOT_FOUND")
    assert api.get("aisha", path).json()["status"] == "hidden"
    assert code(api.post("aisha", path + "/comments", {"body": "x"})) == (409, "CONTENT_FROZEN")
    assert "Your post was hidden (harassment): Policy" in api.notes("aisha")


def test_report_is_decided_once(api):
    _, report, _ = hidden_post(api)
    assert code(api.act("maya", report)) == (409, "ALREADY_DECIDED")


def test_action_needs_matching_fields(api):
    report = api.report("omar", api.new_post("aisha")["id"])
    assert code(api.act("sam", report, "mute")) == (400, "VALIDATION_ERROR")
    assert code(api.act("sam", report, "hide", ai_agreed=None)) == (400, "VALIDATION_ERROR")
    body = {"target_type": "user", "target_id": api.id("aisha"), "reason": "spam"}
    report = api.post("omar", "/reports", body).json()["id"]
    assert code(api.act("sam", report, "remove")) == (400, "ACTION_NOT_ALLOWED")


def test_moderator_does_not_judge_themselves(api):
    report = api.report("omar", api.new_post("sam")["id"])
    assert code(api.act("sam", report)) == (400, "NOT_YOURSELF")


def test_mute_blocks_every_write_and_can_be_lifted(api):
    post = api.new_post("aisha")
    report = api.report("omar", post["id"])
    action = api.act("sam", report, "mute", mute_hours=24).json()
    assert api.get("aisha", "/me").json()["muted_until"]
    assert api.get("aisha", f"/posts/{post['id']}").status_code == 200
    conversation = api.get("aisha", "/conversations").json()[0]["id"]
    for method, path, body in (
        ("POST", "/posts", {"body_html": "<p>x</p>", "visibility": "campus"}),
        ("POST", f"/posts/{post['id']}/comments", {"body": "x"}),
        ("PUT", f"/posts/{post['id']}/reactions/like", None),
        ("POST", f"/conversations/{conversation}/messages", {"body": "x"}),
    ):
        assert code(api.call(method, "aisha", path, json=body)) == (403, "MUTED")
    appeal = api.post("aisha", "/appeals", {"action_id": action["id"], "statement": "Please"}).json()
    decision = {"outcome": "overturned", "reason": "Too strict"}
    assert api.post("maya", f"/moderation/appeals/{appeal['id']}/decision", decision).status_code == 200
    api.new_post("aisha")


def test_appeal_overturned_by_another_moderator(api):
    post, _, action = hidden_post(api)
    body = {"action_id": action["id"], "statement": "It was a joke"}
    assert code(api.post("omar", "/appeals", body)) == (404, "ACTION_NOT_FOUND")
    appeal = api.post("aisha", "/appeals", body).json()
    assert code(api.post("aisha", "/appeals", body)) == (409, "ALREADY_APPEALED")
    path = f"/moderation/appeals/{appeal['id']}/decision"
    decision = {"outcome": "overturned", "reason": "Agreed"}
    assert api.get("sam", "/moderation/appeals").json() == []
    assert code(api.post("sam", path, decision)) == (403, "SAME_MODERATOR")
    assert api.post("maya", path, decision).json()["status"] == "overturned"
    assert code(api.post("maya", path, decision)) == (409, "ALREADY_DECIDED")
    assert api.get("omar", f"/posts/{post['id']}").status_code == 200
    assert "Your appeal was decided: overturned. Agreed" in api.notes("aisha")


def test_appeal_window(api, db):
    _, _, action = hidden_post(api)
    db.get(ModerationAction, action["id"]).created_at = now() - timedelta(days=8)
    db.commit()
    body = {"action_id": action["id"], "statement": "late"}
    assert code(api.post("aisha", "/appeals", body)) == (410, "APPEAL_WINDOW_CLOSED")


def test_dm_report_contains_only_selected_messages(api):
    conversation = api.get("aisha", "/conversations").json()[0]["id"]
    path = f"/conversations/{conversation}/messages"
    bad = api.post("omar", path, {"body": "you are stupid"}).json()
    own = api.post("aisha", path, {"body": "stop it"}).json()
    body = {"target_type": "message", "target_id": conversation, "reason": "harassment"}
    assert code(api.post("aisha", "/reports", body)) == (404, "TARGET_NOT_FOUND")
    answer = api.post("aisha", "/reports", {**body, "message_ids": [bad["id"], own["id"]]})
    assert code(answer) == (404, "TARGET_NOT_FOUND")
    assert code(api.post("lina", "/reports", {**body, "message_ids": [bad["id"]]})) == (
        404,
        "CONVERSATION_NOT_FOUND",
    )
    assert api.post("aisha", "/reports", {**body, "message_ids": [bad["id"]]}).status_code == 202
    reported = [r for r in api.get("sam", "/moderation/queue").json() if r["target_type"] == "message"]
    assert [r["target_text"] for r in reported] == ["you are stupid"]


def test_officer_hides_comment_in_own_community(api):
    post = api.new_post("lina", community_id=1)
    comment = api.post("aisha", f"/posts/{post['id']}/comments", {"body": "rude"}).json()
    path = f"/comments/{comment['id']}/officer-hide"
    body = {"reason": "harassment", "explanation": "Rude", "escalate": True}
    assert code(api.post("omar", path, body)) == (403, "NOT_AN_OFFICER")
    assert api.post("karim", path, body).status_code == 204
    assert api.get("omar", f"/posts/{post['id']}/comments").json() == []
    assert any(r["target_type"] == "comment" for r in api.get("sam", "/moderation/queue").json())
    assert len(api.get("aisha", "/me/moderation-actions").json()) == 1


def test_audit_export(api):
    hidden_post(api)
    today = now().date()
    path = f"/admin/audit-log?start={today}&end={today}"
    assert code(api.get("sam", path)) == (403, "NOT_ADMIN")
    api.get("dean", path)
    rows = api.get("dean", path).text.splitlines()
    assert any(",sam,report.hide,post:" in row for row in rows)
    assert any(",dean,audit.export," in row for row in rows)


@pytest.mark.parametrize("statement", ["UPDATE audit_log SET reason = 'x'", "DELETE FROM audit_log"])
def test_audit_log_is_insert_only(api, db, statement):
    hidden_post(api)
    with pytest.raises(IntegrityError, match="insert-only"):
        db.execute(text(statement))

"""FR-INT-4/5 and FR-COL over real WebSocket connections."""

from base64 import b64decode, b64encode
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from pycrdt import Doc, XmlFragment
from starlette.websockets import WebSocketDisconnect

from app.collab import ydoc
from scripts.seed import demo_document
from tests.conftest import code

ROBOTICS, DRAFT = 1, 1
ROOM = f"/ws/drafts/{DRAFT}"


@contextmanager
def connect(api, handle, path="/ws"):
    with api.client.websocket_connect(path) as socket:
        socket.send_json({"type": "auth", "token": api.token(handle)})
        yield socket


@contextmanager
def live(api, handle, *channels):
    with connect(api, handle) as socket:
        assert socket.receive_json() == {"type": "ready", "user_id": api.id(handle)}
        for channel in channels:
            socket.send_json({"type": "subscribe", "channel": channel})
            assert socket.receive_json() == {"type": "subscribed", "channel": channel}
        yield socket


def until(socket, kind):
    while (frame := socket.receive_json())["type"] != kind:
        pass
    return frame


def closed_with(socket):
    with pytest.raises(WebSocketDisconnect) as closed:
        while True:
            socket.receive_json()
    return closed.value.code


# --- /ws ---------------------------------------------------------------------------


def test_new_post_arrives_live(api):
    with live(api, "omar") as socket:
        post = api.new_post("aisha", visibility="followers")
        frame = socket.receive_json()
        assert (frame["event"], frame["data"]["post_id"]) == ("post.created", post["id"])


def test_live_events_follow_the_audience(api):
    with live(api, "yusuf") as socket:
        api.new_post("aisha", visibility="community", community_id=ROBOTICS)
        api.new_post("aisha", visibility="followers")
        campus = api.new_post("aisha")
        assert socket.receive_json()["data"]["post_id"] == campus["id"]  # the first thing that arrives


def test_comment_and_message_arrive_live(api):
    post = api.new_post("aisha")
    with live(api, "omar", f"post:{post['id']}") as socket:
        api.post("lina", f"/posts/{post['id']}/comments", {"body": "hi"})
        assert socket.receive_json()["event"] == "comment.created"
        conversation = api.get("aisha", "/conversations").json()[0]["id"]
        api.post("aisha", f"/conversations/{conversation}/messages", {"body": "hello"})
        assert socket.receive_json()["event"] == "message.created"


@pytest.mark.parametrize(
    "channel", ["moderation", "user:1", "community:1", "post:1", "post:99999", "nonsense", "post:x"]
)
def test_forbidden_channels(api, channel):
    with live(api, "omar") as socket:
        socket.send_json({"type": "subscribe", "channel": channel})
        assert socket.receive_json() == {"type": "error", "code": "FORBIDDEN", "channel": channel}


def test_invalid_frames_and_ping(api):
    with live(api, "omar") as socket:
        socket.send_text("not json")
        assert socket.receive_json() == {"type": "error", "code": "INVALID_FRAME"}
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}


@pytest.mark.parametrize("first_frame", ['{"type": "auth", "token": "wrong"}', "hello"])
@pytest.mark.parametrize("path", ["/ws", ROOM])
def test_unauthenticated_connection_is_closed(api, first_frame, path):
    with api.client.websocket_connect(path) as socket:
        socket.send_text(first_frame)
        assert closed_with(socket) == 4401


def test_lost_membership_revokes_the_channel(api):
    with live(api, "aisha", f"community:{ROBOTICS}") as socket:
        api.delete("lina", f"/communities/{ROBOTICS}/members/{api.id('aisha')}")
        assert socket.receive_json() == {"type": "revoked", "channel": f"community:{ROBOTICS}"}
        api.new_post("lina", visibility="community", community_id=ROBOTICS)
        campus = api.new_post("lina")
        assert socket.receive_json()["data"]["post_id"] == campus["id"]


def test_hidden_post_revokes_its_channel(api):
    post = api.new_post("aisha")
    report = api.report("omar", post["id"])
    with live(api, "yusuf", f"post:{post['id']}") as socket:
        api.act("sam", report)
        assert socket.receive_json() == {"type": "revoked", "channel": f"post:{post['id']}"}


def test_logout_closes_the_connection(api):
    with live(api, "omar") as socket:
        api.post("omar", "/auth/logout")
        assert closed_with(socket) == 4401


# --- /ws/drafts --------------------------------------------------------------------


class Writer:
    """A client-side Yjs document connected to the room."""

    def __init__(self, socket):
        self.socket = socket
        self.doc = Doc()
        self.doc.get("default", type=XmlFragment)

    def sync(self):
        state = b64encode(self.doc.get_state()).decode()
        self.socket.send_json({"type": "sync", "state_vector": state})
        frame = until(self.socket, "sync")
        self.doc.apply_update(b64decode(frame["update"]))
        return frame

    def text(self):
        return self.doc.get("default", type=XmlFragment).children[0].children[0]

    def edit(self, change):
        before = self.doc.get_state()
        change(self.text())
        return self.doc.get_update(before)

    def send(self, update):
        self.socket.send_json({"type": "update", "update": b64encode(update).decode()})

    def receive(self):
        frame = until(self.socket, "update")
        self.doc.apply_update(b64decode(frame["update"]))
        return frame

    def html(self):
        return ydoc.to_html(self.doc.get_update())


def test_concurrent_edits_merge(api):
    with connect(api, "lina", ROOM) as one, connect(api, "karim", ROOM) as two:
        lina, karim = Writer(one), Writer(two)
        lina.sync()
        karim.sync()
        first = lina.edit(lambda t: t.insert(0, "Dear all: "))
        second = karim.edit(lambda t: t.insert(len(str(t)), " Register now."))
        lina.send(first)
        karim.send(second)
        karim.receive()
        lina.receive()
        assert lina.html() == karim.html()
        assert lina.html() == "<p>Dear all: The spring competition is on 12 March. Register now.</p>"


def test_presence_lists_editors(api):
    with connect(api, "lina", ROOM) as one:
        assert [u["display_name"] for u in until(one, "presence")["users"]] == ["Lina Park"]
        with connect(api, "karim", ROOM):
            assert len(until(one, "presence")["users"]) == 2
        assert len(until(one, "presence")["users"]) == 1


def test_offline_edits_are_merged_after_reconnecting(api):
    with connect(api, "lina", ROOM) as one:
        lina = Writer(one)
        lina.sync()
    offline = lina.edit(lambda t: t.insert(0, "OFFLINE "))
    with connect(api, "karim", ROOM) as two:
        karim = Writer(two)
        karim.sync()
        karim.send(karim.edit(lambda t: t.insert(0, "ONLINE ")))
        until(two, "ack")
        with connect(api, "lina", ROOM) as again:
            lina.socket = again
            frame = lina.sync()
            lina.send(lina.doc.get_update(b64decode(frame["state_vector"])))
            karim.receive()
            assert offline and "OFFLINE" in karim.html() and "ONLINE " in lina.html()
            assert karim.html() == lina.html()


def test_awareness_is_relayed(api):
    with connect(api, "lina", ROOM) as one, connect(api, "karim", ROOM) as two:
        until(two, "presence")
        one.send_json({"type": "awareness", "update": "AQID"})
        assert until(two, "awareness")["update"] == "AQID"


@pytest.mark.parametrize("handle", ["aisha", "omar", "sam", "dean"])
def test_outsiders_cannot_join_or_read_a_draft(api, handle):
    with connect(api, handle, ROOM) as socket:
        assert closed_with(socket) == 4403
    assert code(api.get(handle, f"/drafts/{DRAFT}")) == (404, "DRAFT_NOT_FOUND")


def test_demoted_officer_is_disconnected(api):
    with connect(api, "lina", ROOM) as one, connect(api, "karim", ROOM) as two:
        lina, karim = Writer(one), Writer(two)
        lina.sync()
        karim.sync()
        api.patch("lina", f"/communities/{ROBOTICS}/members/{api.id('karim')}", {"role": "member"})
        lina.send(lina.edit(lambda t: t.insert(0, "SECRET ")))
        assert closed_with(two) == 4403


def publish(api, handle, version=1, **fields):
    body = {"expected_version": version, "title": "Spring competition", "visibility": "community", **fields}
    return api.post(handle, f"/drafts/{DRAFT}/publish", body)


def test_publish_makes_editors_read_only(api):
    with connect(api, "karim", ROOM) as socket:
        until(socket, "presence")
        post = publish(api, "lina").json()
        assert until(socket, "published")["post_id"] == post["id"]
        assert closed_with(socket) == 4409
    assert (post["type"], post["body_html"]) == (
        "announcement",
        "<p>The spring competition is on 12 March.</p>",
    )
    assert "Robotics Club: Spring competition" in api.notes("aisha")
    with connect(api, "karim", ROOM) as socket:
        assert closed_with(socket) == 4409


def test_simultaneous_publishing_creates_one_post(api):
    api.token("lina"), api.token("karim")
    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(lambda handle: publish(api, handle), ["lina", "karim"]))
    assert sorted(a.status_code for a in answers) == [201, 409]
    won = next(a for a in answers if a.status_code == 201).json()
    lost = next(a for a in answers if a.status_code == 409).json()["error"]
    assert (lost["code"], lost["details"]["post_id"]) == ("ALREADY_PUBLISHED", won["id"])


def test_publishing_an_old_version_is_refused(api):
    with connect(api, "lina", ROOM) as socket:
        lina = Writer(socket)
        lina.sync()
        lina.send(lina.edit(lambda t: t.insert(0, "New: ")))
        assert until(socket, "ack")["version"] == 2
        assert code(publish(api, "karim", 1)) == (409, "VERSION_CONFLICT")
        assert publish(api, "karim", 2).status_code == 201


def test_event_draft_needs_event_details(api):
    body = {"community_id": ROBOTICS, "kind": "event", "title": "Race", "collaborator_ids": [api.id("karim")]}
    assert code(api.post("aisha", "/drafts", body)) == (403, "NOT_AN_OFFICER")
    draft = api.post("lina", "/drafts", body).json()
    with connect(api, "karim", f"/ws/drafts/{draft['id']}") as socket:
        update = b64encode(demo_document("Race day")).decode()
        socket.send_json({"type": "update", "update": update})
        until(socket, "ack")
    publishing = {"expected_version": 2, "title": "Race", "visibility": "campus"}
    path = f"/drafts/{draft['id']}/publish"
    assert code(api.post("lina", path, publishing)) == (400, "VALIDATION_ERROR")
    publishing["event"] = {
        "starts_at": "2030-01-01T10:00:00Z", "ends_at": "2030-01-01T12:00:00Z", "location": "Lab",
        "capacity": 5, "rsvp_deadline": "2029-12-31T10:00:00Z",
    }  # fmt: skip
    assert api.post("lina", path, publishing).json()["event"]["capacity"] == 5


def test_only_officers_can_be_invited(api):
    answer = api.post("lina", f"/drafts/{DRAFT}/collaborators", {"user_id": api.id("aisha")})
    assert code(answer) == (403, "NOT_AN_OFFICER")


def test_campus_drafts_belong_to_admins(api):
    body = {"kind": "announcement", "title": "Closure"}
    assert code(api.post("lina", "/drafts", body)) == (403, "NOT_AN_OFFICER")
    assert api.post("dean", "/drafts", body).status_code == 201


def test_yjs_document_becomes_safe_html(api):
    attack = demo_document("<script>alert(1)</script>")
    assert ydoc.to_html(attack) == "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"

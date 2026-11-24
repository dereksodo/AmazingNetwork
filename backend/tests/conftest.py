import os
import tempfile

os.environ["CONNECT_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai.provider import get_provider  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts.seed import PASSWORD, load_demo  # noqa: E402

VALID_ANSWER = '{"category": "harassment", "severity": "high", "rationale": "Insults a person."}'


class FakeProvider:
    """Returns a fixed answer, or raises a fixed error, and remembers the prompts."""

    name = "fake-model"

    def __init__(self):
        self.answer = VALID_ANSWER
        self.error = None
        self.prompts = []

    async def complete(self, system, user):
        self.prompts.append(user)
        if self.error:
            raise self.error
        return self.answer


class Api:
    """The test client with a signed-in user per call: api.get("aisha", "/posts")."""

    def __init__(self, client):
        self.client = client
        self.tokens = {}
        self.ids = {}

    def token(self, handle):
        if handle not in self.tokens:
            body = {"email": f"{handle}@campus.example", "password": PASSWORD}
            answer = self.client.post("/api/v1/auth/login", json=body).json()
            self.tokens[handle] = answer["token"]
            self.ids[handle] = answer["user"]["id"]
        return self.tokens[handle]

    def id(self, handle):
        self.token(handle)
        return self.ids[handle]

    def call(self, method, handle, path, headers=None, **kwargs):
        headers = {"Authorization": f"Bearer {self.token(handle)}", **(headers or {})}
        return self.client.request(method, f"/api/v1{path}", headers=headers, **kwargs)

    def get(self, handle, path, **kwargs):
        return self.call("GET", handle, path, **kwargs)

    def post(self, handle, path, json=None, **kwargs):
        return self.call("POST", handle, path, json=json, **kwargs)

    def put(self, handle, path, json=None):
        return self.call("PUT", handle, path, json=json)

    def patch(self, handle, path, json=None, **kwargs):
        return self.call("PATCH", handle, path, json=json, **kwargs)

    def delete(self, handle, path):
        return self.call("DELETE", handle, path)

    def new_post(self, handle, body="<p>Hello</p>", visibility="campus", **fields):
        answer = self.post(handle, "/posts", {"body_html": body, "visibility": visibility, **fields})
        assert answer.status_code == 201, answer.text
        return answer.json()

    def report(self, handle, post_id, reason="harassment"):
        body = {"target_type": "post", "target_id": post_id, "reason": reason}
        answer = self.post(handle, "/reports", body)
        assert answer.status_code == 202, answer.text
        return answer.json()["id"]

    def act(self, handle, report_id, action="hide", **fields):
        body = {
            "action": action,
            "reason": "harassment",
            "explanation": "Policy",
            "ai_agreed": True,
            **fields,
        }
        return self.post(handle, f"/moderation/reports/{report_id}/actions", body)

    def notes(self, handle):
        return [n["text"] for n in self.get(handle, "/notifications").json()]


def code(answer):
    return answer.status_code, answer.json()["error"]["code"]


@pytest.fixture
def provider():
    fake = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def api(provider):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        load_demo(db)
    with TestClient(app) as client:
        yield Api(client)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session

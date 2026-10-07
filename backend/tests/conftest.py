import pytest
from fastapi.testclient import TestClient

from app.api import posts
from app.main import create_app
from app.store import seeded_store


@pytest.fixture
def store():
    return seeded_store()


@pytest.fixture
def client(store):
    app = create_app()
    app.dependency_overrides[posts.get_store] = lambda: store
    return TestClient(app)


def as_user(user_id: str) -> dict:
    return {"X-Demo-User": user_id}

"""Contract test: the running app must match shared/contracts/openapi.yaml."""

from pathlib import Path

import yaml

from conftest import as_user

CONTRACT = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "shared" / "contracts" / "openapi.yaml").read_text()
)
SCHEMAS = CONTRACT["components"]["schemas"]


def test_every_contract_operation_is_implemented(client):
    implemented = client.app.openapi()["paths"]
    for path, ops in CONTRACT["paths"].items():
        for method in ops:
            assert method in implemented.get(path, {}), f"{method.upper()} {path} missing"


def test_post_response_has_exactly_the_contract_fields(client):
    r = client.post(
        "/api/v1/posts",
        json={"visibility": "campus", "body_html": "<p>x</p>"},
        headers=as_user("aisha"),
    )
    assert set(r.json()) == set(SCHEMAS["Post"]["properties"])
    assert set(r.json()) >= set(SCHEMAS["Post"]["required"])


def test_request_fields_match_contract():
    from app.schemas import PostCreate

    assert set(PostCreate.model_fields) == set(SCHEMAS["PostCreate"]["properties"])


def test_enums_match_contract():
    from app.schemas import PostType, Visibility

    assert [v.value for v in Visibility] == SCHEMAS["Visibility"]["enum"]
    assert [t.value for t in PostType] == SCHEMAS["PostType"]["enum"]


def test_error_body_shape(client):
    r = client.get("/api/v1/posts/12345", headers=as_user("aisha"))
    assert set(r.json()) == {"error"}
    assert {"code", "message"} <= set(r.json()["error"])

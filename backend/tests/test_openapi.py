"""The committed API specification matches the code and is complete."""

import pytest

from app.main import app
from scripts import export_erd
from scripts.export_openapi import TARGET, render


def operations():
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            yield f"{method.upper()} {path}", operation


def test_committed_specification_is_current():
    assert render() == TARGET.read_text(), "run: python -m scripts.export_openapi"


def test_every_operation_names_its_role():
    assert [name for name, op in operations() if "**Role:**" not in op.get("description", "")] == []


def test_every_protected_operation_documents_401():
    public = {"GET /api/v1/programmes", "POST /api/v1/auth/register", "GET /api/v1/health"}
    missing = {name for name, op in operations() if "401" not in op["responses"]}
    assert missing == public


def test_every_error_response_has_an_example():
    for name, operation in operations():
        for status, response in operation["responses"].items():
            if status.startswith(("4", "5")):
                assert response["content"]["application/json"]["examples"], (name, status)


@pytest.mark.parametrize("module", export_erd.PARTS)
def test_committed_er_diagrams_are_current(module):
    expected = export_erd.render(module, export_erd.PARTS[module])
    committed = (export_erd.TARGET / f"erd-{module}.mmd").read_text()
    assert expected == committed, "run: python -m scripts.export_erd"

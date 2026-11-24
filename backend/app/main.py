"""Entry point of the Connect API. Run from backend/: uvicorn app.main:app --port 8000"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlalchemy import update

from app import config
from app.auth import router as auth
from app.collab import router as drafts
from app.collab import socket as draft_socket
from app.communities import router as communities
from app.content import comments, events, images, posts
from app.db import Base, SessionLocal, engine
from app.errors import ApiError, api_error_handler, errors, validation_error_handler
from app.messaging import router as messaging
from app.models import Report
from app.moderation import actions, admin, appeals, reports
from app.notifications import router as notifications
from app.people import router as people
from app.realtime import router as realtime
from app.realtime.hub import client_left, hub

DESCRIPTION = """REST API of Connect, the campus social network.

Sign in with `POST /api/v1/auth/login` and send `Authorization: Bearer <token>`.
Every error has the form `{"error": {"code", "message", "details"?}}`; a malformed request
gets 400 `VALIDATION_ERROR`. Items outside the caller's audience answer 404.
Live channels are documented in docs/websocket.md."""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create missing tables and connect the event bus to the running loop."""
    hub.loop = asyncio.get_running_loop()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        # Model calls that were running when the server stopped have no result.
        db.execute(update(Report).where(Report.triage == "pending").values(triage="unscored"))
        db.commit()
    yield


def operation_id(route: APIRoute) -> str:
    """Use function names as operation ids."""
    return route.name


app = FastAPI(
    title="Connect API",
    version="2.0.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    generate_unique_id_function=operation_id,
    responses={422: errors("VALIDATION_ERROR", public=True)[400]},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "If-Match"],
)
app.add_exception_handler(WebSocketDisconnect, client_left)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

for module in (
    auth, people, communities, posts, comments, events, images, messaging, drafts, notifications,
    reports, actions, appeals, admin,
):  # fmt: skip
    app.include_router(module.router, prefix="/api/v1")
app.include_router(realtime.router)
app.include_router(draft_socket.router)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the server runs.

    **Role:** anyone.
    """
    return {"status": "ok"}


def openapi() -> dict:
    """The OpenAPI document, with validation errors as the 400 responses that are really sent."""
    if app.openapi_schema is None:
        schema = FastAPI.openapi(app)
        for path in schema["paths"].values():
            for operation in path.values():
                validation = operation["responses"].pop("422")
                takes_input = "requestBody" in operation or operation.get("parameters")
                if not takes_input:
                    continue
                existing = operation["responses"].setdefault("400", validation)
                examples = existing["content"]["application/json"]["examples"]
                if "VALIDATION_ERROR" not in examples:
                    examples |= validation["content"]["application/json"]["examples"]
                    existing["description"] += " " + validation["description"]
    return app.openapi_schema


app.openapi = openapi

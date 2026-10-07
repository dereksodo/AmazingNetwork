"""Connect API — proof of concept entry point.

Run from backend/:  uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import posts
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.store import seeded_store


def create_app() -> FastAPI:
    app = FastAPI(title="Connect API (proof of concept)", version="0.1.0")
    store = seeded_store()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Demo-User"],
        expose_headers=["Location"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.dependency_overrides[posts.get_store] = lambda: store

    @app.get("/api/v1/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(posts.router, prefix="/api/v1")
    return app


app = create_app()

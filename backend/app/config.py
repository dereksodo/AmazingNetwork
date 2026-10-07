"""Settings read from environment variables (never hard-coded secrets)."""

import os


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


CORS_ORIGINS = _list(
    "CONNECT_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

"""Settings read from environment variables; every variable is listed in .env.example."""

import os


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DATABASE_URL = os.environ.get("CONNECT_DATABASE_URL", "sqlite:///./connect.db")
CORS_ORIGINS = _list("CONNECT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
EMAIL_DOMAIN = os.environ.get("CONNECT_EMAIL_DOMAIN", "campus.example")
SESSION_IDLE_DAYS = 7

LLM_BASE_URL = os.environ.get("CONNECT_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("CONNECT_LLM_MODEL", "gpt-6.1-terra")
LLM_API_KEY = os.environ.get("CONNECT_LLM_API_KEY", "")
LLM_TIMEOUT_SECONDS = float(os.environ.get("CONNECT_LLM_TIMEOUT_SECONDS", "20"))

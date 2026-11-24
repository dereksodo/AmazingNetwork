"""The only code that talks to a language model."""

import asyncio
from typing import Annotated, Protocol

import httpx
from fastapi import Depends
from pydantic import BaseModel

from app import config


class LLMProvider(Protocol):
    """Anything that answers a prompt with text."""

    name: str

    async def complete(self, system: str, user: str) -> str:
        """Return the model's answer."""


class _Message(BaseModel):
    content: str


class _Choice(BaseModel):
    message: _Message


class _ChatResponse(BaseModel):
    choices: list[_Choice]


class OpenAICompatibleProvider:
    """Chat-completions client for LM Studio, DeepSeek, OpenAI and similar servers."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.name = config.LLM_MODEL
        self.transport = transport

    async def complete(self, system: str, user: str) -> str:
        """Call the model; raises TimeoutError, httpx.HTTPError or pydantic.ValidationError."""
        request = {
            "model": config.LLM_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        # One deadline for the whole call; httpx's own timeouts only limit single reads.
        async with asyncio.timeout(config.LLM_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(transport=self.transport, timeout=None) as client:
                response = await client.post(
                    f"{config.LLM_BASE_URL}/chat/completions",
                    json=request,
                    headers={"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {},
                )
        response.raise_for_status()
        return _ChatResponse.model_validate_json(response.content).choices[0].message.content


def get_provider() -> LLMProvider:
    """Dependency; replaced by a fake in the tests."""
    return OpenAICompatibleProvider()


Provider = Annotated[LLMProvider, Depends(get_provider)]

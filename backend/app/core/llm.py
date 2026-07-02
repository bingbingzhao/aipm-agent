"""LLM client wrapper with retry support."""

from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


async def llm_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    max_retries: int = 3,
) -> str:
    """Simple LLM chat with retry on 5xx errors. Returns response text."""
    kwargs = {
        "model": model or settings.llm_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    last_error = None
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            error_str = str(e)[:200]
            if "503" in error_str or "500" in error_str or "busy" in error_str.lower():
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM API busy (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {error_str}")
                await asyncio.sleep(wait)
                continue
            raise

    raise last_error

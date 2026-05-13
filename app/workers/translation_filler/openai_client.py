"""OpenAI client wrapper — gpt-3.5-turbo chat call with retry + parsing.

Kept tiny on purpose:
  - ``parse_response(text) -> dict | None``
  - ``call(messages, *, client) -> dict | None``

The ``client`` is injected (so tests pass a `MagicMock` and prod code passes
the real `openai.AsyncOpenAI`). We never import the SDK at module top so the
worker is importable in environments without the dependency installed.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from app.workers.translation_filler import (
    OPENAI_MAX_TOKENS,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    RETRY_BACKOFF_BASE_SEC,
    RETRY_MAX,
)


def parse_response(content: str | None) -> dict[str, str] | None:
    """Strict JSON parser for the chat response.

    Returns the dict only if both ``name_ko`` and ``short_name_ko`` are
    present and non-empty strings. Otherwise returns ``None`` so the caller
    can skip the row (NULL preserved → retried in the next cycle).
    """
    if not content:
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    name_ko = data.get("name_ko")
    short_name_ko = data.get("short_name_ko")
    if not isinstance(name_ko, str) or not name_ko.strip():
        return None
    if not isinstance(short_name_ko, str) or not short_name_ko.strip():
        return None
    return {"name_ko": name_ko, "short_name_ko": short_name_ko}


async def call(
    messages: list[dict[str, Any]],
    *,
    client: Any,
) -> dict[str, str] | None:
    """Call the OpenAI chat-completions endpoint with retry/backoff.

    On transient errors (any ``Exception`` raised by ``client.chat.completions
    .create``) we retry up to :data:`RETRY_MAX` additional times with an
    exponential backoff (1s, 2s, 4s — base × 2**n). After the final failure
    we return ``None`` so the caller can skip the row.
    """
    # Filter out non-message entries (few-shot example dicts that
    # ``prompt.build_prompt`` interleaves for inspection/tests).
    api_messages = [m for m in messages if isinstance(m, dict) and "role" in m]
    last_exc: BaseException | None = None
    # Total attempts = 1 initial + RETRY_MAX retries.
    for attempt in range(RETRY_MAX + 1):
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=api_messages,
            )
        except Exception as exc:  # noqa: BLE001 — any transient error path
            last_exc = exc
            if attempt >= RETRY_MAX:
                break
            delay = RETRY_BACKOFF_BASE_SEC * (2 ** attempt)
            await asyncio.sleep(delay)
            continue
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            return None
        return parse_response(content)
    # All retries exhausted.
    return None

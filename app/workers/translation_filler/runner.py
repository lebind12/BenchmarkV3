"""Cycle runner — fetch queue, prompt + call OpenAI, write back.

Orchestration only: it relies on ``queue``, ``prompt`` and ``openai_client``
sub-modules so each layer is independently testable. Designed to be invoked
once per minute by ``scheduler.py`` (or directly from an admin endpoint).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

# IMPORTANT: import the module objects (not the inner symbols) so unit tests
# that do `patch.object(queue, "fetch_queue", ...)` actually intercept the
# call this module makes.
from app.workers.translation_filler import (
    BATCH_LIMIT,
    SEMAPHORE,
    openai_client as openai_client_module,
    prompt as prompt_module,
    queue as queue_module,
)


@dataclass
class CycleResult:
    cycle_started_at: str = ""
    duration_seconds: float = 0.0
    queue_size_at_start: int = 0
    processed_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    openai_calls: int = 0
    openai_errors: int = 0
    cost_estimate_usd: float = 0.0
    by_entity: dict[str, int] = field(default_factory=dict)


# Rough per-call price for gpt-3.5-turbo. Only used for log estimates.
_COST_PER_CALL_USD = 0.001


_UPDATE_SQL = {
    "team": text(
        "UPDATE team_translation "
        "SET name_ko = COALESCE(name_ko, :name_ko), "
        "    short_name_ko = COALESCE(short_name_ko, :short_name_ko), "
        "    updated_at = now() "
        "WHERE team_id = :id"
    ),
    "player": text(
        "UPDATE player_translation "
        "SET name_ko = COALESCE(name_ko, :name_ko), "
        "    short_name_ko = COALESCE(short_name_ko, :short_name_ko), "
        "    updated_at = now() "
        "WHERE player_id = :id"
    ),
}


def _row_context(row: dict[str, Any]) -> dict[str, Any]:
    """Map queue row → context dict expected by prompt.build_prompt."""
    if row["entity_type"] == "player":
        return {"nationality": row.get("context_a") or ""}
    if row["entity_type"] == "team":
        return {"country": row.get("context_a") or ""}
    return {}


async def _invoke_openai(openai_client: Any, messages: list[dict[str, str]]):
    """Dispatch to either a wrapped async callable or the raw SDK client.

    The unit tests inject an ``AsyncMock`` that returns a parsed dict directly,
    while integration tests inject a SDK-shaped MagicMock whose
    ``chat.completions.create`` is the real surface. We differentiate by
    checking ``iscoroutinefunction`` — AsyncMock is recognised; MagicMock is
    not.
    """
    if inspect.iscoroutinefunction(openai_client):
        # Direct callable returning parsed dict | None.
        return await openai_client(messages=messages)
    # Raw SDK shape — go through the retry/parse wrapper.
    return await openai_client_module.call(messages=messages, client=openai_client)


async def run_cycle(
    session,
    *,
    openai_client: Any,
    limit: int = BATCH_LIMIT,
    semaphore: int = SEMAPHORE,
) -> CycleResult:
    """Run one polling cycle. Always returns a CycleResult (never raises)."""
    result = CycleResult(
        cycle_started_at=datetime.now(timezone.utc).isoformat(),
    )
    started = time.monotonic()

    raw_rows = queue_module.fetch_queue(session, limit=limit)
    # Enforce batch cap even if the queue layer returned more than asked.
    rows = [r for r in raw_rows if r.get("entity_type") in _UPDATE_SQL][:limit]
    result.queue_size_at_start = len(raw_rows)

    if not rows:
        result.duration_seconds = time.monotonic() - started
        _emit(result)
        return result

    sem = asyncio.Semaphore(max(1, int(semaphore)))

    async def _handle(row: dict[str, Any]) -> None:
        entity_type = row["entity_type"]
        try:
            messages = prompt_module.build_prompt(
                entity_type=entity_type,
                name=row.get("eng_name") or "",
                context=_row_context(row),
            )
        except Exception:  # noqa: BLE001 — bad row, skip safely
            result.failed_count += 1
            return

        async with sem:
            result.openai_calls += 1
            try:
                parsed = await _invoke_openai(openai_client, messages)
            except Exception:  # noqa: BLE001
                result.openai_errors += 1
                result.failed_count += 1
                return

        if not parsed:
            result.failed_count += 1
            return

        try:
            session.execute(
                _UPDATE_SQL[entity_type],
                {
                    "id": row["id"],
                    "name_ko": parsed["name_ko"],
                    "short_name_ko": parsed["short_name_ko"],
                },
            )
            commit = getattr(session, "commit", None)
            if callable(commit):
                commit()
        except Exception:  # noqa: BLE001 — UPDATE failure, retry next cycle
            result.failed_count += 1
            return

        result.succeeded_count += 1
        result.by_entity[entity_type] = result.by_entity.get(entity_type, 0) + 1

    await asyncio.gather(*(_handle(row) for row in rows))

    result.processed_count = result.succeeded_count + result.failed_count
    result.duration_seconds = time.monotonic() - started
    result.cost_estimate_usd = round(result.openai_calls * _COST_PER_CALL_USD, 6)
    _emit(result)
    return result


def _emit(result: CycleResult) -> None:
    """Emit a single-line JSON log to stdout (spec §9)."""
    payload = {
        "cycle_started_at": result.cycle_started_at,
        "duration_seconds": round(result.duration_seconds, 4),
        "queue_size_at_start": result.queue_size_at_start,
        "processed_count": result.processed_count,
        "succeeded_count": result.succeeded_count,
        "failed_count": result.failed_count,
        "openai_calls": result.openai_calls,
        "openai_errors": result.openai_errors,
        "cost_estimate_usd": result.cost_estimate_usd,
    }
    try:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:  # noqa: BLE001 — logging must never crash a cycle
        pass


# Convenience alias for scheduler integration.
async def run() -> None:  # pragma: no cover — boot path, exercised manually
    """No-arg entry usable by APScheduler.

    Opens a short-lived SQLAlchemy session and runs one cycle. Real OpenAI
    client is constructed inside (kept out of unit/integration test paths).
    """
    from app.core.config import get_settings  # local import
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    try:
        from openai import AsyncOpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "openai package is not installed — required for prod run()."
        ) from e

    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    with Session(engine) as session:
        await run_cycle(session, openai_client=client)

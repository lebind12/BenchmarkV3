"""APScheduler integration — registers the 1-minute polling job.

Kept dependency-free at import: the real ``AsyncIOScheduler`` is created by
the caller (typically the FastAPI startup hook) and passed to ``register``.
That makes the worker boot-time wiring testable with a plain ``MagicMock``.
"""
from __future__ import annotations

from typing import Any

from app.workers.translation_filler import POLL_INTERVAL_SEC
from app.workers.translation_filler.runner import run

# How often to invoke `runner.run`. Spec §16 fixes 60 s; we restate in
# minutes too because APScheduler's `interval` trigger accepts either keyword.
_INTERVAL_KWARGS = {"minutes": 1}
JOB_ID = "translation-filler"


def register(scheduler: Any) -> None:
    """Add the polling job to a caller-supplied APScheduler instance."""
    scheduler.add_job(
        run,
        "interval",
        id=JOB_ID,
        replace_existing=True,
        **_INTERVAL_KWARGS,
    )


# Backwards-compatible alternate entry name expected by tests.
def add_jobs(scheduler: Any) -> None:  # pragma: no cover — tested via register
    register(scheduler)

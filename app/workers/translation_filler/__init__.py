"""translation-filler worker.

Polls `*_translation` tables for NULL Korean rows, calls gpt-3.5-turbo with
few-shot prompts seeded from `_Player__202605131748.csv`, and fills the
columns. Spec SSOT: `docs/workers/translation-filler.md` (+ mirror at
`docs/spec/endpoints/phase-5-translation-filler.md`).

The submodules deliberately keep narrow surfaces so unit tests can mock
each layer independently:

- ``queue``         — SQL fetch of NULL rows (UNION ALL of team + player)
- ``prompt``        — few-shot prompt builder (entity-type aware)
- ``openai_client`` — gpt-3.5-turbo call + retry/backoff + JSON parsing
- ``runner``        — orchestrates one cycle (semaphore, batch limit)
- ``scheduler``     — APScheduler integration point (`register(scheduler)`)
"""
from __future__ import annotations

# Confirmed operating parameters (translation-filler.md §16).
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_TEMPERATURE = 0
OPENAI_MAX_TOKENS = 100
SEMAPHORE = 5
BATCH_LIMIT = 50
RETRY_MAX = 3
RETRY_BACKOFF_BASE_SEC = 1
POLL_INTERVAL_SEC = 60
FAIL_ALERT_THRESHOLD_CYCLES = 10

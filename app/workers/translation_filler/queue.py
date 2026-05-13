"""Queue lookup — rows pending Korean translation.

Implements the team + player UNION ALL from
`docs/workers/translation-filler.md` §3 (league is **not** part of this
worker — ADMIN manual flow handles it). Selects rows whose `name_ko` or
`short_name_ko` is still NULL after `daily-sync` created them.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

# Fixed SQL — UNION ALL of team + player. Excludes league per spec §2.
# `LIMIT` is interpolated as a positive int literal to keep the call to
# session.execute() purely positional (tests assert args[0] is the SQL).
_QUEUE_SQL_TEMPLATE = """
SELECT 'team' AS entity_type,
       tt.team_id AS id,
       t.name AS eng_name,
       t.country AS context_a,
       t.code AS context_b
FROM team_translation tt
JOIN team t ON t.id = tt.team_id
WHERE tt.name_ko IS NULL OR tt.short_name_ko IS NULL

UNION ALL

SELECT 'player' AS entity_type,
       pt.player_id AS id,
       p.name AS eng_name,
       p.nationality AS context_a,
       p.firstname || ' ' || p.lastname AS context_b
FROM player_translation pt
JOIN player p ON p.id = pt.player_id
WHERE pt.name_ko IS NULL OR pt.short_name_ko IS NULL

LIMIT {limit}
"""


def _build_sql(*, limit: int) -> str:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"limit must be a positive int, got {limit!r}")
    return _QUEUE_SQL_TEMPLATE.format(limit=limit)


def fetch_queue(session, *, limit: int) -> list[dict[str, Any]]:
    """Return up to ``limit`` rows from the translation queue.

    Each row is a plain dict with keys ``entity_type``, ``id``, ``eng_name``,
    ``context_a``, ``context_b`` so downstream consumers (and tests) do not
    depend on SQLAlchemy Row objects.
    """
    sql = _build_sql(limit=limit)
    result = session.execute(text(sql))
    rows = result.all()
    out: list[dict[str, Any]] = []
    for r in rows:
        # Row supports ._mapping (SQLAlchemy 2.x) but mocks return arbitrary
        # objects — fall back to attribute access.
        mapping = getattr(r, "_mapping", None)
        if mapping is not None:
            d = dict(mapping)
        else:
            d = {
                "entity_type": getattr(r, "entity_type", None),
                "id": getattr(r, "id", None),
                "eng_name": getattr(r, "eng_name", None),
                "context_a": getattr(r, "context_a", None),
                "context_b": getattr(r, "context_b", None),
            }
        out.append(d)
    return out

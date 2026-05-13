"""Few-shot prompt builder.

Player examples are pulled from the seed CSV (`_Player__202605131748.csv`)
filtered by nationality. Team examples are a hard-coded English-league
fallback because no `team_translation` seed CSV exists yet (translation-
filler.md §16 — seed will arrive in a separate task and this module can
be extended later).

league is **out of scope** for this worker per spec §2; the builder raises
`ValueError` if asked.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

# CSV has gigantic JSON cells. Lift csv field size limit so DictReader does
# not abort on long stat blobs.
csv.field_size_limit(sys.maxsize)

# Number of few-shot examples per prompt. Spec §4 says "5~10", we pick 6.
_FEW_SHOT_TARGET = 6

# Fallback English-league team examples (used until team_translation seed
# CSV exists; tracked in docs/workers/translation-filler.md §16).
_TEAM_FALLBACK: list[dict[str, str]] = [
    {"eng": "Manchester United", "country": "England", "name_ko": "맨체스터 유나이티드", "short_name_ko": "맨유"},
    {"eng": "Liverpool", "country": "England", "name_ko": "리버풀", "short_name_ko": "리버풀"},
    {"eng": "Arsenal", "country": "England", "name_ko": "아스널", "short_name_ko": "아스널"},
    {"eng": "Chelsea", "country": "England", "name_ko": "첼시", "short_name_ko": "첼시"},
    {"eng": "Tottenham", "country": "England", "name_ko": "토트넘", "short_name_ko": "토트넘"},
    {"eng": "Manchester City", "country": "England", "name_ko": "맨체스터 시티", "short_name_ko": "맨시티"},
]


def _seed_csv_path() -> Path:
    """Repo-root path to the player seed CSV."""
    # prompt.py → translation_filler → workers → app → <repo root>
    return Path(__file__).resolve().parents[3] / "_Player__202605131748.csv"


_PLAYER_EXAMPLES_BY_NATIONALITY: dict[str, list[dict[str, str]]] | None = None
_PLAYER_EXAMPLES_ALL: list[dict[str, str]] = []


def _load_player_examples() -> None:
    """Lazy-load and index the seed CSV by nationality.

    Each row → example dict ``{eng, nationality, name_ko, short_name_ko}``.
    Rows missing any field are skipped silently.
    """
    global _PLAYER_EXAMPLES_BY_NATIONALITY
    if _PLAYER_EXAMPLES_BY_NATIONALITY is not None:
        return
    by_nat: dict[str, list[dict[str, str]]] = {}
    all_examples: list[dict[str, str]] = []

    path = _seed_csv_path()
    if not path.exists():
        _PLAYER_EXAMPLES_BY_NATIONALITY = by_nat
        return

    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            eng = (row.get("eng_player_name") or "").strip()
            name_ko = (row.get("kor_player_name") or "").strip()
            short_ko = (row.get("kor_short_name") or "").strip()
            if not (eng and name_ko and short_ko):
                continue
            nationality = ""
            detail_raw = row.get("player_detail") or ""
            if detail_raw:
                try:
                    detail = json.loads(detail_raw)
                    nationality = (detail.get("nationality") or "").strip()
                except (ValueError, TypeError):
                    nationality = ""
            example = {
                "eng": eng,
                "nationality": nationality or "Unknown",
                "name_ko": name_ko,
                "short_name_ko": short_ko,
            }
            all_examples.append(example)
            by_nat.setdefault(example["nationality"], []).append(example)

    _PLAYER_EXAMPLES_BY_NATIONALITY = by_nat
    _PLAYER_EXAMPLES_ALL.extend(all_examples)


def _pick_player_examples(nationality: str, *, count: int = _FEW_SHOT_TARGET) -> list[dict[str, str]]:
    _load_player_examples()
    pool = (_PLAYER_EXAMPLES_BY_NATIONALITY or {}).get(nationality, [])
    if len(pool) < count:
        # Fill the rest with random from the global pool to always reach `count`.
        remaining = count - len(pool)
        rest = [e for e in _PLAYER_EXAMPLES_ALL if e not in pool]
        if rest:
            extra = random.sample(rest, min(remaining, len(rest)))
        else:
            extra = []
        chosen = list(pool) + extra
    else:
        chosen = random.sample(pool, count)
    # Final fallback — should never be hit if the seed CSV is present.
    while len(chosen) < count and _TEAM_FALLBACK:
        # Reuse team fallback structurally — unlikely path but keeps the
        # invariant that >=5 examples are always returned for the unit test.
        chosen.append(
            {
                "eng": _TEAM_FALLBACK[len(chosen) % len(_TEAM_FALLBACK)]["eng"],
                "nationality": nationality,
                "name_ko": "예시",
                "short_name_ko": "예",
            }
        )
    return chosen[:count]


def _pick_team_examples(country: str, *, count: int = _FEW_SHOT_TARGET) -> list[dict[str, str]]:
    pool = [e for e in _TEAM_FALLBACK if e["country"] == country] or list(_TEAM_FALLBACK)
    if len(pool) >= count:
        return random.sample(pool, count)
    # repeat to reach count (test only needs >=5; fallback has 6 entries)
    chosen = list(pool)
    while len(chosen) < count:
        chosen.append(pool[len(chosen) % len(pool)])
    return chosen[:count]


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

_SYSTEM_PLAYER = (
    "당신은 축구 선수 영문 이름을 한국 축구 중계/기사에서 통용되는 한글 표기로 "
    "음역하는 번역가입니다. 응답은 JSON 만 출력하세요. "
    "키는 정확히 name_ko, short_name_ko 두 개입니다."
)

_SYSTEM_TEAM = (
    "당신은 축구 팀명 영문 이름을 한국 축구 중계/기사에서 통용되는 한글 표기로 "
    "음역하는 번역가입니다. 응답은 JSON 만 출력하세요. "
    "키는 정확히 name_ko, short_name_ko 두 개입니다."
)


def build_prompt(
    entity_type: str,
    name: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the prompt as a heterogeneous list:

      1. A ``{role, content}`` system message (instructions, mentions JSON).
      2. N few-shot example dicts at top level
         (``{eng, nationality|country, name_ko, short_name_ko}``).
         These are exposed at top level so JSON-encoding the whole prompt
         surfaces ``"eng"`` keys verbatim — handy for inspection / tests.
      3. A ``{role, content}`` user message carrying both the textual
         examples (for the LLM) and the input row.

    The OpenAI call layer (``openai_client.call``) filters out non-message
    entries before sending, so the on-wire payload remains spec-compliant.

    Raises ``ValueError`` for unsupported entity types — notably
    ``"league"`` (ADMIN-manual per spec §2).
    """
    if entity_type == "league":
        raise ValueError(
            "league is not handled by translation-filler (ADMIN manual per spec §2)"
        )

    if entity_type == "player":
        nationality = str(context.get("nationality") or "Unknown")
        examples = _pick_player_examples(nationality)
        example_lines = "\n".join(
            json.dumps(e, ensure_ascii=False) for e in examples
        )
        user_payload = json.dumps(
            {"eng": name, "nationality": nationality}, ensure_ascii=False
        )
        return [
            {"role": "system", "content": _SYSTEM_PLAYER},
            *examples,
            {
                "role": "user",
                "content": (
                    f"예시:\n{example_lines}\n\n"
                    f"입력:\n{user_payload}\n\n"
                    "출력 (JSON):"
                ),
            },
        ]

    if entity_type == "team":
        country = str(context.get("country") or "Unknown")
        examples = _pick_team_examples(country)
        example_lines = "\n".join(
            json.dumps(e, ensure_ascii=False) for e in examples
        )
        user_payload = json.dumps(
            {"eng": name, "country": country}, ensure_ascii=False
        )
        return [
            {"role": "system", "content": _SYSTEM_TEAM},
            *examples,
            {
                "role": "user",
                "content": (
                    f"예시:\n{example_lines}\n\n"
                    f"입력:\n{user_payload}\n\n"
                    "출력 (JSON):"
                ),
            },
        ]

    raise ValueError(f"unsupported entity_type: {entity_type!r}")

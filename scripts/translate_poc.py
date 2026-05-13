#!/usr/bin/env python3
"""
Translation PoC: API-Football 영문 표기 → 한국 중계/기사 통용 표기

OpenAI Responses API + web_search 도구로 한국 스포츠 매체 도메인만 검색해
가장 자주 쓰이는 한글 표기를 산출한다.

Usage:
    pip install 'openai>=1.50'
    export OPENAI_API_KEY=sk-...
    python3 scripts/translate_poc.py

비용 견적: 11 entity × ~$0.0034 ≈ $0.04
"""

import json
import os
import sys
from openai import OpenAI

MODEL = "gpt-4.1"  # 정밀도 우선. filters(allowed_domains) 지원 모델

# gpt-4.1 (full) 은 web_search filters 를 지원하므로 도메인 화이트리스트로 하드 제한한다.
PREFERRED_KOREAN_SOURCES = [
    # namu.wiki 는 OpenAI web_search 가 크롤하지 못한다(404/blocked). 화이트리스트에서 제외.
    "ko.wikipedia.org",          # 한국어 위키백과: 축구 인물/팀 정본
    "sports.naver.com",
    "sports.daum.net",
    "mksports.co.kr",
    "sports.chosun.com",
    "sports.khan.co.kr",
    "interfootball.heraldcorp.com",
    "sportalkorea.com",
    "footballist.co.kr",
]

TRANSLATION_SCHEMA = {
    "name": "translation_result",
    "schema": {
        "type": "object",
        "properties": {
            "name_ko":       {"type": "string"},
            "short_name_ko": {"type": "string"},
            "confidence":    {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "sources":       {
                "type":  "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
        },
        "required":             ["name_ko", "short_name_ko", "confidence", "sources"],
        "additionalProperties": False,
    },
    "strict": True,
}

# (entity_type, name, context_dict)
TEST_CASES = [
    ("player", "Son Heung-Min",        {"team": "Tottenham Hotspur", "league": "Premier League"}),
    ("player", "Mohamed Salah",        {"team": "Liverpool",         "league": "Premier League"}),
    ("player", "C.Ronaldo",            {"team": None,                "league": None}),
    ("player", "Łukasz Fabiański",     {"team": "West Ham United",   "league": "Premier League"}),
    ("player", "N'Golo Kanté",         {"team": None,                "league": None}),
    ("player", "Dušan Vlahović",       {"team": "Juventus",          "league": None}),
    ("player", "Vinícius Júnior",      {"team": "Real Madrid",       "league": "Champions League"}),
    ("player", "J.Bellingham",         {"team": "Real Madrid",       "league": "Champions League"}),
    ("team",   "Manchester United",    {"league": "Premier League"}),
    ("team",   "Tottenham Hotspur",    {"league": "Premier League"}),
    ("competition", "Carabao Cup",     {}),
]


def build_prompt(entity_type: str, name: str, context: dict) -> str:
    ctx_lines = []
    if context.get("team"):
        ctx_lines.append(f'- team: "{context["team"]}"')
    if context.get("league"):
        ctx_lines.append(f'- league: "{context["league"]}"')
    ctx_block = "\n".join(ctx_lines) if ctx_lines else "- (no additional context)"

    sources_hint = ", ".join(PREFERRED_KOREAN_SOURCES)

    return f"""You are translating a football {entity_type} name from English (as provided by API-Football)
into the Korean broadcasting/news convention used in South Korea.

Use the web_search tool to look up Korean-language sources. Domains are restricted via filters
(ko.wikipedia.org and major Korean sports media).

Decision policy:
1. If you find this name spelled consistently in the searched sources, use that spelling
   and set confidence 0.8~1.0.
2. If you find some sources but they conflict, pick the spelling used by the most authoritative
   one (ko.wikipedia.org > sports.naver.com > sports.daum.net > others), and set confidence 0.6~0.8.
3. If web_search returns nothing useful, FALL BACK to your own knowledge of standard Korean
   football broadcasting convention. Still produce a best-effort translation with confidence 0.3~0.5.
   In this fallback case put the string "fallback:prior-knowledge" as the single source.
4. NEVER refuse. NEVER return prose. ALWAYS return the JSON object defined by the schema.

For input abbreviated as "X.Surname" (e.g. "C.Ronaldo", "J.Bellingham"), use the context to
identify the full player, then translate. short_name_ko should match Korean media convention
(e.g. "호날두", "벨링엄"). For famous players Korean media commonly uses just the surname.

If the input is abbreviated (e.g. "C.Ronaldo", "J.Bellingham"), use the provided context
(team, league) to identify the full player, then translate the full name. The short_name_ko
should reflect how Korean media typically refers to that player in short form
(e.g. "호날두" for Cristiano Ronaldo, "벨링엄" for Jude Bellingham).

Input:
- name: "{name}"
- entity_type: "{entity_type}"
{ctx_block}

Respond ONLY with a single JSON object (no code fences, no extra text):
{{"name_ko": "...", "short_name_ko": "...", "confidence": 0.0~1.0, "sources": ["url1", "url2"]}}

- name_ko        : full Korean name as used in Korean broadcast/news
- short_name_ko  : shortened form Korean media commonly uses
                   (e.g. "맨유" for Manchester United, "호날두" for Cristiano Ronaldo).
                   If no clear short form exists, repeat name_ko.
- confidence     : 0.0~1.0 based on how consistently Korean media uses this spelling
- sources        : up to 3 URLs actually consulted
"""


def parse_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def call_translate(client: OpenAI, entity_type: str, name: str, context: dict):
    prompt = build_prompt(entity_type, name, context)
    resp = client.responses.create(
        model=MODEL,
        tools=[{
            "type": "web_search",
            "filters": {"allowed_domains": PREFERRED_KOREAN_SOURCES},
        }],
        input=prompt,
        text={"format": {"type": "json_schema", **TRANSLATION_SCHEMA}},
    )
    text = resp.output_text
    return parse_json_response(text), text


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY 환경변수가 필요합니다.", file=sys.stderr)
        return 1

    client = OpenAI()

    print(f"\n{'=' * 80}")
    print(f"Translation PoC — model={MODEL}")
    print(f"allowed_domains (filters): {len(PREFERRED_KOREAN_SOURCES)} sites — {', '.join(PREFERRED_KOREAN_SOURCES[:3])}...")
    print(f"{'=' * 80}\n")

    summary = []
    for entity_type, name, context in TEST_CASES:
        print(f"[{entity_type:11s}] input: {name!r}  context: {context}")
        try:
            parsed, raw = call_translate(client, entity_type, name, context)
            if parsed:
                print(f"  → name_ko        : {parsed.get('name_ko')!r}")
                print(f"  → short_name_ko  : {parsed.get('short_name_ko')!r}")
                print(f"  → confidence     : {parsed.get('confidence')}")
                for src in (parsed.get("sources") or [])[:3]:
                    print(f"    src: {src}")
                summary.append((name, parsed.get("name_ko"), parsed.get("short_name_ko"),
                                parsed.get("confidence"), "OK"))
            else:
                print(f"  → JSON 파싱 실패. raw[:200]: {raw[:200]!r}")
                summary.append((name, None, None, None, "PARSE_FAIL"))
        except Exception as e:
            print(f"  → ERROR: {type(e).__name__}: {e}")
            summary.append((name, None, None, None, f"ERR:{type(e).__name__}"))
        print()

    print(f"\n{'=' * 80}\n요약 (input → name_ko / short_name_ko / confidence / status)\n{'=' * 80}")
    for row in summary:
        print(f"  {row[0]:25s} → {str(row[1]):20s} / {str(row[2]):15s} / "
              f"{str(row[3]):>5s} / {row[4]}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

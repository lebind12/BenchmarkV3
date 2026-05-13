"""W1 — translation-filler 단위 테스트.

전부 mock. DB, OpenAI 모두 in-process.

be-dev 가 `app/workers/translation_filler/` 를 작성하기 전까지 ImportError 로 fail
(TDD Red 정상).

API 가정 (be-dev 와 합의된 SSOT 인터페이스):
  - `app.workers.translation_filler.queue.fetch_queue(session, *, limit: int) -> list[QueueItem]`
      QueueItem: dataclass / TypedDict {entity_type, id, eng_name, context_a, context_b}
      entity_type in {"team", "player"}  (league 제외)
      SQL 은 UNION ALL with NULL OR 조건
  - `app.workers.translation_filler.prompt.build_prompt(entity_type, name, context) -> list[ChatMessage]`
      few-shot 5~10건 포함
  - `app.workers.translation_filler.openai_client.call(messages, *, client=None) -> dict|None`
      returns parsed JSON dict {name_ko, short_name_ko} or None on failure
      retry 1s/2s/4s on 5xx
      params: model=gpt-3.5-turbo, temperature=0, max_tokens=100, response_format=json_object
  - `app.workers.translation_filler.runner.run_cycle(session, openai_client, *, limit=50, semaphore=5) -> CycleResult`

dev 가 이름이 다른 함수로 구현하면 본 단위 테스트가 import 단계에서 fail → spec
일치 강제.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 모듈 import (Red 단계에서 ImportError 정상)
# ---------------------------------------------------------------------------

def _import_module():
    from app.workers import translation_filler  # noqa: F401
    from app.workers.translation_filler import (  # noqa: F401
        openai_client,
        prompt,
        queue,
        runner,
    )
    return {
        "translation_filler": translation_filler,
        "queue": queue,
        "prompt": prompt,
        "openai_client": openai_client,
        "runner": runner,
    }


@pytest.fixture(scope="module")
def mods():
    return _import_module()


# ---------------------------------------------------------------------------
# TF-U-01 큐 조회 SQL
# ---------------------------------------------------------------------------

def test_tf_u01_queue_sql_unions_team_and_player_not_league(mods):
    queue = mods["queue"]
    # fetch_queue 는 SQLAlchemy session 을 받음. 빈 결과를 반환하도록 mock.
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    result = queue.fetch_queue(session, limit=50)
    # mock 의 execute 가 받은 첫 인자는 SQL Text or selectable
    args, _ = session.execute.call_args
    sql_obj = args[0]
    sql_text = str(getattr(sql_obj, "text", sql_obj)).lower()

    # 필수 키워드
    for kw in ("team_translation", "player_translation", "name_ko is null", "union all"):
        assert kw in sql_text, f"queue SQL 누락: {kw!r}\n--- SQL ---\n{sql_text}"
    # league 처리 제외
    assert "league_translation" not in sql_text, (
        "league 는 본 워커 처리 대상이 아님 (ADMIN manual)"
    )
    assert result == []


# ---------------------------------------------------------------------------
# TF-U-02 빈 큐 즉시 종료
# ---------------------------------------------------------------------------

def test_tf_u02_empty_queue_short_circuits(mods):
    runner = mods["runner"]
    session = MagicMock()
    # fetch_queue 가 빈 list 를 반환하도록 패치
    openai_mock = AsyncMock()
    with patch.object(mods["queue"], "fetch_queue", return_value=[]):
        res = asyncio.run(runner.run_cycle(session, openai_client=openai_mock))
    openai_mock.assert_not_called()
    # CycleResult 의 openai_calls / processed_count 가 0
    assert getattr(res, "openai_calls", 0) == 0
    assert getattr(res, "processed_count", 0) == 0


# ---------------------------------------------------------------------------
# TF-U-03 few-shot prompt 빌더
# ---------------------------------------------------------------------------

def test_tf_u03_prompt_builder_player_nationality_match(mods):
    prompt = mods["prompt"]
    msgs = prompt.build_prompt(
        entity_type="player",
        name="Bukayo Saka",
        context={"nationality": "England"},
    )
    blob = json.dumps(msgs, ensure_ascii=False)
    # 입력 이름이 포함
    assert "Bukayo Saka" in blob
    # 최소 5건의 예시 (eng 키 5회 이상 등장)
    assert blob.count('"eng"') >= 5, f"few-shot 예시 5건 이상 필요. count={blob.count('eng')}"
    # JSON 응답 강제 문구
    assert "json" in blob.lower()


def test_tf_u03_prompt_builder_team_country_match(mods):
    prompt = mods["prompt"]
    msgs = prompt.build_prompt(
        entity_type="team",
        name="Manchester United",
        context={"country": "England"},
    )
    blob = json.dumps(msgs, ensure_ascii=False)
    assert "Manchester United" in blob
    assert blob.count('"eng"') >= 5


def test_tf_u03_prompt_builder_league_unsupported(mods):
    prompt = mods["prompt"]
    with pytest.raises((ValueError, NotImplementedError)):
        prompt.build_prompt(
            entity_type="league",
            name="Premier League",
            context={"country_name": "England"},
        )


# ---------------------------------------------------------------------------
# TF-U-04 응답 파싱
# ---------------------------------------------------------------------------

def test_tf_u04_parse_valid_json(mods):
    parsed = mods["openai_client"].parse_response(
        '{"name_ko": "부카요 사카", "short_name_ko": "사카"}'
    )
    assert parsed == {"name_ko": "부카요 사카", "short_name_ko": "사카"}


def test_tf_u04_parse_broken_json(mods):
    assert mods["openai_client"].parse_response("not a json") is None


def test_tf_u04_parse_missing_short_name(mods):
    assert mods["openai_client"].parse_response('{"name_ko": "X"}') is None


def test_tf_u04_parse_empty_string(mods):
    assert mods["openai_client"].parse_response('{"name_ko": "", "short_name_ko": "X"}') is None


# ---------------------------------------------------------------------------
# TF-U-05 OpenAI 파라미터
# ---------------------------------------------------------------------------

def test_tf_u05_openai_call_parameters(mods):
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"name_ko":"A","short_name_ko":"B"}'))]
        )
    )
    asyncio.run(
        mods["openai_client"].call(
            messages=[{"role": "user", "content": "x"}], client=fake_client
        )
    )
    fake_client.chat.completions.create.assert_called()
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs.get("model") == "gpt-3.5-turbo"
    assert kwargs.get("temperature") == 0
    assert kwargs.get("max_tokens") == 100
    assert kwargs.get("response_format") == {"type": "json_object"}


# ---------------------------------------------------------------------------
# TF-U-06 배치 상한 50
# ---------------------------------------------------------------------------

def test_tf_u06_batch_limit_50(mods):
    runner = mods["runner"]
    queue_mod = mods["queue"]
    session = MagicMock()
    # 200 row 입력
    big_queue = [
        {"entity_type": "player", "id": i, "eng_name": f"P{i}", "context_a": "England", "context_b": ""}
        for i in range(200)
    ]
    openai_mock = AsyncMock(
        return_value={"name_ko": "X", "short_name_ko": "X"}
    )
    with patch.object(queue_mod, "fetch_queue", return_value=big_queue) as fq:
        asyncio.run(runner.run_cycle(session, openai_client=openai_mock, limit=50))
    # fetch_queue 가 limit=50 을 받아야 함
    assert fq.call_args.kwargs.get("limit") == 50
    # 한 사이클 OpenAI 호출 ≤ 50
    assert openai_mock.call_count <= 50


# ---------------------------------------------------------------------------
# TF-U-07 semaphore 5 동시성
# ---------------------------------------------------------------------------

def test_tf_u07_semaphore_concurrency_5(mods):
    runner = mods["runner"]
    queue_mod = mods["queue"]
    session = MagicMock()
    q = [
        {"entity_type": "player", "id": i, "eng_name": f"P{i}", "context_a": "England", "context_b": ""}
        for i in range(30)
    ]

    in_flight = 0
    max_in_flight = 0

    async def fake_openai(*_args, **_kwargs):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return {"name_ko": "X", "short_name_ko": "X"}

    openai_mock = AsyncMock(side_effect=fake_openai)
    with patch.object(queue_mod, "fetch_queue", return_value=q):
        asyncio.run(runner.run_cycle(session, openai_client=openai_mock, limit=50, semaphore=5))
    assert max_in_flight <= 5, f"semaphore 5 위반: max_in_flight={max_in_flight}"


# ---------------------------------------------------------------------------
# TF-U-08 지수 백오프
# ---------------------------------------------------------------------------

def test_tf_u08_exponential_backoff_1_2_4(mods):
    fake_client = MagicMock()
    err = Exception("OpenAI 5xx")
    fake_client.chat.completions.create = AsyncMock(side_effect=err)

    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with patch("asyncio.sleep", side_effect=fake_sleep):
        result = asyncio.run(
            mods["openai_client"].call(
                messages=[{"role": "user", "content": "x"}], client=fake_client
            )
        )
    assert result is None, "3회 실패 후 None 반환 필요"
    # 호출 4회 (초기 1 + 재시도 3)
    assert fake_client.chat.completions.create.call_count >= 3
    # sleeps 의 첫 3개가 [1, 2, 4] (대략)
    waited = [s for s in sleeps if s in (1, 2, 4)]
    assert waited[:3] == [1, 2, 4], f"백오프 시퀀스 어긋남: {sleeps}"


# ---------------------------------------------------------------------------
# TF-U-09 league 처리 제외
# ---------------------------------------------------------------------------

def test_tf_u09_league_entity_skipped_in_runner(mods):
    runner = mods["runner"]
    queue_mod = mods["queue"]
    session = MagicMock()
    queue = [
        {"entity_type": "league", "id": 1, "eng_name": "Premier League", "context_a": "England", "context_b": "League"},
        {"entity_type": "player", "id": 1, "eng_name": "Bukayo Saka", "context_a": "England", "context_b": ""},
    ]
    openai_mock = AsyncMock(return_value={"name_ko": "X", "short_name_ko": "X"})
    with patch.object(queue_mod, "fetch_queue", return_value=queue):
        res = asyncio.run(runner.run_cycle(session, openai_client=openai_mock))
    # league 는 처리 제외 → OpenAI 호출 1회 (player 만)
    assert openai_mock.call_count == 1, (
        f"league 가 OpenAI 로 흘러들어감 (호출 {openai_mock.call_count}회)"
    )
    # CycleResult.processed_count 이 1 (player 만)
    assert getattr(res, "processed_count", 0) == 1

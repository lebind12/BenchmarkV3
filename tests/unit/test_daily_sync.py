"""W2 — daily-sync 단위 테스트.

전부 mock. DB / API-Football 모두 in-process.
be-dev 가 `app/workers/daily_sync/` 작성 전까지 ImportError 로 fail (TDD Red).

가정 인터페이스 (dev 합의 — testplan §6 참고):
  app.workers.daily_sync.parsers
    - parse_league(api_response) -> dict (league row)
    - parse_team(api_response_entry) -> tuple[venue_dict, team_dict]
    - parse_fixture(api_response_entry) -> dict (fixture row; home_team_external_id may be None)
    - parse_player(api_response_entry) -> tuple[player_dict, list[player_season_stat_dict]]
    - parse_standing(api_response_entry) -> list[standings_dict]
    - parse_height_cm(s: str|None) -> int|None     # '188 cm' -> 188
    - parse_weight_kg(s: str|None) -> int|None
  app.workers.daily_sync.queries
    - build_active_fixture_query(active_league_ids, current_season) -> SQL text
    - active_leagues(session) -> list[LeagueRow]    # filters is_active=true
  app.workers.daily_sync.api_client
    - APIFootballClient protocol + DefaultAPIFootballClient
  app.workers.daily_sync.runner
    - run_cycle(session, api_client, *, semaphore=6) -> CycleResult
  app.workers.daily_sync.steps
    - step1_leagues, step2_teams, ... step9_translations 각 entry 함수
  Exception type:
    - DailySyncFatalError (401 / DB 접속 불가 시 raise)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "api_football"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# 모듈 import (Red 단계 ImportError 정상)
# ---------------------------------------------------------------------------

def _import_mods():
    from app.workers import daily_sync  # noqa: F401
    from app.workers.daily_sync import (  # noqa: F401
        api_client,
        parsers,
        queries,
        runner,
        steps,
    )
    return {
        "daily_sync": daily_sync,
        "parsers": parsers,
        "queries": queries,
        "api_client": api_client,
        "runner": runner,
        "steps": steps,
    }


@pytest.fixture(scope="module")
def mods():
    return _import_mods()


# ---------------------------------------------------------------------------
# DS-U-01 Step 1 league 메타 sync
# ---------------------------------------------------------------------------

def test_ds_u01_parse_league_maps_fields(mods):
    parsed = mods["parsers"].parse_league(_load("leagues_39.json")["response"][0])
    assert parsed["external_id"] == 39
    assert parsed["name"] == "Premier League"
    assert parsed["type"] == "League"
    assert parsed["country_name"] == "England"
    assert parsed["country_code"] == "GB"
    assert parsed["country_flag"].endswith(".svg")
    assert parsed["current_season"] == 2024  # seasons[current=true].year
    assert parsed["logo_url"].endswith(".png")


def test_ds_u01_parse_league_ucl_cup_type(mods):
    parsed = mods["parsers"].parse_league(_load("leagues_2.json")["response"][0])
    assert parsed["type"] == "Cup"
    assert parsed["current_season"] == 2024


# ---------------------------------------------------------------------------
# DS-U-02 Step 2 team + venue
# ---------------------------------------------------------------------------

def test_ds_u02_parse_team_venue_pair(mods):
    entry = _load("teams_39_2024.json")["response"][0]
    venue, team = mods["parsers"].parse_team(entry)
    assert venue["external_id"] == 556
    assert venue["name"] == "Old Trafford"
    assert team["external_id"] == 33
    assert team["name"] == "Manchester United"
    assert team["code"] == "MUN"
    assert team["founded"] == 1878
    assert team["is_national"] is False
    # slug 형식: slugify(name)-external_id
    assert team["slug"] == "manchester-united-33"


# ---------------------------------------------------------------------------
# DS-U-03 Step 3 fixture (NULL home/away)
# ---------------------------------------------------------------------------

def test_ds_u03_parse_fixture_normal(mods):
    entry = _load("fixtures_39_2024.json")["response"][0]
    fx = mods["parsers"].parse_fixture(entry)
    assert fx["external_id"] == 1001
    assert fx["home_team_external_id"] == 33
    assert fx["away_team_external_id"] == 50
    assert fx["status_short"] == "FT"
    assert fx["score_ft_home"] == 2
    assert fx["score_ft_away"] == 1
    assert fx["home_winner"] is True
    assert fx["away_winner"] is False


def test_ds_u03_parse_fixture_cup_draw_null_teams(mods):
    entry = _load("fixtures_2_2024.json")["response"][0]
    fx = mods["parsers"].parse_fixture(entry)
    assert fx["external_id"] == 9001
    assert fx["home_team_external_id"] is None, "추첨 미정 → home None"
    assert fx["away_team_external_id"] is None, "추첨 미정 → away None"
    assert fx["status_short"] == "TBD"


# ---------------------------------------------------------------------------
# DS-U-04 Step 4 활성 fixture 큐 SQL
# ---------------------------------------------------------------------------

def test_ds_u04_active_fixture_query_includes_thresholds(mods):
    sql = mods["queries"].build_active_fixture_query(
        active_league_ids=[1, 2, 3, 4, 5], current_season=2024
    )
    sql_text = str(getattr(sql, "text", sql)).lower()
    for kw in ("48 hours", "14 days", "status_short", "league_id"):
        assert kw in sql_text, f"누락: {kw}\n--- SQL ---\n{sql_text}"
    # 종료 상태 NOT IN 조건
    for st in ("'ft'", "'aet'", "'pen'", "'canc'", "'pst'"):
        assert st in sql_text, f"종료 status 누락: {st}"


# ---------------------------------------------------------------------------
# DS-U-05 Step 5 fixture_detail 3 calls 묶음
# ---------------------------------------------------------------------------

def test_ds_u05_fixture_detail_combines_three_responses(mods):
    events = _load("fixtures_events_1001.json")
    stats = _load("fixtures_statistics_1001.json")
    lineups = _load("fixtures_lineups_1001.json")
    detail = mods["parsers"].combine_fixture_detail(
        fixture_external_id=1001, events=events, statistics=stats, lineups=lineups
    )
    assert detail["events"] == events.get("response")
    assert detail["statistics"] == stats.get("response")
    assert detail["lineups"] == lineups.get("response")
    assert detail.get("fetched_at") is not None


# ---------------------------------------------------------------------------
# DS-U-06 Step 6 player + height/weight 파싱
# ---------------------------------------------------------------------------

def test_ds_u06_parse_height_weight(mods):
    p = mods["parsers"]
    assert p.parse_height_cm("188 cm") == 188
    assert p.parse_height_cm("179 cm") == 179
    assert p.parse_height_cm(None) is None
    assert p.parse_height_cm("unknown") is None
    assert p.parse_weight_kg("78 kg") == 78
    assert p.parse_weight_kg(None) is None


def test_ds_u06_parse_player_full(mods):
    entry = _load("players_33_2024.json")["response"][0]
    player, stats = mods["parsers"].parse_player(entry)
    assert player["external_id"] == 2
    assert player["name"] == "Bruno Fernandes"
    assert player["nationality"] == "Portugal"
    assert player["height_cm"] == 179
    assert player["weight_kg"] == 69
    assert player["birth_date"] == "1994-09-08" or hasattr(player["birth_date"], "isoformat")
    assert len(stats) == 1
    s = stats[0]
    # API typo appearences → appearances
    assert s["appearances"] == 10
    assert s["minutes"] == 900
    assert s["position"] == "Midfielder"
    assert s["shirt_number"] == 8
    assert float(s["rating"]) == 7.43
    assert s["goals"] == 4
    assert s["assists"] == 5
    assert s["yellow_cards"] == 2
    assert s["red_cards"] == 0
    # raw_stats 보존
    assert "raw_stats" in s


def test_ds_u06_parse_player_unknown_height(mods):
    entry = _load("players_33_2024.json")["response"][1]
    player, _ = mods["parsers"].parse_player(entry)
    assert player["height_cm"] is None
    assert player["weight_kg"] is None


# ---------------------------------------------------------------------------
# DS-U-07 Step 7 standings group_name
# ---------------------------------------------------------------------------

def test_ds_u07_parse_standings_league_no_group(mods):
    parsed = mods["parsers"].parse_standing(_load("standings_39_2024.json")["response"][0])
    # 리그는 group_name 가 NULL (UI 표시명일 뿐, API 의 group='Premier League' 는
    # 리그 단일 그룹이므로 spec 상 NULL 로 매핑)
    for row in parsed:
        assert row["group_name"] is None or row["group_name"] == "Premier League"
    # 최소 2팀
    assert len(parsed) == 2


def test_ds_u07_parse_standings_ucl_group_name(mods):
    parsed = mods["parsers"].parse_standing(_load("standings_2_2024.json")["response"][0])
    groups = {row["group_name"] for row in parsed}
    assert "Group A" in groups, f"group_name 매핑 실패: {groups}"


# ---------------------------------------------------------------------------
# DS-U-08 Step 8 team_season 정션 upsert
# ---------------------------------------------------------------------------

def test_ds_u08_team_season_uses_on_conflict_do_nothing(mods):
    steps = mods["steps"]
    session = MagicMock()
    captured_sqls: list[str] = []

    def _exec(sql, *_a, **_kw):
        captured_sqls.append(str(getattr(sql, "text", sql)).lower())
        return MagicMock()

    session.execute.side_effect = _exec

    # (team_id, league_id, season_year) 3-튜플
    pairs = [(33, 1, 2024), (50, 1, 2024)]
    steps.step8_team_season(session, pairs)
    blob = " | ".join(captured_sqls)
    assert "team_season" in blob
    assert "on conflict" in blob
    assert "do nothing" in blob


# ---------------------------------------------------------------------------
# DS-U-09 Step 9 *_translation
# ---------------------------------------------------------------------------

def test_ds_u09_translation_row_insert_on_conflict_do_nothing(mods):
    steps = mods["steps"]
    session = MagicMock()
    captured: list[str] = []

    def _exec(sql, *_a, **_kw):
        captured.append(str(getattr(sql, "text", sql)).lower())
        return MagicMock()

    session.execute.side_effect = _exec
    steps.step9_translations(
        session,
        new_league_ids=[1, 2],
        new_team_ids=[10],
        new_player_ids=[100, 101, 102],
    )
    blob = " | ".join(captured)
    for tbl in ("league_translation", "team_translation", "player_translation"):
        assert tbl in blob, f"{tbl} 누락"
    assert "on conflict" in blob
    assert "do nothing" in blob


# ---------------------------------------------------------------------------
# DS-U-10 semaphore 6 동시성
# ---------------------------------------------------------------------------

def test_ds_u10_semaphore_concurrency_6(mods):
    runner = mods["runner"]
    in_flight = 0
    max_in_flight = 0

    async def fake_call(*_a, **_kw):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.005)
        in_flight -= 1
        return {"response": []}

    client = MagicMock()
    for name in (
        "get_leagues", "get_teams", "get_fixtures",
        "get_fixture_events", "get_fixture_statistics", "get_fixture_lineups",
        "get_players", "get_standings",
    ):
        setattr(client, name, AsyncMock(side_effect=fake_call))

    session = MagicMock()
    # active_leagues 가 빈 list 반환하지 않도록 30개 가짜 league 주입
    with patch.object(
        mods["queries"], "active_leagues",
        return_value=[MagicMock(id=i + 1, external_id=i + 1, current_season=2024) for i in range(30)],
    ):
        asyncio.run(runner.run_cycle(session, api_client=client, semaphore=6))

    assert max_in_flight <= 6, f"semaphore=6 위반 (max={max_in_flight})"


# ---------------------------------------------------------------------------
# DS-U-11 백오프 1s/2s/4s × 3회
# ---------------------------------------------------------------------------

def test_ds_u11_exponential_backoff(mods):
    api = mods["api_client"]
    fake = MagicMock()
    fake.get.side_effect = Exception("simulated 5xx")
    sleeps: list[float] = []

    async def _fake_sleep(s):
        sleeps.append(s)

    with patch("asyncio.sleep", side_effect=_fake_sleep):
        # client 의 retry wrapper 호출. 인터페이스 가정:
        # api_client.call_with_retry(coro_factory, retries=3) 또는 매 메소드가 내부 retry
        client = api.DefaultAPIFootballClient(http=fake, api_key="x")
        try:
            asyncio.run(client.get_leagues(external_id=39))
        except Exception:
            pass
    waited = [s for s in sleeps if s in (1, 2, 4)]
    assert waited[:3] == [1, 2, 4], f"백오프 시퀀스 어긋남: {sleeps}"


# ---------------------------------------------------------------------------
# DS-U-12 멱등성 (in-memory)
# ---------------------------------------------------------------------------

def test_ds_u12_parser_idempotent(mods):
    """같은 응답 2회 파싱 → 결과 동일."""
    entry = _load("teams_39_2024.json")["response"][0]
    v1, t1 = mods["parsers"].parse_team(entry)
    v2, t2 = mods["parsers"].parse_team(entry)
    assert v1 == v2
    assert t1 == t2


# ---------------------------------------------------------------------------
# DS-U-13 활성 league 동적 조회
# ---------------------------------------------------------------------------

def test_ds_u13_active_leagues_filters_is_active_true(mods):
    queries = mods["queries"]
    session = MagicMock()
    # mock execute 가 SQL 받았을 때 'is_active' / 'true' 가 포함되어야 함
    captured: list[str] = []

    def _exec(sql, *_a, **_kw):
        captured.append(str(getattr(sql, "text", sql)).lower())
        mock_res = MagicMock()
        mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = _exec
    queries.active_leagues(session)
    blob = " | ".join(captured)
    assert "league" in blob
    assert "is_active" in blob and "true" in blob, (
        f"is_active=true 필터 누락: {blob}"
    )


# ---------------------------------------------------------------------------
# DS-U-14 에러 분기
# ---------------------------------------------------------------------------

class _Http401(Exception):
    status_code = 401


class _Http500(Exception):
    status_code = 500


class _Http404(Exception):
    status_code = 404


def test_ds_u14_401_is_fatal(mods):
    api = mods["api_client"]
    fake = MagicMock()
    fake.get.side_effect = _Http401("auth")

    client = api.DefaultAPIFootballClient(http=fake, api_key="x")
    with pytest.raises((api.DailySyncFatalError, _Http401)):
        asyncio.run(client.get_leagues(external_id=39))


def test_ds_u14_500_retried_then_skipped(mods):
    api = mods["api_client"]
    fake = MagicMock()
    fake.get.side_effect = _Http500("server")

    async def _no_sleep(_):
        return None

    client = api.DefaultAPIFootballClient(http=fake, api_key="x")
    with patch("asyncio.sleep", side_effect=_no_sleep):
        result = asyncio.run(client.get_leagues(external_id=39))
    # 5xx 는 retry 후 None 또는 빈 응답 반환 (fatal 아님)
    assert result is None or result == {} or result.get("response") == []


def test_ds_u14_404_immediate_skip(mods):
    api = mods["api_client"]
    fake = MagicMock()
    fake.get.side_effect = _Http404("not found")

    sleeps: list[float] = []

    async def _fake_sleep(s):
        sleeps.append(s)

    client = api.DefaultAPIFootballClient(http=fake, api_key="x")
    with patch("asyncio.sleep", side_effect=_fake_sleep):
        result = asyncio.run(client.get_leagues(external_id=39))
    # 4xx 는 즉시 skip — sleep 호출 거의 없음 (백오프 안 함)
    assert sleeps == [] or all(s == 0 for s in sleeps), (
        f"4xx 에 백오프 발생 (sleeps={sleeps})"
    )
    assert result is None or result == {} or result.get("response") == []

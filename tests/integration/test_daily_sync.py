"""W2 — daily-sync 통합 테스트.

격리 schema 에 alembic upgrade head 적용 후, mock APIFootballClient 를 주입해
1 사이클 실행. 실 API-Football 호출 금지 (Ultra plan quota 보호 + 결정성).

be-dev 가 `app/workers/daily_sync/` 미작성 시 ImportError 로 fail (TDD Red 정상).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "api_football"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_alembic(args: list[str], schema: str, db_url: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    existing = env.get("PGOPTIONS", "")
    env["PGOPTIONS"] = f"-c search_path={schema} {existing}".strip()
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=_project_root(),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture(scope="function")
def migrated_db(isolated_db, test_database_url):
    engine, schema = isolated_db
    result = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head 실패 (schema={schema})\n{result.stdout}\n{result.stderr}"
        )
    return engine, schema


# ---------------------------------------------------------------------------
# 헬퍼: 5 league seed (is_active=true)
# ---------------------------------------------------------------------------

def _seed_leagues(conn) -> dict[int, int]:
    """5리그 시드 INSERT. 반환: {external_id: internal_id}."""
    leagues = [
        (39, "Premier League", "League", "premier-league", 2024),
        (2,  "UEFA Champions League", "Cup", "champions-league", 2024),
        (3,  "UEFA Europa League", "Cup", "europa-league", 2024),
        (48, "League Cup (Carabao)", "Cup", "carabao-cup", 2024),
        (45, "FA Cup", "Cup", "fa-cup", 2024),
    ]
    out = {}
    for ext, name, type_, slug, season in leagues:
        lid = conn.execute(
            text(
                "INSERT INTO league (external_id, name, type, slug, current_season, is_active) "
                "VALUES (:e, :n, :t, :s, :y, true) RETURNING id"
            ),
            {"e": ext, "n": name, "t": type_, "s": slug, "y": season},
        ).scalar()
        out[ext] = lid
    return out


def _make_mock_api(
    *,
    extra_fixtures_response: dict | None = None,
    detail_fail_for: set[int] | None = None,
):
    """기본 fixture JSON 으로 응답하는 mock client.

    - extra_fixtures_response: 특정 (league, season) 의 fixtures 응답 override.
    - detail_fail_for: 이 fixture_id 들의 detail (events/statistics/lineups) 호출은
      Exception 을 반복 raise (Step 5 부분 실패 회복 테스트).
    """
    detail_fail_for = detail_fail_for or set()
    client = MagicMock()

    async def _get_leagues(*, external_id):
        path = FIXTURES / f"leagues_{external_id}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_teams(*, league, season):
        path = FIXTURES / f"teams_{league}_{season}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_fixtures(*, league, season):
        if extra_fixtures_response is not None:
            return extra_fixtures_response
        path = FIXTURES / f"fixtures_{league}_{season}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_fixture_events(*, fixture):
        if fixture in detail_fail_for:
            raise Exception("simulated 5xx (events)")
        path = FIXTURES / f"fixtures_events_{fixture}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_fixture_statistics(*, fixture):
        if fixture in detail_fail_for:
            raise Exception("simulated 5xx (statistics)")
        path = FIXTURES / f"fixtures_statistics_{fixture}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_fixture_lineups(*, fixture):
        if fixture in detail_fail_for:
            raise Exception("simulated 5xx (lineups)")
        path = FIXTURES / f"fixtures_lineups_{fixture}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    async def _get_players(*, team, season, page=1):
        path = FIXTURES / f"players_{team}_{season}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": [], "paging": {"current": 1, "total": 1}}

    async def _get_standings(*, league, season):
        path = FIXTURES / f"standings_{league}_{season}.json"
        return json.loads(path.read_text()) if path.exists() else {"response": []}

    client.get_leagues           = AsyncMock(side_effect=_get_leagues)
    client.get_teams             = AsyncMock(side_effect=_get_teams)
    client.get_fixtures          = AsyncMock(side_effect=_get_fixtures)
    client.get_fixture_events    = AsyncMock(side_effect=_get_fixture_events)
    client.get_fixture_statistics= AsyncMock(side_effect=_get_fixture_statistics)
    client.get_fixture_lineups   = AsyncMock(side_effect=_get_fixture_lineups)
    client.get_players           = AsyncMock(side_effect=_get_players)
    client.get_standings         = AsyncMock(side_effect=_get_standings)
    return client


# ---------------------------------------------------------------------------
# DS-I-01 빈 DB → 1 사이클
# ---------------------------------------------------------------------------

def test_ds_i01_full_cycle_populates_all_tables(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)

    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))

    with engine.connect() as conn:
        counts = {
            tbl: conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            for tbl in (
                "league", "venue", "team", "fixture",
                "fixture_detail", "player", "player_season_stat",
                "standings", "team_season",
                "league_translation", "team_translation", "player_translation",
            )
        }
    assert counts["league"] >= 5
    for tbl in ("venue", "team", "fixture", "player", "standings",
                "team_season", "league_translation",
                "team_translation", "player_translation"):
        assert counts[tbl] > 0, f"{tbl} row 미생성 (counts={counts})"


# ---------------------------------------------------------------------------
# DS-I-02 멱등성
# ---------------------------------------------------------------------------

def test_ds_i02_idempotent_two_cycles(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)

    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))
    with engine.connect() as conn:
        counts1 = {
            tbl: conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            for tbl in ("league", "venue", "team", "fixture", "player",
                        "team_season", "league_translation", "team_translation")
        }

    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))
    with engine.connect() as conn:
        counts2 = {
            tbl: conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            for tbl in ("league", "venue", "team", "fixture", "player",
                        "team_season", "league_translation", "team_translation")
        }
    assert counts1 == counts2, f"멱등성 위반: {counts1} → {counts2}"


# ---------------------------------------------------------------------------
# DS-I-03 활성 fixture 큐 동작
# ---------------------------------------------------------------------------

def test_ds_i03_only_active_fixtures_get_detail_calls(migrated_db):
    """종료 후 48h 이상 지난 fixture 는 detail 호출 대상에서 제외.
    종료 직후 / 미래 / 진행 중 fixture 는 포함.
    """
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)

    # 사이클 1: 기본 mock — fixtures_39_2024.json 에 FT(과거), NS(미래), 1H(진행) 3개
    # fixtures_39_2024.json 의 1001(FT) 는 2024-08-16, 1002(NS) 는 2099-01-01 미래, 1003(1H) 는 진행 중.
    # 본 테스트가 실행되는 시점 (지금) 기준으로 1001 의 kickoff_at 은 이미 48h 이상 지남 → step5 제외
    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))

    # 호출된 fixture id 추출
    called_ids = {
        c.kwargs["fixture"] for c in api.get_fixture_events.call_args_list
    }
    assert 1001 not in called_ids, "오래된 FT fixture 가 detail 호출됨"
    # 1002 (미래 14d 이내인지는 2099 라 가시적 미래 — 14d 범위 밖일 수 있음 / 본 케이스는 IT-04 와 묶어 분석)
    # 1003 (진행 중) 은 status_short NOT IN 종료세트 조건으로 활성
    assert 1003 in called_ids, "진행 중 fixture 가 detail 호출 대상에서 빠짐"


# ---------------------------------------------------------------------------
# DS-I-04 컵 추첨 미정 NULL home/away
# ---------------------------------------------------------------------------

def test_ds_i04_cup_draw_null_teams_inserted(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)

    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT home_team_id, away_team_id, round, status_short "
                "FROM fixture WHERE external_id = 9001"
            )
        ).first()
    assert row is not None, "UCL TBD fixture 가 INSERT 되지 않음"
    assert row.home_team_id is None, "추첨 미정 home 이 NULL 가 아님"
    assert row.away_team_id is None, "추첨 미정 away 가 NULL 가 아님"


# ---------------------------------------------------------------------------
# DS-I-05 is_active=false league skip
# ---------------------------------------------------------------------------

def test_ds_i05_inactive_league_is_skipped(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)
        # UCL 비활성화
        conn.execute(
            text("UPDATE league SET is_active = false WHERE external_id = 2")
        )

    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))

    # mock 의 get_leagues / get_teams / get_fixtures 가 external_id=2 로 불리지 않아야 함
    for method_name, kw in (
        ("get_leagues", "external_id"),
        ("get_teams", "league"),
        ("get_fixtures", "league"),
        ("get_standings", "league"),
    ):
        method = getattr(api, method_name)
        called_ids = [c.kwargs.get(kw) for c in method.call_args_list]
        assert 2 not in called_ids, (
            f"{method_name} 가 inactive league(2) 로 호출됨: {called_ids}"
        )

    # UCL 의 TBD fixture 도 INSERT 되면 안 됨
    with engine.connect() as conn:
        cnt = conn.execute(
            text("SELECT COUNT(*) FROM fixture WHERE external_id = 9001")
        ).scalar()
    assert cnt == 0, "inactive league 의 fixture 가 INSERT 됨"


# ---------------------------------------------------------------------------
# DS-I-06 번역 한글 보호
# ---------------------------------------------------------------------------

def test_ds_i06_translation_korean_preserved(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        ext_to_id = _seed_leagues(conn)
        # 미리 league_translation 에 한글 INSERT
        conn.execute(
            text(
                "INSERT INTO league_translation (league_id, name_ko, short_name_ko) "
                "VALUES (:l, '프리미어 리그', 'EPL')"
            ),
            {"l": ext_to_id[39]},
        )

    api = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api))

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT name_ko, short_name_ko FROM league_translation "
                "WHERE league_id = :l"
            ),
            {"l": ext_to_id[39]},
        ).first()
    assert row.name_ko == "프리미어 리그", "기존 한글 name_ko 덮어쓰기 발생"
    assert row.short_name_ko == "EPL", "기존 한글 short_name_ko 덮어쓰기 발생"


# ---------------------------------------------------------------------------
# DS-I-07 Step 5 부분 실패 → 다음 사이클 회복
# ---------------------------------------------------------------------------

def test_ds_i07_partial_detail_failure_recovers_next_cycle(migrated_db):
    from app.workers.daily_sync.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _seed_leagues(conn)

    # 사이클 1: fixture_id=1003 의 detail 호출 항상 실패 (1003 은 active 인 진행 중 fixture)
    api1 = _make_mock_api(detail_fail_for={1003})

    async def _no_sleep(_):
        return None

    with Session(engine) as session:
        # 백오프 sleep 우회로 테스트 시간 단축
        from unittest.mock import patch
        with patch("asyncio.sleep", side_effect=_no_sleep):
            asyncio.run(run_cycle(session, api_client=api1))

    with engine.connect() as conn:
        cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM fixture_detail fd "
                "JOIN fixture f ON f.id = fd.fixture_id WHERE f.external_id = 1003"
            )
        ).scalar()
    assert cnt == 0, "실패한 fixture 의 detail 이 row 로 만들어짐"

    # 사이클 2: 정상화. 회복되어 detail row 생성
    api2 = _make_mock_api()
    with Session(engine) as session:
        asyncio.run(run_cycle(session, api_client=api2))

    with engine.connect() as conn:
        cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM fixture_detail fd "
                "JOIN fixture f ON f.id = fd.fixture_id WHERE f.external_id = 1003"
            )
        ).scalar()
    assert cnt == 1, "사이클 2 에서 회복되지 않음"

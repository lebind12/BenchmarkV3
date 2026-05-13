"""L3 — h2h_fixture 통합 테스트.

격리 schema 에 alembic upgrade head (0001+0002+0003+0004) 적용 후 검증.
L2 (0003) 머지 전에는 alembic 의 revision chain 결손으로 fail (Red 정상).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


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


EXPECTED_17 = {
    "league", "league_translation", "venue", "team", "team_translation",
    "team_season", "player", "player_translation", "player_season_stat",
    "fixture", "fixture_detail", "standings", "app_user",
    "transfer", "injury", "news_article",
    "h2h_fixture",
}


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _insert_team(conn, *, external_id, slug=None):
    return conn.execute(
        text(
            "INSERT INTO team (external_id, name, slug) "
            "VALUES (:e, :n, :s) RETURNING id"
        ),
        {"e": external_id, "n": f"T{external_id}", "s": slug or f"team-{external_id}"},
    ).scalar()


def _insert_h2h(conn, *, external_id, home_id, away_id, kickoff="2024-08-01T15:00:00Z",
                 league_external_id=None, league_name="Friendlies", season_year=None,
                 status_short="FT", gh=1, ga=0):
    return conn.execute(
        text(
            "INSERT INTO h2h_fixture "
            "(external_id, home_team_id, away_team_id, league_external_id, "
            " league_name, season_year, kickoff_at, status_short, goals_home, goals_away) "
            "VALUES (:e, :h, :a, :le, :ln, :sy, :k, :st, :gh, :ga) RETURNING id"
        ),
        {"e": external_id, "h": home_id, "a": away_id, "le": league_external_id,
         "ln": league_name, "sy": season_year, "k": kickoff, "st": status_short,
         "gh": gh, "ga": ga},
    ).scalar()


# ---------------------------------------------------------------------------
# L3I-01 17 테이블
# ---------------------------------------------------------------------------

def test_l3i01_17_tables(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows} - {"alembic_version"}
    assert names == EXPECTED_17, f"missing/extra: {names ^ EXPECTED_17}"


# ---------------------------------------------------------------------------
# L3I-02 함수 인덱스 정의 확인
# ---------------------------------------------------------------------------

def test_l3i02_h2h_pair_idx_is_functional_least_greatest(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        indexdef = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=:s AND indexname='h2h_pair_idx'"
            ),
            {"s": schema},
        ).scalar()
    assert indexdef is not None, "h2h_pair_idx 인덱스 생성되지 않음"
    iu = indexdef.upper()
    assert "LEAST(" in iu, f"LEAST 함수 누락: {indexdef!r}"
    assert "GREATEST(" in iu, f"GREATEST 함수 누락: {indexdef!r}"
    assert "KICKOFF_AT" in iu, f"kickoff_at 누락: {indexdef!r}"
    assert "DESC" in iu, f"DESC 정렬 누락: {indexdef!r}"


# ---------------------------------------------------------------------------
# L3I-03 external_id UNIQUE
# ---------------------------------------------------------------------------

def test_l3i03_external_id_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        a = _insert_team(conn, external_id=33)
        b = _insert_team(conn, external_id=50)
        _insert_h2h(conn, external_id=7001, home_id=a, away_id=b)
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                # 다른 시간/팀이지만 같은 external_id
                a2 = conn.execute(text("SELECT id FROM team WHERE external_id=33")).scalar()
                b2 = conn.execute(text("SELECT id FROM team WHERE external_id=50")).scalar()
                _insert_h2h(conn, external_id=7001, home_id=a2, away_id=b2,
                            kickoff="2025-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# L3I-04 home / away NOT NULL
# ---------------------------------------------------------------------------

def test_l3i04_home_away_not_null(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        a = _insert_team(conn, external_id=33)
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO h2h_fixture (external_id, home_team_id, away_team_id, kickoff_at) "
                        "VALUES (7002, :h, NULL, now())"
                    ),
                    {"h": a},
                )


# ---------------------------------------------------------------------------
# L3I-05 league_external_id NULL 허용
# ---------------------------------------------------------------------------

def test_l3i05_league_external_id_null_allowed(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        a = _insert_team(conn, external_id=33)
        b = _insert_team(conn, external_id=50)
        _insert_h2h(
            conn, external_id=7003, home_id=a, away_id=b,
            league_external_id=None, league_name="Friendlies",
        )
        row = conn.execute(
            text("SELECT league_external_id, league_name FROM h2h_fixture WHERE external_id=7003")
        ).first()
    assert row.league_external_id is None
    assert row.league_name == "Friendlies"


# ---------------------------------------------------------------------------
# L3I-06 FK CASCADE
# ---------------------------------------------------------------------------

def test_l3i06_fk_cascade_on_team_delete(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        a = _insert_team(conn, external_id=33)
        b = _insert_team(conn, external_id=50)
        _insert_h2h(conn, external_id=7004, home_id=a, away_id=b)
        # home team 삭제 → h2h row 사라짐
        conn.execute(text("DELETE FROM team WHERE id=:t"), {"t": a})
        cnt = conn.execute(text("SELECT COUNT(*) FROM h2h_fixture WHERE external_id=7004")).scalar()
    assert cnt == 0


# ---------------------------------------------------------------------------
# L3I-07 함수 인덱스 — 순서 무관 H2H 쿼리
# ---------------------------------------------------------------------------

def test_l3i07_query_pair_order_insensitive(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        a = _insert_team(conn, external_id=33)
        b = _insert_team(conn, external_id=50)
        c = _insert_team(conn, external_id=100)
        # (a,b) 와 (b,a) 두 row + (a,c) 하나 (방해 데이터)
        _insert_h2h(conn, external_id=8001, home_id=a, away_id=b, kickoff="2024-01-01T00:00:00Z")
        _insert_h2h(conn, external_id=8002, home_id=b, away_id=a, kickoff="2024-06-01T00:00:00Z")
        _insert_h2h(conn, external_id=8003, home_id=a, away_id=c, kickoff="2024-03-01T00:00:00Z")

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT external_id FROM h2h_fixture "
                "WHERE LEAST(home_team_id, away_team_id)    = LEAST(:x, :y) "
                "  AND GREATEST(home_team_id, away_team_id) = GREATEST(:x, :y) "
                "ORDER BY kickoff_at DESC LIMIT 5"
            ),
            {"x": a, "y": b},
        ).all()
    ext_ids = [r[0] for r in rows]
    # (a,b) 와 (b,a) 두 row 모두 반환되고, (a,c) 는 제외, kickoff_at DESC 정렬
    assert ext_ids == [8002, 8001], f"순서 무관 H2H 쿼리 실패 (got {ext_ids})"


# ---------------------------------------------------------------------------
# L3I-08 downgrade -1
# ---------------------------------------------------------------------------

def test_l3i08_downgrade_drops_h2h_only(migrated_db, test_database_url):
    engine, schema = migrated_db
    result = _run_alembic(["downgrade", "-1"], schema=schema, db_url=test_database_url)
    assert result.returncode == 0, f"downgrade -1 failed:\n{result.stdout}\n{result.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema=:s"),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows} - {"alembic_version"}
    assert "h2h_fixture" not in names, "h2h_fixture 가 downgrade 후에도 남음"
    # 다른 16 테이블 모두 유지
    expected_16 = EXPECTED_17 - {"h2h_fixture"}
    assert expected_16 <= names, f"기존 16 테이블 누락: {expected_16 - names}"


# ---------------------------------------------------------------------------
# L3I-09 reversibility
# ---------------------------------------------------------------------------

def test_l3i09_reversibility_base_to_head(migrated_db, test_database_url):
    engine, schema = migrated_db
    r1 = _run_alembic(["downgrade", "base"], schema=schema, db_url=test_database_url)
    assert r1.returncode == 0, f"downgrade base failed: {r1.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema=:s"),
            {"s": schema},
        ).all()
    remaining = {r[0] for r in rows} - {"alembic_version"}
    assert remaining == set(), f"base 후에도 남음: {remaining}"

    r2 = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    assert r2.returncode == 0, f"upgrade head 2nd failed: {r2.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema=:s"),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows} - {"alembic_version"}
    assert names == EXPECTED_17

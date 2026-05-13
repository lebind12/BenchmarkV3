"""L2 — transfer / injury / news_article 통합 테스트.

격리 schema 에 alembic upgrade head (0001 + 0002 + 0003) 적용 후 검증.
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


EXPECTED_16 = {
    "league", "league_translation", "venue", "team", "team_translation",
    "team_season", "player", "player_translation", "player_season_stat",
    "fixture", "fixture_detail", "standings", "app_user",
    "transfer", "injury", "news_article",
}

EXPECTED_NEW_INDEXES = {
    "transfer_player_idx",
    "transfer_date_idx",
    "transfer_to_team_idx",
    "transfer_from_team_idx",
    "injury_player_idx",
    "injury_team_season_idx",
    "injury_fixture_idx",
    "news_article_published_idx",
    "news_article_pending_idx",
    "news_article_tags_gin",
}


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _insert_league(conn, *, external_id=39, slug="premier-league"):
    return conn.execute(
        text(
            "INSERT INTO league (external_id, name, type, slug, current_season) "
            "VALUES (:e, 'Premier League', 'League', :s, 2024) RETURNING id"
        ),
        {"e": external_id, "s": slug},
    ).scalar()


def _insert_team(conn, *, external_id, name="Team", slug=None):
    return conn.execute(
        text(
            "INSERT INTO team (external_id, name, slug) "
            "VALUES (:e, :n, :s) RETURNING id"
        ),
        {"e": external_id, "n": name, "s": slug or f"team-{external_id}"},
    ).scalar()


def _insert_player(conn, *, external_id=1001, team_id=None):
    return conn.execute(
        text(
            "INSERT INTO player (external_id, name, slug, current_team_id) "
            "VALUES (:e, :n, :s, :t) RETURNING id"
        ),
        {"e": external_id, "n": f"P{external_id}", "s": f"player-{external_id}", "t": team_id},
    ).scalar()


def _insert_fixture(conn, *, external_id=2001, league_id, season_year=2024):
    return conn.execute(
        text(
            "INSERT INTO fixture (external_id, league_id, season_year, kickoff_at, status_short) "
            "VALUES (:e, :l, :y, now(), 'NS') RETURNING id"
        ),
        {"e": external_id, "l": league_id, "y": season_year},
    ).scalar()


# ---------------------------------------------------------------------------
# L2I-01 / L2I-02
# ---------------------------------------------------------------------------

def test_l2i01_16_tables_present(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows} - {"alembic_version"}
    assert names == EXPECTED_16, f"missing/extra: {names ^ EXPECTED_16}"


def test_l2i02_new_indexes_exist(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname=:s"),
            {"s": schema},
        ).all()
    found = {r[0] for r in rows}
    missing = EXPECTED_NEW_INDEXES - found
    assert not missing, f"누락된 인덱스: {missing}"


# ---------------------------------------------------------------------------
# L2I-03 / L2I-04 transfer FK + NULL 허용
# ---------------------------------------------------------------------------

def test_l2i03_transfer_insert_with_fk(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        t1 = _insert_team(conn, external_id=33)
        t2 = _insert_team(conn, external_id=50)
        pid = _insert_player(conn, external_id=1001, team_id=t2)
        conn.execute(
            text(
                "INSERT INTO transfer (player_id, transfer_date, type, from_team_id, to_team_id) "
                "VALUES (:p, '2024-08-01', 'Permanent', :f, :t)"
            ),
            {"p": pid, "f": t1, "t": t2},
        )
        cnt = conn.execute(text("SELECT COUNT(*) FROM transfer")).scalar()
        assert cnt == 1


def test_l2i04_transfer_null_from_team_allowed(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        t = _insert_team(conn, external_id=33)
        pid = _insert_player(conn, external_id=1001, team_id=t)
        conn.execute(
            text(
                "INSERT INTO transfer (player_id, transfer_date, type, from_team_id, to_team_id) "
                "VALUES (:p, '2023-01-01', 'Free', NULL, :t)"
            ),
            {"p": pid, "t": t},
        )
        row = conn.execute(
            text("SELECT from_team_id FROM transfer WHERE player_id=:p"), {"p": pid}
        ).first()
    assert row.from_team_id is None


# ---------------------------------------------------------------------------
# L2I-05 transfer_uniq 동일 4-tuple
# ---------------------------------------------------------------------------

def test_l2i05_transfer_uniq_blocks_exact_duplicate(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        t1 = _insert_team(conn, external_id=33)
        t2 = _insert_team(conn, external_id=50)
        pid = _insert_player(conn, external_id=1001, team_id=t2)
        conn.execute(
            text(
                "INSERT INTO transfer (player_id, transfer_date, from_team_id, to_team_id) "
                "VALUES (:p, '2024-08-01', :f, :t)"
            ),
            {"p": pid, "f": t1, "t": t2},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO transfer (player_id, transfer_date, from_team_id, to_team_id) "
                        "VALUES (:p, '2024-08-01', :f, :t)"
                    ),
                    {"p": pid, "f": t1, "t": t2},
                )


# ---------------------------------------------------------------------------
# L2I-06 / L2I-07 transfer ON DELETE
# ---------------------------------------------------------------------------

def test_l2i06_transfer_cascade_on_player_delete(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        t1 = _insert_team(conn, external_id=33)
        t2 = _insert_team(conn, external_id=50)
        pid = _insert_player(conn, external_id=1001)
        conn.execute(
            text(
                "INSERT INTO transfer (player_id, transfer_date, from_team_id, to_team_id) "
                "VALUES (:p, '2024-08-01', :f, :t)"
            ),
            {"p": pid, "f": t1, "t": t2},
        )
        conn.execute(text("DELETE FROM player WHERE id=:p"), {"p": pid})
        cnt = conn.execute(text("SELECT COUNT(*) FROM transfer")).scalar()
    assert cnt == 0


def test_l2i07_transfer_set_null_on_team_delete(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        t1 = _insert_team(conn, external_id=33)
        t2 = _insert_team(conn, external_id=50)
        pid = _insert_player(conn, external_id=1001)
        conn.execute(
            text(
                "INSERT INTO transfer (player_id, transfer_date, from_team_id, to_team_id) "
                "VALUES (:p, '2024-08-01', :f, :t)"
            ),
            {"p": pid, "f": t1, "t": t2},
        )
        conn.execute(text("DELETE FROM team WHERE id=:t"), {"t": t1})
        row = conn.execute(
            text("SELECT from_team_id, to_team_id FROM transfer WHERE player_id=:p"),
            {"p": pid},
        ).first()
    assert row.from_team_id is None
    assert row.to_team_id == t2


# ---------------------------------------------------------------------------
# L2I-08 / L2I-09 injury UNIQUE + NULL fixture_id
# ---------------------------------------------------------------------------

def test_l2i08_injury_uniq_blocks_dup(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn, external_id=33)
        pid = _insert_player(conn, external_id=1001, team_id=tid)
        fid = _insert_fixture(conn, external_id=2001, league_id=lid)
        conn.execute(
            text(
                "INSERT INTO injury (player_id, fixture_id, team_id, league_id, season_year) "
                "VALUES (:p, :f, :t, :l, 2024)"
            ),
            {"p": pid, "f": fid, "t": tid, "l": lid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO injury (player_id, fixture_id, team_id, league_id, season_year) "
                        "VALUES (:p, :f, :t, :l, 2024)"
                    ),
                    {"p": pid, "f": fid, "t": tid, "l": lid},
                )


def test_l2i09_injury_fixture_id_null_allowed(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn, external_id=33)
        pid = _insert_player(conn, external_id=1001, team_id=tid)
        conn.execute(
            text(
                "INSERT INTO injury (player_id, fixture_id, team_id, league_id, season_year) "
                "VALUES (:p, NULL, :t, :l, 2024)"
            ),
            {"p": pid, "t": tid, "l": lid},
        )
        cnt = conn.execute(text("SELECT COUNT(*) FROM injury")).scalar()
    assert cnt == 1


# ---------------------------------------------------------------------------
# L2I-10 injury partial index
# ---------------------------------------------------------------------------

def test_l2i10_injury_fixture_idx_is_partial(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        indexdef = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=:s AND indexname='injury_fixture_idx'"
            ),
            {"s": schema},
        ).scalar()
    assert indexdef is not None
    assert "WHERE" in indexdef.upper()
    assert "fixture_id" in indexdef.lower()
    assert "not null" in indexdef.lower()


# ---------------------------------------------------------------------------
# L2I-11 injury ON DELETE
# ---------------------------------------------------------------------------

def test_l2i11_injury_on_delete(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn, external_id=33)
        pid = _insert_player(conn, external_id=1001, team_id=tid)
        fid = _insert_fixture(conn, external_id=2001, league_id=lid)
        conn.execute(
            text(
                "INSERT INTO injury (player_id, fixture_id, team_id, league_id, season_year) "
                "VALUES (:p, :f, :t, :l, 2024)"
            ),
            {"p": pid, "f": fid, "t": tid, "l": lid},
        )

        # fixture 삭제 → injury.fixture_id NULL
        conn.execute(text("DELETE FROM fixture WHERE id=:f"), {"f": fid})
        nf = conn.execute(
            text("SELECT fixture_id FROM injury WHERE player_id=:p"), {"p": pid}
        ).scalar()
        assert nf is None

        # team 삭제 → injury row 사라짐 (CASCADE)
        conn.execute(text("DELETE FROM team WHERE id=:t"), {"t": tid})
        cnt = conn.execute(text("SELECT COUNT(*) FROM injury")).scalar()
        assert cnt == 0


# ---------------------------------------------------------------------------
# L2I-12 news_article.source_url UNIQUE
# ---------------------------------------------------------------------------

def test_l2i12_news_article_source_url_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO news_article (source, source_url, original_title, published_at) "
                "VALUES ('BBC', 'https://bbc/1', 'T', now())"
            )
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO news_article (source, source_url, original_title, published_at) "
                        "VALUES ('Guardian', 'https://bbc/1', 'T2', now())"
                    )
                )


# ---------------------------------------------------------------------------
# L2I-13 GIN tags JSONB
# ---------------------------------------------------------------------------

def test_l2i13_news_article_tags_jsonb_containment(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO news_article "
                "(source, source_url, original_title, published_at, tags) "
                "VALUES ('BBC', 'https://bbc/2', 'T', now(), '{\"teams\":[33]}'::jsonb)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO news_article "
                "(source, source_url, original_title, published_at, tags) "
                "VALUES ('BBC', 'https://bbc/3', 'U', now(), '{\"teams\":[50]}'::jsonb)"
            )
        )
        cnt = conn.execute(
            text("SELECT COUNT(*) FROM news_article WHERE tags @> '{\"teams\":[33]}'::jsonb")
        ).scalar()
    assert cnt == 1


# ---------------------------------------------------------------------------
# L2I-14 news_article partial index
# ---------------------------------------------------------------------------

def test_l2i14_news_article_pending_idx_is_partial(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        indexdef = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=:s AND indexname='news_article_pending_idx'"
            ),
            {"s": schema},
        ).scalar()
    assert indexdef is not None
    assert "WHERE" in indexdef.upper()
    assert "title_ko" in indexdef.lower()


# ---------------------------------------------------------------------------
# L2I-15 downgrade -1
# ---------------------------------------------------------------------------

def test_l2i15_downgrade_drops_three_tables_keeps_others(migrated_db, test_database_url):
    engine, schema = migrated_db
    result = _run_alembic(["downgrade", "-1"], schema=schema, db_url=test_database_url)
    assert result.returncode == 0, f"downgrade -1 failed:\n{result.stdout}\n{result.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
        names = {r[0] for r in rows} - {"alembic_version"}
        # 3 신규 테이블 사라지고 13 유지
        for tbl in ("transfer", "injury", "news_article"):
            assert tbl not in names, f"{tbl} 가 downgrade 후에도 남아 있음"
        # league.is_active 컬럼은 0002 적용 상태로 여전히 존재
        has_is_active = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=:s AND table_name='league' AND column_name='is_active'"
            ),
            {"s": schema},
        ).scalar()
        assert has_is_active == 1


# ---------------------------------------------------------------------------
# L2I-16 reversibility (downgrade base → upgrade head)
# ---------------------------------------------------------------------------

def test_l2i16_reversibility_base_to_head(migrated_db, test_database_url):
    engine, schema = migrated_db
    # base 까지 내림
    r1 = _run_alembic(["downgrade", "base"], schema=schema, db_url=test_database_url)
    assert r1.returncode == 0, f"downgrade base failed: {r1.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
    remaining = {r[0] for r in rows} - {"alembic_version"}
    assert remaining == set(), f"downgrade base 후에도 테이블 남음: {remaining}"

    # 다시 head 까지 올림
    r2 = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    assert r2.returncode == 0, f"upgrade head (2nd) failed: {r2.stderr}"
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows} - {"alembic_version"}
    assert names == EXPECTED_16

"""Phase 1 — DB 스키마 통합 테스트.

격리 schema (`test_<run_id>_<endpoint>`) 안에 alembic `upgrade head` 를 적용한 뒤
13 테이블 / 인덱스 / CHECK / UNIQUE / FK action / NULL 정책 / downgrade 까지 검증.

전제 환경변수:
- `TEST_DATABASE_URL` — Postgres URL (없으면 conftest 가 skip 처리)

이 테스트는 be-dev 가 모델 + 마이그레이션을 작성하기 전까지 fail 한다 (TDD Red 정상).
"""

from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "league",
    "league_translation",
    "venue",
    "team",
    "team_translation",
    "team_season",
    "player",
    "player_translation",
    "player_season_stat",
    "fixture",
    "fixture_detail",
    "standings",
    "app_user",
}

EXPECTED_INDEXES = {
    "league_type_idx",
    "team_country_idx",
    "team_venue_idx",
    "team_season_league_year_idx",
    "player_team_idx",
    "player_nationality_idx",
    "player_season_stat_player_idx",
    "player_season_stat_team_year_idx",
    "player_season_stat_topscorer_idx",
    "fixture_league_season_idx",
    "fixture_kickoff_idx",
    "fixture_status_idx",
    "fixture_home_team_idx",
    "fixture_away_team_idx",
    "standings_uniq",
    "standings_league_season_rank_idx",
    "app_user_role_idx",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_alembic(args: list[str], schema: str, db_url: str) -> subprocess.CompletedProcess:
    """alembic 을 격리 schema 의 search_path 로 실행.

    search_path 는 libpq 의 `PGOPTIONS` 환경변수로 전달한다 (URL 에 `%` 가 들어가면
    alembic 의 configparser 가 interpolation 으로 해석해서 깨지기 때문).
    psycopg2 와 psycopg v3 모두 PGOPTIONS 를 자동으로 적용한다.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    # 기존 PGOPTIONS 가 있으면 보존하면서 search_path 추가
    existing = env.get("PGOPTIONS", "")
    env["PGOPTIONS"] = f"-c search_path={schema} {existing}".strip()
    # 현재 pytest 가 사용하는 Python 인터프리터의 alembic 모듈을 직접 호출한다.
    # PATH 상 `alembic` 바이너리가 다른 Python (예: anaconda) 의 것이라
    # psycopg 가 없는 경우가 있어 ModuleNotFoundError 가 발생하기 때문.
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
    """격리 schema 에 alembic upgrade head 적용 후 (engine, schema_name) 반환."""
    engine, schema = isolated_db
    result = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head 실패 (schema={schema})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return engine, schema


# ---------------------------------------------------------------------------
# I-01 13 테이블 생성
# ---------------------------------------------------------------------------

def test_i01_all_13_tables_created(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :s"
            ),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows}
    # alembic_version 은 alembic 이 만드는 메타 테이블이라 제외
    names.discard("alembic_version")
    assert names == EXPECTED_TABLES, f"missing/extra tables: {names ^ EXPECTED_TABLES}"


# ---------------------------------------------------------------------------
# I-02 인덱스 일람
# ---------------------------------------------------------------------------

def test_i02_all_expected_indexes_exist(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = :s"
            ),
            {"s": schema},
        ).all()
    found = {r[0] for r in rows}
    missing = EXPECTED_INDEXES - found
    assert not missing, f"누락된 인덱스: {missing}"


# ---------------------------------------------------------------------------
# 헬퍼: 최소 row 만들기
# ---------------------------------------------------------------------------

def _insert_league(conn, *, external_id=39, name="Premier League", type_="League", slug="premier-league"):
    return conn.execute(
        text(
            "INSERT INTO league (external_id, name, type, slug) "
            "VALUES (:e, :n, :t, :s) RETURNING id"
        ),
        {"e": external_id, "n": name, "t": type_, "s": slug},
    ).scalar()


def _insert_venue(conn, *, external_id=None, name="Old Trafford"):
    return conn.execute(
        text("INSERT INTO venue (external_id, name) VALUES (:e, :n) RETURNING id"),
        {"e": external_id, "n": name},
    ).scalar()


def _insert_team(conn, *, external_id=33, name="Manchester United", slug=None, venue_id=None):
    return conn.execute(
        text(
            "INSERT INTO team (external_id, name, slug, venue_id) "
            "VALUES (:e, :n, :s, :v) RETURNING id"
        ),
        {"e": external_id, "n": name, "s": slug or f"team-{external_id}", "v": venue_id},
    ).scalar()


def _insert_player(conn, *, external_id=1001, name="Bruno Fernandes", slug=None, team_id=None):
    return conn.execute(
        text(
            "INSERT INTO player (external_id, name, slug, current_team_id) "
            "VALUES (:e, :n, :s, :t) RETURNING id"
        ),
        {"e": external_id, "n": name, "s": slug or f"player-{external_id}", "t": team_id},
    ).scalar()


# ---------------------------------------------------------------------------
# I-03 league.type CHECK
# ---------------------------------------------------------------------------

def test_i03_league_type_check_rejects_invalid(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO league (external_id, name, type, slug) "
                        "VALUES (1, 'X', 'Invalid', 'x')"
                    )
                )


# ---------------------------------------------------------------------------
# I-04 app_user.role CHECK + default USER
# ---------------------------------------------------------------------------

def test_i04_app_user_role_check_and_default(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_user (email, password_hash) "
                "VALUES ('a@b.com', 'hash')"
            )
        )
        role = conn.execute(
            text("SELECT role FROM app_user WHERE email='a@b.com'")
        ).scalar()
        assert role == "USER"

    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO app_user (email, password_hash, role) "
                        "VALUES ('c@d.com', 'h', 'SUPER')"
                    )
                )


# ---------------------------------------------------------------------------
# I-05 ~ I-10 UNIQUE
# ---------------------------------------------------------------------------

def test_i05_league_external_id_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_league(conn, external_id=39, slug="pl-1")
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_league(conn, external_id=39, slug="pl-2")


def test_i06_team_external_id_and_slug_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_team(conn, external_id=33, slug="team-33")
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_team(conn, external_id=33, slug="team-33-dup")
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_team(conn, external_id=34, slug="team-33")


def test_i07_player_external_id_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_player(conn, external_id=1001)
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_player(conn, external_id=1001, slug="player-dup")


def test_i08_fixture_external_id_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        league_id = _insert_league(conn)
        conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "kickoff_at, status_short) "
                "VALUES (1, :l, 2024, now(), 'NS')"
            ),
            {"l": league_id},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO fixture (external_id, league_id, season_year, "
                        "kickoff_at, status_short) "
                        "VALUES (1, :l, 2024, now(), 'NS')"
                    ),
                    {"l": league_id},
                )


def test_i09_venue_external_id_nullable_allows_multiple_nulls(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_venue(conn, external_id=None, name="V1")
        _insert_venue(conn, external_id=None, name="V2")
        # 둘 다 성공해야 함 (PG 기본: NULL 들은 UNIQUE 충돌 안 함)
        cnt = conn.execute(text("SELECT COUNT(*) FROM venue")).scalar()
        assert cnt == 2


def test_i10_app_user_email_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_user (email, password_hash) VALUES ('a@b.com', 'h')"
            )
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO app_user (email, password_hash) "
                        "VALUES ('a@b.com', 'h2')"
                    )
                )


# ---------------------------------------------------------------------------
# I-11 ~ I-13 translation 1:1
# ---------------------------------------------------------------------------

def test_i11_league_translation_pk_enforces_1to1(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        conn.execute(
            text("INSERT INTO league_translation (league_id, name_ko) VALUES (:l, '프리미어 리그')"),
            {"l": lid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO league_translation (league_id, name_ko) "
                        "VALUES (:l, '다른 이름')"
                    ),
                    {"l": lid},
                )


def test_i12_team_translation_pk_enforces_1to1(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        tid = _insert_team(conn)
        conn.execute(
            text("INSERT INTO team_translation (team_id, name_ko) VALUES (:t, '맨유')"),
            {"t": tid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO team_translation (team_id, name_ko) "
                        "VALUES (:t, '맨체스터')"
                    ),
                    {"t": tid},
                )


def test_i13_player_translation_pk_enforces_1to1(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        pid = _insert_player(conn)
        conn.execute(
            text("INSERT INTO player_translation (player_id, name_ko) VALUES (:p, '브루누')"),
            {"p": pid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO player_translation (player_id, name_ko) "
                        "VALUES (:p, '페르난데스')"
                    ),
                    {"p": pid},
                )


# ---------------------------------------------------------------------------
# I-14 team_season composite PK
# ---------------------------------------------------------------------------

def test_i14_team_season_composite_pk(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        conn.execute(
            text(
                "INSERT INTO team_season (team_id, league_id, season_year) "
                "VALUES (:t, :l, 2024)"
            ),
            {"t": tid, "l": lid},
        )
        # 다른 season 은 OK
        conn.execute(
            text(
                "INSERT INTO team_season (team_id, league_id, season_year) "
                "VALUES (:t, :l, 2025)"
            ),
            {"t": tid, "l": lid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO team_season (team_id, league_id, season_year) "
                        "VALUES (:t, :l, 2024)"
                    ),
                    {"t": tid, "l": lid},
                )


# ---------------------------------------------------------------------------
# I-15 player_season_stat UNIQUE(4-tuple)
# ---------------------------------------------------------------------------

def test_i15_player_season_stat_unique(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        pid = _insert_player(conn, team_id=tid)
        conn.execute(
            text(
                "INSERT INTO player_season_stat "
                "(player_id, team_id, league_id, season_year, raw_stats) "
                "VALUES (:p, :t, :l, 2024, '{}'::jsonb)"
            ),
            {"p": pid, "t": tid, "l": lid},
        )
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO player_season_stat "
                        "(player_id, team_id, league_id, season_year, raw_stats) "
                        "VALUES (:p, :t, :l, 2024, '{}'::jsonb)"
                    ),
                    {"p": pid, "t": tid, "l": lid},
                )


# ---------------------------------------------------------------------------
# I-16 standings UNIQUE w/ COALESCE
# ---------------------------------------------------------------------------

def _insert_standing(conn, *, league_id, team_id, season_year=2024, group_name=None, rank=1):
    return conn.execute(
        text(
            "INSERT INTO standings "
            "(league_id, season_year, team_id, group_name, rank, points, "
            " played, win, draw, loss, goals_for, goals_against) "
            "VALUES (:l, :y, :t, :g, :r, 0, 0, 0, 0, 0, 0, 0)"
        ),
        {"l": league_id, "y": season_year, "t": team_id, "g": group_name, "r": rank},
    )


def test_i16_standings_unique_with_coalesce(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        # (l, y, t, NULL) 1번 OK
        _insert_standing(conn, league_id=lid, team_id=tid, group_name=None, rank=1)
    # 같은 (l, y, t, NULL) 두 번째 → COALESCE 로 충돌해야 함
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_standing(conn, league_id=lid, team_id=tid, group_name=None, rank=2)

    # 새 team 으로 group_name 다르게 → 둘 다 OK
    with engine.begin() as conn:
        tid2 = _insert_team(conn, external_id=34, slug="team-34")
        _insert_standing(conn, league_id=lid, team_id=tid2, group_name="Group A", rank=1)
        _insert_standing(conn, league_id=lid, team_id=tid2, group_name="Group B", rank=1)

    # 같은 (l, y, t, 'Group A') → 충돌
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                _insert_standing(conn, league_id=lid, team_id=tid2, group_name="Group A", rank=2)


# ---------------------------------------------------------------------------
# I-17 ~ I-23 ON DELETE 정책
# ---------------------------------------------------------------------------

def test_i17_cascade_league_to_translation(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        conn.execute(
            text("INSERT INTO league_translation (league_id, name_ko) VALUES (:l, 'X')"),
            {"l": lid},
        )
        assert conn.execute(
            text("SELECT COUNT(*) FROM league_translation WHERE league_id=:l"),
            {"l": lid},
        ).scalar() == 1
        conn.execute(text("DELETE FROM league WHERE id=:l"), {"l": lid})
        assert conn.execute(
            text("SELECT COUNT(*) FROM league_translation WHERE league_id=:l"),
            {"l": lid},
        ).scalar() == 0


def test_i18_cascade_team_to_dependents(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        conn.execute(
            text("INSERT INTO team_translation (team_id, name_ko) VALUES (:t, 'X')"),
            {"t": tid},
        )
        conn.execute(
            text(
                "INSERT INTO team_season (team_id, league_id, season_year) "
                "VALUES (:t, :l, 2024)"
            ),
            {"t": tid, "l": lid},
        )
        pid = _insert_player(conn, team_id=tid)
        conn.execute(
            text(
                "INSERT INTO player_season_stat "
                "(player_id, team_id, league_id, season_year, raw_stats) "
                "VALUES (:p, :t, :l, 2024, '{}'::jsonb)"
            ),
            {"p": pid, "t": tid, "l": lid},
        )
        _insert_standing(conn, league_id=lid, team_id=tid)

        conn.execute(text("DELETE FROM team WHERE id=:t"), {"t": tid})

        for q in (
            "SELECT COUNT(*) FROM team_translation WHERE team_id=:t",
            "SELECT COUNT(*) FROM team_season WHERE team_id=:t",
            "SELECT COUNT(*) FROM player_season_stat WHERE team_id=:t",
            "SELECT COUNT(*) FROM standings WHERE team_id=:t",
        ):
            assert conn.execute(text(q), {"t": tid}).scalar() == 0, q


def test_i19_cascade_player_to_dependents(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        pid = _insert_player(conn, team_id=tid)
        conn.execute(
            text("INSERT INTO player_translation (player_id, name_ko) VALUES (:p, 'X')"),
            {"p": pid},
        )
        conn.execute(
            text(
                "INSERT INTO player_season_stat "
                "(player_id, team_id, league_id, season_year, raw_stats) "
                "VALUES (:p, :t, :l, 2024, '{}'::jsonb)"
            ),
            {"p": pid, "t": tid, "l": lid},
        )
        conn.execute(text("DELETE FROM player WHERE id=:p"), {"p": pid})
        assert conn.execute(
            text("SELECT COUNT(*) FROM player_translation WHERE player_id=:p"),
            {"p": pid},
        ).scalar() == 0
        assert conn.execute(
            text("SELECT COUNT(*) FROM player_season_stat WHERE player_id=:p"),
            {"p": pid},
        ).scalar() == 0


def test_i20_cascade_fixture_to_detail(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        fid = conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "kickoff_at, status_short) "
                "VALUES (1, :l, 2024, now(), 'NS') RETURNING id"
            ),
            {"l": lid},
        ).scalar()
        conn.execute(
            text("INSERT INTO fixture_detail (fixture_id) VALUES (:f)"),
            {"f": fid},
        )
        conn.execute(text("DELETE FROM fixture WHERE id=:f"), {"f": fid})
        assert conn.execute(
            text("SELECT COUNT(*) FROM fixture_detail WHERE fixture_id=:f"),
            {"f": fid},
        ).scalar() == 0


def test_i21_cascade_league_to_fixture(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "kickoff_at, status_short) VALUES (1, :l, 2024, now(), 'NS')"
            ),
            {"l": lid},
        )
        conn.execute(text("DELETE FROM league WHERE id=:l"), {"l": lid})
        assert conn.execute(
            text("SELECT COUNT(*) FROM fixture WHERE league_id=:l"),
            {"l": lid},
        ).scalar() == 0


def test_i22_set_null_venue(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        vid = _insert_venue(conn, external_id=100)
        tid = _insert_team(conn, venue_id=vid)
        lid = _insert_league(conn)
        fid = conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "kickoff_at, status_short, venue_id) "
                "VALUES (1, :l, 2024, now(), 'NS', :v) RETURNING id"
            ),
            {"l": lid, "v": vid},
        ).scalar()
        conn.execute(text("DELETE FROM venue WHERE id=:v"), {"v": vid})

        # team / fixture 자체는 살아있고 venue_id 가 NULL 이어야 함
        team_venue = conn.execute(
            text("SELECT venue_id FROM team WHERE id=:t"), {"t": tid}
        ).scalar()
        fixture_venue = conn.execute(
            text("SELECT venue_id FROM fixture WHERE id=:f"), {"f": fid}
        ).scalar()
        assert team_venue is None
        assert fixture_venue is None


def test_i23_set_null_team(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        pid = _insert_player(conn, team_id=tid)
        fid = conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "kickoff_at, status_short, home_team_id, away_team_id) "
                "VALUES (1, :l, 2024, now(), 'NS', :t, :t) RETURNING id"
            ),
            {"l": lid, "t": tid},
        ).scalar()
        conn.execute(text("DELETE FROM team WHERE id=:t"), {"t": tid})

        # player 자체는 살아있고 current_team_id 가 NULL
        assert conn.execute(
            text("SELECT current_team_id FROM player WHERE id=:p"), {"p": pid}
        ).scalar() is None
        # fixture 자체는 살아있고 home/away team NULL
        row = conn.execute(
            text("SELECT home_team_id, away_team_id FROM fixture WHERE id=:f"),
            {"f": fid},
        ).first()
        assert row.home_team_id is None
        assert row.away_team_id is None


# ---------------------------------------------------------------------------
# I-24 fixture team NULL 허용 (컵 추첨 미정)
# ---------------------------------------------------------------------------

def test_i24_fixture_home_away_nullable_for_cup_draw(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn, external_id=45, name="FA Cup", type_="Cup", slug="fa-cup")
        fid = conn.execute(
            text(
                "INSERT INTO fixture (external_id, league_id, season_year, "
                "round, kickoff_at, status_short) "
                "VALUES (9001, :l, 2024, 'Round of 16 - TBD', now(), 'TBD') RETURNING id"
            ),
            {"l": lid},
        ).scalar()
        row = conn.execute(
            text(
                "SELECT home_team_id, away_team_id FROM fixture WHERE id=:f"
            ),
            {"f": fid},
        ).first()
        assert row.home_team_id is None
        assert row.away_team_id is None


# ---------------------------------------------------------------------------
# I-25 translation name_ko NULL INSERT 가능
# ---------------------------------------------------------------------------

def test_i25_translation_null_name_ko_inserts(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        conn.execute(
            text("INSERT INTO league_translation (league_id) VALUES (:l)"),
            {"l": lid},
        )
        nk = conn.execute(
            text("SELECT name_ko FROM league_translation WHERE league_id=:l"),
            {"l": lid},
        ).scalar()
        assert nk is None


# ---------------------------------------------------------------------------
# I-26 created_at / updated_at server default
# ---------------------------------------------------------------------------

def test_i26_timestamps_auto_filled(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        row = conn.execute(
            text("SELECT created_at, updated_at FROM league WHERE id=:l"),
            {"l": lid},
        ).first()
        assert row.created_at is not None
        assert row.updated_at is not None


# ---------------------------------------------------------------------------
# I-27 Numeric(4,2) 정밀도
# ---------------------------------------------------------------------------

def test_i27_player_rating_numeric_precision(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        tid = _insert_team(conn)
        pid = _insert_player(conn, team_id=tid)
        conn.execute(
            text(
                "INSERT INTO player_season_stat "
                "(player_id, team_id, league_id, season_year, rating, raw_stats) "
                "VALUES (:p, :t, :l, 2024, 7.13, '{}'::jsonb)"
            ),
            {"p": pid, "t": tid, "l": lid},
        )
        val = conn.execute(
            text(
                "SELECT rating FROM player_season_stat "
                "WHERE player_id=:p AND team_id=:t AND league_id=:l AND season_year=2024"
            ),
            {"p": pid, "t": tid, "l": lid},
        ).scalar()
        assert val == Decimal("7.13")


# ---------------------------------------------------------------------------
# I-28 downgrade
# ---------------------------------------------------------------------------

def test_i28_downgrade_drops_all_tables(migrated_db, test_database_url):
    engine, schema = migrated_db
    result = _run_alembic(["downgrade", "base"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic downgrade base 실패\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=:s"
            ),
            {"s": schema},
        ).all()
    remaining = {r[0] for r in rows} - {"alembic_version"}
    assert remaining == set(), f"downgrade 후에도 남은 테이블: {remaining}"

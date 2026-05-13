"""L1 — league.is_active 통합 테스트.

격리 schema 에 `alembic upgrade head` (0001 + 0002) 적용한 뒤
- league.is_active 컬럼 정의 (boolean, NOT NULL, default true)
- league_active_idx partial index
- default 백필, NOT NULL 강제, 토글, downgrade reversibility
를 검증.

be-dev 가 `alembic/versions/0002_league_is_active.py` 와 모델 변경을
작성하기 전까지 fail (TDD Red).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 유틸 (phase-1 통합 테스트와 동일 패턴)
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_alembic(args: list[str], schema: str, db_url: str) -> subprocess.CompletedProcess:
    """alembic 을 격리 schema 의 search_path 로 실행 (PGOPTIONS 사용)."""
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
    """upgrade head 적용 후 (engine, schema_name) 반환."""
    engine, schema = isolated_db
    result = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head 실패 (schema={schema})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return engine, schema


def _insert_league(conn, *, external_id=39, name="Premier League", type_="League", slug="premier-league"):
    return conn.execute(
        text(
            "INSERT INTO league (external_id, name, type, slug) "
            "VALUES (:e, :n, :t, :s) RETURNING id"
        ),
        {"e": external_id, "n": name, "t": type_, "s": slug},
    ).scalar()


# ---------------------------------------------------------------------------
# LI-01 ~ LI-03 마이그레이션 결과
# ---------------------------------------------------------------------------

def test_li01_is_active_column_definition(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT data_type, is_nullable FROM information_schema.columns "
                "WHERE table_schema=:s AND table_name='league' AND column_name='is_active'"
            ),
            {"s": schema},
        ).first()
    assert row is not None, "league.is_active 컬럼이 생성되지 않음"
    # postgres 의 boolean 은 information_schema 에서 'boolean' 으로 보고됨
    assert row.data_type == "boolean", f"data_type={row.data_type}"
    assert row.is_nullable == "NO", f"is_nullable={row.is_nullable}"


def test_li02_is_active_default_true(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        default = conn.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema=:s AND table_name='league' AND column_name='is_active'"
            ),
            {"s": schema},
        ).scalar()
    assert default is not None, "is_active column_default 없음"
    assert "true" in default.lower(), f"is_active default 가 true 가 아님: {default!r}"


def test_li03_league_active_idx_is_partial(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        indexdef = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=:s AND indexname='league_active_idx'"
            ),
            {"s": schema},
        ).scalar()
    assert indexdef is not None, "league_active_idx 인덱스 생성되지 않음"
    # partial index 조건이 정의되어야 함
    assert "WHERE" in indexdef.upper(), f"partial index 가 아님: {indexdef!r}"
    assert "is_active" in indexdef.lower(), f"is_active 조건 누락: {indexdef!r}"


# ---------------------------------------------------------------------------
# LI-04 ~ LI-06 default / NOT NULL / 토글
# ---------------------------------------------------------------------------

def test_li04_insert_uses_default_true(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        val = conn.execute(
            text("SELECT is_active FROM league WHERE id=:l"), {"l": lid}
        ).scalar()
        assert val is True


def test_li05_explicit_null_rejected(migrated_db):
    from sqlalchemy.exc import IntegrityError

    engine, _ = migrated_db
    with engine.connect() as conn:
        with pytest.raises(IntegrityError):
            with conn.begin():
                conn.execute(
                    text(
                        "INSERT INTO league (external_id, name, type, slug, is_active) "
                        "VALUES (1, 'X', 'League', 'x', NULL)"
                    )
                )


def test_li06_toggle_to_false(migrated_db):
    engine, _ = migrated_db
    with engine.begin() as conn:
        lid = _insert_league(conn)
        conn.execute(
            text("UPDATE league SET is_active = false WHERE id=:l"), {"l": lid}
        )
        val = conn.execute(
            text("SELECT is_active FROM league WHERE id=:l"), {"l": lid}
        ).scalar()
        assert val is False


# ---------------------------------------------------------------------------
# LI-07 partial index 존재
# ---------------------------------------------------------------------------

def test_li07_partial_index_listed(migrated_db):
    engine, schema = migrated_db
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname=:s"),
            {"s": schema},
        ).all()
    names = {r[0] for r in rows}
    assert "league_active_idx" in names, f"league_active_idx 누락. found: {names}"


# ---------------------------------------------------------------------------
# LI-08 / LI-09 downgrade -1
# ---------------------------------------------------------------------------

def test_li08_downgrade_removes_column_and_index_but_keeps_table(migrated_db, test_database_url):
    engine, schema = migrated_db
    result = _run_alembic(["downgrade", "-1"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic downgrade -1 실패\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    with engine.connect() as conn:
        # 컬럼 제거 확인
        col_exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=:s AND table_name='league' AND column_name='is_active'"
            ),
            {"s": schema},
        ).scalar()
        assert col_exists is None, "downgrade 후에도 is_active 컬럼이 남아 있음"
        # 인덱스 제거 확인
        idx_exists = conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname=:s AND indexname='league_active_idx'"
            ),
            {"s": schema},
        ).scalar()
        assert idx_exists is None, "downgrade 후에도 league_active_idx 가 남아 있음"
        # league 테이블 자체는 유지
        league_exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema=:s AND table_name='league'"
            ),
            {"s": schema},
        ).scalar()
        assert league_exists == 1, "downgrade 가 league 테이블 자체를 drop 하면 안 됨"


def test_li09_alembic_revision_chain(migrated_db, test_database_url):
    """downgrade 1단계 후 current revision 이 0001_initial_schema 여야 함.

    LI-08 와 같은 단계지만, 의존성 체인이 명확히 0002 -> 0001 인지 검증.
    """
    _, schema = migrated_db
    # downgrade -1 (== 0002 제거)
    result = _run_alembic(["downgrade", "-1"], schema=schema, db_url=test_database_url)
    assert result.returncode == 0, f"downgrade 실패: {result.stderr}"

    # current 가 0001_initial_schema
    result = _run_alembic(["current"], schema=schema, db_url=test_database_url)
    assert result.returncode == 0, f"current 조회 실패: {result.stderr}"
    out = (result.stdout + result.stderr).lower()
    assert "0001_initial_schema" in out, (
        f"downgrade 후 current 가 0001_initial_schema 가 아님. raw:\n{result.stdout}\n{result.stderr}"
    )

"""L1 — league.is_active 단위 테스트.

SQLAlchemy 메타데이터 introspection 으로 모델에 `is_active` 컬럼 +
`league_active_idx` 인덱스가 정의되어 있는지 검증.

be-dev 가 `app/models/league.py` (또는 entity 가 있는 모듈) 의 `League`
클래스에 `is_active: Mapped[bool]` 을 추가하기 전까지 fail (TDD Red).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def models():
    from app.models import (  # noqa: F401
        AppUser,
        Base,
        Fixture,
        FixtureDetail,
        League,
        LeagueTranslation,
        Player,
        PlayerSeasonStat,
        PlayerTranslation,
        Standings,
        Team,
        TeamSeason,
        TeamTranslation,
        Venue,
    )
    return {"Base": Base, "League": League}


@pytest.fixture(scope="module")
def metadata(models):
    return models["Base"].metadata


@pytest.fixture(scope="module")
def league_tbl(metadata):
    return metadata.tables["league"]


# ---------------------------------------------------------------------------
# LU-01 ~ LU-04 컬럼 정의
# ---------------------------------------------------------------------------

def test_lu01_is_active_column_exists(league_tbl):
    assert "is_active" in league_tbl.columns, "league.is_active 컬럼 정의 필요"


def test_lu02_is_active_is_boolean(league_tbl):
    from sqlalchemy import Boolean

    col = league_tbl.columns["is_active"]
    assert isinstance(col.type, Boolean), f"is_active Boolean 필요 (got {type(col.type)})"


def test_lu03_is_active_not_null(league_tbl):
    assert league_tbl.columns["is_active"].nullable is False, "is_active NOT NULL 필요"


def test_lu04_is_active_server_default_true(league_tbl):
    col = league_tbl.columns["is_active"]
    sd = col.server_default
    assert sd is not None, "is_active server_default 필요"
    sd_text = (str(sd.arg) if hasattr(sd, "arg") else str(sd)).lower()
    assert "true" in sd_text, f"is_active server_default 가 true 여야 함 (got {sd_text!r})"


# ---------------------------------------------------------------------------
# LU-05 partial index 모델 선언
# ---------------------------------------------------------------------------

def test_lu05_league_active_idx_declared_on_model(league_tbl):
    """모델 측 metadata 에 'league_active_idx' 인덱스가 등록되어야 함.

    dev 가 SQLAlchemy `Index('league_active_idx', League.is_active,
    postgresql_where=...)` 로 선언하면 통과. 마이그레이션만 만들고 모델에
    선언 안 하면 fail.
    """
    names = {idx.name for idx in league_tbl.indexes}
    assert "league_active_idx" in names, (
        f"league_active_idx 모델 인덱스 선언 필요 (existing: {names})"
    )


# ---------------------------------------------------------------------------
# LU-06 회귀 방지 — 13 테이블 유지
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


def test_lu06_table_count_unchanged(metadata):
    assert set(metadata.tables.keys()) == EXPECTED_TABLES, (
        "L1 task 는 컬럼/인덱스 추가만. 테이블 추가/삭제 금지"
    )

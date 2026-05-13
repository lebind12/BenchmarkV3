"""Phase 1 — DB 모델 단위 테스트.

정본: docs/spec/db-schema.md (그리고 docs/spec/endpoints/phase-1-db-schema.md).
SQLAlchemy 메타데이터 introspection 만으로 13 모델의 컬럼/제약/타입을 검증한다.
외부 DB 미사용. mock 도 불필요 (메타데이터만 본다).

이 테스트는 be-dev 가 `app/models/` 에 모델을 작성하기 전까지 ImportError 로 실패한다 (TDD Red 정상).
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 모델 import
# ---------------------------------------------------------------------------

def _import_models():
    """13 모델 + Base 를 import. dev 가 모듈 작성 전이면 ImportError."""
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
    return {
        "Base": Base,
        "League": League,
        "LeagueTranslation": LeagueTranslation,
        "Venue": Venue,
        "Team": Team,
        "TeamTranslation": TeamTranslation,
        "TeamSeason": TeamSeason,
        "Player": Player,
        "PlayerTranslation": PlayerTranslation,
        "PlayerSeasonStat": PlayerSeasonStat,
        "Fixture": Fixture,
        "FixtureDetail": FixtureDetail,
        "Standings": Standings,
        "AppUser": AppUser,
    }


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


@pytest.fixture(scope="module")
def models():
    return _import_models()


@pytest.fixture(scope="module")
def metadata(models):
    return models["Base"].metadata


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _get_fk(column):
    fks = list(column.foreign_keys)
    assert len(fks) == 1, f"{column.name} 에 FK 가 정확히 1개 있어야 함"
    return fks[0]


def _has_unique(table, column_name):
    col = table.columns[column_name]
    if col.unique:
        return True
    from sqlalchemy import UniqueConstraint
    for c in table.constraints:
        if isinstance(c, UniqueConstraint) and list(c.columns.keys()) == [column_name]:
            return True
    # 단일 컬럼 unique index
    for idx in table.indexes:
        if idx.unique and [c.name for c in idx.columns] == [column_name]:
            return True
    return False


# ---------------------------------------------------------------------------
# U-01, U-02
# ---------------------------------------------------------------------------

def test_u01_all_models_importable(models):
    assert len(models) == 14  # 13 models + Base


def test_u02_metadata_contains_exactly_13_tables(metadata):
    assert set(metadata.tables.keys()) == EXPECTED_TABLES


# ---------------------------------------------------------------------------
# U-03 PK
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name,expected_pk",
    [
        ("league", ["id"]),
        ("league_translation", ["league_id"]),
        ("venue", ["id"]),
        ("team", ["id"]),
        ("team_translation", ["team_id"]),
        ("team_season", ["team_id", "league_id", "season_year"]),
        ("player", ["id"]),
        ("player_translation", ["player_id"]),
        ("player_season_stat", ["id"]),
        ("fixture", ["id"]),
        ("fixture_detail", ["fixture_id"]),
        ("standings", ["id"]),
        ("app_user", ["id"]),
    ],
)
def test_u03_primary_keys(metadata, table_name, expected_pk):
    tbl = metadata.tables[table_name]
    pk_cols = [c.name for c in tbl.primary_key.columns]
    assert sorted(pk_cols) == sorted(expected_pk), f"{table_name} PK mismatch"


# ---------------------------------------------------------------------------
# U-04 entity external_id UNIQUE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name",
    ["league", "venue", "team", "player", "fixture"],
)
def test_u04_entity_external_id_unique(metadata, table_name):
    tbl = metadata.tables[table_name]
    assert "external_id" in tbl.columns
    assert _has_unique(tbl, "external_id"), f"{table_name}.external_id UNIQUE 필요"


# ---------------------------------------------------------------------------
# U-05 *_translation PK=FK ON DELETE CASCADE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name,fk_col,target",
    [
        ("league_translation", "league_id", "league.id"),
        ("team_translation", "team_id", "team.id"),
        ("player_translation", "player_id", "player.id"),
    ],
)
def test_u05_translation_pk_fk_cascade(metadata, table_name, fk_col, target):
    tbl = metadata.tables[table_name]
    col = tbl.columns[fk_col]
    # PK
    assert col.primary_key, f"{table_name}.{fk_col} 가 PK 여야 함"
    # FK + CASCADE
    fk = _get_fk(col)
    assert fk.target_fullname == target
    assert (fk.ondelete or "").upper() == "CASCADE"


# ---------------------------------------------------------------------------
# U-06 ON DELETE SET NULL
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name,fk_col,target",
    [
        ("team", "venue_id", "venue.id"),
        ("player", "current_team_id", "team.id"),
        ("fixture", "home_team_id", "team.id"),
        ("fixture", "away_team_id", "team.id"),
        ("fixture", "venue_id", "venue.id"),
    ],
)
def test_u06_set_null_fks(metadata, table_name, fk_col, target):
    tbl = metadata.tables[table_name]
    col = tbl.columns[fk_col]
    fk = _get_fk(col)
    assert fk.target_fullname == target
    assert (fk.ondelete or "").upper() == "SET NULL"
    assert col.nullable is True


# ---------------------------------------------------------------------------
# U-07 team_season composite PK
# ---------------------------------------------------------------------------

def test_u07_team_season_composite_pk(metadata):
    tbl = metadata.tables["team_season"]
    pk_cols = sorted(c.name for c in tbl.primary_key.columns)
    assert pk_cols == ["league_id", "season_year", "team_id"]


# ---------------------------------------------------------------------------
# U-08 player_season_stat UNIQUE 4-tuple
# ---------------------------------------------------------------------------

def test_u08_player_season_stat_unique(metadata):
    from sqlalchemy import UniqueConstraint

    tbl = metadata.tables["player_season_stat"]
    expected = {"player_id", "team_id", "league_id", "season_year"}
    found = False
    for c in tbl.constraints:
        if isinstance(c, UniqueConstraint) and set(c.columns.keys()) == expected:
            found = True
            break
    if not found:
        for idx in tbl.indexes:
            if idx.unique and set(c.name for c in idx.columns) == expected:
                found = True
                break
    assert found, "player_season_stat UNIQUE(player_id, team_id, league_id, season_year) 필요"


# ---------------------------------------------------------------------------
# U-09 league.type CHECK
# ---------------------------------------------------------------------------

def test_u09_league_type_check(metadata):
    from sqlalchemy import CheckConstraint

    tbl = metadata.tables["league"]
    texts = [str(c.sqltext) for c in tbl.constraints if isinstance(c, CheckConstraint)]
    blob = " ".join(texts)
    assert "'League'" in blob and "'Cup'" in blob, f"league.type CHECK 필요: found={texts}"


# ---------------------------------------------------------------------------
# U-10 app_user.role CHECK + default USER
# ---------------------------------------------------------------------------

def test_u10_app_user_role_check_and_default(metadata):
    from sqlalchemy import CheckConstraint

    tbl = metadata.tables["app_user"]
    texts = [str(c.sqltext) for c in tbl.constraints if isinstance(c, CheckConstraint)]
    blob = " ".join(texts)
    for v in ("'USER'", "'STREAMER'", "'ADMIN'"):
        assert v in blob, f"app_user.role CHECK 에 {v} 필요"

    role_col = tbl.columns["role"]
    # server_default 가 'USER' 를 포함해야 함
    sd = role_col.server_default
    sd_text = (
        str(sd.arg) if sd is not None and hasattr(sd, "arg") else str(sd)
    )
    assert "USER" in (sd_text or ""), f"app_user.role server_default 'USER' 필요 (got={sd_text})"


# ---------------------------------------------------------------------------
# U-11 fixture team FK nullable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("col_name", ["home_team_id", "away_team_id", "venue_id"])
def test_u11_fixture_optional_fk_nullable(metadata, col_name):
    tbl = metadata.tables["fixture"]
    assert tbl.columns[col_name].nullable is True


# ---------------------------------------------------------------------------
# U-12 translation cols nullable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name", ["league_translation", "team_translation", "player_translation"]
)
@pytest.mark.parametrize("col_name", ["name_ko", "short_name_ko"])
def test_u12_translation_cols_nullable(metadata, table_name, col_name):
    tbl = metadata.tables[table_name]
    assert tbl.columns[col_name].nullable is True


# ---------------------------------------------------------------------------
# U-13 created_at / updated_at server_default
# ---------------------------------------------------------------------------

# created_at 컬럼이 있는 테이블 일람 (정본 §3 기반)
TABLES_WITH_CREATED_AT = [
    "league",
    "venue",
    "team",
    "team_season",
    "player",
    "fixture",
    "app_user",
]

TABLES_WITH_UPDATED_AT = [
    "league",
    "league_translation",
    "venue",
    "team",
    "team_translation",
    "player",
    "player_translation",
    "player_season_stat",
    "fixture",
    "fixture_detail",
    "standings",
    "app_user",
]


@pytest.mark.parametrize("table_name", TABLES_WITH_CREATED_AT)
def test_u13a_created_at_server_default(metadata, table_name):
    col = metadata.tables[table_name].columns["created_at"]
    assert col.server_default is not None, f"{table_name}.created_at server_default 필요"
    assert col.nullable is False


@pytest.mark.parametrize("table_name", TABLES_WITH_UPDATED_AT)
def test_u13b_updated_at_server_default(metadata, table_name):
    col = metadata.tables[table_name].columns["updated_at"]
    assert col.server_default is not None, f"{table_name}.updated_at server_default 필요"
    assert col.nullable is False


# ---------------------------------------------------------------------------
# U-14 player_season_stat.rating Numeric(4,2)
# ---------------------------------------------------------------------------

def test_u14_rating_numeric(metadata):
    from sqlalchemy import Numeric

    col = metadata.tables["player_season_stat"].columns["rating"]
    assert isinstance(col.type, Numeric), f"rating Numeric 필요 (got {type(col.type)})"
    assert col.type.precision == 4
    assert col.type.scale == 2


# ---------------------------------------------------------------------------
# U-15 JSONB 컬럼
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "table_name,col_name,not_null",
    [
        ("player_season_stat", "raw_stats", True),
        ("fixture_detail", "events", False),
        ("fixture_detail", "statistics", False),
        ("fixture_detail", "lineups", False),
        ("standings", "home_away_breakdown", False),
        ("standings", "raw_data", False),
    ],
)
def test_u15_jsonb_columns(metadata, table_name, col_name, not_null):
    from sqlalchemy.dialects.postgresql import JSONB

    col = metadata.tables[table_name].columns[col_name]
    assert isinstance(col.type, JSONB), f"{table_name}.{col_name} JSONB 필요 (got {type(col.type)})"
    if not_null:
        assert col.nullable is False


# ---------------------------------------------------------------------------
# 추가: league type 시드 매핑 검증용 슬러그/이름 컬럼 타입 확인 등 sanity
# ---------------------------------------------------------------------------

def test_league_slug_unique_and_not_null(metadata):
    tbl = metadata.tables["league"]
    slug = tbl.columns["slug"]
    assert slug.nullable is False
    assert _has_unique(tbl, "slug")


def test_team_slug_unique_and_not_null(metadata):
    tbl = metadata.tables["team"]
    slug = tbl.columns["slug"]
    assert slug.nullable is False
    assert _has_unique(tbl, "slug")


def test_player_slug_unique_and_not_null(metadata):
    tbl = metadata.tables["player"]
    slug = tbl.columns["slug"]
    assert slug.nullable is False
    assert _has_unique(tbl, "slug")


def test_app_user_email_unique(metadata):
    tbl = metadata.tables["app_user"]
    assert _has_unique(tbl, "email")
    assert tbl.columns["email"].nullable is False


def test_venue_external_id_nullable(metadata):
    """venue.external_id 는 nullable 이지만 UNIQUE 여야 함 (NULL 다중 허용은 PG 기본)."""
    tbl = metadata.tables["venue"]
    assert tbl.columns["external_id"].nullable is True
    assert _has_unique(tbl, "external_id")


def test_fixture_kickoff_not_null(metadata):
    tbl = metadata.tables["fixture"]
    assert tbl.columns["kickoff_at"].nullable is False
    assert tbl.columns["status_short"].nullable is False


def test_standings_unique_index_uses_coalesce(metadata):
    """standings_uniq 는 UNIQUE index 이며 group_name 을 COALESCE 한 functional index 여야 한다.

    SQLAlchemy 메타데이터에서 functional index 표현 방식이 다양하므로,
    여기서는 (a) 이름이 'standings_uniq' 인 unique 인덱스가 존재하고
    (b) (league_id, season_year, team_id) 가 포함되는지 정도만 확인한다.
    (COALESCE 동작 자체는 통합 테스트 I-16 에서 검증.)
    """
    tbl = metadata.tables["standings"]
    found = None
    for idx in tbl.indexes:
        if idx.name == "standings_uniq":
            found = idx
            break
    assert found is not None, "standings_uniq 인덱스 필요"
    assert found.unique is True
    expr_blob = " ".join(str(e) for e in found.expressions)
    for c in ("league_id", "season_year", "team_id"):
        assert c in expr_blob, f"standings_uniq 에 {c} 포함 필요 (got {expr_blob!r})"
    # COALESCE 가 표현식 어딘가에 있어야 한다 (대소문자 무시)
    assert re.search(r"coalesce", expr_blob, re.IGNORECASE), (
        f"standings_uniq 는 group_name COALESCE 사용 필요 (got {expr_blob!r})"
    )

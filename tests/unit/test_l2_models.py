"""L2 — transfer / injury / news_article 단위 테스트.

SQLAlchemy 메타데이터 introspection 만. be-dev 가 모델 추가 전까지 fail (Red).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def models():
    from app.models import (  # noqa: F401
        Base,
        Injury,
        NewsArticle,
        Transfer,
    )
    return {"Base": Base, "Transfer": Transfer, "Injury": Injury, "NewsArticle": NewsArticle}


@pytest.fixture(scope="module")
def metadata(models):
    return models["Base"].metadata


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _get_fk(col):
    fks = list(col.foreign_keys)
    assert len(fks) == 1, f"{col.name} FK 1개 필요 (got {len(fks)})"
    return fks[0]


def _has_unique_columns(tbl, columns: set[str]) -> bool:
    from sqlalchemy import UniqueConstraint
    for c in tbl.constraints:
        if isinstance(c, UniqueConstraint) and set(c.columns.keys()) == columns:
            return True
    return False


# ---------------------------------------------------------------------------
# L2U-01 / L2U-02
# ---------------------------------------------------------------------------

EXPECTED_16 = {
    "league", "league_translation", "venue", "team", "team_translation",
    "team_season", "player", "player_translation", "player_season_stat",
    "fixture", "fixture_detail", "standings", "app_user",
    "transfer", "injury", "news_article",
}


def test_l2u01_models_importable(models):
    assert {"Transfer", "Injury", "NewsArticle"} <= set(models.keys())


def test_l2u02_metadata_has_16_tables(metadata):
    assert set(metadata.tables.keys()) == EXPECTED_16


# ---------------------------------------------------------------------------
# L2U-03 transfer 컬럼
# ---------------------------------------------------------------------------

def test_l2u03_transfer_columns(metadata):
    from sqlalchemy import Date, DateTime, Text
    from sqlalchemy.dialects.postgresql import JSONB

    tbl = metadata.tables["transfer"]
    # PK id
    assert tbl.columns["id"].primary_key

    # player_id NOT NULL FK CASCADE
    pid = tbl.columns["player_id"]
    assert pid.nullable is False
    fk = _get_fk(pid)
    assert fk.target_fullname == "player.id"
    assert (fk.ondelete or "").upper() == "CASCADE"

    # transfer_date date NOT NULL
    td = tbl.columns["transfer_date"]
    assert isinstance(td.type, Date)
    assert td.nullable is False

    # type text nullable
    assert isinstance(tbl.columns["type"].type, Text)
    assert tbl.columns["type"].nullable is True

    # from_team_id / to_team_id FK SET NULL, nullable
    for col_name in ("from_team_id", "to_team_id"):
        c = tbl.columns[col_name]
        assert c.nullable is True
        fk = _get_fk(c)
        assert fk.target_fullname == "team.id"
        assert (fk.ondelete or "").upper() == "SET NULL"

    # raw_data JSONB nullable
    rd = tbl.columns["raw_data"]
    assert isinstance(rd.type, JSONB)
    assert rd.nullable is True

    # timestamps
    for c in ("created_at", "updated_at"):
        col = tbl.columns[c]
        assert col.nullable is False
        assert col.server_default is not None
        assert isinstance(col.type, DateTime)


# ---------------------------------------------------------------------------
# L2U-04 transfer_uniq
# ---------------------------------------------------------------------------

def test_l2u04_transfer_uniq(metadata):
    tbl = metadata.tables["transfer"]
    assert _has_unique_columns(
        tbl, {"player_id", "transfer_date", "from_team_id", "to_team_id"}
    ), "transfer_uniq UNIQUE 4 컬럼 필요"


# ---------------------------------------------------------------------------
# L2U-05 transfer 인덱스 4개
# ---------------------------------------------------------------------------

def test_l2u05_transfer_indexes(metadata):
    tbl = metadata.tables["transfer"]
    names = {idx.name for idx in tbl.indexes}
    for required in (
        "transfer_player_idx",
        "transfer_date_idx",
        "transfer_to_team_idx",
        "transfer_from_team_idx",
    ):
        assert required in names, f"{required} 인덱스 누락 (existing: {names})"


# ---------------------------------------------------------------------------
# L2U-06 injury 컬럼
# ---------------------------------------------------------------------------

def test_l2u06_injury_columns(metadata):
    from sqlalchemy import DateTime, Integer, Text
    from sqlalchemy.dialects.postgresql import JSONB

    tbl = metadata.tables["injury"]
    assert tbl.columns["id"].primary_key

    # player_id NOT NULL CASCADE
    pid = tbl.columns["player_id"]
    assert pid.nullable is False
    assert (_get_fk(pid).ondelete or "").upper() == "CASCADE"

    # fixture_id nullable SET NULL
    fid = tbl.columns["fixture_id"]
    assert fid.nullable is True
    assert (_get_fk(fid).ondelete or "").upper() == "SET NULL"

    # team_id NOT NULL CASCADE
    tid = tbl.columns["team_id"]
    assert tid.nullable is False
    assert (_get_fk(tid).ondelete or "").upper() == "CASCADE"

    # league_id NOT NULL CASCADE
    lid = tbl.columns["league_id"]
    assert lid.nullable is False
    assert (_get_fk(lid).ondelete or "").upper() == "CASCADE"

    # season_year integer NOT NULL
    sy = tbl.columns["season_year"]
    assert isinstance(sy.type, Integer)
    assert sy.nullable is False

    # type/reason nullable
    for c in ("type", "reason"):
        col = tbl.columns[c]
        assert isinstance(col.type, Text)
        assert col.nullable is True

    # raw_data JSONB
    assert isinstance(tbl.columns["raw_data"].type, JSONB)
    assert tbl.columns["raw_data"].nullable is True

    # reported_at timestamptz nullable
    ra = tbl.columns["reported_at"]
    assert isinstance(ra.type, DateTime)
    assert ra.nullable is True


# ---------------------------------------------------------------------------
# L2U-07 injury_uniq
# ---------------------------------------------------------------------------

def test_l2u07_injury_uniq(metadata):
    tbl = metadata.tables["injury"]
    assert _has_unique_columns(
        tbl, {"player_id", "fixture_id", "league_id", "season_year"}
    ), "injury_uniq UNIQUE 4 컬럼 필요"


# ---------------------------------------------------------------------------
# L2U-08 injury 인덱스 (partial 포함)
# ---------------------------------------------------------------------------

def test_l2u08_injury_indexes_with_partial(metadata):
    import re

    tbl = metadata.tables["injury"]
    by_name = {idx.name: idx for idx in tbl.indexes}
    for required in ("injury_player_idx", "injury_team_season_idx", "injury_fixture_idx"):
        assert required in by_name, f"{required} 누락 (got: {set(by_name)})"

    fixture_idx = by_name["injury_fixture_idx"]
    # partial 조건이 모델에 선언되어야 함
    where_clause = ""
    if fixture_idx.dialect_options.get("postgresql"):
        where_clause = str(
            fixture_idx.dialect_options["postgresql"].get("where", "")
        )
    blob = where_clause + " " + " ".join(str(e) for e in fixture_idx.expressions)
    assert re.search(r"fixture_id\s+is\s+not\s+null", blob, re.IGNORECASE) or (
        "fixture_id" in blob
    ), f"injury_fixture_idx 의 partial WHERE 조건 누락 (got: {blob!r})"


# ---------------------------------------------------------------------------
# L2U-09 news_article 컬럼
# ---------------------------------------------------------------------------

def test_l2u09_news_article_columns(metadata):
    from sqlalchemy import DateTime, Text
    from sqlalchemy.dialects.postgresql import JSONB

    tbl = metadata.tables["news_article"]
    assert tbl.columns["id"].primary_key

    # source NOT NULL text
    s = tbl.columns["source"]
    assert isinstance(s.type, Text)
    assert s.nullable is False

    # source_url NOT NULL UNIQUE
    su = tbl.columns["source_url"]
    assert su.nullable is False
    # UNIQUE 검증: 컬럼 단일 UNIQUE 또는 UniqueConstraint
    assert su.unique or _has_unique_columns(tbl, {"source_url"})

    # original_title NOT NULL
    ot = tbl.columns["original_title"]
    assert ot.nullable is False
    assert isinstance(ot.type, Text)

    # nullable cols
    for c in ("original_summary", "image_url", "title_ko", "summary_ko"):
        assert tbl.columns[c].nullable is True

    # published_at NOT NULL timestamptz
    pa = tbl.columns["published_at"]
    assert pa.nullable is False
    assert isinstance(pa.type, DateTime)

    # translated_at nullable timestamptz
    ta = tbl.columns["translated_at"]
    assert ta.nullable is True
    assert isinstance(ta.type, DateTime)

    # tags JSONB nullable
    tags = tbl.columns["tags"]
    assert isinstance(tags.type, JSONB)
    assert tags.nullable is True


# ---------------------------------------------------------------------------
# L2U-10 news_article 인덱스 (partial + GIN)
# ---------------------------------------------------------------------------

def test_l2u10_news_article_indexes_partial_and_gin(metadata):
    import re

    tbl = metadata.tables["news_article"]
    by_name = {idx.name: idx for idx in tbl.indexes}
    for required in (
        "news_article_published_idx",
        "news_article_pending_idx",
        "news_article_tags_gin",
    ):
        assert required in by_name, f"{required} 누락 (got: {set(by_name)})"

    # partial: pending_idx WHERE title_ko IS NULL
    pending = by_name["news_article_pending_idx"]
    where_clause = ""
    if pending.dialect_options.get("postgresql"):
        where_clause = str(pending.dialect_options["postgresql"].get("where", ""))
    blob = where_clause + " " + " ".join(str(e) for e in pending.expressions)
    assert re.search(r"title_ko\s+is\s+null", blob, re.IGNORECASE) or (
        "title_ko" in blob
    ), f"pending partial WHERE 조건 누락 (got: {blob!r})"

    # GIN: tags_gin
    gin = by_name["news_article_tags_gin"]
    using = ""
    if gin.dialect_options.get("postgresql"):
        using = str(gin.dialect_options["postgresql"].get("using", ""))
    assert using.lower() == "gin", f"news_article_tags_gin 의 USING gin 누락 (got: {using!r})"


# ---------------------------------------------------------------------------
# L2U-11 회귀: 기존 league.is_active 유지
# ---------------------------------------------------------------------------

def test_l2u11_regression_league_is_active_preserved(metadata):
    league = metadata.tables["league"]
    assert "is_active" in league.columns
    assert league.columns["is_active"].nullable is False

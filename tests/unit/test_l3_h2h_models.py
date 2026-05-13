"""L3 — h2h_fixture 단위 테스트."""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def models():
    from app.models import Base, H2HFixture  # noqa: F401
    return {"Base": Base, "H2HFixture": H2HFixture}


@pytest.fixture(scope="module")
def metadata(models):
    return models["Base"].metadata


def _get_fk(col):
    fks = list(col.foreign_keys)
    assert len(fks) == 1, f"{col.name} FK 1개 필요 (got {len(fks)})"
    return fks[0]


def _has_unique(tbl, column_name):
    from sqlalchemy import UniqueConstraint
    col = tbl.columns[column_name]
    if col.unique:
        return True
    for c in tbl.constraints:
        if isinstance(c, UniqueConstraint) and list(c.columns.keys()) == [column_name]:
            return True
    for idx in tbl.indexes:
        if idx.unique and [c.name for c in idx.columns] == [column_name]:
            return True
    return False


EXPECTED_17 = {
    "league", "league_translation", "venue", "team", "team_translation",
    "team_season", "player", "player_translation", "player_season_stat",
    "fixture", "fixture_detail", "standings", "app_user",
    "transfer", "injury", "news_article",
    "h2h_fixture",
}


# ---------------------------------------------------------------------------
# L3U-01 / L3U-02
# ---------------------------------------------------------------------------

def test_l3u01_h2h_fixture_importable(models):
    assert "H2HFixture" in models


def test_l3u02_metadata_has_17_tables(metadata):
    assert set(metadata.tables.keys()) == EXPECTED_17


# ---------------------------------------------------------------------------
# L3U-03 컬럼/타입/NULL
# ---------------------------------------------------------------------------

def test_l3u03_columns(metadata):
    from sqlalchemy import DateTime, Integer, SmallInteger, Text
    from sqlalchemy.dialects.postgresql import JSONB

    tbl = metadata.tables["h2h_fixture"]
    assert tbl.columns["id"].primary_key

    # external_id integer NOT NULL UNIQUE
    eid = tbl.columns["external_id"]
    assert isinstance(eid.type, Integer)
    assert eid.nullable is False

    # home_team_id NOT NULL FK CASCADE
    hid = tbl.columns["home_team_id"]
    assert hid.nullable is False
    fk = _get_fk(hid)
    assert fk.target_fullname == "team.id"
    assert (fk.ondelete or "").upper() == "CASCADE"

    # away_team_id NOT NULL FK CASCADE
    aid = tbl.columns["away_team_id"]
    assert aid.nullable is False
    fk = _get_fk(aid)
    assert fk.target_fullname == "team.id"
    assert (fk.ondelete or "").upper() == "CASCADE"

    # league_external_id integer nullable (FK 없음)
    le = tbl.columns["league_external_id"]
    assert isinstance(le.type, Integer)
    assert le.nullable is True
    assert list(le.foreign_keys) == []

    # league_name text nullable
    ln = tbl.columns["league_name"]
    assert isinstance(ln.type, Text)
    assert ln.nullable is True

    # season_year integer nullable
    sy = tbl.columns["season_year"]
    assert isinstance(sy.type, Integer)
    assert sy.nullable is True

    # kickoff_at timestamptz NOT NULL
    ka = tbl.columns["kickoff_at"]
    assert isinstance(ka.type, DateTime)
    assert ka.nullable is False

    # status_short text nullable
    assert isinstance(tbl.columns["status_short"].type, Text)
    assert tbl.columns["status_short"].nullable is True

    # goals_home / goals_away smallint nullable
    for c in ("goals_home", "goals_away"):
        col = tbl.columns[c]
        assert isinstance(col.type, SmallInteger), f"{c} SmallInteger 필요"
        assert col.nullable is True

    # raw_data JSONB nullable
    rd = tbl.columns["raw_data"]
    assert isinstance(rd.type, JSONB)
    assert rd.nullable is True

    # created_at / updated_at
    for c in ("created_at", "updated_at"):
        col = tbl.columns[c]
        assert col.nullable is False
        assert col.server_default is not None


# ---------------------------------------------------------------------------
# L3U-04 external_id UNIQUE
# ---------------------------------------------------------------------------

def test_l3u04_external_id_unique(metadata):
    tbl = metadata.tables["h2h_fixture"]
    assert _has_unique(tbl, "external_id")


# ---------------------------------------------------------------------------
# L3U-05 h2h_pair_idx (LEAST/GREATEST 함수 인덱스)
# ---------------------------------------------------------------------------

def test_l3u05_h2h_pair_idx_uses_least_greatest(metadata):
    tbl = metadata.tables["h2h_fixture"]
    by_name = {idx.name: idx for idx in tbl.indexes}
    assert "h2h_pair_idx" in by_name, f"h2h_pair_idx 모델 선언 필요 (found: {set(by_name)})"

    idx = by_name["h2h_pair_idx"]
    blob = " ".join(str(e) for e in idx.expressions).lower()
    assert re.search(r"least\s*\(", blob), f"LEAST 함수 누락: {blob!r}"
    assert re.search(r"greatest\s*\(", blob), f"GREATEST 함수 누락: {blob!r}"
    assert "kickoff_at" in blob, f"kickoff_at 컬럼 누락: {blob!r}"
    # DESC 정렬
    assert "desc" in blob, f"kickoff_at DESC 정렬 누락: {blob!r}"

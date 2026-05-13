"""fixture + fixture_detail. Spec §3.10–§3.11."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Fixture(Base):
    __tablename__ = "fixture"
    __table_args__ = (
        Index("fixture_league_season_idx", "league_id", "season_year"),
        Index("fixture_kickoff_idx", "kickoff_at"),
        Index("fixture_status_idx", "status_short"),
        Index("fixture_home_team_idx", "home_team_id"),
        Index("fixture_away_team_idx", "away_team_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    league_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("league.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[str | None] = mapped_column(Text)

    # Cup-draw fixtures may have null teams until the draw resolves (§5).
    home_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="SET NULL")
    )
    away_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="SET NULL")
    )
    venue_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("venue.id", ondelete="SET NULL")
    )
    referee: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str | None] = mapped_column(Text)
    kickoff_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    timestamp_unix: Mapped[int | None] = mapped_column(BigInteger)

    status_long: Mapped[str | None] = mapped_column(Text)
    status_short: Mapped[str] = mapped_column(Text, nullable=False)
    status_elapsed: Mapped[int | None] = mapped_column(SmallInteger)
    period_first: Mapped[int | None] = mapped_column(BigInteger)
    period_second: Mapped[int | None] = mapped_column(BigInteger)

    goals_home: Mapped[int | None] = mapped_column(SmallInteger)
    goals_away: Mapped[int | None] = mapped_column(SmallInteger)
    score_ht_home: Mapped[int | None] = mapped_column(SmallInteger)
    score_ht_away: Mapped[int | None] = mapped_column(SmallInteger)
    score_ft_home: Mapped[int | None] = mapped_column(SmallInteger)
    score_ft_away: Mapped[int | None] = mapped_column(SmallInteger)
    score_et_home: Mapped[int | None] = mapped_column(SmallInteger)
    score_et_away: Mapped[int | None] = mapped_column(SmallInteger)
    score_pen_home: Mapped[int | None] = mapped_column(SmallInteger)
    score_pen_away: Mapped[int | None] = mapped_column(SmallInteger)
    home_winner: Mapped[bool | None] = mapped_column(Boolean)
    away_winner: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FixtureDetail(Base):
    __tablename__ = "fixture_detail"

    fixture_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("fixture.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    events: Mapped[dict | None] = mapped_column(JSONB)
    statistics: Mapped[dict | None] = mapped_column(JSONB)
    lineups: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

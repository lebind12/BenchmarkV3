"""standings. Spec §3.12.

The uniqueness rule is a *functional* unique index on
``(league_id, season_year, team_id, COALESCE(group_name, ''))`` so that
NULL group_name rows still collide with each other (different from PG's
default NULL-is-not-equal behaviour).
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Standings(Base):
    __tablename__ = "standings"
    __table_args__ = (
        Index(
            "standings_uniq",
            "league_id",
            "season_year",
            "team_id",
            text("COALESCE(group_name, '')"),
            unique=True,
        ),
        Index(
            "standings_league_season_rank_idx",
            "league_id",
            "season_year",
            "rank",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    league_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("league.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_name: Mapped[str | None] = mapped_column(Text)

    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    points: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    played: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    win: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    draw: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    loss: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goals_for: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goals_against: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goals_diff: Mapped[int | None] = mapped_column(SmallInteger)
    form: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    home_away_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

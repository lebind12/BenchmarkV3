"""injury. Spec: docs/spec/db-schema.md §3.15."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Injury(Base):
    __tablename__ = "injury"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "fixture_id", "league_id", "season_year",
            name="injury_uniq",
        ),
        Index("injury_player_idx", "player_id"),
        Index("injury_team_season_idx", "team_id", "season_year"),
        # Partial: fixture-scoped lookups dominate the hot path; ignore
        # season-wide rows (fixture_id NULL).
        Index(
            "injury_fixture_idx",
            "fixture_id",
            postgresql_where=text("fixture_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("player.id", ondelete="CASCADE"), nullable=False
    )
    fixture_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("fixture.id", ondelete="SET NULL")
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("league.id", ondelete="CASCADE"), nullable=False
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    reported_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

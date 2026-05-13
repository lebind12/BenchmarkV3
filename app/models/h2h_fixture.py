"""h2h_fixture. Spec: docs/spec/db-schema.md §3.17.

Stores head-to-head fixture rows. Unlike :class:`Fixture` this table also
covers matches in leagues *outside* the curated whitelist (e.g. Friendlies)
which is why ``league_external_id`` has no FK back to ``league``.
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class H2HFixture(Base):
    __tablename__ = "h2h_fixture"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    home_team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    away_team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    # No FK — leagues outside the 5-league whitelist (Friendlies, etc.) are
    # legitimate H2H sources but absent from the `league` table.
    league_external_id: Mapped[int | None] = mapped_column(Integer)
    league_name: Mapped[str | None] = mapped_column(Text)
    season_year: Mapped[int | None] = mapped_column(Integer)
    kickoff_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    status_short: Mapped[str | None] = mapped_column(Text)
    goals_home: Mapped[int | None] = mapped_column(SmallInteger)
    goals_away: Mapped[int | None] = mapped_column(SmallInteger)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Functional unique-order index: (LEAST, GREATEST, kickoff DESC) makes
    # "matches between team A and team B" queries order-independent.
    __table_args__ = (
        Index(
            "h2h_pair_idx",
            func.least(home_team_id, away_team_id),
            func.greatest(home_team_id, away_team_id),
            kickoff_at.desc(),
        ),
    )

"""team + team_translation + team_season. Spec: db-schema.md §3.4–§3.6."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Team(Base):
    __tablename__ = "team"
    __table_args__ = (
        Index("team_country_idx", "country"),
        Index("team_venue_idx", "venue_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    founded: Mapped[int | None] = mapped_column(Integer)
    is_national: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    logo_url: Mapped[str | None] = mapped_column(Text)
    venue_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("venue.id", ondelete="SET NULL")
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeamTranslation(Base):
    __tablename__ = "team_translation"

    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("team.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    name_ko: Mapped[str | None] = mapped_column(Text)
    short_name_ko: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeamSeason(Base):
    __tablename__ = "team_season"
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "league_id", "season_year"),
        Index("team_season_league_year_idx", "league_id", "season_year"),
    )

    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    league_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("league.id", ondelete="CASCADE"), nullable=False
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

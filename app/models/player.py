"""player + player_translation + player_season_stat. Spec §3.7–§3.9."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Player(Base):
    __tablename__ = "player"
    __table_args__ = (
        Index("player_team_idx", "current_team_id"),
        Index("player_nationality_idx", "nationality"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    firstname: Mapped[str | None] = mapped_column(Text)
    lastname: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(SmallInteger)
    birth_date: Mapped[object | None] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(Text)
    birth_country: Mapped[str | None] = mapped_column(Text)
    nationality: Mapped[str | None] = mapped_column(Text)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[int | None] = mapped_column(SmallInteger)
    injured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    photo_url: Mapped[str | None] = mapped_column(Text)
    current_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="SET NULL")
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlayerTranslation(Base):
    __tablename__ = "player_translation"

    player_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("player.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    name_ko: Mapped[str | None] = mapped_column(Text)
    short_name_ko: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlayerSeasonStat(Base):
    __tablename__ = "player_season_stat"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_id",
            "league_id",
            "season_year",
            name="player_season_stat_uniq",
        ),
        Index("player_season_stat_player_idx", "player_id"),
        Index("player_season_stat_team_year_idx", "team_id", "season_year"),
        # 득점 랭킹용: goals DESC
        Index(
            "player_season_stat_topscorer_idx",
            "league_id",
            "season_year",
            # SQLAlchemy 가 DESC 를 표현하려면 text/desc 사용
            # alembic op.create_index 에서도 동일하게 처리.
            # 여기서는 컬럼명 + postgresql_using 으로는 부족, raw 표현으로:
            # see migration for actual DDL.
            "goals",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("player.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
    )
    league_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("league.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)

    position: Mapped[str | None] = mapped_column(Text)
    shirt_number: Mapped[int | None] = mapped_column(SmallInteger)
    appearances: Mapped[int | None] = mapped_column(SmallInteger)
    minutes: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[object | None] = mapped_column(Numeric(4, 2))
    goals: Mapped[int | None] = mapped_column(SmallInteger)
    assists: Mapped[int | None] = mapped_column(SmallInteger)
    yellow_cards: Mapped[int | None] = mapped_column(SmallInteger)
    red_cards: Mapped[int | None] = mapped_column(SmallInteger)

    raw_stats: Mapped[dict] = mapped_column(JSONB, nullable=False)

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

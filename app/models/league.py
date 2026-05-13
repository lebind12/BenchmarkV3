"""league + league_translation models.

Spec: docs/spec/db-schema.md §3.1, §3.2.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class League(Base):
    __tablename__ = "league"
    __table_args__ = (
        CheckConstraint("type IN ('League', 'Cup')", name="league_type_check"),
        Index("league_type_idx", "type"),
        # Partial index — only `is_active = true` rows are stored (dynamic
        # league enablement query path: WHERE is_active). Mirrors migration
        # 0002_league_is_active.
        Index(
            "league_active_idx",
            "is_active",
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    country_name: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(Text)
    country_flag: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    current_season: Mapped[int | None] = mapped_column(Integer)
    # Dynamic league enable/disable flag (db-schema.md §3.1). Existing rows
    # default to true via the 0002 migration backfill (server_default 'true').
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LeagueTranslation(Base):
    __tablename__ = "league_translation"

    league_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("league.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    name_ko: Mapped[str | None] = mapped_column(Text)
    short_name_ko: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

"""transfer. Spec: docs/spec/db-schema.md §3.14."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Transfer(Base):
    __tablename__ = "transfer"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "transfer_date",
            "from_team_id",
            "to_team_id",
            name="transfer_uniq",
        ),
        Index("transfer_player_idx", "player_id"),
        # date DESC — actual ordering encoded in the migration DDL.
        Index("transfer_date_idx", "transfer_date"),
        Index("transfer_to_team_idx", "to_team_id"),
        Index("transfer_from_team_idx", "from_team_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("player.id", ondelete="CASCADE"),
        nullable=False,
    )
    transfer_date: Mapped[object] = mapped_column(Date, nullable=False)
    type: Mapped[str | None] = mapped_column(Text)
    from_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="SET NULL")
    )
    to_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("team.id", ondelete="SET NULL")
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

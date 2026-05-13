"""venue model. Spec: docs/spec/db-schema.md §3.3."""
from __future__ import annotations

from sqlalchemy import BigInteger, DateTime, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Venue(Base):
    __tablename__ = "venue"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    # nullable + UNIQUE: some API-Football venues have no id, only name.
    # Postgres treats NULL as not-equal so multiple NULL rows coexist (I-09).
    external_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[int | None] = mapped_column(Integer)
    surface: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

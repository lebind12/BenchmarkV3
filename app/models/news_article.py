"""news_article. Spec: docs/spec/db-schema.md §3.16."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NewsArticle(Base):
    __tablename__ = "news_article"
    __table_args__ = (
        # published_at DESC actual ordering encoded in migration DDL.
        Index("news_article_published_idx", "published_at"),
        # Pending-translation hot path — only rows where title_ko is still NULL.
        Index(
            "news_article_pending_idx",
            "created_at",
            postgresql_where=text("title_ko IS NULL"),
        ),
        # GIN on JSONB tags → `tags @> '{...}'` is index-served.
        Index(
            "news_article_tags_gin",
            "tags",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_title: Mapped[str] = mapped_column(Text, nullable=False)
    original_summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    title_ko: Mapped[str | None] = mapped_column(Text)
    summary_ko: Mapped[str | None] = mapped_column(Text)
    translated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    tags: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

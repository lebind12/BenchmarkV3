"""transfer / injury / news_article — 3 additive tables.

Revision ID: 0003_transfer_injury_news
Revises: 0002_league_is_active
Create Date: 2026-05-14 00:30:00 +09:00

Adds the 3 follow-up tables defined in ``docs/spec/db-schema.md`` §3.14–
§3.16 (mirrored in ``docs/spec/endpoints/phase-1-followup-l2.md``):

  - transfer       — player transfer history (FK player, optional team↔team)
  - injury         — injury reports linked to fixture/team/league/season
  - news_article   — pre-translated news rows + JSONB tags (GIN-indexed)

FK creation order: transfer → injury → news_article. ``news_article`` has
no FKs. ``downgrade()`` drops them in reverse so each parent table can
re-emerge intact at revision 0002.

`h2h_fixture` (§3.17) is **not** included — separate task.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_transfer_injury_news"
down_revision: Union[str, None] = "0002_league_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- transfer ----------------------------------------------------------
    op.create_table(
        "transfer",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "player_id",
            sa.BigInteger(),
            sa.ForeignKey("player.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("type", sa.Text()),
        sa.Column(
            "from_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "to_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
        ),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "player_id",
            "transfer_date",
            "from_team_id",
            "to_team_id",
            name="transfer_uniq",
        ),
    )
    op.create_index("transfer_player_idx", "transfer", ["player_id"])
    # date DESC ordering per spec §3.14.
    op.execute("CREATE INDEX transfer_date_idx ON transfer (transfer_date DESC)")
    op.create_index("transfer_to_team_idx", "transfer", ["to_team_id"])
    op.create_index("transfer_from_team_idx", "transfer", ["from_team_id"])

    # -- injury -----------------------------------------------------------
    op.create_table(
        "injury",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "player_id",
            sa.BigInteger(),
            sa.ForeignKey("player.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fixture_id",
            sa.BigInteger(),
            sa.ForeignKey("fixture.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "league_id",
            sa.BigInteger(),
            sa.ForeignKey("league.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text()),
        sa.Column("reason", sa.Text()),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("reported_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "player_id", "fixture_id", "league_id", "season_year",
            name="injury_uniq",
        ),
    )
    op.create_index("injury_player_idx", "injury", ["player_id"])
    op.create_index(
        "injury_team_season_idx", "injury", ["team_id", "season_year"]
    )
    op.create_index(
        "injury_fixture_idx",
        "injury",
        ["fixture_id"],
        postgresql_where=sa.text("fixture_id IS NOT NULL"),
    )

    # -- news_article ------------------------------------------------------
    op.create_table(
        "news_article",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=False),
        sa.Column("original_summary", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("image_url", sa.Text()),
        sa.Column("title_ko", sa.Text()),
        sa.Column("summary_ko", sa.Text()),
        sa.Column("translated_at", sa.DateTime(timezone=True)),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source_url", name="news_article_source_url_key"),
    )
    op.execute(
        "CREATE INDEX news_article_published_idx ON news_article (published_at DESC)"
    )
    op.execute(
        "CREATE INDEX news_article_pending_idx ON news_article (created_at DESC) "
        "WHERE title_ko IS NULL"
    )
    op.create_index(
        "news_article_tags_gin",
        "news_article",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    # news_article ----------------------------------------------------------
    op.drop_index("news_article_tags_gin", table_name="news_article")
    op.execute("DROP INDEX IF EXISTS news_article_pending_idx")
    op.execute("DROP INDEX IF EXISTS news_article_published_idx")
    op.drop_table("news_article")

    # injury ---------------------------------------------------------------
    op.drop_index("injury_fixture_idx", table_name="injury")
    op.drop_index("injury_team_season_idx", table_name="injury")
    op.drop_index("injury_player_idx", table_name="injury")
    op.drop_table("injury")

    # transfer -------------------------------------------------------------
    op.drop_index("transfer_from_team_idx", table_name="transfer")
    op.drop_index("transfer_to_team_idx", table_name="transfer")
    op.execute("DROP INDEX IF EXISTS transfer_date_idx")
    op.drop_index("transfer_player_idx", table_name="transfer")
    op.drop_table("transfer")

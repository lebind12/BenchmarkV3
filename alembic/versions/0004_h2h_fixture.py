"""h2h_fixture — additive head-to-head table.

Revision ID: 0004_h2h_fixture
Revises: 0003_transfer_injury_news
Create Date: 2026-05-14 01:15:00 +09:00

Adds the ``h2h_fixture`` table (`docs/spec/db-schema.md` §3.17, mirrored in
``phase-1-followup-l3.md``) plus a functional index using
``LEAST/GREATEST`` so order-independent team-pair lookups are index-served.

`downgrade()` drops the functional index then the table so the schema
reverts cleanly to revision 0003.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_h2h_fixture"
down_revision: Union[str, None] = "0003_transfer_injury_news"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "h2h_fixture",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column(
            "home_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "away_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # No FK — leagues outside the curated whitelist are valid H2H rows.
        sa.Column("league_external_id", sa.Integer()),
        sa.Column("league_name", sa.Text()),
        sa.Column("season_year", sa.Integer()),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_short", sa.Text()),
        sa.Column("goals_home", sa.SmallInteger()),
        sa.Column("goals_away", sa.SmallInteger()),
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
        sa.UniqueConstraint("external_id", name="h2h_fixture_external_id_key"),
    )
    # Functional index — order-independent pair lookups with DESC kickoff.
    op.execute(
        "CREATE INDEX h2h_pair_idx ON h2h_fixture "
        "(LEAST(home_team_id, away_team_id), "
        " GREATEST(home_team_id, away_team_id), "
        " kickoff_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS h2h_pair_idx")
    op.drop_table("h2h_fixture")

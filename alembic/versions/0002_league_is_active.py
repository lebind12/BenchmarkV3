"""league.is_active column + partial index.

Revision ID: 0002_league_is_active
Revises: 0001_initial_schema
Create Date: 2026-05-13 22:30:00 +09:00

Adds the dynamic enablement flag (`league.is_active`) per db-schema.md §3.1
and a partial index (`league_active_idx`) that only stores rows where
`is_active = true` — the hot path for "active leagues" queries.

The NOT NULL column is safe to add directly because:
  - `server_default = true` backfills all existing rows in a single statement
    on Postgres ≥ 11 (metadata-only fast path).
  - The 5 seed leagues are all active at this migration's time.

`downgrade()` drops the index then the column. `league` table itself is
preserved so the schema falls back exactly to revision 0001_initial_schema.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_league_is_active"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "league",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index(
        "league_active_idx",
        "league",
        ["is_active"],
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("league_active_idx", table_name="league")
    op.drop_column("league", "is_active")

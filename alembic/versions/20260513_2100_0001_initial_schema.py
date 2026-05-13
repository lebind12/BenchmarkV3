"""Initial schema — 13 tables (Phase 1).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-13 21:00:00 +09:00

Defines the 13 tables specified in ``docs/spec/db-schema.md`` §3:

    league, league_translation, venue, team, team_translation, team_season,
    player, player_translation, player_season_stat, fixture, fixture_detail,
    standings, app_user

Plus the indexes / CHECK / UNIQUE / FK actions catalogued in §3, §4, §7.

`downgrade()` drops them all in reverse FK-dependency order so that integration
test I-28 (`alembic downgrade base`) succeeds.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # -- 1. league ----------------------------------------------------------
    op.create_table(
        "league",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.Text()),
        sa.Column("country_name", sa.Text()),
        sa.Column("country_code", sa.Text()),
        sa.Column("country_flag", sa.Text()),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("current_season", sa.Integer()),
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
        sa.UniqueConstraint("external_id", name="league_external_id_key"),
        sa.UniqueConstraint("slug", name="league_slug_key"),
        sa.CheckConstraint("type IN ('League', 'Cup')", name="league_type_check"),
    )
    op.create_index("league_type_idx", "league", ["type"])

    # -- 2. league_translation ---------------------------------------------
    op.create_table(
        "league_translation",
        sa.Column(
            "league_id",
            sa.BigInteger(),
            sa.ForeignKey("league.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name_ko", sa.Text()),
        sa.Column("short_name_ko", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -- 3. venue ----------------------------------------------------------
    op.create_table(
        "venue",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer()),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("capacity", sa.Integer()),
        sa.Column("surface", sa.Text()),
        sa.Column("address", sa.Text()),
        sa.Column("image_url", sa.Text()),
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
        sa.UniqueConstraint("external_id", name="venue_external_id_key"),
    )

    # -- 4. team -----------------------------------------------------------
    op.create_table(
        "team",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("founded", sa.Integer()),
        sa.Column(
            "is_national",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("logo_url", sa.Text()),
        sa.Column(
            "venue_id",
            sa.BigInteger(),
            sa.ForeignKey("venue.id", ondelete="SET NULL"),
        ),
        sa.Column("slug", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("external_id", name="team_external_id_key"),
        sa.UniqueConstraint("slug", name="team_slug_key"),
    )
    op.create_index("team_country_idx", "team", ["country"])
    op.create_index("team_venue_idx", "team", ["venue_id"])

    # -- 5. team_translation ----------------------------------------------
    op.create_table(
        "team_translation",
        sa.Column(
            "team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name_ko", sa.Text()),
        sa.Column("short_name_ko", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -- 6. team_season ----------------------------------------------------
    op.create_table(
        "team_season",
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("team_id", "league_id", "season_year"),
    )
    op.create_index(
        "team_season_league_year_idx",
        "team_season",
        ["league_id", "season_year"],
    )

    # -- 7. player ---------------------------------------------------------
    op.create_table(
        "player",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("firstname", sa.Text()),
        sa.Column("lastname", sa.Text()),
        sa.Column("age", sa.SmallInteger()),
        sa.Column("birth_date", sa.Date()),
        sa.Column("birth_place", sa.Text()),
        sa.Column("birth_country", sa.Text()),
        sa.Column("nationality", sa.Text()),
        sa.Column("height_cm", sa.SmallInteger()),
        sa.Column("weight_kg", sa.SmallInteger()),
        sa.Column(
            "injured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("photo_url", sa.Text()),
        sa.Column(
            "current_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
        ),
        sa.Column("slug", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("external_id", name="player_external_id_key"),
        sa.UniqueConstraint("slug", name="player_slug_key"),
    )
    op.create_index("player_team_idx", "player", ["current_team_id"])
    op.create_index("player_nationality_idx", "player", ["nationality"])

    # -- 8. player_translation --------------------------------------------
    op.create_table(
        "player_translation",
        sa.Column(
            "player_id",
            sa.BigInteger(),
            sa.ForeignKey("player.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name_ko", sa.Text()),
        sa.Column("short_name_ko", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -- 9. player_season_stat --------------------------------------------
    op.create_table(
        "player_season_stat",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "player_id",
            sa.BigInteger(),
            sa.ForeignKey("player.id", ondelete="CASCADE"),
            nullable=False,
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
        sa.Column("position", sa.Text()),
        sa.Column("shirt_number", sa.SmallInteger()),
        sa.Column("appearances", sa.SmallInteger()),
        sa.Column("minutes", sa.Integer()),
        sa.Column("rating", sa.Numeric(4, 2)),
        sa.Column("goals", sa.SmallInteger()),
        sa.Column("assists", sa.SmallInteger()),
        sa.Column("yellow_cards", sa.SmallInteger()),
        sa.Column("red_cards", sa.SmallInteger()),
        sa.Column("raw_stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "player_id",
            "team_id",
            "league_id",
            "season_year",
            name="player_season_stat_uniq",
        ),
    )
    op.create_index(
        "player_season_stat_player_idx", "player_season_stat", ["player_id"]
    )
    op.create_index(
        "player_season_stat_team_year_idx",
        "player_season_stat",
        ["team_id", "season_year"],
    )
    # Topscorer ranking — goals DESC per spec §3.9.
    op.execute(
        "CREATE INDEX player_season_stat_topscorer_idx "
        "ON player_season_stat (league_id, season_year, goals DESC)"
    )

    # -- 10. fixture -------------------------------------------------------
    op.create_table(
        "fixture",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column(
            "league_id",
            sa.BigInteger(),
            sa.ForeignKey("league.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Text()),
        sa.Column(
            "home_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "away_team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "venue_id",
            sa.BigInteger(),
            sa.ForeignKey("venue.id", ondelete="SET NULL"),
        ),
        sa.Column("referee", sa.Text()),
        sa.Column("timezone", sa.Text()),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timestamp_unix", sa.BigInteger()),
        sa.Column("status_long", sa.Text()),
        sa.Column("status_short", sa.Text(), nullable=False),
        sa.Column("status_elapsed", sa.SmallInteger()),
        sa.Column("period_first", sa.BigInteger()),
        sa.Column("period_second", sa.BigInteger()),
        sa.Column("goals_home", sa.SmallInteger()),
        sa.Column("goals_away", sa.SmallInteger()),
        sa.Column("score_ht_home", sa.SmallInteger()),
        sa.Column("score_ht_away", sa.SmallInteger()),
        sa.Column("score_ft_home", sa.SmallInteger()),
        sa.Column("score_ft_away", sa.SmallInteger()),
        sa.Column("score_et_home", sa.SmallInteger()),
        sa.Column("score_et_away", sa.SmallInteger()),
        sa.Column("score_pen_home", sa.SmallInteger()),
        sa.Column("score_pen_away", sa.SmallInteger()),
        sa.Column("home_winner", sa.Boolean()),
        sa.Column("away_winner", sa.Boolean()),
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
        sa.UniqueConstraint("external_id", name="fixture_external_id_key"),
    )
    op.create_index(
        "fixture_league_season_idx", "fixture", ["league_id", "season_year"]
    )
    op.create_index("fixture_kickoff_idx", "fixture", ["kickoff_at"])
    op.create_index("fixture_status_idx", "fixture", ["status_short"])
    op.create_index("fixture_home_team_idx", "fixture", ["home_team_id"])
    op.create_index("fixture_away_team_idx", "fixture", ["away_team_id"])

    # -- 11. fixture_detail ------------------------------------------------
    op.create_table(
        "fixture_detail",
        sa.Column(
            "fixture_id",
            sa.BigInteger(),
            sa.ForeignKey("fixture.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("statistics", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("lineups", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -- 12. standings -----------------------------------------------------
    op.create_table(
        "standings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "league_id",
            sa.BigInteger(),
            sa.ForeignKey("league.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column(
            "team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("group_name", sa.Text()),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("points", sa.SmallInteger(), nullable=False),
        sa.Column("played", sa.SmallInteger(), nullable=False),
        sa.Column("win", sa.SmallInteger(), nullable=False),
        sa.Column("draw", sa.SmallInteger(), nullable=False),
        sa.Column("loss", sa.SmallInteger(), nullable=False),
        sa.Column("goals_for", sa.SmallInteger(), nullable=False),
        sa.Column("goals_against", sa.SmallInteger(), nullable=False),
        sa.Column("goals_diff", sa.SmallInteger()),
        sa.Column("form", sa.Text()),
        sa.Column("status", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("home_away_breakdown", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Functional UNIQUE index — NULL group_name still collides via COALESCE.
    op.execute(
        "CREATE UNIQUE INDEX standings_uniq "
        "ON standings (league_id, season_year, team_id, COALESCE(group_name, ''))"
    )
    op.create_index(
        "standings_league_season_rank_idx",
        "standings",
        ["league_id", "season_year", "rank"],
    )

    # -- 13. app_user ------------------------------------------------------
    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'USER'"),
        ),
        sa.Column("nickname", sa.Text()),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint("email", name="app_user_email_key"),
        sa.CheckConstraint(
            "role IN ('USER', 'STREAMER', 'ADMIN')", name="app_user_role_check"
        ),
    )
    op.create_index("app_user_role_idx", "app_user", ["role"])


# ---------------------------------------------------------------------------
# downgrade — reverse FK dependency order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_index("app_user_role_idx", table_name="app_user")
    op.drop_table("app_user")

    op.drop_index("standings_league_season_rank_idx", table_name="standings")
    op.execute("DROP INDEX IF EXISTS standings_uniq")
    op.drop_table("standings")

    op.drop_table("fixture_detail")

    op.drop_index("fixture_away_team_idx", table_name="fixture")
    op.drop_index("fixture_home_team_idx", table_name="fixture")
    op.drop_index("fixture_status_idx", table_name="fixture")
    op.drop_index("fixture_kickoff_idx", table_name="fixture")
    op.drop_index("fixture_league_season_idx", table_name="fixture")
    op.drop_table("fixture")

    op.execute("DROP INDEX IF EXISTS player_season_stat_topscorer_idx")
    op.drop_index(
        "player_season_stat_team_year_idx", table_name="player_season_stat"
    )
    op.drop_index(
        "player_season_stat_player_idx", table_name="player_season_stat"
    )
    op.drop_table("player_season_stat")

    op.drop_table("player_translation")

    op.drop_index("player_nationality_idx", table_name="player")
    op.drop_index("player_team_idx", table_name="player")
    op.drop_table("player")

    op.drop_index("team_season_league_year_idx", table_name="team_season")
    op.drop_table("team_season")

    op.drop_table("team_translation")

    op.drop_index("team_venue_idx", table_name="team")
    op.drop_index("team_country_idx", table_name="team")
    op.drop_table("team")

    op.drop_table("venue")

    op.drop_table("league_translation")

    op.drop_index("league_type_idx", table_name="league")
    op.drop_table("league")

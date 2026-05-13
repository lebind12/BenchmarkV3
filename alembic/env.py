"""alembic env.

We rely on:
  - ``app.core.config.get_settings().database_url`` as the canonical URL
    (env var ``DATABASE_URL`` overrides via pydantic-settings).
  - ``app.models.Base.metadata`` as autogenerate target.
The integration test harness (``tests/integration/test_db_schema_migration.py``)
passes ``options=-csearch_path=<schema>`` in the URL to keep DDL inside the
isolated schema.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.models import Base  # noqa: F401 — registers all 13 tables on metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer env (DATABASE_URL or SQLALCHEMY_DATABASE_URL) → settings → alembic.ini.
db_url = (
    os.environ.get("SQLALCHEMY_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or get_settings().database_url
)

# Normalise libpq-style URLs to the psycopg3 dialect we ship in pyproject.
# Supabase / GH Secrets typically expose `postgresql://...` which SQLAlchemy
# would route to psycopg2 (not installed). Rewriting here keeps env files
# untouched and applies uniformly to integration tests + prod migrations.
if db_url.startswith("postgresql://"):
    db_url = "postgresql+psycopg://" + db_url[len("postgresql://"):]
elif db_url.startswith("postgres://"):
    db_url = "postgresql+psycopg://" + db_url[len("postgres://"):]

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

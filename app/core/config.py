"""Application settings (pydantic-settings).

Loaded once at import; used by FastAPI, alembic, and workers. Values come
from ``.env`` (local) or process env (Koyeb / CI). Real secrets are never
checked in — see ``.env.example``.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised env-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database ---------------------------------------------------------
    # Supabase Postgres URL (or any libpq URL). alembic also reads this via
    # `app.core.config.get_settings().database_url`.
    database_url: str = Field(
        default="postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder",
        description="Primary DB URL (Supabase / local).",
    )

    # Integration test DB URL (separate from prod). Conftest skips integration
    # tests if unset.
    test_database_url: str | None = Field(default=None)

    # --- External APIs ----------------------------------------------------
    api_football_key: str | None = Field(default=None)
    api_football_host: str = Field(default="v3.football.api-sports.io")

    # --- Cache / session helpers ------------------------------------------
    upstash_redis_rest_url: str | None = Field(default=None)
    upstash_redis_rest_token: str | None = Field(default=None)

    # --- OpenAI (translation-filler) --------------------------------------
    openai_api_key: str | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor. ``lru_cache`` keeps env parsing one-shot per process."""
    return Settings()

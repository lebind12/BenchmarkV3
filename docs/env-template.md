# Environment variables template

Copy the block below into a local `.env` (gitignored) and fill real values.
This file lives under `docs/` because dot-files starting with `.env` are
blocked by the agent sandbox; the canonical SSOT is right here.

```dotenv
# --- Database ---
# Supabase: settings -> Database -> Connection string -> URI (pooled, ?sslmode=require).
# SQLAlchemy + psycopg3 form:
#   postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres

# Optional: separate DB used by `pytest -m integration`. If unset, integration
# tests are skipped via conftest guard.
TEST_DATABASE_URL=

# --- API-Football (Ultra plan) ---
API_FOOTBALL_KEY=
API_FOOTBALL_HOST=v3.football.api-sports.io

# --- Upstash Redis (refresh token rotation / blacklist) ---
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# --- OpenAI (translation-filler) ---
OPENAI_API_KEY=
```

## Notes

- `DATABASE_URL` is read by `app/core/config.py` (pydantic-settings) and by
  alembic's `env.py` (with `SQLALCHEMY_DATABASE_URL` taking priority for
  per-run overrides — see integration test fixture).
- `pydantic-settings` lower-cases env keys; `DATABASE_URL` → `database_url`.
- For the integration test runner only, `TEST_DATABASE_URL` must point at a
  Postgres where it is safe to `CREATE SCHEMA test_*` and `DROP` them.

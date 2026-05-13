"""Background workers (daily-sync, translation-filler, …).

Each worker is a sub-package under this namespace. See `docs/workers/` for
specs. Workers are designed to be importable without side effects so tests
can drive a single cycle in-process.
"""

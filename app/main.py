"""FastAPI application entrypoint.

Phase 0 scaffold: only exposes `/health` for liveness verification. Real
endpoints arrive in later phases per `Plans.md`.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="benchmark API",
    description="축구 정보 사이트 백엔드 (방송용 페이지 포함).",
    version="0.0.0",
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe used by Koyeb / load balancer health checks."""
    return {"status": "ok"}

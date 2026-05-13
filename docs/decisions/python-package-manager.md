# Decision: Python package manager

- **선택**: `pyproject.toml` (PEP 621) + `pip` 기본. `uv` 사용 권장하되 강제 아님.
- **사유**: pyproject.toml 은 모든 모던 도구 (pip, uv, poetry, hatch) 의 공통 입력이므로 lock-in 회피. `requirements.txt` 는 pip-only 환경 호환용 fallback 으로 병행 유지. lockfile (uv.lock / poetry.lock) 은 Phase 0 완료 후 의존성 안정화되면 도입.
- **결정일**: 2026-05-13 / be-dev

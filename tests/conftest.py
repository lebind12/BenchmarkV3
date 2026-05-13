"""공용 pytest fixtures.

- 통합 테스트는 환경변수 `TEST_DATABASE_URL` 의 Postgres 에 임시 schema 를
  `test_<run_id>_<endpoint>` 형태로 생성해서 격리한다.
- prod (public) schema 접근 금지. 테스트는 격리 schema 안에서만 동작.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Iterator

import pytest


def _make_run_id() -> str:
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"


def _normalize_driver(url: str) -> str:
    """SQLAlchemy 가 명시적 psycopg v3 dialect 를 쓰도록 prefix 보정.

    프로젝트는 psycopg v3 만 dependencies 에 포함. .env 가 `postgresql://` 로 와도
    `postgresql+psycopg://` 로 바꿔서 psycopg2 import error 를 피한다.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        # 환경 가드: 격리 schema 를 만들 실 Postgres 가 없으면 통합 테스트만 skip.
        # 정책 정본: docs/spec/endpoints/phase-1-db-schema.testplan.md §1,
        # docs/spec/agent-workflow.md §8 (외부 의존성 mock 정책).
        # 테스트 로직 자체를 무력화하는 것이 아니라 환경 부재 시의 정상 동작.
        pytest.skip("TEST_DATABASE_URL 미설정 — 통합 테스트 skip (환경 가드)")
    return _normalize_driver(url)


@pytest.fixture(scope="session")
def run_id() -> str:
    return _make_run_id()


@pytest.fixture(scope="function")
def isolated_db(test_database_url, run_id, request) -> Iterator[tuple[object, str]]:
    """함수 단위 격리 schema 를 만들고 (engine, schema_name) 반환.

    schema 이름: `test_<run_id>_<endpoint_key>` (be-test.md §3 규칙, postgres
    identifier 63자 제한 내).

    반환된 engine 은 모든 connection 이 자동으로 해당 schema 를 search_path 로
    가지도록 `options=-csearch_path=<schema>` 가 connect_args 에 박혀 있다.
    bootstrap (schema 생성/삭제) 은 별도의 default-search_path engine 으로 한다.
    """
    from sqlalchemy import create_engine, text

    endpoint_key = request.module.__name__.split(".")[-1].replace("test_", "")[:40]
    schema_name = f"test_{run_id}_{endpoint_key}"
    schema_name = schema_name[:60]  # postgres identifier max 63

    from sqlalchemy import event

    bootstrap = create_engine(test_database_url, future=True)
    with bootstrap.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    # search_path 를 매 connection 마다 적용. Supabase pooler 가 libpq `options`
    # 를 통과시키지 않는 경우가 있어, 명시적 `SET search_path` 을 connect 이벤트
    # 에 후킹한다.
    test_engine = create_engine(test_database_url, future=True)

    @event.listens_for(test_engine, "connect")
    def _set_search_path(dbapi_conn, _conn_record):
        cur = dbapi_conn.cursor()
        try:
            cur.execute(f'SET search_path TO "{schema_name}"')
        finally:
            cur.close()
    try:
        yield test_engine, schema_name
    finally:
        test_engine.dispose()
        with bootstrap.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        bootstrap.dispose()

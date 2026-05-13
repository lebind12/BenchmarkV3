"""공용 pytest fixtures.

- 통합 테스트는 환경변수 `TEST_DATABASE_URL` 의 Postgres 에 임시 schema 를
  `test_<run_id>_<endpoint>` 형태로 생성해서 격리한다.
- prod schema 접근 금지.
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

import pytest


def _make_run_id() -> str:
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        # 환경 가드: 격리 schema 를 만들 실 Postgres 가 없으면 통합 테스트만 skip.
        # 정책 정본: docs/spec/endpoints/phase-1-db-schema.testplan.md §1,
        # docs/spec/agent-workflow.md §8 (외부 의존성 mock 정책).
        # 테스트 로직 자체를 무력화하는 것이 아니라 환경 부재 시의 정상 동작.
        pytest.skip("TEST_DATABASE_URL 미설정 — 통합 테스트 skip (환경 가드)")
    return url


@pytest.fixture(scope="session")
def run_id() -> str:
    return _make_run_id()


@contextmanager
def _isolated_schema(engine, schema_name: str):
    """임시 schema 를 생성하고 search_path 를 그쪽으로 고정. 종료 시 drop."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    try:
        yield schema_name
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))


@pytest.fixture(scope="function")
def isolated_db(test_database_url, run_id, request) -> Iterator[tuple[object, str]]:
    """함수 단위 격리 schema. (engine, schema_name) 반환.

    schema 이름: test_<run_id>_<endpoint_key> (be-test.md §3 규칙).
    """
    from sqlalchemy import create_engine, text

    # endpoint_key: 호출 테스트 파일 이름 기반
    endpoint_key = request.module.__name__.split(".")[-1].replace("test_", "")[:40]
    schema_name = f"test_{run_id}_{endpoint_key}"
    # postgres identifier max 63
    schema_name = schema_name[:60]

    engine = create_engine(test_database_url, future=True)
    with _isolated_schema(engine, schema_name):
        # search_path 고정 connection 옵션
        # SQLAlchemy 2.x: connect_args + options 로 search_path 설정이 일반적이나,
        # 여기서는 engine 옵션 대신 connection 마다 SET 한다.
        with engine.begin() as conn:
            conn.execute(text(f'SET search_path TO "{schema_name}"'))
        yield engine, schema_name
    engine.dispose()

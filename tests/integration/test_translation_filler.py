"""W1 — translation-filler 통합 테스트.

격리 schema 에 마이그레이션 적용 후 실 Postgres + mock OpenAI 로 워커 1 사이클을
실행한다. OpenAI 실 호출 금지 (CLAUDE.md §11 비용 정책 + agent-workflow.md §8).

be-dev 가 `app/workers/translation_filler/` 와 의존 인터페이스를 작성하기 전까지
ImportError 로 fail (TDD Red 정상).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_alembic(args: list[str], schema: str, db_url: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    existing = env.get("PGOPTIONS", "")
    env["PGOPTIONS"] = f"-c search_path={schema} {existing}".strip()
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=_project_root(),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture(scope="function")
def migrated_db(isolated_db, test_database_url):
    engine, schema = isolated_db
    result = _run_alembic(["upgrade", "head"], schema=schema, db_url=test_database_url)
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head 실패 (schema={schema})\n{result.stdout}\n{result.stderr}"
        )
    return engine, schema


# ---------------------------------------------------------------------------
# 헬퍼: 큐 row INSERT
# ---------------------------------------------------------------------------

def _insert_player_with_null_translation(conn, *, external_id, name, nationality="England"):
    pid = conn.execute(
        text(
            "INSERT INTO player (external_id, name, slug, nationality) "
            "VALUES (:e, :n, :s, :nat) RETURNING id"
        ),
        {"e": external_id, "n": name, "s": f"player-{external_id}", "nat": nationality},
    ).scalar()
    conn.execute(
        text("INSERT INTO player_translation (player_id) VALUES (:p)"),
        {"p": pid},
    )
    return pid


def _insert_team_with_null_translation(conn, *, external_id, name, country="England"):
    tid = conn.execute(
        text(
            "INSERT INTO team (external_id, name, slug, country) "
            "VALUES (:e, :n, :s, :c) RETURNING id"
        ),
        {"e": external_id, "n": name, "s": f"team-{external_id}", "c": country},
    ).scalar()
    conn.execute(
        text("INSERT INTO team_translation (team_id) VALUES (:t)"),
        {"t": tid},
    )
    return tid


def _make_fake_openai_client(response: dict | str | Exception):
    """OpenAI client mock 생성. response 가 dict 면 정상 JSON, str 이면 그대로, Exception 이면 raise."""
    fake = MagicMock()
    if isinstance(response, Exception):
        fake.chat.completions.create = AsyncMock(side_effect=response)
    else:
        import json as _json
        content = response if isinstance(response, str) else _json.dumps(response, ensure_ascii=False)
        fake.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content=content))])
        )
    return fake


# ---------------------------------------------------------------------------
# TF-I-01 5 row 정상 처리
# ---------------------------------------------------------------------------

def test_tf_i01_five_rows_normal_path(migrated_db):
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        for i in range(3):
            _insert_player_with_null_translation(conn, external_id=1000 + i, name=f"Player {i}")
        for i in range(2):
            _insert_team_with_null_translation(conn, external_id=2000 + i, name=f"Team {i}")

    fake = _make_fake_openai_client({"name_ko": "한글", "short_name_ko": "약"})

    with Session(engine) as session:
        asyncio.run(run_cycle(session, openai_client=fake))

    with engine.connect() as conn:
        unfilled = conn.execute(
            text(
                "SELECT COUNT(*) FROM player_translation WHERE name_ko IS NULL "
                "UNION ALL SELECT COUNT(*) FROM team_translation WHERE name_ko IS NULL"
            )
        ).all()
    assert sum(r[0] for r in unfilled) == 0, "정상 응답 후 NULL row 가 남음"
    assert fake.chat.completions.create.call_count == 5


# ---------------------------------------------------------------------------
# TF-I-02 빈 큐 즉시 종료
# ---------------------------------------------------------------------------

def test_tf_i02_empty_queue_no_openai_call(migrated_db):
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    fake = _make_fake_openai_client({"name_ko": "X", "short_name_ko": "X"})
    with Session(engine) as session:
        asyncio.run(run_cycle(session, openai_client=fake))
    fake.chat.completions.create.assert_not_called()


# ---------------------------------------------------------------------------
# TF-I-03 OpenAI 5xx → 재시도 → row skip
# ---------------------------------------------------------------------------

def test_tf_i03_openai_5xx_row_skipped_after_retries(migrated_db):
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_player_with_null_translation(conn, external_id=9001, name="Retry P")

    fake = _make_fake_openai_client(Exception("simulated OpenAI 5xx"))

    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with Session(engine) as session, patch("asyncio.sleep", side_effect=fake_sleep):
        asyncio.run(run_cycle(session, openai_client=fake))

    with engine.connect() as conn:
        nk = conn.execute(
            text("SELECT name_ko FROM player_translation WHERE player_id=(SELECT id FROM player WHERE external_id=9001)")
        ).scalar()
    assert nk is None, "5xx 3회 실패 후 row 가 채워지면 안 됨"
    # 1+2+4 백오프 시퀀스 확인
    assert [s for s in sleeps if s in (1, 2, 4)][:3] == [1, 2, 4]


# ---------------------------------------------------------------------------
# TF-I-04 JSON 깨짐
# ---------------------------------------------------------------------------

def test_tf_i04_broken_json_row_skipped(migrated_db):
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        _insert_player_with_null_translation(conn, external_id=9002, name="Broken P")

    fake = _make_fake_openai_client("this is not json")
    with Session(engine) as session:
        asyncio.run(run_cycle(session, openai_client=fake))

    with engine.connect() as conn:
        nk = conn.execute(
            text("SELECT name_ko FROM player_translation WHERE player_id=(SELECT id FROM player WHERE external_id=9002)")
        ).scalar()
    assert nk is None, "JSON 깨짐 시 row 가 채워지면 안 됨"


# ---------------------------------------------------------------------------
# TF-I-05 멱등성
# ---------------------------------------------------------------------------

def test_tf_i05_idempotent_already_filled_row_not_called(migrated_db):
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        pid = _insert_player_with_null_translation(conn, external_id=9003, name="Filled P")
        conn.execute(
            text(
                "UPDATE player_translation SET name_ko='기존', short_name_ko='기' "
                "WHERE player_id=:p"
            ),
            {"p": pid},
        )

    fake = _make_fake_openai_client({"name_ko": "새거", "short_name_ko": "새"})
    with Session(engine) as session:
        asyncio.run(run_cycle(session, openai_client=fake))

    fake.chat.completions.create.assert_not_called()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name_ko, short_name_ko FROM player_translation WHERE player_id=:p"),
            {"p": pid},
        ).first()
    assert row.name_ko == "기존" and row.short_name_ko == "기"


# ---------------------------------------------------------------------------
# TF-I-06 보호: name_ko 만 NULL 인 row 도 채워진 short_name_ko 는 보호
# ---------------------------------------------------------------------------

def test_tf_i06_partial_filled_protects_existing_value(migrated_db):
    """short_name_ko 가 이미 있고 name_ko 만 NULL 인 경우, 워커가 채울 수 있지만
    기존 short_name_ko 를 덮어쓰면 안 된다.
    """
    from app.workers.translation_filler.runner import run_cycle

    engine, _ = migrated_db
    with engine.begin() as conn:
        pid = _insert_player_with_null_translation(conn, external_id=9004, name="Half P")
        conn.execute(
            text("UPDATE player_translation SET short_name_ko='기존약' WHERE player_id=:p"),
            {"p": pid},
        )

    fake = _make_fake_openai_client({"name_ko": "새이름", "short_name_ko": "새약"})
    with Session(engine) as session:
        asyncio.run(run_cycle(session, openai_client=fake))

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name_ko, short_name_ko FROM player_translation WHERE player_id=:p"),
            {"p": pid},
        ).first()
    # name_ko 는 새로 채워지지만 short_name_ko 는 보존
    assert row.name_ko == "새이름"
    assert row.short_name_ko == "기존약", (
        "이미 채워진 short_name_ko 를 덮어쓰면 안 됨 (멱등성 보호)"
    )


# ---------------------------------------------------------------------------
# TF-I-07 1분 폴링 스케줄러 진입점
# ---------------------------------------------------------------------------

def test_tf_i07_scheduler_registers_one_minute_job(migrated_db):
    """스케줄러 모듈이 1분 주기로 run_cycle 을 등록하는지 검증.

    실 1분 대기 금지. mock APScheduler 또는 등록 함수 호출 인자 검증.
    """
    from app.workers.translation_filler import scheduler

    fake_scheduler = MagicMock()
    # 일반적 컨벤션: scheduler.register(scheduler_obj) 또는 add_job
    if hasattr(scheduler, "register"):
        scheduler.register(fake_scheduler)
    elif hasattr(scheduler, "add_jobs"):
        scheduler.add_jobs(fake_scheduler)
    else:
        pytest.fail(
            "translation_filler.scheduler 에 register / add_jobs 함수가 없음. "
            "1분 주기 entry 등록 인터페이스 필요"
        )

    # add_job 이 호출됐는지 + 1분 주기 인자
    assert fake_scheduler.add_job.called, "scheduler.add_job 미호출 — 1분 작업 등록 필요"
    blob = repr(fake_scheduler.add_job.call_args)
    assert any(
        k in blob for k in ("minutes=1", "seconds=60", "'interval'", '"interval"')
    ), f"1분 폴링 주기 인자 누락: {blob}"

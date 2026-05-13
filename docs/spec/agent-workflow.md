# Agent Workflow — Backend Endpoint Lifecycle

백엔드 API endpoint 1개의 라이프사이클을 3개 에이전트 (test / dev / reviewer) 와 사람으로 처리하기 위한 상태 머신, 핸드오프 스키마, 게이트 정책의 SSOT.

## 1. 에이전트 역할 요약

| 에이전트 | 역할 | 권한 (도구) | 권한 (git) |
|---|---|---|---|
| **be-test** | 요구사항 + 테스트 플랜 + 테스트 코드 작성, 테스트 실행 | Read, Write (테스트/스펙 디렉토리만), Bash (pytest, alembic), Glob, Grep | branch 생성 / commit (테스트 파일 한정) / push |
| **be-dev** | 구현 (모델, 라우터, 비즈니스, 마이그레이션), 마이그레이션 작성 | Read, Write (app/, alembic/ 전체), Edit, Bash, Glob, Grep | branch / commit / push, **prod DB 접속 금지** |
| **be-reviewer** | 코드 리뷰, 게이트 판정 (APPROVE / REQUEST_CHANGES) | Read, Grep, Glob, Bash (read-only) | commit/push **불가**. PR comment 만 |

원칙: 각 에이전트는 endpoint 1개에 대해 1 worktree 안에서 turn-taking. 동시에 같은 worktree 를 쓰지 않는다.

## 2. 상태 머신

```
                                  ┌────────────────────┐
                                  │   SPEC_FAILED      │ ← reviewer 가 spec 자체 거절
                                  └──────┬─────────────┘
                                         │ 사람 결정
                                         ↓
 FE_REQUESTED ─→ SPEC_DRAFTING ─→ SPEC_REVIEW ─→ SPEC_APPROVED
       (외부)        (be-test)        (be-reviewer)
                                              ↓
                                       IMPL_IN_PROGRESS ←──────────┐
                                              (be-dev)             │
                                              ↓                    │
                                       IMPL_PUSHED                 │
                                              ↓                    │
                                       TESTING (be-test)           │
                                              │                    │
                                  ┌───────────┴────────┐           │
                              실패│                  통과│           │
                                  ↓                    ↓           │
                          TEST_FAILED         REVIEW_PENDING       │
                          (재시도 ≤3)            (be-reviewer)     │
                                  └─→ IMPL_IN_PROGRESS              │
                                                       ↓           │
                                          ┌────────────┴─────────┐ │
                                       APPROVE              REQUEST_CHANGES
                                          ↓                       ↓
                                       MERGE_GATE          CHANGES_REQUESTED
                                          ↓               (재시도 ≤3)
                                       PR_CREATED                  │
                                          ↓                        │
                                       (사람 또는 자동)              └→ IMPL_IN_PROGRESS
                                       MERGED

                          재시도 한도 초과 / spec 충돌 / 보안 변경
                                          ↓
                                       ESCALATED (사람 결정 필요)
```

### 2.1 상태 정의

| 상태 | 의미 | 다음 상태 | 트리거 |
|---|---|---|---|
| `FE_REQUESTED` | FE 가 endpoint 를 mockup + 요구사항으로 요청함 | `SPEC_DRAFTING` | be-test 가 receive |
| `SPEC_DRAFTING` | be-test 가 spec + test plan + test 코드 작성 중 | `SPEC_REVIEW` | be-test 가 produce 완료 |
| `SPEC_REVIEW` | be-reviewer 가 spec 검토 | `SPEC_APPROVED`, `SPEC_FAILED` | be-reviewer 판정 |
| `SPEC_APPROVED` | spec 승인됨. dev 작업 시작 가능 | `IMPL_IN_PROGRESS` | be-dev 가 start |
| `SPEC_FAILED` | spec 자체가 문제 (spec SSOT 충돌, 명세 부족 등) | ESCALATED | 사람 결정 후 SPEC_DRAFTING 으로 복귀 |
| `IMPL_IN_PROGRESS` | be-dev 가 구현 중 | `IMPL_PUSHED` | be-dev 가 push 완료 |
| `IMPL_PUSHED` | 구현 commit 이 worktree 브랜치에 올라감 | `TESTING` | be-test 가 자동 진입 |
| `TESTING` | be-test 가 단위 + 통합 테스트 실행 | `TEST_FAILED`, `REVIEW_PENDING` | 테스트 결과 |
| `TEST_FAILED` | 테스트 실패. 카운트 증가 | `IMPL_IN_PROGRESS` (재시도) 또는 `ESCALATED` | test_loop ≤ 3 ? |
| `REVIEW_PENDING` | 테스트 통과, reviewer 가 코드 검토 중 | `MERGE_GATE`, `CHANGES_REQUESTED` | be-reviewer 판정 |
| `CHANGES_REQUESTED` | reviewer 가 수정 요구. 카운트 증가 | `IMPL_IN_PROGRESS` 또는 `ESCALATED` | review_loop ≤ 3 ? |
| `MERGE_GATE` | 머지 게이트 검증 (커버리지, 보안 영역 검사 등) | `PR_CREATED` 또는 `ESCALATED` | 전 게이트 통과 ? |
| `PR_CREATED` | `be-ep-* → backend` PR 생성됨 | `MERGED` | 자동 또는 사람 머지 |
| `MERGED` | backend 브랜치 머지 완료 | (종료) | git push 완료 |
| `ESCALATED` | 사람 개입 필요 | (사람 결정) | - |

### 2.2 재시도 한도

- `test_loop` (TEST_FAILED → IMPL_IN_PROGRESS): 최대 3회
- `review_loop` (CHANGES_REQUESTED → IMPL_IN_PROGRESS): 최대 3회
- 한도 초과 → `ESCALATED`

## 3. 핸드오프: 상태 파일

위치: `.claude/state/endpoint-flow/<endpoint_id>.json`

```jsonc
{
  "endpoint_id": "GET__api_v1_fixtures",
  "endpoint": {
    "method": "GET",
    "path": "/api/v1/fixtures",
    "fe_mockup_ref": "frontend/mocks/fixtures.json"
  },
  "state": "REVIEW_PENDING",
  "owner": "be-reviewer",
  "iteration": {
    "test_loop": 1,
    "review_loop": 0
  },
  "artifacts": {
    "spec_path": "docs/spec/endpoints/fixtures-get.md",
    "test_plan_path": "docs/spec/endpoints/fixtures-get.testplan.md",
    "test_code_path": "tests/integration/test_fixtures_get.py",
    "impl_branch": "be-ep-fixtures-get",
    "impl_commit": "abc1234",
    "migrations": ["alembic/versions/20260513_add_fixtures.py"]
  },
  "evidence": {
    "unit_test_log": ".claude/state/endpoint-flow/GET__api_v1_fixtures/unit.log",
    "integration_test_log": ".claude/state/endpoint-flow/GET__api_v1_fixtures/integration.log",
    "test_verdict": "PASS",
    "coverage_pct": 92.4
  },
  "gates": {
    "spec_approved_by": "be-reviewer",
    "test_passed_at": "2026-05-13T18:30:00+09:00",
    "review_approved_by": null,
    "merge_approved_by": null
  },
  "blockers": [],
  "next_action": {
    "agent": "be-reviewer",
    "command": "code review on impl_commit abc1234 vs spec_path"
  }
}
```

history (append-only): `.claude/state/endpoint-flow/<endpoint_id>.history.jsonl`
- 한 줄 = 한 전환: `{"ts":"...","from":"...","to":"...","by":"<agent>","note":"..."}`

## 4. 머지 게이트 (`MERGE_GATE` 통과 조건)

다음 6개를 **모두** 만족해야 PR 자동 생성 및 머지 가능:

1. 단위 테스트 통과: `pytest -m unit` exit 0
2. 통합 테스트 통과: `pytest -m integration` exit 0 (격리 schema 사용)
3. 커버리지 ≥ 80% (변경된 구현 파일 기준)
4. be-reviewer APPROVE: state 파일 `gates.review_approved_by != null`
5. 보안/인증/마이그레이션 영역 변경 시 **사람 승인** (자동 머지 차단, PR 만 생성)
6. CI status check 통과 (lint, type check)

조건 미충족 → `ESCALATED` 또는 직전 단계로 복귀

## 5. 마이그레이션 게이트

PR 단계에서:
- be-dev 가 마이그레이션 추가 시, 그 시점의 `alembic heads` 가 1개여야 함 (충돌 방지). 2개 이상이면 dev 가 작업 정지하고 lead 가 통합
- be-reviewer 가 PR 마다 다음 검사:
  - downgrade 스크립트 존재 여부
  - backward-compat 2-step 패턴 준수 (drop/rename 직접 X)
  - 데이터 마이그레이션은 backfill 스크립트 분리

main 머지 시:
- GH Actions 가 prod DB 에 `alembic upgrade head` 적용 (실패 시 Koyeb 배포 차단)
- service role key 는 이 잡에서만 접근 가능

## 6. 사람 개입 트리거

| 트리거 | 행동 |
|---|---|
| `test_loop ≥ 3` 또는 `review_loop ≥ 3` | `ESCALATED` 로 전이, 알림 |
| spec SSOT 충돌 발견 | `SPEC_FAILED` |
| 인증 / Role / migration 운영 적용 / 비용 임계치 초과 | `MERGE_GATE` 에서 자동 머지 차단 |
| `backend → main` PR | 항상 사람 승인 필수 |

## 7. worktree / branch 사용

- endpoint 1개 = worktree 1개 (디렉토리: `.git/worktrees/be-ep-<id>/` 또는 Harness 가 관리하는 임시 경로)
- 브랜치: `be-ep-<endpoint_id>` (`backend` 브랜치에서 분기)
- 머지 흐름: `be-ep-* → backend`, `backend → main`
- 세 에이전트 모두 같은 worktree, turn-taking

## 8. 외부 의존성 mock 정책

| 의존성 | 단위 테스트 | 통합 테스트 |
|---|---|---|
| API-Football | mock (고정 fixture JSON, git 추적) | 가능한 경우 실 호출 (rate limit 주의) |
| OpenAI (gpt-3.5-turbo) | mock | mock (비용 회피) |
| Supabase | mock (인메모리) 또는 SQLite | 실 Supabase + 격리 schema |
| Upstash | fakeredis | 실 Upstash + 키 prefix 격리 |

## 9. 상태 전환 CLI (`scripts/endpoint-flow.sh`)

```bash
# 새 endpoint 등록
endpoint-flow init <endpoint_id> --method GET --path /api/v1/foo --fe-mockup frontend/mocks/foo.json

# 상태 전환 (검증 포함)
endpoint-flow transition <endpoint_id> <new_state> --by <agent> --note "..."

# 현재 상태 조회
endpoint-flow status <endpoint_id>

# 모든 in-flight endpoint 목록
endpoint-flow list --state-filter "TESTING|REVIEW_PENDING"
```

CLI 가 보장하는 것:
- JSON Schema 검증
- 잘못된 전환 거부 (`MERGED → SPEC_DRAFTING` 등)
- history.jsonl 자동 기록
- 재시도 카운트 자동 증가

## 10. 본 문서의 위치

- 본 문서는 spec SSOT 의 일부 (`docs/spec/agent-workflow.md`).
- 에이전트 명세 (`.claude/agents/be-*.md`) 는 본 문서를 인용 (`@docs/spec/agent-workflow.md`).
- 변경 시 PR + 사람 승인 필수.

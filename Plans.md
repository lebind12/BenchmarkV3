# benchmark Plans.md

축구 정보 사이트 + 방송용 페이지. CLAUDE.md 가 도메인 SSOT, 이 파일은 작업 정본.

작성일: 2026-05-13

---

## Phase 0: 인프라

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 0.1 | Supabase 프로젝트 생성 / DB URL 발급 | `.env.example` 에 DATABASE_URL 자리. 사람이 GitHub Secrets 등록 | - | cc:TODO |
| 0.2 | Koyeb 프로젝트 생성 / 배포 토큰 발급 | GH Secrets 에 KOYEB_TOKEN 등록 | - | cc:TODO |
| 0.3 | Upstash Redis 인스턴스 생성 | `.env.example` 에 UPSTASH_REDIS_REST_URL/TOKEN 자리 | - | cc:TODO |
| 0.4 | FastAPI 골격 (uvicorn 부팅 가능) | `uvicorn app.main:app` 실행 시 `/health` 200 | - | cc:TODO |
| 0.5 | alembic 셋업 + 첫 빈 마이그레이션 | `alembic upgrade head` 가 빈 DB 에 성공 | 0.4 | cc:TODO |
| 0.6 | pytest 셋업 (unit / integration marker 분리) | `pytest -m unit` 동작 | 0.4 | cc:TODO |
| 0.7 | pydantic-settings 로 .env 로드 | `.env.example` 정리 + Settings 클래스 | 0.4 | cc:TODO |
| 0.8 | docker-compose (선택, 로컬 dev DB) [tdd:skip:infra-only] | 로컬에서 Postgres 부팅 가능 | - | cc:TODO |

## Phase 1: DB 스키마

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 1.1 | `league` 테이블 (id, external_id, name, slug, country) | 마이그레이션 적용 + 모델 매핑 테스트 통과 | 0.5 | cc:TODO |
| 1.2 | `team` 테이블 (id, external_id, name, league_id 다대다 또는 시즌별) | 모델 + 외래키 + 테스트 | 1.1 | cc:TODO |
| 1.3 | `player` 테이블 (id, external_id, eng_name, team_id, age 등) | 모델 + 테스트 | 1.2 | cc:TODO |
| 1.4 | `fixture` 테이블 (id, external_id, league_id, home_team_id, away_team_id, kickoff_at, status, score) | 모델 + 인덱스(외부 ID unique, kickoff_at) + 테스트 | 1.2 | cc:TODO |
| 1.5 | `fixture_detail` 테이블 (fixture_id, events JSON, statistics JSON, lineups JSON) | 모델 + 테스트 | 1.4 | cc:TODO |
| 1.6 | `league_translation` / `team_translation` / `player_translation` 매칭 테이블 (external_id, name_ko, short_name_ko, source, verified, updated_at) | 3 테이블 + 외부 ID unique + 테스트 | 1.1, 1.2, 1.3 | cc:TODO |
| 1.7 | `user` / `role` 테이블 (id, email, password_hash, role: USER/STREAMER/ADMIN) | 모델 + Enum role + 테스트 | 0.5 | cc:TODO |
| 1.8 | Supabase RLS 정책 결정 및 적용 | RLS on/off 결정 문서화. 적용 시 정책 SQL | 1.7 | cc:TODO |

## Phase 2: 시드 데이터

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 2.1 | 리그 5개 한글표기 결정 (이 세션, 수동) | `seeds/league_translation.csv` 생성 | - | cc:TODO |
| 2.2 | 팀 한글표기 결정 (이 세션, EPL 20 + UCL/UEL/카라바오/FA컵 본선 클럽) | `seeds/team_translation.csv` 생성 | 2.1 | cc:TODO |
| 2.3 | `_Player__202605131748.csv` → `player_translation` import 스크립트 | `scripts/seed_player_translations.py` + import 결과 row count 검증 | 1.6 | cc:TODO |
| 2.4 | league/team seed import 스크립트 | `scripts/seed_basic_translations.py` | 1.6, 2.1, 2.2 | cc:TODO |
| 2.5 | 시드 결과 무결성 점검 (중복/결측/외부 ID 유효성) | 점검 스크립트 통과 | 2.3, 2.4 | cc:TODO |

## Phase 3: 인증

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.1 | 비밀번호 해시 (bcrypt or argon2) 헬퍼 | 단위 테스트 통과 | 1.7 | cc:TODO |
| 3.2 | JWT 발급 / 검증 (access 짧은 만료) | 단위 테스트 (만료, 변조, role) | 1.7 | cc:TODO |
| 3.3 | Refresh token rotation (Upstash 저장, blacklist) | 단위 + 통합 테스트 | 3.2, 0.3 | cc:TODO |
| 3.4 | Role 검사 FastAPI Dependency (USER/STREAMER/ADMIN) | 권한 검사 단위 테스트 | 3.2 | cc:TODO |
| 3.5 | `/auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout` | 통합 테스트 (정상/오류 케이스) | 3.1-3.4 | cc:TODO |

## Phase 4: 워커 - daily-sync

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 4.1 | API-Football 클라이언트 (httpx + semaphore 6 + exp backoff retry) | 단위 테스트 (mock 응답) | 0.7 | cc:TODO |
| 4.2 | Upstash 분산 락 (SET NX + TTL) | 단위 + 통합 테스트 (동시 호출 1개만 통과) | 0.3 | cc:TODO |
| 4.3 | 리그 메타 upsert (5 리그) | 통합 테스트 (test schema) | 1.1, 4.1 | cc:TODO |
| 4.4 | fixture 적재 (5 리그, 최신 2시즌) | 통합 테스트 | 1.4, 4.1 | cc:TODO |
| 4.5 | fixture 상세 적재 | 통합 테스트 | 1.5, 4.4 | cc:TODO |
| 4.6 | team / player 메타 upsert | 통합 테스트 | 1.2, 1.3, 4.4 | cc:TODO |
| 4.7 | 컵 대회 빈 슬롯 채움 로직 (라운드 추첨 후) | 통합 테스트 | 4.4 | cc:TODO |
| 4.8 | cron 스케줄러 (KST 00/06/12/18) | 스케줄 검증 단위 테스트 + 실행 진입점 | 4.3-4.7 | cc:TODO |

## Phase 5: 워커 - translation-filler

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 5.1 | `name_ko IS NULL` 감지 쿼리 (3 매칭 테이블 통합) | 단위 테스트 | 1.6 | cc:TODO |
| 5.2 | gpt-3.5-turbo few-shot 클라이언트 (시드 CSV 에서 예시 추출) | 단위 테스트 (mock) | 2.3 | cc:TODO |
| 5.3 | 1분 폴링 스케줄 + 분산 락 + 빈 큐 조기 종료 | 단위 + 통합 테스트 | 4.2, 5.1, 5.2 | cc:TODO |

## Phase 6: (제거) live-poll 워커는 워커가 아니라 API endpoint 로 처리

방송용 페이지 라이브 데이터는 워커가 아니라 스트리머 호출 시점에 동작하는 API endpoint + Upstash 캐시 패턴으로 처리한다. Phase 8 의 일반 endpoint 로 흡수됨.

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| (구) 6.x | live-poll 워커 | (삭제됨 — Phase 8 의 라이브 endpoint task 로 이관) | - | deleted |

## Phase 7: 자동화 인프라 (에이전트 워크플로)

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 7.1 | `docs/spec/agent-workflow.md` 작성 (상태 머신 + 게이트) | 본 세션에서 생성 | - | cc:WIP |
| 7.2 | `.claude/agents/be-{test,dev,reviewer}.md` 3개 에이전트 명세 | 본 세션에서 생성 | 7.1 | cc:WIP |
| 7.3 | `.claude/schemas/endpoint-flow.schema.json` (상태 파일 JSON Schema) | schema validation 통과 | 7.1 | cc:TODO |
| 7.4 | `scripts/endpoint-flow.sh` (상태 전환 CLI) | 단위 테스트 통과 | 7.3 | cc:TODO |
| 7.5 | GH Actions: `.github/workflows/be-ep-pr.yml` (be-ep-* PR 검증) | CI 잡 성공 | 7.4 | cc:TODO |
| 7.6 | GH Actions: `.github/workflows/backend-pr.yml` (backend ← be-ep-* PR) | CI 잡 성공 | 7.5 | cc:TODO |
| 7.7 | GH Actions: `.github/workflows/main-deploy.yml` (main push → 마이그레이션 → Koyeb) | dry-run 성공 | 7.6 | cc:TODO |
| 7.8 | 테스트 schema 자동 생성/삭제 fixture (`tests/conftest.py`) | 통합 테스트가 격리 스키마에서 실행됨 | 0.6 | cc:TODO |
| 7.9 | reviewer agent invocation 자동화 (PR comment 또는 CI 잡) | PR 에 reviewer verdict 자동 게시 | 7.2, 7.5 | cc:TODO |

## Phase 8: API endpoint 구현 (프론트엔드 follow)

FE 가 작성한 endpoint 목록 단위로 라이프사이클 자동화 적용.

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 8.1 | FE endpoint 목록 수신 인터페이스 (mock + endpoint spec 파일 위치 약속) | 디렉토리 구조 + 양식 문서 | 7.1 | cc:TODO |
| 8.2 | endpoint 별 라이프사이클 1건 (시범) | 1 endpoint 가 `MERGED` 까지 완주 | 7.1-7.9, 8.1 | cc:TODO |
| 8.3 | 이후 endpoint 들은 8.2 시범을 패턴 삼아 진행 | FE 진행에 따라 채워짐 | 8.2 | cc:TODO |

## Phase 9: 프론트엔드 인프라

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 9.1 | Vue 3 + Vite MPA 골격 (다중 entry) | `npm run dev` 가 다중 entry 부팅 | - | cc:TODO |
| 9.2 | Tailwind + shadcn-vue 셋업 | shadcn-vue CLI 동작 + Button 컴포넌트 추가 | 9.1 | cc:TODO |
| 9.3 | Pinia + Vue Router (페이지별 인스턴스) | entry 별 store 작동 | 9.1 | cc:TODO |
| 9.4 | MSW 셋업 (`VITE_USE_MOCK` 토글) | 토글로 mock/실 API 분기 | 9.1 | cc:TODO |
| 9.5 | openapi-typescript + `npm run gen:api` | BE OpenAPI → TS 타입 생성 | 9.1 | cc:TODO |
| 9.6 | zod 런타임 검증 헬퍼 (응답 schema 검증) | 단위 테스트 통과 | 9.5 | cc:TODO |
| 9.7 | Playwright 셋업 (L1/L2/L3 분리 실행 가능) | `npm run test:e2e` / `test:e2e:integration` 동작 | 9.1, 9.4 | cc:TODO |
| 9.8 | Vercel 배포 셋업 (vercel.json + env) | 첫 push 로 preview URL 생성 | 9.1 | cc:TODO |
| 9.9 | 방송용 페이지 entry + 크로마키 (`#00B140`) 레이아웃 | 방송용 라우트가 녹색 배경으로 렌더 | 9.1, 9.3 | cc:TODO |
| 9.10 | 인증 흐름 (JWT 저장 / refresh / role 가드) — BE Phase 3 완료 후 통합 | 로그인 / 로그아웃 동작 | 3.5, 9.3 | cc:TODO |
| 9.11 | i18n 미도입 결정 명시 + 한글 폰트 토큰화 | 결정 문서 + Tailwind theme 한글 폰트 | 9.2 | cc:TODO |

## Phase 10: FE 자동화 (에이전트 워크플로 — FE 측)

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 10.1 | `docs/features/README.md` (요구사항 템플릿) | 본 세션에서 생성 | - | cc:WIP |
| 10.2 | `docs/spec/fe-workflow.md` (상태 머신 + 게이트) | 본 세션에서 생성 | - | cc:WIP |
| 10.3 | `.claude/agents/fe-{planner,dev,reviewer}.md` 3개 명세 | 본 세션에서 생성 | 10.2 | cc:WIP |
| 10.4 | `.claude/schemas/feature-flow.schema.json` (FE state JSON Schema) | schema validation 통과 | 10.2 | cc:TODO |
| 10.5 | `scripts/feature-flow.sh` (상태 전환 CLI) | 단위 테스트 통과 | 10.4 | cc:TODO |
| 10.6 | `frontend/endpoint-requests/` 양식 + 자동 추출 스크립트 (mock JSON + planner spec → request.json) | 시범 feature 에서 자동 추출 성공 | 10.5, 7.4 | cc:TODO |
| 10.7 | GH Actions: `.github/workflows/fe-feat-pr.yml` (lint/type/vitest/Playwright L2/번들) | CI 잡 성공 | 9.1, 9.7 | cc:TODO |
| 10.8 | GH Actions: `.github/workflows/fe-integration-pr.yml` (L1+L2+L3 on Vercel preview, prod BE) | CI 잡 성공 | 10.7, 9.8 | cc:TODO |
| 10.9 | GH Actions: `.github/workflows/fe-prod-smoke.yml` (Vercel prod 배포 후 L4 1회) | smoke 잡 성공 | 9.8 | cc:TODO |
| 10.10 | Vercel PR preview 연동 확인 (PR 마다 URL 자동 게시) | 동작 확인 | 9.8 | cc:TODO |

## Phase 11: FE 기능 구현 (page-led)

페이지 또는 작은 기능 그룹 단위로 진행. 메인이 `docs/features/<id>.md` 작성 후 FE 팀 트리거.

| Task | 내용 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 11.1 | 기능/페이지 카탈로그 확정 (메인에서 수동 작성) | `docs/features/_catalog.md` 또는 README 의 인덱스 | 10.1 | cc:TODO |
| 11.2 | URL 규칙 / 사이트맵 설계 (`docs/spec/url-convention.md`) | 규칙 문서 + 페이지별 URL 매핑 | 11.1 | cc:TODO |
| 11.3 | 시범 feature 1건 — Mock 라이프사이클 완주 | FE Mock 머지 + endpoint-request 자동 생성 | 9.1-9.11, 10.1-10.10, 11.2 | cc:TODO |
| 11.4 | 시범 feature 1건 — Integration 라이프사이클 완주 (BE 의존 endpoint MERGED 후) | L3 통과, Integration 머지 | 11.3, 8.2 | cc:TODO |
| 11.5 | 이후 feature 들은 11.3-11.4 패턴 반복 | 카탈로그 진척률 100% | 11.4 | cc:TODO |

---

## Notes

- 본 Plans.md 는 백엔드 자동화 + 시드 + 인프라 중심. 프론트엔드 개발 방법론은 별도 기획 후 추가
- DoD 의 `[tdd:skip:<reason>]` 태그 는 Harness 규약 (현재 사용 안 함)
- Status 마커: `cc:TODO`, `cc:WIP`, `cc:완료 [hash]`, `blocked`
- 본 파일은 v2 포맷 (Task / 내용 / DoD / Depends / Status)

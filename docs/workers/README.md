# Workers — 메인 → BE 팀 워커 요구사항

이 디렉토리는 백엔드 **워커(백그라운드 작업)** 의 요구사항을 정본으로 보관한다. API endpoint 와 달리 워커는 외부 HTTP 인터페이스 없이 스케줄/이벤트에 따라 실행되는 작업이므로 별도 문서 체계를 둔다.

한 파일 = 한 워커. BE 팀(be-test → be-dev → be-reviewer)이 이 파일을 입력으로 받아 구현한다.

상위:
- BE 워크플로: `@docs/spec/agent-workflow.md` (endpoint 라이프사이클을 워커에 적용 가능 — 본 문서 §하단 참조)
- 도메인 SSOT: `@CLAUDE.md` (§4 워커 정책)
- 작업 정본: `@Plans.md` (Phase 4 / 5 / 6 의 task 들)

## 파일 이름 규약

```
<worker_id>.md
```

`worker_id` 는 kebab-case. CLAUDE.md §4 에 정의된 3종:
- `daily-sync.md`
- `live-poll.md`
- `translation-filler.md`

(향후 워커 추가 시 동일 규약)

## 템플릿

```markdown
---
worker_id: <slug>
title: <한 줄 제목>
created: YYYY-MM-DD
priority: MVP            # MVP | post-MVP
status: requirements-only
---

## 1. 목적
이 워커가 어떤 문제를 해결하는가 (1~3 문장)

## 2. 스케줄
- 종류: cron / polling / 이벤트 트리거
- 주기/조건: 예) "KST 매일 00:00, 06:00, 12:00, 18:00" / "10초 폴링" / "1분 폴링, 큐 비어있으면 즉시 종료"
- 시작 / 정지 조건 (있다면)

## 3. 트리거 / 입력
- 데이터 소스: API-Football 의 X / DB 테이블 Y / Upstash 키 Z
- 입력 파라미터 (있다면): 예) "리그 ID 화이트리스트 5개", "라이브 fixture 만"

## 4. 처리 단계
1. ...
2. ...
3. ...
4. ...

## 5. 출력 / 부수 효과
- 저장 위치: DB 테이블 / Upstash 키 / 로그
- upsert 조건: 외부 ID 기반
- 갱신 컬럼 / 필드

## 6. 멱등성 / 재시도
- 멱등성: 같은 입력 반복 시 결과 변화 없음 (보장 방법: 외부 ID upsert 등)
- 재시도 정책: 실패 시 지수 백오프, 최대 N회, 그 이상은 다음 주기로 이월
- 부분 적재 후 재시작 안전성 보장 방법

## 7. 분산 락
- 동일 워커 중복 기동 방지를 위한 락 키 (Upstash `SET NX`): 예) `lock:worker:daily-sync`
- 락 TTL: 예) 5분
- 락 획득 실패 시 행동: 즉시 종료 / 대기

## 8. 동시성 / 외부 API 제약
- API-Football: semaphore 상한 6 (CLAUDE.md §4 운영 원칙)
- 기타 외부 API 호출 시 동시 호출 제한
- DB 트랜잭션 경계

## 9. 오류 처리
- 분류: syntax / network / 4xx / 5xx / timeout / 데이터 무결성 등
- 분류별 처리 방식
- 운영자 알림 트리거 조건

## 10. 모니터링 / 로깅
- 매 실행 시 기록할 메트릭: 실행 시간, 처리 row 수, 실패 row 수
- 로그 위치 (stdout / 로깅 인프라)
- 알림 조건 (예: 연속 3회 실패)

## 11. 의존성
- DB 테이블: 읽기 / 쓰기
- 외부 API: 어떤 endpoint
- 다른 워커 / 시드 데이터: 선행 작업

## 12. 비기능
- 1회 실행 예상 시간
- 예상 비용 (API 호출 수 × 단가)
- 메모리 / CPU 예상

## 13. 테스트 전략
- 단위: mock 으로 처리 단계별 검증
- 통합: 격리 schema + 외부 API 고정 fixture
- 회귀: 멱등성 검증 (같은 입력 2회 실행 → 결과 동일)

## 14. BE 팀이 결정해도 되는 것
- 내부 함수 구조 / 디렉토리 배치
- DB 쿼리 최적화 방식
- 단위 테스트 케이스 세부

## 15. BE 팀이 결정해서는 안 되는 것 (메인 확인 필요)
- 스케줄 주기 변경
- 적재 정책 변경
- 외부 API 호출 횟수 / 동시성 상한
- DB 스키마 변경 (별도 Phase 1 task)

## 16. 미확정 / 메모
- ...
```

## 핸드오프 절차 (메인 → BE 팀)

1. 메인이 `docs/workers/<worker_id>.md` 작성 / 확정
2. 메인이 BE 팀(`be-test`)에 트리거 — 요구사항 정제 + 테스트 플랜 작성
3. be-test → be-dev → be-reviewer 의 라이프사이클 적용 (단, endpoint 가 아니므로 `agent-workflow.md` 의 일부 단계는 생략 가능)
4. Plans.md 의 Phase 4/5/6 task 들을 본 문서를 정본으로 삼아 작업

## endpoint-flow 와의 차이

| 항목 | endpoint | worker |
|---|---|---|
| 외부 인터페이스 | HTTP API | 없음 (스케줄/이벤트) |
| 상태 머신 | endpoint-flow (FE_REQUESTED → ... → MERGED) | 단순화: be-test → be-dev → be-reviewer (혹은 인프라 패턴) |
| 머지 게이트 조건 | spec / 단위 / 통합 / reviewer | 단위 / 통합 (멱등성) / reviewer |
| 핸드오프 문서 | `frontend/endpoint-requests/*.request.json` | `docs/workers/<worker_id>.md` (본 문서) |

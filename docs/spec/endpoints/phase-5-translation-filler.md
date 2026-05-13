# Phase 5 / W1 — translation-filler 워커

본 문서는 BE 워크플로 spec 산출물이며, **endpoint 가 아닌 백그라운드 워커** 의 요구사항 mirror 다.
정본은 `docs/workers/translation-filler.md` (16 섹션). 본 문서는 그 SSOT 를 BE 팀 implementation/testing 관점으로 재정리.

> ⚠️ **불변 원칙** (dev 가 위반하면 reviewer REQUEST_CHANGES)
> - 스케줄 주기 = **1분** 고정
> - 모델 = **`gpt-3.5-turbo`** 고정 (web_search 도입은 post-MVP)
> - 대상 entity = **team, player** (league 는 ADMIN manual, 본 워커 제외)
> - 큐 조건 = `name_ko IS NULL OR short_name_ko IS NULL`
> - 운영 파라미터: semaphore **5**, 배치 상한 **50**, 연속실패 알림 임계치 **10 사이클**
> - 변경 필요 시 `docs/workers/translation-filler.md` 를 먼저 PR

## 1. 스코프 / 디렉토리

- 워커 모듈 (be-dev 영역): `app/workers/translation_filler/` (구조는 dev 자유)
- 엔트리: 사이클 1회 실행 함수 + 1분 폴링 스케줄러
- 본 spec 단계의 be-test 는 `app/` / `alembic/` 미수정. `docs/` + `tests/` 만.

## 2. 입력 / 큐

3개 매칭 테이블 UNION ALL 중 **team / player 만** 본 워커가 처리. league 는 ADMIN manual.

```sql
-- team
SELECT 'team'   AS entity_type, tt.team_id   AS id, t.name AS eng_name, t.country     AS context_a, t.code                                AS context_b
FROM team_translation tt
JOIN team t ON t.id = tt.team_id
WHERE tt.name_ko IS NULL OR tt.short_name_ko IS NULL

UNION ALL

-- player
SELECT 'player' AS entity_type, pt.player_id AS id, p.name AS eng_name, p.nationality AS context_a, p.firstname || ' ' || p.lastname AS context_b
FROM player_translation pt
JOIN player p ON p.id = pt.player_id
WHERE pt.name_ko IS NULL OR pt.short_name_ko IS NULL;
```

큐가 비면 사이클 **즉시 종료** (OpenAI 호출 0회).

## 3. 처리 단계

```
[cycle start]
  ├─ Step 1. queue = SELECT (위 SQL, 배치 상한 50)
  ├─ Step 2. if not queue → return (OpenAI 호출 없음)
  ├─ Step 3. entity_type 별 그룹화 (team / player)
  ├─ Step 4. semaphore=5 동시성으로 row 처리:
  │           ├─ few-shot prompt 빌드 (entity_type + country/nationality 매칭)
  │           ├─ OpenAI chat.completions.create(...)
  │           ├─ 응답 JSON 파싱
  │           ├─ 파싱 성공 + name_ko + short_name_ko 둘 다 존재 → UPDATE
  │           └─ 실패 → row skip (NULL 유지, 다음 사이클 재시도)
  └─ [cycle end] log {duration, queue_size, processed, succeeded, failed, openai_calls, openai_errors, cost_estimate}
```

## 4. OpenAI 호출 파라미터

| 항목 | 값 |
|---|---|
| model | `gpt-3.5-turbo` |
| temperature | `0` |
| max_tokens | `100` |
| response_format | `{"type": "json_object"}` |
| timeout | dev 결정 (권장 10s) |

### Few-shot 예시 선택
- **team**: `team_translation` 시드 CSV 에서 동일 `country` 의 5~10건 무작위 (없으면 무작위 5건). 시드 미존재 시 fixed 5건 fallback
- **player**: `_Player__202605131748.csv` 에서 동일 `nationality` 의 5~10건 무작위 (없으면 무작위 5건)
- **league**: 본 워커는 처리 안 함

### 프롬프트 (player 예)
```
당신은 축구 선수 영문 이름을 한국 축구 중계/기사에서 통용되는 한글 표기로
음역하는 번역가입니다. 응답은 JSON 만 출력하세요.

예시:
{"eng": "Bukayo Saka", "nationality": "England", "name_ko": "부카요 사카", "short_name_ko": "사카"}
...

입력:
{"eng": "{name}", "nationality": "{nationality}"}

출력 (JSON):
```

## 5. 응답 파싱 규칙

| 케이스 | 처리 |
|---|---|
| JSON 파싱 OK + `name_ko` + `short_name_ko` 둘 다 truthy string | UPDATE (성공) |
| JSON 파싱 실패 | row skip, log warn |
| `name_ko` 또는 `short_name_ko` 누락 / 빈 문자열 | row skip, log warn |
| OpenAI 5xx / timeout | 지수 백오프 1s/2s/4s 3회 후 row skip |
| OpenAI 4xx (인증/quota) | 사이클 abort, 운영자 알림 |

## 6. 멱등성

- `name_ko IS NULL OR short_name_ko IS NULL` 큐 조건으로 채워진 row 는 자동 제외
- 같은 사이클 두 번 실행해도 같은 row 두 번 호출 안 됨
- **이미 채워진 row 는 본 워커가 절대 덮어쓰지 않음** (UPDATE 시 WHERE name_ko IS NULL 또는 short_name_ko IS NULL 명시 권장)

## 7. 재시도 / 백오프

- OpenAI 호출 실패 → 1s, 2s, 4s 지수 백오프 3회. 그 이상 실패 시 row skip (다음 1분 사이클에서 재시도)
- 한 row 가 **10 사이클 연속 실패** 시 운영자 알림 (stdout)

## 8. 동시성 / 락

- semaphore **5** (동시 OpenAI 호출)
- 분산 락 없음 (단일 인스턴스 전제, CLAUDE.md §4)

## 9. 로깅 / 모니터링

매 사이클 종료 시 stdout 1줄 JSON:
```json
{
  "cycle_started_at": "...",
  "duration_seconds": 0.0,
  "queue_size_at_start": 0,
  "processed_count": 0,
  "succeeded_count": 0,
  "failed_count": 0,
  "openai_calls": 0,
  "openai_errors": 0,
  "cost_estimate_usd": 0.0
}
```

알람 트리거 (stdout):
- OpenAI 4xx
- DB 접속 불가
- 같은 row 가 10 사이클 연속 실패
- 큐 크기 ≥ 1000

## 10. 의존성

- DB: `league_translation`, `team_translation`, `player_translation` (UPDATE), `team`, `player` (SELECT JOIN), `league` (큐에 없지만 SQL 정의상 포함 가능)
- 외부: OpenAI API (`gpt-3.5-turbo`)
- 선행: daily-sync 가 NULL row 생성, 시드 CSV import 완료

## 11. 인증

워커는 인증 endpoint 가 아님. 그러나 ADMIN endpoint `POST /api/v1/admin/workers/translation-filler/run` 으로 수동 트리거할 수 있도록 entry function 은 공개 (단 그 endpoint 자체는 별도 task — CLAUDE.md §4 운영 원칙 "수동 트리거").

## 12. 비기능 / 비용

| 지표 | 값 |
|---|---|
| 사이클 평시 | < 1초 (큐 비면 즉시 종료) |
| 사이클 큐 50 row | ~10초 (semaphore 5, 1초/call) |
| 호출당 비용 | ~$0.001 미만 |
| 일일 비용 | < $0.01 (평시), 시즌 시작 일시 ~$1 |

## 13. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-13 | spec 작성 (be-test, W1). docs/workers/translation-filler.md SSOT mirror |

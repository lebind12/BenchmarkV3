# Features — 메인 → FE 팀 요구사항 문서

이 디렉토리는 **메인(사용자 + Claude)이 작성하는 high-level 기능/페이지 요구사항** 의 정본 위치다.

한 파일 = 한 feature. FE 팀은 이 파일을 입력으로 받아 더 구체화된 spec / devplan / testplan 을 생성한다.

상위 워크플로 문서: `@docs/spec/fe-workflow.md`

## 파일 이름 규약

```
<feature_id>.md
```

`feature_id` 는 kebab-case, 페이지/기능을 식별할 수 있는 짧은 슬러그.
예: `main-fixtures-list`, `team-detail-squad`, `broadcast-livescore`.

## 템플릿

새 feature 작성 시 아래를 복사해서 채운다.

```markdown
---
feature_id: <slug>
title: <한 줄 제목>
created: YYYY-MM-DD
priority: MVP            # MVP | post-MVP
status: requirements-only
---

## 1. 개요
한두 문장으로 이 기능이 무엇이고 왜 만드는지.

## 2. 사용자
- 주 role: USER | STREAMER | ADMIN | public
- 부가 role: (있다면)

## 3. 사용자 흐름
- 사용자는 ... 화면에 진입한다
- ... 정보를 본다
- ... 동작을 한다
- 결과로 ... 한다

## 4. 페이지 / URL 후보
- 페이지 이름: <이름>
- URL 제안: `/path/...`
- 방송용 페이지 여부: yes | no

## 5. 표시 데이터 (개념)
- A: ... (데이터 소스를 아는 경우 명시 — 모르면 비워둠)
- B: ...

## 6. 인터랙션
- 클릭/입력/정렬/필터/페이지네이션 등

## 7. 비기능 요구
- 데이터 신선도: 6h / 실시간 / N/A
- 접근성: 키보드, 색 대비, 스크린리더 라벨
- 성능: 초기 렌더 임계치, 번들 회귀 한도
- 반응형: 데스크탑 / 모바일 포함 여부

## 8. 디자인 참고
- 시안 경로 (있다면)
- 색/타이포 제약
- 방송용 페이지인 경우: 크로마키 `#00B140` 배경, 1920×1080 송출 기준

## 9. MVP 여부 / 우선순위
- MVP 포함: yes / no
- 우선순위 (1=최우선): 1~10

## 10. FE 팀이 결정해도 되는 것
- 컴포넌트 분해
- Pinia store 모양
- 빈 상태 / 로딩 / 에러 표현
- 페이지네이션 여부

## 11. FE 팀이 결정해서는 안 되는 것 (메인 확인 필요)
- URL 규칙 변경
- 방송용 페이지 여부 전환
- 인증 요구 변경
- 새 외부 데이터 의존성 추가

## 12. 미확정 / 메모
- ...
```

## 작성 규칙

1. **frontmatter** 는 반드시 채운다 (도구가 파싱).
2. `status: requirements-only` 인 동안만 메인이 자유롭게 수정. FE 팀이 트리거 받아 작업 시작하면 `status: in-fe-pipeline` 으로 메인이 변경.
3. **§10/§11 권한 경계는 빈 항목 금지** — 적어도 1줄씩.
4. **데이터 소스를 모르면 §5 항목을 비워두고** "FE 팀이 mock 으로 추론" 메모.
5. **시안 이미지** 는 `designs/` 디렉토리 별도 관리. 본 markdown 은 경로만 참조.

## FE 팀 트리거 흐름

1. 메인이 `docs/features/<id>.md` 작성 / 검토 / 확정
2. 메인이 사용자에게 "FE 팀 트리거합니다" 확인 후 Agent 호출 (`fe-planner`)
3. FE 팀이 자율 워크플로 진입 (`docs/spec/fe-workflow.md` 의 상태 머신)
4. 완료 시 `FE_DONE_AWAITING_BE` 상태로 메인에 보고 → 메인이 BE 트리거 결정

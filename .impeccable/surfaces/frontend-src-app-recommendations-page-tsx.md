---
version: 1
slug: "frontend-src-app-recommendations-page-tsx"
primary_target: "frontend/src/app/recommendations/page.tsx"
related_targets: ["frontend/src/components/board/BoardView.tsx"]
---

# /recommendations — 추천 결과 (개찰판)

## 범위·모드
Operate. 리디자인의 대표 화면(첫 서피스) — 새 비주얼 월드 "개찰판(開札板)"이 여기서 확립되어 나머지 페이지로 퍼진다.

## 방문자·잡
업종 무관 중소기업 대표/담당자. 매일 아침 회사 기준 검토 우선순위를 훑고, 행을 개봉해 근거를 확인하고, 검토할 공고에 도장을 찍어 남긴 뒤 재방문. 성공 = 재방문·재검색 정착.

## 콘텐츠·증거
실데이터: 추천 20건(v2 랭커, score_breakdown·qualification), LLM 총평+상위 5건 근거(스트리밍), 사전규격·발주계획 매칭, 증거 칩. 날조 금지: 후기·도입 사례.

## 제약
- 카피 원칙: "검토 우선순위" 프레이밍, 낙찰 예측 금지, 사업자번호 마스킹, "매일 갱신·나라장터 기반" 상시.
- 금기: 장난스러움·과한 재미. 인주 레드는 마감 임박·인장 전용.
- SEO 구조 보존(이 페이지는 noindex), 스트리밍 API 계약 유지.

## 선택된 방향·기억점
개찰판 — seed f3792acf, 자체 후보 7순위(배정). 크라프트 판머리(명조 대활자+관인) / 괘선 보드 / 행 개봉(시그니처 인터랙션) / 검토 인장(localStorage 저장) / 동작하는 조회 조건 캡슐 바. 라이즈 5건: 단일 마감 축, 타이포=인터페이스, 공유 괘선 tabular, 포커스 행 확장+디밍, 영역 단위 색 커밋+캡슐 컨트롤.

## 미해결
- 점수 표기 스케일(상위권 60~90 혼재) 재보정은 백엔드 SCORE_DISPLAY_DIVISOR 이슈 — 별도 결정.
- Footer·랜딩 등 나머지 표면의 월드 전파는 후속 라운드.
- 키워드 모드 카드별 LLM 설명 부재(회사 모드와 편차)는 제품 결정 대기.

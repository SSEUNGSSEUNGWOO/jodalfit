# 로드맵 2026-10

작성 2026-10-13. 디자인 리뉴얼 전에 측정·운영 기반을 먼저 깐다. 각 Phase는 완료 기준을 통과해야 다음으로 넘어간다.

## 현재 상태 (2026-10-13 측정)
- 실사용자 검색: 최근 30일 685회, 29일/30일 활동
- 뉴스레터 구독자 9명 ("준비 중" 상태, 발송 인프라 없음)
- 저장(검토 인장) 누적 3건 — 추천 효용 증거 부족
- 분석 도구·에러 수집·업타임 모니터: **없음**
- 이용약관: 없음 (`/privacy`만 있음)
- DB: 뭄바이 Micro, 9.98GB, 벡터 인덱스 없음, 벡터 미생성 회사 ~953곳
- 회사 SEO 페이지 76,671건 sitemap 노출, GSC "발견됨·색인 안 됨" 1,912건(2026-06 기준, 재확인 필요)

## Phase 1. 측정·모니터링 — 완료 (2026-10-13)
- [x] PostHog US (cookieless): 페이지뷰 + 이벤트 `search_submit` / `notice_click` / `notice_save` / `g2b_outbound`. 코드 `frontend/src/instrumentation-client.ts`, `lib/analytics.ts`
- [x] Sentry frontend + backend (DSN 없으면 비활성). Vercel·Railway 환경변수 등록
- [x] UptimeRobot: `jodalfit web`(jodalfit.co.kr) / `jodalfit api`(/health), 5분 간격, 알림 jansseung@gmail.com
- 완료 확인: 운영 사이트에서 PostHog `/e/` 200, Sentry envelope 200, 로컬 `search_submit` 전송, Sentry 테스트 이벤트 양쪽 도착, UptimeRobot 2개 Up
- 남은 수동 설정: PostHog Billing spend limit $0 (승우님)

## Phase 2. DB 이전 (뭄바이 → 싱가포르)
- 절차서: `docs/infra/supabase-singapore-migration.md`
- 컴퓨트는 **Small로 시작**, 이전 후 Server-Timing·I/O 측정해서 필요할 때만 Medium (리전은 못 바꾸지만 컴퓨트는 즉시 변경 가능)
- 포함: 개인정보처리방침 리전 표기 + `PRIVACY_VERSION` 갱신, 벡터 미생성 회사 재계산, 옛 DB 덤프 D: 보관, pg_cron 5개 재생성(`purge-logs-older-than-1y` 포함), MV anon 권한 회수
- 완료 기준: 행 수 대조 일치, opt-out 1건 존재, 추천 Server-Timing total < 1s, daily-sync 첫 성공

## Phase 3. 디자인 리뉴얼
- 방향 시안 재작업 ("AI스럽지 않게" — 템플릿 느낌 배제, 타이포·그리드 중심)
- 순서: 토큰 → 컴포넌트 → 랜딩·추천 → 인사이트 → 회사·공고 SEO 페이지(URL·메타·JSON-LD 유지)
- 회사 페이지 노출 범위(7.6만)는 Phase 1 데이터 2주 보고 이 Phase 안에서 결정
- 완료 기준: Lighthouse 성능·접근성 ≥ 90, Phase 1 지표로 전후 비교(검색 제출률·공고 열기율)

## Phase 4. 약관·발송
- 이용약관 `/terms`, 사업자 정보 표기 (결제 전 통신판매업 신고 확인)
- 발송: Resend (도메인 인증), 구독자에게 첫 주간 메일
- 완료 기준: `/terms` 공개, 첫 뉴스레터 발송·수신 확인

## Phase 5. 회원가입·유료 예고
- Supabase Auth 매직링크, 저장 검색 무료 1개
- 유료 예고 배너 + 사전 신청
- 완료 기준: 가입 → 저장 검색 → 알림 메일까지 1명 완주

## 비용
- 추가 고정비는 Supabase 컴퓨트뿐 (Small +$5/월, Medium 시 +$50/월)
- PostHog·Sentry·UptimeRobot·Resend·Auth는 무료 구간, 초과 시 자동 과금 안 되게 한도 0 설정

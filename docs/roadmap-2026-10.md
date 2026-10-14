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

## Phase 2. DB 이전 (뭄바이 → 싱가포르) — 진행 중
- 절차서: `docs/infra/supabase-singapore-migration.md`
- 2026-10-13 낮: 새 프로젝트 생성(싱가포르 Small), 확장 6개·스키마 복원 완료, 옛 DB와 객체 수·RLS 일치 확인. 대시보드 "Restore to new project"는 리전 고정이라 사용 불가. 작업 스크립트는 `C:\dev\ops\jodalfit\migrate\`(리포 밖)
- 2026-10-13 밤: 데이터 복원 완료(1차 실패 원인: 8GB 디스크 자동확장 재시작 → 15GB로 올린 뒤 성공, 부모 테이블 먼저·`--disable-triggers` 없이). 행 수 전부 일치, opt-out 1건 확인, 차분 복사(덤프 이후 공고 1,214건 등), MV 5개 + anon 회수, cron 5개(KST 06:30~07:10으로 당김), Vercel·GitHub secrets·로컬 env 교체. 작업 스크립트 `C:\dev\ops\jodalfit\migrate\`
- 2026-10-14: daily-sync 새 DB 첫 성공(sync 15분). 같은 날 발견한 묵은 결함 2개 수정 — ① enrich-companies 가 90분 한도에 걸려 회사 벡터 재계산이 잘림(10/10·10/14) → `company-vectors` 잡으로 분리(sync 뒤 병렬) ② backfill_companies_basic·check_business_status 가 `DATABASE_URL` 없이 매일 exit 1(9/11 추가 이후 한 번도 안 돎, continue-on-error 에 가려짐) → GH secret `DATABASE_URL` 등록 + env 연결. CI 확인은 10/15 05:00 KST 실행 결과로.
- **남은 것**: Railway 변수 교체(승우님) · 다른 PC의 hourly-sync 태스크 env 교체 · 벡터 인덱스(WAL 4GB로 디스크 부족 → 20GB 올린 뒤 `migrate.sh index`) · 전환 검증(Server-Timing, opt-out 404, sitemap) · 1주 뒤 옛 프로젝트 삭제 전 덤프 D: 보관 · `compute_company_vectors` 수동 1회
- 다이어트(후속): halfvec 전환은 손실 무시 수준 → 진행. `raw`는 **embed 잡이 읽음**(품목분류·규격 등) → 활성 공고 raw는 유지, 마감 지난 것만 비움. 첨부 원문은 로컬 덤프 보관 후 마감 공고만 비움.
- 임베딩 모델 교체 검토: `docs/design/prototypes/embed-eval.html`(블라인드 비교, 모델 매핑은 `_mapping.txt`). OpenAI↔BGE/KURE 겹침 20%. 코덱스 의견(`C:\dev\ops\jodalfit\design\codex_answer.md`): 교체 전에 자격 반영 후보 검색 + 업종·물품 하이브리드(RRF)가 먼저, 평가는 과거 낙찰 held-out(Recall@100)로, 운영 추론은 Railway 동거 금지(Modal GPU 또는 API).
- 추천 평가 하네스(채점표) 완료(2026-10-13, 브랜치 `feat/recommender-eval`): `jobs/evaluate_recommender.py`, 규칙 `docs/recommender/evaluation.md`, baseline 8/1·9/1. 결과: 정답의 절반이 dense 후보 400 밖에서 사라짐(cold 군 가장 심함), 자격 제외 손실은 5~8%, MMR 손실 0. → 다음 작업은 후보 검색(하이브리드/자격 선필터), 점수 재보정은 그 뒤.
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

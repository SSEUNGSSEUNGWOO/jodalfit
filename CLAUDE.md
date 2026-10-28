# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# jodalfit 프로젝트 가이드

## 컨셉
회사명/사업자번호 입력 → **등록업종 + 공급물품 (메인)** + 과거 수주 이력 (보조)을 동적 가중합한 회사 벡터 생성 → 신규 입찰공고와 유사도 매칭 → **20건** 추천(비로그인은 상위 5건 공개 + 15건 흐림) + LLM 설명. 한국 공공조달(나라장터) 대상, B2B(중소 SI), 한국 시장 한정.

- 회사 식별/벡터 미확보 시 키워드 모드 폴백 (자유 텍스트 직접 임베딩).
- 톤: **"낙찰 예측"이 아닌 "검토할 만한 공고 디스커버리"**. 카피 원칙(점수 표현, 사업자번호 마스킹 등)은 README.md §12 — 어기지 말 것.
- 회사 벡터 동적 가중치: 수주 0건 γ(업종)=1.0 / 1~5건 γ=0.65,α=0.30 / 6+건 γ=0.50,α=0.45.

## 스택
- Backend: FastAPI (Python 3.12, uv) + slowapi rate limit
- Frontend: Next.js 16 (App Router, TypeScript, Tailwind v4, React 19)
- DB: Supabase (Postgres + pgvector HNSW + pg_trgm, 싱가포르 ap-southeast-1 — 2026-10-13 뭄바이에서 이전) — 백엔드는 service_role 키로 직접 접근
- Embedding: **두 공간 병행, `EMBED_SPACE` 하나로 전환/롤백** — `openai`(text-embedding-3-small 1536d, 컬럼 `embedding`) / `kure`(KURE-v1 1024d, 컬럼 `embedding_k` + RPC `_k` 변형, 0045). **운영은 2026-10-15부터 kure**(Railway는 int8 ONNX 상주, 배치는 `uv sync --extra embed-cpu`의 torch). 모든 임베딩 호출은 `app/services/embedding.py`만 거친다(sha1 캐시 `text_embeddings` 0046) — openai_client/local_embed 직접 호출 금지. 프론트 `NEXT_PUBLIC_EMBED_SPACE`도 같이 바꾼다.
- LLM 설명: `claude-haiku-4-5`(`EXPLAIN_PROVIDER`, 키 없으면 `gpt-4o-mini` 로 degrade) / 첨부문서 인사이트: claude-haiku-4-5 (Message Batches, `INSIGHT_PROVIDER`)
- 운영: Frontend Vercel / Backend Railway / 배치 GitHub Actions. 계측 PostHog(`frontend/src/instrumentation-client.ts`, `lib/analytics.ts`) + Sentry 양쪽(DSN 없으면 비활성) + UptimeRobot.

## 명령어
- Backend 실행: `cd backend && uv run uvicorn app.main:app --reload` → :8000
- Frontend 실행: `cd frontend && npm run dev` → :3000
- Frontend lint: `cd frontend && npm run lint` / build: `npm run build`
- 잡 실행: `cd backend && uv run python -m jobs.<이름> [--days-back N ...]` (전체 시드 순서는 README.md §8)
- 연결 점검: `uv run python -m jobs.verify_setup` (row count) / `jobs.verify_phase2`
- 추천 평가(채점표): `cd backend && uv run python -m jobs.evaluate_recommender --as-of YYYY-MM-DD --companies 3000 --seed 7` → `backend/data/recommender_eval/<run_id>/report.md`. 규칙은 `docs/recommender/evaluation.md`.
- 의존성 추가: `uv add <pkg>` (backend), `npm install <pkg>` (frontend). 일부 잡(backfill/사업자상태/purge/채점표/상세필드)은 Supabase 대신 `DATABASE_URL`(psycopg 직결)을 쓴다.
- **프론트 검증은 `frontend/scripts/check_*.py`** (Playwright, 운영 데이터로 실제 화면을 친다). 백엔드 venv 로 돌린다:
  `cd backend && uv run --no-sync python ../frontend/scripts/check_entry.py` — entry/results/saved/company/notice/changelog/auth/foundation/funnel 9종.
  화면을 고치면 해당 검증도 같이 고친다. 금지어·주황 면 0·390 가로 넘침·조작(타이핑·방향키)까지 본다.
- 순수 로직 단위 검사: `cd frontend && node --experimental-strip-types --test src/lib/*.test.ts src/components/results/*.test.ts`.
- 인증 흐름 스모크: `cd frontend && node --env-file=.env.local scripts/auth_smoke.mjs` (service_role 로 가입·확인·로그인·로그아웃을 실제 서버에 친다. `AUTH_URL` 로 대상 변경, 기본 :3000).
- 테스트 프레임워크 없음. `jobs/test_api.py`·`probe_*.py`는 pytest가 아니라 API 탐색용 CLI 스크립트. 대신 순수 로직 모듈은 `__main__` 자체 점검을 둔다 — `uv run python -m app.recommender.evaluation` / `app.core.traffic_source` / `app.recommender.qualifications` / `app.recommender.keyword_expand` / `app.recommender.title_match` / `app.services.embedding` / `app.services.doc_extract`. 새 순수 로직도 이 패턴을 따른다.

## 아키텍처 큰 그림

### 추천 파이프라인 (요청 경로)
`POST /recommendations`(회사 SEO 페이지 SSR self-call, `recommendation_cache.py` read-through — 0019 `company_recommendations`, 마감 지난 건 걷어내고 5건 미만이면 미스) / `POST /recommendations/stream`(대화형 보드가 쓰는 실사용자 경로, 항상 라이브) → `app/api/recommendations.py` → `app/services/recommend.py`:
1. `find_company` — pg_trgm fuzzy + 사업자번호로 회사 식별 (실패 시 키워드 모드)
2. `_search_with_embedding` — pgvector RPC(`match_bid_notices`) 3채널(dense + 회사 업종 허용 공고 0044 + 회사 공급물품 코드 공고 0048, `RECO_RETRIEVAL`)을 번갈아 합쳐 후보 풀
3. **v2 랭커 (현재 기본)** — `app/recommender/pipeline.py::rank_v2`:
   취소공고 제외(`cancellation.py`, 공고상태 `bidNtceSttusNm` — 진행 공고의 9.5%) → 자격 하드 제외(`qualifications.py`; 회사 업종이 비면 "면허 확인불가"로 통과 + 감점 12, 공고 쪽 면허 행 없음은 라벨만) → 가중치 score + breakdown(`score.py`) → 협업 시그널(peer 기관, `collaborative.py`) → MMR 다양성(`mmr.py`)
4. `app/services/explain.py` — LLM 상단 요약 1회 + 카드별 설명 (ThreadPoolExecutor 병렬)

`POST /qualifications/check` — 같은 `check_qualifications`를 **라벨용**으로 재사용(하드 제외 아님, 조건 검색 결과에 passed/failures 표시). 자격 규칙은 `app/recommender/qualifications.py` 한 곳만 고친다.

주의: `recommend.py` ↔ `recommender/` 사이 순환 import를 함수 내 lazy import로 회피하고 있음 — 모듈 상단으로 끌어올리지 말 것. v1 rerank(소프트 감점)는 `recommend.py::rerank`에 아직 남아 있음.

### 알고리즘을 바꿀 때 (필수)
- 후보 검색·자격·점수·MMR을 건드리면 **채점표로 전후 비교**한다: `--companies 3000 --seed 7`, 시점 7/1·8/1·9/1, 기준점 `docs/recommender/baseline-2026-10-16-big.md`. 300곳은 잡음과 구분이 안 된다.
- **한 군(cold/small/rich)이 떨어지면 전체 평균이 올라도 채택하지 않는다.** 두 시점 이상 같은 방향이어야 한다.
- **10/1 은 시험 전용이다**(2026-10-23). 가중치·임계값을 고르는 데 쓰지 말고, 7/1·8/1·9/1 에서 채택한 변경이 처음 보는 시점에서도 유지되는지 확인할 때만 돌린다. 여기서 떨어지면 과적합으로 보고 채택하지 않는다.
- 하네스는 운영과 맞춰져 있다 — 채널당 1,000행 천장(`CHANNEL_MAX_ROWS`, Supabase REST 한계), 회사 프로필을 시점 t 로 복원(`rgst_dt`/`valid_to_dt`). 보고서에 `final@5`·`final@20`(운영 화면 조건)과 자격 탈락 사유가 나온다.
- 점수 분해: `--ablate bonuses` 로 유사도 단독 기준선, `--ablate institution,region,...` 로 하나씩. `--channel-max-rows 0` 은 천장을 꺼 전수 채점 상한을 잰다(2026-10-23 실측: 후보를 전부 넣어도 final@20 은 안 오른다 — 병목은 점수다).
- 결과는 `docs/recommender/exp-YYYY-MM-DD-<주제>.md`(실험 기록) + `docs/recommender/changelog.md`(사용자 언어로 "무엇이 왜 달라졌나")에 남긴다. 운영 전환 스위치(`RECO_RETRIEVAL`, `EMBED_SPACE`, `*_PROVIDER`)는 환경변수 하나로 롤백되게 유지한다.

### backend 구조
- `app/api/` — 라우터 (recommendations, events=행동 로깅 + `/events/helpful`(결과 화면 "도움이 됐습니까" → 0063 `result_feedback`, `/admin` 응답 건강 판), qualifications=자격 라벨, feedback=`/feedback` 폼 수신 → 0061 `feedback` 테이블, `/admin` 이 읽는다)
- `app/core/` — pydantic-settings config(환경변수 스위치는 전부 여기, 주석에 근거 문서 링크), rate_limit, bot_guard, traffic_source, timing(Server-Timing)
- `app/services/` — supabase/openai/anthropic 클라이언트, embedding(공간 스위치+캐시)·local_embed(KURE), recommend(후보 검색+v1), recommendation_cache, explain, doc_extract(hwp/hwpx/pdf/xlsx 본문)·notice_insights(LLM 구조화), viz(임베딩 시각화), search_log, notice_events
- `app/recommender/` — v2 랭킹 (pipeline / score / qualifications / mmr / collaborative) + evaluation(지표 순수 함수) + keyword_expand(키워드 질의의 영문 약어 풀이 — "si"→시스템 통합…, 임베딩 전에만 적용) + title_match(키워드 모드 첫 판 "제목 일치 전부" — 낱말 AND·영문은 단어 경계·마감 가까운 순·상한 300, 의미 유사 20건은 이걸 뺀 "그 밖에". 회사 모드 무관)
- `jobs/` — 접두사 규칙: `ingest_*`(나라장터 API 수집) / `embed_*`(임베딩 생성) / `compute_company_vectors`(회사 벡터 통합) / `probe_*`(API 응답 탐색, 개발용) / `verify_*`·`check_*`·`diag_*`(검증/진단). 공통 fetch/페이징/타입 변환은 `jobs/_common.py`.
  - 채점표 도구: `evaluate_recommender`(정량 채점표, 기준) → `--dump-features` 로 뽑은 `features.csv` 위에서 `fit_score_weights`(로지스틱 재보정, held-out)·`sweep_score_scale`(보너스 배율 k 하나만 훑기). `evaluate_recommendations`는 옛 정성 리포트(3버킷 마크다운)로 채점표가 아니다.
  - 로컬 GPU 백필은 `uv sync --extra embed-gpu`(RTX 5060 Ti = cu128). `embed-cpu`와 상호 배제라 cpu 로 sync 하면 CUDA torch 가 CPU 휠로 덮인다.
- `jobs/marketing_report/` — 일일 마케팅 성적표 (`/marketing-report`, 설명서 `docs/marketing/README.md`).
- `jobs/send_weekly_mail.py` — 저장한 회사의 새 공고 주간 메일(월 08:00 KST, `weekly-mail.yml`). 대상 = 메일 인증 + 가입 동의(0052 `user_consents.marketing_opt_in`) + 저장 회사 있음, 6일 내 미발송(0063 `weekly_mail_log`). 회사마다 `recommend()` 를 돌려 최근 7일 등록 공고 상위 5건. 그만 받기 링크는 `INTERNAL_API_TOKEN` HMAC(`frontend/src/lib/mail-link.ts` 와 같은 식) → `/mail/weekly` 가 확인 버튼 뒤 POST 로 바꾼다. `--dry-run`, 시험 발송 `--to 주소 --bizrno 번호`.

### 로그 지표 — 내부 SSR과 실사용자 구분 (필수)

회사·공고 SEO 페이지는 서버 렌더링 때마다 추천 API를 self-call한다. 그래서 로그를 그냥 세면 사용자 지표가 아니다 — **2026-09-18 확인: `search_logs` 최근 1,000건 중 982건이 내부 SSR, `notice_events` 누적 110만 건 중 사용자 행동(save)은 3건.**

- `app/core/traffic_source.py`의 `classify_source(request)`가 출처를 판정한다. 추측이 아니라 `X-Internal-Token`(bot_guard와 같은 신호) → `internal`, 자동화 UA → `bot`, 나머지 → `user`. 자체 점검: `uv run python -m app.core.traffic_source`
- `search_logs.source`는 라벨만 붙인다(내부 호출도 캐시 히트율 분석에 쓰인다). **숫자를 인용할 때는 `v_search_logs_daily_user`·`v_search_logs_top_queries_user` 뷰를 쓴다.** 전체 기준 옛 뷰(`v_search_logs_daily` 등)를 실사용 지표로 착각하지 말 것.
- `notice_events`는 내부 SSR impression을 **적재하지 않는다** (`log_impressions`가 `source != "user"`면 즉시 return). 렌더링마다 20건씩 쌓여 테이블만 커졌다.
- 새 로그 경로를 추가하면 `source`를 같이 넘긴다. `v_search_logs_sources`에서 internal 비중이 갑자기 오르면 계측이 깨진 신호다.

### 데이터 파이프라인 (자동화)
`.github/workflows/` 세 개, 각 스텝 `continue-on-error: true` + `timeout-minutes`:
- `daily-sync.yml` — 매일 KST 05:00: ingest(공고/계약/낙찰/참가업체/사전규격·의견/발주계획/면허/지역) → embed → sitemap warm-up → purge_expired_documents → `check_ingest_health`(실패·0건·48h 누락을 빨간색으로, `if: always()`). 회사 벡터 재계산은 별도 `company-vectors` 잡으로 병렬.
- `hourly-sync.yml` — 매시 5분: 검색된 회사 등록 → 공고 수집(24h) → `ingest_bid_notices_full`(상세 필드: 분류번호·사전규격·자격등록 마감·발주계획 번호, 물품·용역·공사·외자 네 구분) → 임베딩 500건. **임베딩의 주 담당은 이 잡**(daily는 50분 제한에 잘려서 500건만).
- `documents-sync.yml` — 2시간 주기: 첨부 목록 → 본문 추출 150건 → LLM 요약(Batch 수거+제출 100건).
나라장터 API 제약이 코드 전반에 배어 있음: 일일 호출 한도(UsrInfoService02 4,500/일), 조회범위 30일 초과 시 에러 → 청크 처리, 429 백오프 등.

### Supabase migrations
`supabase/migrations/0001~0063` — **CLI 아님, Dashboard SQL Editor에서 번호 순서대로 수동 실행**(psycopg 로 직접 넣기도 한다 — 함수 교체처럼 되돌릴 수 있는 것만). 코드 주석의 "0044 필요" 같은 숫자는 이 파일 번호다. 새 RPC를 쓰는 코드는 미적용 환경에서도 죽지 않게 try/except로 감싸 degrade시키는 패턴 유지 (예: `pipeline.py`의 0015 협업 RPC).
- **뷰는 RLS 를 우회한다**(`security_invoker` 기본 off → 소유자 권한). 표에 RLS 를 켜도 그 위의 뷰는 anon 키로 읽혔다(2026-10-26, `v_search_logs_*`). 0062 가 public 기본 권한에서 anon/authenticated 를 뺐으니 새 표·뷰는 자동으로 anon 에 안 열린다 — 사용자 세션으로 읽을 표만 명시적으로 `grant` + 정책. 점검은 `docs/security/2026-10-26-review.md`.

### frontend 구조
- **모든 페이지가 `src/app/(renewal)/` 안에 있다**(2026-10-24 컷오버). 라우트 그룹이라 URL 은 그대로다 — `(renewal)/companies/[bizrno]` 가 `/companies/[bizrno]` 를 낸다. 그룹 밖에 page.tsx 를 만들면 같은 URL 로 충돌한다.
- `(renewal)/layout.tsx` 가 nav·footer·`<main>` 을 준다. **nav 가 로그인 상태를 읽어 쿠키를 쓰므로 어떤 페이지도 정적 생성이 안 된다** — `generateStaticParams` 를 두면 운영에서 `DYNAMIC_SERVER_USAGE` 로 500 이 난다(2026-10-24 회사·공고 페이지가 이걸로 깨졌다). 페이지는 전부 동적(ƒ)이고, 캐시가 필요하면 **데이터만** `unstable_cache` 로 감싼다(`lib/entry.ts` 가 그 예).
- 입구는 **루트 `/` 하나**다 — 질의 없는 `/recommendations` 는 `/` 로 리다이렉트한다(`(renewal)/recommendations/page.tsx`). 회사명만 적힌 질의는 공고번호 꼴이면 `/notices/*` 로 보낸다.
- `src/lib/` 서버 전용 읽기(`"server-only"`): `supabase-server`(service_role), `company`·`notice`·`saved`·`entry`·`changelog`. 브라우저에서 import 하면 키가 샌다.
- **Supabase 클라이언트가 둘이다 — 섞지 않는다.** `lib/supabase-server.ts`(service_role, 공개 데이터 SSR) vs `lib/supabase/{browser,server}.ts`(`@supabase/ssr` anon 키 + 쿠키 세션, 사용자 RLS 테이블 읽기·쓰기). 세션 갱신은 `src/proxy.ts`(Next 16 — `middleware.ts` 아님)가 매 요청 맡고 보호 경로 리다이렉트는 하지 않는다. 서버에서 현재 사용자는 `lib/auth.ts::getSessionUser`(`getUser`로 토큰 검증 — `getSession`은 쿠키를 믿으므로 쓰지 않는다). 메일 링크는 `app/auth/confirm/route.ts`가 세션으로 바꾸고 `safeNext`로만 복귀한다(recovery 는 `/reset/new` 강제).
- 로그인 필요 페이지: `/saved`(비로그인은 안내 판), `/welcome`(가입 확인 직후 우리 회사 저장 한 판 — `auth/confirm` 이 저장 회사 0곳이고 next 에 회사가 없을 때 보낸다. 폼은 `SaveCompanyForm` → `/api/saved/companies`, 검토함 빈 상태도 같은 폼), `/recommendations/report`(A4 인쇄용, `?company=` 없으면 `/recommendations`로). `/dev/foundation`은 noindex 컴포넌트 시트다. `/admin`은 `ADMIN_EMAILS`에 든 로그인 이메일만 — 아니면 404(403 아님), robots·nav 에 두지 않는다. 읽기 전용(`lib/admin.ts`), 쓰기 동작은 넣지 않는다.
- `src/app/api/` — route handler. `companies/suggest`(입구 자동완성 — **사업자번호는 응답에 싣지 않는다**), `companies/[bizrno]/profile`, 유사 공고. 브라우저가 백엔드를 직접 안 치게 하는 자리.
- `src/components/` — `entry/`·`results/`·`company/`·`notice/`·`board/`(옛 대화형 보드, 일부만 생존) + `ui/`(shadcn). `JsonLd.tsx` 가 구조화 데이터 주입을 한 곳에 모은다.
- SEO 비중이 크다 — 회사·공고 페이지의 메타·canonical·JSON-LD·색인 제외 규칙은 각각 이유가 있다(비공개 요청 0037, 깡통·폐업 noindex, **제목·설명에 수주 건수·평균 투찰률 비노출** 2026-09-22). 옮기거나 고칠 때 주석을 먼저 읽는다.
- GEO(AI 답변 인용용): `public/llms.txt`, `/faq`(FAQPage JSON-LD), 회사·공고 머리 아래 사실 문단. 여기에도 수주 건수·투찰률은 넣지 않는다.
- `frontend/CLAUDE.md`는 `@AGENTS.md`만 가리킨다(Next.js 16 지침).

## 주의사항 (gotchas)
- **Next.js 16**: 학습 데이터와 다른 breaking change 있음. 코드 작성 전 `frontend/node_modules/next/dist/docs/`의 해당 가이드 확인 (frontend/AGENTS.md 지침).
- **shadcn base-nova preset (@base-ui/react 기반)**: `Button`이 `asChild` 미지원 — 링크는 `<a>`에 직접 스타일.
- 브랜드 컬러는 **주황 `#f97316`** (2026-10-24 리뉴얼 배포로 에메랄드 `#047857` 교체). 토큰은 `src/app/globals.css`.
  - **주황은 선이지 면이 아니다** — 테두리·밑줄·점에만. 유일한 면 예외는 로고 타일.
  - **글자에는 `--color-orange-ink` (#b85510)** 를 쓴다. 브랜드 주황은 종이색 위 대비가 2.66:1 이라 큰 글자 기준 3.0 에도 못 미친다(2026-10-23 Lighthouse). Tailwind 로는 `text-orange-ink`. 선·테두리·타일은 `orange` 그대로.
- **금지어가 있다.** `frontend/scripts/check_*.py` 의 `BANNED` 목록 — "하세요"·"주십시오"·"예요"·"에요"·"넣으면"·"낼 수 있"·"이메일 구독"·"매직링크" 등. 공문 톤 유지와 "낼 수 있다"는 단정 금지 때문이다. 문구를 쓰면 검증이 잡는다.
- **디자인 리뉴얼 작업 전 `docs/design/README.md`를 먼저 읽는다.** 결정 사항(주황은 선이지 면이 아니다, 공문 톤 문체, 적합 점수 숫자 비노출·근거는 유지, 폐기한 컨셉 목록, 머리 장면은 로딩 가림막)이 거기 있고 최종 시안은 `prototypes/final/*.html`(그 밖의 `prototypes/*.html`은 폐기·중간안)(생성 스크립트 `scripts/`). 루트 `DESIGN.md`(개찰판·청색 장부)는 **폐기된 옛 디자인** 기록이다 — 현행이 아니다. 로고 자산은 `docs/design/brand/`.
- 한글 브랜드명은 "조달핏". 폰트 Pretendard, 다크모드/회원가입 강제 없음. **로그인은 이메일 + 비밀번호(8자 이상, 조합 규칙 없음) + 확인 메일 1회**(README §"이메일 + 비밀번호", 2026-10-17 결정) — 1차 시안의 매직링크는 폐기됐고 "매직링크"·"이메일 구독"은 금지어다. README 상단 §1의 "매직링크 = 알림 구독" 문장은 옛 기술이다.
  - **구글 로그인**(2026-10-28, Supabase 기본 공급자): `SocialButtons` → `signInWithOAuth` → `/auth/callback`(code 교환) → `lib/after-auth.ts`가 목적지를 정한다. 소셜 가입은 가입 폼을 안 거쳐 `user_consents`가 `''/''`로 생기므로 `/consent` 한 판에서 받아 `/api/consent`가 채운다(0064 — 빈 행만 한 번). 네이버는 Supabase 기본 목록에 없다(커스텀 OAuth 공급자로 시도 예정, 안 되면 카카오). 대시보드 설정: Providers → Google, URL Configuration → Redirect URLs 에 사이트 `/**`.
- `backend/.env`의 `SUPABASE_SERVICE_ROLE_KEY`는 RLS 우회 admin 키 — frontend/git 노출 금지. 환경변수 전체 목록은 README.md §9.
- `data/`는 gitignored 임시 수집 데이터.

### 화면에 숫자를 올릴 때 (필수)
2026-10-23 에 깔때기 숫자가 통째로 거짓이었던 걸 찾았다. 시안 생성기가 **운영에 없는 파이프라인**을 세고 있었다.

- **파이프라인 단계로 그리는 숫자는 앞 칸의 부분집합이어야 한다.** 결과 화면 깔때기는 `지금 입찰 가능 → 비슷한 순서로 추린 후보 → 자격 통과 → 추천` 네 칸이고 전부 중첩이다. "등록업종 허용 공고"는 단계가 아니다 — 후보는 그 집합이 아니라 전체에서 유사도 순으로 뽑는다(최종 20건 중 8건이 그 집합 밖이었다).
- **"지금 입찰 가능한 공고" 수는 `funnel_counts`(0057)** 다 — 마감 90일 이내 + 벡터 있음 + 참가자격 등록 안 지남. 단순 마감일 집계(옛 0056)를 쓰면 낼 수 없는 공고를 센다.
- **시안 숫자는 운영을 재생해서 얻는다.** `docs/design/scripts/gen_data.py` 가 `recommend()` 를 돌려 progress 이벤트로 센다. 화면용 사본을 따로 만들면 반드시 갈라진다.
- 수집 상태에 따라 무너지는 수치는 쓰지 않는다 — "오늘 등록된 공고"는 수집이 한 번 밀리면 한 자리가 된다. 얇으면 라벨을 "최근 등록"으로 바꿔 단다(`lib/entry.ts`).

### 배포
- 컷오버는 `renewal` → `main` PR 하나, 되돌리기는 그 PR revert. `main` push 로 **Vercel 자동 배포**(프론트), Railway(백엔드)는 별도.
- **배포 후 운영 빌드로 전 경로를 친다.** 개발 서버(:3000)는 정적 생성 경로를 안 타서 `DYNAMIC_SERVER_USAGE` 같은 사고를 못 잡는다. `npm run build && npx next start -p 3100` 로 띄워 확인한다.
- Lighthouse 목표 90 이상: `npx lighthouse <url> --only-categories=performance,accessibility,best-practices,seo --chrome-flags="--headless"`.

## 작업 원칙
- MVP는 임베딩 매칭 하나로만 일단 공개 가능한 최소 단위 우선
- 무료/유료 경계선 처음부터 설계: 무료(1회 분석, 주간 추천, 점수 숫자) / 유료 후보(실시간 알림, LLM 점수 설명 상세, 자격요건 매칭 상세)
- README.md가 상세 문서(알고리즘 근거, API 서비스 목록, 잡 시드 순서, 응답 예시) — 중복 기술하지 말고 참조

## 문서 지도
- `PRODUCT.md` — 사용자·성공 기준(재방문·재검색 정착)·카피 원칙·미해결 제품 사실. 제품 판단이 필요하면 여기부터.
- `docs/roadmap-2026-10.md` — 현재 Phase(측정 → DB 이전 → 디자인 → 약관 → 회원가입)와 남은 수동 작업.
- `docs/recommender/` — 평가 규칙(`evaluation.md`), 기준점(`baseline-*.md`), 실험(`exp-*.md`), 사용자 언어 변경 기록(`changelog.md`).
- `docs/design/README.md` — 리뉴얼 결정 사항(위 gotchas 참조). `docs/infra/` — Supabase 이전 절차. `docs/marketing/` — 일일 성적표.
- `docs/superpowers/plans/` — 실행한 구현 계획 원본(날짜 접두). 왜 그렇게 만들었는지 궁금하면 여기.

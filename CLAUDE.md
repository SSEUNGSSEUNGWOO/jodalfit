# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# jodalfit 프로젝트 가이드

## 컨셉
회사명/사업자번호 입력 → **등록업종 + 공급물품 (메인)** + 과거 수주 이력 (보조)을 동적 가중합한 회사 벡터 생성 → 신규 입찰공고와 유사도 매칭 → TOP 5 추천 + LLM 설명. 한국 공공조달(나라장터) 대상, B2B(중소 SI), 한국 시장 한정.

- 회사 식별/벡터 미확보 시 키워드 모드 폴백 (자유 텍스트 직접 임베딩).
- 톤: **"낙찰 예측"이 아닌 "검토할 만한 공고 디스커버리"**. 카피 원칙(점수 표현, 사업자번호 마스킹 등)은 README.md §12 — 어기지 말 것.
- 회사 벡터 동적 가중치: 수주 0건 γ(업종)=1.0 / 1~5건 γ=0.65,α=0.30 / 6+건 γ=0.50,α=0.45.

## 스택
- Backend: FastAPI (Python 3.12, uv) + slowapi rate limit
- Frontend: Next.js 16 (App Router, TypeScript, Tailwind v4, React 19)
- DB: Supabase (Postgres + pgvector HNSW + pg_trgm, Seoul region) — 백엔드는 service_role 키로 직접 접근
- Embedding: OpenAI `text-embedding-3-small` (1536d) / LLM 설명: `gpt-4o-mini`

## 명령어
- Backend 실행: `cd backend && uv run uvicorn app.main:app --reload` → :8000
- Frontend 실행: `cd frontend && npm run dev` → :3000
- Frontend lint: `cd frontend && npm run lint` / build: `npm run build`
- 잡 실행: `cd backend && uv run python -m jobs.<이름> [--days-back N ...]` (전체 시드 순서는 README.md §8)
- 연결 점검: `uv run python -m jobs.verify_setup` (row count) / `jobs.verify_phase2`
- 의존성 추가: `uv add <pkg>` (backend), `npm install <pkg>` (frontend)
- 테스트 프레임워크 없음. `jobs/test_api.py`·`probe_*.py`는 pytest가 아니라 API 탐색용 CLI 스크립트.

## 아키텍처 큰 그림

### 추천 파이프라인 (요청 경로)
`POST /recommendations` → `app/api/recommendations.py` → `app/services/recommend.py`:
1. `find_company` — pg_trgm fuzzy + 사업자번호로 회사 식별 (실패 시 키워드 모드)
2. `_search_with_embedding` — pgvector RPC(`match_bid_notices`)로 후보 TOP 100
3. **v2 랭커 (현재 기본)** — `app/recommender/pipeline.py::rank_v2`:
   자격 하드 제외(`qualifications.py`) → 가중치 score + breakdown(`score.py`) → 협업 시그널(peer 기관, `collaborative.py`) → MMR 다양성(`mmr.py`)
4. `app/services/explain.py` — LLM 상단 요약 1회 + 카드별 설명 (ThreadPoolExecutor 병렬)

주의: `recommend.py` ↔ `recommender/` 사이 순환 import를 함수 내 lazy import로 회피하고 있음 — 모듈 상단으로 끌어올리지 말 것. v1 rerank(소프트 감점)는 `recommend.py::rerank`에 아직 남아 있음.

### backend 구조
- `app/api/` — 라우터 (recommendations, events=행동 로깅)
- `app/core/` — pydantic-settings config, rate_limit, bot_guard
- `app/services/` — supabase/openai 클라이언트, recommend(후보 검색+v1), explain, viz(임베딩 시각화), search_log, notice_events
- `app/recommender/` — v2 랭킹 (pipeline / score / qualifications / mmr / collaborative)
- `jobs/` — 접두사 규칙: `ingest_*`(나라장터 API 수집) / `embed_*`(임베딩 생성) / `compute_company_vectors`(회사 벡터 통합) / `probe_*`(API 응답 탐색, 개발용) / `verify_*`·`check_*`·`diag_*`(검증/진단). 공통 fetch/페이징/타입 변환은 `jobs/_common.py`.
- `jobs/weekly_insight/` — 주간 콘텐츠 발행 파이프라인 (writer → evaluator → proofreader), `.claude/commands/weekly-market.md`·`weekly-picks.md` 스킬이 이걸 구동. 산출물은 frontend `/insights`에 노출.

### 데이터 파이프라인 (자동화)
`.github/workflows/daily-sync.yml` — 매일 KST 5시: ingest(공고/계약/낙찰/참가업체/사전규격/면허/지역...) → embed → compute_company_vectors. 각 스텝 `continue-on-error: true`.
`lunch-sync.yml` — KST 12:30 보조 사이클 (당일 오전 신규 공고).
나라장터 API 제약이 코드 전반에 배어 있음: 일일 호출 한도(UsrInfoService02 4,500/일), 조회범위 30일 초과 시 에러 → 청크 처리, 429 백오프 등.

### Supabase migrations
`supabase/migrations/0001~0015` — **CLI 아님, Dashboard SQL Editor에서 번호 순서대로 수동 실행**. 새 RPC를 쓰는 코드는 미적용 환경에서도 죽지 않게 try/except로 감싸 degrade시키는 패턴 유지 (예: `pipeline.py`의 0015 협업 RPC).

### frontend 구조
- `src/app/` — 랜딩, `recommendations/`(mode=company|keywords), `companies/[bizrno]`(SEO 회사 페이지), `notices/[bid_ntce_no]`(공고 라이프사이클 6단계), `insights/[type]`(주간 콘텐츠), sitemap/robots/JSON-LD (SEO 비중 큼 → 서버 컴포넌트 + `lib/supabase-server.ts` 직접 조회 적극 활용)
- `src/lib/api.ts` — 백엔드 호출 + mock 폴백. `NEXT_PUBLIC_USE_MOCK=true`면 백엔드 없이 디자인 확인 가능.
- `src/components/` — 플랫한 단일 폴더 (BidCard, MatchScore, Lifecycle 등) + `ui/`(shadcn)

## 주의사항 (gotchas)
- **Next.js 16**: 학습 데이터와 다른 breaking change 있음. 코드 작성 전 `frontend/node_modules/next/dist/docs/`의 해당 가이드 확인 (frontend/AGENTS.md 지침).
- **shadcn base-nova preset (@base-ui/react 기반)**: `Button`이 `asChild` 미지원 — 링크는 `<a>`에 직접 스타일.
- 브랜드 컬러는 **에메랄드 `#047857`** (2026-08 리브랜딩; README §13의 `#166534`은 구버전). 토큰은 `src/app/globals.css`.
- 한글 브랜드명은 "조달핏". 폰트 Pretendard, 다크모드/회원가입 강제 없음.
- `backend/.env`의 `SUPABASE_SERVICE_ROLE_KEY`는 RLS 우회 admin 키 — frontend/git 노출 금지. 환경변수 전체 목록은 README.md §9.
- `data/`는 gitignored 임시 수집 데이터.

## 작업 원칙
- MVP는 임베딩 매칭 하나로만 일단 공개 가능한 최소 단위 우선
- 무료/유료 경계선 처음부터 설계: 무료(1회 분석, 주간 TOP5, 점수 숫자) / 유료 후보(실시간 알림, LLM 점수 설명 상세, 자격요건 매칭 상세)
- README.md가 상세 문서(알고리즘 근거, API 서비스 목록, 잡 시드 순서, 응답 예시) — 중복 기술하지 말고 참조

# jodalfit 프로젝트 가이드

## 컨셉
회사명 입력 → **등록업종 + 공급물품 (메인)** + 과거 수주 이력 (보조)을 동적 가중합한 회사 벡터 생성 → 신규 입찰공고와 유사도 매칭 → TOP N 추천. 한국 공공조달(나라장터) 대상, B2B(중소 SI), 한국 시장 한정.

차별점: 키워드/업종코드 1:1 매칭이 아니라 "회사 정체성 + 실제 수주 이력"을 통합 임베딩으로 표현. 회사 식별/벡터 미확보 시 키워드 모드 폴백. **"낙찰 예측"이 아닌 "검토할 만한 공고 디스커버리"** 톤.

알고리즘 v0.2(현재): 동적 가중치 — 수주 0건 γ=1.0 / 1~5건 γ=0.65,α=0.30 / 6+건 γ=0.50,α=0.45. (2026-05-25 PIVOT)

## 스택
- Backend: FastAPI (Python, uv 패키지 관리)
- Frontend: Next.js (App Router, TypeScript, Tailwind)
- DB / Auth: Supabase (Postgres + pgvector + Auth, Seoul region)
- Embedding: OpenAI `text-embedding-3-small`

## 폴더
- `backend/` — FastAPI API + 데이터 수집/임베딩 잡 (별도 스크립트 또는 cron)
- `frontend/` — Next.js 웹 (SEO 중요 → SSR/SSG 적극 활용)
- `supabase/` — DB 스키마, migrations
- `data/` — 임시 수집/실험 데이터, gitignored

## 개발 명령어
- Backend: `cd backend && uv run uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- 의존성 추가: `uv add <pkg>` (backend), `npm install <pkg>` (frontend)

## 핵심 데이터 모델 (Supabase 기준 예정)
- `bid_notices` — 입찰공고 (공공데이터 API 적재), `embedding vector(1536)` 컬럼 포함
- `companies` — 회사 정보 (사업자번호 기준), `embedding vector(1536)` 회사 벡터
- `bid_awards` — 낙찰 이력 (회사-공고 연결)
- `subscribers` — 이메일 알림 구독자

## MVP 단계
1. 데이터 파이프라인 — 나라장터 입찰공고/낙찰정보 API → Supabase 적재
2. 임베딩 생성 — 공고문 임베딩 + 회사 벡터(과거 낙찰 임베딩 평균)
3. 결과 페이지 — 회사명 입력 → TOP 5 공고 + 이메일 수집
4. 메일 잡 — 주간 추천 메일 발송

## 작업 원칙
- MVP는 임베딩 매칭 하나로만 일단 공개 가능한 최소 단위 우선
- 자격요건 하드 필터(시평액/면허/SW사업자)는 후순위, SI 업종부터 도그푸딩
- 무료/유료 경계선 처음부터 설계: 무료(1회 분석, 주간 TOP5, 점수 숫자) / 유료 후보(실시간 알림, LLM 점수 설명, 자격요건 매칭 상세)

## 외부 의존
- 공공데이터포털 OpenAPI: 조달청 나라장터 입찰공고정보서비스 + 낙찰정보서비스 (API 키 보유)
- OpenAI Embeddings API
- Supabase (Seoul region 권장)

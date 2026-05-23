# jodalfit

> **"우리 회사가 따낼 만한 공공입찰, 30초 만에."**
> 회사명을 입력하면 과거 낙찰 이력 기반 임베딩 매칭으로 적합 입찰공고 TOP 5를 추천합니다.

[![GitHub](https://img.shields.io/badge/repo-SSEUNGSSEUNGWOO%2Fjodalfit-black?logo=github)](https://github.com/SSEUNGSSEUNGWOO/jodalfit)
![Status](https://img.shields.io/badge/status-WIP%20MVP-orange)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js%20%2B%20Supabase-2563EB)

---

## 1. 무엇을 만드는가

한국 공공조달(나라장터, G2B) 입찰공고 추천 사이트.

**컨셉:**
1. 사용자가 **회사명** 또는 **사업자번호**를 입력
2. 그 회사가 과거에 따낸 계약을 분석해 **회사 임베딩 벡터** 생성
3. 신규 입찰공고와 의미적으로 비교 → **TOP 5** 반환
4. **LLM**이 "왜 이 공고가 맞는지" 자연어로 설명

**경쟁사 대비 차별화 (검증된 3가지):**

| 일반 입찰 알리미 | jodalfit |
| --- | --- |
| 키워드 알림 | **과거 낙찰 이력 기반 임베딩 매칭** |
| 점수 없음 | 매칭 점수 + 게이지 + 적합도 라벨 |
| 이유 없음 | **LLM이 "왜 추천했는지" 자연어 설명** ⭐ |
| 자격 미확인 공고 다수 | **자격(면허/지역/마감) 하드 필터** |

---

## 2. 핵심 알고리즘

**회사 벡터 = 3가지 시그널 가중합**

```
회사 벡터 = α · 수주벡터 + β · 관심벡터 + γ · 업종벡터   (α+β+γ = 1)
```

| 시그널 | 소스 | 가중치 | 의미 |
| --- | --- | --- | --- |
| **수주(α)** | 계약 정보 → 따낸 공고들의 임베딩 평균 | 0.7 | 실제 revealed preference, 가장 강함 |
| **관심(β)** | 사전규격 의견 → 의견 낸 사양 임베딩 평균 | 0.1 | 부드러운 신호, 회사명 매핑 불확실 |
| **업종(γ)** | UsrInfoService 등록업종 + 공급물품 텍스트 | 0.2 | 콜드스타트(수주 0인 신생 회사) 대응 |

가용한 시그널만 정규화해서 가중합 → 콜드스타트 회사도 추천 가능.

**추천 파이프라인:**

```
회사명 입력
    ↓
[1] 회사 식별 (pg_trgm fuzzy + 사업자번호 매칭)
    ↓
[2] 하드 필터  ← 못 들어가는 공고 제거 (자격/지역/마감/예산)
    ↓
[3] pgvector 코사인 검색  ← 통과 공고 중 TOP 100
    ↓
[4] 휴리스틱 rerank  ← 마감 임박 패널티, 지역 매칭 보너스 등
    ↓
[5] LLM 설명 생성  ← gpt-4o-mini로 "왜 추천했는지"
    ↓
TOP 5 + 매칭 이유 반환
```

**핵심 통찰** *(코덱스 협의 결과)*:
**"의미 유사도" 보다 "실제 입찰 가능성"이 더 큰 결정 요인**입니다. 자격이 안 맞으면 매칭 점수 100점이어도 못 들어갑니다. 그래서 하드 필터가 메인, 임베딩은 후보 정렬용 보조.

---

## 3. 데이터 라이프사이클

조달 단계마다 별도 OpenAPI가 있고, jodalfit은 **모든 단계를 누적**합니다.

```
[발주계획] → [사전규격(+의견)] → [입찰공고] → [낙찰/개찰] → [계약]
       선행지표        SW식별, 관심신호       추천 대상     참여신호    수주신호
```

| 단계 | API 서비스 | 핵심 가치 |
| --- | --- | --- |
| 발주계획 | `OrderPlanSttusService` | "1개월 전" 알림 가능 |
| 사전규격 | `HrcspSsstndrdInfoService` | `swBizObjYn` SW 사업 자동 필터 |
| 사전규격 의견 | 동일 (`getPublicPrcureThngOpinionInfo*`) | **회사 관심 신호** (콜드스타트 해결) |
| 입찰공고 | `PubDataOpnStdService/getDataSetOpnStdBidPblancInfo` | 추천 대상 공고 풀 |
| 입찰공고 자격 | `BidPublicInfoService` (면허제한/참가지역) | **자격 하드 필터** |
| 낙찰/개찰 | `ScsbidInfoService` | **참가 업체 정보** = 회사 3번째 시그널 |
| 계약 | `PubDataOpnStdService/getDataSetOpnStdCntrctInfo` | **사업자번호 → 수주 이력** |
| 회사 마스터 | `UsrInfoService02` | 등록업종, 공급물품, 부정당 제재 |
| 업종 lookup | `IndstrytyBaseLawrgltInfoService` | 자격요건 매핑 |

---

## 4. 아키텍처

```
┌───────────────┐    POST /recommendations    ┌────────────────────┐
│  Next.js 16   │ ───────────────────────────► │  FastAPI 백엔드    │
│  (Pretendard) │ ◄─────────────────────────── │  + Supabase client │
└───────────────┘    TOP 5 + LLM explanation   └──────────┬─────────┘
                                                          │
        ┌─────────────────────────────────────────────────┤
        │                                                 │
        ▼                                                 ▼
┌──────────────────┐                              ┌──────────────────────┐
│  Supabase        │                              │  공공데이터포털       │
│  (Postgres +     │                              │  나라장터 8개 API    │
│   pgvector HNSW) │                              │  data.go.kr          │
└──────────────────┘                              └──────────────────────┘
        ▲
        │   임베딩 적재 / 회사 벡터 생성
        │
┌────────────────┐
│  ingest 잡들   │   ─── 매일 cron (예정)
│  embed 잡들    │
│  compute 잡    │
└────────────────┘
                    OpenAI text-embedding-3-small (1536d)
                    OpenAI gpt-4o-mini (추천 이유 설명)
```

---

## 5. 폴더 구조

```
jodalfit/
├── backend/                   FastAPI + 데이터 수집/임베딩 잡
│   ├── app/
│   │   ├── api/               FastAPI 라우터 (POST /recommendations)
│   │   ├── core/              config (pydantic-settings)
│   │   ├── services/          supabase / openai 클라이언트, recommend, explain
│   │   └── main.py            FastAPI 진입점
│   ├── jobs/                  데이터 수집 + 임베딩 잡 (CLI)
│   │   ├── _common.py         API fetch + 페이징 + 타입 변환 + 로깅
│   │   ├── ingest_*.py        나라장터 OpenAPI 수집 잡들
│   │   ├── embed_*.py         OpenAI 임베딩 생성 잡들
│   │   ├── compute_company_vectors.py    회사 벡터 통합 (batched)
│   │   ├── probe_*.py         endpoint 응답 구조 탐색 (개발용)
│   │   ├── verify_*.py        Supabase 연결 + row count 검증
│   │   └── diag_*.py          데이터 정합성 진단
│   ├── pyproject.toml         uv 패키지
│   ├── uv.lock
│   └── .env.example           NARAJANGTEO_API_KEY, OPENAI_API_KEY, SUPABASE_*
│
├── frontend/                  Next.js 16 + TS + Tailwind v4
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                  랜딩 페이지
│   │   │   ├── recommendations/page.tsx  추천 결과
│   │   │   ├── layout.tsx                Pretendard 폰트, 메타데이터
│   │   │   └── globals.css               컬러 토큰 (Navy/Teal/Ink)
│   │   ├── components/                   13개 UI 컴포넌트
│   │   │   ├── BidCard.tsx               ★ 가장 중요한 카드
│   │   │   ├── MatchScore.tsx
│   │   │   ├── ExplanationBlock.tsx      LLM 추천 이유 (편집 quote rail)
│   │   │   ├── DDayBadge.tsx             마감 임박 색상 단계
│   │   │   └── ...
│   │   ├── lib/
│   │   │   ├── api.ts                    백엔드 호출 + Mock fallback
│   │   │   ├── mock-data.ts              UI 미리보기용
│   │   │   └── utils.ts                  cn, maskBizrno, formatKRW, scoreLabel
│   │   └── types/recommendations.ts
│   └── package.json
│
├── supabase/
│   └── migrations/             스키마 + RPC
│       ├── 0001_init.sql                 12개 테이블 + pgvector + pg_trgm
│       ├── 0002_bizrno_normalize.sql     사업자번호 정규화 generated column
│       ├── 0003_match_rpc.sql            find_companies / match_bid_notices RPC
│       ├── 0004_embedding_update_rpc.sql 임베딩 batch UPDATE RPC
│       └── 0005_license_rgn_tables.sql   면허 + 지역 제한 테이블
│
├── data/                       임시 수집 데이터 (gitignored)
│   └── api_probe/              probe 응답 dump
│
├── docs/                       설계 문서 (예정)
├── README.md                   (이 파일)
└── CLAUDE.md                   프로젝트 가이드 (한국어)
```

---

## 6. 스택

| 영역 | 선택 | 이유 |
| --- | --- | --- |
| **백엔드** | FastAPI (Python 3.12, uv) | 비동기 잘 됨, 한국 데이터 다루기 편함 |
| **DB / Auth** | Supabase (Postgres + pgvector + pg_trgm) | pgvector HNSW로 임베딩 검색, fuzzy 회사명 매칭, Auth 내장 |
| **임베딩** | OpenAI `text-embedding-3-small` (1536d) | 한국어 성능 좋음, 비용 저렴 ($0.02/1M tokens) |
| **LLM 설명** | OpenAI `gpt-4o-mini` | 추천 이유 생성용, 비용/품질 균형 |
| **프론트엔드** | Next.js 16 (App Router, TS, Tailwind v4) | SSR/SSG, SEO 강점, React 19 |
| **UI** | shadcn 패턴 + Radix UI primitive + Pretendard | 한국 B2B 신뢰감 + 접근성 |

---

## 7. 셋업

### 사전 준비

1. **Python 3.12** + [uv](https://docs.astral.sh/uv/) 설치
2. **Node.js 20+** + npm
3. **Supabase 프로젝트** (Seoul region 권장)
4. **공공데이터포털 API 키** — [data.go.kr](https://data.go.kr)에서 아래 8개 서비스 활용신청
   - 조달청_나라장터 공공데이터개방표준서비스
   - 조달청_나라장터 사전규격정보서비스
   - 조달청_나라장터 발주계획현황서비스
   - 조달청_나라장터 사용자정보 서비스 (UsrInfoService02)
   - 조달청_나라장터 업종 및 근거법규서비스
   - 조달청_나라장터 계약과정통합공개서비스
   - 조달청_나라장터 입찰공고정보서비스
   - 조달청_나라장터 낙찰정보서비스
5. **OpenAI API 키** — [platform.openai.com](https://platform.openai.com)

### Supabase 스키마 적용

`supabase/migrations/*.sql`을 **번호 순서대로** Dashboard → SQL Editor에서 실행:

```
0001_init.sql                      # 기본 12개 테이블 + pgvector + pg_trgm
0002_bizrno_normalize.sql          # 사업자번호 정규화 컬럼
0003_match_rpc.sql                 # 추천 검색용 RPC
0004_embedding_update_rpc.sql      # 임베딩 batch UPDATE RPC
0005_license_rgn_tables.sql        # 면허제한 + 참가지역 테이블
```

### 백엔드 셋업

```bash
cd backend
cp .env.example .env
# .env 파일에 다음 4개 키 채우기:
# NARAJANGTEO_API_KEY=...        ← 공공데이터포털 일반인증키 (Decoded)
# OPENAI_API_KEY=sk-...          ← OpenAI API key
# SUPABASE_URL=https://...       ← Supabase Dashboard → Settings → API
# SUPABASE_SERVICE_ROLE_KEY=...  ← service_role (anon 아님, 매우 민감)

uv sync
uv run python -m jobs.verify_phase2  # 연결 점검
uv run uvicorn app.main:app --reload  # → http://localhost:8000
```

### 프론트엔드 셋업

```bash
cd frontend
cp .env.local.example .env.local
# .env.local:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# NEXT_PUBLIC_USE_MOCK=false  (또는 true로 두면 백엔드 없이 디자인 확인 가능)
# NEXT_PUBLIC_SUPABASE_URL=...
# NEXT_PUBLIC_SUPABASE_ANON_KEY=...   ← anon 키, frontend에서만 사용

npm install
npm run dev  # → http://localhost:3000
```

---

## 8. 데이터 파이프라인 (잡 실행 순서)

처음 시드 적재 시 권장 순서:

```bash
cd backend

# === 1. 데이터 수집 ===
# 입찰공고 1주일치 (최대 한도)
uv run python -m jobs.ingest_bid_notices --days-back 7 --batch-size 100

# 계약 1주일치 (회사 수주 신호의 원천)
uv run python -m jobs.ingest_contracts --days-back 7 --batch-size 100

# 사전규격 (SW 사업만)
uv run python -m jobs.ingest_pre_specs --days-back 7

# 사전규격 의견 (회사 관심 신호)
uv run python -m jobs.ingest_pre_spec_opinions --days-back 7

# 발주계획 (선행지표, 분기별이라 sparse)
uv run python -m jobs.ingest_order_plans --months-back 6

# 회사 마스터 풍부화 (UsrInfoService02 — 변경일 기반, 시드는 길게)
uv run python -m jobs.ingest_companies_userinfo --days-back 90

# 부정당 제재 (자격 박탈된 회사 자동 필터)
uv run python -m jobs.ingest_restricted_corps --days-back 90

# 면허제한 / 참가지역 (자격 하드 필터의 핵심)
uv run python -m jobs.ingest_license_limit --days-back 7
uv run python -m jobs.ingest_rgn_limit --days-back 7

# 낙찰자 목록 (참여 신호)
uv run python -m jobs.ingest_scsbid_winners --days-back 7


# === 2. 임베딩 생성 ===
uv run python -m jobs.embed_bid_notices --limit 100000 --batch 50
uv run python -m jobs.embed_pre_specs --limit 10000 --batch 50
uv run python -m jobs.embed_order_plans --limit 5000 --batch 50


# === 3. 회사 벡터 통합 ===
uv run python -m jobs.compute_company_vectors --limit 25000 --chunk-size 100


# === 검증 ===
uv run python -m jobs.verify_setup
```

매일 자동 갱신은 `--days-back 1`로 cron 등록.

---

## 9. 환경변수

`backend/.env`:

| 키 | 설명 | 예시 |
| --- | --- | --- |
| `NARAJANGTEO_API_KEY` | 공공데이터포털 일반인증키 (Decoded 형식) | `3393eec4c0...` |
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-proj-...` |
| `SUPABASE_URL` | Supabase 프로젝트 URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role 키 (admin 권한, 매우 민감) | `eyJhbG...` |
| `CORS_ORIGINS` | (선택) JSON 배열 | `["http://localhost:3000"]` |

`frontend/.env.local`:

| 키 | 설명 |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 URL (`http://localhost:8000`) |
| `NEXT_PUBLIC_USE_MOCK` | `true` 시 백엔드 없이 mock 데이터로 디자인 미리보기 |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon 키 (frontend 전용) |

> ⚠️ **보안 주의**:
> - `SUPABASE_SERVICE_ROLE_KEY`는 **RLS를 우회하는 admin 권한**. 절대 frontend나 git에 노출 금지.
> - `OPENAI_API_KEY` 노출 시 누군가 비용을 발생시킬 수 있음.
> - 모든 키는 `.env`에 직접 입력. 채팅/메신저로 공유 금지.

---

## 10. API 사용 예시

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "주식회사 제이오달소프트",
    "limit": 5,
    "with_explanation": true
  }'
```

응답 형식:

```jsonc
{
  "company": {
    "bizrno": "1378802300",
    "corp_nm": "주식회사 제이오달소프트",
    "rgn_nm": "서울특별시 강남구",
    "corp_bsns_div_nm": "소프트웨어개발"
  },
  "results": [
    {
      "bid_ntce_no": "R26BK01533268",
      "bid_ntce_nm": "한국교육학술정보원 ... 유지관리 용역",
      "bsns_div_nm": "용역",
      "bid_clse_date": "2026-06-01",
      "presmpt_prce": 178000000,
      "dmnd_instt_nm": "한국교육학술정보원",
      "base_similarity": 0.871,
      "bonus": 0.05,
      "score": 0.921,
      "explanation": "최근 3년간 교육기관 대상 시스템 유지보수 수주 이력이 많고..."
    }
    // ...
  ]
}
```

---

## 11. MVP 단계별 발전 계획

| 버전 | 상태 | 핵심 변화 |
| --- | --- | --- |
| **v0.1** | ✅ 진행 중 | 수주 시그널 + 코사인 + 마감/지역 하드 필터 + LLM 설명 |
| v0.2 | ⏳ | 자격 하드 필터 강화 (면허제한 정밀 매칭), 관심 시그널 활성화 |
| v0.3 | ⏳ | 참가업체 시그널(개찰결과) 적재, 시간가중 exp decay (반감기 1년) |
| v0.4 | ⏳ | LightGBM learning-to-rank (수주/참여/노출 데이터 누적 후) |

자세한 결정 근거는 [`docs/`](./docs/) 또는 깃 커밋 히스토리.

---

## 12. 사용 카피 원칙 (어기지 말기)

- ❌ "낙찰 가능성 92%" → ✅ **"매칭 점수 92 / 매우 적합"**
- ❌ 사업자번호 전체 노출 → ✅ **"137-XX-X4567" 형식 마스킹**
- ❌ "AI가 다 해준다" → ✅ **"왜 추천했는지" 자연어 설명**
- ❌ 데이터 출처/갱신일 누락 → ✅ **"매일 갱신 · 나라장터 기반" 항상 명시**
- ❌ 다크모드, 회원가입 강제, 카카오 로그인 → ✅ **무료로 먼저 확인 (회원가입 X)**

---

## 13. 디자인 토큰

```css
/* Korean Financial Bureau — refined data SaaS */
--color-navy:  #12355B;   /* 헤더, 주요 텍스트, 신뢰 영역 */
--color-blue:  #2563EB;   /* CTA, 링크, 선택 상태 */
--color-teal:  #14B8A6;   /* 매칭 점수, 적합도, 긍정 신호 */
--color-bg:    #F7F9FC;   /* 배경 */
--color-ink:   #111827;   /* 본문 */
--color-warning: #F59E0B; /* 마감 임박 (D-3 ~ D-5) */
--color-danger:  #DC2626; /* 마감 직전 (D-1 ~ D-2) */

--font-sans: 'Pretendard Variable', system-ui, ...;
```

---

## 14. 참고 자료

- [공공데이터포털](https://www.data.go.kr) — 나라장터 OpenAPI
- [국가종합전자조달 나라장터](https://www.g2b.go.kr) — 공식 사이트
- [pgvector](https://github.com/pgvector/pgvector) — Postgres vector extension
- [Pretendard](https://github.com/orioncactus/pretendard) — 한글 폰트
- [Supabase](https://supabase.com/docs) — DB / Auth 플랫폼

---

## 15. 라이선스

비공개 프로젝트. © 2026 jodalfit.

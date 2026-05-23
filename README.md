# jodalfit

회사명을 입력하면 과거 낙찰 이력 기반 임베딩 매칭으로 적합한 나라장터 입찰공고를 추천하는 서비스.

## Stack

- **Backend**: FastAPI (Python, uv)
- **Frontend**: Next.js (TypeScript, Tailwind)
- **DB / Auth**: Supabase (Postgres + pgvector + Auth)
- **Embedding**: OpenAI `text-embedding-3-small`

## Folder structure

```
jodalfit/
├── backend/      # FastAPI 서버 + 데이터 수집/임베딩 잡
├── frontend/     # Next.js 웹
├── data/         # 임시 수집 데이터 (gitignored)
├── docs/         # 설계 문서
├── supabase/     # DB 스키마, migrations
└── CLAUDE.md
```

## Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env  # API 키 채우기
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## 환경변수

`backend/.env`:
- `NARAJANGTEO_API_KEY` — 공공데이터포털 나라장터 API 키
- `OPENAI_API_KEY` — 임베딩용
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — Supabase 접속

`frontend/.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

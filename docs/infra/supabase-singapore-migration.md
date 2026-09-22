# Supabase 뭄바이 → 싱가포르(Medium) 이전 절차서

작성 2026-09-22. 현재 프로젝트 `ivjjzsvztsgrbyruenff` (ap-south-1, Micro) → 새 프로젝트 (ap-southeast-1, Medium).

## 0. 왜 옮기나 — 측정 근거

| 문제 | 측정값 (2026-09-21~22) |
|---|---|
| 버퍼 풀이 데이터에 비해 너무 작다 | DB 8.5GB vs `shared_buffers` 256MB (33배). 작업 세트만 2.6GB |
| 디스크 I/O 예산이 바닥난다 | 같은 55행 인덱스 스캔이 아침 1,249ms → 오후 8,817ms (읽기 1회 ~57ms) |
| 백엔드와 DB가 멀다 | Railway·Vercel은 싱가포르, DB만 뭄바이. 추천 1회에 DB 왕복 12회 이상, 1회 ~100ms |

코드 쪽 최적화(0038·0039 MV, 병렬화 등)로 추천 API는 7~9초 → 1.7초가 됐지만, 남은 1.7초는 대부분 뭄바이 왕복 바닥이다. 둘 다 싱가포르면 1회 ~5ms.

> **뭄바이 프로젝트를 Medium으로 올리지 말 것.** Supabase는 리전을 바꿀 수 없어 어차피 새 프로젝트를 만든다. 올린 비용이 버려진다.

---

## 1. 준비 (전날)

- [ ] **대시보드에 다른 리전으로 복제·복원하는 기능이 있는지 먼저 확인.** 있으면 2~4단계를 그걸로 대신하고 5단계부터 따라간다. 이 문서는 그 기능이 없을 때의 수동 절차다.
- [ ] PostgreSQL **17** 클라이언트 도구(`pg_dump`, `pg_restore`, `psql`) 설치. 서버가 17.6이라 클라이언트도 17이어야 한다.
- [ ] 작업 폴더: `C:\dev\ops\jodalfit\migrate\` (덤프는 무거운 I/O라 C:, 끝나면 D:로 백업 복사)
- [ ] 두 프로젝트의 **Direct connection** 문자열과 DB 비밀번호 (대시보드 → Connect). pooler 말고 direct.
- [ ] 작업 시간대: **새벽** (사용자 없음). 단 KST 05:00 daily-sync, 매시 :05 hourly-sync, KST 07:30~08:10 MV 갱신과 겹치지 않게.

---

## 2. 쓰기 멈추기

이전 도중 옛 DB에 쓰인 데이터는 새 DB로 안 넘어간다. 수집 잡부터 멈춘다.

```powershell
# GitHub Actions 수집 잡
gh workflow disable daily-sync.yml
gh workflow disable lunch-sync.yml
# 로컬 스케줄 태스크 (메모리: local-sync-scheduled-tasks)
Disable-ScheduledTask -TaskName jodalfit-daily-sync
Disable-ScheduledTask -TaskName jodalfit-hourly-sync
```

백엔드(Railway)는 계속 돌려도 된다. 그동안 쌓이는 `search_logs`·추천 캐시·`notice_events` 쓰기는 전환 뒤 잃어도 되는 데이터다.

---

## 3. 새 프로젝트 만들기

- [ ] 리전 **Southeast Asia (Singapore)**, 컴퓨트 **Medium**
- [ ] 확장 켜기 (SQL Editor). **스키마를 옛 프로젝트와 똑같이 맞춘다.** `vector`와 `pg_trgm`은
  옛 쪽에서 `public`에 있다. 새 프로젝트는 확장을 기본으로 `extensions`에 만드는데, 덤프는 타입을
  `public.vector(1536)`처럼 스키마를 붙여 적으므로 스키마가 다르면 테이블 생성이 전부 실패한다.
  `pg_dump -n public`은 확장 자체를 덤프하지 않으니 여기서 먼저 만든다.

```sql
create extension if not exists vector   schema public;      -- 옛 쪽: public
create extension if not exists pg_trgm  schema public;      -- 옛 쪽: public
create extension if not exists pg_cron;                     -- pg_catalog
create extension if not exists pg_stat_statements schema extensions;
create extension if not exists pgcrypto           schema extensions;
create extension if not exists "uuid-ossp"        schema extensions;
```

---

## 4. 스키마·데이터 옮기기

### 왜 마이그레이션 파일(0001~0039)을 다시 돌리지 않나

파일과 실제 DB가 이미 어긋나 있다.
- `0018`이 두 개다. `0018_insight_stats_rpc.sql`은 **git에 없는데 DB엔 적용돼 있다** (`insight_bid_rate_stats` 함수).
- 인덱스 일부는 pg_cron 1회성 잡으로 만들었다(0030 등).
- 0037은 MV 재생성 부분을 파일에서 뺐다(락 사고 후 롤백).

그래서 **현재 DB의 스키마를 그대로 떠 간다.**

### 4-1. 스키마

```powershell
cd C:\dev\ops\jodalfit\migrate
$OLD = "postgresql://postgres:<옛비밀번호>@db.ivjjzsvztsgrbyruenff.supabase.co:5432/postgres"
$NEW = "postgresql://postgres:<새비밀번호>@db.<새ref>.supabase.co:5432/postgres"

pg_dump $OLD --schema-only --schema=public --no-owner --no-privileges -f schema.sql
psql $NEW -v ON_ERROR_STOP=1 -f schema.sql
```

`schema.sql`에 MV 정의도 들어간다. MV는 데이터 없이 만들어지니 6단계에서 채운다.

### 4-2. 데이터

옮기지 않는 것:

| 테이블 | 크기 | 이유 |
|---|---|---|
| `company_recommendations` | 514MB | 추천 캐시. 표본 150건 중 135건이 이미 무효(마감 지난 공고 제거 후 5건 미만). 알아서 다시 쌓인다 |
| `notice_events` | 396MB | 누적 110만 건 중 실사용자 행동은 소수, 나머지는 내부 SSR impression 찌꺼기(CLAUDE.md). **옮길지 승우님이 결정** — 옮기려면 아래 exclude에서 빼면 된다 |
| MV 5개 | — | 6단계에서 새로 계산 |

```powershell
pg_dump $OLD --data-only --schema=public --no-owner `
  --exclude-table-data=public.company_recommendations `
  --exclude-table-data=public.notice_events `
  -Fd -j 4 -f data_dump

pg_restore -d $NEW --data-only --no-owner --disable-triggers -j 4 data_dump
```

`bid_notices`가 3.9GB(벡터 TOAST 3.2GB)라 가장 오래 걸린다. 뭄바이 쪽이 I/O 예산이 바닥난 상태면 덤프가 매우 느리니, 예산이 회복된 새벽에 할 것.

### 4-3. 행 수 대조

양쪽에서 같은 쿼리를 돌려 비교한다.

```sql
select 'companies' t, count(*) from companies union all
select 'bid_notices', count(*) from bid_notices union all
select 'contracts', count(*) from contracts union all
select 'award_results', count(*) from award_results union all
select 'company_industries', count(*) from company_industries union all
select 'company_supply_products', count(*) from company_supply_products union all
select 'search_logs', count(*) from search_logs;
```

**그리고 반드시 — 비공개 요청 플래그가 넘어왔는지:**

```sql
select bizrno_norm, corp_nm, optout_at from companies where optout_at is not null;
-- 수건설안전지도사사무소(4626300687) 1건이 나와야 한다. 안 나오면 전환 금지.
```

---

## 5. 벡터 인덱스 만들기

`bid_notices`엔 지금 **벡터 인덱스가 없다.** 2026-09-18 IVFFlat 빌드가 `maintenance_work_mem`(64MB) 부족으로 실패했고, 재시도는 3시간 37분 뒤 취소됐다. Medium에서 메모리를 올려 새로 만든다.

```sql
set maintenance_work_mem = '256MB';
set statement_timeout = 0;
create index concurrently if not exists bid_notices_embedding_ivf_idx
  on bid_notices using ivfflat ((embedding::halfvec(1536)) halfvec_cosine_ops)
  with (lists = 600);
```

`create index concurrently`는 트랜잭션 밖이어야 한다. SQL Editor에서 이 블록만 따로 실행하거나 `psql $NEW`로 실행. 끝나면 확인:

```sql
select c.relname, i.indisvalid from pg_index i join pg_class c on c.oid = i.indexrelid
where c.relname = 'bid_notices_embedding_ivf_idx';   -- indisvalid = true 여야 한다
```

`companies_embedding_idx`(HNSW)는 2026-09-22 뭄바이에서 드롭했고 쓰는 곳도 껐다(`match_companies`). 새로 만들지 않는다.

---

## 6. MV 채우기와 pg_cron 잡

```sql
set statement_timeout = 0;
refresh materialized view sitemap_urls;
refresh materialized view industry_companies;
refresh materialized view industry_directory;
refresh materialized view institution_repeat_stats_mv;
refresh materialized view institution_bid_rate_mv;
```

**그리고 MV 공개 권한 회수** — 스키마를 `--no-privileges`로 떠 왔으므로 새 프로젝트의 기본 권한이 붙어
MV 5개를 공개 키(anon)로 읽을 수 있게 된다. MV엔 RLS가 없다. `supabase/migrations/0041_revoke_public_mv_access.sql`을
그대로 실행하고 확인한다.

```sql
select c.relname, has_table_privilege('anon', c.oid, 'select') as anon
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'm';   -- 전부 false 여야 한다
```

pg_cron 잡은 스키마 덤프에 안 들어간다. 옛 프로젝트와 같은 4개를 다시 만든다. **시간대는 이참에 옮길 것** — 기존 KST 08:00·08:10 갱신은 사용자 트래픽이 시작되는 시간과 겹쳐 그동안 사이트맵이 20초대가 됐다. 아래는 daily-sync(KST 05:00) 이후·트래픽 이전으로 당긴 값이다. daily-sync가 실제로 몇 시에 끝나는지 로그로 보고 조정할 것.

```sql
select cron.schedule('refresh-institution-repeat-stats', '30 21 * * *',   -- KST 06:30
  $$set statement_timeout = 0; refresh materialized view concurrently institution_repeat_stats_mv$$);
select cron.schedule('refresh-institution-bid-rate', '40 21 * * *',       -- KST 06:40
  $$set statement_timeout = 0; refresh materialized view concurrently institution_bid_rate_mv$$);
select cron.schedule('refresh-sitemap-urls', '0 22 * * *',                -- KST 07:00
  $$set statement_timeout = 0; refresh materialized view concurrently sitemap_urls$$);
select cron.schedule('refresh-industry-directory', '10 22 * * *',         -- KST 07:10
  $$set statement_timeout = 0; refresh materialized view concurrently industry_companies; refresh materialized view concurrently industry_directory$$);
```

명령 4개는 옛 프로젝트 `cron.job`과 대조해 같음을 확인했다(2026-09-22). 시간만 바꿨다.

---

## 7. 환경변수 교체

`SUPABASE_URL`·키를 참조하는 곳 전부. 프로젝트 ID가 하드코딩된 곳은 `backend/.env`와 `frontend/.env.local`뿐이다(2026-09-22 전수 검색).

| 위치 | 바꿀 값 |
|---|---|
| `backend/.env` | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — 로컬 스케줄 태스크·잡·마케팅 리포트가 이걸 쓴다. **`DATABASE_URL`도** (직접 Postgres 연결 — `jobs/backfill_companies_basic.py`, `jobs/check_business_status.py`가 쓴다. 지금은 뭄바이 세션 풀러 `aws-1-ap-south-1.pooler.supabase.com:5432`) |
| Railway 백엔드 | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| Vercel 프론트 | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| GitHub Actions secrets | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (daily-sync·lunch-sync) |
| `frontend/.env.local` | 로컬 개발용 같은 값 |
| Claude 메모리 | `infra-hosting-and-db-io`의 프로젝트 ID·리전 |

Railway·Vercel은 값을 바꾼 뒤 **재배포**해야 반영된다.

---

## 8. 전환 후 검증

백엔드 토큰은 `frontend/.env.local`의 `INTERNAL_API_TOKEN`.

```powershell
$TOK = (Select-String -Path C:\dev\personal\jodalfit\frontend\.env.local -Pattern '^INTERNAL_API_TOKEN=').Line.Split('=',2)[1]

# ① 추천 API 구간 시간 — total 이 1.7초보다 확실히 작아야 한다 (기대 1초 미만)
curl.exe -s -o NUL -D - -X POST https://jodalfit-production.up.railway.app/recommendations `
  -H "Content-Type: application/json" -H "X-Internal-Token: $TOK" `
  -d '{\"query\":\"4751201453\",\"mode\":\"company\",\"limit\":20,\"with_explanation\":false,\"algorithm\":\"v2\"}' | Select-String server-timing

# ② 비공개 요청 회사가 여전히 404
curl.exe -s -o NUL -w "%{http_code}`n" https://jodalfit.co.kr/companies/4626300687

# ③ 사이트맵
curl.exe -s -o NUL -w "%{http_code} %{time_total}s`n" https://jodalfit.co.kr/sitemap/4.xml
```

- [ ] ① `total` 1초 안팎, ② `404`, ③ `200`
- [ ] 회사 페이지 몇 곳 cold 응답 (처음 보는 bizrno로) — 지금 0.8~2.5초
- [ ] 잡 재개 후 첫 daily-sync가 성공하는지 `ingest_runs`로 확인

---

## 9. 되돌리기

**옛 프로젝트는 검증이 끝날 때까지 지우지 않는다.** 문제가 생기면 7단계 값을 옛 프로젝트로 되돌리고 재배포하면 끝이다. 그 사이 새 DB에 쓰인 데이터는 잃는다.

---

## 10. 이전 뒤 할 일

- [ ] 잡 재개: `gh workflow enable daily-sync.yml`, `gh workflow enable lunch-sync.yml`, `Enable-ScheduledTask -TaskName jodalfit-daily-sync`, `Enable-ScheduledTask -TaskName jodalfit-hourly-sync`
- [ ] `compute_company_vectors` 한 번 수동 실행 — 재료가 있는데 벡터가 없는 회사 953개가 밀려 있다 (뭄바이에선 쓰기 타임아웃으로 못 끝냈다)
- [ ] 5단계 인덱스가 valid 면 `frontend/src/lib/company.ts`의 `SIMILAR_AWARDEES_ENABLED`를 `true`로 → 회사 페이지 경쟁사 섹션이 처음으로 실제 데이터를 보여준다. 켠 뒤 cold 페이지 응답이 다시 8초대가 되지 않는지 확인
- [ ] 1주일 문제없으면 옛 프로젝트 정리
- [ ] nolai 컴퓨트 내리기 (유료 컴퓨트라 MCP로는 pause 불가 — 대시보드에서)
- [ ] CLAUDE.md의 "Seoul region"을 실제 리전으로 고치기
- [ ] **개인정보처리방침의 국외 이전 표를 고치기** — `frontend/src/app/privacy/page.tsx`의 Supabase 처리 위치 "인도 (AWS 뭄바이)" → 싱가포르. 방침이 바뀌므로 `frontend/src/lib/privacy.ts`의 `PRIVACY_VERSION`(시행일)도 올린다. 공개된 방침과 실제가 다르면 안 된다

# 후보 검색 업종 채널(hybrid) 운영 적용 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. 체크박스로 진행 추적.

**Goal:** 추천 후보 검색에 "회사 등록업종을 허용하는 공고 안에서 벡터 검색" 채널을 추가하고 기존 dense 채널과 번갈아 합친다. 근거·수치: `docs/recommender/exp-2026-10-14-retrieval.md`.

**Architecture:** RPC `match_bid_notices`에 `industry_names text[]` 파라미터(0044). `_search_with_embedding`이 설정 `RECO_RETRIEVAL=hybrid`일 때 RPC를 두 번 병렬 호출해 업종 채널→dense 순으로 번갈아 합친 뒤, 기존 dedup·풀 컷·rank_v2로 진입. 0044 미적용이면 dense 로 degrade. 평가 하네스 `--retrieval` 기본값을 같은 설정에서 읽어 운영과 채점표가 항상 같은 방식을 재생한다.

**Tech Stack:** Postgres SQL 함수, FastAPI(backend/app/services/recommend.py), pydantic-settings.

---

### Task 1: 0044 마이그레이션 + hybrid 검색 + 설정 + 하네스 기본값

**Files:**
- Create: `supabase/migrations/0044_match_bid_notices_industry_names.sql`
- Modify: `backend/app/core/config.py` (Settings 필드 1개)
- Modify: `backend/app/services/recommend.py` (`_search_with_embedding` 의 RPC 호출 블록, 헬퍼 2개 추가)
- Modify: `backend/jobs/evaluate_recommender.py` (`--retrieval` 기본값)
- Modify: `docs/recommender/evaluation.md`, `CLAUDE.md` (한 줄씩)

- [ ] **Step 1: 마이그레이션 파일**

`supabase/migrations/0044_match_bid_notices_industry_names.sql` — 0018 과 같은 본문에 파라미터·필터만 추가. returns table 컬럼 목록은 0018 과 **글자 그대로 동일**.

```sql
-- 후보 검색 업종 채널.
--
-- 평가 하네스 결과(docs/recommender/exp-2026-10-14-retrieval.md): dense 검색이 놓친 낙찰 공고의
-- 56%는 회사 등록업종이 공고 허용업종(bidprc_psbl_indstryty_nm)에 들어 있는 공고였다.
-- industry_names 가 주어지면 그 업종을 허용하는 공고 안에서만 유사도 검색한다. null 이면 종전과 동일.
-- 호출 측(recommend.py)이 dense 호출과 업종 호출을 병렬로 보내 번갈아 합친다.
--
-- 0018 과 같은 이유로 create or replace 가 아니라 drop 후 create (arity 가 달라지면 overload 모호 → PGRST203).
-- 활성 공고 CTE 는 ~1만 행 정확 탐색이라 필터가 늘어도 비용은 같거나 줄어든다(실측 230ms → 187ms).

begin;

drop function if exists match_bid_notices(vector, int, date, text, date);

create function match_bid_notices(
  query_embedding vector(1536),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null,
  max_clse_date date default null,
  industry_names text[] default null
)
returns table (
  bid_ntce_no text,
  bid_ntce_ord text,
  bid_ntce_nm text,
  bsns_div_nm text,
  bid_ntce_date date,
  bid_clse_date date,
  openg_date date,
  presmpt_prce bigint,
  ntce_instt_nm text,
  dmnd_instt_nm text,
  bidprc_psbl_indstryty_nm text,
  rgn_lmt_yn char(1),
  prtcpt_psbl_rgn_nm text,
  indstryty_lmt_yn char(1),
  bid_ntce_url text,
  similarity real
)
language sql
stable
as $$
  with active as materialized (
    select b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
           b.bid_ntce_date, b.bid_clse_date, b.openg_date,
           b.presmpt_prce, b.ntce_instt_nm, b.dmnd_instt_nm,
           b.bidprc_psbl_indstryty_nm, b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm,
           b.indstryty_lmt_yn, b.bid_ntce_url, b.embedding
    from bid_notices b
    where b.embedding is not null
      and b.bid_clse_date >= coalesce(min_clse_date, current_date)
      and (max_clse_date is null or b.bid_clse_date <= max_clse_date)
      and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
      and (industry_names is null
           or exists (select 1 from unnest(industry_names) n
                      where b.bidprc_psbl_indstryty_nm like '%' || n || '%'))
  )
  select a.bid_ntce_no, a.bid_ntce_ord, a.bid_ntce_nm, a.bsns_div_nm,
         a.bid_ntce_date, a.bid_clse_date, a.openg_date,
         a.presmpt_prce, a.ntce_instt_nm, a.dmnd_instt_nm,
         a.bidprc_psbl_indstryty_nm, a.rgn_lmt_yn, a.prtcpt_psbl_rgn_nm,
         a.indstryty_lmt_yn, a.bid_ntce_url,
         (1 - (a.embedding <=> query_embedding))::real as similarity
  from active a
  order by a.embedding <=> query_embedding
  limit match_count;
$$;

notify pgrst, 'reload schema';

commit;
```

- [ ] **Step 2: 설정**

`backend/app/core/config.py` Settings 에 `sentry_dsn` 아래 추가 (`from typing import Literal` 도):
```python
    # 추천 후보 검색 방식 — dense(벡터 1채널) / hybrid(dense + 업종 허용 공고 채널, 0044 필요).
    # 근거: docs/recommender/exp-2026-10-14-retrieval.md. 문제 시 dense 로 즉시 롤백.
    reco_retrieval: Literal["dense", "hybrid"] = "hybrid"
```

- [ ] **Step 3: recommend.py**

import 에 `from itertools import zip_longest`, `from app.core.config import get_settings` 추가. `_rpc_with_retry` 바로 아래에 헬퍼 2개:

```python
def _match_notices(client, params: dict, horizon: date) -> list[dict]:
    """match_bid_notices 1회. 0018 미적용 환경은 max_clse_date 없이 받아 파이썬에서 거른다."""
    try:
        res = _rpc_with_retry(client, "match_bid_notices", {**params, "max_clse_date": horizon.isoformat()})
        return res.data or []
    except APIError as e:
        if e.code != FUNCTION_NOT_FOUND:
            raise
        logger.warning("match_bid_notices max_clse_date 미지원 (0018 미적용) — 파이썬 필터로 degrade")
        res = _rpc_with_retry(client, "match_bid_notices", params)
        return [r for r in (res.data or []) if _within_horizon(r, horizon)]


def _interleave(first: list[dict], second: list[dict]) -> list[dict]:
    """두 채널을 번갈아 합친다(동률 RRF). 같은 (no, ord)는 첫 등장만.
    평가 하네스 jobs/evaluate_recommender.py::replay(hybrid) 와 같은 순서여야 한다."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for a, b in zip_longest(first, second):
        for r in (a, b):
            if r is None:
                continue
            k = (r.get("bid_ntce_no"), r.get("bid_ntce_ord"))
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
    return out
```

`_search_with_embedding` 안의 `params = {...}` 부터 0018 degrade 블록의 `raw = [...]` 까지를 다음으로 교체:

```python
    params = {
        "query_embedding": embedding_str,
        "match_count": candidate_pool * 2,
        "min_clse_date": today.isoformat(),
    }
    names = sorted(company_industry_names or ())
    if get_settings().reco_retrieval == "hybrid" and names:
        # 업종 채널: 회사 등록업종을 허용하는 공고 안에서 유사도 검색(0044) → dense 채널과 번갈아 합친다.
        # dense 가 놓친 낙찰 공고의 56% 가 이런 공고였다 (docs/recommender/exp-2026-10-14-retrieval.md).
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_dense = submit_timed(ex, "match_bid_notices", _match_notices, client, params, horizon)
            f_ind = submit_timed(ex, "match_industry", _match_notices, client, {**params, "industry_names": names}, horizon)
            dense_raw = f_dense.result()
            try:
                ind_raw = f_ind.result()
            except APIError as e:
                if e.code != FUNCTION_NOT_FOUND:
                    raise
                logger.warning("match_bid_notices industry_names 미지원 (0044 미적용) — dense 채널만 사용")
                ind_raw = []
        raw = _interleave(ind_raw, dense_raw)
    else:
        with timed("match_bid_notices"):
            raw = _match_notices(client, params, horizon)
```
바로 아래 주석 `# similarity 내림차순 정렬은 RPC가 보장 → 첫 등장 유지` 는 `# 채널별 similarity 내림차순은 RPC가 보장, 합친 뒤에는 번갈아 순서 → 첫 등장 유지` 로. 나머지(dedup, pool 컷, rank_v2)는 손대지 않는다. 기존 `with timed("match_bid_notices"):` 블록과 0018 degrade 블록은 헬퍼로 흡수되므로 삭제.

- [ ] **Step 4: 하네스 기본값**

`backend/jobs/evaluate_recommender.py`: `from app.core.config import get_settings` 추가, `--retrieval` 의 `default="dense"` → `default=get_settings().reco_retrieval`, `help="기본값은 운영 설정 RECO_RETRIEVAL"`.

- [ ] **Step 5: 문서 한 줄씩**

`docs/recommender/evaluation.md` "## 규칙" 마지막에: `- 후보 검색 방식은 --retrieval (기본값 = 운영 설정 RECO_RETRIEVAL). 운영 변경 전후 비교는 --retrieval dense / hybrid 로 명시한다.`
`CLAUDE.md` 추천 파이프라인 2번 줄을 `` 2. `_search_with_embedding` — pgvector RPC(`match_bid_notices`) 2채널(dense + 회사 업종 허용 공고, 0044·`RECO_RETRIEVAL`)을 번갈아 합쳐 후보 풀 `` 로.

- [ ] **Step 6: 검증**

```bash
cd backend && uv run python -c "from app.services.recommend import _interleave as f; a=[{'bid_ntce_no':'A','bid_ntce_ord':'0'},{'bid_ntce_no':'B','bid_ntce_ord':'0'}]; b=[{'bid_ntce_no':'B','bid_ntce_ord':'0'},{'bid_ntce_no':'C','bid_ntce_ord':'0'},{'bid_ntce_no':'D','bid_ntce_ord':'0'}]; print([r['bid_ntce_no'] for r in f(a,b)])"
```
Expected: `['A', 'B', 'C', 'D']`.
```bash
uv run python -c "import app.services.recommend; from app.core.config import get_settings; print(get_settings().reco_retrieval)"
```
Expected: `hybrid`. 0044 는 아직 DB 에 없으므로 실제 추천 호출은 하지 않는다.

- [ ] **Step 7: 커밋 (push 금지 — 0044 적용·검증 후 push)**
```bash
git add supabase/migrations/0044_match_bid_notices_industry_names.sql backend/app/core/config.py backend/app/services/recommend.py backend/jobs/evaluate_recommender.py docs/recommender/evaluation.md CLAUDE.md
git -c core.safecrlf=false commit -m "feat(recommender): 후보 검색 업종 채널(hybrid) — 0044 industry_names + 2채널 병렬 합치기 + RECO_RETRIEVAL"
```
(Co-Authored-By 줄 포함)

### Task 2: 0044 적용 후 운영 검증
- 승우님: Dashboard SQL Editor 에서 0044 실행.
- 로컬 백엔드로 회사 1곳 추천 호출 → "0044 미적용" 경고 없음, Server-Timing 에 `match_industry` 구간, 결과 정상.
- 채점표 `--as-of 2026-08-01 --retrieval hybrid` 결과가 `exp-0801-hybrid2` 와 동일.
- push → Railway 배포 → 운영 추천 1회 호출 확인.
- 배포 후 1~2일: 추천 API 57014(statement timeout) 비율과 Server-Timing `match_industry` 분포 확인(요청당 pgvector 쿼리 2배). 악화되면 `RECO_RETRIEVAL=dense` 로 즉시 롤백.

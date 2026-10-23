# 리뉴얼 05 — results: 결과 페이지 교체 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 먼저 `2026-10-19-renewal-00-master.md` §3.1·§3.4·§3.5·§3.6, 01 부품(`Sheet` `Gate` `Panel` `PageHead` `Btn`), 03 부품(`StarCompany` `ReviewButton`, `lib/saved.ts`)을 읽는다. 시안: `docs/design/prototypes/final/results-final.html`(원천 `docs/design/scripts/gen_results_final.py` + `gen_flow.py` + `gen_split.py`), 인쇄 `prototypes/final/report.html`(`gen_report.py`). 결정 기록 `docs/design/README.md` "결과 페이지 — 오늘 결정 반영 + 빠진 상태 넷" · "한 페이지 보고서" · "두 단 시안" · "결과 페이지 최종 시안".

**Goal:** `/recommendations` 를 시안대로 교체한다 — 머리(회사 이름·사업자번호 마스킹·☆·다른 회사) → 선 캔버스 머리 장면(백엔드 진행 이벤트에 묶임) → 걸러낸 경로 + 종류 탭·마감 요약 → 흰 판 두 단(회사 정보 sticky / 표 5건 + 게이트 + 흐림 7건) → 네 상태(0건·오류·로그인 뒤·검토 뒤) → 인쇄 뷰.

**Architecture:** 백엔드 `/recommendations/stream` 이 `results` 앞에 `funnel`(전체·업종 허용 건수)과 `stage`(후보 검색·자격 거르기·점수 완료 + 건수) 줄을 먼저 내보낸다 — `recommend()` 를 워커 스레드에서 돌리고 ContextVar 콜백이 큐에 넣은 이벤트를 제너레이터가 흘려 보낸다. 프론트는 `lib/stream.ts` 가 NDJSON 을 이벤트로 바꾸고, `ResultsView`(클라이언트 상태 기계) 가 장면·경로·표를 그린다. 머리 장면은 `gen_flow.py` ENGINE_JS 를 그대로 옮긴 `scene-engine.ts` 위에 **이벤트 구동 러너**를 얹는다: 전진선은 다음 관문 앞에서 이벤트를 기다리고, 이벤트가 먼저 오면 남은 구간을 짧게 마무리한다(시안의 고정 3.6초 타임라인 폐기, 가짜 진행률 없음). 회사 정보(등록업종 목록·공급물품·수주 건수)는 공개 데이터라 서버 route handler 가 service_role 로 준다. 인쇄 뷰는 비스트림 `POST /recommendations`(캐시) 로 서버 렌더. 옛 보드 페이지는 지우고 `components/board/*` 는 09 에서 삭제.

**Tech Stack:** FastAPI(ContextVar + queue.Queue + 워커 스레드) · Supabase RPC(0056 `funnel_counts`) · Next.js 16.2 App Router · React 19 · Canvas 2D · Tailwind v4 토큰(01) · Playwright(backend venv).

---

## 결정 (이 계획이 시안과 다르게 가는 곳)

| 시안 | 구현 | 이유 |
|---|---|---|
| 깔때기 셋째 칸 "참가 자격 통과 공고 372" = 업종 허용 공고 전수 자격 판정 | 후보 풀(최대 200) 중 자격 통과 수, 부제 ` · 후보 N건 중 M% 통과` | 매 요청 835건 자격 판정은 못 한다. 숫자의 기준을 글로 밝혀 거짓이 되지 않게 |
| 고정 타임라인 3.6초 / 재방문 1.1초 | 이벤트 구동. 각 관문은 해당 `stage` 가 와야 통과, 전부 와 있으면 구간당 최소 260ms 만 쓰고 끝 | README "실제 진행에 묶는다", 마스터 §3.4 |
| 머리 장면의 공고명(`.ttl`, 탈락 공고 9건) | 넣지 않음. 탈락 이유 글자(등록업종 미허용 / 면허·지역 제한 미충족 / 회사와의 유사도 낮음)는 넣음 | 탈락 공고명은 백엔드가 모른다. 장식이라 09 이후 |
| 이메일 뒤 `okline`("이메일 등록 완료 · 전체 결과 공개") | 없음. 로그인이면 게이트·흐림만 없다 | 02 결정(이메일 구독 폐기) |
| 검토 뒤 `.rvm` "검토함" 라벨 + `.rvn` "브라우저에 저장" 안내 | 행 왼쪽 주황 괘선(`SheetRow reviewed`) + 버튼 "검토함" 만 | 계정 저장(03)이라 안내가 거짓. 라벨은 괘선과 중복 |
| 키워드 모드 | 장면·깔때기·왼쪽 단 없음. 머리에 검색어 + "다른 검색" → 바로 표(근거 칩 없음, 자격 줄 없음) | 시안이 회사 모드만 그렸고 키워드는 0.5초 |
| 사업자번호 `124-81*****` | `maskBizrno` → `124-XX-X731` | README:196 결정 |
| 종류 탭(사전규격·발주계획) 클릭 | 숫자만 표시(시안과 같음). 클릭 전환은 06/07 뒤 | 시안에 전환이 없다 |
| 0건 문구 | 후보 풀에서 자격 통과 0 → "참가 자격이 있는 공고가 없습니다", 통과했는데 결과 0 → "검토할 공고가 없습니다" | README:48 지적 |
| 오류 판정 1.2초 | 요청 시작 8초 안에 `results` 가 없거나 fetch 실패 → 오류. "다시 시도" | README "실제는 8초" |

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `backend/app/core/progress.py` | ContextVar 기반 진행 이벤트 발행(`emit`) + 콜백 set/reset |
| `backend/app/services/recommend.py` | `_recommend_by_company` 에 `funnel` 발행(0056 RPC) + 후보 검색 끝 `stage` 발행, 응답에 `funnel` |
| `backend/app/recommender/pipeline.py` | 자격 거르기 끝·점수 끝 `stage` 발행 |
| `backend/app/api/recommendations.py` | `/stream` 이 워커 스레드 + 큐로 `funnel`·`stage` 줄을 `results` 앞에 흘림, 404 는 `error` 줄 |
| `supabase/migrations/0056_funnel_counts.sql` | `funnel_counts(p_names text[], p_days int)` — 마감 90일 내 전체 건수·회사 업종 허용 건수 |
| `frontend/src/types/recommendations.ts` | `StreamEvent`·`FunnelCounts` 타입 추가, 응답에 `funnel?` |
| `frontend/src/lib/stream.ts` | NDJSON 스트림 → 이벤트 콜백(브라우저 전용) |
| `frontend/src/lib/why.ts` (+ `.test.ts`) | 근거 문장·참가 자격 줄 만들기(순수 함수, 시안 `why_lines`·`qual_lines`) |
| `frontend/src/components/SearchBox.tsx` | 주황 상자 검색창(입구·다른 회사 공용). `search_submit` 계측 |
| `frontend/src/components/results/scene-engine.ts` | `gen_flow.py` ENGINE_JS 포팅(선·벽·라벨 칠하기) |
| `frontend/src/components/results/Scene.tsx` | 캔버스 + 라벨 넷 + 탈락 이유, 이벤트 구동 러너, 건너뛰기, reduced-motion |
| `frontend/src/components/results/FunnelLine.tsx` | 걸러낸 경로(숫자 + 단계 라벨) + 종류 탭 + 마감 요약 |
| `frontend/src/components/results/CompanySide.tsx` | 왼쪽 단(등록업종 목록·공급물품·지역·면허·규모·사업자 상태·갱신일), 720 이하 `<details>` |
| `frontend/src/components/results/ResultRows.tsx` | 표: `SheetHead/SheetRow/SheetExpand` + `ReviewButton` + `Gate` + `SheetFade`, 0건 블록 |
| `frontend/src/components/results/ResultsView.tsx` | 상태 기계(running/done/zero/error/search), 스트림 호출, 머리(이름·☆·다른 회사), 조립 |
| `frontend/src/app/(renewal)/recommendations/page.tsx` | URL 계약 유지(`company`·`q`·`keywords`·`algorithm`·`from`, 공고번호 리다이렉트), 세션·저장 키, 빈 질의 입구 |
| `frontend/src/app/(renewal)/recommendations/report/page.tsx` (+ `PrintButton.tsx`) | 인쇄 뷰(A4 한 장, 로그인 사용자) |
| `frontend/src/app/api/companies/[bizrno]/profile/route.ts` | 왼쪽 단 데이터(JSON) — service_role 공개 조회 |
| `frontend/src/app/globals.css` | `[data-lab].on`·`[data-rsn].on`, `@page`·`.report` 인쇄 규칙 |
| `frontend/src/app/recommendations/` | 삭제(옛 보드 페이지·loading) |
| `frontend/scripts/check_results.py` | Playwright 검증 |

---

### Task 1: 0056 `funnel_counts` RPC

**Files:**
- Create: `supabase/migrations/0056_funnel_counts.sql`

- [x] **Step 1: 마이그레이션**

```sql
-- supabase/migrations/0056_funnel_counts.sql
-- 결과 페이지 "걸러낸 경로" 앞 두 칸 — 지금 입찰 가능한 공고 수(마감 p_days 일 이내)와 그중 회사 등록업종을 허용하는 공고 수.
-- 시안(gen_data.py::funnel)은 파이썬에서 전수를 돌렸다. 운영은 한 번의 집계로 — 두 수 모두 같은 범위(bid_clse_date 오늘~오늘+p_days).
-- 업종 허용 판정은 0044 의 업종 채널과 같은 기준(bidprc_psbl_indstryty_nm 에 등록업종 이름 포함). p_names 가 비면 industry = 0.
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 운영에 먼저 적용해도 무해(읽기 전용 함수).
create or replace function public.funnel_counts(p_names text[], p_days int default 90)
returns table (total bigint, industry bigint)
language sql
stable
as $$
  select count(*) as total,
         count(*) filter (
           where coalesce(array_length(p_names, 1), 0) > 0
             and exists (select 1 from unnest(p_names) nm where n.bidprc_psbl_indstryty_nm like '%' || nm || '%')
         ) as industry
    from public.bid_notices n
   where n.bid_clse_date between current_date and current_date + p_days;
$$;

grant execute on function public.funnel_counts(text[], int) to service_role;
revoke execute on function public.funnel_counts(text[], int) from anon, authenticated;
```

- [x] **Step 2: 적용·측정** — Dashboard 또는 `backend/.env` 의 `DATABASE_URL` 로 실행(0053·0054 와 같은 방법: 스크래치패드에 psycopg 스크립트). 확인:

```sql
explain analyze select * from public.funnel_counts(array['환경전문공사업','전기공사업','엔지니어링사업'], 90);
-- 실행 시간을 기록한다. 1초를 넘기면 bid_notices(bid_clse_date) 인덱스 유무를 본다(0001 에 있다).
select * from public.funnel_counts(array[]::text[], 90);  -- industry = 0
```

- [x] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add supabase/migrations/0056_funnel_counts.sql && git commit -m "feat(db): 0056 funnel_counts — 입찰 가능·등록업종 허용 공고 수 집계"
```

---

### Task 2: 백엔드 진행 이벤트 — `progress.py` + 발행 지점 + 스트림

**Files:**
- Create: `backend/app/core/progress.py`
- Modify: `backend/app/services/recommend.py`(`_recommend_by_company` ThreadPool 블록, `_search_with_embedding` 끝), `backend/app/recommender/pipeline.py`(`rank_v2`), `backend/app/api/recommendations.py`(`post_recommendations_stream`)

- [x] **Step 1: `progress.py`**

```python
# backend/app/core/progress.py
"""추천 파이프라인 진행 이벤트 — /recommendations/stream 이 머리 장면을 실제 진행에 묶는 데 쓴다.

emit(name, **fields) 는 현재 컨텍스트에 콜백이 있을 때만 호출한다(없으면 no-op — 비스트림 경로·잡은 비용 0).
ContextVar 라 submit_timed(copy_context) 로 넘어간 워커에서도 같은 콜백이 보인다.
"""
from contextvars import ContextVar
from typing import Any, Callable

_cb: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar("progress_cb", default=None)


def emit(type_: str, **fields: Any) -> None:
    cb = _cb.get()
    if cb is not None:
        cb({"type": type_, **fields})


def set_callback(cb: Callable[[dict[str, Any]], None] | None):
    """토큰을 돌려준다 — 끝나면 reset(token)."""
    return _cb.set(cb)


def reset(token) -> None:
    _cb.reset(token)


if __name__ == "__main__":
    got: list[dict] = []
    emit("stage", stage="search", candidates=3)  # 콜백 없음 → 아무 일 없음
    assert got == []
    tok = set_callback(got.append)
    emit("funnel", total=10, industry=2)
    emit("stage", stage="qualify", passed=1)
    reset(tok)
    emit("stage", stage="rank", results=1)
    assert got == [{"type": "funnel", "total": 10, "industry": 2}, {"type": "stage", "stage": "qualify", "passed": 1}], got
    print("ok progress: no-op without callback · emits with callback · reset stops")
```

Run `cd C:/Dev/personal/jodalfit/backend && uv run --no-sync python -m app.core.progress` → `ok progress: …`.

- [x] **Step 2: 발행 지점 셋 + funnel** — `backend/app/services/recommend.py`:

(a) 상단 import 에 `from app.core.progress import emit` 추가.

(b) `_search_with_embedding` 의 dedupe for 루프가 끝난 바로 뒤(`recommend.py:561` 부근, `if len(deduped) >= candidate_pool: break` 다음 줄)에:

```python
    emit("stage", stage="search", candidates=len(deduped))
```

(c) `_recommend_by_company` 의 `with ThreadPoolExecutor(max_workers=4) as ex:` 블록 — `max_workers=5` 로 올리고, `company_terms, company_industry_names, company_product_codes = f_terms.result()` 바로 뒤에 funnel 집계를 같은 풀에 던지고, 풀 블록 끝에서 받는다:

```python
        company_terms, company_industry_names, company_product_codes = f_terms.result()
        f_funnel = submit_timed(ex, "funnel", _fetch_funnel, client, sorted(company_industry_names))
        company_institutions, company_amt_median = f_hist.result()
        # … ranked = _search_with_embedding(...) 그대로 …
        pre_specs = f_pre.result()
        order_plans = f_ord.result()
        funnel = f_funnel.result()
```

반환 dict 에 `"funnel": funnel,` 추가(비스트림 응답·캐시에도 실린다 — 인쇄 뷰가 쓴다). 모듈에 함수 추가:

```python
def _fetch_funnel(client, names: list[str]) -> dict[str, int] | None:
    """걸러낸 경로 앞 두 칸(0056). 미적용·실패면 None — 머리 장면은 두 칸 없이 간다."""
    try:
        res = client.rpc("funnel_counts", {"p_names": names, "p_days": MAX_CLSE_HORIZON_DAYS}).execute()
        row = (res.data or [{}])[0]
        out = {"total": int(row.get("total") or 0), "industry": int(row.get("industry") or 0)}
        emit("funnel", **out)
        return out
    except Exception as e:  # 0056 미적용 등
        logger.warning("funnel_counts 실패: %s", e)
        return None
```

`MAX_CLSE_HORIZON_DAYS` 는 이미 모듈 상수(90). `logger` 는 `_search_with_embedding` 이 이미 쓰고 있다.

(d) `backend/app/recommender/pipeline.py` `rank_v2`: 상단 `from app.core.progress import emit`. `passed` 루프가 끝난 직후(peer 주석 블록 앞)에

```python
    emit("stage", stage="qualify", candidates=len(candidates), passed=len(passed))
```

마지막 `return diversified[:limit]` 을

```python
    out = diversified[:limit]
    emit("stage", stage="rank", results=len(out))
    return out
```

로.

- [x] **Step 3: 스트림 경로** — `backend/app/api/recommendations.py` 상단에 `import queue, threading` 과 `from app.core import progress` 를 추가하고, `post_recommendations_stream` 본문을 바꾼다(`t0 = time.time()` 부터 `return StreamingResponse(...)` 까지). 매개변수 `background: BackgroundTasks` 는 남겨 두되 안 쓴다(시그니처 유지):

```python
    t0 = time.time()
    source = classify_source(request)

    # recommend() 를 워커에서 돌리고 진행 이벤트를 큐로 받는다 — results 줄 앞에 funnel·stage 줄을 흘린다.
    q: "queue.Queue[dict | None]" = queue.Queue()
    box: dict = {}

    def work():
        tok = progress.set_callback(q.put)
        try:
            box["result"] = recommend(
                req.query, limit=req.limit, candidate_pool=req.candidate_pool,
                mode=req.mode, keywords=req.keywords, algorithm=req.algorithm,
            )
        except Exception as e:  # 제너레이터 쪽에서 다시 던진다
            box["error"] = e
        finally:
            progress.reset(tok)
            q.put(None)

    threading.Thread(target=work, daemon=True).start()

    def _line(obj: dict) -> bytes:
        return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")

    def stream():
        while True:
            item = q.get()
            if item is None:
                break
            yield _line(item)
        if "error" in box:
            raise box["error"]
        result = box["result"]

        has_any_results = bool(result.get("results") or result.get("keyword_results"))
        if result.get("error") and not has_any_results and not result.get("fallback"):
            yield _line({"type": "error", "message": result["error"], "status": 404})
            return

        company = result.get("company") or {}
        # 검색 로그·노출 로그 — 스트림 안에서는 BackgroundTasks 를 못 쓰므로 스레드로
        threading.Thread(target=log_search, kwargs=dict(
            query=req.query, mode=req.mode, matched_bizrno=company.get("bizrno"), matched_corp_nm=company.get("corp_nm"),
            result_count=len(result.get("results") or []), kw_result_count=len(result.get("keyword_results") or []),
            has_error=bool(result.get("error")), error_msg=result.get("error"), with_explanation=True,
            ip=_client_ip(request), user_agent=request.headers.get("user-agent"), referer=request.headers.get("referer"),
            latency_ms=int((time.time() - t0) * 1000), source=source,
        ), daemon=True).start()
        if result.get("results"):
            threading.Thread(target=log_impressions, args=(result["results"],), kwargs=dict(
                session_id=req.session_id, target_bizrno=company.get("bizrno"), source=source, algorithm_version=req.algorithm,
            ), daemon=True).start()

        yield _line({"type": "results", "data": result})

        primary_top = (result.get("results") or [])[: req.explain_top]
        keyword_top = (result.get("keyword_results") or [])[: req.explain_top]
        use_company_ctx = bool(result.get("company"))
        use_summary = req.algorithm == "v2" and use_company_ctx and bool(primary_top)

        if req.explain_top <= 0 or (not primary_top and not keyword_top):
            yield _line({"type": "done"})
            return
        if use_summary:
            try:
                text = explain_summary(company, primary_top)
                yield _line({"type": "summary", "text": text})
            except Exception as e:
                yield _line({"type": "summary", "text": "", "error": type(e).__name__})
            yield _line({"type": "done"})
            return
        with ThreadPoolExecutor(max_workers=max(1, len(primary_top) + len(keyword_top))) as ex:
            futures = {}
            for bid in primary_top:
                fut = ex.submit(explain_recommendation, company, bid) if use_company_ctx else ex.submit(explain_keyword_match, req.query, bid)
                futures[fut] = ("primary", bid)
            for bid in keyword_top:
                futures[ex.submit(explain_keyword_match, req.query, bid)] = ("keyword", bid)
            for fut in as_completed(futures):
                scope, bid = futures[fut]
                try:
                    text = fut.result(timeout=30)
                except Exception as e:
                    text = f"(설명 생성 실패: {type(e).__name__})"
                yield _line({"type": "explanation", "scope": scope, "bid_ntce_no": bid["bid_ntce_no"], "bid_ntce_ord": bid["bid_ntce_ord"], "text": text})
        yield _line({"type": "done"})

    return StreamingResponse(stream(), media_type="application/x-ndjson")
```

404 를 HTTP 404 대신 `error` 줄로 바꾼 이유: funnel 줄이 먼저 나간 뒤라 상태 코드를 바꿀 수 없다. 비스트림 `POST /recommendations` 는 손대지 않는다. docstring 의 줄 형식 목록에 `{"type":"funnel","total":N,"industry":N}` · `{"type":"stage","stage":"search|qualify|rank",…}` · `{"type":"error","message":…,"status":404}` 를 추가한다.

- [x] **Step 4: 자체 점검** — 백엔드를 띄우고(`cd backend && uv run uvicorn app.main:app --port 8000`, 이미 떠 있으면 재시작) 스트림 첫 줄들을 본다:

```bash
curl -s -N -X POST http://localhost:8000/recommendations/stream -H "Content-Type: application/json" \
  -d '{"query":"1248177731","mode":"company","algorithm":"v2","limit":12,"candidate_pool":200,"explain_top":0}' | head -c 1500
```

기대: `{"type":"funnel",…}` / `{"type":"stage","stage":"search",…}` / `{"type":"stage","stage":"qualify",…}` / `{"type":"stage","stage":"rank","results":12}` 가 `{"type":"results",…` 앞에(funnel 과 search 의 순서는 바뀔 수 있다 — 프론트가 순서에 의존하지 않는다). 키워드 모드(`"mode":"keywords","query":"하수처리"`)는 `stage search` → `results`(qualify·rank 없음). 회사 못 찾는 질의(`"query":"존재하지않는회사명zzz"`)는 `results` 에 `"fallback":"keywords"`. `uv run --no-sync python -m app.core.progress` 통과.

- [x] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add backend/app/core/progress.py backend/app/services/recommend.py backend/app/recommender/pipeline.py backend/app/api/recommendations.py && git commit -m "feat(api): /recommendations/stream 에 funnel·stage 진행 이벤트 — recommend 를 워커에서 돌리고 ContextVar 콜백으로 흘림, 404 는 error 줄"
```

---

### Task 3: 프론트 타입 · `lib/stream.ts` · `lib/why.ts`(TDD)

**Files:**
- Modify: `frontend/src/types/recommendations.ts`
- Create: `frontend/src/lib/stream.ts`, `frontend/src/lib/why.ts`, `frontend/src/lib/why.test.ts`

- [x] **Step 1: 타입** — `types/recommendations.ts` 끝에 추가. `RecommendationResponse` 에 `funnel?: FunnelCounts | null;` 한 줄도 넣는다.

```ts
export type FunnelCounts = { total: number; industry: number };

export type StreamEvent =
  | { type: "funnel"; total: number; industry: number }
  | { type: "stage"; stage: "search"; candidates: number }
  | { type: "stage"; stage: "qualify"; candidates: number; passed: number }
  | { type: "stage"; stage: "rank"; results: number }
  | { type: "results"; data: RecommendationResponse }
  | { type: "summary"; text: string; error?: string }
  | { type: "explanation"; scope: "primary" | "keyword"; bid_ntce_no: string; bid_ntce_ord: string; text: string }
  | { type: "error"; message: string; status?: number }
  | { type: "done" };
```

- [x] **Step 2: `lib/stream.ts`**

```ts
// frontend/src/lib/stream.ts
// POST /recommendations/stream (NDJSON) 을 이벤트로. 브라우저에서 백엔드로 직접(옛 BoardView 와 같은 경로).
import type { StreamEvent } from "@/types/recommendations";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type StreamBody = {
  query: string; mode: "company" | "keywords"; keywords?: string | null; algorithm: "v1" | "v2";
  session_id?: string | null; limit: number; candidate_pool: number; explain_top: number; with_explanation: boolean;
};

/** 이벤트마다 onEvent. 네트워크/HTTP 오류는 throw — 호출자가 오류 상태로 바꾼다. */
export async function streamRecommendations(body: StreamBody, onEvent: (e: StreamEvent) => void, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${API_BASE}/recommendations/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  });
  if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try { onEvent(JSON.parse(line) as StreamEvent); } catch { /* 깨진 줄은 버린다 */ }
    }
  }
  if (buf.trim()) { try { onEvent(JSON.parse(buf) as StreamEvent); } catch { /* ignore */ } }
}
```

- [x] **Step 3: `why.test.ts` (실패부터)**

```ts
// frontend/src/lib/why.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { whyLines, qualLines } from "./why.ts";

test("whyLines: 시안 gen_flow.why_lines 문장, vector 는 마지막", () => {
  const out = whyLines(
    [
      { key: "vector", label: "유사도 73%", points: 73 },
      { key: "institution", label: "재출현 기관", points: 12, instt: "경기도 평택시 상하수도사업소" },
      { key: "region", label: "지역 매칭", points: 9, rgn: "경상남도" },
      { key: "industry_tokens", label: "업종·물품 일치", points: 6, matched: ["공공하수도", "관리대행", "x", "y"] },
      { key: "budget", label: "예산대 매칭", points: 2, ratio: 1.08 },
      { key: "budget_mismatch", label: "예산대 괴리", points: -2, ratio: 12.5 },
      { key: "instt_closed", label: "고정 거래처 경향", points: -3, repeat_ratio: 0.62 },
    ],
    "경기도 평택시 상하수도사업소",
  );
  assert.deepEqual(out, [
    "경기도 평택시 상하수도사업소 — 과거 거래 이력 있음",
    "공고의 지역 제한이 본사 소재지 경상남도와 일치",
    "등록업종 표현이 허용업종과 중복 — 공공하수도, 관리대행, x",
    "추정가가 회사 평균 수주가의 1.08배 — 유사한 규모",
    "추정가가 회사 평균 수주가의 12.5배 — 규모 차이 큼",
    "해당 기관 최근 낙찰의 62%를 같은 회사가 수주",
    "공고 내용과 회사 업종 설명 유사도 73%",
  ]);
});

test("qualLines: reasons 를 세 상태로, 규모 줄은 항상 끝에", () => {
  const out = qualLines({ passed: true, unverified: false, reasons: ["면허 제한 없음", "지역 자격 충족"], failures: [] });
  assert.deepEqual(out, [
    { state: "none", text: "면허 — 제한 없음" },
    { state: "ok", text: "지역 — 자격 충족" },
    { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" },
  ]);
  assert.deepEqual(qualLines(undefined), [{ state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" }]);
  assert.equal(qualLines({ passed: false, unverified: false, reasons: ["면허 미충족(a, b)"], failures: ["면허 미충족(a, b)"] })[0].state, "warn");
});
```

Run `cd C:/Dev/personal/jodalfit/frontend && node --experimental-strip-types --test src/lib/why.test.ts` → 모듈 없음으로 실패.

- [x] **Step 4: `lib/why.ts`**

```ts
// frontend/src/lib/why.ts
// 추천 근거 문장과 참가 자격 줄 — 시안 gen_flow.py::why_lines / qual_lines 와 같은 말. 순수 함수, node --test.
import type { QualLine } from "@/components/Sheet";
import type { ScoreSignal } from "@/types/recommendations";

export type Qualification = { passed: boolean; unverified: boolean; reasons: string[]; failures: string[] };

export function whyLines(breakdown: ScoreSignal[] | undefined, org: string): string[] {
  const out: string[] = [];
  let vector: string | null = null;
  for (const b of breakdown ?? []) {
    switch (b.key) {
      case "institution": out.push(`${org} — 과거 거래 이력 있음`); break;
      case "region": out.push(`공고의 지역 제한이 본사 소재지 ${String(b.rgn ?? "")}와 일치`); break;
      case "industry_tokens": out.push(`등록업종 표현이 허용업종과 중복 — ${((b.matched as string[] | undefined) ?? []).slice(0, 3).join(", ")}`); break;
      case "budget": out.push(`추정가가 회사 평균 수주가의 ${String(b.ratio)}배 — 유사한 규모`); break;
      case "budget_mismatch": out.push(`추정가가 회사 평균 수주가의 ${String(b.ratio)}배 — 규모 차이 큼`); break;
      case "instt_closed": out.push(`해당 기관 최근 낙찰의 ${Math.round(Number(b.repeat_ratio ?? 0) * 100)}%를 같은 회사가 수주`); break;
      case "vector": vector = `공고 내용과 회사 업종 설명 ${b.label}`; break;
      default: break; // peer_institution·deadline_urgent·qual_unverified 는 칩으로만(시안과 같음)
    }
  }
  if (vector) out.push(vector);
  return out;
}

const SIZE_LINE: QualLine = { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" };

export function qualLines(q: Qualification | undefined): QualLine[] {
  const fails = new Set(q?.failures ?? []);
  const lines: QualLine[] = (q?.reasons ?? []).map((t) => ({
    state: fails.has(t) ? "warn" : t.includes("제한 없음") ? "none" : "ok",
    text: t.replace(/^면허 /, "면허 — ").replace(/^지역 /, "지역 — "),
  }));
  return [...lines, SIZE_LINE];
}
```

`QualLine` 은 `components/Sheet.tsx:83` 의 `{ state: "ok" | "none" | "warn" | "todo"; text: string }`. `import type` 은 `node --experimental-strip-types` 가 지우므로 `@/` 경로여도 node 에서 문제없다(`ScoreSignal` 도 type import).

- [x] **Step 5: 통과·커밋** — `node --experimental-strip-types --test src/lib/why.test.ts` → pass 2. `npx tsc --noEmit -p tsconfig.json; echo $?` → 0.

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/types/recommendations.ts frontend/src/lib/stream.ts frontend/src/lib/why.ts frontend/src/lib/why.test.ts && git commit -m "feat(renewal): 스트림 이벤트 타입·NDJSON 리더, 근거 문장·자격 줄 순수 함수 + 테스트"
```

---

### Task 4: `SearchBox` + 회사 프로필 route handler

**Files:**
- Create: `frontend/src/components/SearchBox.tsx`, `frontend/src/app/api/companies/[bizrno]/profile/route.ts`

- [x] **Step 1: `SearchBox`** (입구 04 와 "다른 회사"가 같이 쓴다. 시안 `gen_results_final.py:50-56` `.box` CSS)

```tsx
// frontend/src/components/SearchBox.tsx
// 주황 테두리 검색창 하나 — 회사명·사업자번호·업종/품목. 제출은 /recommendations 로 이동(회사명/사업자번호면 company, 그 외 keywords).
// 사업자번호(숫자 10자리, 하이픈 허용)·회사 접미(주식회사·(주)·㈜·유한회사·(유))가 보이면 회사 모드, 아니면 키워드 모드.
"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/utils";

const CO_HINT = /(주식회사|\(주\)|㈜|유한회사|\(유\)|합자회사|법인)/;

export function modeOf(q: string): "company" | "keywords" {
  const digits = q.replace(/\D/g, "");
  if (/^[\d-]+$/.test(q.trim()) && digits.length === 10) return "company";
  return CO_HINT.test(q) ? "company" : "keywords";
}

export function SearchBox({ defaultValue = "", autoFocus = false, className, onSubmitted }: { defaultValue?: string; autoFocus?: boolean; className?: string; onSubmitted?: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState(defaultValue);
  function submit(e: FormEvent) {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    const mode = modeOf(v);
    track("search_submit", { mode, length: v.length });
    router.push(mode === "company" ? `/recommendations?company=${encodeURIComponent(v)}` : `/recommendations?q=${encodeURIComponent(v)}`);
    onSubmitted?.();
  }
  return (
    <form onSubmit={submit} role="search" data-searchbox
      className={cn("flex max-w-[720px] items-stretch rounded-[6px] border-2 border-orange bg-panel transition-shadow duration-150 focus-within:shadow-[0_0_0_4px_rgba(249,115,22,.18)]", className)}>
      <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus={autoFocus} autoComplete="off" spellCheck={false}
        placeholder="회사명 · 사업자등록번호 · 업종 또는 품목" aria-label="회사명, 사업자등록번호, 업종 또는 품목"
        className="min-w-0 flex-1 bg-transparent px-[18px] py-3.5 text-[20px] font-medium tracking-[-0.02em] text-ink outline-none placeholder:font-[450] placeholder:text-ink-mute max-sm:px-3.5 max-sm:py-3 max-sm:text-[17px]" />
      <button type="submit" className="cursor-pointer border-l border-rule bg-panel px-5 text-[15px] font-[650] text-ink max-sm:px-3.5">
        <span className="border-b-2 border-orange pb-px">찾기</span>
      </button>
    </form>
  );
}
```

`modeOf` 는 `lib/` 로 빼지 않는다(여기서만 쓴다).

- [x] **Step 2: 프로필 route handler** — 왼쪽 단이 쓰는 공개 데이터. `lib/company.ts::fetchCompanyProfile(bizrno)`(`industries: string[]` 대표 먼저, `industryLinks`, `products: string[]`)와 `fetchCompanyByBizrno(bizrnoNorm)`(`CompanyDetail`: `contract_count`, `biz_status_cd`, `is_restricted`, 상태 확인 시각 컬럼)를 쓴다 — 실제 필드명은 `lib/company.ts:5-21`·`172-238` 에서 확인해 맞춘다.

```ts
// frontend/src/app/api/companies/[bizrno]/profile/route.ts
// 결과 페이지 왼쪽 단 — 등록업종 목록·공급물품·수주 건수·사업자 상태. 공개 데이터, service_role 로 읽는다.
import { NextResponse } from "next/server";
import { fetchCompanyByBizrno, fetchCompanyProfile } from "@/lib/company";

export type CompanySideData = {
  industries: string[];      // 대표가 맨 앞
  repCount: number;          // 대표 업종 수(앞에서부터)
  products: string[];
  contractCount: number;
  status: string;            // "계속사업자" | "휴업" | "폐업" | "확인 전"
  restricted: boolean;
  checkedAt: string | null;  // YYYY-MM-DD
};

export async function GET(_: Request, { params }: { params: Promise<{ bizrno: string }> }) {
  const { bizrno } = await params;
  const norm = bizrno.replace(/\D/g, "");
  if (!/^\d{10}$/.test(norm)) return NextResponse.json({ error: "invalid bizrno" }, { status: 400 });
  const [co, prof] = await Promise.all([fetchCompanyByBizrno(norm), fetchCompanyProfile(norm)]);
  if (!co) return NextResponse.json({ error: "not found" }, { status: 404 });
  const status = co.biz_status_cd === "03" ? "폐업" : co.biz_status_cd === "02" ? "휴업" : co.biz_status_cd === "01" ? "계속사업자" : "확인 전";
  const body: CompanySideData = {
    industries: prof.industries,
    repCount: Math.max(1, prof.industryLinks.filter((x) => x.rep).length),
    products: prof.products,
    contractCount: co.contract_count ?? 0,
    status,
    restricted: !!co.is_restricted,
    checkedAt: (co.biz_status_checked_at ?? null)?.slice(0, 10) ?? null,
  };
  return NextResponse.json(body, { headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } });
}
```

`industryLinks` 의 대표 표시 필드명(`rep`?)은 `lib/company.ts` 를 읽고 맞춘다; 없으면 `repCount: 1`(대표는 보통 하나, `fetchCompanyProfile` 이 대표를 맨 앞에 둔다) 로 두고 보고. `biz_status_checked_at` 이 `CompanyDetail` 에 없으면 `fetchCompanyByBizrno` 의 select 에 그 컬럼(0028 `biz_status_checked_at`)을 한 단어 추가한다.

- [x] **Step 3: 확인·커밋** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0. 개발 서버에서 `curl -s http://localhost:3000/api/companies/1248177731/profile` → JSON(한종산업개발, industries 15개 안팎).

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/SearchBox.tsx "frontend/src/app/api/companies/[bizrno]/profile/route.ts" frontend/src/lib/company.ts && git commit -m "feat(renewal): SearchBox(주황 상자 검색창, 회사/키워드 판별) + 회사 프로필 route handler"
```

---

### Task 5: 머리 장면 — `scene-engine.ts` 포팅 + `Scene.tsx` 이벤트 구동 러너

**Files:**
- Create: `frontend/src/components/results/scene-engine.ts`, `frontend/src/components/results/Scene.tsx`
- Modify: `frontend/src/app/globals.css`(`[data-lab].on`·`[data-rsn].on`)

- [x] **Step 1: 엔진 포팅** — `docs/design/scripts/gen_flow.py` 의 `ENGINE_JS`(139~285행: `rng`·좌표·`Path2D` 코호트·`fade`·벽·오프스크린 blit·`labels`·`paint`)를 **동작 그대로** TypeScript 모듈로 옮긴다. 바꾸는 것은 넷뿐: ① 전역 `document.querySelector` 대신 생성자가 캔버스·라벨·이유 엘리먼트를 받는다 ② `cfg` JSON 대신 상수(`W,H,CY,XS,FAN_X,FAN_SP,HH,CONV,PRESS` — 값은 `gen_flow.py:33-40` 그대로)와 `CNT` 를 인자로 ③ 공고명 `.ttl`(`T` 배열) 자리에 탈락 이유 엘리먼트(`data-x` 를 지나면 `.on`)를 넣는다 ④ `paint` 가 `document.body.classList.toggle('done')` 하던 것은 **하지 않는다**(React 가 `done` 을 든다). 모듈 API:

```ts
// frontend/src/components/results/scene-engine.ts
// gen_flow.py::ENGINE_JS 포팅 — 선 하나 = 공고 하나, 벽 셋, 통로만 뚫림. 색·펜·이징·오프스크린 blit 전부 원본 값.
export const SCENE = { W: 1120, H: 392, CY: 196, XS: [0, 288, 576, 864], FAN_X: 936, FAN_SP: 150, HH: [180, 160, 150, 100], CONV: 44, PRESS: 44 } as const;
export type Engine = {
  setup(): void;                                 // 캔버스 크기·dpr(sx·sy)·오프스크린 렌더
  paint(x: number, settled: boolean): void;     // x 까지 blit + 라벨·숫자·이유 켜기
  setCounts(cnt: number[]): void;                // 숫자가 바뀌면 코호트 다시 만든다(모르는 칸은 -1 → 0 으로 계산, 라벨엔 "…")
  counts(): number[];
};
export function createEngine(canvas: HTMLCanvasElement, labels: HTMLElement[], reasons: HTMLElement[], counts: number[]): Engine
```

`labels[i]` 는 `data-x`(=XS[i]) 와 안쪽 `.cnt`(data-to) 를 가진 엘리먼트 — 원본 `labels(x)` 가 그대로 돌아가게 같은 구조를 Scene.tsx 가 만든다. 숫자 카운트업(벽 지나 150px 동안 ease-out cubic)·`toLocaleString('ko-KR')` 유지, `data-to` 가 `-1` 이면 `…`.

- [x] **Step 2: `Scene.tsx`** — 러너. 규칙(README "실제 진행에 묶는다"): 관문 i 는 `counts` 의 i번째 값을 알아야 통과, 모르면 관문 30px 앞에서 기다린다, 전부 알면 남은 구간을 구간당 260ms 로 마무리, 클릭·Esc = 건너뛰기, reduced-motion 이면 결과 오는 순간 즉시 접힘.

```tsx
// frontend/src/components/results/Scene.tsx
// 머리 장면 — 백엔드 funnel/stage 이벤트에 묶인 전진선. 관문 i 는 counts[i] 를 알아야 통과한다.
// 아직 모르면 관문 30px 앞에서 기다린다. 전부 알면 남은 구간을 짧게(구간당 260ms) 마무리한다. 클릭·Esc = 건너뛰기(settle).
"use client";

import { useEffect, useRef, useState } from "react";
import { createEngine, SCENE, type Engine } from "./scene-engine";
import { cn } from "@/lib/utils";

const LABELS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "참가 자격 통과 공고", "검토할 공고"] as const;
const REASONS = ["등록업종 미허용", "면허·지역 제한 미충족", "회사와의 유사도 낮음"] as const;

export type SceneCounts = { total: number | null; industry: number | null; candidates: number | null; passed: number | null; results: number | null };

function subOf(c: SceneCounts, i: number): string {
  const pct = (a: number | null, b: number | null, d = 1) => (a != null && b ? `${((a / b) * 100).toFixed(d)}%` : "…");
  if (i === 0) return " · 마감 90일 이내";
  if (i === 1) return ` · 전체의 ${pct(c.industry, c.total)}`;
  if (i === 2) return c.passed === 0 ? " · 면허·지역 0% 통과" : ` · 후보 ${c.candidates ?? "…"}건 중 ${pct(c.passed, c.candidates, 0)} 통과`;
  return c.results === 0 ? " · 없음" : ` · 앞 단계의 ${pct(c.results, c.passed)}`;
}

export function Scene({ counts, state, onSettled }: { counts: SceneCounts; state: "running" | "done" | "error"; onSettled: () => void }) {
  const cv = useRef<HTMLCanvasElement>(null);
  const labs = useRef<(HTMLDivElement | null)[]>([]);
  const rsns = useRef<(HTMLSpanElement | null)[]>([]);
  const eng = useRef<Engine | null>(null);
  const xRef = useRef(0);
  const [settled, setSettled] = useState(false);
  const reduce = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

  const cnt = [counts.total ?? -1, counts.industry ?? -1, counts.passed ?? -1, counts.results ?? -1];
  const known = [counts.total != null, counts.industry != null, counts.passed != null, counts.results != null];
  const firstUnknown = known.findIndex((k) => !k);
  const target = state === "error" ? Math.min(xRef.current, SCENE.XS[3] - 30) : firstUnknown < 0 ? SCENE.W : Math.max(0, SCENE.XS[firstUnknown] - 30);

  useEffect(() => {
    if (!cv.current) return;
    const e = createEngine(cv.current, labs.current.filter(Boolean) as HTMLElement[], rsns.current.filter(Boolean) as HTMLElement[], cnt);
    eng.current = e; e.setup(); e.paint(0, false);
    const onResize = () => { e.setup(); e.paint(xRef.current, settled); };
    addEventListener("resize", onResize);
    return () => removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { eng.current?.setCounts(cnt); eng.current?.paint(xRef.current, settled); }, [cnt.join(","), settled]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (settled || state === "error") return;
    if (reduce) { if (target >= SCENE.W) finish(); return; }
    let raf = 0; const from = xRef.current, t0 = performance.now();
    const dist = Math.max(0, target - from); const dur = Math.max(1, dist / 288) * 260;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      xRef.current = from + dist * (1 - Math.pow(1 - p, 2.2));
      eng.current?.paint(xRef.current, false);
      if (p < 1) raf = requestAnimationFrame(tick);
      else if (target >= SCENE.W) setTimeout(finish, 150);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, settled, state]);

  function finish() {
    if (settled) return;
    xRef.current = SCENE.W; eng.current?.paint(SCENE.W, true); setSettled(true); onSettled();
  }
  function skip() { if (state !== "error") finish(); }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") skip(); };
    addEventListener("keydown", onKey); return () => removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled, state]);

  const done = settled && state !== "error";
  return (
    <div data-scene data-done={done} className={cn("mt-5 border-t border-ink", !done && state !== "error" && "cursor-pointer")} onClick={skip} aria-hidden="true">
      <div className={cn("relative overflow-hidden transition-[height] duration-500 [transition-timing-function:var(--ease-sheet)]", done ? "h-0" : "h-14 max-sm:h-auto max-sm:grid max-sm:grid-cols-4 max-sm:gap-x-2.5 max-sm:py-2.5")}>
        {LABELS.map((k, i) => (
          <div key={k} ref={(el) => { labs.current[i] = el; }} data-x={SCENE.XS[i]} data-lab
            className={cn("absolute top-1 opacity-0 transition-opacity duration-[400ms] max-sm:static", i > 0 && "border-l border-field pl-3 max-sm:border-0 max-sm:pl-0")}
            style={{ left: `${(SCENE.XS[i] / SCENE.W) * 100}%` }}>
            <span className="block text-[12px] text-ink-g">{k}</span>
            <span className={cn("num mt-[5px] block text-[26px] font-[650] tracking-[-0.04em] max-sm:text-[18px]", i === 3 ? "text-orange" : "text-ink")}>
              <span className="cnt" data-to={cnt[i]} />
              <small className="text-[11.5px] font-normal text-ink-mute">{subOf(counts, i)}</small>
            </span>
          </div>
        ))}
      </div>
      <div className={cn("relative overflow-hidden transition-[height] duration-[550ms] [transition-timing-function:var(--ease-sheet)]", done ? "h-0" : "h-[392px] max-sm:h-[220px]")}>
        <canvas ref={cv} height={SCENE.H} className={cn("block h-[392px] w-full transition-transform duration-[550ms] max-sm:h-[220px]", done && "-translate-y-[150px]")} />
        {REASONS.map((r, i) => (
          <span key={r} ref={(el) => { rsns.current[i] = el; }} data-x={SCENE.XS[i + 1] + 14} data-rsn={i + 1}
            className={cn("absolute text-[11.5px] text-ink-mute opacity-0 transition-opacity duration-[400ms] max-sm:hidden", i === 2 && counts.passed === 0 && "hidden")}
            style={{ right: `${100 - (SCENE.XS[i + 1] / SCENE.W) * 100}%`, top: 346, marginRight: 8 }}>{r}</span>
        ))}
      </div>
    </div>
  );
}
```

`globals.css` 에 두 줄: `[data-lab].on, [data-rsn].on { opacity: 1; }` — 엔진이 `classList.toggle('on')` 으로 켠다(Tailwind 클래스 토글은 엔진이 모른다). 390 에서는 라벨이 4칸 격자(`max-sm:` 클래스), 캔버스 220px(원본 `setup()` 의 `sy` 세로 배율 유지).

- [x] **Step 3: 확인** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0, `npm run lint` 통과(페이지 연결은 Task 7 에서 눈으로 본다).

- [x] **Step 4: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/results/scene-engine.ts frontend/src/components/results/Scene.tsx frontend/src/app/globals.css && git commit -m "feat(renewal): 머리 장면 — gen_flow 엔진 포팅 + funnel/stage 이벤트 구동 러너(관문 앞 대기·짧은 마무리·건너뛰기·reduced-motion)"
```

---

### Task 6: `FunnelLine` · `CompanySide` · `ResultRows`

**Files:**
- Create: `frontend/src/components/results/FunnelLine.tsx`, `CompanySide.tsx`, `ResultRows.tsx`
- Modify: `frontend/src/components/Sheet.tsx`(`SheetRow` 에 `onOpen?: () => void`)

- [x] **Step 1: `FunnelLine`** (시안 `.chain` + `.tabs`, 판 스킨 숫자 28 / 마지막 34)

```tsx
// frontend/src/components/results/FunnelLine.tsx
// 걸러낸 경로(숫자 + 단계 라벨) 왼쪽, 종류 탭·마감 요약 오른쪽. 장면이 접힌 뒤(open) 펼쳐진다. 0건이면 탭·마감 요약 숨김(12건 기준 계산이라 거짓).
import { cn } from "@/lib/utils";
import type { SceneCounts } from "./Scene";

const LABELS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "참가 자격 통과 공고", "검토할 공고"];
const fmt = (n: number | null) => (n == null ? "…" : n.toLocaleString("ko-KR"));

export function FunnelLine({ counts, open, tabs, due }: {
  counts: SceneCounts; open: boolean;
  tabs: { notices: number; preSpecs: number; orderPlans: number } | null;
  due: { week: number; soonest: { days: number; month: number; day: number } | null } | null;
}) {
  const nums = [counts.total, counts.industry, counts.passed, counts.results];
  return (
    <div data-funnel className={cn("grid grid-cols-[1fr_auto] items-start gap-6 transition-[grid-template-rows,padding] duration-[450ms] [transition-timing-function:var(--ease-sheet)] max-sm:grid-cols-1 max-sm:gap-y-2.5", open ? "grid-rows-[1fr] pt-4" : "grid-rows-[0fr]")}>
      <div className="flex min-h-0 items-start gap-3 overflow-hidden">
        <span className="t-k pt-[3px] max-sm:hidden">걸러낸 경로</span>
        {LABELS.map((l, i) => (
          <div key={l} className="contents">
            {i > 0 && <i className="pt-0.5 text-[16px] not-italic text-ink-mute">→</i>}
            <div className="flex flex-col">
              <span className="num flex items-baseline">
                <b className={cn("text-[28px] leading-[1.15] max-sm:text-[20px]", i === 3 && "text-[34px] text-orange max-sm:text-[24px]")} data-n={i}>{fmt(nums[i])}</b>
                {i === 3 && <span className="ml-1 text-[11.5px] text-ink-mute">건</span>}
              </span>
              <span className="mt-[3px] text-[12.5px] leading-[1.3] text-ink-mute max-sm:text-[10.5px]">{l}</span>
            </div>
          </div>
        ))}
      </div>
      {tabs && due && (
        <div className="min-h-0 overflow-hidden text-right text-[14px] leading-[1.9] text-ink-g max-sm:text-left" data-tabs>
          <div>
            <em className="border-b border-ink pb-px font-[650] not-italic text-ink">공고 {tabs.notices}</em>
            <span className="before:mx-2 before:text-[#c9c9c4] before:content-['·']">사전규격 {tabs.preSpecs}</span>
            <span className="before:mx-2 before:text-[#c9c9c4] before:content-['·']">발주계획 {tabs.orderPlans}</span>
          </div>
          <div>
            이번 주 마감 {due.week}건 · 가장 빠른 마감{" "}
            {due.soonest ? <><span className={cn("font-[650]", due.soonest.days <= 7 ? "text-orange" : "text-ink")}>D-{due.soonest.days}</span> ({due.soonest.month}.{String(due.soonest.day).padStart(2, "0")})</> : "—"}
          </div>
        </div>
      )}
    </div>
  );
}
```

`due` 는 `companyStats(results.map(r => r.bid_clse_date))`(03 `lib/saved-stats.ts`)로 호출자가 만든다 — 12건 전체 기준(README 결정).

- [x] **Step 2: `CompanySide`** (시안 `gen_split.py:107-124` 문구 그대로, 720 이하 `<details>` 접힘)

```tsx
// frontend/src/components/results/CompanySide.tsx
// 왼쪽 단 — 추천 기준이 되는 회사 정보. 판정 규칙 문구는 시안 그대로(공문 톤).
"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Btn } from "@/components/Btn";
import { rgnBase } from "@/lib/format";
import type { CompanySideData } from "@/app/api/companies/[bizrno]/profile/route";

function dedupeIndustries(names: string[]): string[] {
  const seen = new Set<string>(); const out: string[] = [];
  for (const n of names) { const k = n.split("(")[0].trim(); if (!seen.has(k)) { seen.add(k); out.push(k); } }
  return out;
}

export function CompanySide({ bizrnoNorm, region }: { bizrnoNorm: string; region: string | null }) {
  const [d, setD] = useState<CompanySideData | null>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => {
    const ac = new AbortController();
    fetch(`/api/companies/${bizrnoNorm}/profile`, { signal: ac.signal }).then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    if (matchMedia("(max-width: 720px)").matches) setOpen(false);
    return () => ac.abort();
  }, [bizrnoNorm]);
  const inds = d ? dedupeIndustries(d.industries) : [];
  return (
    <details open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} data-side
      className="sticky top-0 pb-5 pt-[22px] text-[14px] max-sm:static max-sm:border-b max-sm:border-rule max-sm:py-3.5 max-sm:text-[13.5px]">
      <summary className="t-k list-none cursor-default max-sm:flex max-sm:cursor-pointer max-sm:justify-between">회사 정보<span className="hidden max-sm:inline">{open ? "접기" : "펼치기"}</span></summary>
      <Sec k={`등록업종 ${d?.industries.length ?? "…"}`}>
        <ul className="m-0 list-none p-0">
          {inds.map((n, i) => (
            <li key={n} className={`border-b border-[#f1f0ec] py-1 leading-[1.5] text-ink-g ${i < (d?.repCount ?? 1) ? "font-semibold after:ml-1.5 after:text-[10.5px] after:font-medium after:text-ink-mute after:content-['대표']" : ""}`}>{n}</li>
          ))}
        </ul>
      </Sec>
      <Sec k="공급물품">{d && d.products.length > 0 ? `${d.products.length}종` : <><span className="text-ink-dim">등록 없음</span> — 물품 공고 추천에는 등록 필요</>}</Sec>
      <Sec k="지역">본사 <b className="font-semibold text-ink">{rgnBase(region) || "—"}</b><br /><span className="text-ink-dim">제한 공고가 적은 단위(시·도 또는 시·군·구)까지 판정</span></Sec>
      <Sec k="면허">공고 요구 면허 그룹마다 등록업종 중 하나 포함 시 통과</Sec>
      <Sec k="규모"><span className="text-ink-dim">미입력</span> — 소기업·중소기업 제한 공고 판정 기준</Sec>
      <Sec k="사업자 상태">{d ? `${d.status} · ${d.restricted ? "제재 있음" : "제재 없음"}` : "…"}</Sec>
      <div className="mt-[18px] flex items-center gap-2.5 border-t border-hair pt-3.5">
        <Btn variant="dark" className="h-8" href={`/companies/${bizrnoNorm}`}>확인</Btn>
        <Btn variant="text" className="h-8" href="/privacy#request"><u>수정 요청</u></Btn>
      </div>
      <span className="mt-2.5 block text-[12px] text-ink-mute">나라장터 업체정보{d?.checkedAt ? ` · ${d.checkedAt.slice(5).replace("-", ".")} 갱신` : ""}</span>
    </details>
  );
}

function Sec({ k, children }: { k: string; children: ReactNode }) {
  return (<div className="pt-4 leading-[1.7] text-ink-g"><span className="t-k block">{k}</span><div className="mt-1 text-[14px]">{children}</div></div>);
}
```

"확인"은 회사 페이지로, "수정 요청"은 개인정보처리방침의 요청 절로(09 에서 전용 폼이 생기면 바꾼다) — 시안의 `#` 링크를 실제 목적지로 채운 것.

- [x] **Step 3: `Sheet.tsx` 에 `onOpen`** — `SheetRowProps` 에 `onOpen?: () => void;` 추가, 펼침 토글이 닫힘→열림으로 바뀔 때 한 번 호출. `check_foundation.py` 영향 없음.

- [x] **Step 4: `ResultRows`** (표 + 게이트 + 흐림 + 0건)

```tsx
// frontend/src/components/results/ResultRows.tsx
// 오른쪽 단 — 표 5건 + Gate + 흐림 7건(로그인이면 전부). 행 펼침 안: 참가 자격·추천 근거·나라장터 원문·검토.
"use client";

import { useState } from "react";
import { Gate } from "@/components/Gate";
import { Btn } from "@/components/Btn";
import { ReviewButton } from "@/components/ReviewButton";
import { SheetExpand, SheetFade, SheetHead, SheetRow } from "@/components/Sheet";
import { dLeft, won } from "@/lib/format";
import { emitNoticeEvent } from "@/lib/events";
import { strongestWhy } from "@/lib/saved-stats";
import { qualLines, whyLines } from "@/lib/why";
import type { BidRecommendation } from "@/types/recommendations";

const FREE = 5;

export function ResultRows({ results, loggedIn, reviewed, viaBizrno, next, today, keywordMode = false }: {
  results: BidRecommendation[]; loggedIn: boolean; reviewed: Set<string>; viaBizrno: string | null; next: string; today: Date; keywordMode?: boolean;
}) {
  const [rv, setRv] = useState(reviewed);
  const row = (b: BidRecommendation, i: number) => {
    const key = `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
    const org = b.dmnd_instt_nm || b.ntce_instt_nm || "—";
    const why = keywordMode ? null : strongestWhy(b.score_breakdown);
    const ev = { bid_ntce_no: b.bid_ntce_no, bid_ntce_ord: b.bid_ntce_ord, target_bizrno: viaBizrno, rank_position: i + 1, algorithm_version: "v2", score: b.score };
    return (
      <SheetRow key={key} no={i + 1} title={b.bid_ntce_nm} org={org} why={why ?? undefined} dLeft={dLeft(b.bid_clse_date, today)} price={won(b.presmpt_prce)}
        reviewed={rv.has(key)} defaultOpen={i === 0} href={`/notices/${b.bid_ntce_no}`}
        onOpen={() => emitNoticeEvent({ event_type: "click", ...ev })}>
        <SheetExpand quals={keywordMode ? [] : qualLines(b.qualification)} whys={keywordMode ? [] : whyLines(b.score_breakdown, org)}
          actions={<>
            {b.bid_ntce_url && <Btn variant="dark" href={b.bid_ntce_url} target="_blank" rel="noopener">나라장터 원문</Btn>}
            <ReviewButton no={b.bid_ntce_no} ord={b.bid_ntce_ord} via={viaBizrno} why={why} reviewed={rv.has(key)} loggedIn={loggedIn}
              onChange={(on) => { setRv((s) => { const n = new Set(s); if (on) n.add(key); else n.delete(key); return n; }); if (on) emitNoticeEvent({ event_type: "save", ...ev }); }} />
          </>} />
      </SheetRow>
    );
  };
  const head = results.slice(0, loggedIn ? results.length : FREE);
  const rest = loggedIn ? [] : results.slice(FREE);
  return (
    <div data-rows>
      <SheetHead />
      {head.map(row)}
      {rest.length > 0 && <Gate rest={rest.length} next={next} />}
      {rest.length > 0 && <SheetFade>{rest.map((b, i) => row(b, i + FREE))}</SheetFade>}
    </div>
  );
}

export function ZeroBlock({ reason, viaBizrno }: { reason: "qualify" | "rank"; viaBizrno: string | null }) {
  return (
    <div data-zero className="pb-[34px] pt-[22px]">
      <b className="block text-[18px] font-[650] tracking-[-0.015em] text-ink">{reason === "qualify" ? "참가 자격이 있는 공고가 없습니다" : "검토할 공고가 없습니다"}</b>
      <span className="mt-1.5 block text-[14px] text-ink-dim">기준 확인 또는 키워드 검색</span>
      <div className="mt-[18px] flex flex-wrap items-center gap-2.5">
        <Btn variant="dark" href="/recommendations">키워드로 공고 검색</Btn>
        {viaBizrno && <Btn href="/privacy#request">업종·물품 수정 요청</Btn>}
      </div>
    </div>
  );
}
```

`emitNoticeEvent` 시그니처는 `lib/events.ts:35-39` 를 읽고 맞춘다(필드명 `rank_position`·`algorithm_version`·`score`·`target_bizrno`). 0건 블록의 "키워드로 공고 검색"은 입구(`/recommendations` 빈 질의 = SearchBox)로.

- [x] **Step 5: 확인·커밋** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0, `npm run lint`.

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/results frontend/src/components/Sheet.tsx && git commit -m "feat(renewal): 결과 페이지 부품 — 걸러낸 경로·종류 탭·마감 요약, 회사 정보 단, 표(게이트·흐림·검토·0건)"
```

---

### Task 7: `ResultsView` 상태 기계 + 페이지 교체

**Files:**
- Create: `frontend/src/components/results/ResultsView.tsx`, `frontend/src/app/(renewal)/recommendations/page.tsx`
- Modify: `frontend/src/components/Panel.tsx`(`data-*` 통과)
- Delete: `frontend/src/app/recommendations/page.tsx`, `frontend/src/app/recommendations/loading.tsx`

- [x] **Step 1: `ResultsView`**

```tsx
// frontend/src/components/results/ResultsView.tsx
// 결과 페이지 본체(클라이언트). 상태: running(장면) → done(표) / zero / error / search(다른 회사). 키워드 모드는 장면 없이 표만.
"use client";

import { useEffect, useRef, useState } from "react";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { Btn } from "@/components/Btn";
import { SearchBox } from "@/components/SearchBox";
import { StarCompany } from "@/components/StarCompany";
import { streamRecommendations } from "@/lib/stream";
import { getSessionId } from "@/lib/events";
import { cn, maskBizrno } from "@/lib/utils";
import { companyStats } from "@/lib/saved-stats";
import type { RecommendationResponse } from "@/types/recommendations";
import { Scene, type SceneCounts } from "./Scene";
import { FunnelLine } from "./FunnelLine";
import { CompanySide } from "./CompanySide";
import { ResultRows, ZeroBlock } from "./ResultRows";

const TIMEOUT_MS = 8000;
const EMPTY: SceneCounts = { total: null, industry: null, candidates: null, passed: null, results: null };
const OTHER = "ml-3.5 cursor-pointer border-b border-field text-[13px] font-medium text-ink-g hover:border-orange";

export function ResultsView({ query, mode, keywords, algorithm, from, loggedIn, savedKeys, reviewedKeys, next }: {
  query: string; mode: "company" | "keywords"; keywords: string | null; algorithm: "v1" | "v2"; from: string | null;
  loggedIn: boolean; savedKeys: string[]; reviewedKeys: string[]; next: string;
}) {
  const [counts, setCounts] = useState<SceneCounts>(EMPTY);
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [settled, setSettled] = useState(mode === "keywords");
  const [search, setSearch] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const today = useRef(new Date()).current;

  useEffect(() => {
    const ac = new AbortController();
    let got = false;
    setCounts(EMPTY); setData(null); setError(null);
    const timer = setTimeout(() => { if (!got) { ac.abort(); setError("결과를 불러오지 못했습니다"); } }, TIMEOUT_MS);
    streamRecommendations(
      { query, mode, keywords, algorithm, session_id: getSessionId(), limit: 12, candidate_pool: 200, explain_top: 0, with_explanation: false },
      (e) => {
        if (e.type === "funnel") setCounts((c) => ({ ...c, total: e.total, industry: e.industry }));
        else if (e.type === "stage" && e.stage === "search") setCounts((c) => ({ ...c, candidates: e.candidates }));
        else if (e.type === "stage" && e.stage === "qualify") setCounts((c) => ({ ...c, candidates: e.candidates, passed: e.passed }));
        else if (e.type === "stage" && e.stage === "rank") setCounts((c) => ({ ...c, results: e.results }));
        else if (e.type === "results") { got = true; clearTimeout(timer); setData(e.data); setCounts((c) => ({ ...c, results: e.data.results.length, passed: c.passed ?? (mode === "keywords" ? null : 0) })); }
        else if (e.type === "error") { got = true; clearTimeout(timer); setError(e.message); }
      },
      ac.signal,
    ).catch((err) => { if (!ac.signal.aborted) { clearTimeout(timer); setError(String(err?.message || "결과를 불러오지 못했습니다")); } });
    return () => { clearTimeout(timer); ac.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, mode, keywords, algorithm, attempt]);

  // 회사 모드인데 회사를 못 찾았으면 키워드로 넘어간다(옛 보드와 같은 규칙)
  useEffect(() => {
    if (mode === "company" && data && !data.company && data.fallback === "keywords") {
      location.replace(`/recommendations?q=${encodeURIComponent(query)}&from=company`);
    }
  }, [data, mode, query]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSearch(false); };
    addEventListener("keydown", onKey); return () => removeEventListener("keydown", onKey);
  }, []);

  const co = data?.company ?? null;
  const bizrno = co ? co.bizrno.replace(/\D/g, "") : null;
  const results = data?.results ?? [];
  const state: "running" | "done" | "error" = error ? "error" : settled && data ? "done" : "running";
  const zero = state === "done" && results.length === 0;
  const stats = results.length ? companyStats(results.map((r) => r.bid_clse_date), today) : null;

  return (
    <div className={cn(search && "[&_[data-scene]]:opacity-20 [&_[data-scene]]:blur-[1px] [&_[data-res]]:opacity-20 [&_[data-res]]:blur-[1px] [&_[data-res]]:pointer-events-none")}>
      {search ? (
        <div className="pb-1 pt-[26px]" data-search>
          <SearchBox autoFocus onSubmitted={() => setSearch(false)} />
          <div className="mt-2.5 flex max-w-[720px] items-center gap-3.5 text-[13px] text-ink-g">
            <span className="t-k">최근 조회</span>
            {co && <a className="border-b border-field text-ink" href={`/recommendations?company=${encodeURIComponent(co.bizrno)}`}>{co.corp_nm}</a>}
            <button type="button" className="ml-auto cursor-pointer text-ink-mute" onClick={() => setSearch(false)}>취소 · Esc</button>
          </div>
        </div>
      ) : mode === "company" ? (
        <PageHead title={co?.corp_nm ?? query} small={co ? maskBizrno(co.bizrno) : undefined} className="border-b-0 pb-0"
          aside={<>
            {bizrno && <StarCompany bizrnoNorm={bizrno} saved={savedKeys.includes(bizrno)} loggedIn={loggedIn} className="ml-3 h-[30px] text-[13px]" />}
            <button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 회사</button>
          </>}
          meta={co ? [co.rgn_nm ?? "—", `기준일 ${today.toISOString().slice(0, 10)}`] : undefined} />
      ) : (
        <PageHead title={`“${query}”`} className="border-b-0 pb-0" aside={<button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 검색</button>}
          meta={[from === "company" ? "회사명으로 찾지 못해 키워드로 검색" : "입력한 관심 분야와 의미가 가까운 순서"]} />
      )}

      {mode === "company" && <Scene counts={counts} state={state} onSettled={() => setSettled(true)} />}
      {mode === "keywords" && <div className="mt-5 border-t border-ink" />}

      {error && (
        <div data-err className="flex items-center gap-3.5 border-t border-hair py-4 text-[13.5px] text-ink">
          <span>결과를 불러오지 못했습니다</span><span className="flex-1" />
          <Btn onClick={() => { setSettled(mode === "keywords"); setAttempt((a) => a + 1); }}>다시 시도</Btn>
        </div>
      )}

      {mode === "company" && !error && (
        <FunnelLine counts={counts} open={state === "done"} tabs={zero || !data ? null : { notices: results.length, preSpecs: data.pre_spec_results?.length ?? 0, orderPlans: data.order_plan_results?.length ?? 0 }} due={stats} />
      )}

      {state === "done" && data && (
        <Panel data-res className="mt-[22px] translate-y-0 opacity-100 transition-[opacity,transform] duration-500 [transition-timing-function:var(--ease-sheet)] starting:translate-y-2.5 starting:opacity-0">
          <div className={cn("grid items-start gap-x-11", mode === "company" ? "grid-cols-[240px_minmax(0,1fr)] max-sm:grid-cols-1" : "grid-cols-1")}>
            {mode === "company" && bizrno && <CompanySide bizrnoNorm={bizrno} region={co?.rgn_nm ?? null} />}
            <div className="pt-[22px] max-sm:pt-3.5">
              {!zero && (
                <div className="flex items-center justify-between border-b border-ink pb-2.5">
                  <span className="t-k"><b className="mr-1.5 text-[14px] font-[650] text-ink">검토할 공고 {results.length}건</b>{mode === "company" ? "적합 순" : "유사도 순"}</span>
                  {mode === "company" && co && <a href={loggedIn ? `/recommendations/report?company=${encodeURIComponent(co.bizrno)}` : `/login?next=${encodeURIComponent(`/recommendations/report?company=${co.bizrno}`)}`} className="border-b border-field text-[13px] text-ink-g hover:border-orange">인쇄 / PDF 저장</a>}
                </div>
              )}
              {zero ? <ZeroBlock reason={counts.passed === 0 ? "qualify" : "rank"} viaBizrno={bizrno} />
                    : <ResultRows results={results} loggedIn={loggedIn} reviewed={new Set(reviewedKeys)} viaBizrno={bizrno} next={next} today={today} keywordMode={mode === "keywords"} />}
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
```

`starting:` 변형(`@starting-style`)이 Tailwind v4 에 있다 — 없으면 `useEffect` 로 마운트 뒤 클래스를 바꾸는 두 줄로 대신한다. `Panel` 이 `data-*` 를 받지 않으면 `Panel.tsx` props 를 `{ children, className } & ComponentProps<"section">` 로 넓히고 `...rest` 를 펼친다. `explain_top: 0` — LLM 설명·총평은 이 페이지에서 쓰지 않는다(카드 = 근거 칩). `getSessionId` 는 `lib/events.ts:8-20`. `maskBizrno`·`cn` 은 `lib/utils.ts`.

- [x] **Step 2: 페이지** — 옛 `app/recommendations/page.tsx` 의 URL 계약을 그대로 옮긴다.

```tsx
// frontend/src/app/(renewal)/recommendations/page.tsx
// 결과 페이지. URL 계약은 옛 페이지 그대로: company=회사명|사업자번호 / q=키워드 / keywords=하이브리드 / algorithm=v1|v2 / from=company. 공고번호면 공고 상세로.
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { PageHead } from "@/components/PageHead";
import { SearchBox } from "@/components/SearchBox";
import { ResultsView } from "@/components/results/ResultsView";
import { getSessionUser } from "@/lib/auth";
import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";

export const metadata: Metadata = { title: "추천 공고 | 조달핏", robots: { index: false, follow: false } };

const NOTICE_NO = /^\s*(R\d{2}[A-Z]{2}\d{6,})(?:-\d{3})?\s*$/i;

export default async function RecommendationsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const p = await searchParams;
  const one = (k: string) => { const v = p[k]; return (Array.isArray(v) ? v[0] : v)?.trim() || ""; };
  const company = one("company"), q = one("q"), keywords = one("keywords") || null, from = one("from") || null;
  const algorithm = one("algorithm") === "v1" ? "v1" : "v2";
  const query = company || q;
  const m = query.match(NOTICE_NO);
  if (m) redirect(`/notices/${m[1].toUpperCase()}`);

  const user = await getSessionUser();
  const [saved, reviewed] = user ? await Promise.all([getSavedCompanyKeys(), getReviewedKeys()]) : [new Set<string>(), new Set<string>()];
  const qs = new URLSearchParams(Object.entries(p).flatMap(([k, v]) => (typeof v === "string" ? [[k, v]] : []))).toString();
  const next = `/recommendations${qs ? `?${qs}` : ""}`;

  if (!query) {
    return (
      <>
        <PageHead title="추천 공고" meta={["회사명 · 사업자등록번호 · 업종 또는 품목으로 검색"]} />
        <div className="mt-6"><SearchBox autoFocus /></div>
      </>
    );
  }
  return (
    <ResultsView key={`${company ? "company" : "keywords"}:${query}:${keywords ?? ""}:${algorithm}`}
      query={query} mode={company ? "company" : "keywords"} keywords={keywords} algorithm={algorithm} from={from}
      loggedIn={!!user} savedKeys={[...saved]} reviewedKeys={[...reviewed]} next={next} />
  );
}
```

옛 페이지 삭제: `git rm -r frontend/src/app/recommendations`(같은 경로가 둘이면 Next 가 빌드에서 막는다). `components/board/*`·`BoardSearch` 는 남긴다(09 삭제) — `grep -rn "components/board" frontend/src` 로 다른 import 가 남아 있으면(랜딩 `app/page.tsx` 등) 그대로 둔다(04 가 랜딩을 바꾼다).

- [x] **Step 3: 눈으로 확인** — 백엔드(:8000, Task 2 반영)와 프론트 개발 서버를 띄우고:
  - `http://localhost:3000/recommendations?company=1248177731` — 장면이 이벤트 따라 진행·접힘 → 걸러낸 경로 숫자 넷 → 흰 판 두 단, 표 5 + 게이트 + 흐림 7(비로그인), 로그인하면 12 전부. 행 펼침에 자격 3줄·근거·나라장터 원문·검토.
  - `?q=하수처리` — 장면 없이 표.
  - `?company=존재하지않는회사zzz` — 키워드로 넘어감(`from=company`).
  - "다른 회사" → 상자 + 최근 조회 + 취소 · Esc.
  - 백엔드를 끄고 열면 8초 뒤 "결과를 불러오지 못했습니다 · 다시 시도".
  - 390 폭에서 가로 넘침 없음, 회사 정보가 접힌 한 줄.
  `npx tsc --noEmit -p tsconfig.json; echo $?` → 0, `npm run lint`, `npm run build 2>&1 | tail -5` 성공.

- [x] **Step 4: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add -A frontend/src/app/recommendations "frontend/src/app/(renewal)/recommendations" frontend/src/components/results/ResultsView.tsx frontend/src/components/Panel.tsx && git commit -m "feat(renewal): /recommendations 교체 — 머리(☆·다른 회사)·이벤트 구동 장면·걸러낸 경로·두 단 표·네 상태, 옛 보드 페이지 삭제"
```

---

### Task 8: 인쇄 뷰 `/recommendations/report`

**Files:**
- Create: `frontend/src/app/(renewal)/recommendations/report/page.tsx`, `frontend/src/app/(renewal)/recommendations/report/PrintButton.tsx`
- Modify: `frontend/src/app/globals.css`(`@page`·`.report` 인쇄 규칙)

- [x] **Step 1: 페이지** — 로그인 사용자만(아니면 `/login?next=`). 비스트림 `getRecommendations`(서버 self-call, `X-Internal-Token` 자동, 캐시 read-through)로 12건. 시안 `gen_report.py:97-107` 구성·문구 그대로.

```tsx
// frontend/src/app/(renewal)/recommendations/report/page.tsx
// 추천 공고 보고서 — A4 세로 한 장. 화면에선 종이색 위 210mm 판, 위에 "인쇄 / PDF 저장"만. 인쇄는 nav·footer 숨김(globals.css .report).
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Tile } from "@/components/Logo";
import { getRecommendations } from "@/lib/api";
import { getSessionUser } from "@/lib/auth";
import { dLeft, rgnBase, won } from "@/lib/format";
import { qualLines, whyLines } from "@/lib/why";
import { PrintButton } from "./PrintButton";

export const metadata: Metadata = { robots: { index: false, follow: false } };
const LABELS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "참가 자격 통과 공고", "검토할 공고"];

export default async function ReportPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const p = await searchParams;
  const company = (p.company ?? "").trim();
  if (!company) redirect("/recommendations");
  const user = await getSessionUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(`/recommendations/report?company=${company}`)}`);
  const d = await getRecommendations({ query: company, mode: "company", limit: 12, candidate_pool: 200, with_explanation: false });
  if (!d.company) redirect(`/recommendations?company=${encodeURIComponent(company)}`);
  const today = new Date(); const ymd = today.toISOString().slice(0, 10);
  const f = d.funnel ?? null; const res = d.results;
  // 비스트림 응답은 stage 를 모른다 — 셋째 칸(자격 통과)은 "—", 넷째는 결과 수
  const nums = [f?.total ?? null, f?.industry ?? null, null, res.length];
  return (
    <div className="report mx-auto w-[210mm] max-sm:w-auto">
      <div className="report-nav flex items-center justify-between py-[18px] pb-3 text-[13px] text-ink-g">
        <a href={`/recommendations?company=${encodeURIComponent(company)}`} className="border-b border-field text-ink">← 결과로 돌아가기</a>
        <PrintButton />
      </div>
      <div className="report-page flex min-h-[297mm] flex-col border border-hair bg-panel p-[16mm] text-[10px] leading-[1.3] text-ink">
        <div className="flex items-start justify-between border-b border-ink pb-2">
          <span className="flex items-center gap-1.5 text-[12px] font-extrabold tracking-[-0.035em]"><Tile size={20} />조달핏</span>
          <div className="text-right"><b>추천 공고 보고서 · 기준일 {ymd}</b><div className="mt-0.5 text-ink-g">{d.company.corp_nm} · {rgnBase(d.company.rgn_nm) || "—"}</div></div>
        </div>
        <div className="mt-2.5 flex items-start gap-3 border-b border-hair pb-2">
          <span className="t-k pt-0.5">걸러낸 경로</span>
          {nums.map((n, i) => (
            <div key={LABELS[i]} className="flex items-center gap-3"><div><b className={`num text-[13px] ${i === 3 ? "text-orange" : ""}`}>{n == null ? "—" : n.toLocaleString("ko-KR")}</b><div className="text-[9px] text-ink-mute">{LABELS[i]}</div></div>{i < 3 && <span className="text-ink-mute">→</span>}</div>
          ))}
        </div>
        <div className="t-k mt-3 border-b border-ink pb-1">검토할 공고 {res.length}건 · 적합 순</div>
        {res.map((b, i) => {
          const org = b.dmnd_instt_nm || b.ntce_instt_nm || "—"; const dl = dLeft(b.bid_clse_date, today);
          const q = qualLines(b.qualification).map((l) => (l.state === "todo" ? "규모 미입력" : l.text.replace(" — ", " ") + (l.state === "ok" ? " ✓" : l.state === "warn" ? " !" : ""))).join(" · ");
          return (
            <div key={`${b.bid_ntce_no}-${b.bid_ntce_ord}`} className="grid grid-cols-[20px_1fr] gap-x-1.5 border-b border-[#ececea] py-1.5 break-inside-avoid">
              <span className="num text-ink-mute">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <div className="flex items-baseline justify-between gap-3"><b className="text-[10.5px]">{b.bid_ntce_nm}</b>
                  <span className="num shrink-0">마감 <span className={dl && dl.days <= 7 ? "font-semibold text-orange" : "font-semibold"}>{dl ? `D-${dl.days}` : "—"}</span>{dl && ` (${dl.month}.${String(dl.day).padStart(2, "0")})`} · 추정가 {won(b.presmpt_prce)}</span></div>
                <div className="text-ink-g">{org}{b.bid_ntce_url && <> · <span className="text-ink-mute">{b.bid_ntce_url.replace("https://www.", "")}</span></>}</div>
                <div><span className="text-ink-mute">참가 자격</span> {q}</div>
                <div><span className="text-ink-mute">추천 근거</span> {whyLines(b.score_breakdown, org).slice(0, 2).join(" · ")}</div>
              </div>
            </div>
          );
        })}
        <div className="mt-auto flex items-center justify-between border-t border-ink pt-1.5 text-[9px] text-ink-g">
          <span><b className="text-ink">조달핏</b> · jodalfit.co.kr · 이 보고서는 낙찰 예측이 아니라 검토 대상 선별입니다 · 자격 판정은 나라장터 업체정보와 공고 제한 필드 기준이며 서류로 증빙되는 조건은 판정하지 않습니다</span>
          <span className="num">1 / 1</span>
        </div>
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/app/(renewal)/recommendations/report/PrintButton.tsx
"use client";
export function PrintButton() {
  return <button type="button" onClick={() => window.print()} className="cursor-pointer border-b-2 border-orange pb-px text-ink">인쇄 / PDF 저장</button>;
}
```

`Tile` 은 `Logo.tsx:23`. 비스트림 응답의 `funnel` 은 Task 2(c) 에서 넣었다 — 캐시된 옛 payload 에는 없으니 `—` 로 degrade. `getRecommendations` 의 `RecommendInput` 에 `candidate_pool`·`with_explanation` 이 있는지 `lib/api.ts:19` 에서 확인.

- [x] **Step 2: 인쇄 CSS** — `globals.css` 끝에:

```css
/* 추천 공고 보고서(/recommendations/report) — A4 한 장 */
@page { size: A4; margin: 16mm; }
.report { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
@media print {
  html, body { background: #fff; }
  .rn nav, .rn footer, .report-nav { display: none !important; }
  .rn > div { padding: 0 !important; max-width: none !important; }
  .report { width: auto; }
  .report-page { width: auto; min-height: 264mm; margin: 0; border: 0; padding: 0; }
}
@media screen and (max-width: 820px) { .report-page { padding: 24px 16px; min-height: 0; } }
```

`.rn nav`·`footer` 선택자는 `(renewal)/layout.tsx` 의 실제 요소에 맞춘다(`Nav` 가 `<nav>` 인지, `SiteFooter` 가 `<footer>` 인지 확인해 그 태그·클래스로).

- [x] **Step 3: 확인·커밋** — 로그인한 브라우저에서 `/recommendations/report?company=1248177731` → 12행, 인쇄 미리보기에서 1장. `npx tsc`, `npm run lint`.

```bash
cd C:/Dev/personal/jodalfit && git add "frontend/src/app/(renewal)/recommendations/report" frontend/src/app/globals.css && git commit -m "feat(renewal): 추천 공고 보고서(/recommendations/report) — A4 한 장 인쇄 뷰"
```

---

### Task 9: 화면 검증 `check_results.py`

**Files:**
- Create: `frontend/scripts/check_results.py`

전제: 백엔드 :8000(Task 2 반영) + 프론트 :3000. 로그인 흐름은 `check_saved.py` 와 같은 Admin API 사용자로.

- [x] **Step 1: 스크립트**

```python
# frontend/scripts/check_results.py
"""결과 페이지(05) 검증 — 시안 gen_results_final.py --check 를 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_results.py   (RESULTS_BASE 기본 http://localhost:3000)
회사 1248177731(한종산업개발): 장면 → 건너뛰기 → done, 숫자 넷(… 아님), 표 5 + 게이트 2버튼 + 흐림 ≥1, 행 펼침에 자격·근거 줄,
다른 회사 → 상자·흐림 → Esc 복귀, 금지어·주황 면·인주 0, 바닥색·판 14px, 390 한 단·넘침 없음.
키워드(하수처리): 장면 없음, 표 ≥1. 로그인(키 있으면): 게이트 없음·12행, 검토 → 괘선, 보고서.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent; ROOT = OUT.parent.parent
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]
CO = "1248177731"

def env(path, key):
    m = re.search(rf"^{key}=(.*)$", Path(path).read_text(encoding="utf-8"), re.M) if Path(path).exists() else None
    return m.group(1).strip().strip('"') if m else None

RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    overflow: document.documentElement.scrollWidth > window.innerWidth } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, (bad, pg.url)
    s = pg.evaluate(RULES); assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"] and not s["overflow"], (pg.url, s)

def goto(pg, path, wait=600):
    pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(wait)

def wait_done(pg):
    pg.wait_for_selector("[data-scene][data-done=true], [data-err]", timeout=30000)
    assert not pg.query_selector("[data-err]"), "오류 상태 — 백엔드(:8000) 확인"
    pg.wait_for_selector("[data-res]", timeout=5000); pg.wait_for_timeout(700)

def admin(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/auth/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b"{}")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_URL"); anon = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY"); srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None); pg = b.new_page(viewport={"width": 1280, "height": 900})

        # 회사 모드 — 장면 진행 중 건너뛰기
        goto(pg, f"/recommendations?company={CO}", 300)
        assert pg.query_selector("[data-scene]") and not pg.query_selector("[data-scene][data-done=true]"), "장면이 먼저 보여야 한다"
        pg.click("[data-scene]"); wait_done(pg); rules(pg)
        s = pg.evaluate("""() => ({ nums: [...document.querySelectorAll('[data-funnel] b[data-n]')].map(e => e.textContent), acc: getComputedStyle(document.querySelector('[data-funnel] b[data-n="3"]')).color,
            rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, gate: document.querySelectorAll('.hairline a[href^="/login"], .hairline a[href^="/signup"]').length,
            fade: document.querySelectorAll('[inert] [data-sheet-row]').length, side: getComputedStyle(document.querySelector('[data-side]')).position,
            panel: getComputedStyle(document.querySelector('[data-res]')).backgroundColor, radius: getComputedStyle(document.querySelector('[data-res]')).borderRadius,
            quals: document.querySelectorAll('.x-wrap[data-open=true] li').length, star: !!document.querySelector('[data-star]'), other: !!document.querySelector('[data-other]') })""")
        assert "…" not in s["nums"] and s["acc"] == "rgb(249, 115, 22)", s
        assert s["rows"] >= 6 and s["gate"] == 2 and s["fade"] >= 1 and s["side"] == "sticky" and s["panel"] == "rgb(255, 255, 255)" and s["radius"] == "14px" and s["quals"] >= 3 and s["star"] and s["other"], s
        pg.screenshot(path=str(OUT / "_shot_results_default.png"), full_page=True)
        # 다른 회사
        pg.click("[data-other]"); pg.wait_for_timeout(500)
        o = pg.evaluate("() => ({ box: !!document.querySelector('[data-search] [data-searchbox]'), res: getComputedStyle(document.querySelector('[data-res]')).opacity, focus: document.activeElement?.tagName })")
        assert o["box"] and float(o["res"]) < 0.3 and o["focus"] == "INPUT", o
        pg.screenshot(path=str(OUT / "_shot_results_search.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        assert not pg.query_selector("[data-search]") and pg.evaluate("getComputedStyle(document.querySelector('[data-res]')).opacity") == "1"
        # 390
        pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, f"/recommendations?company={CO}", 300); pg.click("[data-scene]"); wait_done(pg); rules(pg)
        m = pg.evaluate("() => ({ open: document.querySelector('[data-side]').open, cols: getComputedStyle(document.querySelector('[data-res] > div')).gridTemplateColumns.split(' ').length })")
        assert m["open"] is False and m["cols"] == 1, m
        pg.screenshot(path=str(OUT / "_shot_results_390.png"), full_page=True)
        pg.set_viewport_size({"width": 1280, "height": 900})
        # 키워드 모드
        goto(pg, "/recommendations?q=%ED%95%98%EC%88%98%EC%B2%98%EB%A6%AC"); pg.wait_for_selector("[data-res]", timeout=30000); rules(pg)
        k = pg.evaluate("() => ({ scene: !!document.querySelector('[data-scene]'), rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, side: !!document.querySelector('[data-side]') })")
        assert not k["scene"] and k["rows"] >= 1 and not k["side"], k
        # 빈 질의 = 입구
        goto(pg, "/recommendations"); assert pg.query_selector("[data-searchbox]")

        if not (url and anon and srv):
            print("ok results(guest): scene→done · funnel 4 · rows/gate/fade · side sticky · other company · 390 · keywords · 로그인 검사 건너뜀"); b.close(); return 0
        email, pw_ = "check-results@jodalfit.test", "check-results-pw-1"
        for u in admin(url, srv, "GET", "/admin/users?per_page=200").get("users", []):
            if u.get("email") == email: admin(url, srv, "DELETE", f"/admin/users/{u['id']}")
        user = admin(url, srv, "POST", "/admin/users", {"email": email, "password": pw_, "email_confirm": True})
        try:
            goto(pg, f"/login?next=%2Frecommendations%3Fcompany%3D{CO}"); pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw_); pg.click("button[type=submit]")
            pg.wait_for_url(re.compile(r"/recommendations")); pg.wait_for_load_state("networkidle"); pg.click("[data-scene]"); wait_done(pg)
            l = pg.evaluate("() => ({ gate: document.querySelectorAll('.hairline a[href^=\"/login\"]').length, rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, fade: document.querySelectorAll('[inert]').length, report: !!document.querySelector('a[href^=\"/recommendations/report\"]') })")
            assert l["gate"] == 0 and l["rows"] >= 6 and l["fade"] == 0 and l["report"], l
            pg.click("[data-review=off]"); pg.wait_for_selector("[data-review=on]"); pg.wait_for_timeout(500)
            assert pg.evaluate("getComputedStyle(document.querySelector('[data-sheet-row]'), '::before').transform") != "matrix(1, 0, 0, 0, 0, 0)"  # scaleY(1)
            pg.screenshot(path=str(OUT / "_shot_results_reviewed.png"), full_page=True)
            goto(pg, f"/recommendations/report?company={CO}"); assert pg.evaluate("document.querySelectorAll('.report-page .break-inside-avoid').length") >= 5
            pg.emulate_media(media="print"); pg.pdf(path=str(OUT / "_report.pdf"), format="A4")
            pg.screenshot(path=str(OUT / "_shot_results_report.png"), full_page=True)
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{user['id']}")
        print("ok results: guest · login(no gate, 12 rows) · review rule · report"); b.close(); return 0

if __name__ == "__main__":
    sys.exit(main())
```

선택자(`[data-scene]`·`[data-done]`·`[data-funnel] b[data-n]`·`[data-res]`·`[data-side]`·`[data-rows]`·`[data-search]`·`[data-searchbox]`·`[data-other]`·`[data-err]`·`.x-wrap[data-open=true]`·`[data-sheet-row]`·`[inert]`·`.hairline a`)는 Task 5~8 의 마크업과 맞춘다 — 다르면 스크립트가 아니라 **마크업의 data 속성을 추가**한다(스타일 변경 없이). PDF 가 2장이면 행 패딩·글자 크기를 시안 값(10px·1.3)으로 되돌린다. 스크린샷·PDF 는 `frontend/.gitignore` 의 `scripts/_shot_*.png` 규칙대로 커밋하지 않는다(`scripts/_report.pdf` 도 ignore 에 한 줄 추가).

- [x] **Step 2: 실행** — 백엔드·프론트 띄운 채 `cd C:/Dev/personal/jodalfit/backend && PYTHONIOENCODING=utf-8 uv run --no-sync python ../frontend/scripts/check_results.py` → `ok results: …`.

- [x] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/scripts/check_results.py frontend/.gitignore && git commit -m "test(renewal): 결과 페이지 Playwright 검증 — 장면·깔때기·표·게이트·다른 회사·390·키워드·로그인·검토·보고서"
```

---

### Task 10: 기록 · 푸시

**Files:**
- Modify: `docs/design/README.md`, `docs/recommender/changelog.md`, `docs/superpowers/plans/2026-10-23-renewal-05-results.md`

- [x] **Step 1: README** 끝에:

```markdown
## 구현 — 05 results (2026-10-2x, 브랜치 `renewal`)
`/recommendations` 교체. 백엔드 `/recommendations/stream` 이 `funnel`(0056 `funnel_counts`: 마감 90일 내 전체·등록업종 허용)·`stage`(search/qualify/rank + 건수) 줄을 `results` 앞에 흘린다 — `recommend()` 를 워커 스레드에서 돌리고 `app/core/progress.py` ContextVar 콜백이 큐에 넣는다. 404 는 `error` 줄. 머리 장면은 `gen_flow` 엔진 포팅(`scene-engine.ts`) + 이벤트 구동 러너(관문 30px 앞 대기, 전부 알면 구간당 260ms, 클릭·Esc 건너뛰기, reduced-motion 즉시). 깔때기 셋째 칸은 **후보 풀 기준**(부제 "후보 N건 중 M% 통과") — 시안의 전수 집계와 다르다. 키워드 모드는 장면 없이 표만. 네 상태: 0건(자격 0 → "참가 자격이 있는 공고가 없습니다", 통과 후 0 → "검토할 공고가 없습니다")·오류(8초·다시 시도)·로그인 뒤(게이트·흐림 없음)·검토 뒤(괘선). 다른 회사 = `SearchBox`(04 와 공용). 왼쪽 단은 `/api/companies/[bizrno]/profile`. 인쇄 `/recommendations/report`(로그인, A4 한 장, 비스트림 캐시). 옛 보드 페이지 삭제(`components/board` 는 09).
빼거나 바꾼 것: 장면 공고명(탈락 공고 9건) 없음 · okline 없음 · "검토함" 라벨·브라우저 저장 안내 없음 · LLM 설명·총평 미사용(`explain_top: 0`) · 종류 탭은 숫자만.
검증: `scripts/check_results.py`, `lib/why.test.ts`, `app/core/progress` 자체 점검.
```

- [x] **Step 2: changelog 한 줄** — `docs/recommender/changelog.md` 맨 위 항목(기존 항목 형식대로, 사용자 언어): "결과 페이지가 계산 단계(후보 검색 → 참가 자격 → 순서 매기기)를 실제 진행대로 보여 준다. 숫자는 그 요청에서 실제로 센 값이다."

- [x] **Step 3: 체크박스·커밋·푸시**

```bash
cd C:/Dev/personal/jodalfit && git add docs/design/README.md docs/recommender/changelog.md docs/superpowers/plans/2026-10-23-renewal-05-results.md && git commit -m "docs(design): 구현 05 results 기록" && git push origin renewal
```

---

## 자체 검토

- **시안 ↔ 태스크**: 머리(이름 32·마스킹·다른 회사·☆) → T7. 장면(라벨 넷·캔버스·탈락 이유·접힘·건너뛰기·reduced-motion) → T5. 걸러낸 경로·종류 탭·마감 요약(0건 숨김) → T6 FunnelLine. 두 단 판(240px sticky 왼쪽·표) → T6·T7. 표 행(번호·제목·기관·근거 칩·D-day hot·추정가·펼침 자격 3줄·근거·원문·검토) → T3 why + T6 ResultRows(01 Sheet). 게이트 5건 뒤·흐림 7 → T6. 네 상태 → T7(+T6 ZeroBlock). 390 → 각 부품 `max-sm:` + T9. 인쇄 → T8. 금지어·주황 선 → T9.
- **마스터**: §3.4 stage 이벤트(T2), §3.5 문구·마스킹·지역 `rgnBase`·점수 비노출, §3.6 Playwright + node --test.
- **타입 일관**: `SceneCounts`(Scene) ↔ ResultsView/FunnelLine. `StreamEvent`(types) ↔ stream.ts ↔ ResultsView 분기. `QualLine`(Sheet) ↔ why.ts ↔ SheetExpand. `CompanySideData`(route) ↔ CompanySide. `ReviewButton(no, ord, via, why, reviewed, loggedIn, onChange)` 03 그대로. `Gate(rest, next)` 01 그대로. `companyStats`·`strongestWhy` 03 그대로. `createEngine(canvas, labels, reasons, counts)` T5 두 곳.
- **06·07 이 이어받는 접점**: `FunnelLine`·`CompanySide`·`ResultRows`·`SearchBox`·`lib/why.ts`. 회사 페이지(06)는 `ResultRows` 를 비스트림 캐시 데이터로 그린다(장면 없음). 공고 상세(07)는 `qualLines` 문구와 세 상태 표기를 공유.
- **알려진 빈 곳(의도)**: 종류 탭 클릭 전환, 하이브리드 `keywords` 입력 UI(URL 로만), 설명/총평, 장면 공고명.

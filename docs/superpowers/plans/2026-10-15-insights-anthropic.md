# 첨부문서 인사이트 모델 전환 (gpt-4o-mini → claude-haiku-4-5) 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** `jobs/summarize_bid_documents.py` 가 Anthropic Message Batches 로 Haiku 4.5 를 호출하게 한다. 근거: 40건 표본 비교에서 Haiku 37승 3패, 필수조건 누락 116→32 (`docs/recommender/exp-2026-10-15-insights-model.md`, 작성 예정).

**Architecture:** 프롬프트·스키마는 그대로. `notice_insights.py` 에 Anthropic 요청 빌더 추가(tool_use 로 스키마 강제). 잡은 설정 `INSIGHT_PROVIDER`(기본 anthropic)로 제출 경로를 고르고, 수거는 placeholder prefix 로 두 공급자를 모두 처리한다(`batch:` = OpenAI 잔여분 drain, `abatch:` = Anthropic). 결과 행의 `model` 컬럼에 실제 모델명을 기록한다.

---

### Task 1: Anthropic 클라이언트 + 요청 빌더 + 잡 전환

**Files:**
- Modify: `backend/app/core/config.py` — 필드 2개
- Create: `backend/app/services/anthropic_client.py`
- Modify: `backend/app/services/notice_insights.py` — `ANTHROPIC_MODEL`, `anthropic_request()`
- Modify: `backend/jobs/summarize_bid_documents.py` — submit/collect 분기
- Modify: `README.md` §9 (환경변수 표 1행), `CLAUDE.md` 스택 줄

- [ ] **Step 1: config**

`Settings` 에 추가 (sentry_dsn 아래):
```python
    # Anthropic — 첨부문서 인사이트(Haiku). 비우면 openai 로 degrade 하지 않고 잡이 명시적으로 실패한다.
    anthropic_api_key: str | None = None
    # 첨부문서 인사이트 공급자. anthropic(Haiku 4.5, 2026-10-15 비교 37:3) / openai(gpt-4o-mini, 롤백용)
    insight_provider: Literal["openai", "anthropic"] = "anthropic"
```

- [ ] **Step 2: anthropic_client.py**

```python
"""Anthropic 클라이언트 — 첨부문서 인사이트(summarize_bid_documents). 임베딩은 계속 OpenAI."""
from functools import lru_cache

import anthropic

from app.core.config import get_settings


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다 (backend/.env)")
    return anthropic.Anthropic(api_key=key)
```

- [ ] **Step 3: notice_insights.py**

`MODEL = "gpt-4o-mini"` 아래에:
```python
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_MAX_TOKENS = 1500  # 표본 40건 출력 평균 861 토큰
```
`chat_request` 아래에:
```python
def anthropic_request(notice_name: str, input_text: str) -> dict:
    """Message Batches 의 `params` — 같은 SYSTEM/SCHEMA, tool_use 로 구조화 강제."""
    return {
        "model": ANTHROPIC_MODEL,
        "max_tokens": ANTHROPIC_MAX_TOKENS,
        "system": SYSTEM,
        "tools": [{"name": "bid_notice_insight", "description": "입찰 문서 구조화 결과", "input_schema": SCHEMA["schema"]}],
        "tool_choice": {"type": "tool", "name": "bid_notice_insight"},
        "messages": [{"role": "user", "content": f"[공고명] {notice_name}\n\n{input_text}"}],
    }
```
(`temperature` 는 넣지 않는다 — SDK 1.14 Messages.create 가 받지 않는다.)

- [ ] **Step 4: summarize_bid_documents.py**

상단 import 에 `from app.core.config import get_settings`, `from app.services.anthropic_client import get_anthropic_client`, `from app.services.notice_insights import ANTHROPIC_MODEL, anthropic_request` 추가. 상수에 `A_PENDING_PREFIX = "abatch:"` 추가.

`_build_line` 을 공급자 무관하게 바꾼다 — 반환을 `(custom_id, notice_name, text, seqs)` 로:
```python
def _build_line(sb, no: str, ord_: str) -> tuple[str, str, str, list[int]] | None:
    """공고 하나 → (custom_id, 공고명, 입력 텍스트, source_seqs). 쓸 만한 텍스트가 없으면 None."""
    docs = ...(기존 그대로)
    notice = ...(기존 그대로)
    text, seqs = build_input(docs)
    if not text:
        return None
    return f"{no}_{ord_}", notice["bid_ntce_nm"], text, seqs
```
custom_id 는 `no_ord` (Anthropic 은 `[A-Za-z0-9_-]{1,64}` 만 허용, `|` 불가). 파싱은 `rsplit("_", 1)`.

`submit` 을 두 경로로:
```python
def submit(sb, limit: int) -> tuple[str | None, int]:
    provider = get_settings().insight_provider
    targets = ...(기존 rpc_next)
    built = [b for t in targets if (b := _build_line(sb, t["bid_ntce_no"], t["bid_ntce_ord"]))]
    if not built:
        return None, 0
    placeholders = [{"bid_ntce_no": cid.rsplit("_", 1)[0], "bid_ntce_ord": cid.rsplit("_", 1)[1], "summary": None, "source_seqs": seqs, "input_chars": len(text)}
                    for cid, _, text, seqs in built]
    if provider == "anthropic":
        client = get_anthropic_client()
        batch = client.messages.batches.create(requests=[{"custom_id": cid, "params": anthropic_request(name, text)} for cid, name, text, _ in built])
        prefix, cancel = A_PENDING_PREFIX, lambda: client.messages.batches.cancel(batch.id)
    else:
        client = get_openai_client()
        lines = [{"custom_id": cid, "method": "POST", "url": "/v1/chat/completions", "body": chat_request(name, text)} for cid, name, text, _ in built]
        jsonl = "\n".join(json.dumps(line, ensure_ascii=False) for line in lines).encode("utf-8")
        f = client.files.create(file=(f"{JOB_NAME}.jsonl", jsonl), purpose="batch")
        batch = client.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions", completion_window="24h", metadata={"job": JOB_NAME})
        prefix, cancel = PENDING_PREFIX, lambda: client.batches.cancel(batch.id)
    for p in placeholders:
        p["model"] = prefix + batch.id
    try:
        _db("upsert_placeholders", lambda: upsert_rows(TABLE, placeholders, on_conflict="bid_ntce_no,bid_ntce_ord"))
    except Exception:
        cancel()
        raise
    return batch.id, len(built)
```

`_ingest_output` 의 custom_id 파싱을 `no, ord_ = rec["custom_id"].rsplit("_", 1)` 로 바꾸되, 옛 OpenAI 배치(`|`)도 drain 되도록 `sep = "|" if "|" in rec["custom_id"] else "_"` 로 분기. (`"model": MODEL` 유지.)

Anthropic 수거 함수 추가:
```python
def _ingest_anthropic(sb, client, batch_id: str) -> tuple[int, int]:
    """ended 된 Anthropic 배치 결과 → 인사이트 upsert. (ok, failed)"""
    rows: list[dict] = []
    failed = 0
    for item in client.messages.batches.results(batch_id):
        no, ord_ = item.custom_id.rsplit("_", 1)
        try:
            if item.result.type != "succeeded":
                raise ValueError(f"result {item.result.type}")
            tool = next(b for b in item.result.message.content if b.type == "tool_use")
            ins = tool.input
            rows.append({"bid_ntce_no": no, "bid_ntce_ord": ord_, "summary": ins["summary"], "scope": ins["scope"],
                         "requirements": ins["requirements"], "evaluation": ins["evaluation"], "schedule": ins["schedule"],
                         "keywords": ins["keywords"], "model": ANTHROPIC_MODEL})
        except Exception as e:  # 한 건 때문에 배치 전체를 버리지 않는다
            failed += 1
            print(f"  ! {no} failed: {type(e).__name__}: {str(e)[:120]}")
    for i in range(0, len(rows), 200):
        chunk = rows[i:i + 200]
        _db("upsert_insights", lambda: upsert_rows(TABLE, chunk, on_conflict="bid_ntce_no,bid_ntce_ord"))
    return len(rows), failed
```

`collect(sb)` 가 두 prefix 를 모두 처리:
```python
def collect(sb) -> tuple[int, int, int]:
    pending = _db("select_pending", lambda: (
        sb.table(TABLE).select("model").is_("summary", "null").like("model", "%batch:%").limit(5000).execute().data or []
    ))
    ok = failed = running = 0
    for model_tag in sorted({r["model"] for r in pending}):
        if model_tag.startswith(A_PENDING_PREFIX):
            client = get_anthropic_client(); bid = model_tag[len(A_PENDING_PREFIX):]
            batch = client.messages.batches.retrieve(bid)
            if batch.processing_status != "ended":
                running += 1; c = batch.request_counts
                print(f"  abatch {bid} {batch.processing_status}: {c.succeeded}/{c.processing + c.succeeded + c.errored + c.canceled + c.expired}")
                continue
            n_ok, n_fail = _ingest_anthropic(sb, client, bid)
        elif model_tag.startswith(PENDING_PREFIX):
            client = get_openai_client(); bid = model_tag[len(PENDING_PREFIX):]
            batch = client.batches.retrieve(bid)
            if batch.status in _RUNNING:
                running += 1; print(f"  batch {bid} {batch.status}: {batch.request_counts.completed}/{batch.request_counts.total}"); continue
            n_ok, n_fail = _ingest_output(sb, client, batch)
            for fid in (batch.input_file_id, batch.output_file_id, batch.error_file_id):
                if fid:
                    try: client.files.delete(fid)
                    except Exception: pass
        else:
            continue
        leftover = _db("delete_leftover", lambda: sb.table(TABLE).delete().eq("model", model_tag).is_("summary", "null").execute().data or [])
        n_fail += len(leftover)
        print(f"  {model_tag} done: ok={n_ok} failed={n_fail}")
        ok += n_ok; failed += n_fail
    return ok, failed, running
```
`run()` 은 `collect(sb)` / `submit(sb, limit)` 호출로 맞추고 `client = get_openai_client()` 줄 제거. 모듈 docstring 의 모델·비용 줄을 "Haiku 4.5 Message Batch(50% 할인), 공고당 입력 ≈1.3만 토큰 → 약 12원; `INSIGHT_PROVIDER=openai` 로 롤백" 으로 갱신.

- [ ] **Step 5: 문서**

README §9 표에 `ANTHROPIC_API_KEY` | (비움) | 첨부문서 인사이트(Haiku) 와 `INSIGHT_PROVIDER` | `anthropic` | 인사이트 공급자, openai 로 롤백. CLAUDE.md 스택 줄 `LLM 설명: gpt-4o-mini` 뒤에 ` / 첨부문서 인사이트: claude-haiku-4-5 (Message Batches)` 추가.

- [ ] **Step 6: 검증 (실제 API, 소량)**

```bash
cd backend && uv run python -m jobs.summarize_bid_documents --limit 3
```
Expected: `submitted 3 notices as msgbatch_...`, DB 에 placeholder 3행(model = `abatch:msgbatch_...`). 몇 분 뒤 `--limit 0` 재실행 → `abatch ... done: ok=3 failed=0`, 행의 model = `claude-haiku-4-5-20251001`, summary 채워짐. (처리 중이면 `abatch ... in_progress` 출력 후 종료 — 정상.)
또 `INSIGHT_PROVIDER=openai uv run python -m jobs.summarize_bid_documents --limit 0` 이 에러 없이 수거만 도는지(기존 OpenAI 잔여 배치 drain) 확인.

- [ ] **Step 7: 커밋**
```bash
git add backend/app/core/config.py backend/app/services/anthropic_client.py backend/app/services/notice_insights.py backend/jobs/summarize_bid_documents.py backend/pyproject.toml backend/uv.lock README.md CLAUDE.md
git -c core.safecrlf=false commit -m "feat(insights): 첨부문서 인사이트를 Haiku 4.5 Message Batches 로 전환 (40건 비교 37:3, 누락 116→32) — INSIGHT_PROVIDER 로 롤백"
```
Co-Authored-By 줄 포함. push 는 컨트롤러가.

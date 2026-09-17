"""첨부문서 텍스트 → LLM 구조화 인사이트 → bid_notice_insights 저장 잡 (OpenAI Batch API).

대상: 추출 성공 문서가 있고 인사이트 없는 **진행 중** 공고, 수의계약 제외
(RPC next_bid_notices_for_insights, 0023 → 0029). 수의계약은 요약 모집단의 43%인데
추천 TOP 5 노출은 4%라 뺐다 (2026-09 실측).
인사이트는 추천 설명 프롬프트와 공고 상세 UI에만 쓴다 — 공고 임베딩 텍스트에 섞지 않는다
(요약을 섞으면 벡터가 평균화돼 짧은 질의와의 코사인이 떨어짐: 실측 0.504 → 0.462).

동작 (한 번 실행 = 수거 → 제출):
  1. collect — 진행 중 배치를 조회해 완료된 것의 결과를 bid_notice_insights에 채운다.
     실패·만료 배치는 placeholder를 지워 다음 제출에서 다시 잡히게 한다.
  2. submit  — 대기 공고 최대 --limit건(≤500)을 JSONL 한 파일로 묶어 배치 1개를 제출하고,
     placeholder 행(summary null, model='batch:<id>')을 넣어 중복 제출을 막는다.
  결과는 보통 수십 분~수 시간 뒤(최대 24h) 도착하고 다음 실행의 collect가 가져간다.
  UI·추천 설명은 summary null인 행을 없는 것으로 취급한다.

비용: gpt-4o-mini Batch(정가의 50%), 공고당 입력 ≤12k자(≈8k 토큰) → 공고당 약 1원.

실행:
    cd backend
    uv run python -m jobs.summarize_bid_documents --limit 100   # 수거 + 최대 100건 제출
    uv run python -m jobs.summarize_bid_documents --limit 0     # 수거만
"""

from __future__ import annotations

import argparse
import json
import time

from postgrest.exceptions import APIError

from app.services.notice_insights import MODEL, build_input, chat_request
from app.services.openai_client import get_openai_client
from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "summarize_bid_documents"
TABLE = "bid_notice_insights"
MAX_SUBMIT = 500  # 배치 1개 = RPC 1회 (PostgREST 1,000행 상한 아래)
STATEMENT_TIMEOUT = "57014"
PENDING_PREFIX = "batch:"  # placeholder 행의 model 값: 'batch:<openai batch id>'
_RUNNING = ("validating", "in_progress", "finalizing", "cancelling")


def _db(step: str, fn, retries: int = 3):
    """Supabase 호출 — statement timeout(57014)이면 backoff 재시도. 실패 단계명을 에러에 남긴다."""
    for attempt in range(retries):
        try:
            return fn()
        except APIError as e:
            if e.code != STATEMENT_TIMEOUT or attempt == retries - 1:
                raise RuntimeError(f"[{step}] {e.code}: {e.message}") from e
            wait = 3 * (attempt + 1)
            print(f"  {step}: statement timeout, retry in {wait}s")
            time.sleep(wait)


def _build_line(sb, no: str, ord_: str) -> tuple[dict, dict] | None:
    """공고 하나 → (JSONL 한 줄, placeholder 행). 쓸 만한 텍스트가 없으면 None."""
    docs = _db("select_docs", lambda: (
        sb.table("bid_notice_documents")
        .select("seq,file_name,text")
        .eq("bid_ntce_no", no).eq("bid_ntce_ord", ord_).eq("status", "ok")
        .execute().data or []
    ))
    notice = _db("select_notice", lambda: (
        sb.table("bid_notices").select("bid_ntce_nm")
        .eq("bid_ntce_no", no).eq("bid_ntce_ord", ord_).single().execute().data
    ))
    text, seqs = build_input(docs)
    if not text:
        return None
    line = {
        "custom_id": f"{no}|{ord_}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": chat_request(notice["bid_ntce_nm"], text),
    }
    placeholder = {
        "bid_ntce_no": no, "bid_ntce_ord": ord_,
        "summary": None, "source_seqs": seqs, "input_chars": len(text),
    }
    return line, placeholder


def submit(sb, client, limit: int) -> tuple[str | None, int]:
    """대기 공고를 배치 1개로 제출. (batch_id, 제출 건수)"""
    targets = _db("rpc_next", lambda: (
        sb.rpc("next_bid_notices_for_insights", {"p_limit": min(limit, MAX_SUBMIT)}).execute().data or []
    ))
    lines: list[dict] = []
    placeholders: list[dict] = []
    for t in targets:
        built = _build_line(sb, t["bid_ntce_no"], t["bid_ntce_ord"])
        if built:
            lines.append(built[0])
            placeholders.append(built[1])
    if not lines:
        return None, 0

    jsonl = "\n".join(json.dumps(line, ensure_ascii=False) for line in lines).encode("utf-8")
    f = client.files.create(file=(f"{JOB_NAME}.jsonl", jsonl), purpose="batch")
    batch = client.batches.create(
        input_file_id=f.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"job": JOB_NAME},
    )
    for p in placeholders:
        p["model"] = PENDING_PREFIX + batch.id
    try:
        _db("upsert_placeholders", lambda: upsert_rows(
            TABLE, placeholders, on_conflict="bid_ntce_no,bid_ntce_ord",
        ))
    except Exception:
        # placeholder 없이 배치만 돌면 결과를 수거할 길이 없다 — 취소하고 다음 실행에 다시 제출
        client.batches.cancel(batch.id)
        raise
    return batch.id, len(lines)


def _ingest_output(sb, client, batch) -> tuple[int, int]:
    """완료(또는 부분 완료)된 배치의 output 파일을 읽어 인사이트 upsert. (ok, failed)"""
    if not batch.output_file_id:
        return 0, 0
    content = client.files.content(batch.output_file_id).text
    rows: list[dict] = []
    failed = 0
    for raw in content.splitlines():
        if not raw.strip():
            continue
        rec = json.loads(raw)
        no, ord_ = rec["custom_id"].split("|", 1)
        resp = rec.get("response") or {}
        try:
            if resp.get("status_code") != 200:
                raise ValueError(f"status {resp.get('status_code')}")
            ins = json.loads(resp["body"]["choices"][0]["message"]["content"])
            rows.append({
                "bid_ntce_no": no, "bid_ntce_ord": ord_,
                "summary": ins["summary"], "scope": ins["scope"],
                "requirements": ins["requirements"], "evaluation": ins["evaluation"],
                "schedule": ins["schedule"], "keywords": ins["keywords"],
                "model": MODEL,
            })
        except Exception as e:  # 한 건 때문에 배치 전체를 버리지 않는다
            failed += 1
            print(f"  ! {no} failed: {type(e).__name__}: {str(e)[:120]}")
    for i in range(0, len(rows), 200):
        chunk = rows[i:i + 200]
        _db("upsert_insights", lambda: upsert_rows(TABLE, chunk, on_conflict="bid_ntce_no,bid_ntce_ord"))
    return len(rows), failed


def collect(sb, client) -> tuple[int, int, int]:
    """진행 중 배치 수거. (ok, failed, 아직 진행 중인 배치 수)"""
    pending = _db("select_pending", lambda: (
        sb.table(TABLE).select("model")
        .is_("summary", "null").like("model", PENDING_PREFIX + "%")
        .limit(5000).execute().data or []
    ))
    batch_ids = sorted({r["model"][len(PENDING_PREFIX):] for r in pending})
    ok = failed = running = 0
    for bid in batch_ids:
        batch = client.batches.retrieve(bid)
        if batch.status in _RUNNING:
            running += 1
            print(f"  batch {bid} {batch.status}: {batch.request_counts.completed}/{batch.request_counts.total}")
            continue
        n_ok, n_fail = _ingest_output(sb, client, batch)
        # 결과를 못 받은 placeholder(에러 라인·만료·실패)는 지워서 다음 제출에 다시 잡히게 한다
        leftover = _db("delete_leftover", lambda: (
            sb.table(TABLE).delete()
            .eq("model", PENDING_PREFIX + bid).is_("summary", "null")
            .execute().data or []
        ))
        n_fail += len(leftover)
        print(f"  batch {bid} {batch.status}: ok={n_ok} failed={n_fail}")
        ok += n_ok
        failed += n_fail
        for fid in (batch.input_file_id, batch.output_file_id, batch.error_file_id):
            if fid:
                try:
                    client.files.delete(fid)
                except Exception:
                    pass
    return ok, failed, running


def run(limit: int = 100) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    sb = get_admin_client()
    client = get_openai_client()
    ok = failed = 0
    try:
        ok, failed, running = collect(sb, client)
        print(f"[{JOB_NAME}] collected ok={ok} failed={failed} running_batches={running}")
        if limit > 0:
            batch_id, n = submit(sb, client, limit)
            print(f"[{JOB_NAME}] submitted {n} notices" + (f" as {batch_id}" if batch_id else ""))
        log_ingest_finish(run_id, "success", rows_inserted=ok, rows_failed=failed)
        print(f"[{JOB_NAME}] done. ok={ok} failed={failed}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=ok, rows_failed=failed, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="이번 실행에서 제출할 공고 수 (0=수거만, 최대 500)")
    args = parser.parse_args()
    run(args.limit)

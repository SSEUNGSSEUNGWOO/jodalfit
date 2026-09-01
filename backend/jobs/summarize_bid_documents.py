"""첨부문서 텍스트 → LLM 구조화 인사이트 → bid_notice_insights 저장 잡.

대상: 추출 성공 문서가 있고 인사이트 없는 **진행 중** 공고 (RPC next_bid_notices_for_insights, 0022).
인사이트는 추천 설명 프롬프트와 공고 상세 UI에만 쓴다 — 공고 임베딩 텍스트에 섞지 않는다
(요약을 섞으면 벡터가 평균화돼 짧은 질의와의 코사인이 떨어짐: 실측 0.504 → 0.462).

비용: gpt-4o-mini, 공고당 입력 ≤12k자(≈8k 토큰) → 공고당 약 2원. 시간별 100건 기준 하루 2,400건 ≈ 5천 원.

실행:
    cd backend
    uv run python -m jobs.summarize_bid_documents --limit 100
"""

from __future__ import annotations

import argparse
import time

from postgrest.exceptions import APIError

from app.services.notice_insights import MODEL, build_input, summarize
from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "summarize_bid_documents"
RPC_BATCH = 500  # PostgREST 1,000행 상한 아래
STATEMENT_TIMEOUT = "57014"


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


def _process(sb, no: str, ord_: str) -> bool:
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
        return False
    ins = summarize(notice["bid_ntce_nm"], text)
    _db("upsert_insight", lambda: upsert_rows(
        "bid_notice_insights",
        [{
            "bid_ntce_no": no, "bid_ntce_ord": ord_,
            "summary": ins["summary"], "scope": ins["scope"],
            "requirements": ins["requirements"], "evaluation": ins["evaluation"],
            "keywords": ins["keywords"], "source_seqs": seqs,
            "input_chars": len(text), "model": MODEL,
        }],
        on_conflict="bid_ntce_no,bid_ntce_ord",
    ))
    return True


def run(limit: int = 100) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    sb = get_admin_client()
    print(f"[{JOB_NAME}] up to {limit} notices")

    done = 0
    failed = 0
    seen = 0
    try:
        while seen < limit:
            batch = min(RPC_BATCH, limit - seen)
            targets = _db("rpc_next", lambda: (
                sb.rpc("next_bid_notices_for_insights", {"p_limit": batch}).execute().data or []
            ))
            if not targets:
                break
            for t in targets:
                seen += 1
                no, ord_ = t["bid_ntce_no"], t["bid_ntce_ord"]
                try:
                    if _process(sb, no, ord_):
                        done += 1
                except Exception as e:  # LLM/DB 실패 — 공고 하나 때문에 잡이 죽지 않게
                    failed += 1
                    print(f"  ! {no} failed: {type(e).__name__}: {str(e)[:160]}")
                    if "no credits" in str(e).lower():
                        # OpenAI 잔액 소진 — 나머지도 전부 실패하므로 즉시 중단 (충전 후 재실행하면 이어서 처리됨).
                        # RuntimeError라야 바깥 except에서 ingest_runs가 failed로 기록됨 (SystemExit는 통과해 running으로 남음)
                        raise RuntimeError(f"OpenAI credits exhausted — stopped (ok={done}, failed={failed})")
                    time.sleep(2)
                if seen % 20 == 0:
                    print(f"  {seen} (ok={done}, failed={failed})")
            # 실패한 공고는 인사이트가 없어 다음 RPC에 다시 잡힘 → 전부 실패면 무한루프 방지
            if failed and done == 0 and failed >= batch:
                break

        log_ingest_finish(run_id, "success", rows_inserted=done, rows_failed=failed)
        print(f"[{JOB_NAME}] done. ok={done} failed={failed}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=done, rows_failed=failed, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="처리할 공고 수")
    args = parser.parse_args()
    run(args.limit)

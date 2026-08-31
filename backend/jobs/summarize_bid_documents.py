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

from app.services.notice_insights import MODEL, build_input, summarize
from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "summarize_bid_documents"


def run(limit: int = 100) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    sb = get_admin_client()
    targets = sb.rpc("next_bid_notices_for_insights", {"p_limit": limit}).execute().data or []
    print(f"[{JOB_NAME}] {len(targets)} notices to summarize")

    done = 0
    failed = 0
    try:
        for i, t in enumerate(targets, 1):
            no, ord_ = t["bid_ntce_no"], t["bid_ntce_ord"]
            docs = (
                sb.table("bid_notice_documents")
                .select("seq,file_name,text")
                .eq("bid_ntce_no", no).eq("bid_ntce_ord", ord_).eq("status", "ok")
                .execute().data or []
            )
            notice = (
                sb.table("bid_notices").select("bid_ntce_nm")
                .eq("bid_ntce_no", no).eq("bid_ntce_ord", ord_).single().execute().data
            )
            text, seqs = build_input(docs)
            if not text:
                continue
            try:
                ins = summarize(notice["bid_ntce_nm"], text)
            except Exception as e:
                failed += 1
                print(f"  ! {no} failed: {type(e).__name__}: {e}")
                time.sleep(2)
                continue
            upsert_rows(
                "bid_notice_insights",
                [{
                    "bid_ntce_no": no, "bid_ntce_ord": ord_,
                    "summary": ins["summary"], "scope": ins["scope"],
                    "requirements": ins["requirements"], "evaluation": ins["evaluation"],
                    "keywords": ins["keywords"], "source_seqs": seqs,
                    "input_chars": len(text), "model": MODEL,
                }],
                on_conflict="bid_ntce_no,bid_ntce_ord",
            )
            done += 1
            if i % 20 == 0:
                print(f"  {i}/{len(targets)} (ok={done}, failed={failed})")

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

"""입찰공고 임베딩 생성.

입력 텍스트 = 공고명 + 업무구분 + 참가가능업종 + 수요기관 (필드명 prefix 포함)
대상: bid_notices.embedded_at IS NULL

실행:
    cd backend
    uv run python -m jobs.embed_bid_notices --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "embed_bid_notices"


def build_text(r: dict) -> str:
    parts = []
    if r.get("bid_ntce_nm"):
        parts.append(f"공고명: {r['bid_ntce_nm']}")
    if r.get("bsns_div_nm"):
        parts.append(f"업무구분: {r['bsns_div_nm']}")
    if r.get("bidprc_psbl_indstryty_nm"):
        parts.append(f"참가가능업종: {r['bidprc_psbl_indstryty_nm']}")
    if r.get("dmnd_instt_nm"):
        parts.append(f"수요기관: {r['dmnd_instt_nm']}")
    return "\n".join(parts)


def fetch_pending(client, batch: int) -> list[dict]:
    return (
        client.table("bid_notices")
        .select("bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bidprc_psbl_indstryty_nm,dmnd_instt_nm")
        .is_("embedded_at", "null")
        .limit(batch)
        .execute()
        .data
    )


def run(limit: int = 5000, batch: int = 200) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch})
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = fetch_pending(client, min(batch, limit - total))
            if not rows:
                break
            texts = [build_text(r) for r in rows]
            embeddings = embed_texts(texts)
            now_iso = datetime.now().isoformat()
            updates = [
                {
                    "bid_ntce_no": r["bid_ntce_no"],
                    "bid_ntce_ord": r["bid_ntce_ord"],
                    "embedding": vector_to_pgvector_str(e),
                    "embedded_at": now_iso,
                }
                for r, e in zip(rows, embeddings)
            ]
            client.table("bid_notices").upsert(
                updates, on_conflict="bid_ntce_no,bid_ntce_ord"
            ).execute()
            total += len(rows)
            print(f"  embedded {total}")
        log_ingest_finish(run_id, "success", rows_updated=total)
        print(f"[{JOB_NAME}] done. {total} rows embedded")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--batch", type=int, default=200)
    args = parser.parse_args()
    run(args.limit, args.batch)

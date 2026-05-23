"""발주계획 임베딩 생성.

입력 텍스트 = 사업명 + 업무구분 + 용도 + 사양 + 발주기관

실행:
    cd backend
    uv run python -m jobs.embed_order_plans --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "embed_order_plans"


def build_text(r: dict) -> str:
    parts = []
    if r.get("biz_nm"):
        parts.append(f"사업명: {r['biz_nm']}")
    if r.get("bsns_div_nm"):
        parts.append(f"업무구분: {r['bsns_div_nm']}")
    if r.get("usg_cntnts"):
        parts.append(f"용도: {r['usg_cntnts']}")
    if r.get("spec_cntnts"):
        parts.append(f"사양: {r['spec_cntnts']}")
    if r.get("order_instt_nm"):
        parts.append(f"발주기관: {r['order_instt_nm']}")
    return "\n".join(parts)


def run(limit: int = 5000, batch: int = 200) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch})
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = (
                client.table("order_plans")
                .select("order_plan_unty_no,biz_nm,bsns_div_nm,usg_cntnts,spec_cntnts,order_instt_nm")
                .is_("embedded_at", "null")
                .limit(min(batch, limit - total))
                .execute()
                .data
            )
            if not rows:
                break
            texts = [build_text(r) for r in rows]
            embeddings = embed_texts(texts)
            now_iso = datetime.now().isoformat()
            updates = [
                {
                    "order_plan_unty_no": r["order_plan_unty_no"],
                    "embedding": vector_to_pgvector_str(e),
                    "embedded_at": now_iso,
                }
                for r, e in zip(rows, embeddings)
            ]
            client.table("order_plans").upsert(updates, on_conflict="order_plan_unty_no").execute()
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

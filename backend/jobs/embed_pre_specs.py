"""사전규격 임베딩 생성.

입력 텍스트 = 사업명 + 업무구분 + 세부품목 + 수요기관

실행:
    cd backend
    uv run python -m jobs.embed_pre_specs --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "embed_pre_specs"


def build_text(r: dict) -> str:
    parts = []
    if r.get("prdct_clsfc_no_nm"):
        parts.append(f"사업명: {r['prdct_clsfc_no_nm']}")
    if r.get("bsns_div_nm"):
        parts.append(f"업무구분: {r['bsns_div_nm']}")
    if r.get("prdct_dtl_list"):
        parts.append(f"세부품목: {r['prdct_dtl_list']}")
    if r.get("rl_dminstt_nm"):
        parts.append(f"수요기관: {r['rl_dminstt_nm']}")
    return "\n".join(parts)


def run(limit: int = 5000, batch: int = 200) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch})
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = (
                client.table("pre_specs")
                .select("bf_spec_rgst_no,prdct_clsfc_no_nm,bsns_div_nm,prdct_dtl_list,rl_dminstt_nm")
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
                    "bf_spec_rgst_no": r["bf_spec_rgst_no"],
                    "embedding": vector_to_pgvector_str(e),
                    "embedded_at": now_iso,
                }
                for r, e in zip(rows, embeddings)
            ]
            client.rpc("update_pre_specs_embeddings", {"updates": updates}).execute()
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

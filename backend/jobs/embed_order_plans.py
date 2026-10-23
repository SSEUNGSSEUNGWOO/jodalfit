"""발주계획 임베딩 생성.

입력 텍스트 = 사업명 + 업무구분 + 용도 + 사양 + 발주기관

공간(--space)에 따라 대상 조건·쓰는 컬럼·RPC 가 바뀐다 (0045/0046). 기본값은 settings.embed_space.

실행:
    cd backend
    uv run python -m jobs.embed_order_plans --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.core.config import get_settings
from app.services.embedding import embed_texts
from app.services.openai_client import vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import (
    log_ingest_finish,
    log_ingest_start,
    upsert_embeddings_with_retry,
)

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


def pending_query(client, space: str, select: str, count: str | None = None):
    # 공고 예정일이 늦은 것부터 — 발주계획은 '앞으로 나올 공고'라 최근 것이 쓸모 있다.
    # embed_pre_specs 와 같은 이유(2026-10-23): 정렬이 없으면 적재 순서대로 집어가 오래된 것만 채운다.
    q = client.table("order_plans").select(select, count=count)
    q = q.is_("embedding_k", "null") if space == "kure" else q.is_("embedded_at", "null")
    return q.order("ntice_dt", desc=True, nullsfirst=False)


def run(
    limit: int = 5000, batch: int = 200, space: str | None = None, dry_run: bool = False
) -> None:
    space = space or get_settings().embed_space
    rpc = "update_order_plans_embeddings_k" if space == "kure" else "update_order_plans_embeddings"
    if dry_run:
        res = pending_query(get_admin_client(), space, "order_plan_unty_no", count="exact").limit(1).execute()
        print(f"[{JOB_NAME}] dry-run space={space} rpc={rpc} 대상={res.count:,} 첫행={res.data}")
        return
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch, "space": space})
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = (
                pending_query(client, space, "order_plan_unty_no,biz_nm,bsns_div_nm,usg_cntnts,spec_cntnts,order_instt_nm")
                .limit(min(batch, limit - total))
                .execute()
                .data
            )
            if not rows:
                break
            texts = [build_text(r) for r in rows]
            embeddings = embed_texts(texts, space)
            now_iso = datetime.now(timezone.utc).isoformat()  # tz 없는 지역시각을 쓰면 Postgres 가 UTC 로 해석해 KST PC 에서 9시간 밀린다
            updates = [
                {
                    "order_plan_unty_no": r["order_plan_unty_no"],
                    "embedding": vector_to_pgvector_str(e),
                    "embedded_at": now_iso,
                }
                for r, e in zip(rows, embeddings)
            ]
            upsert_embeddings_with_retry(client, rpc, updates)
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
    parser.add_argument("--space", choices=["openai", "kure"], default=None)
    parser.add_argument("--dry-run", action="store_true", help="대상 건수만 출력, 쓰기 없음")
    args = parser.parse_args()
    run(args.limit, args.batch, args.space, args.dry_run)

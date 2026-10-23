"""사전규격 임베딩 생성.

입력 텍스트 = 사업명 + 업무구분 + 세부품목 + 수요기관

공간(--space)에 따라 대상 조건·쓰는 컬럼·RPC 가 바뀐다 (0045/0046). 기본값은 settings.embed_space.

실행:
    cd backend
    uv run python -m jobs.embed_pre_specs --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime

from app.core.config import get_settings
from app.services.embedding import embed_texts
from app.services.openai_client import vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import (
    log_ingest_finish,
    log_ingest_start,
    upsert_embeddings_with_retry,
)

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


def pending_query(client, space: str, select: str, count: str | None = None):
    # 의견 마감이 늦은 것부터 — 아직 접수 중인(= 추천에 쓸 수 있는) 사전규격이 먼저 처리돼야 한다.
    # 정렬이 없던 동안 적재 순서대로(사실상 옛날 것부터) 집어갔다. 2026-10-23 확인: 접수 중 2,549건 중
    # 벡터가 있는 건 20건(0.8%)뿐이었고, 밀린 54,943건을 하루 1,000건으로 소화하면 55일 — 평균 공개
    # 기간 6.2일인 사전규격은 영원히 못 따라잡는다. 입찰공고 쪽은 마감 조건이 있어 같은 문제가 없었다.
    q = client.table("pre_specs").select(select, count=count)
    q = q.is_("embedding_k", "null") if space == "kure" else q.is_("embedded_at", "null")
    return q.order("opnin_rgst_clse_dt", desc=True, nullsfirst=False)


def run(
    limit: int = 5000, batch: int = 200, space: str | None = None, dry_run: bool = False
) -> None:
    space = space or get_settings().embed_space
    rpc = "update_pre_specs_embeddings_k" if space == "kure" else "update_pre_specs_embeddings"
    if dry_run:
        res = pending_query(get_admin_client(), space, "bf_spec_rgst_no", count="exact").limit(1).execute()
        print(f"[{JOB_NAME}] dry-run space={space} rpc={rpc} 대상={res.count:,} 첫행={res.data}")
        return
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch, "space": space})
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = (
                pending_query(client, space, "bf_spec_rgst_no,prdct_clsfc_no_nm,bsns_div_nm,prdct_dtl_list,rl_dminstt_nm")
                .limit(min(batch, limit - total))
                .execute()
                .data
            )
            if not rows:
                break
            texts = [build_text(r) for r in rows]
            embeddings = embed_texts(texts, space)
            now_iso = datetime.now().isoformat()
            updates = [
                {
                    "bf_spec_rgst_no": r["bf_spec_rgst_no"],
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

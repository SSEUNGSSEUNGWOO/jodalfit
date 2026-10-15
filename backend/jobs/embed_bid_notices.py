"""입찰공고 임베딩 생성.

입력 텍스트 = 공고명 + 업무구분 + 참가가능업종(PubData) + 품목분류/규격/주공종/용역구분(raw) + 수요기관
회사 벡터의 "등록업종/공급물품" 어휘와 매칭되도록 raw에서 핵심 필드를 추가 추출.

대상:
  기본: embedded_at IS NULL (openai) / embedding_k IS NULL (kure)
  --reembed-all: 모든 행 재임베딩 (작업 시작 시각보다 오래된 임베딩만 재처리)

공간(--space)에 따라 읽는 조건·쓰는 컬럼·RPC 가 바뀐다 (0045/0046). 기본값은 settings.embed_space.

실행:
    cd backend
    uv run python -m jobs.embed_bid_notices --limit 5000
    uv run python -m jobs.embed_bid_notices --space kure --limit 20
    uv run python -m jobs.embed_bid_notices --reembed-all --limit 250000
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

JOB_NAME = "embed_bid_notices"


def build_text(r: dict) -> str:
    raw = r.get("raw") or {}
    parts: list[str] = []

    if r.get("bid_ntce_nm"):
        parts.append(f"공고명: {r['bid_ntce_nm']}")
    if r.get("bsns_div_nm"):
        parts.append(f"업무구분: {r['bsns_div_nm']}")
    if r.get("bidprc_psbl_indstryty_nm"):
        parts.append(f"참가가능업종: {r['bidprc_psbl_indstryty_nm']}")

    # 회사 공급물품 어휘와 직접 매칭되는 핵심 신호
    dtl_prdct = (raw.get("dtilPrdctClsfcNoNm") or "").strip()
    if dtl_prdct:
        parts.append(f"품목분류: {dtl_prdct}")

    # "규격서 참조" 같은 보일러플레이트 텍스트는 노이즈 → 제외
    prdct_spec = (raw.get("prdctSpecNm") or "").strip()
    if prdct_spec and len(prdct_spec) > 3 and "참조" not in prdct_spec:
        parts.append(f"규격: {prdct_spec}")

    main_cnstty = (raw.get("mainCnsttyNm") or "").strip()
    if main_cnstty:
        parts.append(f"주공종: {main_cnstty}")

    srvce_div = (raw.get("srvceDivNm") or "").strip()
    if srvce_div:
        parts.append(f"용역구분: {srvce_div}")

    if r.get("dmnd_instt_nm"):
        parts.append(f"수요기관: {r['dmnd_instt_nm']}")

    return "\n".join(parts)


SELECT_COLS = (
    "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,"
    "bidprc_psbl_indstryty_nm,dmnd_instt_nm,raw"
)


def pending_query(
    client, space: str, reembed_all: bool, job_start: str, select: str, count: str | None = None
):
    at_col = "embedded_k_at" if space == "kure" else "embedded_at"
    q = client.table("bid_notices").select(select, count=count)
    if reembed_all:
        # 이번 사이클 시작 이전 임베딩 + NULL → 한 번씩만 처리됨
        q = q.or_(f"{at_col}.is.null,{at_col}.lt.{job_start}")
    elif space == "kure":
        q = q.is_("embedding_k", "null")
    else:
        q = q.is_("embedded_at", "null")
    return q


def run(
    limit: int = 5000,
    batch: int = 200,
    reembed_all: bool = False,
    space: str | None = None,
    dry_run: bool = False,
) -> None:
    space = space or get_settings().embed_space
    rpc = "update_bid_notice_embeddings_k" if space == "kure" else "update_bid_notice_embeddings"
    job_start = datetime.now().isoformat()
    if dry_run:
        res = (
            pending_query(
                get_admin_client(), space, reembed_all, job_start, "bid_ntce_no", count="exact"
            )
            .limit(1)
            .execute()
        )
        print(f"[{JOB_NAME}] dry-run space={space} rpc={rpc} 대상={res.count:,} 첫행={res.data}")
        return
    run_id = log_ingest_start(
        JOB_NAME,
        {"limit": limit, "batch": batch, "reembed_all": reembed_all, "space": space},
    )
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = (
                pending_query(client, space, reembed_all, job_start, SELECT_COLS)
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
                    "bid_ntce_no": r["bid_ntce_no"],
                    "bid_ntce_ord": r["bid_ntce_ord"],
                    "embedding": vector_to_pgvector_str(e),
                    "embedded_at": now_iso,
                }
                for r, e in zip(rows, embeddings)
            ]
            upsert_embeddings_with_retry(client, rpc, updates)
            total += len(rows)
            print(f"  embedded {total:,}")
        log_ingest_finish(run_id, "success", rows_updated=total)
        print(f"[{JOB_NAME}] done. {total} rows embedded")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--batch", type=int, default=200)
    parser.add_argument(
        "--reembed-all",
        action="store_true",
        help="모든 행 재임베딩 (이번 사이클 시작 이전 임베딩만 대상)",
    )
    parser.add_argument("--space", choices=["openai", "kure"], default=None)
    parser.add_argument("--dry-run", action="store_true", help="대상 건수만 출력, 쓰기 없음")
    args = parser.parse_args()
    run(args.limit, args.batch, args.reembed_all, args.space, args.dry_run)

"""입찰공고 임베딩 생성.

입력 텍스트 = 공고명 + 업무구분 + 참가가능업종(PubData) + 품목분류/규격/주공종/용역구분(raw) + 수요기관
회사 벡터의 "등록업종/공급물품" 어휘와 매칭되도록 raw에서 핵심 필드를 추가 추출.

대상:
  기본: bid_notices.embedded_at IS NULL
  --reembed-all: 모든 행 재임베딩 (작업 시작 시각보다 오래된 임베딩만 재처리)

실행:
    cd backend
    uv run python -m jobs.embed_bid_notices --limit 5000
    uv run python -m jobs.embed_bid_notices --reembed-all --limit 250000
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

from postgrest.exceptions import APIError

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "embed_bid_notices"
RETRIES = 3


def upsert_embeddings_with_retry(client, updates: list[dict]) -> None:
    """RPC 호출 — cold pool/HNSW 부하로 인한 57014 timeout 대응.

    같은 batch로 지수 backoff retry → 그래도 실패하면 절반 분할 재귀.
    배치 1개까지 줄여도 실패하면 raise.
    """
    for attempt in range(RETRIES):
        try:
            client.rpc(
                "update_bid_notice_embeddings", {"updates": updates}
            ).execute()
            return
        except APIError as e:
            if e.code != "57014":
                raise
            if attempt < RETRIES - 1:
                wait = 2 * (attempt + 1)
                print(f"    rpc timeout (n={len(updates)}), retry in {wait}s")
                time.sleep(wait)
    if len(updates) <= 1:
        raise RuntimeError(f"rpc timeout even with n=1 ({len(updates)} rows)")
    mid = len(updates) // 2
    print(f"    splitting batch {len(updates)} -> {mid} + {len(updates) - mid}")
    upsert_embeddings_with_retry(client, updates[:mid])
    upsert_embeddings_with_retry(client, updates[mid:])


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


def fetch_pending(
    client, batch: int, reembed_all: bool, job_start: str
) -> list[dict]:
    q = client.table("bid_notices").select(SELECT_COLS)
    if reembed_all:
        # 이번 사이클 시작 이전 임베딩 + NULL → 한 번씩만 처리됨
        q = q.or_(f"embedded_at.is.null,embedded_at.lt.{job_start}")
    else:
        q = q.is_("embedded_at", "null")
    return q.limit(batch).execute().data


def run(limit: int = 5000, batch: int = 200, reembed_all: bool = False) -> None:
    job_start = datetime.now().isoformat()
    run_id = log_ingest_start(
        JOB_NAME,
        {"limit": limit, "batch": batch, "reembed_all": reembed_all},
    )
    client = get_admin_client()
    total = 0
    try:
        while total < limit:
            rows = fetch_pending(
                client, min(batch, limit - total), reembed_all, job_start
            )
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
            upsert_embeddings_with_retry(client, updates)
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
    args = parser.parse_args()
    run(args.limit, args.batch, args.reembed_all)

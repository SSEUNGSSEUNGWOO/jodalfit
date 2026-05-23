"""회사 벡터 통합 생성 잡 (3 시그널 가중합) — batched 버전.

회사 벡터 = α·수주 + β·관심 + γ·업종

성능 최적화 (v2):
- contracts에서 active bizrno_norm 풀을 먼저 받음 (한 번)
- chunk 단위(100 회사씩)로 contracts + bid_notices.embedding을 in_ 쿼리로 한 번에
- 회사별 그룹화 + 평균 → batch RPC update

MVP는 **수주 시그널 중심**. 관심/업종은 데이터 풍부해진 후 v0.2.

실행:
    cd backend
    uv run python -m jobs.compute_company_vectors --limit 25000
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from typing import Iterator

import numpy as np

from app.services.openai_client import vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "compute_company_vectors"

ALPHA = 0.7  # 수주 (현재 유일한 활성 시그널)
BETA = 0.1   # 관심 (사전규격 의견 — 1주치 0건이라 보류)
GAMMA = 0.2  # 업종 (UsrInfoService02 데이터 풍부해진 후)


def parse_pgvector(s: str | list | None) -> np.ndarray | None:
    if s is None:
        return None
    if isinstance(s, list):
        return np.array(s, dtype=np.float32)
    inner = s.strip()[1:-1]
    if not inner:
        return None
    return np.fromstring(inner, sep=",", dtype=np.float32)


def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def fetch_active_bizrnos(client) -> list[str]:
    """contracts에 등장한 unique bizrno_norm을 페이지 단위로 받음."""
    bizrnos: set[str] = set()
    offset = 0
    PAGE = 1000
    while True:
        r = (
            client.table("contracts")
            .select("rprsnt_corp_bizrno_norm")
            .not_.is_("rprsnt_corp_bizrno_norm", "null")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            v = row.get("rprsnt_corp_bizrno_norm")
            if v:
                bizrnos.add(v)
        if len(r) < PAGE:
            break
        offset += PAGE
    return sorted(bizrnos)


def chunks(seq: list[str], size: int) -> Iterator[list[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def process_chunk(client, chunk_bizrnos: list[str]) -> tuple[list[dict], int]:
    """100개 회사를 한 번에 처리해 update payload + skipped count 반환."""
    # 1. 회사 정보
    corps = (
        client.table("companies")
        .select("bizrno,bizrno_norm,corp_nm")
        .in_("bizrno_norm", chunk_bizrnos)
        .execute()
        .data
    )
    if not corps:
        return [], len(chunk_bizrnos)

    norm_to_corp = {c["bizrno_norm"]: c for c in corps if c.get("bizrno_norm")}

    # 2. 그 회사들의 모든 계약
    contracts = (
        client.table("contracts")
        .select("rprsnt_corp_bizrno_norm,bid_ntce_no,bid_ntce_ord")
        .in_("rprsnt_corp_bizrno_norm", chunk_bizrnos)
        .execute()
        .data
    )
    if not contracts:
        return [], len(chunk_bizrnos)

    # 3. 공고 임베딩 (bid_ntce_no 단위 in_)
    bid_nos = list({c["bid_ntce_no"] for c in contracts if c.get("bid_ntce_no")})
    emb_map: dict[tuple[str, str], np.ndarray] = {}
    EMB_PAGE = 300
    for sub in chunks(bid_nos, EMB_PAGE):
        rows = (
            client.table("bid_notices")
            .select("bid_ntce_no,bid_ntce_ord,embedding")
            .in_("bid_ntce_no", sub)
            .not_.is_("embedding", "null")
            .execute()
            .data
        )
        for r in rows:
            vec = parse_pgvector(r.get("embedding"))
            if vec is not None:
                emb_map[(r["bid_ntce_no"], r["bid_ntce_ord"])] = vec

    # 4. 회사별 그룹화
    by_biz: dict[str, list[np.ndarray]] = defaultdict(list)
    for c in contracts:
        b = c["rprsnt_corp_bizrno_norm"]
        key = (c["bid_ntce_no"], c["bid_ntce_ord"])
        v = emb_map.get(key)
        if v is not None:
            by_biz[b].append(v)

    # 5. 회사별 평균 → update payload
    updates: list[dict] = []
    skipped = 0
    now_iso = datetime.now().isoformat()
    for bizrno_norm in chunk_bizrnos:
        vectors = by_biz.get(bizrno_norm)
        corp = norm_to_corp.get(bizrno_norm)
        if not vectors or not corp:
            skipped += 1
            continue
        suju = np.mean(vectors, axis=0)
        # MVP: 수주 시그널만 → 정규화
        vec = normalize(suju)
        updates.append(
            {
                "bizrno": corp["bizrno"],
                "embedding": vector_to_pgvector_str(vec.tolist()),
                "embedded_at": now_iso,
            }
        )
    return updates, skipped


def run(limit: int = 25000, chunk_size: int = 100) -> None:
    run_id = log_ingest_start(
        JOB_NAME,
        {"limit": limit, "chunk": chunk_size, "alpha": ALPHA, "version": "batched_v2"},
    )
    client = get_admin_client()

    print(f"[{JOB_NAME}] fetching active bizrnos from contracts...")
    active = fetch_active_bizrnos(client)
    target = active[:limit]
    print(f"[{JOB_NAME}] active bizrnos = {len(active):,}, will process = {len(target):,}")

    total = 0
    total_skipped = 0
    chunks_done = 0
    chunks_total = (len(target) + chunk_size - 1) // chunk_size

    try:
        for ch in chunks(target, chunk_size):
            updates, skipped = process_chunk(client, ch)
            if updates:
                client.rpc("update_company_embeddings", {"updates": updates}).execute()
            total += len(updates)
            total_skipped += skipped
            chunks_done += 1
            if chunks_done % 5 == 0 or chunks_done == chunks_total:
                print(
                    f"  [{chunks_done}/{chunks_total}] vectors {total:,} | skipped {total_skipped:,}"
                )

        log_ingest_finish(run_id, "success", rows_updated=total)
        print(f"[{JOB_NAME}] done. {total:,} vectors, {total_skipped:,} skipped")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25000)
    parser.add_argument("--chunk-size", type=int, default=100)
    args = parser.parse_args()
    run(args.limit, args.chunk_size)

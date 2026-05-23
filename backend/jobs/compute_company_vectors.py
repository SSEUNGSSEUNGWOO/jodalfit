"""회사 벡터 통합 생성 잡 (3 시그널 가중합).

회사 벡터 = α·수주 + β·관심 + γ·업종 (가중치는 사용 가능한 시그널만 정규화)

- 수주 (α=0.7): contracts → bid_notices.embedding 평균
- 관심 (β=0.1): pre_spec_opinions(mkng_corp_nm fuzzy 매칭) → pre_specs.embedding 평균
- 업종 (γ=0.2): companies.corp_bsns_div_nm 텍스트 임베딩 (UsrInfoService02 적재 후 풍부해짐)

MVP는 수주 시그널 중심. 다른 시그널은 데이터 있는 회사만 가중합.
콜드스타트(수주 0)는 관심/업종으로 폴백.

실행:
    cd backend
    uv run python -m jobs.compute_company_vectors --limit 5000
"""

from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "compute_company_vectors"

ALPHA = 0.7  # 수주
BETA = 0.1   # 관심
GAMMA = 0.2  # 업종


def parse_pgvector(s: str | list) -> np.ndarray | None:
    """pgvector → numpy. supabase-py가 list 또는 str로 반환."""
    if s is None:
        return None
    if isinstance(s, list):
        return np.array(s, dtype=np.float32)
    # "[1.0,2.0,...]" 형식
    inner = s.strip()[1:-1]
    if not inner:
        return None
    return np.fromstring(inner, sep=",", dtype=np.float32)


def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def compute_suju_vector(client, bizrno_norm: str) -> np.ndarray | None:
    """그 회사가 따낸 공고들의 임베딩 평균."""
    contract_rows = (
        client.table("contracts")
        .select("bid_ntce_no,bid_ntce_ord")
        .eq("rprsnt_corp_bizrno_norm", bizrno_norm)
        .execute()
        .data
    )
    if not contract_rows:
        return None

    bid_keys = [(r["bid_ntce_no"], r.get("bid_ntce_ord") or "000") for r in contract_rows if r["bid_ntce_no"]]
    if not bid_keys:
        return None

    # 공고 임베딩 조회 (in_은 단일 컬럼만 지원 → 공고번호로만 필터하고 차수는 post-filter)
    bid_nos = list({k[0] for k in bid_keys})
    rows = (
        client.table("bid_notices")
        .select("bid_ntce_no,bid_ntce_ord,embedding")
        .in_("bid_ntce_no", bid_nos)
        .not_.is_("embedding", "null")
        .execute()
        .data
    )
    bid_set = set(bid_keys)
    vectors = []
    for r in rows:
        if (r["bid_ntce_no"], r["bid_ntce_ord"]) in bid_set:
            vec = parse_pgvector(r["embedding"])
            if vec is not None:
                vectors.append(vec)
    if not vectors:
        return None
    return np.mean(vectors, axis=0)


def compute_interest_vector(client, corp_nm: str) -> np.ndarray | None:
    """그 회사명으로 의견 작성한 사양들의 임베딩 평균.

    NOTE: 회사명 매핑 신뢰성 낮음 (코덱스 지적). 임시 fuzzy 매칭만 적용.
    추후 정규화/임계값 로직 추가 필요.
    """
    if not corp_nm or len(corp_nm) < 2:
        return None
    opinion_rows = (
        client.table("pre_spec_opinions")
        .select("bf_spec_rgst_no")
        .ilike("mkng_corp_nm", corp_nm)
        .execute()
        .data
    )
    if not opinion_rows:
        return None
    spec_ids = list({r["bf_spec_rgst_no"] for r in opinion_rows if r["bf_spec_rgst_no"]})
    rows = (
        client.table("pre_specs")
        .select("embedding")
        .in_("bf_spec_rgst_no", spec_ids)
        .not_.is_("embedding", "null")
        .execute()
        .data
    )
    vectors = [v for v in (parse_pgvector(r["embedding"]) for r in rows) if v is not None]
    if not vectors:
        return None
    return np.mean(vectors, axis=0)


def compute_industry_vector(corp: dict) -> np.ndarray | None:
    """회사 업종 텍스트 임베딩. UsrInfoService02 적재 후 풍부해짐."""
    parts = []
    if corp.get("corp_bsns_div_nm"):
        parts.append(f"업무구분: {corp['corp_bsns_div_nm']}")
    if corp.get("mnfctr_div_nm"):
        parts.append(f"제조구분: {corp['mnfctr_div_nm']}")
    if not parts:
        return None
    text = "\n".join(parts)
    vecs = embed_texts([text])
    return np.array(vecs[0], dtype=np.float32) if vecs else None


def combine(signals: list[tuple[float, np.ndarray]]) -> np.ndarray:
    """가용 시그널만 정규화해서 가중합."""
    used = [(w, v) for w, v in signals if v is not None]
    total_w = sum(w for w, _ in used)
    if total_w == 0:
        return None  # type: ignore
    out = np.zeros_like(used[0][1])
    for w, v in used:
        out += (w / total_w) * v
    return normalize(out)


def run(limit: int = 5000, batch: int = 50) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "batch": batch, "alpha": ALPHA, "beta": BETA, "gamma": GAMMA})
    client = get_admin_client()
    total = 0
    skipped = 0
    try:
        offset = 0
        while total + skipped < limit:
            corps = (
                client.table("companies")
                .select("bizrno,bizrno_norm,corp_nm,corp_bsns_div_nm,mnfctr_div_nm")
                .range(offset, offset + batch - 1)
                .execute()
                .data
            )
            if not corps:
                break

            updates = []
            for corp in corps:
                bizrno_norm = corp.get("bizrno_norm") or corp.get("bizrno", "").replace("-", "")
                if not bizrno_norm:
                    skipped += 1
                    continue

                suju = compute_suju_vector(client, bizrno_norm)
                interest = compute_interest_vector(client, corp.get("corp_nm") or "")
                industry = compute_industry_vector(corp) if (suju is None or interest is None) else None

                vec = combine([(ALPHA, suju), (BETA, interest), (GAMMA, industry)])
                if vec is None:
                    skipped += 1
                    continue

                updates.append(
                    {
                        "bizrno": corp["bizrno"],
                        "embedding": vector_to_pgvector_str(vec.tolist()),
                        "embedded_at": datetime.now().isoformat(),
                    }
                )

            if updates:
                client.rpc("update_company_embeddings", {"updates": updates}).execute()
                total += len(updates)
                print(f"  computed {total} company vectors (skipped {skipped})")

            offset += batch

        log_ingest_finish(run_id, "success", rows_updated=total)
        print(f"[{JOB_NAME}] done. {total} vectors computed, {skipped} skipped (no signal)")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--batch", type=int, default=50)
    args = parser.parse_args()
    run(args.limit, args.batch)

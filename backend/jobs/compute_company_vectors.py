"""회사 벡터 통합 생성 잡 — v0.2 동적 가중치 (업종 메인).

코덱스 + 사용자 직관 협의 결과:
- 메인 시그널 = 업종/공급물품 ("이 회사가 뭐하는 회사인가")
- 보조 시그널 = 수주 ("과거에 뭘 따냈는가")
- 회사별 데이터 풍부도에 따른 동적 가중치

가중치 공식:
- 수주 0건:         업종 1.0   /  수주 0.00 /  관심 0.00  (콜드스타트)
- 수주 1~5건:       업종 0.65  /  수주 0.30 /  관심 0.05  (균형)
- 수주 6+건:        업종 0.50  /  수주 0.45 /  관심 0.05  (수주 풍부)

업종 벡터 입력 텍스트:
  등록업종: {industries[10]}
  공급물품: {products[10]}
  업무구분: {corp_bsns_div_nm}

실행:
    cd backend
    uv run python -m jobs.compute_company_vectors --limit 25000
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime
from typing import Iterator

import numpy as np

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "compute_company_vectors"


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


def dynamic_weights(suju_count: int, has_interest: bool) -> dict[str, float]:
    """수주 데이터 풍부도에 따른 동적 가중치 (코덱스 협의 결과)."""
    if suju_count == 0:
        # 콜드스타트: 업종 메인, 관심 있으면 보조
        return {"suju": 0.0, "interest": 0.1 if has_interest else 0.0,
                "industry": 0.9 if has_interest else 1.0}
    if suju_count <= 5:
        # 균형: 업종 메인, 수주 보조
        return {"suju": 0.30, "interest": 0.05, "industry": 0.65}
    # 수주 6건+: 업종 + 수주 비등하게
    return {"suju": 0.45, "interest": 0.05, "industry": 0.50}


def fetch_active_bizrnos(client) -> list[str]:
    """contracts에 등장한 unique bizrno_norm 페이지로 수집."""
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


def build_industry_text(
    corp: dict,
    industries: tuple[list[str], list[str]],
    products: tuple[list[str], list[str]],
) -> str | None:
    """업종 벡터용 입력 텍스트.

    대표 업종/공급물품은 별도 줄로 prefix 강조 + 중복 노출 (벡터에 더 큰 영향).
    그래서 등록업종 5~10개 회사도 정체성(대표)이 강하게 반영됨.

    `corp_bsns_div_nm`/`mnfctr_div_nm`은 풍부화 회사 cover 0%(2026-05-25 측정)라 제외.
    """
    rep_ind, rest_ind = industries
    rep_prd, rest_prd = products
    parts: list[str] = []
    if rep_ind:
        # 대표 업종은 두 번 노출(헤더 + 본문) — 토큰 빈도 ↑로 벡터에 더 큰 영향
        parts.append(f"대표 업종: {', '.join(rep_ind[:3])}")
    if rep_prd:
        parts.append(f"대표 공급물품: {', '.join(rep_prd[:3])}")
    all_ind = rep_ind + rest_ind
    if all_ind:
        parts.append(f"등록업종: {', '.join(all_ind[:10])}")
    all_prd = rep_prd + rest_prd
    if all_prd:
        parts.append(f"공급물품: {', '.join(all_prd[:10])}")
    return "\n".join(parts) if parts else None


def process_chunk(
    client, chunk_bizrnos: list[str]
) -> tuple[list[dict], int]:
    """100개 회사를 한 번에 처리."""
    # 1. 회사 정보
    corps = (
        client.table("companies")
        .select("bizrno,bizrno_norm,corp_nm,corp_bsns_div_nm,mnfctr_div_nm")
        .in_("bizrno_norm", chunk_bizrnos)
        .execute()
        .data
    )
    if not corps:
        return [], len(chunk_bizrnos)

    norm_to_corp = {c["bizrno_norm"]: c for c in corps if c.get("bizrno_norm")}
    biz_pks = [c["bizrno"] for c in corps if c.get("bizrno")]

    # 2. 등록업종 한 번에 (in_)
    industries_rows = (
        client.table("company_industries")
        .select("bizrno,indstryty_nm,rprsnt_indstryty_yn")
        .in_("bizrno", biz_pks)
        .execute()
        .data
    )
    # (대표 리스트, 나머지 리스트) 튜플로 분리 — 대표는 텍스트에서 더 강조됨
    industries_by_biz: dict[str, tuple[list[str], list[str]]] = defaultdict(
        lambda: ([], [])
    )
    for r in industries_rows:
        nm = r.get("indstryty_nm")
        if not nm:
            continue
        rep, rest = industries_by_biz[r["bizrno"]]
        if r.get("rprsnt_indstryty_yn") == "Y":
            rep.append(nm)
        else:
            rest.append(nm)

    # 3. 공급물품 한 번에
    supply_rows = (
        client.table("company_supply_products")
        .select("bizrno,dtl_prdct_clsfc_nm,rprsnt_prdct_yn")
        .in_("bizrno", biz_pks)
        .execute()
        .data
    )
    supply_by_biz: dict[str, tuple[list[str], list[str]]] = defaultdict(
        lambda: ([], [])
    )
    for r in supply_rows:
        nm = r.get("dtl_prdct_clsfc_nm")
        if not nm:
            continue
        rep, rest = supply_by_biz[r["bizrno"]]
        if r.get("rprsnt_prdct_yn") == "Y":
            rep.append(nm)
        else:
            rest.append(nm)

    # 4. 수주 시그널 — contracts → bid_notices.embedding 시간 가중 평균
    # 반감기 365일 exp decay: weight = 0.5 ** (days_ago / 365)
    contracts = (
        client.table("contracts")
        .select("rprsnt_corp_bizrno_norm,bid_ntce_no,bid_ntce_ord,cntrct_cncls_date")
        .in_("rprsnt_corp_bizrno_norm", chunk_bizrnos)
        .execute()
        .data
    )
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

    today = date.fromisoformat(datetime.now().date().isoformat())
    HALF_LIFE = 365.0

    suju_weighted: dict[str, list[tuple[float, np.ndarray]]] = defaultdict(list)
    suju_count_by_biz: dict[str, int] = defaultdict(int)
    for c in contracts:
        b = c["rprsnt_corp_bizrno_norm"]
        suju_count_by_biz[b] += 1
        key = (c["bid_ntce_no"], c["bid_ntce_ord"])
        v = emb_map.get(key)
        if v is None:
            continue
        # 시간 가중치
        ds = c.get("cntrct_cncls_date")
        if ds:
            try:
                d = date.fromisoformat(ds[:10])
                days_ago = max((today - d).days, 0)
                w = 0.5 ** (days_ago / HALF_LIFE)
            except Exception:
                w = 1.0
        else:
            w = 1.0
        suju_weighted[b].append((w, v))

    # 평균(가중) 벡터 계산
    suju_by_biz: dict[str, np.ndarray] = {}
    for b, pairs in suju_weighted.items():
        if not pairs:
            continue
        ws = np.array([p[0] for p in pairs], dtype=np.float32)
        vs = np.stack([p[1] for p in pairs])
        total_w = ws.sum()
        if total_w == 0:
            continue
        suju_by_biz[b] = (vs * ws[:, None]).sum(axis=0) / total_w

    # 5. 업종 텍스트 배치 임베딩 (회사당 1 텍스트, 한 번에)
    industry_texts: list[str] = []
    industry_targets: list[str] = []  # bizrno_norm
    for bizrno_norm in chunk_bizrnos:
        corp = norm_to_corp.get(bizrno_norm)
        if not corp:
            continue
        text = build_industry_text(
            corp,
            industries_by_biz.get(corp["bizrno"], ([], [])),
            supply_by_biz.get(corp["bizrno"], ([], [])),
        )
        if text:
            industry_texts.append(text)
            industry_targets.append(bizrno_norm)

    industry_by_biz: dict[str, np.ndarray] = {}
    if industry_texts:
        embs = embed_texts(industry_texts)
        for b, e in zip(industry_targets, embs):
            industry_by_biz[b] = np.array(e, dtype=np.float32)

    # 6. 회사별 가중합
    now_iso = datetime.now().isoformat()
    updates: list[dict] = []
    skipped = 0
    for bizrno_norm in chunk_bizrnos:
        corp = norm_to_corp.get(bizrno_norm)
        if not corp:
            skipped += 1
            continue

        suju_v = suju_by_biz.get(bizrno_norm)  # 이미 시간 가중 평균
        suju_count = suju_count_by_biz.get(bizrno_norm, 0)
        industry_vec = industry_by_biz.get(bizrno_norm)

        # 관심 시그널은 v0.2.1에서 (회사명 매핑 후) — 일단 0
        interest_v = None

        # 가용한 시그널만으로 가중합. dynamic_weights는 수주 건수 기반
        signals: list[tuple[float, np.ndarray]] = []
        weights = dynamic_weights(suju_count, interest_v is not None)
        if industry_vec is not None:
            signals.append((weights["industry"], industry_vec))
        if suju_v is not None:
            signals.append((weights["suju"], suju_v))
        if interest_v is not None:
            signals.append((weights["interest"], interest_v))

        if not signals:
            skipped += 1
            continue

        total_w = sum(w for w, _ in signals)
        if total_w == 0:
            skipped += 1
            continue
        out = np.zeros_like(signals[0][1])
        for w, v in signals:
            out += (w / total_w) * v
        vec = normalize(out)

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
        JOB_NAME, {"limit": limit, "chunk": chunk_size, "version": "dynamic_weights_v3"}
    )
    client = get_admin_client()

    print(f"[{JOB_NAME}] fetching active bizrnos from contracts...")
    active = fetch_active_bizrnos(client)

    # 풍부화 안 된 회사 (등록업종 없음)도 포함 — 콜드스타트는 corp_bsns_div_nm 폴백
    # active list에 없는 회사도 추가하고 싶다면 companies 전체 + active 합집합 가능
    target = active[:limit]
    print(f"[{JOB_NAME}] active={len(active):,} will_process={len(target):,}")

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
        print(
            f"[{JOB_NAME}] done. {total:,} vectors / {total_skipped:,} skipped"
        )
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25000)
    parser.add_argument("--chunk-size", type=int, default=100)
    args = parser.parse_args()
    run(args.limit, args.chunk_size)

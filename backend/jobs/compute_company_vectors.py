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
from jobs._common import (
    log_ingest_finish,
    log_ingest_start,
    upsert_embeddings_with_retry,
)

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


def dynamic_weights(suju_count: float, has_interest: bool) -> dict[str, float]:
    """수주 데이터 풍부도에 따른 동적 가중치 (코덱스 협의 결과).

    suju_count는 유효 건수 = 낙찰 + 0.4×참가 — 참가만 있는 회사도
    수주 시그널 티어에 진입한다 (참가 = 실제로 노리는 공고라는 의도 시그널).
    """
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
    """contracts 낙찰사 ∪ award_results 참가사 unique bizrno.

    참가만 하고 수주 못 한 회사도 벡터를 만들어야 키워드 폴백 없이 추천 가능.
    (양쪽 모두 숫자만 남긴 정규화 사업자번호)
    """
    bizrnos: set[str] = set()
    PAGE = 1000

    # offset 페이징은 47만 행 뒤쪽에서 8초 timeout(57014)에 걸린다 (2026-09-18) →
    # 사업자번호 인덱스를 타는 keyset. gt(last) 가 같은 번호의 나머지 행을 건너뛰지만 필요한 건 번호 집합뿐이다.
    last = ""
    while True:
        q = (
            client.table("contracts")
            .select("rprsnt_corp_bizrno_norm")
            .not_.is_("rprsnt_corp_bizrno_norm", "null")
            .order("rprsnt_corp_bizrno_norm")
            .limit(PAGE)
        )
        if last:
            q = q.gt("rprsnt_corp_bizrno_norm", last)
        r = q.execute().data
        if not r:
            break
        for row in r:
            v = row.get("rprsnt_corp_bizrno_norm")
            if v:
                bizrnos.add(v)
        last = r[-1]["rprsnt_corp_bizrno_norm"]
        if len(r) < PAGE:
            break

    # is_winner=False에는 인덱스가 없어 offset 페이징이 timeout(57014) →
    # bizrno 인덱스를 타는 keyset 페이지네이션 사용
    last = ""
    while True:
        q = (
            client.table("award_results")
            .select("bizrno")
            .eq("is_winner", False)
            .not_.is_("bizrno", "null")
            .order("bizrno")
            .limit(PAGE)
        )
        if last:
            q = q.gt("bizrno", last)
        r = q.execute().data
        if not r:
            break
        for row in r:
            v = row.get("bizrno")
            if v:
                bizrnos.add(v)
        last = r[-1]["bizrno"]
        if len(r) < PAGE:
            break

    return sorted(bizrnos)


def fetch_embedded_at_map(client) -> dict[str, str | None]:
    """companies 페이지 스캔 → bizrno_norm별 embedded_at (없으면 None).
    같은 사업자번호가 여러 행이면 가장 최근 embedded_at (한 행이라도 벡터가 있으면 '있음')."""
    out: dict[str, str | None] = {}
    PAGE = 1000
    offset = 0
    while True:
        r = (
            client.table("companies")
            .select("bizrno_norm,embedded_at")
            .not_.is_("bizrno_norm", "null")
            .order("bizrno")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            n, at = row["bizrno_norm"], row.get("embedded_at")
            if n not in out or (at and (out[n] is None or at > out[n])):
                out[n] = at
        if len(r) < PAGE:
            break
        offset += PAGE
    return out


def _digits(s: str | None) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def fetch_user_searched(client) -> set[str]:
    """실사용자가 검색한 회사 (search_logs.source='user', 0034). 내부 SSR·봇은 제외."""
    out: set[str] = set()
    last = 0
    while True:
        r = (
            client.table("search_logs").select("id,matched_bizrno")
            .eq("source", "user").not_.is_("matched_bizrno", "null")
            .gt("id", last).order("id").limit(1000).execute().data
        )
        if not r:
            break
        out.update(_digits(x["matched_bizrno"]) for x in r)
        last = r[-1]["id"]
        if len(r) < 1000:
            break
    return out


def fetch_enriched(client) -> set[str]:
    """등록업종 또는 공급물품이 수집된 회사 — 업종 벡터 재료가 있어 거의 확실히 벡터가 만들어진다."""
    out: set[str] = set()
    for table in ("company_industries", "company_supply_products"):
        last = ""
        while True:
            q = client.table(table).select("bizrno").order("bizrno").limit(1000)
            if last:
                q = q.gt("bizrno", last)
            r = q.execute().data
            if not r:
                break
            out.update(_digits(x["bizrno"]) for x in r)
            last = r[-1]["bizrno"]
            if len(r) < 1000:
                break
    return out


def order_targets(active: list[str], emb_at: dict[str, str | None],
                  searched: set[str], enriched: set[str], today: str) -> tuple[list[str], dict[str, int]]:
    """처리 순서.
    0) 실사용자가 검색했는데 벡터 없는 회사  1) 업종·물품 재료가 있는데 벡터 없는 회사
    2) 나머지 벡터 없는 회사 — 날짜별 해시로 순환 (예전엔 사업자번호 순이라 매일 같은 앞쪽 2.5만 개만 돌고
       재료 없어 건너뛴 회사가 계속 자리를 차지해, 뒤쪽 4만 개는 영영 차례가 오지 않았다)
    3) 벡터 있는 회사 — 오래된 순 갱신
    대상 = (낙찰사 ∪ 참가사 ∪ 검색된 회사 ∪ 재료 있는 회사) ∩ companies.
    """
    import hashlib

    universe = (set(active) | searched | enriched) & emb_at.keys()
    tiers: dict[str, list[str]] = {"searched": [], "enriched": [], "rotating": [], "refresh": []}
    for b in universe:
        if emb_at[b] is not None:
            tiers["refresh"].append(b)
        elif b in searched:
            tiers["searched"].append(b)
        elif b in enriched:
            tiers["enriched"].append(b)
        else:
            tiers["rotating"].append(b)
    tiers["searched"].sort()
    tiers["enriched"].sort()
    tiers["rotating"].sort(key=lambda b: hashlib.md5(f"{today}:{b}".encode()).hexdigest())
    tiers["refresh"].sort(key=lambda b: emb_at[b] or "")
    ordered = tiers["searched"] + tiers["enriched"] + tiers["rotating"] + tiers["refresh"]
    return ordered, {k: len(v) for k, v in tiers.items()}


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

    # companies 에는 같은 사업자번호가 하이픈 유무로 두 행인 회사가 있다 (2026-09 기준 7.5천 개).
    # 업종은 하이픈 행에만 붙어 있기도 해서, 사업자번호(norm) 단위로 묶어 재료를 합치고 벡터는 모든 행에 쓴다.
    norm_to_rows: dict[str, list[dict]] = defaultdict(list)
    for c in corps:
        if c.get("bizrno_norm") and c.get("bizrno"):
            norm_to_rows[c["bizrno_norm"]].append(c)
    norm_to_corp = {n: rows[0] for n, rows in norm_to_rows.items()}
    biz_to_norm = {c["bizrno"]: n for n, rows in norm_to_rows.items() for c in rows}
    biz_pks = list(biz_to_norm)

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
        rep, rest = industries_by_biz[biz_to_norm[r["bizrno"]]]
        if nm in rep or nm in rest:
            continue
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
        rep, rest = supply_by_biz[biz_to_norm[r["bizrno"]]]
        if nm in rep or nm in rest:
            continue
        if r.get("rprsnt_prdct_yn") == "Y":
            rep.append(nm)
        else:
            rest.append(nm)

    # 4. 수주 시그널 — 낙찰(contracts) + 참가(award_results) → bid_notices.embedding
    # 시간 가중 평균. 반감기 365일 exp decay: weight = 0.5 ** (days_ago / 365)
    # 재료 가중: 낙찰 1.0 vs 참가 0.4 (참가는 의도 시그널이지만 검증 강도가 낮음)
    contracts = (
        client.table("contracts")
        .select("rprsnt_corp_bizrno_norm,bid_ntce_no,bid_ntce_ord,cntrct_cncls_date")
        .in_("rprsnt_corp_bizrno_norm", chunk_bizrnos)
        .execute()
        .data
    )
    participations = (
        client.table("award_results")
        .select("bizrno,bid_ntce_no,bid_ntce_ord,created_at,bidprc_dt:raw->>bidprcDt")
        .in_("bizrno", chunk_bizrnos)
        .eq("is_winner", False)
        .execute()
        .data
    )
    bid_nos = list(
        {c["bid_ntce_no"] for c in contracts if c.get("bid_ntce_no")}
        | {p["bid_ntce_no"] for p in participations if p.get("bid_ntce_no")}
    )
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
    PARTICIPATION_WEIGHT = 0.4

    def time_weight(ds: str | None) -> float:
        if not ds:
            return 1.0
        try:
            d = date.fromisoformat(ds[:10])
            days_ago = max((today - d).days, 0)
            return 0.5 ** (days_ago / HALF_LIFE)
        except Exception:
            return 1.0

    suju_weighted: dict[str, list[tuple[float, np.ndarray]]] = defaultdict(list)
    suju_count_by_biz: dict[str, float] = defaultdict(float)
    for c in contracts:
        b = c["rprsnt_corp_bizrno_norm"]
        suju_count_by_biz[b] += 1
        v = emb_map.get((c["bid_ntce_no"], c["bid_ntce_ord"]))
        if v is None:
            continue
        suju_weighted[b].append((time_weight(c.get("cntrct_cncls_date")), v))

    for p in participations:
        b = p["bizrno"]
        suju_count_by_biz[b] += PARTICIPATION_WEIGHT
        v = emb_map.get((p["bid_ntce_no"], p["bid_ntce_ord"]))
        if v is None:
            continue
        w = time_weight(p.get("bidprc_dt") or p.get("created_at"))
        suju_weighted[b].append((w * PARTICIPATION_WEIGHT, v))

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
            industries_by_biz.get(bizrno_norm, ([], [])),
            supply_by_biz.get(bizrno_norm, ([], [])),
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

        vec_str = vector_to_pgvector_str(vec.tolist())
        for row in norm_to_rows[bizrno_norm]:  # 중복 행 모두에 — 추천이 어느 행을 읽어도 같은 벡터
            updates.append({"bizrno": row["bizrno"], "embedding": vec_str, "embedded_at": now_iso})
    return updates, skipped


def run(limit: int = 25000, chunk_size: int = 100) -> None:
    run_id = log_ingest_start(
        JOB_NAME, {"limit": limit, "chunk": chunk_size, "version": "dynamic_weights_v3"}
    )
    client = get_admin_client()

    print(f"[{JOB_NAME}] fetching active bizrnos from contracts...")
    active = fetch_active_bizrnos(client)

    # 대상(~13만) > limit(25k)라 절단 필요 — 순서는 order_targets 참고.
    # companies 에 없는 회사는 process_chunk 에서 어차피 스킵되므로 제외.
    emb_at = fetch_embedded_at_map(client)
    searched = fetch_user_searched(client)
    enriched = fetch_enriched(client)
    ordered, tier_sizes = order_targets(active, emb_at, searched, enriched, date.today().isoformat())
    target = ordered[:limit]
    print(
        f"[{JOB_NAME}] active={len(active):,} targets={len(ordered):,} "
        f"(검색됨·벡터없음 {tier_sizes['searched']:,} / 재료있음·벡터없음 {tier_sizes['enriched']:,} / "
        f"나머지 벡터없음 {tier_sizes['rotating']:,} 순환 / 갱신 {tier_sizes['refresh']:,}) will_process={len(target):,}"
    )

    total = 0
    total_skipped = 0
    chunks_done = 0
    chunks_total = (len(target) + chunk_size - 1) // chunk_size

    try:
        for ch in chunks(target, chunk_size):
            updates, skipped = process_chunk(client, ch)
            if updates:
                upsert_embeddings_with_retry(
                    client, "update_company_embeddings", updates
                )
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

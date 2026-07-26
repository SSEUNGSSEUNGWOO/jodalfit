"""추천 비즈니스 로직.

모드:
- mode="company": 회사명/사업자번호 → 회사 벡터로 매칭 (기본)
- mode="keywords": 관심 키워드 텍스트 → 직접 임베딩으로 매칭 (콜드스타트 대응)
- mode="auto": 입력 자동 감지 + 양쪽 결과

v0.3 (단계 풀 확장 + 키워드 하이브리드):
- 추천 풀 = 입찰공고 + 사전규격(골든타임) + 발주계획(선행지표)
- keywords 파라미터: 회사 벡터에 키워드 임베딩을 0.6/0.4로 가중합 → 다부서 회사 부서 좁힘
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import numpy as np

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client
from app.services.viz import anchor_positions, project_many, project_point

COMPANY_WEIGHT = 0.6
KEYWORDS_WEIGHT = 0.4
VIZ_RESULT_LIMIT = 10  # viz에 띄울 입찰공고 결과 점 개수


def find_company(query: str) -> dict | None:
    """회사명 또는 사업자번호로 식별. 가장 매칭 좋은 1개 반환.

    한국어 회사명 fuzzy 매칭에서 공백 위치 변형이 trigram 점수에 영향(예:
    "케이브레인 컴퍼니"가 "케이 컴퍼니"와 trigram 더 많이 겹쳐 잘못 매칭).
    원본과 공백 제거 query를 둘 다 시도해서 similarity 더 높은 쪽 채택.
    """
    client = get_admin_client()
    digits = "".join(ch for ch in query if ch.isdigit())
    if len(digits) == 10:
        res = (
            client.table("companies")
            .select(
                "bizrno,corp_nm,english_nm,ceo_nm,corp_bsns_div_nm,rgn_nm,embedding,is_restricted"
            )
            .eq("bizrno_norm", digits)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]

    res = client.rpc("find_companies", {"query_name": query, "max_count": 1}).execute()
    best = res.data[0] if res.data else None

    normalized = "".join(query.split())
    if normalized and normalized != query:
        res2 = client.rpc(
            "find_companies", {"query_name": normalized, "max_count": 1}
        ).execute()
        cand = res2.data[0] if res2.data else None
        if cand and (
            not best
            or (cand.get("similarity") or 0) > (best.get("similarity") or 0)
        ):
            best = cand

    if not best:
        return None
    full = (
        client.table("companies")
        .select(
            "bizrno,corp_nm,english_nm,ceo_nm,corp_bsns_div_nm,rgn_nm,embedding,is_restricted"
        )
        .eq("bizrno", best["bizrno"])
        .limit(1)
        .execute()
    )
    return full.data[0] if full.data else None


import re as _re


def _tokenize(s: str | None) -> set[str]:
    if not s:
        return set()
    return {t.strip() for t in _re.split(r"[\s,·/\-]+", s) if t.strip() and len(t.strip()) >= 2}


def rerank(
    rows: list[dict],
    company_rgn: str | None,
    company_terms: set[str] | None = None,
    company_institutions: set[str] | None = None,
    company_amt_median: float | None = None,
) -> list[dict]:
    """후보 공고를 재랭킹.

    bonus 구성 (v0.3 — 도메인·이력 우대):
      - 마감 임박 -0.20 / 6~14일 적정 +0.05
      - 회사 지역 ↔ 공고 참가가능지역 일치 +0.05
      - 회사 등록업종·공급물품 토큰 ↔ 공고 토큰 공통수 (1개 +0.06 ~ 3개+ +0.18)
      - 회사 과거 거래 기관 ↔ 공고 발주기관 일치 +0.15
      - 회사 과거 수주 중간값 vs 공고 추정가 적합성 (0.7x~1.5x +0.03, 외곽 -0.05)
    """
    today = date.today()
    rgn = company_rgn.split()[0] if company_rgn else None
    company_terms = company_terms or set()
    company_institutions = company_institutions or set()

    for r in rows:
        bonus = 0.0
        detail: dict[str, Any] = {}
        clse = r.get("bid_clse_date")
        if clse:
            clse_dt = date.fromisoformat(clse) if isinstance(clse, str) else clse
            days_left = (clse_dt - today).days
            if days_left <= 1:
                bonus -= 0.20
                detail["urgent_penalty"] = -0.20
            elif 6 <= days_left <= 14:
                bonus += 0.05
                detail["dday_sweet"] = 0.05

        if rgn and r.get("prtcpt_psbl_rgn_nm"):
            if rgn in r["prtcpt_psbl_rgn_nm"]:
                bonus += 0.05
                detail["region_match"] = {"score": 0.05, "rgn": rgn}

        if company_terms:
            notice_terms = _tokenize(r.get("bidprc_psbl_indstryty_nm")) | _tokenize(
                r.get("bid_ntce_nm")
            )
            overlap_set = company_terms & notice_terms
            overlap = len(overlap_set)
            if overlap > 0:
                inc = min(0.06 + 0.05 * (overlap - 1), 0.18)
                bonus += inc
                detail["industry_tokens"] = {
                    "score": round(inc, 3),
                    "matched": sorted(overlap_set)[:5],
                }

        # 기관 친화도
        if company_institutions:
            instt = (r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "").strip()
            if instt and instt in company_institutions:
                bonus += 0.15
                detail["institution_familiar"] = {"score": 0.15, "instt": instt}

        # 금액대 적합성 — 부수 시그널. 좁은 영역만 적합 인정.
        if company_amt_median and company_amt_median > 0:
            price = r.get("presmpt_prce") or r.get("asign_bdgt_amt")
            if price and price > 0:
                ratio = price / company_amt_median
                if 0.7 <= ratio <= 1.5:
                    bonus += 0.03
                    detail["amount_fit"] = {
                        "score": 0.03,
                        "ratio": round(ratio, 2),
                        "company_median": company_amt_median,
                        "notice_price": price,
                    }
                elif ratio < 0.1 or ratio > 10.0:
                    bonus -= 0.05
                    detail["amount_mismatch"] = {
                        "score": -0.05,
                        "ratio": round(ratio, 2),
                    }

        # 자격 미달
        if r.get("_lic_pass") is False:
            bonus -= 0.30
            detail["license_fail"] = -0.30
        if r.get("_rgn_pass") is False:
            bonus -= 0.30
            detail["region_fail"] = -0.30

        r["base_similarity"] = r.get("similarity", 0)
        r["bonus"] = bonus
        r["bonus_detail"] = detail
        r["score"] = r["base_similarity"] + bonus

    return sorted(rows, key=lambda r: r["score"], reverse=True)


def _fetch_result_embeddings(
    client, results: list[dict]
) -> dict[tuple[str, str], list[float]]:
    """추천 입찰공고들의 임베딩을 한 번에 fetch (viz 좌표 계산용)."""
    keys = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in results if r.get("bid_ntce_no")]
    if not keys:
        return {}
    bid_nos = list({k[0] for k in keys})
    rows = (
        client.table("bid_notices")
        .select("bid_ntce_no,bid_ntce_ord,embedding")
        .in_("bid_ntce_no", bid_nos)
        .not_.is_("embedding", "null")
        .execute()
        .data
        or []
    )
    out: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        emb = r.get("embedding")
        if isinstance(emb, str):
            inner = emb.strip()[1:-1]
            emb = [float(x) for x in inner.split(",")] if inner else []
        if emb:
            out[(r["bid_ntce_no"], r["bid_ntce_ord"])] = emb
    return out


def _build_viz(
    company_vec: list[float],
    results: list[dict],
    result_embs: dict[tuple[str, str], list[float]],
) -> dict:
    """회사 + 추천 TOP N 좌표를 anchor 기반으로 계산."""
    cx, cy = project_point(company_vec)
    top = results[:VIZ_RESULT_LIMIT]
    paired = [
        (r, result_embs[(r["bid_ntce_no"], r["bid_ntce_ord"])])
        for r in top
        if (r["bid_ntce_no"], r["bid_ntce_ord"]) in result_embs
    ]
    coords = project_many([e for _, e in paired]) if paired else []
    return {
        "anchors": anchor_positions(),
        "company": {"x": cx, "y": cy},
        "results": [
            {
                "bid_ntce_no": r["bid_ntce_no"],
                "bid_ntce_ord": r["bid_ntce_ord"],
                "x": x,
                "y": y,
                "score": r.get("score", 0),
                "bid_ntce_nm": r.get("bid_ntce_nm"),
            }
            for (r, _), (x, y) in zip(paired, coords)
        ],
    }


def _blend_embeddings(
    company_vec: list[float] | np.ndarray,
    keyword_vec: list[float] | np.ndarray,
    wc: float = COMPANY_WEIGHT,
    wk: float = KEYWORDS_WEIGHT,
) -> list[float]:
    """회사 벡터 × 키워드 임베딩 가중합 후 정규화.

    회사 벡터와 키워드 임베딩 모두 unit vector(compute_company_vectors / OpenAI)이므로
    가중합 후 L2 정규화만 하면 cosine 유사도 검색에 그대로 쓸 수 있다.
    """
    cv = np.asarray(company_vec, dtype=np.float32)
    kv = np.asarray(keyword_vec, dtype=np.float32)
    blended = wc * cv + wk * kv
    n = float(np.linalg.norm(blended))
    if n > 0:
        blended = blended / n
    return blended.tolist()


def _search_pre_specs(
    embedding_str: str, limit: int, candidate_pool: int
) -> list[dict]:
    """사전규격(골든타임) 매칭 — 단순 코사인 정렬. 자격/지역 보너스 없음.

    의견 마감일이 지난 사전규격은 RPC 단계에서 제외(골든타임 카피와 일관).
    """
    client = get_admin_client()
    res = client.rpc(
        "match_pre_specs",
        {
            "query_embedding": embedding_str,
            "match_count": candidate_pool,
            "min_opnin_clse_date": date.today().isoformat(),
        },
    ).execute()
    raw = res.data or []
    seen: set[str] = set()
    out: list[dict] = []
    for r in raw:
        n = r.get("bf_spec_rgst_no")
        if not n or n in seen:
            continue
        seen.add(n)
        r["stage"] = "pre_spec"
        r["base_similarity"] = r.get("similarity", 0)
        r["score"] = r["base_similarity"]
        out.append(r)
        if len(out) >= limit:
            break
    return out


def _search_order_plans(
    embedding_str: str, limit: int, candidate_pool: int
) -> list[dict]:
    """발주계획(선행지표) 매칭 — 단순 코사인 정렬."""
    client = get_admin_client()
    res = client.rpc(
        "match_order_plans",
        {"query_embedding": embedding_str, "match_count": candidate_pool},
    ).execute()
    raw = res.data or []
    seen: set[str] = set()
    out: list[dict] = []
    for r in raw:
        n = r.get("order_plan_unty_no")
        if not n or n in seen:
            continue
        seen.add(n)
        r["stage"] = "order_plan"
        r["base_similarity"] = r.get("similarity", 0)
        r["score"] = r["base_similarity"]
        out.append(r)
        if len(out) >= limit:
            break
    return out


def _search_with_embedding(
    embedding_str: str,
    company_rgn: str | None,
    limit: int,
    candidate_pool: int,
    company_terms: set[str] | None = None,
    company_institutions: set[str] | None = None,
    company_amt_median: float | None = None,
    company_industry_names: set[str] | None = None,
    algorithm: str = "v1",
    company_bizrno_norm: str | None = None,
) -> list[dict]:
    client = get_admin_client()
    # 같은 bid_ntce_no 다른 ord가 여러 건일 수 있어 풀을 넉넉히 가져온 뒤 dedupe
    res = client.rpc(
        "match_bid_notices",
        {
            "query_embedding": embedding_str,
            "match_count": candidate_pool * 2,
            "min_clse_date": date.today().isoformat(),
        },
    ).execute()
    raw = res.data or []
    # similarity 내림차순 정렬은 RPC가 보장 → 첫 등장 유지
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in raw:
        n = r.get("bid_ntce_no")
        if not n or n in seen:
            continue
        seen.add(n)
        r["stage"] = "notice"
        deduped.append(r)
        if len(deduped) >= candidate_pool:
            break

    if algorithm == "v2":
        # v2: 하드 필터 + 가중치 score + MMR (lazy import — 순환 방지)
        from app.recommender.pipeline import rank_v2

        return rank_v2(
            client,
            deduped,
            company_rgn=company_rgn,
            company_terms=company_terms or set(),
            company_institutions=company_institutions or set(),
            company_amt_median=company_amt_median,
            company_industry_names=company_industry_names or set(),
            limit=limit,
            company_embedding_str=embedding_str,
            company_bizrno_norm=company_bizrno_norm,
        )

    # 자격 데이터 한 번에 fetch + 미통과 표시 (소프트 감점은 rerank 안에서)
    if company_industry_names is not None or company_rgn is not None:
        bid_keys = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in deduped]
        elig = _fetch_eligibility(client, bid_keys)
        for r in deduped:
            slot = elig.get((r["bid_ntce_no"], r["bid_ntce_ord"]))
            if not slot:
                r["_lic_pass"] = True
                r["_rgn_pass"] = True
                continue
            r["_lic_pass"] = _check_license_pass(
                company_industry_names or set(), slot["licenses"]
            )
            r["_rgn_pass"] = _check_rgn_pass(company_rgn, slot["regions"])

    return rerank(
        deduped,
        company_rgn,
        company_terms=company_terms,
        company_institutions=company_institutions,
        company_amt_median=company_amt_median,
    )[:limit]


def _fetch_company_terms(client, bizrno: str) -> set[str]:
    """회사 등록업종 + 공급물품 토큰 set — 재랭킹 보너스 계산용."""
    terms: set[str] = set()
    ind = (
        client.table("company_industries")
        .select("indstryty_nm")
        .eq("bizrno", bizrno)
        .execute()
        .data
        or []
    )
    for r in ind:
        terms |= _tokenize(r.get("indstryty_nm"))
    prd = (
        client.table("company_supply_products")
        .select("dtl_prdct_clsfc_nm")
        .eq("bizrno", bizrno)
        .execute()
        .data
        or []
    )
    for r in prd:
        terms |= _tokenize(r.get("dtl_prdct_clsfc_nm"))
    return terms


def _fetch_company_industry_names(client, bizrno: str) -> set[str]:
    """회사 등록업종 이름 set — 면허 자격 매칭용."""
    out: set[str] = set()
    rows = (
        client.table("company_industries")
        .select("indstryty_nm")
        .eq("bizrno", bizrno)
        .execute()
        .data
        or []
    )
    for r in rows:
        nm = r.get("indstryty_nm")
        if nm:
            # 정규화: 괄호 앞 부분으로도 매칭 가능하도록 두 형태 모두
            out.add(nm)
            base = nm.split("(")[0].strip()
            if base and base != nm:
                out.add(base)
    return out


def _fetch_eligibility(client, bid_keys: list[tuple[str, str]]) -> dict:
    """후보 공고들의 면허/지역 제한 한 번에 fetch.

    bid_keys: [(bid_ntce_no, bid_ntce_ord), ...]
    return: {(no, ord): {"licenses": [...], "regions": [...]}}
    """
    if not bid_keys:
        return {}
    bid_nos = list({k[0] for k in bid_keys if k[0]})
    out: dict[tuple[str, str], dict] = {}

    # license 한 번에 (in_)
    PAGE = 300
    for i in range(0, len(bid_nos), PAGE):
        sub = bid_nos[i : i + PAGE]
        rows = (
            client.table("bid_license_limits")
            .select("bid_ntce_no,bid_ntce_ord,lcns_lmt_nm,lmt_grp_no")
            .in_("bid_ntce_no", sub)
            .execute()
            .data
            or []
        )
        for r in rows:
            key = (r["bid_ntce_no"], r["bid_ntce_ord"])
            slot = out.setdefault(key, {"licenses": [], "regions": []})
            slot["licenses"].append(r)

    for i in range(0, len(bid_nos), PAGE):
        sub = bid_nos[i : i + PAGE]
        rows = (
            client.table("bid_rgn_limits")
            .select("bid_ntce_no,bid_ntce_ord,prtcpt_psbl_rgn_nm")
            .in_("bid_ntce_no", sub)
            .execute()
            .data
            or []
        )
        for r in rows:
            key = (r["bid_ntce_no"], r["bid_ntce_ord"])
            slot = out.setdefault(key, {"licenses": [], "regions": []})
            slot["regions"].append(r)
    return out


def _check_license_pass(
    company_industries: set[str], licenses: list[dict]
) -> bool:
    """면허 자격: 그룹별로 OR — 한 그룹 안의 면허 중 하나라도 보유하면 그 그룹 통과.
    모든 그룹 통과해야 자격 통과.
    """
    if not licenses:
        return True  # 데이터 없음 = 자격 무제한
    if not company_industries:
        return False  # 회사 면허 정보 없음 = 검증 불가 (보수적: 미통과)

    # 그룹별 묶기
    groups: dict[str, list[str]] = {}
    for lim in licenses:
        nm = (lim.get("lcns_lmt_nm") or "").strip()
        if not nm:
            continue
        # "면허명/코드" → 면허명만
        name_only = nm.split("/")[0].strip()
        # 추가로 괄호 앞 base 추출
        base = name_only.split("(")[0].strip()
        grp = str(lim.get("lmt_grp_no") or "1")
        groups.setdefault(grp, []).extend([name_only, base])

    for grp, needed in groups.items():
        needed_set = {n for n in needed if n}
        if not (company_industries & needed_set):
            return False
    return True


def _check_rgn_pass(company_rgn: str | None, regions: list[dict]) -> bool:
    """지역 자격: 회사 지역의 시·도가 허용 지역 중 하나에 포함되면 통과."""
    if not regions:
        return True
    if not company_rgn:
        return True  # 회사 지역 모름 → 보수적 통과
    company_sido = company_rgn.split()[0] if company_rgn else ""
    for lim in regions:
        rgn = (lim.get("prtcpt_psbl_rgn_nm") or "").strip()
        if not rgn:
            continue
        # 공고 지역도 시도 단위로 정규화
        if rgn.split()[0] == company_sido or company_sido in rgn:
            return True
    return False


def _fetch_company_history(client, bizrno_norm: str) -> tuple[set[str], float | None]:
    """회사 과거 거래 기관 set + 수주 금액 중간값.

    rerank의 기관 친화도 + 금액대 적합성 보너스에 사용.
    """
    rows = (
        client.table("contracts")
        .select("dmnd_instt_nm,cntrct_amt")
        .eq("rprsnt_corp_bizrno_norm", bizrno_norm)
        .limit(500)  # 충분히 크게
        .execute()
        .data
        or []
    )
    institutions: set[str] = set()
    amts: list[float] = []
    for r in rows:
        instt = (r.get("dmnd_instt_nm") or "").strip()
        if instt:
            institutions.add(instt)
        amt = r.get("cntrct_amt")
        if amt and amt > 0:
            amts.append(float(amt))
    median = sorted(amts)[len(amts) // 2] if amts else None
    return institutions, median


def recommend(
    query: str,
    limit: int = 5,
    candidate_pool: int = 100,
    mode: Literal["company", "keywords", "auto"] = "company",
    keywords: str | None = None,
    algorithm: Literal["v1", "v2"] = "v1",
) -> dict[str, Any]:
    """추천 메인 진입점.

    company 모드: query는 회사명/사업자번호. keywords가 있으면 회사 벡터에 하이브리드 블렌딩
    keywords 모드: query는 자유 텍스트 (keywords 파라미터는 무시)
    auto 모드: 입력 자동 감지 + 회사/키워드 결과 둘 다 반환 (UI 탭)

    algorithm (A/B):
    - v1: 코사인 + 소프트 보너스 rerank (기존)
    - v2: 자격 하드 필터 + 가중치 score + MMR — company 모드에만 적용
      (키워드 모드는 회사 컨텍스트가 없어 자격/이력 시그널 부재 → 항상 v1)

    응답 공통:
    - results: 입찰공고 매칭 (기존)
    - pre_spec_results: 사전규격 매칭 (v0.3)
    - order_plan_results: 발주계획 매칭 (v0.3)
    """
    if mode == "auto":
        return _recommend_auto(query, limit, candidate_pool, keywords, algorithm)
    if mode == "keywords":
        return _recommend_by_keywords(query, limit, candidate_pool)
    return _recommend_by_company(query, limit, candidate_pool, keywords, algorithm)


def _recommend_auto(
    query: str,
    limit: int,
    candidate_pool: int,
    keywords: str | None = None,
    algorithm: str = "v1",
) -> dict[str, Any]:
    """입력 자동 라우팅 + 양쪽 결과 합치기.

    - 숫자 10자리: 사업자번호 → company 모드만 (키워드 매칭 의미 없음)
    - 그 외: company + keywords 둘 다 호출, 회사 식별 실패해도 키워드 결과 반환

    keywords 파라미터는 회사 결과의 하이브리드 블렌딩에만 영향 (보조 키워드 결과는 query 그대로).
    """
    digits = "".join(ch for ch in query if ch.isdigit())
    is_bizrno = len(digits) == 10

    if is_bizrno:
        result = _recommend_by_company(query, limit, candidate_pool, keywords, algorithm)
        result["mode"] = "auto"
        result["primary"] = "company"
        result["keyword_results"] = []
        return result

    # 텍스트 입력: 두 모드 병렬 실행 (단순 직렬, 비용 거의 동일)
    company_result = _recommend_by_company(query, limit, candidate_pool, keywords, algorithm)
    keyword_result = _recommend_by_keywords(query, limit, candidate_pool)

    company_hit = bool(company_result.get("company")) and bool(company_result.get("results"))

    return {
        "mode": "auto",
        "algorithm": algorithm,
        "primary": "company" if company_hit else "keywords",
        "company": company_result.get("company"),
        "keywords": keywords,
        "results": company_result.get("results", []),
        "pre_spec_results": company_result.get("pre_spec_results", []),
        "order_plan_results": company_result.get("order_plan_results", []),
        "keyword_query": query,
        "keyword_results": keyword_result.get("results", []),
        "keyword_pre_spec_results": keyword_result.get("pre_spec_results", []),
        "keyword_order_plan_results": keyword_result.get("order_plan_results", []),
        "error": None if company_hit or keyword_result.get("results") else "결과가 없습니다",
    }


def _recommend_by_keywords(
    query: str, limit: int, candidate_pool: int
) -> dict[str, Any]:
    text = query.strip()
    if not text:
        return {
            "company": None,
            "mode": "keywords",
            "error": "키워드를 입력해주세요",
            "results": [],
            "pre_spec_results": [],
            "order_plan_results": [],
        }

    embedding = embed_texts([f"관심 영역: {text}"])[0]
    embedding_str = vector_to_pgvector_str(embedding)
    ranked = _search_with_embedding(embedding_str, None, limit, candidate_pool)
    pre_specs = _search_pre_specs(embedding_str, limit, candidate_pool)
    order_plans = _search_order_plans(embedding_str, limit, candidate_pool)

    return {
        "company": None,
        "mode": "keywords",
        "query": text,
        "results": ranked,
        "pre_spec_results": pre_specs,
        "order_plan_results": order_plans,
    }


def _recommend_by_company(
    query: str,
    limit: int,
    candidate_pool: int,
    keywords: str | None = None,
    algorithm: str = "v1",
) -> dict[str, Any]:
    company = find_company(query)
    if not company:
        return {
            "company": None,
            "mode": "company",
            "error": "회사를 찾을 수 없습니다",
            "fallback": "keywords",
            "results": [],
            "pre_spec_results": [],
            "order_plan_results": [],
        }
    if company.get("is_restricted"):
        return {
            "company": company,
            "mode": "company",
            "error": "부정당 제재 회사입니다",
            "results": [],
            "pre_spec_results": [],
            "order_plan_results": [],
        }
    if not company.get("embedding"):
        return {
            "company": {
                "bizrno": company["bizrno"],
                "corp_nm": company["corp_nm"],
                "rgn_nm": company.get("rgn_nm"),
                "corp_bsns_div_nm": company.get("corp_bsns_div_nm"),
            },
            "mode": "company",
            "error": "회사 벡터가 아직 생성되지 않았습니다 (수주 이력 부족)",
            "fallback": "keywords",
            "results": [],
            "pre_spec_results": [],
            "order_plan_results": [],
        }

    # 회사 벡터 준비 — keywords 있으면 키워드 임베딩과 가중합
    raw_company_vec = company["embedding"]
    if isinstance(raw_company_vec, str):
        # pgvector "[a,b,...]" 문자열 → list[float]
        inner = raw_company_vec.strip()[1:-1]
        raw_company_vec = [float(x) for x in inner.split(",")] if inner else []

    keywords_text = (keywords or "").strip()
    if keywords_text:
        keyword_vec = embed_texts([f"관심 영역: {keywords_text}"])[0]
        blended = _blend_embeddings(raw_company_vec, keyword_vec)
        embedding_str = vector_to_pgvector_str(blended)
    else:
        embedding_str = vector_to_pgvector_str(raw_company_vec)

    client = get_admin_client()
    company_terms = _fetch_company_terms(client, company["bizrno"])
    company_industry_names = _fetch_company_industry_names(client, company["bizrno"])
    bizrno_norm = "".join(ch for ch in company["bizrno"] if ch.isdigit())
    company_institutions, company_amt_median = _fetch_company_history(client, bizrno_norm)

    ranked = _search_with_embedding(
        embedding_str,
        company.get("rgn_nm"),
        limit,
        candidate_pool,
        company_terms=company_terms,
        company_institutions=company_institutions,
        company_amt_median=company_amt_median,
        company_industry_names=company_industry_names,
        algorithm=algorithm,
        company_bizrno_norm=bizrno_norm,
    )
    pre_specs = _search_pre_specs(embedding_str, limit, candidate_pool)
    order_plans = _search_order_plans(embedding_str, limit, candidate_pool)

    # viz 좌표 — 회사 벡터(블렌딩 전 원본)와 TOP N 결과 임베딩을 anchor 좌표에 투영
    try:
        result_embs = _fetch_result_embeddings(client, ranked[:VIZ_RESULT_LIMIT])
        viz = _build_viz(raw_company_vec, ranked, result_embs)
    except Exception:  # 시각화 실패해도 본 응답은 영향 없음
        viz = None

    return {
        "company": {
            "bizrno": company["bizrno"],
            "corp_nm": company["corp_nm"],
            "rgn_nm": company.get("rgn_nm"),
            "corp_bsns_div_nm": company.get("corp_bsns_div_nm"),
        },
        "mode": "company",
        "algorithm": algorithm,
        "keywords": keywords_text or None,
        "results": ranked,
        "pre_spec_results": pre_specs,
        "order_plan_results": order_plans,
        "viz": viz,
    }

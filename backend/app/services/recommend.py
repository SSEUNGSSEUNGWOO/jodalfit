"""추천 비즈니스 로직.

두 가지 모드:
- mode="company": 회사명/사업자번호 → 회사 벡터로 매칭 (기본)
- mode="keywords": 관심 키워드 텍스트 → 직접 임베딩으로 매칭 (콜드스타트 대응)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from app.services.openai_client import embed_texts, vector_to_pgvector_str
from app.services.supabase_client import get_admin_client


def find_company(query: str) -> dict | None:
    """회사명 또는 사업자번호로 식별. 가장 매칭 좋은 1개 반환."""
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
    if not res.data:
        return None
    top = res.data[0]
    full = (
        client.table("companies")
        .select(
            "bizrno,corp_nm,english_nm,ceo_nm,corp_bsns_div_nm,rgn_nm,embedding,is_restricted"
        )
        .eq("bizrno", top["bizrno"])
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


def _search_with_embedding(
    embedding_str: str,
    company_rgn: str | None,
    limit: int,
    candidate_pool: int,
    company_terms: set[str] | None = None,
    company_institutions: set[str] | None = None,
    company_amt_median: float | None = None,
    company_industry_names: set[str] | None = None,
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
        deduped.append(r)
        if len(deduped) >= candidate_pool:
            break
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
) -> dict[str, Any]:
    """추천 메인 진입점.

    company 모드: query는 회사명/사업자번호
    keywords 모드: query는 자유 텍스트
    auto 모드: 입력 자동 감지 + 회사/키워드 결과 둘 다 반환 (UI 탭)
    """
    if mode == "auto":
        return _recommend_auto(query, limit, candidate_pool)
    if mode == "keywords":
        return _recommend_by_keywords(query, limit, candidate_pool)
    return _recommend_by_company(query, limit, candidate_pool)


def _recommend_auto(query: str, limit: int, candidate_pool: int) -> dict[str, Any]:
    """입력 자동 라우팅 + 양쪽 결과 합치기.

    - 숫자 10자리: 사업자번호 → company 모드만 (키워드 매칭 의미 없음)
    - 그 외: company + keywords 둘 다 호출, 회사 식별 실패해도 키워드 결과 반환
    """
    digits = "".join(ch for ch in query if ch.isdigit())
    is_bizrno = len(digits) == 10

    if is_bizrno:
        result = _recommend_by_company(query, limit, candidate_pool)
        result["mode"] = "auto"
        result["primary"] = "company"
        result["keyword_results"] = []
        return result

    # 텍스트 입력: 두 모드 병렬 실행 (단순 직렬, 비용 거의 동일)
    company_result = _recommend_by_company(query, limit, candidate_pool)
    keyword_result = _recommend_by_keywords(query, limit, candidate_pool)

    company_hit = bool(company_result.get("company")) and bool(company_result.get("results"))

    return {
        "mode": "auto",
        "primary": "company" if company_hit else "keywords",
        "company": company_result.get("company"),
        "results": company_result.get("results", []),  # 회사 매칭 (없으면 빈 배열)
        "keyword_query": query,
        "keyword_results": keyword_result.get("results", []),
        "error": None if company_hit or keyword_result.get("results") else "결과가 없습니다",
    }


def _recommend_by_keywords(
    query: str, limit: int, candidate_pool: int
) -> dict[str, Any]:
    text = query.strip()
    if not text:
        return {"company": None, "mode": "keywords", "error": "키워드를 입력해주세요", "results": []}

    embedding = embed_texts([f"관심 영역: {text}"])[0]
    embedding_str = vector_to_pgvector_str(embedding)
    ranked = _search_with_embedding(embedding_str, None, limit, candidate_pool)

    return {
        "company": None,
        "mode": "keywords",
        "query": text,
        "results": ranked,
    }


def _recommend_by_company(
    query: str, limit: int, candidate_pool: int
) -> dict[str, Any]:
    company = find_company(query)
    if not company:
        return {
            "company": None,
            "mode": "company",
            "error": "회사를 찾을 수 없습니다",
            "fallback": "keywords",
            "results": [],
        }
    if company.get("is_restricted"):
        return {
            "company": company,
            "mode": "company",
            "error": "부정당 제재 회사입니다",
            "results": [],
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
        }

    embedding = company["embedding"]
    if isinstance(embedding, list):
        embedding = vector_to_pgvector_str(embedding)

    client = get_admin_client()
    company_terms = _fetch_company_terms(client, company["bizrno"])
    company_industry_names = _fetch_company_industry_names(client, company["bizrno"])
    bizrno_norm = "".join(ch for ch in company["bizrno"] if ch.isdigit())
    company_institutions, company_amt_median = _fetch_company_history(client, bizrno_norm)

    ranked = _search_with_embedding(
        embedding,
        company.get("rgn_nm"),
        limit,
        candidate_pool,
        company_terms=company_terms,
        company_institutions=company_institutions,
        company_amt_median=company_amt_median,
        company_industry_names=company_industry_names,
    )

    return {
        "company": {
            "bizrno": company["bizrno"],
            "corp_nm": company["corp_nm"],
            "rgn_nm": company.get("rgn_nm"),
            "corp_bsns_div_nm": company.get("corp_bsns_div_nm"),
        },
        "mode": "company",
        "results": ranked,
    }

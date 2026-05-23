"""추천 비즈니스 로직.

파이프라인: 회사 식별 → 회사 벡터 → 하드필터 + 코사인 TOP100 → rerank → TOP N
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.openai_client import vector_to_pgvector_str
from app.services.supabase_client import get_admin_client


def find_company(query: str) -> dict | None:
    """회사명 또는 사업자번호로 식별. 가장 매칭 좋은 1개 반환."""
    client = get_admin_client()
    # 사업자번호 형식이면 직접 조회
    digits = "".join(ch for ch in query if ch.isdigit())
    if len(digits) == 10:
        res = (
            client.table("companies")
            .select("bizrno,corp_nm,english_nm,ceo_nm,corp_bsns_div_nm,rgn_nm,embedding,is_restricted")
            .eq("bizrno_norm", digits)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]

    # 회사명 fuzzy
    res = client.rpc("find_companies", {"query_name": query, "max_count": 1}).execute()
    if not res.data:
        return None
    top = res.data[0]
    full = (
        client.table("companies")
        .select("bizrno,corp_nm,english_nm,ceo_nm,corp_bsns_div_nm,rgn_nm,embedding,is_restricted")
        .eq("bizrno", top["bizrno"])
        .limit(1)
        .execute()
    )
    return full.data[0] if full.data else None


def rerank(rows: list[dict], company: dict) -> list[dict]:
    """휴리스틱 가산점 적용.

    - 준비 기간: 마감까지 0~1일 강패널티, 6~14일 +0.05
    - 지역 매칭: 공고 prtcpt_psbl_rgn_nm 에 회사 지역 포함시 +0.05
    """
    today = date.today()
    company_rgn = (company.get("rgn_nm") or "").split()[0] if company.get("rgn_nm") else None
    for r in rows:
        bonus = 0.0
        clse = r.get("bid_clse_date")
        if clse:
            clse_dt = date.fromisoformat(clse) if isinstance(clse, str) else clse
            days_left = (clse_dt - today).days
            if days_left <= 1:
                bonus -= 0.20
            elif 6 <= days_left <= 14:
                bonus += 0.05

        if company_rgn and r.get("prtcpt_psbl_rgn_nm"):
            if company_rgn in r["prtcpt_psbl_rgn_nm"]:
                bonus += 0.05

        r["base_similarity"] = r.get("similarity", 0)
        r["bonus"] = bonus
        r["score"] = r["base_similarity"] + bonus

    return sorted(rows, key=lambda r: r["score"], reverse=True)


def recommend(query: str, limit: int = 5, candidate_pool: int = 100) -> dict[str, Any]:
    """추천 메인 진입점."""
    company = find_company(query)
    if not company:
        return {"company": None, "error": "회사를 찾을 수 없습니다", "results": []}
    if company.get("is_restricted"):
        return {"company": company, "error": "부정당 제재 회사입니다", "results": []}
    if not company.get("embedding"):
        return {"company": company, "error": "회사 벡터가 아직 생성되지 않았습니다 (수주 이력 부족)", "results": []}

    client = get_admin_client()
    embedding = company["embedding"]
    if isinstance(embedding, list):
        embedding = vector_to_pgvector_str(embedding)

    res = client.rpc(
        "match_bid_notices",
        {
            "query_embedding": embedding,
            "match_count": candidate_pool,
            "min_clse_date": date.today().isoformat(),
        },
    ).execute()
    candidates = res.data or []

    ranked = rerank(candidates, company)[:limit]
    return {
        "company": {
            "bizrno": company["bizrno"],
            "corp_nm": company["corp_nm"],
            "rgn_nm": company.get("rgn_nm"),
            "corp_bsns_div_nm": company.get("corp_bsns_div_nm"),
        },
        "results": ranked,
    }

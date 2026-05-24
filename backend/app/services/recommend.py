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


def rerank(rows: list[dict], company_rgn: str | None) -> list[dict]:
    today = date.today()
    rgn = company_rgn.split()[0] if company_rgn else None
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

        if rgn and r.get("prtcpt_psbl_rgn_nm"):
            if rgn in r["prtcpt_psbl_rgn_nm"]:
                bonus += 0.05

        r["base_similarity"] = r.get("similarity", 0)
        r["bonus"] = bonus
        r["score"] = r["base_similarity"] + bonus

    return sorted(rows, key=lambda r: r["score"], reverse=True)


def _search_with_embedding(
    embedding_str: str,
    company_rgn: str | None,
    limit: int,
    candidate_pool: int,
) -> list[dict]:
    client = get_admin_client()
    res = client.rpc(
        "match_bid_notices",
        {
            "query_embedding": embedding_str,
            "match_count": candidate_pool,
            "min_clse_date": date.today().isoformat(),
        },
    ).execute()
    candidates = res.data or []
    return rerank(candidates, company_rgn)[:limit]


def recommend(
    query: str,
    limit: int = 5,
    candidate_pool: int = 100,
    mode: Literal["company", "keywords"] = "company",
) -> dict[str, Any]:
    """추천 메인 진입점.

    company 모드: query는 회사명/사업자번호
    keywords 모드: query는 자유 텍스트(관심 영역). 회사 식별 안 함.
    """
    if mode == "keywords":
        return _recommend_by_keywords(query, limit, candidate_pool)
    return _recommend_by_company(query, limit, candidate_pool)


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

    ranked = _search_with_embedding(
        embedding, company.get("rgn_nm"), limit, candidate_pool
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

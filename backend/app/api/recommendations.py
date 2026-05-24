"""추천 API 엔드포인트."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.explain import explain_batch
from app.services.recommend import recommend

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="회사명/사업자번호 또는 관심 키워드")
    mode: Literal["company", "keywords"] = Field(
        "company", description="company: 회사 벡터 매칭 / keywords: 키워드 직접 임베딩"
    )
    limit: int = Field(5, ge=1, le=20)
    candidate_pool: int = Field(100, ge=10, le=500)
    with_explanation: bool = Field(False, description="LLM 추천 이유 생성 (OpenAI 비용 발생)")


@router.post("")
def post_recommendations(req: RecommendRequest):
    result = recommend(
        req.query,
        limit=req.limit,
        candidate_pool=req.candidate_pool,
        mode=req.mode,
    )

    # fallback이 가능한 에러는 404 대신 200 + payload로 반환 (프론트에서 분기)
    if result.get("error") and not result.get("results") and not result.get("fallback"):
        raise HTTPException(status_code=404, detail=result["error"])

    if req.with_explanation and result.get("results"):
        # company 모드: company 정보 전달 / keywords 모드: query 텍스트 전달
        ctx = result.get("company") or {
            "corp_nm": f"키워드: {req.query}",
            "corp_bsns_div_nm": req.query,
        }
        explanations = explain_batch(ctx, result["results"])
        for r, ex in zip(result["results"], explanations):
            r["explanation"] = ex

    return result

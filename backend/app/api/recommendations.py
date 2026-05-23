"""추천 API 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.explain import explain_batch
from app.services.recommend import recommend

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="회사명 또는 사업자번호")
    limit: int = Field(5, ge=1, le=20)
    candidate_pool: int = Field(100, ge=10, le=500)
    with_explanation: bool = Field(False, description="LLM 추천 이유 생성 (OpenAI 비용 발생)")


@router.post("")
def post_recommendations(req: RecommendRequest):
    result = recommend(req.query, limit=req.limit, candidate_pool=req.candidate_pool)
    if result.get("error") and not result.get("results"):
        raise HTTPException(status_code=404, detail=result["error"])

    if req.with_explanation and result.get("results"):
        explanations = explain_batch(result["company"], result["results"])
        for r, ex in zip(result["results"], explanations):
            r["explanation"] = ex

    return result

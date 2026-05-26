"""추천 API 엔드포인트."""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.explain import explain_batch, explain_keyword_batch
from app.services.recommend import recommend
from app.services.search_log import log_search

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="회사명/사업자번호 또는 관심 키워드")
    mode: Literal["company", "keywords", "auto"] = Field(
        "company",
        description="company: 회사 벡터 / keywords: 키워드 직접 임베딩 / auto: 자동 라우팅 + 양쪽 결과",
    )
    limit: int = Field(20, ge=1, le=40)
    candidate_pool: int = Field(200, ge=10, le=500)
    explain_top: int = Field(
        5, ge=0, le=10, description="LLM 설명은 상위 explain_top건만 (비용 절약)"
    )
    with_explanation: bool = Field(False, description="LLM 추천 이유 생성 (OpenAI 비용 발생)")


@router.post("")
def post_recommendations(
    req: RecommendRequest,
    request: Request,
    background: BackgroundTasks,
):
    t0 = time.time()
    result = recommend(
        req.query,
        limit=req.limit,
        candidate_pool=req.candidate_pool,
        mode=req.mode,
    )

    has_any_results = bool(result.get("results") or result.get("keyword_results"))
    error_404 = (
        result.get("error")
        and not has_any_results
        and not result.get("fallback")
    )

    if not error_404 and req.with_explanation and req.explain_top > 0:
        # 회사 모드 결과 → 회사 컨텍스트 기반 설명
        # 키워드/회사식별실패 → 키워드 기반 설명 (회사 호칭 안 씀)
        if result.get("results"):
            top_results = result["results"][: req.explain_top]
            if result.get("company"):
                explanations = explain_batch(result["company"], top_results)
            else:
                explanations = explain_keyword_batch(req.query, top_results)
            for r, ex in zip(top_results, explanations):
                r["explanation"] = ex
        # auto 모드 키워드 결과(보조)도 키워드 기반 설명
        if result.get("keyword_results"):
            top_kw = result["keyword_results"][: req.explain_top]
            kw_explanations = explain_keyword_batch(req.query, top_kw)
            for r, ex in zip(top_kw, kw_explanations):
                r["explanation"] = ex

    company = result.get("company") or {}
    background.add_task(
        log_search,
        query=req.query,
        mode=req.mode,
        matched_bizrno=company.get("bizrno"),
        matched_corp_nm=company.get("corp_nm"),
        result_count=len(result.get("results") or []),
        kw_result_count=len(result.get("keyword_results") or []),
        has_error=bool(result.get("error")),
        error_msg=result.get("error"),
        with_explanation=req.with_explanation,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        latency_ms=int((time.time() - t0) * 1000),
    )

    if error_404:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

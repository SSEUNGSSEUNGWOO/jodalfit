"""자격 판정 라벨 API — 검색 결과(또는 아무 공고 목록)에 "이 회사가 낼 수 있는가"를 붙인다.

추천 파이프라인(app/recommender/qualifications.py::check_qualifications)의 판정을 그대로 재사용한다.
하드 제외가 아니라 라벨용: 호출부(조건 검색 페이지)가 결과를 걸러내지 않고 passed/failures 를 표시한다.
검색 RPC(0050 search_bid_notices)에 회사 식별자를 넣지 않는 이유 — total_count 가 안 흔들리고, 자격 규칙이
바뀌어도 SQL 을 안 건드린다.

POST /qualifications/check  {"bizrno": "123-45-67890", "bid_ntce_nos": ["R26BK...", ...]}  (최대 50)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.bot_guard import guard_external_traffic
from app.core.rate_limit import limiter
from app.recommender.qualifications import check_qualifications
from app.services.recommend import _fetch_company_terms, _fetch_eligibility, _row_by_norm
from app.services.supabase_client import get_admin_client

router = APIRouter(prefix="/qualifications", tags=["qualifications"])

MAX_NOTICES = 50


class QualificationCheckRequest(BaseModel):
    bizrno: str = Field(..., min_length=10, max_length=20, description="사업자번호 (하이픈 유무 무관)")
    bid_ntce_nos: list[str] = Field(..., min_length=1, max_length=MAX_NOTICES, description="공고번호 목록")


class NoticeQualification(BaseModel):
    bid_ntce_no: str
    bid_ntce_ord: str
    passed: bool
    unverified: bool
    reasons: list[str]
    failures: list[str]


class QualificationCheckResponse(BaseModel):
    bizrno: str
    corp_nm: str | None
    results: list[NoticeQualification]
    missing: list[str] = Field(default_factory=list, description="bid_notices 에 없는 공고번호")


@router.post("/check", dependencies=[Depends(guard_external_traffic)])
@limiter.limit("30/minute;300/day")
def post_check(request: Request, req: QualificationCheckRequest) -> QualificationCheckResponse:
    client = get_admin_client()
    company = _row_by_norm(client, req.bizrno)
    if not company:
        raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다")
    _, industry_names, _ = _fetch_company_terms(client, company["bizrno"])
    company_rgn = company.get("rgn_nm")

    # 같은 공고번호의 여러 차수 중 최신 차수 하나 — 추천·목록과 같은 규칙
    wanted = list(dict.fromkeys(n.strip() for n in req.bid_ntce_nos if n.strip()))
    rows = (
        client.table("bid_notices")
        .select("bid_ntce_no,bid_ntce_ord")
        .in_("bid_ntce_no", wanted)
        .execute()
        .data
        or []
    )
    latest: dict[str, str] = {}
    for r in rows:
        if r["bid_ntce_ord"] >= latest.get(r["bid_ntce_no"], ""):
            latest[r["bid_ntce_no"]] = r["bid_ntce_ord"]
    bid_keys = [(no, latest[no]) for no in wanted if no in latest]
    elig = _fetch_eligibility(client, bid_keys)

    results = []
    for no, ord_ in bid_keys:
        slot = elig.get((no, ord_)) or {"licenses": [], "regions": []}
        q = check_qualifications(industry_names, company_rgn, slot["licenses"], slot["regions"])
        results.append(NoticeQualification(bid_ntce_no=no, bid_ntce_ord=ord_, **q))
    return QualificationCheckResponse(
        bizrno=company["bizrno"],
        corp_nm=company.get("corp_nm"),
        results=results,
        missing=[no for no in wanted if no not in latest],
    )

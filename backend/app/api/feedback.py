"""의견·문의·오류 제보 수신 — /feedback 폼 (0061 feedback).

가입 없이 보낼 수 있다. 봇 차단(guard_external_traffic)·IP 요청 제한·허니팟(website 칸이 차 있으면 조용히 버림)으로
스팸을 거른다. 답장 주소(email)는 선택. 읽는 쪽은 프론트 /admin(service_role).
"""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.bot_guard import guard_external_traffic
from app.core.rate_limit import limiter
from app.services.search_log import _hash_ip
from app.services.supabase_client import get_admin_client

router = APIRouter(prefix="/feedback", tags=["feedback"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FeedbackRequest(BaseModel):
    kind: Literal["idea", "question", "bug"]
    message: str = Field(..., min_length=5, max_length=2000)
    email: str | None = Field(None, max_length=200)
    page: str | None = Field(None, max_length=500)
    website: str | None = Field(None, max_length=200)   # 허니팟 — 사람은 비워 둔다(화면에 없음)


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("", dependencies=[Depends(guard_external_traffic)])
@limiter.limit("5/minute;30/day")
def post_feedback(request: Request, req: FeedbackRequest):
    if req.website:
        return {"ok": True}   # 봇 — 저장하지 않고 성공처럼 응답
    email = (req.email or "").strip() or None
    if email and not _EMAIL.match(email):
        email = None
    get_admin_client().table("feedback").insert(
        {
            "kind": req.kind,
            "message": req.message.strip(),
            "email": email,
            "page": (req.page or "").strip()[:500] or None,
            "ip_hash": _hash_ip(_client_ip(request)),
            "user_agent": (request.headers.get("user-agent") or "")[:500] or None,
        }
    ).execute()
    return {"ok": True}

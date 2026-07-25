"""프론트 행동 이벤트 수신 (click 등) — 경량 fire-and-forget."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field

from app.core.bot_guard import guard_external_traffic
from app.core.rate_limit import limiter
from app.services.notice_events import log_notice_events

router = APIRouter(prefix="/events", tags=["events"])


class NoticeEventRequest(BaseModel):
    session_id: str | None = Field(None, max_length=64)
    target_bizrno: str | None = Field(None, max_length=20)
    event_type: Literal["click", "save", "dismiss", "subscribe"]
    bid_ntce_no: str = Field(..., min_length=1, max_length=40)
    bid_ntce_ord: str | None = Field(None, max_length=10)
    rank_position: int | None = Field(None, ge=1, le=100)
    algorithm_version: str | None = Field(None, max_length=20)
    score: float | None = None


@router.post("", dependencies=[Depends(guard_external_traffic)])
@limiter.limit("60/minute")
def post_notice_event(
    request: Request,
    req: NoticeEventRequest,
    background: BackgroundTasks,
):
    background.add_task(log_notice_events, [req.model_dump()])
    return {"ok": True}

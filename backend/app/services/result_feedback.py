"""결과 화면 "도움이 됐습니까" 응답 저장 (0063 result_feedback). 실패해도 요청에는 영향 없다(백그라운드)."""

from __future__ import annotations

import logging

from app.services.supabase_client import get_admin_client

logger = logging.getLogger(__name__)


def log_result_feedback(row: dict) -> None:
    try:
        get_admin_client().table("result_feedback").insert(row).execute()
    except Exception as e:  # 0063 미적용 등 — 조용히 넘어간다
        logger.warning("result_feedback insert failed: %s", e)

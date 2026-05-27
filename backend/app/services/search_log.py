"""사용자 검색 로그 — fire-and-forget 저장.

추천 응답 흐름과 분리되어야 하므로 실패 시 silent (raise X).
"""

from __future__ import annotations

import hashlib

from app.core.config import get_settings
from app.services.supabase_client import get_admin_client


def _hash_ip(ip: str | None) -> str | None:
    """IPv4 주소 공간(~4B)은 솔트 없는 sha256이면 사전계산 가능 → IP_HASH_SALT 필수."""
    if not ip:
        return None
    salt = get_settings().ip_hash_salt or ""
    return hashlib.sha256(f"{ip}{salt}".encode()).hexdigest()[:16]


def log_search(
    *,
    query: str,
    mode: str,
    matched_bizrno: str | None,
    matched_corp_nm: str | None,
    result_count: int,
    kw_result_count: int,
    has_error: bool,
    error_msg: str | None,
    with_explanation: bool,
    ip: str | None,
    user_agent: str | None,
    referer: str | None,
    latency_ms: int | None,
) -> None:
    try:
        get_admin_client().table("search_logs").insert(
            {
                "query": query[:500],
                "mode": mode,
                "matched_bizrno": matched_bizrno,
                "matched_corp_nm": matched_corp_nm,
                "result_count": result_count,
                "kw_result_count": kw_result_count,
                "has_error": has_error,
                "error_msg": (error_msg or "")[:500] or None,
                "with_explanation": with_explanation,
                "ip_hash": _hash_ip(ip),
                "user_agent": (user_agent or "")[:500] or None,
                "referer": (referer or "")[:500] or None,
                "latency_ms": latency_ms,
            }
        ).execute()
    except Exception:
        # fire-and-forget — 로깅 실패가 사용자 응답에 영향 주면 안 됨
        pass

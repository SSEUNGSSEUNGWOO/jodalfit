"""notice_events 로그 — fire-and-forget batch insert.

impression은 추천 응답 background task에서, click은 /events 엔드포인트에서 호출.
search_log와 마찬가지로 실패 시 silent.
"""

from __future__ import annotations

from app.services.supabase_client import get_admin_client

ALLOWED_EVENT_TYPES = {"impression", "click", "save", "dismiss", "subscribe"}


def log_notice_events(rows: list[dict]) -> None:
    clean = [
        {
            "session_id": (r.get("session_id") or "")[:64] or None,
            "target_bizrno": (r.get("target_bizrno") or "")[:20] or None,
            "event_type": r["event_type"],
            "bid_ntce_no": str(r["bid_ntce_no"])[:40],
            "bid_ntce_ord": (str(r.get("bid_ntce_ord") or ""))[:10] or None,
            "rank_position": r.get("rank_position"),
            "algorithm_version": (r.get("algorithm_version") or "")[:20] or None,
            "score": r.get("score"),
            "metadata": r.get("metadata"),
            "source": (r.get("source") or "user")[:16],
        }
        for r in rows
        if r.get("bid_ntce_no") and r.get("event_type") in ALLOWED_EVENT_TYPES
    ]
    if not clean:
        return
    try:
        get_admin_client().table("notice_events").insert(clean).execute()
    except Exception:
        pass


def log_impressions(
    results: list[dict],
    *,
    session_id: str | None,
    target_bizrno: str | None,
    algorithm_version: str,
    top_n: int = 20,
    source: str = "user",
) -> None:
    # 내부 SSR 렌더링마다 20건씩 쌓으면 실사용 지표와 무관하게 테이블만 커진다
    # (2026-09-18 확인: 누적 110만 건 중 사용자 행동은 save 3건). 사용자 요청만 남긴다.
    if source != "user":
        return
    log_notice_events(
        [
            {
                "session_id": session_id,
                "target_bizrno": target_bizrno,
                "event_type": "impression",
                "bid_ntce_no": r.get("bid_ntce_no"),
                "bid_ntce_ord": r.get("bid_ntce_ord"),
                "rank_position": i + 1,
                "algorithm_version": algorithm_version,
                "score": r.get("score"),
            }
            for i, r in enumerate(results[:top_n])
        ]
    )

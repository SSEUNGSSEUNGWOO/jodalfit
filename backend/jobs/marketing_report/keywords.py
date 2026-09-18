"""자동 키워드 — 실제 유입 검색어를 추적 목록에 올리고 내린다.

수동 목록(config.yaml keywords)은 그대로 두고, 그 위에 자동 목록을 매일 스냅샷에서 다시 계산한다 (별도 상태 파일 없음).
올리는 조건 (둘 중 하나):
  - 오늘 수집한 네이버 최근 7일 누적 상위 검색어에서 클릭 MIN_CLICKS_7D 이상
  - 네이버 일별 상위 검색어에 최근 LOOKBACK_DAYS 일 중 MIN_DAYS 일 이상 등장
내리는 조건: 위 조건에서 벗어나면 다음 계산에서 자연히 빠진다 (최대 LOOKBACK_DAYS 일 뒤).
상한 MAX_AUTO 개, 최근 클릭 합이 큰 순.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .compare import load_snapshot

MIN_CLICKS_7D = 2
MIN_DAYS = 2
LOOKBACK_DAYS = 14
MAX_AUTO = 40


def norm(q: str) -> str:
    return re.sub(r"\s+", " ", q).strip()


def auto_keywords(day: date, today_naver: dict | None, manual: list[str]) -> list[str]:
    manual_set = {norm(k) for k in manual}
    clicks: dict[str, int] = {}
    days_seen: dict[str, set[str]] = {}

    def seen(q: dict, d: str):
        k = norm(q["query"])
        days_seen.setdefault(k, set()).add(d)
        clicks[k] = clicks.get(k, 0) + q.get("clicks", 0)

    # 오늘 + 지난 스냅샷의 일별 상위 검색어
    if today_naver:
        for q in today_naver.get("top_queries", []):
            seen(q, today_naver.get("top_date") or day.isoformat())
    for back in range(1, LOOKBACK_DAYS):
        s = load_snapshot(day - timedelta(days=back))
        nv = (s or {}).get("naver") or {}
        for q in nv.get("top_queries", []):
            seen(q, nv.get("top_date") or (day - timedelta(days=back)).isoformat())

    picked: dict[str, int] = {}
    for q in (today_naver or {}).get("top_queries_7d", []):
        k = norm(q["query"])
        if q.get("clicks", 0) >= MIN_CLICKS_7D:
            picked[k] = max(picked.get(k, 0), q["clicks"])
    for k, ds in days_seen.items():
        if len(ds) >= MIN_DAYS:
            picked[k] = max(picked.get(k, 0), clicks.get(k, 0))

    ranked = sorted((k for k in picked if k not in manual_set), key=lambda k: (-picked[k], k))
    return ranked[:MAX_AUTO]


def tracked_from_top(top_queries: list[dict], keywords: list[str]) -> dict[str, dict | None]:
    """상위 검색어 목록에서 키워드별 순위. 목록에 없으면 None (= 노출 없음)."""
    by_q = {norm(q["query"]): q for q in top_queries}
    return {
        k: ({"position": by_q[k]["position"], "impressions": by_q[k]["impressions"], "clicks": by_q[k]["clicks"]}
            if k in by_q else None)
        for k in (norm(x) for x in keywords)
    }

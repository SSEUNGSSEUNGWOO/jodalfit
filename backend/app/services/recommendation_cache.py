"""회사 페이지 SSR 추천 결과 read-through 캐시.

`POST /recommendations`의 회사 모드(사업자번호 질의)만 대상으로 한다. 대화형
보드가 쓰는 `/stream`은 실사용자 경로라 항상 라이브로 둔다.

무효화는 시간이 아니라 내용 기준이다. 0018이 마감 지평선을 D+90으로 자르므로
저장된 공고는 90일 안에 전부 마감된다. 읽을 때 마감 지난 건을 걷어내고 남은
결과가 MIN_SURVIVING 미만이면 미스로 취급해 재계산시킨다.

캐시 조회·저장 실패는 전부 삼킨다. 캐시는 최적화지 정답의 출처가 아니다.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.services.supabase_client import get_admin_client

logger = logging.getLogger("jodalfit")

TABLE = "company_recommendations"
# 마감 제외 후 이만큼도 안 남으면 캐시가 낡은 것으로 보고 재계산한다.
MIN_SURVIVING = 5


def cache_key(query: str, mode: str, keywords: str | None, algorithm: str) -> str | None:
    """캐시 대상이면 bizrno_norm, 아니면 None.

    회사명 질의는 제외한다 — 식별 결과가 fuzzy 매칭에 달려 있어 질의 문자열을
    키로 쓰면 같은 회사가 여러 키로 흩어진다. SSR은 항상 사업자번호로 부르므로
    이 조건만으로 대상 트래픽을 모두 덮는다.
    """
    if mode != "company" or keywords or algorithm != "v2":
        return None
    digits = "".join(ch for ch in query if ch.isdigit())
    return digits if len(digits) == 10 else None


def _alive(value: Any, today: date) -> bool:
    """마감 필드가 오늘 이후인가. 값이 없으면 보수적으로 살린다."""
    if not value:
        return True
    text = str(value)[:10]
    try:
        return date.fromisoformat(text) >= today
    except ValueError:
        return True


def prune(payload: dict, today: date | None = None) -> dict:
    """마감 지난 항목을 걷어낸 사본 반환. 발주계획은 마감 개념이 없어 그대로 둔다."""
    today = today or date.today()
    out = dict(payload)

    results = [r for r in (payload.get("results") or []) if _alive(r.get("bid_clse_date"), today)]
    out["results"] = results

    out["pre_spec_results"] = [
        r
        for r in (payload.get("pre_spec_results") or [])
        if _alive(r.get("opnin_rgst_clse_dt"), today)
    ]

    viz = payload.get("viz")
    if viz and viz.get("results"):
        alive_keys = {(r.get("bid_ntce_no"), r.get("bid_ntce_ord")) for r in results}
        out["viz"] = dict(
            viz,
            results=[
                p for p in viz["results"]
                if (p.get("bid_ntce_no"), p.get("bid_ntce_ord")) in alive_keys
            ],
        )
    return out


def load(bizrno_norm: str, algorithm: str, limit: int) -> dict | None:
    """살아있는 캐시 페이로드. 없거나 낡았으면 None."""
    try:
        rows = (
            get_admin_client()
            .table(TABLE)
            .select("payload,result_limit")
            .eq("bizrno_norm", bizrno_norm)
            .eq("algorithm", algorithm)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as e:
        # 0019 미적용 등 — 캐시 없이 라이브로 간다.
        logger.warning("추천 캐시 조회 실패 (%s) — 라이브 계산", type(e).__name__)
        return None

    if not rows:
        return None
    row = rows[0]
    # 저장된 것보다 많이 요구하면 미스. 결과는 점수 내림차순이라 자르는 건 안전하다.
    if row.get("result_limit", 0) < limit:
        return None

    payload = prune(row.get("payload") or {})
    if len(payload.get("results") or []) < MIN_SURVIVING:
        return None

    payload["results"] = payload["results"][:limit]
    payload["cached"] = True
    return payload


def store(bizrno_norm: str, algorithm: str, limit: int, payload: dict) -> None:
    """계산 결과 저장. 실패해도 응답에는 영향이 없어야 한다."""
    try:
        get_admin_client().table(TABLE).upsert(
            {
                "bizrno_norm": bizrno_norm,
                "algorithm": algorithm,
                "result_limit": limit,
                "payload": payload,
                "computed_at": "now()",
            },
            on_conflict="bizrno_norm",
        ).execute()
    except Exception as e:
        logger.warning("추천 캐시 저장 실패 (%s)", type(e).__name__)

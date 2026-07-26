"""가중치 합산 점수 + 라벨 breakdown.

각 시그널은 {key, label, points} 형태로 breakdown에 남는다.
label은 그대로 프론트 배지가 되고(Phase 3), points 합이 raw score.
스케일: 벡터 유사도 0~100 기준. 프론트 표시용 정규화는 pipeline에서.
"""

from __future__ import annotations

import re
from datetime import date

TOKEN_SPLIT = re.compile(r"[\s,·/\-]+")


def _tokenize(s: str | None) -> set[str]:
    if not s:
        return set()
    return {t.strip() for t in TOKEN_SPLIT.split(s) if t.strip() and len(t.strip()) >= 2}


def score_notice(
    r: dict,
    *,
    company_rgn: str | None,
    company_terms: set[str],
    company_institutions: set[str],
    company_amt_median: float | None,
    today: date,
    peer_instt_counts: dict[str, int] | None = None,
    instt_stats: dict[str, dict] | None = None,
) -> tuple[float, list[dict]]:
    breakdown: list[dict] = []

    sim = float(r.get("similarity") or 0)
    breakdown.append({"key": "vector", "label": f"유사도 {round(sim * 100)}%", "points": round(100 * sim, 1)})

    instt = (r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "").strip()
    if instt and instt in company_institutions:
        breakdown.append({"key": "institution", "label": "재출현 기관", "points": 50, "instt": instt})
    elif instt and peer_instt_counts and instt in peer_instt_counts:
        # 재출현(+50)과 스택 방지 — 협업 시그널은 "발굴" 톤이라 미거래 기관에만
        cnt = peer_instt_counts[instt]
        pts = 80 if cnt >= 2 else 40
        breakdown.append({"key": "peer_institution", "label": "유사 회사 수주 기관", "points": pts, "peer_awards": cnt})

    if instt and instt_stats and instt in instt_stats:
        st = instt_stats[instt]
        total = st.get("total") or 0
        if total >= 10:
            repeat_ratio = 1 - (st.get("distinct_winners") or 0) / total
            if repeat_ratio >= 0.5:
                breakdown.append({"key": "instt_closed", "label": "고정 거래처 경향", "points": -20, "repeat_ratio": round(repeat_ratio, 2)})
            elif repeat_ratio <= 0.25:
                breakdown.append({"key": "instt_open", "label": "신규 진입 열린 기관", "points": 15, "repeat_ratio": round(repeat_ratio, 2)})

    sido = company_rgn.split()[0] if company_rgn else None
    if sido and r.get("prtcpt_psbl_rgn_nm") and sido in r["prtcpt_psbl_rgn_nm"]:
        breakdown.append({"key": "region", "label": "지역 매칭", "points": 30, "rgn": sido})

    if company_amt_median and company_amt_median > 0:
        price = r.get("presmpt_prce") or r.get("asign_bdgt_amt")
        if price and price > 0:
            ratio = price / company_amt_median
            if 0.7 <= ratio <= 1.5:
                breakdown.append({"key": "budget", "label": "예산대 매칭", "points": 20, "ratio": round(ratio, 2)})
            elif ratio < 0.1 or ratio > 10.0:
                breakdown.append({"key": "budget_mismatch", "label": "예산대 괴리", "points": -15, "ratio": round(ratio, 2)})

    if company_terms:
        notice_terms = _tokenize(r.get("bidprc_psbl_indstryty_nm")) | _tokenize(r.get("bid_ntce_nm"))
        overlap = sorted(company_terms & notice_terms)
        if overlap:
            pts = min(10 * len(overlap), 30)
            breakdown.append({"key": "industry_tokens", "label": "업종·물품 일치", "points": pts, "matched": overlap[:5]})

    clse = r.get("bid_clse_date")
    if clse:
        clse_dt = date.fromisoformat(clse) if isinstance(clse, str) else clse
        days_left = (clse_dt - today).days
        if days_left <= 1:
            breakdown.append({"key": "deadline_urgent", "label": "마감 임박", "points": -30, "days_left": days_left})
        elif 6 <= days_left <= 14:
            breakdown.append({"key": "deadline_ok", "label": "검토 여유", "points": 10, "days_left": days_left})

    return sum(b["points"] for b in breakdown), breakdown

"""Picks 큐레이션 + Market 통계 (LLM 없음, 순수 룰)."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date


_PRIVATE_TOKENS = ("주식회사", "(주)", "㈜", "유한회사", "유한책임회사", "합자회사", "합명회사")

_INSTT_BLACKLIST = {
    "각 수요기관",
    "수요기관",
    "수요처",
    "각수요기관",
    "각 기관",
}


def is_private_org(name: str | None) -> bool:
    if not name:
        return False
    return any(tok in name for tok in _PRIVATE_TOKENS)


def institution_ok(name: str | None) -> bool:
    if not name:
        return False
    if name.strip() in _INSTT_BLACKLIST:
        return False
    if is_private_org(name):
        return False
    return True


def name_key(nm: str | None) -> str:
    if not nm:
        return ""
    s = nm
    s = re.sub(r"\(재공고\)|\(긴급\)|\(공동\)|\(2차\)|\(3차\)|\(4차\)|\(5차\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:30]


def format_amount(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.1f}조"
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v / 10_000:.0f}만"
    return f"{int(v):,}"


def days_until(date_str: str | None, ref: date) -> int | None:
    if not date_str:
        return None
    try:
        d = date.fromisoformat(date_str[:10])
    except Exception:
        return None
    return (d - ref).days


def pick_top10(notices: list[dict], today: date) -> list[dict]:
    candidates = []
    for n in notices:
        instt = n.get("dmnd_instt_nm") or n.get("ntce_instt_nm")
        if not institution_ok(instt):
            continue
        price = n.get("presmpt_prce") or n.get("asign_bdgt_amt") or 0
        if price and price < 100_000_000:
            continue
        d = days_until(n.get("bid_clse_date"), today)
        if d is None or d < 0:
            continue
        candidates.append(
            {**n, "_dday": d, "_price": price or 0, "_key": name_key(n.get("bid_ntce_nm"))}
        )

    def score(n):
        price_score = min(n["_price"] / 1_000_000_000, 5.0)
        d = n["_dday"]
        if d < 3:
            dday_score = 0.3
        elif d <= 14:
            dday_score = 1.0
        elif d <= 30:
            dday_score = 0.7
        else:
            dday_score = 0.4
        return price_score * dday_score

    candidates.sort(key=score, reverse=True)

    picked: list[dict] = []
    inst_count: Counter = Counter()
    bsns_count: Counter = Counter()
    seen_keys: set[str] = set()
    for c in candidates:
        if c["_key"] and c["_key"] in seen_keys:
            continue
        instt = c.get("dmnd_instt_nm") or c.get("ntce_instt_nm") or "—"
        bsns = c.get("bsns_div_nm") or "—"
        if inst_count[instt] >= 1:
            continue
        if bsns_count[bsns] >= 5:
            continue
        picked.append(c)
        if c["_key"]:
            seen_keys.add(c["_key"])
        inst_count[instt] += 1
        bsns_count[bsns] += 1
        if len(picked) >= 10:
            break
    return picked


MIN_PREV_FOR_WOW = 200


def market_stats(notices: list[dict], prev_notices: list[dict]) -> dict:
    total = len(notices)
    prev_total = len(prev_notices)
    wow_reliable = prev_total >= MIN_PREV_FOR_WOW
    wow = ((total - prev_total) / prev_total * 100) if (prev_total and wow_reliable) else None

    bsns_counter: Counter = Counter()
    instt_counter: Counter = Counter()
    prices: list[float] = []

    for n in notices:
        bsns = n.get("bsns_div_nm") or "기타"
        bsns_counter[bsns] += 1
        instt = n.get("dmnd_instt_nm") or n.get("ntce_instt_nm")
        if institution_ok(instt):
            instt_counter[instt] += 1
        p = n.get("presmpt_prce") or n.get("asign_bdgt_amt")
        if p:
            prices.append(float(p))

    buckets = {
        "1억 미만": 0,
        "1억~10억": 0,
        "10억~50억": 0,
        "50억~100억": 0,
        "100억 이상": 0,
    }
    for p in prices:
        if p < 100_000_000:
            buckets["1억 미만"] += 1
        elif p < 1_000_000_000:
            buckets["1억~10억"] += 1
        elif p < 5_000_000_000:
            buckets["10억~50억"] += 1
        elif p < 10_000_000_000:
            buckets["50억~100억"] += 1
        else:
            buckets["100억 이상"] += 1

    avg_price = sum(prices) / len(prices) if prices else 0
    median_price = sorted(prices)[len(prices) // 2] if prices else 0

    return {
        "total": total,
        "prev_total": prev_total,
        "wow_pct": wow,
        "wow_reliable": wow_reliable,
        "bsns_dist": bsns_counter.most_common(),
        "top_institutions": instt_counter.most_common(10),
        "price_buckets": buckets,
        "price_sample_count": len(prices),
        "avg_price": avg_price,
        "median_price": median_price,
    }

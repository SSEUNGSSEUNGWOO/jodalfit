"""Supabase에서 주간 공고 데이터 가져오기."""

from __future__ import annotations

from datetime import date


def fetch_window_notices(client, start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    PAGE = 1000
    while True:
        r = (
            client.table("bid_notices")
            .select(
                "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bid_ntce_date,bid_clse_date,"
                "presmpt_prce,asign_bdgt_amt,dmnd_instt_nm,ntce_instt_nm,bidprc_psbl_indstryty_nm,"
                "prtcpt_psbl_rgn_nm,bid_ntce_url"
            )
            .gte("bid_ntce_date", start.isoformat())
            .lte("bid_ntce_date", end.isoformat())
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not r:
            break
        rows.extend(r)
        if len(r) < PAGE:
            break
        offset += PAGE
    return rows


def dedupe_by_no(rows: list[dict]) -> list[dict]:
    by_no: dict[str, dict] = {}
    for r in rows:
        n = r.get("bid_ntce_no")
        if not n:
            continue
        prev = by_no.get(n)
        if prev is None or (r.get("bid_ntce_ord") or "") > (prev.get("bid_ntce_ord") or ""):
            by_no[n] = r
    return list(by_no.values())

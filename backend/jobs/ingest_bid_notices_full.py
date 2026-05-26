"""BidPublicInfoService 기반 과거 입찰공고 백필 — 4 endpoint × 30일 윈도우.

기존 ingest_bid_notices.py가 사용하는 PubDataOpnStdService는 1주 윈도우 한도라
과거 백필 불가. BidPublicInfoService는 30일 윈도우 + 4개 endpoint(용역/물품/공사/외자)
나눠져 있고 응답 컬럼명이 약간 달라 별도 mapper.

bid_notices에 upsert (`ignore_duplicates=True`)로 기존 데이터 보존.

실행:
    cd backend
    uv run python -m jobs.ingest_bid_notices_full --months 1   # 한 달치 probe
    uv run python -m jobs.ingest_bid_notices_full --months 12  # 1년치 풀
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Any

from app.services.supabase_client import upsert_rows
from jobs._common import (
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_date,
    to_int,
    to_yn,
)

BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
ENDPOINTS = {
    "용역": f"{BASE}/getBidPblancListInfoServc",
    "물품": f"{BASE}/getBidPblancListInfoThng",
    "공사": f"{BASE}/getBidPblancListInfoCnstwk",
    "외자": f"{BASE}/getBidPblancListInfoFrgcpt",
}
JOB_NAME = "ingest_bid_notices_full"

DATE_FMT = "%Y%m%d%H%M"


def map_item(it: dict, bsns_div: str) -> dict[str, Any]:
    """BidPublicInfoService 응답을 bid_notices 스키마로 매핑.

    PubDataOpnStdService와 컬럼명 다름:
      bidNtceDt vs bidNtceDate, bidClseDt vs bidClseDate, opengDt vs opengDate,
      dminsttCd vs dmndInsttCd, dminsttNm vs dmndInsttNm,
      cmmnSpldmdCorpRgnLmtYn vs rgnLmtYn,
      bidPrtcptLmtYn vs indstrytyLmtYn.
    bsns_div_nm은 endpoint URL이 정보를 주므로 인자로 주입.
    """
    return {
        "bid_ntce_no": it.get("bidNtceNo"),
        "bid_ntce_ord": it.get("bidNtceOrd") or "000",
        "bid_ntce_nm": it.get("bidNtceNm"),
        "bsns_div_nm": bsns_div,
        "bid_ntce_date": to_date(it.get("bidNtceDt")),
        "bid_clse_date": to_date(it.get("bidClseDt")),
        "openg_date": to_date(it.get("opengDt")),
        "presmpt_prce": to_int(it.get("presmptPrce")),
        "asign_bdgt_amt": to_int(it.get("asignBdgtAmt")),
        "ntce_instt_cd": it.get("ntceInsttCd"),
        "ntce_instt_nm": it.get("ntceInsttNm"),
        "dmnd_instt_cd": it.get("dminsttCd"),
        "dmnd_instt_nm": it.get("dminsttNm"),
        "bidwinr_dcsn_mthd_nm": it.get("bidwinrDcsnMthdNm"),
        "cntrct_cncls_mthd_nm": it.get("cntrctCnclsMthdNm"),
        "bid_ntce_url": it.get("bidNtceUrl"),
        "rgn_lmt_yn": to_yn(it.get("cmmnSpldmdCorpRgnLmtYn")),
        "indstryty_lmt_yn": to_yn(it.get("bidPrtcptLmtYn")),
        "raw": it,
    }


def windows(
    end: datetime,
    *,
    months: int | None = None,
    since: datetime | None = None,
    win_days: int = 30,
) -> list[tuple[datetime, datetime]]:
    """end에서 과거로 win_days 윈도우 N개. months 또는 since 중 하나로 끝점 지정."""
    if since is not None:
        start_floor = since
    elif months is not None:
        start_floor = end - timedelta(days=months * 30)
    else:
        raise ValueError("months 또는 since 둘 중 하나는 필요")
    out: list[tuple[datetime, datetime]] = []
    cursor = end
    while cursor > start_floor:
        win_start = max(cursor - timedelta(days=win_days), start_floor)
        out.append((win_start, cursor))
        cursor = win_start
    return out


def run_one_window(
    label: str, url: str, begin: datetime, end: datetime, batch_size: int
) -> int:
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    total = 0
    batch: list[dict] = []
    for it in iter_all_items(url, extra, rows_per_page=500, max_pages=200):
        row = map_item(it, label)
        if not row["bid_ntce_no"] or not row["bid_ntce_nm"]:
            continue
        batch.append(row)
        if len(batch) >= batch_size:
            upsert_rows(
                "bid_notices",
                batch,
                on_conflict="bid_ntce_no,bid_ntce_ord",
                ignore_duplicates=True,
            )
            total += len(batch)
            batch.clear()
    if batch:
        upsert_rows(
            "bid_notices",
            batch,
            on_conflict="bid_ntce_no,bid_ntce_ord",
            ignore_duplicates=True,
        )
        total += len(batch)
    return total


def run(
    months: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    win_days: int = 30,
    batch_size: int = 500,
) -> None:
    end = until or datetime.now()
    wins = windows(end, months=months, since=since, win_days=win_days)
    run_id = log_ingest_start(
        JOB_NAME,
        {
            "months": months,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "win_days": win_days,
            "windows": len(wins),
        },
    )
    print(
        f"[{JOB_NAME}] windows={len(wins)} "
        f"range={wins[-1][0].strftime('%Y-%m-%d')} ~ {wins[0][1].strftime('%Y-%m-%d')}"
    )

    grand_total = 0
    try:
        for i, (begin, win_end) in enumerate(wins, 1):
            print(
                f"\n[window {i}/{len(wins)}] {begin.strftime('%Y-%m-%d')} ~ {win_end.strftime('%Y-%m-%d')}"
            )
            for label, url in ENDPOINTS.items():
                n = run_one_window(label, url, begin, win_end, batch_size)
                print(f"  {label}: +{n:,}")
                grand_total += n
        log_ingest_finish(run_id, "success", rows_inserted=grand_total)
        print(f"\n[{JOB_NAME}] done. total {grand_total:,} notices upserted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=grand_total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=None, help="과거 N개월치 백필")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="시작일 YYYY-MM-DD (예: 2026-01-01)",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        help="종료일 YYYY-MM-DD. 미지정 시 오늘",
    )
    parser.add_argument(
        "--win-days",
        type=int,
        default=30,
        help="윈도우 일수 (데이터 많아 API '입력 초과' 에러 시 15로 단축)",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    since_dt = (
        datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    )
    until_dt = (
        datetime.strptime(args.until, "%Y-%m-%d") if args.until else None
    )
    if not since_dt and args.months is None:
        args.months = 1
    run(
        months=args.months,
        since=since_dt,
        until=until_dt,
        win_days=args.win_days,
        batch_size=args.batch_size,
    )

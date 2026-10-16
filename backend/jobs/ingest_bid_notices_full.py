"""BidPublicInfoService 기반 과거 입찰공고 백필 — 4 endpoint × 30일 윈도우.

기존 ingest_bid_notices.py가 사용하는 PubDataOpnStdService는 1주 윈도우 한도라
과거 백필 불가. BidPublicInfoService는 30일 윈도우 + 4개 endpoint(용역/물품/공사/외자)
나눠져 있고 응답 컬럼명이 약간 달라 별도 mapper.

bid_notices에 upsert (`ignore_duplicates=True`)로 기존 데이터 보존.

--fill: 상세 API 에만 오는 필드 4개(0047: 물품분류번호 배열·사전규격 번호·참가자격 등록 마감·공동수급 방식)를
기존 행에도 채운다. 1차 패스가 새 행을 통째로 넣고(PostgREST, 있는 행은 건드리지 않음), 2차 패스가
psycopg 직결로 그 4개 컬럼만 UPDATE 한다. DATABASE_URL 필요.

실행:
    cd backend
    uv run python -m jobs.ingest_bid_notices_full --months 1   # 한 달치 probe
    uv run python -m jobs.ingest_bid_notices_full --months 12  # 1년치 풀
    uv run python -m jobs.ingest_bid_notices_full --months 4 --div 물품 --fill   # 물품 통로용 분류번호 채우기
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timedelta
from typing import Any

import psycopg

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

_PRDCT_CODE = re.compile(r"\^(\d{10})\^")  # purchsObjPrdctList: '[1^4227171301^이름],[1^...]'


def _to_ts(s: str | None) -> str | None:
    """'2026-02-03 18:00' → ISO(+09:00). 빈 값·이상값은 None.

    나라장터 시각은 KST 벽시계다. 오프셋 없이 넣으면 timestamptz 가 UTC 로 해석해 9시간 미래로 저장된다 —
    2026-10-16 까지 그렇게 들어간 bid_qlfct_rgst_dt 5.9만 행은 -9h 로 일괄 보정했다 (_common.to_timestamptz 와 같은 규칙).
    """
    if not s or not str(s).strip():
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(s).strip(), fmt).isoformat() + "+09:00"
        except ValueError:
            continue
    return None


def detail_fields(it: dict) -> dict[str, Any]:
    """상세 API 에만 오는 4개(0047). 표준 API 응답에는 키 자체가 없어 전부 None 이 된다."""
    codes = _PRDCT_CODE.findall(str(it.get("purchsObjPrdctList") or ""))
    if not codes and it.get("dtilPrdctClsfcNo"):
        codes = [str(it["dtilPrdctClsfcNo"])]
    return {
        "prdct_clsfc_nos": sorted(set(codes)) or None,
        "bf_spec_rgst_no": (it.get("bfSpecRgstNo") or "").strip() or None,
        "bid_qlfct_rgst_dt": _to_ts(it.get("bidQlfctRgstDt")),
        "cmmn_spldmd_methd_nm": (it.get("cmmnSpldmdMethdNm") or "").strip() or None,
    }


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
        **detail_fields(it),
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


_DETAIL_KEYS = ("prdct_clsfc_nos", "bf_spec_rgst_no", "bid_qlfct_rgst_dt", "cmmn_spldmd_methd_nm")


_FILL_SQL = """
update bid_notices set
  prdct_clsfc_nos = %(prdct_clsfc_nos)s, bf_spec_rgst_no = %(bf_spec_rgst_no)s,
  bid_qlfct_rgst_dt = %(bid_qlfct_rgst_dt)s, cmmn_spldmd_methd_nm = %(cmmn_spldmd_methd_nm)s
where bid_ntce_no = %(bid_ntce_no)s and bid_ntce_ord = %(bid_ntce_ord)s
"""


def _flush(batch: list[dict], conn) -> None:
    # 1차: 새 행은 통째로, 있는 행은 건드리지 않는다.
    upsert_rows("bid_notices", batch, on_conflict="bid_ntce_no,bid_ntce_ord", ignore_duplicates=True)
    if conn is None:
        return
    # 2차: 진짜 UPDATE. upsert 로 키+4개만 보내면 Postgres 가 충돌 판정보다 NOT NULL(bid_ntce_nm) 검사를
    # 먼저 해서 거절한다 — 그래서 PostgREST merge 가 아니라 psycopg 직결(backfill_companies_basic 과 같은 길).
    rows = [
        {k: r[k] for k in ("bid_ntce_no", "bid_ntce_ord", *_DETAIL_KEYS)}
        for r in batch
        if any(r[k] is not None for k in _DETAIL_KEYS)
    ]
    if rows:
        with conn.cursor() as cur:
            cur.executemany(_FILL_SQL, rows)


def run_one_window(
    label: str, url: str, begin: datetime, end: datetime, batch_size: int, conn=None
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
            _flush(batch, conn)
            total += len(batch)
            batch.clear()
    if batch:
        _flush(batch, conn)
        total += len(batch)
    return total


def run(
    months: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    win_days: int = 30,
    batch_size: int = 500,
    divs: list[str] | None = None,
    fill: bool = False,
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

    conn = None
    if fill:
        if not os.getenv("DATABASE_URL"):
            raise SystemExit("--fill 에는 DATABASE_URL 이 필요합니다 (backend/.env)")
        conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
    grand_total = 0
    try:
        for i, (begin, win_end) in enumerate(wins, 1):
            print(
                f"\n[window {i}/{len(wins)}] {begin.strftime('%Y-%m-%d')} ~ {win_end.strftime('%Y-%m-%d')}"
            )
            for label, url in ENDPOINTS.items():
                if divs and label not in divs:
                    continue
                n = run_one_window(label, url, begin, win_end, batch_size, conn)
                print(f"  {label}: +{n:,}")
                grand_total += n
        log_ingest_finish(run_id, "success", rows_inserted=grand_total)
        print(f"\n[{JOB_NAME}] done. total {grand_total:,} notices upserted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=grand_total, error_msg=str(e))
        raise
    finally:
        if conn is not None:
            conn.close()


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
    parser.add_argument("--div", action="append", choices=list(ENDPOINTS), help="이 구분만 (반복 가능). 기본 전부")
    parser.add_argument("--fill", action="store_true", help="기존 행에도 상세 필드 4개(0047)를 채운다")
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
        divs=args.div,
        fill=args.fill,
    )

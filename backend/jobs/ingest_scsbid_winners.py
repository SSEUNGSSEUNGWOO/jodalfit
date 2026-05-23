"""낙찰자 목록 수집 (회사 수주 신호 보강).

소스: ScsbidInfoService/getScsbidListSttus[Servc|Thng|Cnstwk]
조회: 등록일시 (날짜 기반 페이지네이션)

award_results 테이블에 1순위(낙찰자)로 적재. is_winner=True.
참가업체 정보는 별도 큐잉 잡(추후) - 공고별 호출 필요.

실행:
    cd backend
    uv run python -m jobs.ingest_scsbid_winners --days-back 3
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta

from app.services.supabase_client import upsert_rows
from jobs._common import (
    DATE_FMT,
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_decimal,
    to_int,
)

BASE = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"
ENDPOINTS = {
    "용역": f"{BASE}/getScsbidListSttusServc",
    "물품": f"{BASE}/getScsbidListSttusThng",
    "공사": f"{BASE}/getScsbidListSttusCnstwk",
    "외자": f"{BASE}/getScsbidListSttusFrgcpt",
}
JOB_NAME = "ingest_scsbid_winners"


def normalize_bizrno(v: str | None) -> str | None:
    if not v:
        return None
    s = re.sub(r"\D", "", v)
    return s or None


def map_item(it: dict, bsns_div: str) -> dict:
    return {
        "bid_ntce_no": it.get("bidNtceNo"),
        "bid_ntce_ord": it.get("bidNtceOrd") or "000",
        "openg_rank": 1,
        "bizrno": normalize_bizrno(it.get("bidwinnrBizno")),
        "corp_nm": it.get("bidwinnrNm"),
        "corp_ceo_nm": it.get("bidwinnrCeoNm"),
        "bid_amt": to_int(it.get("sucsfbidAmt")),
        "bid_rate": to_decimal(it.get("sucsfbidRate")),
        "is_winner": True,
        "openg_result_div_nm": "낙찰",
        "bsns_div_nm": bsns_div,
        "raw": it,
    }


def run_one(label: str, url: str, extra: dict, batch_size: int) -> int:
    total = 0
    batch: list[dict] = []
    for it in iter_all_items(url, extra):
        row = map_item(it, label)
        if not row["bid_ntce_no"]:
            continue
        batch.append(row)
        if len(batch) >= batch_size:
            upsert_rows("award_results", batch, on_conflict="bid_ntce_no,bid_ntce_ord,openg_rank")
            total += len(batch)
            batch.clear()
    if batch:
        upsert_rows("award_results", batch, on_conflict="bid_ntce_no,bid_ntce_ord,openg_rank")
        total += len(batch)
    return total


def run(days_back: int = 3, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra_base = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back})
    print(f"[{JOB_NAME}] {extra_base['inqryBgnDt']} ~ {extra_base['inqryEndDt']}")

    grand_total = 0
    try:
        for label, url in ENDPOINTS.items():
            n = run_one(label, url, extra_base, batch_size)
            print(f"  {label}: {n} winners")
            grand_total += n
        log_ingest_finish(run_id, "success", rows_inserted=grand_total)
        print(f"[{JOB_NAME}] done. total {grand_total} winners")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=grand_total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

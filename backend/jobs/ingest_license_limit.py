"""입찰공고 면허제한 수집 (자격필터 핵심).

소스: BidPublicInfoService/getBidPblancListInfoLicenseLimit
조회: 등록일시 (inqryDiv=1 + inqryBgnDt/EndDt)

실행:
    cd backend
    uv run python -m jobs.ingest_license_limit --days-back 3
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.services.supabase_client import upsert_rows
from jobs._common import DATE_FMT, iter_all_items, log_ingest_finish, log_ingest_start, to_timestamptz

URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoLicenseLimit"
JOB_NAME = "ingest_license_limit"


def map_item(it: dict) -> dict:
    return {
        "bid_ntce_no": it.get("bidNtceNo"),
        "bid_ntce_ord": it.get("bidNtceOrd") or "000",
        "lmt_grp_no": str(it.get("lmtGrpNo") or "1"),
        "lmt_sno": str(it.get("lmtSno") or "1"),
        "bsns_div_nm": it.get("bsnsDivNm"),
        "lcns_lmt_nm": it.get("lcnsLmtNm"),
        "permsn_indstryty_list": it.get("permsnIndstrytyList") or None,
        "indstryty_mfrc_fld_list": it.get("indstrytyMfrcFldList") or None,
        "rgst_dt": to_timestamptz(it.get("rgstDt")),
        "raw": it,
    }


def run(days_back: int = 3, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back})
    print(f"[{JOB_NAME}] {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    total = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["bid_ntce_no"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("bid_license_limits", batch, on_conflict="bid_ntce_no,bid_ntce_ord,lmt_grp_no,lmt_sno")
                total += len(batch)
                batch.clear()
        if batch:
            upsert_rows("bid_license_limits", batch, on_conflict="bid_ntce_no,bid_ntce_ord,lmt_grp_no,lmt_sno")
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {total} rows upserted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

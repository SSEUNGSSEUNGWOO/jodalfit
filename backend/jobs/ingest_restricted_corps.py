"""부정당 제재 업체 수집 (자동 필터링용).

소스: UsrInfoService02/getUnptRsttCorpInfo02
조회조건: 제재시작일자 범위 (inqryDiv=1 + 날짜)

부수효과: companies.is_restricted = true 마킹.

실행:
    cd backend
    uv run python -m jobs.ingest_restricted_corps --days-back 30
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta

from app.services.supabase_client import get_admin_client
from jobs._common import (
    DATE_FMT,
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_date,
)

URL = "https://apis.data.go.kr/1230000/ao/UsrInfoService02/getUnptRsttCorpInfo02"
JOB_NAME = "ingest_restricted_corps"


def normalize_bizrno(v: str | None) -> str | None:
    if not v:
        return None
    s = re.sub(r"\D", "", v)
    return s or None


def run(days_back: int = 30) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back})
    print(f"[{JOB_NAME}] 제재시작일 {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    client = get_admin_client()
    updated = 0
    try:
        for it in iter_all_items(URL, extra):
            bizrno = normalize_bizrno(it.get("bizno"))
            if not bizrno:
                continue
            client.table("companies").update(
                {
                    "is_restricted": True,
                    "restricted_until": to_date(it.get("rstrEndDt")),
                }
            ).eq("bizrno_norm", bizrno).execute()
            updated += 1
        log_ingest_finish(run_id, "success", rows_updated=updated)
        print(f"[{JOB_NAME}] done. {updated} companies flagged as restricted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=updated, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=30)
    args = parser.parse_args()
    run(args.days_back)

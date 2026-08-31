"""입찰공고 첨부파일(제안요청서·공고서 등) 목록 수집 잡.

ingest_bid_notices.py가 쓰는 PubDataOpnStdService는 첨부 필드를 안 주므로,
BidPublicInfoService(용역/물품/공사/외자)의 ntceSpecDocUrl1~10 / ntceSpecFileNm1~10을
받아 bid_notices.attachments(jsonb)에 UPDATE (RPC update_bid_notice_attachments, 0020).

이미 bid_notices에 있는 공고만 갱신됨 → ingest_bid_notices 뒤에 실행.

실행:
    cd backend
    uv run python -m jobs.ingest_bid_attachments --days-back 1
    uv run python -m jobs.ingest_bid_attachments --days-back 30   # 최대 30일 (API 조회범위 한도)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.services.supabase_client import get_admin_client
from jobs._common import DATE_FMT, iter_all_items, log_ingest_finish, log_ingest_start
from jobs.ingest_bid_notices_full import ENDPOINTS

JOB_NAME = "ingest_bid_attachments"
RPC_NAME = "update_bid_notice_attachments"


def extract_attachments(it: dict) -> list[dict]:
    out = []
    for i in range(1, 11):
        url = (it.get(f"ntceSpecDocUrl{i}") or "").strip()
        if not url:
            continue
        out.append({"seq": i, "name": it.get(f"ntceSpecFileNm{i}") or None, "url": url})
    return out


def flush(client, batch: list[dict]) -> int:
    if not batch:
        return 0
    res = client.rpc(RPC_NAME, {"updates": batch}).execute()
    return int(res.data or 0)


def run(days_back: int = 1, batch_size: int = 200) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(
        JOB_NAME,
        {"days_back": days_back, "begin": extra["inqryBgnDt"], "end": extra["inqryEndDt"]},
    )
    print(f"[{JOB_NAME}] range {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    client = get_admin_client()
    seen = 0
    updated = 0
    try:
        for label, url in ENDPOINTS.items():
            batch: list[dict] = []
            n_label = 0
            for it in iter_all_items(url, extra):
                seen += 1
                atts = extract_attachments(it)
                if not it.get("bidNtceNo") or not atts:
                    continue
                batch.append(
                    {
                        "bid_ntce_no": it["bidNtceNo"],
                        "bid_ntce_ord": it.get("bidNtceOrd") or "000",
                        "attachments": atts,
                    }
                )
                if len(batch) >= batch_size:
                    n_label += flush(client, batch)
                    batch.clear()
            n_label += flush(client, batch)
            updated += n_label
            print(f"  {label}: updated {n_label}")
        log_ingest_finish(run_id, "success", rows_updated=updated)
        print(f"[{JOB_NAME}] done. seen {seen}, updated {updated}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=updated, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

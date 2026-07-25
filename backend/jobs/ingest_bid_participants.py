"""개찰결과 참가업체 수집 (회사 벡터 참가 시그널 재료).

소스: ScsbidInfoService/getOpengResultListInfoOpengCompt (inqryDiv=2, 공고별 호출)

큐: 최근 N일 award_results 낙찰 공고 중 bid_notices에 임베딩 있는 공고만.
  - 임베딩 없는 공고는 벡터 재료가 안 되므로 API 호출 낭비 (하루 5천건+ 한도 위험)
  - 이미 rank 2+ 행이 있는 공고는 수집 완료로 보고 스킵
적재: rank 2+만 is_winner=False로 upsert. rank 1은 winners 잡 담당이라 안 건드림.
  (외자 다품목 공고는 rank=1이 복수라 PK 충돌 — rank 2+ 필터로 자연 회피)

실행:
    cd backend
    uv run python -m jobs.ingest_bid_participants --days-back 3 --limit 2000
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta

from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import (
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_decimal,
    to_int,
)

BASE = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"
ENDPOINT = f"{BASE}/getOpengResultListInfoOpengCompt"
JOB_NAME = "ingest_bid_participants"

PAGE = 1000


def normalize_bizrno(v: str | None) -> str | None:
    if not v:
        return None
    s = re.sub(r"\D", "", v)
    return s or None


def map_item(it: dict, bsns_div: str | None) -> dict | None:
    rank = to_int(it.get("opengRank"))
    if rank is None or rank < 2:
        return None
    return {
        "bid_ntce_no": it.get("bidNtceNo"),
        "bid_ntce_ord": it.get("bidNtceOrd") or "000",
        "openg_rank": rank,
        "bizrno": normalize_bizrno(it.get("prcbdrBizno")),
        "corp_nm": it.get("prcbdrNm"),
        "corp_ceo_nm": it.get("prcbdrCeoNm"),
        "bid_amt": to_int(it.get("bidprcAmt")),
        "bid_rate": to_decimal(it.get("bidprcrt")),
        "is_winner": False,
        "openg_result_div_nm": it.get("opengRsltDivNm"),
        "bsns_div_nm": bsns_div,
        "raw": it,
    }


def fetch_queue(client, days_back: int, limit: int) -> list[dict]:
    """수집 대상 공고 목록 = 최근 낙찰 공고 ∩ 임베딩 보유 - 이미 참가자 있는 공고."""
    since = (datetime.now() - timedelta(days=days_back)).isoformat()

    winners: list[dict] = []
    offset = 0
    while True:
        rows = (
            client.table("award_results")
            .select("bid_ntce_no,bid_ntce_ord,bsns_div_nm")
            .eq("is_winner", True)
            .gte("created_at", since)
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        winners.extend(rows)
        if len(rows) < PAGE:
            break
        offset += PAGE

    if not winners:
        return []

    bid_nos = sorted({w["bid_ntce_no"] for w in winners})

    embedded: set[str] = set()
    done: set[str] = set()
    for i in range(0, len(bid_nos), 200):
        sub = bid_nos[i : i + 200]
        emb_rows = (
            client.table("bid_notices")
            .select("bid_ntce_no")
            .in_("bid_ntce_no", sub)
            .not_.is_("embedding", "null")
            .execute()
            .data
        )
        embedded.update(r["bid_ntce_no"] for r in emb_rows)
        done_rows = (
            client.table("award_results")
            .select("bid_ntce_no")
            .in_("bid_ntce_no", sub)
            .gte("openg_rank", 2)
            .execute()
            .data
        )
        done.update(r["bid_ntce_no"] for r in done_rows)

    seen: set[str] = set()
    queue: list[dict] = []
    for w in winners:
        no = w["bid_ntce_no"]
        if no in seen or no not in embedded or no in done:
            continue
        seen.add(no)
        queue.append(w)
        if len(queue) >= limit:
            break
    return queue


def run(days_back: int = 3, limit: int = 2000, batch_size: int = 500) -> None:
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back, "limit": limit})
    client = get_admin_client()

    queue = fetch_queue(client, days_back, limit)
    print(f"[{JOB_NAME}] queue={len(queue)} notices (days_back={days_back})")

    total = 0
    calls = 0
    batch: dict[tuple, dict] = {}
    try:
        for w in queue:
            calls += 1
            for it in iter_all_items(
                ENDPOINT,
                {"inqryDiv": "2", "bidNtceNo": w["bid_ntce_no"]},
                rows_per_page=500,
                max_pages=5,
            ):
                row = map_item(it, w.get("bsns_div_nm"))
                if not row or not row["bid_ntce_no"]:
                    continue
                batch[(row["bid_ntce_no"], row["bid_ntce_ord"], row["openg_rank"])] = row
            if len(batch) >= batch_size:
                upsert_rows(
                    "award_results",
                    list(batch.values()),
                    on_conflict="bid_ntce_no,bid_ntce_ord,openg_rank",
                )
                total += len(batch)
                batch.clear()
            if calls % 100 == 0:
                print(f"  [{calls}/{len(queue)}] participants {total + len(batch):,}")
        if batch:
            upsert_rows(
                "award_results",
                list(batch.values()),
                on_conflict="bid_ntce_no,bid_ntce_ord,openg_rank",
            )
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {calls} calls / {total:,} participants")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.limit, args.batch_size)

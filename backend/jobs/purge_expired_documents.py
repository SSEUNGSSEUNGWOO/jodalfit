"""마감+7일 지난 공고의 첨부문서 텍스트를 비운다 (status='purged'). 인사이트는 이미 뽑혀 있고 임베딩은 문서를 안 쓴다.
문서 텍스트 1.6GB 가 매달 1GB 씩 늘던 것을 진행 중 공고분(~0.4GB)으로 고정한다. 실행: uv run python -m jobs.purge_expired_documents [--grace-days 7] [--batch 2000]"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg
from dotenv import load_dotenv

from jobs._common import log_ingest_finish, log_ingest_start

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DATABASE_URL = os.getenv("DATABASE_URL")
JOB_NAME = "purge_expired_documents"

PURGE_SQL = """
with t as (
  select d.bid_ntce_no, d.bid_ntce_ord, d.seq from bid_notice_documents d
  join bid_notices b using (bid_ntce_no, bid_ntce_ord)
  where d.text is not null and b.bid_clse_date < current_date - (%s)::int
  limit %s)
update bid_notice_documents d set text = null, status = 'purged'
from t where d.bid_ntce_no = t.bid_ntce_no and d.bid_ntce_ord = t.bid_ntce_ord and d.seq = t.seq
"""


def run(grace_days: int, batch: int) -> None:
    run_id = log_ingest_start(JOB_NAME, {"grace_days": grace_days, "batch": batch})
    if not DATABASE_URL:
        log_ingest_finish(run_id, "failed", error_msg="DATABASE_URL 이 필요합니다 (backend/.env)")
        raise SystemExit("DATABASE_URL 이 필요합니다 (backend/.env)")
    purged = 0
    try:
        # autocommit — 배치 UPDATE 하나가 곧 트랜잭션 하나
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            conn.execute("set statement_timeout = 300000")  # 5분
            while True:
                with conn.cursor() as cur:
                    cur.execute(PURGE_SQL, (grace_days, batch))
                    n = cur.rowcount
                if not n:
                    break
                purged += n
                print(f"  purged {purged:,}")
        log_ingest_finish(run_id, "success", rows_updated=purged)
        print(f"[{JOB_NAME}] done. purged={purged:,}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=purged, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grace-days", type=int, default=7, help="마감 후 이 일수가 지난 공고부터 비움")
    parser.add_argument("--batch", type=int, default=2000, help="한 번의 UPDATE 로 비울 행 수")
    args = parser.parse_args()
    run(args.grace_days, args.batch)

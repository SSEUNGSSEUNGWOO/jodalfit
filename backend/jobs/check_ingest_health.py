"""수집 잡 건강 점검 — "성공인데 0건", "너무 빨리 끝남", 실패, 실행 누락을 잡는다.

continue-on-error 뒤에서 조용히 죽는 잡을 잡기 위한 것. 2026-10 에 두 번 당했다 —
DATABASE_URL 이 없어 한 달간 매일 1초 만에 exit 1 하던 잡, 공급물품 API 가 5주간 빈 응답을 주는데
잡이 "완료"로 삼킨 것. 둘 다 Actions 에서는 초록색이었다.

ingest_runs 를 읽어 잡별로 최근 실행을 직전 14일 성공 실행의 중앙값과 비교한다.
  - 최근 실행이 failed                                     → 경고
  - 최근 실행이 success 인데 rows 0, 중앙값 50 이상        → 경고 "성공인데 0건"
  - 최근 실행 소요 2초 미만, 중앙값 60초 이상               → 경고 "너무 빨리 끝남"
  - 스케줄에 있는 잡(SCHEDULED)이 48시간 안에 실행 기록 없음 → 경고
rows 는 잡마다 rows_inserted 또는 rows_updated 한쪽만 쓴다(ROWS_FIELD). 매번 0 에 가까운 잡
(register_searched_companies 처럼 "있으면 처리")은 중앙값이 50 을 못 넘어 자연히 소요 시간 규칙만 걸린다.
중앙값 규칙 둘은 성공 실행이 3번 이상 쌓인 뒤에만 본다 — 2개의 "중앙값"은 평균이라 한 번의 큰 값에 끌려간다.

소요 시간은 finished_at - started_at. 2026-10-16 이전 로컬 PC 실행은 finished_at 이 KST 벽시계를 UTC 로
적어 9시간 길게 나온다 — 8시간 넘는 값은 중앙값에서 뺀다(잡 timeout 이 최대 90분이라 진짜 8시간은 없다).

경고가 하나라도 있으면 exit 1. daily-sync.yml 마지막 스텝에서 continue-on-error 없이 돈다.

실행:
    cd backend
    uv run python -m jobs.check_ingest_health
"""

from __future__ import annotations

import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 스케줄(hourly-sync.yml / daily-sync.yml)에 있는 잡. 워크플로를 바꾸면 여기도 맞춘다.
SCHEDULED = (
    # hourly-sync
    "register_searched_companies",
    "ingest_bid_notices",
    "ingest_bid_notices_full",
    "ingest_bid_attachments",
    "extract_bid_documents",
    "summarize_bid_documents",
    "embed_bid_notices",
    # daily-sync / sync
    "ingest_contracts",
    "ingest_scsbid_winners",
    "ingest_bid_participants",
    "ingest_pre_specs",
    "ingest_pre_spec_opinions",
    "ingest_license_limit",
    "ingest_rgn_limit",
    "embed_pre_specs",
    "purge_expired_documents",
    # daily-sync / enrich-companies
    "ingest_companies_userinfo",
    "backfill_companies_basic",
    "check_business_status",
    "ingest_company_details",
    # daily-sync / company-vectors
    "compute_company_vectors",
)

# 잡이 성공 시 채우는 건수 컬럼. 코드의 log_ingest_finish(... rows_inserted= / rows_updated=) 기준(2026-10-16).
ROWS_FIELD = {
    "rows_inserted": (
        "ingest_bid_notices", "ingest_bid_notices_full", "ingest_bid_participants",
        "ingest_companies_userinfo", "ingest_company_details", "ingest_contracts",
        "ingest_license_limit", "ingest_order_plans", "ingest_pre_spec_opinions", "ingest_pre_specs",
        "ingest_rgn_limit", "ingest_scsbid_winners", "extract_bid_documents",
        "register_searched_companies", "summarize_bid_documents",
    ),
    "rows_updated": (
        "compute_company_vectors", "embed_bid_notices", "embed_order_plans", "embed_pre_specs",
        "ingest_bid_attachments", "ingest_restricted_corps", "purge_expired_documents",
        "backfill_companies_basic", "check_business_status",
    ),
}
_FIELD_OF = {job: field for field, jobs in ROWS_FIELD.items() for job in jobs}

ZERO_ROWS_MIN_MEDIAN = 50
TOO_FAST_SEC = 2
TOO_FAST_MIN_MEDIAN_SEC = 60
MISSING_HOURS = 48
MIN_SAMPLES = 3
BOGUS_DURATION_SEC = 8 * 3600

_SQL = """
with runs as (
  select job_name, status, started_at, finished_at,
         rows_inserted, rows_updated,
         extract(epoch from (finished_at - started_at)) as sec
  from ingest_runs
  where started_at > now() - interval '14 days'
),
latest as (
  select distinct on (job_name) job_name, status, started_at, rows_inserted, rows_updated, sec
  from runs where status in ('success', 'failed')
  order by job_name, started_at desc
),
med as (
  select job_name,
         percentile_cont(0.5) within group (order by rows_inserted) as med_ins,
         percentile_cont(0.5) within group (order by rows_updated) as med_upd,
         percentile_cont(0.5) within group (order by sec)
           filter (where sec is not null and sec < %(bogus)s) as med_sec,
         count(*) as n_ok
  from runs where status = 'success'
  group by job_name
),
seen as (select job_name, max(started_at) as last_started from runs group by job_name)
select l.job_name, l.status, l.started_at, l.rows_inserted, l.rows_updated, l.sec,
       m.med_ins, m.med_upd, m.med_sec, m.n_ok, s.last_started
from latest l
left join med m using (job_name)
left join seen s using (job_name)
order by l.job_name
"""


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL 이 없어 ingest_runs 를 읽을 수 없습니다")
        return 1
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(_SQL, {"bogus": BOGUS_DURATION_SEC})
        rows = cur.fetchall()
        cur.execute("select now()")
        now = cur.fetchone()[0]

    warnings: list[str] = []
    seen_jobs: set[str] = set()
    for job, status, started, ins, upd, sec, med_ins, med_upd, med_sec, n_ok, last_started in rows:
        seen_jobs.add(job)
        when = started.astimezone().strftime("%m-%d %H:%M")
        if status == "failed":
            warnings.append(f"{job}: 최근 실행({when})이 실패")
            continue
        enough = n_ok is not None and n_ok >= MIN_SAMPLES
        field = _FIELD_OF.get(job)
        if field is not None and enough:
            n = ins if field == "rows_inserted" else upd
            med = med_ins if field == "rows_inserted" else med_upd
            if n == 0 and med is not None and med >= ZERO_ROWS_MIN_MEDIAN:
                warnings.append(
                    f"{job}: 성공인데 0건 — 최근 실행({when}) {field}=0, 14일 중앙값 {med:,.0f}건"
                )
        if enough and sec is not None and med_sec is not None and sec < TOO_FAST_SEC and med_sec >= TOO_FAST_MIN_MEDIAN_SEC:
            warnings.append(
                f"{job}: 너무 빨리 끝남 — 최근 실행({when}) {sec:.1f}초, 14일 중앙값 {med_sec:,.0f}초"
            )
    last_by_job = {r[0]: r[10] for r in rows}
    for job in SCHEDULED:
        last = last_by_job.get(job)
        if last is None:
            warnings.append(f"{job}: 최근 14일 실행 기록 없음 (스케줄에는 있음)")
        elif (now - last).total_seconds() > MISSING_HOURS * 3600:
            warnings.append(
                f"{job}: {MISSING_HOURS}시간 안에 실행 기록 없음 — 마지막 {last.astimezone().strftime('%m-%d %H:%M')}"
            )

    if not warnings:
        print(f"정상 — 잡 {len(seen_jobs)}개, 경고 없음")
        return 0
    print(f"경고 {len(warnings)}건")
    for w in warnings:
        print(f"- {w}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

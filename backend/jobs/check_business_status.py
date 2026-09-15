"""회사 사업자등록 상태 조회 — 국세청 진위확인·상태조회 API (공공데이터포털 odcloud).

회사 페이지 6만 개 중 폐업한 회사를 가려낸다. 폐업(03)은 페이지 noindex + 사이트맵·업종
디렉토리 제외(migration 0028). 휴업(02)은 표시만 한다.

- 대상: embedding 보유 회사 중 미조회 → 조회한 지 오래된 순. 한 번에 100건 POST.
- 한도: 1회 100건, 일 100만 건. 전량(6만)도 600회 호출이라 첫 실행에 --limit 100000 으로 끝낸다.
- 이후 daily-sync 에서 --limit 3000 으로 돌리면 30일 주기로 전량 재확인된다 (--max-age-days).

실행:
    cd backend
    uv run python -m jobs.check_business_status --limit 100000
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx
import psycopg
from dotenv import load_dotenv

from jobs._common import log_ingest_finish, log_ingest_start

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")  # data.go.kr 계정 키 — 국세청 API 도 같은 키
DATABASE_URL = os.getenv("DATABASE_URL")
URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"
JOB_NAME = "check_business_status"
BATCH = 100
MAX_CONSECUTIVE_ERRORS = 5


def fetch_status(bizrnos: list[str], retries: int = 3) -> list[dict]:
    for attempt in range(retries):
        try:
            resp = httpx.post(
                URL, params={"serviceKey": API_KEY}, json={"b_no": bizrnos}, timeout=30.0
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500 and e.response.status_code != 429:
                raise
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")


def select_candidates(conn: psycopg.Connection, limit: int, max_age_days: int) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select bizrno, bizrno_norm
            from companies
            where embedding is not null
              and bizrno_norm ~ '^\\d{10}$'
              and (biz_status_checked_at is null
                   or biz_status_checked_at < now() - make_interval(days => %s))
            order by biz_status_checked_at nulls first
            limit %s
            """,
            (max_age_days, limit),
        )
        return cur.fetchall()


def to_date(v: str | None) -> str | None:
    # end_dt: "20230131" 또는 ""
    if not v or len(v) != 8:
        return None
    return f"{v[:4]}-{v[4:6]}-{v[6:]}"


def run(limit: int, max_age_days: int) -> None:
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL 이 필요합니다 (backend/.env)")
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "max_age_days": max_age_days})
    updated = errors = 0
    counts = {"01": 0, "02": 0, "03": 0, "": 0}
    consecutive_errors = 0
    stopped_early = False
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("set statement_timeout = 0")
            candidates = select_candidates(conn, limit, max_age_days)
            print(f"[{JOB_NAME}] 대상 {len(candidates):,}개")
            by_norm = {norm: bizrno for bizrno, norm in candidates}
            norms = list(by_norm)

            for i in range(0, len(norms), BATCH):
                chunk = norms[i : i + BATCH]
                try:
                    rows = fetch_status(chunk)
                except httpx.HTTPError as e:
                    errors += len(chunk)
                    consecutive_errors += 1
                    # e 를 그대로 찍으면 URL 의 serviceKey 가 로그에 남는다.
                    status = getattr(getattr(e, "response", None), "status_code", None)
                    print(f"  ! batch {i // BATCH}: {type(e).__name__} {status or ''}")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"[{JOB_NAME}] 연속 오류 {consecutive_errors}회 — 중단")
                        stopped_early = True
                        break
                    time.sleep(5)
                    continue
                consecutive_errors = 0

                params = []
                for r in rows:
                    norm = r.get("b_no")
                    if norm not in by_norm:
                        continue
                    cd = r.get("b_stt_cd") or ""
                    counts[cd if cd in counts else ""] += 1
                    params.append((cd or None, r.get("b_stt") or None, to_date(r.get("end_dt")), by_norm[norm]))
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        update companies
                        set biz_status_cd = %s, biz_status_nm = %s, biz_closed_dt = %s,
                            biz_status_checked_at = now()
                        where bizrno = %s
                        """,
                        params,
                    )
                updated += len(params)
                if (i // BATCH) % 50 == 0:
                    print(f"  [{i + len(chunk)}/{len(norms)}] updated={updated} 폐업={counts['03']} 휴업={counts['02']} errors={errors}")

        status = "failed" if stopped_early else "success"
        log_ingest_finish(run_id, status, rows_updated=updated, rows_failed=errors,
                          error_msg="consecutive api errors" if stopped_early else None)
        print(
            f"[{JOB_NAME}] done. updated={updated} 계속={counts['01']} 휴업={counts['02']} "
            f"폐업={counts['03']} 미등록={counts['']} errors={errors}"
        )
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=updated, rows_failed=errors, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()
    run(args.limit, args.max_age_days)

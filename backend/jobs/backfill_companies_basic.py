"""회사 기본정보 백필 — 사업자번호 단위 조회 (UsrInfoService02 getPrcrmntCorpBasicInfo02, inqryDiv=3).

ingest_companies_userinfo 는 "최근 N일 내 변경된 회사"만 받아오므로, 낙찰·계약에서
stub 으로 생긴 회사(raw null, 지역·주소 없음)는 영영 채워지지 않는다. 2026-09-11 기준
색인 대상(임베딩 보유) 60,059개 중 57,285개가 이 상태라 지역별 기업 페이지가 4.6%만 담겼다.

- 대상: embedding 보유 + raw null. bizrno_norm 순으로 limit 만큼.
- 조회 결과 없는 회사는 raw 에 표식을 남겨 다음 실행에서 제외한다.
- 기존 행의 bizrno 키(대시 포함)를 그대로 써서 in-place UPDATE — ingest_companies_userinfo 의
  map_item 은 bizno 를 정규화하므로 그걸 그대로 upsert 하면 중복 행이 생긴다.
- 일일 한도(4,500/일)에 걸리면 연속 실패로 감지해 조기 종료.

실행:
    cd backend
    uv run python -m jobs.backfill_companies_basic --limit 3000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
import psycopg
from dotenv import load_dotenv

from jobs._common import log_ingest_finish, log_ingest_start
from jobs.ingest_companies_userinfo import map_item

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
URL = "https://apis.data.go.kr/1230000/ao/UsrInfoService02/getPrcrmntCorpBasicInfo02"
JOB_NAME = "backfill_companies_basic"

# 연속으로 이만큼 API 오류가 나면 한도 소진/장애로 보고 멈춘다.
MAX_CONSECUTIVE_ERRORS = 5

UPDATE_COLS = [
    "corp_nm", "english_nm", "ceo_nm", "opng_dt", "rgn_cd", "rgn_nm", "zip_no", "addr",
    "dtl_addr", "tel_no", "fax_no", "hmpg_addr", "mnfctr_div_cd", "mnfctr_div_nm",
    "emp_count", "corp_bsns_div_cd", "corp_bsns_div_nm", "hd_off_div_nm",
    "unq_no_crtfct_yn", "rgst_dt", "raw",
]


class ApiError(Exception):
    pass


def fetch_basic(bizrno_norm: str) -> dict | None:
    """사업자번호로 기본정보 1건. 없으면 None, API 오류면 ApiError."""
    params = {
        "ServiceKey": API_KEY,
        "type": "json",
        "pageNo": "1",
        "numOfRows": "1",
        "inqryDiv": "3",
        "bizno": bizrno_norm,
    }
    resp = httpx.get(URL, params=params, timeout=30.0)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        raise ApiError(f"non-json response: {resp.text[:120]}")
    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        raise ApiError(f"code={err.get('resultCode')} msg={err.get('resultMsg')}")
    body = data.get("response", {}).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    return items[0] if items else None


def select_candidates(conn: psycopg.Connection, limit: int) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select bizrno, bizrno_norm
            from companies
            where embedding is not null and raw is null and bizrno_norm ~ '^\\d{10}$'
            order by bizrno_norm
            limit %s
            """,
            (limit,),
        )
        return cur.fetchall()


def update_company(conn: psycopg.Connection, bizrno: str, row: dict) -> None:
    sets = ", ".join(f"{c} = %({c})s" for c in UPDATE_COLS)
    payload = {c: row.get(c) for c in UPDATE_COLS}
    payload["raw"] = json.dumps(payload["raw"], ensure_ascii=False)
    payload["bizrno"] = bizrno
    with conn.cursor() as cur:
        cur.execute(
            f"update companies set {sets}, updated_at = now() where bizrno = %(bizrno)s",
            payload,
        )


def mark_not_found(conn: psycopg.Connection, bizrno: str) -> None:
    marker = json.dumps(
        {"_basic_lookup": "not_found", "at": datetime.now(timezone.utc).isoformat()}
    )
    with conn.cursor() as cur:
        cur.execute(
            "update companies set raw = %s, updated_at = now() where bizrno = %s",
            (marker, bizrno),
        )


def run(limit: int) -> None:
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL 이 필요합니다 (backend/.env)")
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    updated = not_found = errors = 0
    consecutive_errors = 0
    stopped_early = False
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("set statement_timeout = 0")
            candidates = select_candidates(conn, limit)
            print(f"[{JOB_NAME}] 대상 {len(candidates):,}개")

            for i, (bizrno, bizrno_norm) in enumerate(candidates, 1):
                try:
                    item = fetch_basic(bizrno_norm)
                except (ApiError, httpx.HTTPError) as e:
                    errors += 1
                    consecutive_errors += 1
                    # httpx 오류 메시지엔 URL(ServiceKey 포함)이 들어가므로 종류만 남긴다.
                    detail = str(e) if isinstance(e, ApiError) else type(e).__name__
                    print(f"  ! {bizrno_norm}: {detail}")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"[{JOB_NAME}] 연속 오류 {consecutive_errors}회 — 한도 소진/장애로 보고 중단")
                        stopped_early = True
                        break
                    time.sleep(3)
                    continue
                consecutive_errors = 0

                if item is None:
                    mark_not_found(conn, bizrno)
                    not_found += 1
                else:
                    update_company(conn, bizrno, map_item(item))
                    updated += 1

                if i % 200 == 0:
                    print(f"  [{i}/{len(candidates)}] updated={updated} not_found={not_found} errors={errors}")

        status = "failed" if stopped_early else "success"
        log_ingest_finish(run_id, status, rows_updated=updated, rows_failed=errors,
                          error_msg="consecutive api errors" if stopped_early else None)
        print(f"[{JOB_NAME}] done. updated={updated} not_found={not_found} errors={errors}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=updated, rows_failed=errors, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3000)
    args = parser.parse_args()
    run(args.limit)

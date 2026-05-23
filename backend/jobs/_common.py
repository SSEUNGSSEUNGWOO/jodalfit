"""수집 잡 공통 유틸.

- 나라장터 OpenAPI 호출, 페이징
- API 응답 필드 → DB 컬럼 type 변환
- ingest_runs 로깅
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Iterator

import httpx
from dotenv import load_dotenv

from app.services.supabase_client import get_admin_client

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
if not API_KEY:
    raise SystemExit("NARAJANGTEO_API_KEY가 .env에 설정되지 않았습니다.")

DATE_FMT = "%Y%m%d%H%M"


# ----- 타입 변환 (API string → DB 적합 타입) -----

def to_int(v: Any) -> int | None:
    if v in (None, "", " "):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def to_decimal(v: Any) -> float | None:
    if v in (None, "", " "):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def to_date(v: Any) -> str | None:
    """'YYYY-MM-DD' 또는 빈 문자열 → ISO 날짜 또는 None."""
    if not v or str(v).strip() in ("", "0"):
        return None
    s = str(v).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def to_timestamptz(v: Any) -> str | None:
    """'YYYY-MM-DD HH:MM:SS' → ISO timestamptz (KST 가정)."""
    if not v or str(v).strip() in ("", "0"):
        return None
    s = str(v).strip()
    if len(s) >= 19 and s[4] == "-" and s[10] == " ":
        return s[:19].replace(" ", "T") + "+09:00"
    return None


def to_yn(v: Any) -> str | None:
    if v in ("Y", "N"):
        return v
    return None


# ----- API 호출 + 페이징 -----

def fetch_page(
    url: str,
    extra_params: dict[str, str],
    page_no: int,
    rows_per_page: int,
) -> dict[str, Any]:
    params = {
        "ServiceKey": API_KEY,
        "type": "json",
        "pageNo": str(page_no),
        "numOfRows": str(rows_per_page),
        **extra_params,
    }
    resp = httpx.get(url, params=params, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def iter_all_items(
    url: str,
    extra_params: dict[str, str],
    rows_per_page: int = 500,
    max_pages: int = 200,
) -> Iterator[dict]:
    """페이징하며 모든 item 반환. 너무 큰 응답 대비 max_pages 안전장치."""
    page = 1
    while page <= max_pages:
        data = fetch_page(url, extra_params, page, rows_per_page)
        if "nkoneps.com.response.ResponseError" in data:
            err = data["nkoneps.com.response.ResponseError"].get("header", {})
            raise RuntimeError(
                f"API error code={err.get('resultCode')} msg={err.get('resultMsg')}"
            )
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if not items:
            return
        for it in items:
            yield it
        total = to_int(body.get("totalCount")) or 0
        if page * rows_per_page >= total:
            return
        page += 1


# ----- ingest_runs 로깅 -----

def log_ingest_start(job_name: str, payload: dict | None = None) -> int:
    client = get_admin_client()
    res = (
        client.table("ingest_runs")
        .insert({"job_name": job_name, "status": "running", "payload": payload})
        .execute()
    )
    return res.data[0]["id"]


def log_ingest_finish(
    run_id: int,
    status: str,
    rows_inserted: int = 0,
    rows_updated: int = 0,
    rows_failed: int = 0,
    error_msg: str | None = None,
) -> None:
    client = get_admin_client()
    client.table("ingest_runs").update(
        {
            "status": status,
            "finished_at": datetime.now().isoformat(),
            "rows_inserted": rows_inserted,
            "rows_updated": rows_updated,
            "rows_failed": rows_failed,
            "error_msg": error_msg,
        }
    ).eq("id", run_id).execute()

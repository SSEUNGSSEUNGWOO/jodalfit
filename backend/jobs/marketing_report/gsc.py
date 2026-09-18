"""구글 서치콘솔 수집 — Search Analytics(노출·클릭·쿼리·페이지), 사이트맵 상태, URL 검사 표본.

인증: 서비스 계정 JSON (`GSC_SERVICE_ACCOUNT_JSON`, 기본 backend/secrets/gsc-service-account.json).
서치콘솔 속성에 그 계정 이메일을 사용자(전체)로 추가해야 한다. 설정 방법은 docs/marketing/README.md.
서치콘솔 데이터는 1~2일 늦게 확정되므로 어제 데이터가 비어 있으면 최대 3일 전까지 물러난다 (data_date 에 기록).
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

import httpx

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
SA_DEFAULT = Path(__file__).resolve().parents[2] / "secrets" / "gsc-service-account.json"
SA_BASE = "https://www.googleapis.com/webmasters/v3"
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def _token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    path = Path(os.environ.get("GSC_SERVICE_ACCOUNT_JSON") or SA_DEFAULT)
    if not path.exists():
        raise FileNotFoundError(f"서비스 계정 JSON 없음: {path}")
    creds = service_account.Credentials.from_service_account_file(str(path), scopes=SCOPES)
    creds.refresh(Request())
    return creds.token


def _client() -> httpx.Client:
    return httpx.Client(headers={"Authorization": f"Bearer {_token()}"}, timeout=60)


def _query(c: httpx.Client, site: str, day: date, dimensions: list[str], row_limit: int = 1000) -> list[dict]:
    body = {
        "startDate": day.isoformat(), "endDate": day.isoformat(),
        "dimensions": dimensions, "rowLimit": row_limit,
        "dataState": "all",  # 확정 전(fresh) 데이터 포함
    }
    r = c.post(f"{SA_BASE}/sites/{site}/searchAnalytics/query", json=body)
    r.raise_for_status()
    return r.json().get("rows", [])


def classify_page(url: str, page_types: list[dict]) -> str:
    path = re.sub(r"^https?://[^/]+", "", url) or "/"
    for pt in page_types:
        if re.search(pt["pattern"], path):
            return pt["name"]
    return "other"


def collect_search(site: str, day: date, page_types: list[dict], keywords: list[str]) -> dict:
    """노출·클릭 총계 + 페이지 유형별 + 상위 쿼리 + 추적 키워드 순위. 데이터 없는 날은 최대 3일 물러남."""
    with _client() as c:
        data_date = None
        totals: list[dict] = []
        for back in range(0, 4):
            d = day - timedelta(days=back)
            totals = _query(c, site, d, [])
            if totals:
                data_date = d
                break
        if data_date is None:
            return {"data_date": None, "note": "최근 4일 데이터 없음 (서치콘솔 지연 또는 노출 0)"}

        t = totals[0]
        pages = _query(c, site, data_date, ["page"], 5000)
        by_type: dict[str, dict] = {}
        for row in pages:
            k = classify_page(row["keys"][0], page_types)
            agg = by_type.setdefault(k, {"clicks": 0, "impressions": 0})
            agg["clicks"] += row["clicks"]
            agg["impressions"] += row["impressions"]

        queries = _query(c, site, data_date, ["query"], 1000)
        top = [
            {"query": r["keys"][0], "clicks": r["clicks"], "impressions": r["impressions"], "position": round(r["position"], 1)}
            for r in queries[:20]
        ]
        by_query = {r["keys"][0]: r for r in queries}
        tracked = {
            q: ({"position": round(by_query[q]["position"], 1), "impressions": by_query[q]["impressions"], "clicks": by_query[q]["clicks"]}
                if q in by_query else None)
            for q in keywords
        }
        return {
            "data_date": data_date.isoformat(),
            "clicks": t["clicks"], "impressions": t["impressions"],
            "ctr": round(t["ctr"] * 100, 2), "position": round(t["position"], 1),
            "by_type": by_type, "top_queries": top, "tracked": tracked,
        }


def collect_sitemaps(site: str) -> list[dict]:
    with _client() as c:
        r = c.get(f"{SA_BASE}/sites/{site}/sitemaps")
        r.raise_for_status()
        out = []
        for s in r.json().get("sitemap", []):
            contents = s.get("contents") or []
            out.append({
                "path": s.get("path"),
                "last_downloaded": (s.get("lastDownloaded") or "")[:10],
                "submitted": sum(int(x.get("submitted", 0)) for x in contents),
                "indexed": sum(int(x.get("indexed", 0)) for x in contents),
                "errors": int(s.get("errors", 0)), "warnings": int(s.get("warnings", 0)),
            })
        return out


def inspect_urls(site: str, urls: list[str]) -> dict:
    """URL 검사 API 로 표본의 색인 상태. verdict: PASS(색인됨) / NEUTRAL(미색인) / FAIL. 하루 한도 2,000건."""
    by_state: dict[str, int] = {}
    indexed = 0
    with _client() as c:
        for u in urls:
            r = c.post(INSPECT_URL, json={"inspectionUrl": u, "siteUrl": site})
            r.raise_for_status()
            res = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
            state = res.get("coverageState") or res.get("verdict") or "UNKNOWN"
            by_state[state] = by_state.get(state, 0) + 1
            if res.get("verdict") == "PASS":
                indexed += 1
    return {"sampled": len(urls), "indexed": indexed, "by_state": by_state}

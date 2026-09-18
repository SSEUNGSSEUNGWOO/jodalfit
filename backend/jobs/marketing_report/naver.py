"""네이버 서치어드바이저 수집 — 공식 API 가 없어 로그인된 브라우저 프로필의 세션으로 콘솔 내부 API 를 호출한다.

1회: `--naver-login` → 창에서 네이버 로그인("로그인 상태 유지" 체크) 후 창을 닫는다. 프로필은 backend/data/naver-profile.
매일: headless 로 사이트 요약 화면을 열어 세션을 살린 뒤, 화면이 쓰는 API 를 같은 세션으로 직접 부른다.
원본 응답은 backend/data/naver/YYYY-MM-DD/*.json 에 남긴다 (형태가 바뀌면 여기서 확인).

엔드포인트 (2026-09-18 확인, {enc}=로그인 사용자 enc_id, {site}=https:%2F%2Fjodalfit.co.kr):
- report/expose/{enc}?site&period=7&device=d&topN=0   → logs[]: 일별 clickCount·exposeCount·ctr·exposedRank
- report/expose/{enc}?site&period=1&device=d&topN=N   → 최신일(meta.latestDate) 상위 querys[]·urls[] (key, 클릭·노출·순위)
- report/crawl/{enc}?site&start_date&end_date&isAlly=false&count=0 → stats[]: 일별 pageCount·sumErrorCount·오류 유형
- report/diagnosis/meta/{enc}?site&startDate&endDate  → meta[].stateCount {1: 색인, 2: 수집제한, 3: 색인제외, 4: SEO}
  (화면 "사이트 진단 > 진단 현황" 라벨로 확인. typeCount 1000=색인된 페이지, 2400=접근 불가, 2500=서버 접근 불가로 수집 실패,
   3003=meta robots로 색인 제외)
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROFILE_DIR = DATA_DIR / "naver-profile"
DUMP_DIR = DATA_DIR / "naver"
BASE = "https://searchadvisor.naver.com"
STATE_LABELS = {"1": "indexed", "2": "crawl_limited", "3": "index_excluded", "4": "seo"}
TOP_N = 50


def login(console_url: str) -> None:
    from playwright.sync_api import sync_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"https://nid.naver.com/nidlogin.login?url={console_url}")
        print("브라우저에서 네이버 로그인('로그인 상태 유지' 체크)을 마친 뒤 창을 닫으세요...")
        while ctx.pages:
            time.sleep(1)
        ctx.close()
    print(f"프로필 저장: {PROFILE_DIR}")


def _ymd(d: date, sep: str = "") -> str:
    return d.strftime(f"%Y{sep}%m{sep}%d")


def collect(site_url: str, day: date, page_types: list[dict], keywords: list[str]) -> dict:
    """site_url 예: https://jodalfit.co.kr. day 는 성적표 날짜(어제)."""
    from playwright.sync_api import sync_playwright

    from .gsc import classify_page

    if not PROFILE_DIR.exists():
        raise RuntimeError("네이버 로그인 프로필 없음 — `--naver-login` 먼저")
    site_q = quote(site_url, safe=":")  # 콘솔이 쓰는 형태: https:%2F%2Fjodalfit.co.kr
    enc: dict[str, str] = {}

    def on_resp(r):
        if r.url.endswith("/api/auth/login-token"):
            try:
                enc["id"] = r.json()["userData"]["enc_id"]
            except Exception:
                pass

    raw: dict[str, dict] = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=True)
        page = ctx.new_page()
        page.on("response", on_resp)
        page.goto(f"{BASE}/console/site/summary?site={quote(site_url, safe='')}", wait_until="networkidle")
        if "nid.naver.com" in page.url or "id" not in enc:
            ctx.close()
            raise RuntimeError("로그인 세션 만료 — `--naver-login` 다시")
        R = f"{BASE}/api-console/report"
        e = enc["id"]
        urls = {
            "expose_daily": f"{R}/expose/{e}?site={site_q}&period=7&device=d&topN=0",
            "expose_top": f"{R}/expose/{e}?site={site_q}&period=1&device=d&topN={TOP_N}",
            "crawl": f"{R}/crawl/{e}?site={site_q}&start_date={_ymd(day - timedelta(days=7))}&end_date={_ymd(day)}&isAlly=false&count=0",
            "diagnosis": f"{R}/diagnosis/meta/{e}?site={site_q}&startDate={_ymd(day - timedelta(days=10))}&endDate={_ymd(day + timedelta(days=1))}",
        }
        for k, u in urls.items():
            r = page.request.get(u)
            raw[k] = r.json() if r.ok else {"http_status": r.status}
        ctx.close()

    out_dir = DUMP_DIR / day.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    for k, b in raw.items():
        (out_dir / f"{k}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")

    def items(k):
        b = raw.get(k) or {}
        return (b.get("items") or [{}])[0] if b.get("code") == 0 else {}

    res: dict = {}

    # 일별 노출·클릭 — 성적표 날짜와 정확히 같은 날
    logs = {x["date"]: x for x in items("expose_daily").get("logs", [])}
    d = logs.get(_ymd(day))
    res["data_date"] = day.isoformat() if d else None
    if d:  # 일별 로그의 exposedRank 는 늘 1이라 쓰지 않는다
        res.update(clicks=d["clickCount"], impressions=d["exposeCount"], ctr=d["ctr"])

    # 최신일 상위 검색어·URL (최신일이 성적표 날짜와 다르면 기준일을 남긴다)
    top = items("expose_top")
    latest = (raw.get("expose_top") or {}).get("meta", {}).get("latestDate")
    res["top_date"] = f"{latest[:4]}-{latest[4:6]}-{latest[6:]}" if latest else None
    queries = top.get("querys", [])
    res["top_queries"] = [
        {"query": q["key"], "clicks": q["clickCount"], "impressions": q["exposeCount"], "position": q["exposedRank"]}
        for q in queries
    ]
    by_type: dict[str, dict] = {}
    for u in top.get("urls", []):
        agg = by_type.setdefault(classify_page(u["key"], page_types), {"clicks": 0, "impressions": 0})
        agg["clicks"] += u["clickCount"]
        agg["impressions"] += u["exposeCount"]
    res["by_type_top"] = by_type
    by_q = {q["key"]: q for q in queries}
    res["tracked"] = {
        k: ({"position": by_q[k]["exposedRank"], "impressions": by_q[k]["exposeCount"], "clicks": by_q[k]["clickCount"]}
            if k in by_q else None)
        for k in keywords
    }

    # 수집 — 성적표 날짜
    stats = {s["date"]: s for s in items("crawl").get("stats", [])}
    s = stats.get(_ymd(day))
    res["crawl"] = {"pages": s["pageCount"], "errors": s["sumErrorCount"],
                    "server_errors": s.get("serverError", 0), "not_found": s.get("notFound", 0)} if s else None

    # 색인 상태 — 성적표 날짜 이하 최신 (네이버 진단은 1~2일 늦게 갱신)
    metas = sorted(items("diagnosis").get("meta", []), key=lambda m: m["date"])
    cutoff = _ymd(day, ".")
    m = next((x for x in reversed(metas) if x["date"] <= cutoff), None)
    res["index"] = ({"date": m["date"].replace(".", "-"),
                     **{STATE_LABELS.get(k, k): v for k, v in m["stateCount"].items()}} if m else None)
    return res

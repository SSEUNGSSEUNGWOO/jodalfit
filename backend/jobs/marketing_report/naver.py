"""네이버 서치어드바이저 수집 — 공식 API 가 없어 로그인된 브라우저 프로필로 콘솔을 열고 XHR JSON 을 가로챈다.

1회: `--naver-login` → 창이 뜨면 네이버 로그인 후 창을 닫는다. 프로필은 backend/data/naver-profile 에 남는다.
매일: headless 로 콘솔 메뉴를 돌며 searchadvisor.naver.com 의 JSON 응답 전부를 backend/data/naver/YYYY-MM-DD/ 에 저장하고,
parse() 가 아는 형태만 숫자로 뽑는다. 응답 형태를 실물로 확정하기 전까지 parse() 는 키 이름 추정 최소 구현이다 —
첫 수집 덤프를 보고 고정한다 (docs/marketing/README.md "네이버 파서 확정").
"""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROFILE_DIR = DATA_DIR / "naver-profile"
DUMP_DIR = DATA_DIR / "naver"
MENU_LABELS = ("요약", "검색어", "콘텐츠 노출", "사이트 진단", "수집", "색인", "사이트맵")


def login(console_url: str) -> None:
    from playwright.sync_api import sync_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"https://nid.naver.com/nidlogin.login?url={console_url}")
        print("브라우저에서 네이버 로그인을 마친 뒤 창을 닫으세요...")
        while ctx.pages:
            time.sleep(1)
        ctx.close()
    print(f"프로필 저장: {PROFILE_DIR}")


def collect(console_url: str, site_domain: str, day: date) -> dict:
    from playwright.sync_api import sync_playwright

    if not PROFILE_DIR.exists():
        raise RuntimeError("네이버 로그인 프로필 없음 — `--naver-login` 먼저")
    dumps: list[dict] = []

    def on_response(resp):
        if "searchadvisor.naver.com" not in resp.url or "json" not in (resp.headers.get("content-type") or ""):
            return
        try:
            dumps.append({"url": resp.url, "body": resp.json()})
        except Exception:
            pass

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=True)
        page = ctx.new_page()
        page.on("response", on_response)
        page.goto(console_url, wait_until="networkidle")
        if "nid.naver.com" in page.url:
            ctx.close()
            raise RuntimeError("로그인 세션 만료 — `--naver-login` 다시")
        site = page.get_by_text(site_domain, exact=False).first
        if site.count():
            site.click()
            page.wait_for_load_state("networkidle")
        for label in MENU_LABELS:
            loc = page.get_by_role("link", name=re.compile(label)).first
            if loc.count():
                loc.click()
                page.wait_for_load_state("networkidle")
                time.sleep(1.5)
        out = DUMP_DIR / day.isoformat()
        out.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out / "last.png"), full_page=True)
        ctx.close()

    for i, d in enumerate(dumps):
        (out / f"{i:02d}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"dumps": len(dumps), "dump_dir": str(out), "parsed": parse(dumps)}


def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v, path + "[]")
    else:
        yield path, o


def parse(dumps: list[dict]) -> dict | None:
    """덤프에서 노출/클릭/색인 수로 보이는 첫 숫자를 키 이름으로 추정. 확정 전 임시."""
    found: dict[str, int | float] = {}
    for d in dumps:
        for path, v in _walk(d["body"]):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            key = path.lower()
            for name, pats in (("impressions", ("impress", "expos", "노출")), ("clicks", ("click", "클릭")),
                               ("indexed", ("index", "색인")), ("crawled", ("crawl", "수집"))):
                if name not in found and any(x in key for x in pats):
                    found[name] = v
    return found or None

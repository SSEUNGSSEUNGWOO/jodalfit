# frontend/scripts/check_entry.py
"""입구 화면(04) 검증 — 시안 gen_entry_v2.py D 안을 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_entry.py
묻는 줄 + 자동완성(두 글자부터·↑↓·Enter) + 판(현황 셋 + 등록 공고), 금지어 0, 주황 면 0, 390 넘침 없음.
캡처: scripts/_shot_entry_{desk,typed,390}.png
"""
import os, re, sys
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
URL = f"{BASE}/"  # 입구는 루트다 — 실사용자 검색의 97.7% 가 여기서 시작한다
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요",
          "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]

RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    over: document.documentElement.scrollWidth > window.innerWidth,
    stats: document.querySelectorAll('[data-entry-panel] .num').length } }"""


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        resp = pg.goto(URL, wait_until="networkidle", timeout=30000)
        # 보안 헤더(next.config.ts SECURITY_HEADERS, 2026-10-26) — 로그인 화면 클릭재킹 차단·MIME 스니핑 금지
        h = {k.lower(): v for k, v in (resp.headers if resp else {}).items()}
        assert h.get("x-frame-options") == "DENY", f"X-Frame-Options 없음: {h.get('x-frame-options')!r}"
        assert h.get("x-content-type-options") == "nosniff", "X-Content-Type-Options 없음"
        assert "frame-ancestors 'none'" in h.get("content-security-policy", ""), "CSP frame-ancestors 없음"
        assert "x-powered-by" not in h, "X-Powered-By 가 노출된다"

        txt = pg.evaluate("document.body.innerText")
        bad = [w for w in BANNED if w in txt]
        assert not bad, f"금지어 {bad}"
        assert "어느" in txt and "찾습니까" in txt, "묻는 줄이 없다"

        s = pg.evaluate(RULES)
        assert s["orangeFaces"] == 0, f"주황 면 {s['orangeFaces']} (주황은 선이지 면이 아니다)"
        assert not s["over"], "가로 넘침"

        nums = pg.evaluate("""() => [...document.querySelectorAll('b.num')].map(e => e.textContent.trim())""")
        assert len(nums) >= 3, f"현황 숫자가 셋이 아니다: {nums}"
        rows = pg.evaluate("() => document.querySelectorAll('ul li').length")
        assert rows >= 1, "등록 공고 목록이 비었다"
        # 등록 공고 행의 제목은 공고 페이지 링크 (2026-10-25 — 그 전엔 번호가 없어 눌러도 갈 데가 없었다)
        href = pg.evaluate("() => document.querySelector('ul li a[href^=\"/notices/\"]')?.getAttribute('href') || ''")
        assert href.startswith("/notices/") and len(href) > len("/notices/"), f"등록 공고 행에 공고 링크가 없다: {href!r}"
        # 마감이 지난 공고가 섞이면 'D--1' 이 찍힌다(재공고·정정 건)
        assert "D--" not in txt, "마감 지난 공고가 목록에 있다"
        pg.screenshot(path=str(OUT / "_shot_entry_desk.png"), full_page=True)

        # 굴러가는가 — 두 글자부터 뜨고 ↑↓·Enter 로 고를 수 있어야 한다
        pg.click("[data-suggest] input")
        pg.type("[data-suggest] input", "엔", delay=20)
        pg.wait_for_timeout(350)
        assert pg.evaluate("() => document.querySelectorAll('[role=option]').length") == 0, "한 글자에 목록이 떴다"
        pg.type("[data-suggest] input", "지니어링", delay=20)
        # 기본 검색 기준은 회사 — 회사 줄이 붙을 때까지 기다린다(디바운스 + 왕복).
        assert pg.get_attribute("[data-suggest]", "data-mode") == "company", "기본 검색 기준이 회사가 아니다"
        pg.wait_for_function("() => document.querySelectorAll('[role=option]').length >= 1", timeout=10000)
        n = pg.evaluate("() => document.querySelectorAll('[role=option]').length")
        assert n >= 1, f"자동완성 {n}행"
        pg.screenshot(path=str(OUT / "_shot_entry_typed.png"))
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(120)
        assert pg.evaluate("() => document.querySelectorAll('[role=option]').length") == 0, "Esc 로 안 닫힌다"

        pg.fill("[data-suggest] input", "한종")  # 다른 회사명을 입력하면 열린다
        pg.wait_for_function("() => document.querySelectorAll('[role=option]').length >= 2", timeout=10000)
        pg.keyboard.press("ArrowDown")
        pg.keyboard.press("Enter")
        pg.wait_for_url(re.compile(r"/recommendations\?company="), timeout=15000)
        picked = pg.url

        # 일치하는 회사가 없으면 '키워드로 찾기' 한 줄만 남고, 고르면 키워드 검색이다.
        pg.goto(URL, wait_until="networkidle", timeout=30000)
        pg.fill("[data-suggest] input", "하수처리시설 관리대행")
        pg.wait_for_function("() => document.querySelectorAll('[role=option]').length === 1", timeout=10000)
        assert "키워드로 찾기" in pg.inner_text("[role=option]"), pg.inner_text("[role=option]")
        pg.keyboard.press("Enter")
        pg.wait_for_url(re.compile(r"/recommendations\?q="), timeout=15000)

        # 키워드 기준: 목록 없이 입력 그대로. 이전 후보가 남아 있어도 새 검색어를 제출해야 한다.
        pg.goto(URL, wait_until="networkidle", timeout=30000)
        pg.fill("[data-suggest] input", "한종")
        pg.wait_for_function("document.querySelectorAll('[role=option]').length >= 2", timeout=10000)
        pg.click("[data-search-mode=keywords]")
        assert pg.evaluate("() => document.querySelectorAll('[role=option]').length") == 0, "키워드 기준인데 회사 목록이 남았다"
        pg.fill("[data-suggest] input", "전기")
        pg.keyboard.press("Enter")
        pg.wait_for_url(re.compile(r"/recommendations\?q="), timeout=15000)
        assert parse_qs(urlsplit(pg.url).query)["q"] == ["전기"], pg.url

        # 자동완성의 두 글자 문턱과 검색 제출은 별개다.
        pg.goto(URL, wait_until="networkidle", timeout=30000)
        pg.click("[data-search-mode=keywords]")
        pg.fill("[data-suggest] input", "물")
        pg.click("[data-suggest] button[type=submit]")
        pg.wait_for_url(re.compile(r"/recommendations\?q="), timeout=15000)
        assert parse_qs(urlsplit(pg.url).query)["q"] == ["물"], pg.url

        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(URL, wait_until="networkidle", timeout=30000)
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        pg2.screenshot(path=str(OUT / "_shot_entry_390.png"), full_page=True)
        b.close()
    print(f"ok entry: 숫자 {nums[:3]} · 목록 {rows}행 · 자동완성 {n}행 · 고르면 {picked.split('?')[-1][:40]}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

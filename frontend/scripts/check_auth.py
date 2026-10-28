# frontend/scripts/check_auth.py
"""로그인·가입·보냄·재설정·약관 화면 검증 — 금지어 0 · 인주 0 · 주황 면 0 · 버튼 활성 조건 · 390.
실행: cd backend && AUTH_URL=http://localhost:3001 uv run --no-sync python ../frontend/scripts/check_auth.py
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("AUTH_URL", "http://localhost:3000")
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "아침 7시", "주십시오"]
OUT = Path(__file__).resolve().parent
RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    bg: cs(document.querySelector('.rn')).backgroundColor, h1: document.querySelector('h1') && cs(document.querySelector('h1')).fontSize } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, f"{pg.url} 금지어 {bad}"
    r = pg.evaluate(RULES); assert r["orangeFaces"] == 0 and not r["injuk"] and r["bg"] == "rgb(250, 249, 247)", (pg.url, r); return r

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None); pg = b.new_page(viewport={"width": 1280, "height": 900})
        dis = lambda: pg.evaluate("document.querySelector('form button[type=submit]').disabled")
        # 로그인 — 이메일·비밀번호 둘 다 있어야 켜짐, 비밀번호 표시 토글, 회원가입 링크에 next 유지
        pg.goto(f"{BASE}/login?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); r = rules(pg); assert r["h1"] == "28px", r
        assert dis(); pg.fill("input[type=email]", "you@company.co.kr"); assert dis(); pg.fill("input[type=password]", "x"); assert not dis()
        pg.click("button[aria-pressed]"); assert pg.evaluate("document.querySelector('input[autocomplete=current-password]').type") == "text"
        assert pg.evaluate("document.querySelector('a[href^=\"/signup?next=\"]').getAttribute('href')") == "/signup?next=%2Fsaved"
        assert pg.evaluate("!!document.querySelector('nav a[href^=\"/login?next=\"]')")   # 레이아웃의 비로그인 nav 링크
        pg.screenshot(path=str(OUT / "_shot_auth_login.png"), full_page=True)
        # 회원가입 — 8자 힌트, 필수 동의 둘 전엔 꺼짐
        pg.goto(f"{BASE}/signup?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); rules(pg)
        pg.fill("input[type=email]", "you@company.co.kr"); pg.fill("input[type=password]", "short"); assert dis()
        assert pg.evaluate("!!document.querySelector('.border-l-2.border-orange')"), "8자 힌트 없음"
        pg.fill("input[type=password]", "longenough1"); assert dis()
        cb = pg.locator("input[type=checkbox]"); assert cb.count() == 3; cb.nth(0).check(); assert dis(); cb.nth(1).check(); assert not dis()
        pg.screenshot(path=str(OUT / "_shot_auth_signup.png"), full_page=True)
        # 보냄 — 이메일 강조 주황 밑줄, 다시 보내기 카운트다운
        pg.goto(f"{BASE}/signup/sent?email=you%40company.co.kr&next=%2Fsaved"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("getComputedStyle(document.querySelector('li b')).borderBottomColor") == "rgb(249, 115, 22)"
        assert "다시 보내기 — " in pg.evaluate("document.body.innerText")
        pg.screenshot(path=str(OUT / "_shot_auth_sent.png"), full_page=True)
        # 재설정 — 이메일 채워짐, 버튼 켜짐
        pg.goto(f"{BASE}/reset?email=you%40company.co.kr"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("document.querySelector('input[type=email]').value") == "you@company.co.kr" and not dis()
        # 새 비밀번호 — 비로그인은 /reset 으로
        pg.goto(f"{BASE}/reset/new"); pg.wait_for_load_state("networkidle"); assert pg.url.rstrip("/").endswith("/reset"), pg.url
        # 소셜 로그인(2026-10-28) — 로그인·가입 둘 다 "Google로 계속" 버튼이 폼 위에, 주황 면 아님. /consent 는 비로그인이면 로그인으로.
        for path in ("/login?next=%2Fsaved", "/signup?next=%2Fsaved"):
            pg.goto(BASE + path); pg.wait_for_load_state("networkidle")
            g = pg.evaluate("""() => { const b = document.querySelector('[data-social-google]'); const f = document.querySelector('form');
                return { txt: b?.innerText.trim(), bg: getComputedStyle(b).backgroundColor, above: b.getBoundingClientRect().bottom <= f.getBoundingClientRect().top } }""")
            assert g["txt"] == "Google로 계속" and g["bg"] == "rgb(255, 255, 255)" and g["above"], (path, g)
        pg.goto(f"{BASE}/consent?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); assert "/login?next=%2Fconsent" in pg.url, pg.url
        pg.goto(f"{BASE}/login?error=oauth"); pg.wait_for_load_state("networkidle"); assert "Google 로그인이 완료되지 않았습니다" in pg.evaluate("document.body.innerText")
        # 우리 회사 저장(/welcome, 2026-10-28) — 비로그인은 로그인으로, next 에 /welcome 을 품는다
        pg.goto(f"{BASE}/welcome?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); assert "/login?next=%2Fwelcome" in pg.url, pg.url
        # 약관
        pg.goto(f"{BASE}/terms"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("document.querySelectorAll('h2').length") >= 10
        pg.screenshot(path=str(OUT / "_shot_auth_terms.png"), full_page=True)
        # 390
        pg.set_viewport_size({"width": 390, "height": 844})
        for path in ("/login", "/signup", "/signup/sent?email=a%40b.c", "/reset", "/terms"):
            pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); assert not pg.evaluate("document.documentElement.scrollWidth > 390"), path
        pg.screenshot(path=str(OUT / "_shot_auth_390.png"), full_page=True)
        b.close()
    print("ok auth pages: login · signup · sent · reset · reset/new guard · terms · 390")

if __name__ == "__main__":
    sys.exit(main())

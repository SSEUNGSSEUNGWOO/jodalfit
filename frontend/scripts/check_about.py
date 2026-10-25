# frontend/scripts/check_about.py
"""서비스 소개(/about) 검증 — 리뉴얼 문법으로 다시 그린 뒤(2026-10-25).

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_about.py   (ABOUT_BASE 기본 http://localhost:3000)
금지어 0, 주황 면 0(로고 타일 제외), 옛 토큰(gc-*) 0, 바닥색, 머리 숫자 넷(… 아님), 예시 표 2행(1행 펼침 + 자격·근거),
점수표 항목 수 = lib/how-we-pick.ts(POSITIVE 6 + NEGATIVE 3), 적합 점수 숫자 비노출, 390 한 단·가로 넘침 없음, favicon.ico 200.
"""
import os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("ABOUT_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오", "적합 72", "검토 여유"]

RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    gc: all.filter(e => [...e.classList].some(c => c.includes('gc-'))).length,
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    nums: [...document.querySelectorAll('dl dd .num')].map(e => e.textContent),
    rows: document.querySelectorAll('[data-sheet-row]').length,
    open: document.querySelectorAll('.x-wrap[data-open=true] li').length,
    factors: document.querySelectorAll('[data-factors] li').length,
    panels: document.querySelectorAll('section.rounded-\\\\[14px\\\\], section[class*="rounded-"]').length,
    score: /적합\\s*\\d{2}/.test(document.body.innerText) } }"""

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None); pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(BASE + "/about"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, bad
        s = pg.evaluate(RULES)
        assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and s["gc"] == 0 and not s["overflow"], s
        assert len(s["nums"]) == 4 and "…" not in "".join(s["nums"]), s["nums"]
        assert s["rows"] == 2 and s["open"] >= 4 and s["factors"] == 9 and s["panels"] >= 5 and not s["score"], s
        assert pg.locator('link[rel="icon"][href*="favicon.ico"]').count() >= 1, "favicon.ico 링크가 없다"
        with urllib.request.urlopen(BASE + "/favicon.ico") as r:
            assert r.status == 200 and r.read(4) == b"\x00\x00\x01\x00", "favicon.ico 가 ICO 가 아니다"
        pg.screenshot(path=str(OUT / "_shot_about_default.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(300)
        m = pg.evaluate(RULES); assert not m["overflow"] and m["orangeFaces"] == 0, m
        pg.screenshot(path=str(OUT / "_shot_about_390.png"), full_page=True)
        b.close()
    print("ok about: 금지어 0 · 주황 면 0 · gc 0 · 숫자 4 · 예시 2행 · 점수표 9 · favicon.ico · 390"); return 0

if __name__ == "__main__":
    sys.exit(main())

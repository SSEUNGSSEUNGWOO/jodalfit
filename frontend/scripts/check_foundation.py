# frontend/scripts/check_foundation.py
"""/dev/foundation 검증 — 금지어 0 · 인주 0 · 주황 면 0(로고 타일 제외) · 핵심 요소 · 펼침 · 메뉴 · 390.
실행: cd backend && uv run --no-sync python ../frontend/scripts/check_foundation.py  (frontend 에서 npm run dev 가 떠 있어야 한다)
주소: 환경변수 FOUNDATION_URL (기본 http://localhost:3000/dev/foundation)
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get("FOUNDATION_URL", "http://localhost:3000/dev/foundation")
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "아침 7시"]
OUT = Path(__file__).resolve().parent

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(URL); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, f"금지어 {bad}"
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e);
            // 주황 면 금지 — 실제 요소의 배경만 본다. ::before/::after 는 못 본다(검토 행 왼쪽 2px 괘선 before:bg-orange 는 '선'이라 허용 대상)
            const orangeFaces = [...document.querySelectorAll('body *')].filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length;
            // 인주 #e8431b 금지 — border 는 shorthand 가 아니라 네 변 longhand 로 본다(한 변만 색이 있으면 shorthand 는 다중값이라 못 잡는다)
            const injuk = [...document.querySelectorAll('body *')].some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); });
            const h1 = document.querySelector('h1'); const head = h1.closest('.rule-ink');
            return { bg: cs(document.querySelector('.rn')).backgroundColor, orangeFaces, injuk,
              rule: cs(head).borderBottomColor, h1: cs(h1).fontSize, panel: cs(document.querySelector('section')).backgroundColor, radius: cs(document.querySelector('section')).borderRadius,
              rows: document.querySelectorAll('button.num[aria-expanded]').length, open: document.querySelectorAll('.x-wrap[data-open=true]').length,
              gateBtns: document.querySelectorAll('.hairline a[href^="/login"], .hairline a[href^="/signup"]').length, fade: document.querySelectorAll('[inert] > [data-sheet-row]').length,
              login: !!document.querySelector('nav a[href^="/login?next="]') } }""")
        assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"], s
        assert s["rule"] == "rgb(20, 20, 20)" and s["h1"] == "32px" and s["panel"] == "rgb(255, 255, 255)" and s["radius"] == "14px", s
        assert s["rows"] >= 1 and s["open"] == 1 and s["gateBtns"] == 2 and s["fade"] >= 2 and s["login"], s   # 게이트 두 버튼(로그인됨이라 nav 에는 로그인 링크 없음)
        pg.locator("button.num[aria-expanded]").first.click(); pg.wait_for_timeout(500)   # 1행 접힘
        assert pg.evaluate("document.querySelectorAll('.x-wrap[data-open=true]').length") == 0
        pg.screenshot(path=str(OUT / "_shot_foundation.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)
        mo = pg.evaluate("""() => ({ overflow: document.documentElement.scrollWidth > 390, radius: getComputedStyle(document.querySelector('section')).borderRadius,
            priceHidden: getComputedStyle(document.querySelector('[data-sheet-row]').children[3]).display === 'none' })""")
        assert not mo["overflow"] and mo["radius"] == "12px" and mo["priceHidden"], mo
        pg.screenshot(path=str(OUT / "_shot_foundation_390.png"), full_page=True)
        b.close()
    print("ok foundation: tokens · head rule · panel · sheet(open/close) · gate · fade · nav login · 390")

if __name__ == "__main__":
    sys.exit(main())

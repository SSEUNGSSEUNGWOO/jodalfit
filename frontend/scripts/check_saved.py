# frontend/scripts/check_saved.py
"""검토함(03) 화면 검증 — 시안 gen_saved.py --check 를 옮긴 것.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_saved.py
주소: SAVED_BASE (기본 http://localhost:3000). 3000 이 다른 프로젝트면 SAVED_BASE=http://localhost:3001.

비로그인: /saved 안내 판(버튼 2, 탭 0), 금지어 0, 주황 면 0, 인주 0, 바닥색, 390 가로 넘침 없음.
로그인(키 있을 때만): Admin API 로 사용자 생성 → /login 폼 → /dev/foundation 에서 ☆·검토 → /saved 공고 1(★ 칩·근거)·회사 1(★)
→ 해제 → 흐림+되돌리기 → 되돌리기 → 390 에서 추정가·해제 열 숨김 → 사용자 삭제.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("SAVED_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요", "검토 인장", "낼 수 있", "메모", "폴더", "매직링크", "회사 연결", "주십시오"]

def env(path, key):
    m = re.search(rf"^{key}=(.*)$", Path(path).read_text(encoding="utf-8"), re.M) if Path(path).exists() else None
    return m.group(1).strip().strip('"') if m else None

RULES = """() => { const cs = e => getComputedStyle(e);
  const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    overflow: document.documentElement.scrollWidth > window.innerWidth } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText")
    bad = [w for w in BANNED if w in txt]
    assert not bad, f"금지어 {bad} @ {pg.url}"
    s = pg.evaluate(RULES)
    assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"] and not s["overflow"], (pg.url, s)

def goto(pg, path):
    pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(400)

def admin(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/auth/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_URL")
    anon = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900})

        # ── 비로그인
        goto(pg, "/saved"); rules(pg)
        g = pg.evaluate("""() => ({ btns: document.querySelectorAll('[data-saved-gate] a[href^="/login?next="], [data-saved-gate] a[href^="/signup?next="]').length,
            tabs: document.querySelectorAll('[role=tab]').length, h1: document.querySelector('h1').textContent })""")
        assert g["btns"] == 2 and g["tabs"] == 0 and g["h1"] == "검토함", g
        pg.screenshot(path=str(OUT / "_shot_saved_guest.png"))
        goto(pg, "/dev/foundation")
        assert pg.evaluate("!!document.querySelector('[data-star=guest][href^=\"/login?next=\"]') && !!document.querySelector('[data-review=guest][href^=\"/login?next=\"]')"), "foundation guest links"
        pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/saved"); rules(pg)
        pg.set_viewport_size({"width": 1280, "height": 900})

        if not (url and anon and srv):
            b.close()
            print("ok saved(guest): gate 2 buttons · tabs 0 · foundation guest links · 390 — 로그인 검사 건너뜀(키 없음)")
            return 0

        # ── 로그인
        email, pw_ = "check-saved@jodalfit.test", "check-saved-pw-1"
        for u in admin(url, srv, "GET", "/admin/users?per_page=200").get("users", []):
            if u.get("email") == email: admin(url, srv, "DELETE", f"/admin/users/{u['id']}")
        user = admin(url, srv, "POST", "/admin/users", {"email": email, "password": pw_, "email_confirm": True})
        try:
            goto(pg, "/login?next=%2Fdev%2Ffoundation")
            pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw_); pg.click("button[type=submit]")
            pg.wait_for_url(re.compile(r"/dev/foundation")); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
            pg.click("[data-star=off]"); pg.wait_for_selector("[data-star=on]"); pg.wait_for_timeout(800)
            if pg.evaluate("document.querySelectorAll('.x-wrap[data-open=true]').length") == 0:
                pg.locator("button.num[aria-expanded]").first.click(); pg.wait_for_timeout(300)
            pg.click("[data-review=off]"); pg.wait_for_selector("[data-review=on]"); pg.wait_for_timeout(800)

            goto(pg, "/saved"); rules(pg)
            s = pg.evaluate("""() => ({ tabs: [...document.querySelectorAll('[role=tab] small')].map(e => e.textContent),
                rows: document.querySelectorAll('#pane-n [data-saved-row]').length,
                star: getComputedStyle(document.querySelector('#pane-n [data-saved-row] span span span'), '::before').color,
                past: !!document.querySelector('#pane-n [data-saved-past] [data-saved-row]'),
                why: !!document.querySelector('#pane-n [data-saved-row] [class*="rounded-"]') })""")
            assert s["rows"] == 1 and s["tabs"][1] == "1", s
            assert s["past"] or (s["tabs"][0] == "1" and s["star"] == "rgb(249, 115, 22)" and s["why"]), s  # 마감 지남이면 ★ 회색·live 0·근거 칩 없음이 정상
            pg.screenshot(path=str(OUT / "_shot_saved_notices.png"), full_page=True)
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            u = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); return { op: getComputedStyle(r).opacity, t: r.querySelector('[data-unreview]').textContent } }""")
            assert float(u["op"]) < 0.5 and u["t"] == "되돌리기", u
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            assert pg.evaluate("document.querySelector('#pane-n [data-unreview]').textContent") == "해제"

            pg.click("#tab-c"); pg.wait_for_timeout(200)
            c = pg.evaluate("""() => ({ shown: !document.getElementById('pane-c').hidden, rows: document.querySelectorAll('#pane-c [data-saved-company]').length,
                name: document.querySelector('#pane-c [data-saved-company] span span').textContent, result: !!document.querySelector('#pane-c a[href="/companies/1248177731"]') })""")
            assert c["shown"] and c["rows"] == 1 and "한종산업개발" in c["name"] and c["result"], c
            pg.screenshot(path=str(OUT / "_shot_saved_companies.png"), full_page=True)

            pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/saved"); rules(pg)
            m = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); const ch = r.children;
                return { price: getComputedStyle(ch[2]).display, un: getComputedStyle(ch[3]).display } }""")
            assert m["price"] == "none" and m["un"] == "none", m
            pg.screenshot(path=str(OUT / "_shot_saved_390.png"), full_page=True)

            # 메뉴 ★ 목록·검토 건수 (Nav)
            pg.set_viewport_size({"width": 1280, "height": 900}); goto(pg, "/saved")
            pg.click("nav button[aria-controls=nav-user-menu]"); pg.wait_for_timeout(200)
            n = pg.evaluate("""() => ({ star: document.querySelectorAll('[data-menu] a[href^="/companies/1248177731"]').length,
                cnt: [...document.querySelectorAll('[data-menu] small')].map(e => e.textContent).find(t => t.includes('검토한 공고')) })""")
            assert n["star"] == 1 and n["cnt"] == "검토한 공고 1건", n
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{user['id']}")
        b.close()
        print("ok saved: guest gate · login · ☆ · 검토 · notices 1(★·why) · 해제/되돌리기 · companies 1 · nav ★ 1/검토 1건 · 390 cols hidden · banned 0")
        return 0

if __name__ == "__main__":
    sys.exit(main())

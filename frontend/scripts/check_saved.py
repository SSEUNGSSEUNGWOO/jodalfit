# frontend/scripts/check_saved.py
"""검토함(03) 화면 검증 — 시안 gen_saved.py --check 를 옮긴 것.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_saved.py
주소: SAVED_BASE (기본 http://localhost:3000). 3000 이 다른 프로젝트면 SAVED_BASE=http://localhost:3001.

비로그인: /saved 안내 판(버튼 2, 탭 0), 금지어 0, 주황 면 0, 인주 0, 바닥색, 390 가로 넘침 없음.
로그인(키 있을 때만): Admin API 로 사용자 생성 → /login 폼 → /dev/foundation 에서 ☆·검토 → /saved 공고 1(★ 칩·근거)·회사 1(★)
→ 해제 → 흐림+되돌리기 → 되돌리기 → 390 에서 추정가·해제·회사 결과 확인 → 사용자 삭제.
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

            # 우리 회사 저장(/welcome, 2026-10-28) — 저장 회사 0곳이면 폼, 목록에서 고르면 saved_companies 에 넣고 검토함으로. 1곳이라도 있으면 next 로.
            goto(pg, "/welcome"); rules(pg)
            assert pg.url.endswith("/welcome") and pg.evaluate("!!document.querySelector('[data-save-company] [data-suggest][data-mode=company]') && !!document.querySelector('[data-welcome-skip]')"), pg.url
            pg.fill("[data-save-company] input[role=combobox]", "케이브레인컴퍼니"); pg.wait_for_selector("[data-save-company] [role=option]")
            assert "키워드로 찾기" not in pg.inner_text("[data-save-company]"), "저장 폼에 키워드 폴백이 떴다"
            assert pg.inner_text("[data-save-company] button[type=submit]").strip() == "저장", "저장 폼 버튼 글자"
            pg.keyboard.press("Enter"); pg.wait_for_url(re.compile(r"/saved$")); pg.wait_for_load_state("networkidle")
            pg.click("#tab-c"); pg.wait_for_timeout(200)
            assert pg.evaluate("document.querySelectorAll('#pane-c [data-saved-company]').length") == 1 and "케이브레인컴퍼니" in pg.inner_text("#pane-c [data-saved-company] a"), "welcome 저장이 검토함에 없다"
            goto(pg, "/welcome"); assert not pg.url.endswith("/welcome"), f"저장 회사가 있는데 /welcome 이 떴다 {pg.url}"
            # 빈 상태로 되돌린다(해제) — 아래 검사는 회사 1곳(한종산업개발) 기준. 빈 상태엔 같은 폼이 있다.
            goto(pg, "/saved"); pg.click("#tab-c"); pg.click("[data-unstar]"); pg.wait_for_timeout(500); goto(pg, "/saved"); pg.click("#tab-c"); pg.wait_for_timeout(200)
            assert pg.evaluate("!!document.querySelector('[data-saved-empty] [data-save-company]')"), "빈 상태에 저장 폼이 없다"
            pg.fill("[data-save-company] input[role=combobox]", "없는회사이름zz"); pg.keyboard.press("Enter"); pg.wait_for_selector("[data-save-company][data-state=notfound]")
            rules(pg)

            goto(pg, "/dev/foundation")
            pg.click("[data-star=off]"); pg.wait_for_selector("[data-star=on]"); pg.wait_for_timeout(800)
            if pg.evaluate("document.querySelectorAll('.x-wrap[data-open=true]').length") == 0:
                pg.locator("button.num[aria-expanded]").first.click(); pg.wait_for_timeout(300)
            pg.click("[data-review=off]"); pg.wait_for_selector("[data-review=on]"); pg.wait_for_timeout(800)

            goto(pg, "/saved"); rules(pg)
            # 주간 메일 줄(2026-10-27) — 가입 동의값을 보여주고 같은 폼으로 바꾼다. 토글 한 번 → 상태가 뒤집히고 /saved 로 돌아온다.
            w0 = pg.evaluate("document.querySelector('[data-weekly-mail]')?.dataset.on"); assert w0 in ("0", "1"), "주간 메일 줄이 없다"
            # 토글은 role=switch 버튼(2026-10-28). aria-checked 가 data-on 과 같고, 켜짐 면은 먹색이지 주황이 아니다.
            sw = pg.evaluate("""() => { const b = document.querySelector('[data-weekly-switch]'); const c = getComputedStyle(b);
                return { role: b.getAttribute('role'), checked: b.getAttribute('aria-checked'), bg: c.backgroundColor, w: b.offsetWidth, h: b.offsetHeight } }""")
            assert sw["role"] == "switch" and sw["checked"] == ("true" if w0 == "1" else "false"), f"주간 메일 스위치 상태 불일치 {sw}"
            assert sw["bg"] != "rgb(249, 115, 22)" and sw["w"] >= 36 and sw["h"] >= 20, f"주간 메일 스위치 모양 {sw}"
            pg.click("[data-weekly-switch]"); pg.wait_for_url(re.compile(r"/saved$")); pg.wait_for_load_state("networkidle")
            assert pg.evaluate("document.querySelector('[data-weekly-mail]')?.dataset.on") == ("0" if w0 == "1" else "1"), "주간 메일 토글이 안 바뀐다"
            assert pg.evaluate("document.querySelector('[data-weekly-switch]')?.getAttribute('aria-checked')") == ("false" if w0 == "1" else "true"), "스위치 aria-checked 가 안 바뀐다"
            s = pg.evaluate("""() => ({ tabs: [...document.querySelectorAll('[role=tab] small')].map(e => e.textContent),
                rows: document.querySelectorAll('#pane-n [data-saved-row]').length,
                star: getComputedStyle(document.querySelector('#pane-n [data-saved-row] span span span'), '::before').color,
                past: !!document.querySelector('#pane-n [data-saved-past] [data-saved-row]'),
                why: !!document.querySelector('#pane-n [data-saved-row] [class*="rounded-"]') })""")
            assert s["rows"] == 1 and s["tabs"][1] == "1", s
            assert s["past"] or (s["tabs"][0] == "1" and s["star"] == "rgb(184, 85, 16)" and s["why"]), s  # 마감 지남이면 ★ 회색·live 0·근거 칩 없음이 정상
            pg.screenshot(path=str(OUT / "_shot_saved_notices.png"), full_page=True)
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            u = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); return { op: getComputedStyle(r).opacity, t: r.querySelector('[data-unreview]').textContent } }""")
            assert float(u["op"]) < 0.5 and u["t"] == "되돌리기", u
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            assert pg.evaluate("document.querySelector('#pane-n [data-unreview]').textContent") == "해제"

            pg.click("#tab-c"); pg.wait_for_timeout(200)
            c = pg.evaluate("""() => ({ shown: !document.getElementById('pane-c').hidden, rows: document.querySelectorAll('#pane-c [data-saved-company]').length,
                name: document.querySelector('#pane-c [data-saved-company] a').textContent, result: !!document.querySelector('#pane-c a[href="/companies/1248177731"]') })""")
            assert c["shown"] and c["rows"] == 1 and "한종산업개발" in c["name"] and c["result"], c
            pg.screenshot(path=str(OUT / "_shot_saved_companies.png"), full_page=True)

            pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/saved"); rules(pg)
            m = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); const ch = r.children;
                return { price: getComputedStyle(ch[2]).display, un: getComputedStyle(ch[3]).display } }""")
            assert m["price"] != "none" and m["un"] != "none", m
            pg.click("[data-unreview]"); pg.wait_for_timeout(500)
            assert pg.locator("[data-unreview]").inner_text() == "되돌리기"
            pg.click("[data-unreview]"); pg.wait_for_timeout(500)
            pg.click("#tab-c")
            assert pg.locator("#pane-c a").first.is_visible()
            assert pg.locator("[data-unstar]").is_visible()
            pg.click("[data-unstar]"); pg.wait_for_timeout(500)
            assert pg.locator("[data-unstar]").inner_text() == "되돌리기"
            pg.click("[data-unstar]"); pg.wait_for_timeout(500)
            pg.click("#tab-n"); rules(pg)
            # 계정 글자(2026-10-28) — 390 은 "계정", 데스크톱은 메일 앞부분 10자까지 + "@…"
            assert pg.inner_text("[data-nav-account]").strip() == "계정", pg.inner_text("[data-nav-account]")
            pg.screenshot(path=str(OUT / "_shot_saved_390.png"), full_page=True)

            # 메뉴 ★ 목록·검토 건수 (Nav)
            pg.set_viewport_size({"width": 1280, "height": 900}); goto(pg, "/saved")
            assert pg.inner_text("[data-nav-account]").strip() == "check-sav…", pg.inner_text("[data-nav-account]")  # check-saved 는 11자라 9자 + …
            pg.click("nav button[aria-controls=nav-user-menu]"); pg.wait_for_timeout(200)
            n = pg.evaluate("""() => ({ star: document.querySelectorAll('[data-menu] a[href^="/companies/1248177731"]').length,
                cnt: [...document.querySelectorAll('[data-menu] small')].map(e => e.textContent).find(t => t.includes('검토한 공고')) })""")
            assert n["star"] == 1 and n["cnt"] == "검토한 공고 1건", n
            assert pg.locator('[data-menu] a[href="/settings"]').count() == 0
            goto(pg, "/companies/1248177731")
            assert pg.locator("[data-star=on]").is_visible(), "회사 상세에 저장 상태가 반영되지 않았다"
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{user['id']}")
        b.close()
        print("ok saved: guest gate · login · ☆ · 검토 · notices 1(★·why) · 해제/되돌리기 · companies 1 · nav ★ 1/검토 1건 · 390 actions · banned 0")
        return 0

if __name__ == "__main__":
    sys.exit(main())

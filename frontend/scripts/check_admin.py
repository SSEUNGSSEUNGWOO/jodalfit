# frontend/scripts/check_admin.py
"""관리 페이지(/admin) 검증 — 읽기 전용 운영 숫자, 관리자만.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_admin.py
주소: ADMIN_BASE (기본 http://localhost:3000).

비로그인: /admin 은 404(403 아님 — 경로 존재를 알리지 않는다). robots.txt 에 admin 이 없다.
로그인(키 있을 때만): 서버가 ADMIN_EMAILS 에 `@jodalfit.test` 주소를 갖고 있어야 한다 — ADMIN_TEST_EMAIL 로 알려 준다(기본 check-admin@jodalfit.test).
  Admin API 로 그 사용자 생성 → /login → /admin 200 · 판 8(깔때기·방문·건강·0건·가입자·검색·저장·검토) · 깔때기 7 + 날짜별 7행 · 건강 3 ·
  방문 판은 PostHog 키 없으면 "미설정" 한 줄, 있으면 표 3 · 가입자 표에 본인(마스킹) ·
  원문 이메일 비노출 · 금지어 0 · 주황 면 0 · 390 → 일반 사용자는 404 → 사용자 삭제.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("ADMIN_BASE", "http://localhost:3000")
ADMIN_EMAIL = os.environ.get("ADMIN_TEST_EMAIL", "check-admin@jodalfit.test")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요", "검토 인장", "낼 수 있", "매직링크", "회사 연결", "주십시오", "넣으면"]

def env(path, key):
    m = re.search(rf"^{key}=(.*)$", Path(path).read_text(encoding="utf-8"), re.M) if Path(path).exists() else None
    return m.group(1).strip().strip('"') if m else None

RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    overflow: document.documentElement.scrollWidth > window.innerWidth } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText")
    bad = [w for w in BANNED if w in txt]
    assert not bad, f"금지어 {bad} @ {pg.url}"
    s = pg.evaluate(RULES)
    assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["overflow"], (pg.url, s)
    return txt

def goto(pg, path):
    r = pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(400)
    return r

def admin(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/auth/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")

def login(pg, email, pw_):
    goto(pg, "/login?next=%2Fsaved")
    pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw_); pg.click("button[type=submit]")
    pg.wait_for_url(re.compile(r"/saved")); pg.wait_for_load_state("networkidle")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    anon = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900})

        # ── 비로그인: 404, robots 에 없음
        r = goto(pg, "/admin")
        assert r.status == 404, f"비로그인 /admin 이 {r.status} (404 여야 한다)"
        robots = pg.request.get(BASE + "/robots.txt").text()
        assert "admin" not in robots, "robots.txt 에 admin 이 있다 — 경로를 광고하지 않는다"

        if not (url and anon and srv):
            b.close()
            print("ok admin(guest): 404 · robots 에 없음 — 로그인 검사 건너뜀(키 없음)")
            return 0

        pw_ = "check-admin-pw-1"
        users = admin(url, srv, "GET", "/admin/users?per_page=200").get("users", [])
        for u in users:
            if u.get("email") in (ADMIN_EMAIL, "check-admin-user@jodalfit.test"): admin(url, srv, "DELETE", f"/admin/users/{u['id']}")
        a = admin(url, srv, "POST", "/admin/users", {"email": ADMIN_EMAIL, "password": pw_, "email_confirm": True})
        n = admin(url, srv, "POST", "/admin/users", {"email": "check-admin-user@jodalfit.test", "password": pw_, "email_confirm": True})
        try:
            # ── 관리자
            login(pg, ADMIN_EMAIL, pw_)
            r = goto(pg, "/admin")
            assert r.status == 200, f"관리자 /admin 이 {r.status} — 서버 ADMIN_EMAILS 에 {ADMIN_EMAIL} 가 있어야 한다"
            txt = rules(pg)
            s = pg.evaluate("""() => ({ panels: [...document.querySelectorAll('[data-admin]')].map(e => e.dataset.admin),
                funnel: document.querySelectorAll('[data-admin=funnel] dl dt').length,
                daily: document.querySelectorAll('[data-admin-daily] tbody tr').length,
                health: document.querySelectorAll('[data-admin=health] dt').length,
                visitsText: document.querySelector('[data-admin=visits]').innerText,
                h1: document.querySelector('h1').textContent.trim() })""")
            assert s["panels"] == ["funnel", "visits", "health", "zero", "feedback", "users", "searches", "saved", "reviewed"], s
            assert s["funnel"] == 7 and s["daily"] == 7 and s["health"] == 3 and s["h1"].startswith("관리"), s
            # PostHog 키가 없으면 안내 한 줄, 있으면 세 표(날짜·페이지·유입)
            assert ("미설정" in s["visitsText"]) or ("유입" in s["visitsText"] and "페이지뷰" in s["visitsText"]), s["visitsText"][:200]
            assert "ch***@jodalfit.test" in txt, "가입자 표에 본인(마스킹)이 없다"
            assert ADMIN_EMAIL not in txt.replace("ch***@jodalfit.test", ""), "원문 이메일이 화면에 보인다"
            pg.screenshot(path=str(OUT / "_shot_admin.png"), full_page=True)
            pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/admin"); rules(pg)
            pg.screenshot(path=str(OUT / "_shot_admin_390.png"), full_page=True)
            pg.set_viewport_size({"width": 1280, "height": 900})

            # ── 일반 사용자: 404
            # /logout 은 sec-fetch-site 가 same-origin 일 때만 세션을 지운다(주소창 직접 입력은 none) — 페이지 안에서 이동시킨다
            pg.evaluate("location.href = '/logout'"); pg.wait_for_url(re.compile(r"logout=1")); pg.wait_for_load_state("networkidle")
            login(pg, "check-admin-user@jodalfit.test", pw_)
            r = goto(pg, "/admin")
            assert r.status == 404, f"일반 사용자 /admin 이 {r.status} (404 여야 한다)"
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{a['id']}")
            admin(url, srv, "DELETE", f"/admin/users/{n['id']}")
        b.close()
        print("ok admin: guest 404 · robots 없음 · 관리자 200 · 판 9 · 깔때기 7+일별 7 · 건강 3 · 방문 판 · 의견 판 · 마스킹 · 390 · 일반 사용자 404")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

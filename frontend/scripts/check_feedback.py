# frontend/scripts/check_feedback.py
"""의견 보내기(/feedback) 검증 — 폼 → 백엔드 POST /feedback → feedback 테이블(0061).

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_feedback.py
주소: FEEDBACK_BASE (기본 http://localhost:3000). 백엔드(:8000)가 떠 있어야 한다.

화면: 금지어 0 · 주황 면 0 · 390 가로 넘침 없음 · 종류 3 · 보내기는 내용 5자 전엔 비활성 · 푸터·소개 페이지에 /feedback 링크.
전송: 시험 문구를 보내 "받았습니다" 확인 → service_role 로 행이 들어왔는지(kind·email·page) 확인 → 그 행 삭제.
허니팟: website 칸을 채워 보내면 200 이지만 행이 생기지 않는다.
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("FEEDBACK_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요", "검토 인장", "낼 수 있", "매직링크", "회사 연결", "주십시오", "넣으면"]
MARK = f"check-feedback {int(time.time())}"

def env(path, key):
    import re
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

def rest(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/rest/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"[]")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "backend/.env", "SUPABASE_URL"); srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900})

        # 링크 — 푸터·소개
        pg.goto(f"{BASE}/about", wait_until="networkidle")
        assert pg.locator('footer a[href="/feedback?from=%2Fabout"]').count() == 1, "푸터 링크가 /feedback?from=/about 이 아니다"
        assert pg.locator('main a[href^="/feedback"]').count() >= 1, "소개 페이지 연락처에 /feedback 링크가 없다"
        pg.click('footer a[href="/feedback?from=%2Fabout"]'); pg.wait_for_url(re.compile(r"/feedback")); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.locator("input[name=kind]").count() == 3, "종류 3개가 아니다"
        assert pg.locator("button[type=submit]").is_disabled(), "내용 없이 보내기가 활성이다"
        pg.fill("textarea", MARK + " — 회사 검색 결과에 다른 지역 공고가 섞입니다.")
        pg.click("label:has-text('오류 제보')")
        pg.fill("input[type=email]", "check-feedback@jodalfit.test")
        assert pg.locator("button[type=submit]").is_enabled()
        pg.screenshot(path=str(OUT / "_shot_feedback.png"), full_page=True)
        pg.click("button[type=submit]")
        pg.wait_for_selector("[data-feedback-done]", timeout=30000); rules(pg)
        assert "받았습니다" in pg.evaluate("document.body.innerText")

        pg2 = b.new_page(viewport={"width": 390, "height": 844})
        pg2.goto(f"{BASE}/feedback", wait_until="networkidle"); rules(pg2)
        pg2.screenshot(path=str(OUT / "_shot_feedback_390.png"), full_page=True)

        if not (url and srv):
            b.close(); print("ok feedback(화면): 링크 · 종류 3 · 전송 '받았습니다' · 390 — DB 확인 건너뜀(키 없음)"); return 0

        rows = rest(url, srv, "GET", f"/feedback?select=id,kind,message,email,page&message=like.*{MARK.replace(' ', '%20')}*")
        try:
            assert len(rows) == 1, f"feedback 행 {len(rows)}개"
            r = rows[0]
            assert r["kind"] == "bug" and r["email"] == "check-feedback@jodalfit.test" and r["page"] == "/about", r
            # 허니팟 — 채우면 저장되지 않는다
            pg.goto(f"{BASE}/feedback", wait_until="networkidle")
            pg.fill("textarea", MARK + " honeypot 시험 문구입니다")
            pg.evaluate("document.querySelector('input[name=website]').value = 'http://spam.example'")
            pg.click("button[type=submit]"); pg.wait_for_selector("[data-feedback-done]", timeout=30000)
            rows2 = rest(url, srv, "GET", f"/feedback?select=id&message=like.*honeypot%20{MARK.split()[1]}*")
            assert len(rows2) == 0, "허니팟을 채운 전송이 저장됐다"
        finally:
            for r in rows:
                rest(url, srv, "DELETE", f"/feedback?id=eq.{r['id']}")
        b.close()
    print("ok feedback: 푸터·소개 링크 · 종류 3 · 비활성→활성 · 전송 '받았습니다' · DB 행(kind·email·page) · 허니팟 미저장 · 390 · 금지어 0")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

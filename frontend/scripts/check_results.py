# frontend/scripts/check_results.py
"""결과 페이지(05) 검증 — 시안 gen_results_final.py --check 를 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_results.py   (RESULTS_BASE 기본 http://localhost:3000)
회사 1248177731(한종산업개발): 장면 → 건너뛰기 → done, 숫자 넷(… 아님), 표 5 + 게이트 2버튼 + 흐림 ≥1, 행 펼침에 자격·근거 줄,
다른 회사 → 상자·흐림 → Esc 복귀, 금지어·주황 면·인주 0, 바닥색·판 14px, 390 한 단·넘침 없음.
키워드(하수처리): 장면 없음, 표 ≥1. 업종 0건 회사(4191800117): 면허 판정 불가 안내 줄. 로그인(키 있으면): 게이트 없음·20행, 검토 → 괘선, 보고서.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent; ROOT = OUT.parent.parent
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]
CO = "1248177731"
NO_IND = "3208703862"   # 지안관리 주식회사 — 나라장터 등록업종 0건 (면허 확인불가 안내 줄 검사용). 2026-10-26 교체: 전 기준(유원디자인연구소)에 업종 10건이 들어왔다. 실패하면 업종이 생긴 것 — companies 에서 company_industries 행 없는 회사로 바꾼다

def env(path, key):
    m = re.search(rf"^{key}=(.*)$", Path(path).read_text(encoding="utf-8"), re.M) if Path(path).exists() else None
    return m.group(1).strip().strip('"') if m else None

RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    overflow: document.documentElement.scrollWidth > window.innerWidth } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, (bad, pg.url)
    s = pg.evaluate(RULES); assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"] and not s["overflow"], (pg.url, s)

def goto(pg, path, wait=600):
    pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(wait)

def wait_done(pg):
    pg.wait_for_selector("[data-scene][data-done=true], [data-err]", timeout=30000)
    assert not pg.query_selector("[data-err]"), "오류 상태 — 백엔드(:8000) 확인"
    # 건너뛰기는 장면만 끝낸다. 데이터는 화면의 8초 제한까지 기다린다.
    pg.wait_for_selector("[data-res], [data-err]", timeout=10000)
    assert not pg.query_selector("[data-err]"), "추천 데이터 조회 실패"
    pg.wait_for_timeout(700)

def admin(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/auth/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b"{}")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_URL"); anon = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY"); srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None); pg = b.new_page(viewport={"width": 1280, "height": 900})

        # 회사 모드 — 장면 진행 중 건너뛰기 (networkidle 을 기다리면 로컬 백엔드가 이미 스트림을 끝내버린다 — mount 직후 확인)
        pg.goto(BASE + f"/recommendations?company={CO}"); pg.wait_for_selector("[data-scene]", timeout=10000)
        assert not pg.query_selector("[data-scene][data-done=true]"), "장면이 먼저 보여야 한다"
        pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg); rules(pg)
        s = pg.evaluate("""() => ({ nums: [...document.querySelectorAll('[data-funnel] b[data-n]')].map(e => e.textContent), acc: getComputedStyle(document.querySelector('[data-funnel] b[data-n="3"]')).color,
            rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, gate: document.querySelectorAll('.hairline a[href^="/login"], .hairline a[href^="/signup"]').length,
            fade: document.querySelectorAll('[inert] [data-sheet-row]').length, side: document.querySelector('[data-side]').open,
            panel: getComputedStyle(document.querySelector('[data-res]')).backgroundColor, radius: getComputedStyle(document.querySelector('[data-res]')).borderRadius,
            quals: document.querySelectorAll('.x-wrap[data-open=true] li').length, star: !!document.querySelector('[data-star]'), other: !!document.querySelector('[data-other]') })""")
        # 글자용 주황(--color-orange-ink #b85510) — 브랜드 주황 #f97316 은 종이색 위 대비가 2.66:1 이라
        # 글자로 쓸 수 없다(2026-10-23 Lighthouse). 선·테두리·로고 타일은 여전히 #f97316.
        assert "…" not in s["nums"] and s["acc"] == "rgb(184, 85, 16)", s
        assert s["rows"] >= 6 and s["gate"] == 2 and s["fade"] >= 1 and s["side"] is False and s["panel"] == "rgb(255, 255, 255)" and s["radius"] == "14px" and s["quals"] == 0 and s["star"] and s["other"], s
        expected = f"/recommendations?company={CO}"
        for selector in ("[data-star=guest]", "[data-review=guest]"):
            href = pg.locator(selector).first.get_attribute("href")
            assert urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)["next"] == [expected], href
        assert pg.locator("[data-rows] > [inert] [data-sheet-row]").count() == 3
        hidden = pg.locator(".x-wrap[data-open=false] a").first
        hidden.focus()
        assert not hidden.evaluate("e => document.activeElement === e"), "접힌 공고의 링크에 포커스가 들어간다"
        pg.screenshot(path=str(OUT / "_shot_results_default.png"), full_page=True)
        pg.get_by_role("button", name="1번 공고 펼치기", exact=True).click()
        pg.wait_for_selector(".x-wrap[data-open=true] li")
        assert pg.locator(".x-wrap[data-open=true] li").count() >= 3
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(OUT / "_shot_results_expanded.png"), full_page=True)
        pg.locator("[data-side] summary").click()
        assert pg.locator("[data-side]").evaluate("e => e.open")
        pg.locator("[data-side] summary").click()
        pg.locator("[data-funnel] summary").click()
        assert pg.locator("[data-funnel] ol").is_visible()
        pg.locator("[data-funnel] summary").click()
        # 다른 회사
        pg.click("[data-other]"); pg.wait_for_timeout(500)
        o = pg.evaluate("() => ({ box: !!document.querySelector('[data-search] [data-suggest]'), res: getComputedStyle(document.querySelector('[data-res]')).opacity, focus: document.activeElement?.tagName })")
        assert o["box"] and float(o["res"]) < 0.3 and o["focus"] == "INPUT", o
        pg.screenshot(path=str(OUT / "_shot_results_search.png"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        assert not pg.query_selector("[data-search]") and pg.evaluate("getComputedStyle(document.querySelector('[data-res]')).opacity") == "1"
        # 390
        # 같은 탭에서 다시 연 검색은 받아 둔 결과로 바로 — 장면 없이 표(계산이 없으면 가림막도 없다)
        pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, f"/recommendations?company={CO}", 300)
        pg.wait_for_selector("[data-res]", timeout=3000)
        assert not pg.query_selector("[data-scene]"), "다시 연 검색인데 장면이 돈다"
        rules(pg)
        m = pg.evaluate("() => ({ open: document.querySelector('[data-side]').open, first: document.querySelector('[data-sheet-row]').getBoundingClientRect().top, side: document.querySelector('[data-side]').getBoundingClientRect().top })")
        assert m["open"] is False and m["first"] < 450 and m["side"] > m["first"], m
        pg.screenshot(path=str(OUT / "_shot_results_390.png"), full_page=True)
        pg.set_viewport_size({"width": 1280, "height": 900})
        # 공고 전 단계 줄 — CO 는 사전규격 0·발주계획 20 이라 접힌 채 "앞으로 나올 공고"
        lead = pg.evaluate("() => { const e = document.querySelector('[data-leads]'); return e && { golden: e.dataset.golden ?? null, open: e.querySelector('button').getAttribute('aria-expanded'), txt: e.innerText } }")
        assert lead and lead["golden"] is None and lead["open"] == "false" and "앞으로 나올 공고" in lead["txt"], lead
        # 키워드 모드
        goto(pg, "/recommendations?q=%ED%95%98%EC%88%98%EC%B2%98%EB%A6%AC"); pg.wait_for_selector("[data-res]", timeout=30000); rules(pg)
        k = pg.evaluate("() => ({ scene: !!document.querySelector('[data-scene]'), rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, side: !!document.querySelector('[data-side]'), leads: !!document.querySelector('[data-leads]') })")
        assert not k["scene"] and k["rows"] >= 1 and not k["side"] and k["leads"], k
        # 골든타임 — 의견 창이 열린 사전규격을 DB 에서 하나 골라 그 품명으로 키워드 검색하면 사전규격 줄이 "골든타임" 으로 펼쳐져 있어야 한다
        if srv and (surl := env(ROOT / "backend/.env", "SUPABASE_URL")):
            now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            req = urllib.request.Request(f"{surl}/rest/v1/pre_specs?select=prdct_clsfc_no_nm&opnin_rgst_clse_dt=gt.{urllib.parse.quote(now)}&embedding_k=not.is.null&order=opnin_rgst_clse_dt.desc&limit=1", headers={"apikey": srv, "Authorization": f"Bearer {srv}"})
            with urllib.request.urlopen(req) as r: spec = json.loads(r.read())[0]["prdct_clsfc_no_nm"]
            goto(pg, f"/recommendations?q={urllib.parse.quote(spec)}"); pg.wait_for_selector("[data-res]", timeout=30000); rules(pg)
            g = pg.evaluate("() => { const e = document.querySelector('[data-leads][data-golden]'); return e && { golden: e.dataset.golden, open: e.querySelector('button').getAttribute('aria-expanded'), txt: e.innerText, rows: e.querySelectorAll('ul li').length } }")
            assert g and int(g["golden"]) >= 1 and g["open"] == "true" and "골든타임" in g["txt"] and g["rows"] >= 1, (spec, g)
            pg.screenshot(path=str(OUT / "_shot_results_golden.png"), full_page=True)
        # 등록업종 0건 회사(유원디자인연구소) — 면허 자격을 판정하지 못했다는 줄이 있고, 업종 있는 회사(위 CO)에는 없다
        goto(pg, f"/recommendations?company={NO_IND}"); pg.wait_for_selector("[data-scene]", timeout=10000)
        pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg); rules(pg)
        assert "면허 자격을 판정하지 못했습니다" in (pg.locator("[data-noind]").text_content() or ""), "업종 0건 안내 줄이 없다"
        goto(pg, f"/recommendations?company={CO}", 300); pg.wait_for_selector("[data-res]", timeout=30000)
        assert not pg.query_selector("[data-noind]"), "업종 있는 회사에 업종 0건 안내가 뜬다"
        # 빈 질의 = 입구로 보낸다(입구는 루트 하나다 — 실사용자 검색의 97.7% 가 / 에서 시작)
        goto(pg, "/recommendations")
        assert pg.url.rstrip("/").endswith(BASE.rstrip("/").split("//")[-1]) or pg.url.rstrip("/") == BASE.rstrip("/"), pg.url
        assert pg.query_selector("[data-suggest] input"), "입구 검색창이 없다"

        if not (url and anon and srv):
            print("ok results(guest): scene→done · funnel 4 · rows/gate/fade · disclosures · other company · 390 · keywords · 로그인 검사 건너뜀"); b.close(); return 0
        email, pw_ = "check-results@jodalfit.test", "check-results-pw-1"
        for u in admin(url, srv, "GET", "/admin/users?per_page=200").get("users", []):
            if u.get("email") == email: admin(url, srv, "DELETE", f"/admin/users/{u['id']}")
        user = admin(url, srv, "POST", "/admin/users", {"email": email, "password": pw_, "email_confirm": True})
        try:
            goto(pg, f"/login?next=%2Frecommendations%3Fcompany%3D{CO}"); pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw_); pg.click("button[type=submit]")
            pg.wait_for_url(re.compile(r"/recommendations")); pg.wait_for_load_state("networkidle"); pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg)
            l = pg.evaluate("() => ({ gate: document.querySelectorAll('.hairline a[href^=\"/login\"]').length, rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, fade: document.querySelectorAll('[inert]:not(.x-wrap)').length, report: !!document.querySelector('a[href^=\"/recommendations/report\"]') })")
            assert l["gate"] == 0 and l["rows"] >= 6 and l["fade"] == 0 and l["report"], l
            pg.get_by_role("button", name="1번 공고 펼치기", exact=True).click()
            pg.click("[data-review=off]"); pg.wait_for_selector("[data-review=on]"); pg.wait_for_timeout(500)
            assert pg.evaluate("getComputedStyle(document.querySelector('[data-sheet-row]'), '::before').transform") != "matrix(1, 0, 0, 0, 0, 0)"  # scaleY(1)
            pg.screenshot(path=str(OUT / "_shot_results_reviewed.png"), full_page=True)
            goto(pg, f"/recommendations/report?company={CO}"); assert pg.evaluate("document.querySelectorAll('.report-page .break-inside-avoid').length") >= 5
            pg.emulate_media(media="print"); pg.pdf(path=str(OUT / "_report.pdf"), format="A4")
            pg.screenshot(path=str(OUT / "_shot_results_report.png"), full_page=True)
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{user['id']}")
        print("ok results: guest · login(no gate, 20 rows) · review rule · report"); b.close(); return 0

if __name__ == "__main__":
    sys.exit(main())

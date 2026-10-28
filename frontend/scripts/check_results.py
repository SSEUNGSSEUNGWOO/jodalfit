# frontend/scripts/check_results.py
"""결과 페이지(05) 검증 — 시안 gen_results_final.py --check 를 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_results.py   (RESULTS_BASE 기본 http://localhost:3000)
회사 1248177731(한종산업개발): 장면 → 건너뛰기 → done, 숫자 넷(… 아님), 표 5 + 게이트 2버튼 + 흐림 ≥1, 행 펼침에 자격·근거 줄,
다른 회사 → 상자·흐림 → Esc 복귀, 금지어·주황 면·인주 0, 바닥색·판 14px, 390 한 단·넘침 없음.
키워드(하수처리): 장면 없음, 표 ≥1. 키워드(폐기물): 제목·기관·지역 일치 판 전부·25건 쪽 넘김·의미 판과 중복 없음. 좁히기(폐기물 용역·30일): 칩 2개 켜짐·행 전부 용역·D-30 이내. 기관명(국무조정실): 제목 0건인데 "발주기관에 일치" 칩. 좁혀서 0건: "조건 해제". 오타 매칭(한종산업개빌): "가장 가까운 이름" 줄. 번호 못 찾음(000-00-00001): "다음 시간부터" 판. 업종 0건 회사(4191800117): 면허 판정 불가 안내 줄. 로그인(키 있으면): 게이트 없음·20행, 검토 → 괘선, 보고서.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent; ROOT = OUT.parent.parent
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]
CO = "1248177731"
NO_INFO = "1138635250"  # (주)윈디자인 — 등록업종·공급물품 둘 다 없음 → 회사 기준 추천 불가, 키워드 검색창(2026-10-26). 업종이 생기면 바꾼다
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
        direct_save = pg.locator("[data-rows] > [data-sheet-row] [data-row-actions] [data-review=guest]")
        assert direct_save.count() == 5 and direct_save.first.is_visible()
        assert direct_save.first.inner_text() == "저장", "행을 펼치기 전에 저장 버튼이 보여야 한다"
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
        # 공고 전 단계 줄 — 의견 창 열린 사전규격이 없으면 접힌 채 "앞으로 나올 공고", 있으면(2026-10-27 CO 에 1건 생김) "골든타임" 으로 펼쳐진다
        lead = pg.evaluate("() => { const e = document.querySelector('[data-leads]'); return e && { golden: e.dataset.golden ?? null, open: e.querySelector('button').getAttribute('aria-expanded'), txt: e.innerText } }")
        assert lead and "앞으로 나올 공고" in lead["txt"] and ((lead["golden"] is None and lead["open"] == "false") or (lead["golden"] and lead["open"] == "true" and "골든타임" in lead["txt"])), lead
        # 키워드 모드
        goto(pg, "/recommendations?q=%ED%95%98%EC%88%98%EC%B2%98%EB%A6%AC"); pg.wait_for_selector("[data-res]", timeout=30000); rules(pg)
        k = pg.evaluate("() => ({ scene: !!document.querySelector('[data-scene]'), rows: document.querySelectorAll('[data-rows] [data-sheet-row]').length, side: !!document.querySelector('[data-side]'), leads: !!document.querySelector('[data-leads]') })")
        assert not k["scene"] and k["rows"] >= 1 and not k["side"] and k["leads"], k
        # "도움이 됐습니까" 한 줄(2026-10-27) — 아니오 → 메모 칸 → 보내기 → 고맙습니다. 운영 DB 에 시험 행을 남기지 않게 요청은 가로채 200 으로 답한다.
        hits = []
        pg.route("**/events/helpful", lambda r: (hits.append(r.request.post_data), r.fulfill(status=200, content_type="application/json", body='{"ok":true}')))
        assert pg.evaluate("document.querySelector('[data-helpful]')?.dataset.state") == "ask", "도움이 됐습니까 줄이 없다"
        pg.click("[data-helpful] button:has-text('아니오')"); pg.fill("#helpful-note", "검증 메모"); pg.click("[data-helpful] button[type=submit]"); pg.wait_for_timeout(300)
        assert pg.evaluate("document.querySelector('[data-helpful]')?.dataset.state") == "done" and len(hits) == 1 and '"helpful":false' in hits[0] and "검증 메모" in hits[0], hits
        pg.unroute("**/events/helpful")
        # 제목 일치 판(2026-10-27) — "폐기물" 은 제목에 든 진행 공고가 200건 넘는다. 첫 판에 전부(25건씩 쪽), 의미 유사 판에는 같은 공고가 없다.
        goto(pg, "/recommendations?q=%ED%8F%90%EA%B8%B0%EB%AC%BC"); pg.wait_for_selector("[data-title-matches]", timeout=30000); rules(pg)
        t = pg.evaluate("""() => { const e = document.querySelector('[data-title-matches]'); const hrefs = s => [...document.querySelectorAll(s + ' [data-sheet-row] a[href^="/notices/"]')].map(a => a.getAttribute('href'));
          return { n: +e.querySelector('h2 .num').textContent, page: e.dataset.page, pages: +e.dataset.pages, rows: e.querySelectorAll('[data-sheet-row]').length, pager: !!e.querySelector('[data-pager]'),
                   head: e.querySelector('h2').textContent, first: e.querySelector('[data-sheet-row]').textContent, title: hrefs('[data-title-matches]'), sem: hrefs('[data-rows]'), zero: !!document.querySelector('[data-zero]') } }""")
        assert t["n"] > 25 and t["page"] == "1" and t["pages"] == -(-t["n"] // 25) and t["rows"] == 25 and t["pager"] and "제목·기관·지역 일치" in t["head"] and not t["zero"], t
        assert not (set(t["title"]) & set(t["sem"])), "같은 공고가 글자 일치와 의미 유사 두 판에 있다"
        # 행 글에 낱말이 있어야 한다 — 제목에 없으면 기관명(둘째 줄)에 있고 "발주기관에 일치" 칩이 붙는다(2026-10-28)
        assert all("폐기물" in x for x in pg.evaluate("() => [...document.querySelectorAll('[data-title-matches] [data-sheet-row]')].map(r => r.textContent)")), "낱말이 없는 행이 글자 일치 판에 있다"
        assert pg.evaluate("() => ({ bar: !!document.querySelector('[data-kw-filters]'), on: [...document.querySelectorAll('[data-kw-filters] a[aria-current]')].map(a => a.textContent) })") == {"bar": True, "on": ["전체", "전체"]}
        pg.screenshot(path=str(OUT / "_shot_results_title.png"), full_page=False)
        pg.click("[data-title-matches] [data-pager] button:has-text('다음')")
        t2 = pg.evaluate("() => { const e = document.querySelector('[data-title-matches]'); return { page: e.dataset.page, first: e.querySelector('[data-sheet-row]').textContent } }")
        assert t2["page"] == "2" and t2["first"] != t["first"], t2
        # 좁히기 칩(2026-10-28) — 용역 → 주소에 div, 30일 이내 → due. 글자 일치 행은 전부 "용역 ·" 로 시작하고 D-30 이내, 의미 유사 판도 같은 조건.
        pg.click("[data-kw-filters] a:has-text('용역')"); pg.wait_for_url("**div=%EC%9A%A9%EC%97%AD**"); pg.wait_for_selector("[data-title-matches]", timeout=30000)
        pg.click("[data-kw-filters] a:has-text('30일 이내')"); pg.wait_for_url("**due=30**"); pg.wait_for_selector("[data-title-matches]", timeout=30000); rules(pg)
        f = pg.evaluate("""() => { const rows = s => [...document.querySelectorAll(s + ' [data-sheet-row]')]; const days = s => rows(s).map(r => +(r.dataset.days ?? 999));
          return { on: [...document.querySelectorAll('[data-kw-filters] a[aria-current]')].map(a => a.textContent), n: +document.querySelector('[data-title-matches] h2 .num').textContent,
          div: rows('[data-title-matches]').every(r => r.textContent.includes('용역 ·')), due: Math.max(...days('[data-title-matches]'), ...days('[data-rows]')), sem: rows('[data-rows]').length } }""")
        assert f["on"] == ["용역", "30일 이내"] and 0 < f["n"] < t["n"] and f["div"] and f["due"] <= 30, f
        pg.screenshot(path=str(OUT / "_shot_results_filtered.png"), full_page=False)
        # 기관명 검색(2026-10-28) — 제목에는 없고 발주기관에만 있는 낱말. 행마다 "발주기관에 일치" 칩. 기관이 공고를 안 내면 다른 기관으로 바꾼다
        goto(pg, "/recommendations?q=%EA%B5%AD%EB%AC%B4%EC%A1%B0%EC%A0%95%EC%8B%A4"); pg.wait_for_selector("[data-title-matches]", timeout=30000); rules(pg)
        i = pg.evaluate("() => [...document.querySelectorAll('[data-title-matches] [data-sheet-row]')].map(r => r.textContent)")
        assert len(i) >= 1 and all("국무조정실" in x and "발주기관에 일치" in x for x in i), i[:3]
        # 좁혀서 0건 — 공사 구분에는 국무조정실 공고가 없다 → "조건 해제" 링크로 되돌린다
        goto(pg, "/recommendations?q=%EA%B5%AD%EB%AC%B4%EC%A1%B0%EC%A0%95%EC%8B%A4&div=%EA%B3%B5%EC%82%AC&due=7"); pg.wait_for_selector("[data-zero][data-filtered], [data-title-matches]", timeout=30000); rules(pg)
        z = pg.evaluate("() => { const e = document.querySelector('[data-zero][data-filtered]'); return e && { txt: e.textContent, href: e.querySelector('a').getAttribute('href'), bar: !!document.querySelector('[data-kw-filters]') } }")
        assert z and "조건 해제" in z["txt"] and z["href"] == "/recommendations?q=%EA%B5%AD%EB%AC%B4%EC%A1%B0%EC%A0%95%EC%8B%A4" and z["bar"], z
        # 골든타임 — 의견 창이 열린 사전규격을 DB 에서 하나 골라 그 품명으로 키워드 검색하면 사전규격 줄이 "골든타임" 으로 펼쳐져 있어야 한다
        if srv and (surl := env(ROOT / "backend/.env", "SUPABASE_URL")):
            now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            req = urllib.request.Request(f"{surl}/rest/v1/pre_specs?select=prdct_clsfc_no_nm&opnin_rgst_clse_dt=gt.{urllib.parse.quote(now)}&embedding_k=not.is.null&order=opnin_rgst_clse_dt.desc&limit=1", headers={"apikey": srv, "Authorization": f"Bearer {srv}"})
            with urllib.request.urlopen(req) as r: spec = json.loads(r.read())[0]["prdct_clsfc_no_nm"]
            goto(pg, f"/recommendations?q={urllib.parse.quote(spec)}"); pg.wait_for_selector("[data-res]", timeout=30000); rules(pg)
            g = pg.evaluate("() => { const e = document.querySelector('[data-leads][data-golden]'); return e && { golden: e.dataset.golden, open: e.querySelector('button').getAttribute('aria-expanded'), txt: e.innerText, rows: e.querySelectorAll('ul li').length } }")
            assert g and int(g["golden"]) >= 1 and g["open"] == "true" and "골든타임" in g["txt"] and g["rows"] >= 1, (spec, g)
            pg.screenshot(path=str(OUT / "_shot_results_golden.png"), full_page=True)
        # 오타 등급으로만 잡힌 회사(2026-10-27) — "한종산업개빌" 은 difflib 0.83 으로 CO 에 잡힌다. 머리 아래 "가장 가까운 이름" 줄 + 번호 검색 버튼. 정확 매칭(CO 번호)에는 없다.
        goto(pg, "/recommendations?company=%ED%95%9C%EC%A2%85%EC%82%B0%EC%97%85%EA%B0%9C%EB%B9%8C"); pg.wait_for_selector("[data-scene]", timeout=10000)
        pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg); rules(pg)
        fz = pg.evaluate("() => { const e = document.querySelector('[data-fuzzy]'); return e && { txt: e.innerText, h1: document.querySelector('h1').textContent } }")
        assert fz and "가장 가까운 이름" in fz["txt"] and "한종산업개발" in fz["h1"], fz
        pg.click("[data-fuzzy] button"); pg.wait_for_selector("[data-search]", timeout=3000)
        # 사업자번호로 찾지 못함(2026-10-27) — 키워드로 숫자를 검색하지 않고 "다음 시간부터 검색된다" 판. 시간 잡이 이 번호를 조달청에 한 번 물어보고 not_found 로 적는다
        goto(pg, "/recommendations?company=000-00-00001"); pg.wait_for_selector("[data-nobizrno]", timeout=20000); rules(pg)
        nb = pg.evaluate("() => ({ url: location.search, txt: document.querySelector('[data-nobizrno]').innerText, rows: document.querySelectorAll('[data-sheet-row]').length, input: !!document.querySelector('[data-nobizrno] input') })")
        assert "from=company" in nb["url"] and "다음 시간부터 검색됩니다" in nb["txt"] and nb["rows"] == 0 and nb["input"], nb
        # 등록업종 0건 회사(유원디자인연구소) — 면허 자격을 판정하지 못했다는 줄이 있고, 업종 있는 회사(위 CO)에는 없다
        goto(pg, f"/recommendations?company={NO_IND}"); pg.wait_for_selector("[data-scene]", timeout=10000)
        pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg); rules(pg)
        assert "면허 자격을 판정하지 못했습니다" in (pg.locator("[data-noind]").text_content() or ""), "업종 0건 안내 줄이 없다"
        goto(pg, f"/recommendations?company={CO}", 300); pg.wait_for_selector("[data-res]", timeout=30000)
        assert not pg.query_selector("[data-noind]"), "업종 있는 회사에 업종 0건 안내가 뜬다"
        # 등록업종·공급물품 둘 다 없는 회사 — "자격 있는 공고가 없다"가 아니라 "등록정보가 없다" + 키워드 검색창(깔때기·회사 옆판 없음)
        goto(pg, f"/recommendations?company={NO_INFO}"); pg.wait_for_selector("[data-scene]", timeout=10000)
        pg.evaluate("document.querySelector('[data-scene]')?.click()"); wait_done(pg); rules(pg)
        ni = pg.evaluate("() => ({ block: !!document.querySelector('[data-noinfo]'), zero: !!document.querySelector('[data-zero]'), funnel: !!document.querySelector('[data-funnel]'), side: !!document.querySelector('[data-side]'), mode: document.querySelector('[data-noinfo] [data-suggest]')?.dataset.mode, txt: document.querySelector('[data-noinfo]')?.innerText || '' })")
        assert ni["block"] and not ni["zero"] and not ni["funnel"] and not ni["side"] and ni["mode"] == "keywords" and "등록업종·공급물품이 나라장터에 없습니다" in ni["txt"], ni
        pg.screenshot(path=str(OUT / "_shot_results_noinfo.png"), full_page=True)
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

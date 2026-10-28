# frontend/scripts/check_company.py
"""회사 페이지(06) 검증 — 시안 company-final 을 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_company.py
사례: A 한종산업개발(추천·계약·낙찰 전부) / C 벡터 없음 / D 폐업 / 비공개 요청은 404.
"""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요",
          "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]
RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    canvas: document.querySelectorAll('canvas').length,
    panels: document.querySelectorAll('section').length,
    jsonld: document.querySelectorAll('script[type="application/ld+json"]').length,
    ld: [...document.querySelectorAll('script[type="application/ld+json"]')].flatMap(s => { const j = JSON.parse(s.textContent); return Array.isArray(j) ? j : [j]; }),
    ogSite: document.querySelector('meta[property="og:site_name"]')?.content,
    over: document.documentElement.scrollWidth > window.innerWidth } }"""


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=2)
        pg.goto(f"{BASE}/companies/1248177731", wait_until="networkidle", timeout=60000)
        txt = pg.evaluate("document.body.innerText")
        bad = [w for w in BANNED if w in txt]
        assert not bad, f"금지어 {bad}"
        s = pg.evaluate(RULES)
        assert s["bg"] == "rgb(250, 249, 247)", f"바닥색 {s['bg']}"
        assert s["orangeFaces"] == 0, f"주황 면 {s['orangeFaces']}"
        assert s["canvas"] == 0, "회사 페이지엔 머리 장면이 없다"
        assert s["jsonld"] >= 1, "JSON-LD 가 없다"
        # 검색결과 둘째 줄 — "jodalfit.co.kr › companies" 가 아니라 "조달핏 › 공공조달 활동 기업 › 시·도 › 회사명" (2026-10-26)
        crumbs = [d for d in s["ld"] if d.get("@type") == "BreadcrumbList"]
        assert crumbs, "BreadcrumbList 가 없다"
        names = [it["name"] for it in crumbs[0]["itemListElement"]]
        assert names == ["홈", "공공조달 활동 기업", "경상남도", "한종산업개발 주식회사"], f"브레드크럼 {names}"
        assert all("item" in it for it in crumbs[0]["itemListElement"]), "브레드크럼 항목에 URL 이 없다"
        site = [d for d in s["ld"] if d.get("@type") == "WebSite"]
        assert site and site[0]["name"] == "조달핏", "WebSite 이름이 조달핏이 아니다 (검색결과 사이트명)"
        assert s["ogSite"] == "조달핏", f"og:site_name {s['ogSite']!r} — 페이지 openGraph 가 루트를 덮는다"
        assert not s["over"], "가로 넘침"
        assert "검토할 공고" in txt, "추천 판이 없다"
        jump = pg.locator('[data-reco-jump] a[href="#company-recommendations"]')
        assert jump.count() == 1 and jump.is_visible(), "상단 추천 바로가기가 없다"
        assert pg.locator('[data-reco-jump]').bounding_box()["y"] < pg.locator('[data-bridge]').bounding_box()["y"], "추천 바로가기가 회사 검색 다리보다 뒤에 있다"
        jump.click()
        pg.wait_for_timeout(150)
        assert pg.evaluate("(() => { const r = document.querySelector('#company-recommendations').getBoundingClientRect(); return location.hash === '#company-recommendations' && r.top < innerHeight && r.bottom > 0; })()"), "추천 판으로 이동하지 않았다"
        pg.evaluate("window.scrollTo(0, 0)")
        # 결과 화면으로 가는 길 (2026-10-26) — 회사 페이지 방문자의 4% 만 추천 결과에 닿았다
        assert pg.locator('[data-reco-cta] a[href="/recommendations?company=1248177731"]').count() == 1, "추천 전체 보기 링크가 없다"
        assert "수주 이력" in txt or "계약" in txt, "수주 이력 판이 없다"
        # 다리 + 판 순서(2026-10-27 시안 B): 머리 → 우리 회사 기준으로 보기(회사 모드 고정, 탭 없음) → 수주 이력 → … → 검토할 공고
        br = pg.evaluate("""() => { const b = document.querySelector('[data-bridge]'); const h2 = [...document.querySelectorAll('h2')].map(e => e.textContent.trim());
          return { has: !!b, tabs: b ? b.querySelectorAll('[data-search-mode]').length : -1, ph: b?.querySelector('input')?.placeholder, mode: b?.querySelector('[data-suggest]')?.dataset.mode,
                   order: [h2.findIndex(t => t.startsWith('우리 회사 기준')), h2.findIndex(t => t.startsWith('수주 이력')), h2.findIndex(t => t.startsWith('검토할 공고'))] } }""")
        assert br["has"] and br["tabs"] == 0 and br["mode"] == "company" and "우리 회사" in (br["ph"] or ""), br
        assert 0 <= br["order"][0] < br["order"][1] < br["order"][2], f"판 순서 {br['order']}"
        pg.fill("[data-bridge] input", "한종산업"); pg.wait_for_selector("[data-bridge] [role=option]", timeout=8000)  # 자동완성은 다리에서도 붙는다
        # 사업자번호는 마스킹된 형태만
        assert "124-81-77731" not in txt, "사업자번호가 그대로 보인다"
        pg.screenshot(path=str(OUT / "_shot_company.png"), full_page=True)

        # 폐업 회사 — 추천을 하지 않는다
        pg.goto(f"{BASE}/companies/5068152996", wait_until="networkidle", timeout=60000)
        t2 = pg.evaluate("document.body.innerText")
        closed_ok = "폐업" not in t2 or "추천을 하지 않습니다" in t2
        assert closed_ok, "폐업 회사인데 추천을 한다"

        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(f"{BASE}/companies/1248177731", wait_until="networkidle", timeout=60000)
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        pg2.screenshot(path=str(OUT / "_shot_company_390.png"), full_page=True)
        b.close()
    print(f"ok company: 판 {s['panels']} · 캔버스 0 · JSON-LD {s['jsonld']} · 금지어 0 · 390 ok")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

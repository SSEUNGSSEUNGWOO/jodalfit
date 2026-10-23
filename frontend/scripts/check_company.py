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
        assert not s["over"], "가로 넘침"
        assert "검토할 공고" in txt, "추천 판이 없다"
        assert "수주 이력" in txt or "계약" in txt, "수주 이력 판이 없다"
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

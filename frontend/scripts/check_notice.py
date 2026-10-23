# frontend/scripts/check_notice.py
"""공고 상세(07) 검증 — 시안 notice-final 을 운영 데이터로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_notice.py [요약있는공고] [요약없는공고]
"""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
WITH = sys.argv[1] if len(sys.argv) > 1 else "R26BK01759885"
WITHOUT = sys.argv[2] if len(sys.argv) > 2 else "R26BK01778343"
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요",
          "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오",
          "제안요청서·공고문이 붙은"]
RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    rail: cs(document.querySelector('aside')).position,
    jsonld: document.querySelectorAll('script[type="application/ld+json"]').length,
    files: [...document.querySelectorAll('aside a')].filter(a => a.href.includes('downloadFile')).length,
    over: document.documentElement.scrollWidth > window.innerWidth } }"""


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=2)

        pg.goto(f"{BASE}/notices/{WITH}", wait_until="networkidle", timeout=60000)
        txt = pg.evaluate("document.body.innerText")
        bad = [w for w in BANNED if w in txt]
        assert not bad, f"금지어 {bad}"
        s = pg.evaluate(RULES)
        assert s["bg"] == "rgb(250, 249, 247)", f"바닥색 {s['bg']}"
        assert s["orangeFaces"] == 0, f"주황 면 {s['orangeFaces']}"
        assert s["rail"] == "sticky", f"레일이 sticky 가 아니다 ({s['rail']})"
        assert s["jsonld"] >= 1, "JSON-LD 가 없다"
        assert not s["over"], "가로 넘침"
        assert "과업 내용" in txt and "단계" in txt, "본문 블록이 없다"
        assert "참가 자격" in txt, "레일에 자격이 없다"
        assert "첨부문서를 아직 읽지 않았습니다" not in txt, "요약이 있는 공고인데 '안 읽음' 문구가 뜬다"
        pg.screenshot(path=str(OUT / "_shot_notice_with.png"), full_page=True)

        pg.goto(f"{BASE}/notices/{WITHOUT}", wait_until="networkidle", timeout=60000)
        t2 = pg.evaluate("document.body.innerText")
        assert "첨부문서를 아직 읽지 않았습니다" in t2, "요약 없는 공고인데 안내가 없다"
        assert "순서를 기다리는 중" in t2 or "수의계약" in t2, "기다리는 건지 안 하는 건지 구분이 없다"
        s2 = pg.evaluate(RULES)
        assert s2["files"] >= 1, "첨부 원본 직링크가 없다"
        pg.screenshot(path=str(OUT / "_shot_notice_without.png"), full_page=True)

        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(f"{BASE}/notices/{WITH}", wait_until="networkidle", timeout=60000)
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        pg2.screenshot(path=str(OUT / "_shot_notice_390.png"), full_page=True)
        b.close()
    print(f"ok notice: 레일 sticky · JSON-LD {s['jsonld']} · 첨부 직링크 {s2['files']} · 금지어 0 · 390 ok")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

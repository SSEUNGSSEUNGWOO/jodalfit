# frontend/scripts/check_changelog.py
"""개선 기록(08) 검증 — 원천 문서와 화면이 어긋나지 않는지, 점수표가 운영 코드와 같은지.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_changelog.py
"""
import os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent
MD = ROOT / "docs" / "recommender" / "changelog.md"
SCORE = ROOT / "backend" / "app" / "recommender" / "score.py"
HOW = ROOT / "frontend" / "src" / "lib" / "how-we-pick.ts"
HIDE = ["재는 회사 수를 300곳에서 3,000곳으로", '"성공인데 0건"을 잡는 건강 점검',
        "프론트 검사 오류 4개 정리", "조건 검색에 키워드·발주기관을 더하는 바탕"]
BANNED = ["해드려요", "예요", "에요", "하세요", "주십시오"]


def main() -> None:
    md = MD.read_text(encoding="utf-8")
    heads = re.findall(r"^## (\d{4}-\d{2}-\d{2}) · (.+)$", md, re.M)
    shown = [t for _, t in heads if t not in HIDE]

    # 점수표가 운영 코드와 같은가 — 여기 어긋나면 페이지가 거짓말을 한다
    sp, how = SCORE.read_text(encoding="utf-8"), HOW.read_text(encoding="utf-8")
    for key, want in (("institution", "+12"), ("region", "+9"), ("instt_closed", "−3"), ("deadline_urgent", "−9")):
        m = re.search(rf'"key": "{key}".*?"points": (-?\d+)', sp, re.S)
        assert m, f"score.py 에서 {key} 를 못 찾음"
        n = int(m.group(1))
        txt = f"{'+' if n > 0 else '−'}{abs(n)}"
        assert txt == want, f"{key}: score.py {txt} vs 검사 기대 {want} — 점수표가 바뀌었다"
        assert f'v: "{txt}"' in how, f"how-we-pick.ts 에 {key} 의 {txt} 가 없다 — 운영 점수표와 어긋남"

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=2)
        pg.goto(f"{BASE}/changelog", wait_until="networkidle", timeout=40000)
        txt = pg.evaluate("document.body.innerText")
        bad = [w for w in BANNED if w in txt]
        assert not bad, f"금지어 {bad}"
        for t in HIDE:
            assert t not in txt, f"숨겨야 할 내부 항목이 보인다: {t}"
        arts = pg.evaluate("() => document.querySelectorAll('article').length")
        assert arts == len(shown), f"항목 {arts} vs 문서 {len(shown)}"
        # 최신순
        dates = pg.evaluate(r"""() => [...document.querySelectorAll('article .num')].map(e => e.textContent.trim()).filter(t => /^\d{4}\./.test(t))""")
        assert dates == sorted(dates, reverse=True), f"최신순이 아니다: {dates[:4]}"
        assert "어떻게 고르는가" in txt and "점수를 올리는 것" in txt, "어떻게 고르는가 판이 없다"
        assert "측정 전" in txt, "측정 전 표시가 없다"
        assert not pg.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "가로 넘침"
        pg.screenshot(path=str(OUT / "_shot_changelog.png"), full_page=True)
        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(f"{BASE}/changelog", wait_until="networkidle", timeout=40000)
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        b.close()
    print(f"ok changelog: 항목 {arts}건(숨김 {len(HIDE)}) · 최신 {dates[0]} · 점수표 운영 코드와 일치")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

# frontend/scripts/check_changelog.py
"""공개 개선 기록의 명시적 목록·최신순·내부 정보 비노출 검증.

cd backend; uv run --no-sync python ../frontend/scripts/check_changelog.py
RESULTS_BASE 기본 http://localhost:3000. GitHub 공개 상태는 변경하지 않는다.
"""
import os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "frontend/src/lib/changelog.ts"
BANNED = ["해드려요", "예요", "에요", "하세요", "주십시오"]
INTERNAL = ["KURE-v1", "0.65", "0.45", "+12", "−9", "다음 병목", "해 보고 뺀 것", "운영 점수표 값 그대로", "한 분이", "내부 작업", "HNSW", "채점표"]


def main():
    source = SOURCE.read_text(encoding="utf-8")
    expected = re.findall(r'date: "(\d{4}-\d{2}-\d{2})", title: "([^"\n]+)"', source)
    assert expected, "공개 허용 목록이 없다"
    assert "PUBLIC_CHANGES" in source and "readFile" not in source and "node:fs" not in source, "내부 문서를 자동으로 읽는 구조가 돌아왔다"
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 1000})
        pg.route("**/*posthog.com/**", lambda r: r.abort())
        for width in (1280, 390):
            pg.set_viewport_size({"width": width, "height": 1000})
            response = pg.goto(BASE + "/changelog", wait_until="networkidle", timeout=40000)
            assert response.status == 200
            txt = pg.evaluate("document.body.innerText")
            raw = response.text()
            assert not [w for w in BANNED + INTERNAL if w in txt], "내부 정보 또는 금지어가 본문에 있다"
            assert not [w for w in INTERNAL if w in raw], "숨겨진 HTML 또는 전달 데이터에 내부 정보가 있다"
            titles = pg.locator("article h2").all_text_contents()
            assert set(titles) == {title for _, title in expected} and len(titles) == len(expected)
            dates = pg.locator("article time").evaluate_all("els => els.map(e => e.dateTime)")
            assert dates == sorted(dates, reverse=True)
            assert "서비스 개선 기록" in txt and "낙찰 가능성을 예측하지 않습니다" in txt
            assert pg.locator('a[href="/about#how-we-pick"]').count() == 1
            assert not pg.evaluate("document.documentElement.scrollWidth > innerWidth")
        # 소개·FAQ의 중복 공개도 검사한다. 자격 확인불가·원문 확인 안내는 남아 있어야 한다.
        for path in ("/about", "/faq"):
            response = pg.goto(BASE + path, wait_until="networkidle", timeout=40000)
            assert response.status == 200
            txt = pg.evaluate("document.body.innerText")
            assert not [w for w in INTERNAL if w in txt], path
            assert not [w for w in INTERNAL if w in response.text()], path + " hidden payload"
            assert "확인이 필요" in txt and "공고 원문" in txt, path + " 한계 안내가 없다"
            assert not pg.evaluate("document.documentElement.scrollWidth > innerWidth")
        b.close()
    print(f"ok public changelog: {len(expected)} explicit entries · latest first · no internal payload · about/FAQ limits retained · 1280/390")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

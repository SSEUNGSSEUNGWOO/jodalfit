# frontend/scripts/shoot_design.py
"""디자인 점검용 일괄 캡처 — 구현된 화면(운영 데이터)과 아직 시안만 있는 화면을 같은 폭으로.

사용: cd backend && uv run --no-sync python ../frontend/scripts/shoot_design.py
저장: frontend/scripts/_design/<이름>.png
"""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent / "_design"
PROTO = ROOT / "docs" / "design" / "prototypes" / "final"
CO = "1248177731"

# (이름, URL, 장면이 접히길 기다릴지)
LIVE = [
    ("live-05-results", f"{BASE}/recommendations?company={CO}", True),
    ("live-03-saved", f"{BASE}/saved", False),
    ("live-02-login", f"{BASE}/login", False),
    ("live-04-entry", f"{BASE}/recommendations", False),  # 질의 없음 = 입력 화면
]
PROTOS = ["entry-simple", "company-final", "notice-final", "changelog-final", "results-final", "saved-final"]


def shoot(pg, name: str, url: str, wait_done: bool) -> str:
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception as e:
        return f"  {name:22} 열기 실패 {type(e).__name__}"
    if wait_done:
        try:
            pg.wait_for_function("() => document.querySelector('[data-scene][data-done=true]')", timeout=25000)
            pg.wait_for_timeout(800)
        except Exception:
            pass
    else:
        pg.wait_for_timeout(700)
    pg.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    h = pg.evaluate("document.documentElement.scrollHeight")
    over = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    return f"  {name:22} 높이 {h:>5}px{'  ← 가로 넘침' if over else ''}"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    lines = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        lines.append("구현됨 (운영 데이터)")
        for name, url, wd in LIVE:
            lines.append(shoot(pg, name, url, wd))
        lines.append("시안만 있음")
        for n in PROTOS:
            f = PROTO / f"{n}.html"
            if not f.exists():
                lines.append(f"  {n:22} 파일 없음")
                continue
            lines.append(shoot(pg, f"proto-{n}", f.as_uri(), False))
        b.close()
    print("\n".join(lines))
    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()

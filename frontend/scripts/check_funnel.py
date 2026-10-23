# frontend/scripts/check_funnel.py
"""머리 장면(D-2 점 격자) 검증 — 네 칸이 앞 칸의 부분집합인지, 점이 보이는지, 선이 한 벌인지.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_funnel.py
캡처: scripts/_shot_scene_d2_{mid,end,390}.png
"""
import base64, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
CO = "1248177731"
URL = f"{BASE}/recommendations?company={CO}"

# 캔버스가 비었는지 — 알파가 있는 픽셀 비율. 점 격자는 첫 칸만으로도 꽤 찍혀야 한다.
INK = """() => { const c = document.querySelector('[data-scene] canvas'); if (!c) return null;
  const g = c.getContext('2d'); const d = g.getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
  return { w: c.width, h: c.height, inked: n / (c.width * c.height) }; }"""

# 라벨 괘선 x 와 캔버스 관문선 x 가 같은 벌인지 — 2026-10-23 '필터 줄이 안 맞는다'
LABX = """() => [...document.querySelectorAll('[data-lab]')].map(e => Math.round(e.getBoundingClientRect().left))"""


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("[data-scene]", timeout=20000)

        # 중간 — 장면이 아직 접히지 않은 상태
        pg.wait_for_timeout(900)
        mid = pg.evaluate(INK)
        assert mid, "캔버스가 없다"
        assert mid["inked"] > 0.01, f"캔버스가 거의 비었다 inked={mid['inked']:.4f}"
        labs = pg.evaluate(LABX)
        pg.screenshot(path=str(OUT / "_shot_scene_d2_mid.png"))

        # 숫자 넷 — 네 칸이 앞 칸의 부분집합이어야 한다
        pg.wait_for_function("() => document.querySelector('[data-scene][data-done=true]')", timeout=25000)
        nums = pg.evaluate(
            """() => [...document.querySelectorAll('[data-funnel] b[data-n]')].map(e => e.textContent.trim())"""
        )
        # 캔버스는 접히는 중이라 페이지 캡처로는 네 칸이 안 보인다 — 마지막 paint 상태를 그대로 뜬다.
        png = pg.evaluate("""() => { const c = document.querySelector('[data-scene] canvas');
            return c ? c.toDataURL('image/png').slice(22) : null; }""")
        assert png, "캔버스를 뜨지 못했다"
        (OUT / "_shot_scene_d2_canvas.png").write_bytes(base64.b64decode(png))
        pg.wait_for_timeout(900)  # 접힘이 끝난 뒤의 페이지
        pg.screenshot(path=str(OUT / "_shot_scene_d2_end.png"))

        vals = [int(s.replace(",", "")) for s in nums if s and s != "…"]
        assert len(vals) == 4, f"숫자 넷이 아니다: {nums}"
        for i in range(3):
            assert vals[i] >= vals[i + 1], f"포함 관계가 깨졌다: {vals}"
        # 둘째 칸은 후보 풀 — 운영은 200 을 요청한다(0 건 회사면 더 적을 수 있다)
        assert vals[1] <= 200, f"후보가 요청값보다 많다: {vals}"

        # 390 — 점이 얼룩이 되지 않는지
        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(URL, wait_until="domcontentloaded")
        pg2.wait_for_selector("[data-scene]", timeout=20000)
        pg2.wait_for_timeout(900)
        m390 = pg2.evaluate(INK)
        assert m390 and m390["inked"] > 0.005, f"390 에서 캔버스가 비었다 {m390}"
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        pg2.screenshot(path=str(OUT / "_shot_scene_d2_390.png"))

        b.close()
    print(f"ok funnel: 숫자 {nums} · 라벨 x {labs}")
    print(f"   데스크톱 inked {mid['inked']:.3f} ({mid['w']}x{mid['h']}) · 390 inked {m390['inked']:.3f}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

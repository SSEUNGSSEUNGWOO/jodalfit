"""공고 전 단계·가입 구간 UI. 운영 DB에 쓰지 않고 스트림을 모의 응답으로 대체한다.

cd backend; uv run --no-sync python ../frontend/scripts/check_design_refinements.py
RESULTS_BASE 기본 http://localhost:3000.
"""
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")


def main():
    rows = [{"bid_ntce_no": f"CHECK{i}", "bid_ntce_ord": "000", "bid_ntce_nm": f"검증용 시스템 유지보수 {i}",
             "bid_clse_date": "2099-01-01", "score": .7, "dmnd_instt_nm": "검증 기관"} for i in range(20)]
    pre = [{"bf_spec_rgst_no": "PRE1", "prdct_clsfc_no_nm": "검증 사전규격", "opnin_rgst_clse_dt": "2099-01-01T00:00:00+09:00"}]
    plans = [{"order_plan_unty_no": f"PLAN{i}", "biz_nm": f"검증 발주계획 {i}", "order_year": "2099", "order_mnth": "12"} for i in range(7)]
    payload = {"company": None, "results": rows, "pre_spec_results": pre, "order_plan_results": plans}
    body = '\n'.join(json.dumps(e, ensure_ascii=False) for e in [{"type": "results", "data": payload}, {"type": "done"}]) + '\n'
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.route("**/recommendations/stream", lambda r: r.fulfill(status=200, content_type="application/x-ndjson", body=body, headers={"access-control-allow-origin": "*"}))
        pg.route("**/*posthog.com/**", lambda r: r.abort())
        for width in (1280, 390):
            pg.set_viewport_size({"width": width, "height": 900})
            pg.goto(BASE + "/recommendations?q=design-check")
            pg.wait_for_selector("[data-res]")
            assert pg.locator("[data-rows] > [data-sheet-row]").count() == 5
            assert pg.locator("[data-rows] > [inert] [data-sheet-row]").count() == 1
            gate = pg.locator("[data-gate]")
            assert "나머지 15건" in gate.inner_text() and "보관" in gate.inner_text()
            for link in gate.locator("a").all():
                assert parse_qs(urlsplit(link.get_attribute("href")).query)["next"] == ["/recommendations?q=design-check"]
            pre_section = pg.locator("[data-pre-specs]")
            plan_section = pg.locator("[data-order-plans]")
            assert pre_section.locator("button").get_attribute("aria-expanded") == "true"
            assert plan_section.locator("li:visible").count() == 3
            plan_section.locator("[data-plans-more]").click()
            assert plan_section.locator("li:visible").count() == 7
            plan_section.locator("[data-plans-more]").click()
            assert plan_section.locator("li:visible").count() == 3
            plan_section.get_by_role("button", name="발주계획 접기", exact=True).click()
            assert plan_section.locator("li:visible").count() == 0
            assert pre_section.locator("li").is_visible(), "발주계획을 접으며 골든타임도 숨겼다"
            plan_section.get_by_role("button", name="발주계획 펼치기", exact=True).click()
            assert plan_section.locator("li:visible").count() == 3
            pre_section.get_by_role("button", name="사전규격 접기", exact=True).click()
            assert plan_section.locator("li:visible").count() == 3
            assert not pg.evaluate("document.documentElement.scrollWidth > innerWidth")
        b.close()
    print("ok refinements: free 5 · inert preview 1 · gate benefit/return URL · plans 3/7 · independent sections · 1280/390")


if __name__ == "__main__":
    main()

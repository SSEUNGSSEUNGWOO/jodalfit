"""저장 버튼 노출·제목 클릭·모바일 검증. 추천/이벤트 요청은 가로채며 운영 DB에 쓰지 않는다.

cd backend; uv run --no-sync python ../frontend/scripts/check_result_actions.py
RESULTS_BASE 기본 http://localhost:3000. 백엔드는 필요 없다.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")


def main():
    events = []
    rows = [{"bid_ntce_no": f"CHECK{i}", "bid_ntce_ord": "000", "bid_ntce_nm": f"검증용 시스템 유지보수 {i}",
             "bid_clse_date": "2099-01-01", "presmpt_prce": 10000000, "score": .7,
             "dmnd_instt_nm": "검증 기관", "bid_ntce_url": "https://www.g2b.go.kr/"} for i in range(8)]
    body = '\n'.join(json.dumps(e, ensure_ascii=False) for e in [
        {"type": "results", "data": {"company": None, "results": rows}}, {"type": "done"}]) + '\n'
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(exe) if exe else None)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/recommendations/stream", lambda r: r.fulfill(status=200, content_type="application/x-ndjson", body=body, headers={"access-control-allow-origin": "*"}))
        page.route("**/events", lambda r: (events.append(json.loads(r.request.post_data)), r.fulfill(status=200, body='{"ok":true}', headers={"access-control-allow-origin": "*"})))
        page.route("**/*posthog.com/**", lambda r: r.abort())
        for width in (1280, 390):
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(BASE + "/recommendations?q=test")
            page.wait_for_selector("[data-res]")
            assert page.locator("[data-rows] > [data-sheet-row] [data-review=guest]").count() == 5
            first = page.locator("[data-sheet-row]").first
            save = first.locator("[data-review=guest]")
            assert save.is_visible() and save.inner_text() == "저장"
            assert "next=%2Frecommendations%3Fq%3Dtest" in save.get_attribute("href")
            assert first.locator("button[aria-expanded]").get_attribute("aria-expanded") == "false"
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), width
            assert page.locator("[data-rows] > [inert] [data-review=guest]").count() == 1
            # 제목 링크를 눌러도 행 펼침 이벤트와 겹치지 않으며 클릭은 한 번 기록한다.
            before = len(events)
            first.locator("a[href^='/notices/']").click()
            page.wait_for_timeout(400)
            assert len(events) == before + 1 and events[-1]["event_type"] == "click", events
        browser.close()
    print("ok result actions: visible save · return URL · inert gate · title click once · 1280/390")


if __name__ == "__main__":
    main()

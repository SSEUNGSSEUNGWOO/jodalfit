import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RESULTS_BASE", "http://localhost:3000")
JS = """() => {
  const n = document.querySelector('nav') || document.querySelector('header');
  if (!n) return '(nav 없음)';
  return [...n.querySelectorAll('a, span, button')]
    .map(e => e.textContent.trim()).filter(Boolean).join(' | ');
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    for path in ["/", "/companies/1248177731", "/changelog", "/notices", "/about", "/privacy"]:
        pg.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=45000)
        print(f"  {path:<26} {pg.evaluate(JS)[:120]}")
    b.close()

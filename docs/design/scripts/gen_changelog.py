"""개선 기록 최종 시안(`prototypes/changelog-final.html`) — `/changelog`. `docs/recommender/changelog.md` 를 그대로 렌더링하는 읽기 페이지.

- 머리: 제목 + 재는 방법(문서 첫 문단 그대로). 왼쪽 목차(날짜·제목, sticky, 스크롤 스파이) / 오른쪽 흰 판에 글 순서 그대로(처음 → 변경 → 지금).
- 마크다운 부분집합만 변환: ## · 문단 · 표 · **굵게** · `코드` · ---. 표 숫자는 tabular, 전/후 열은 그대로(화살표·색 안 입힘 — 숫자가 말한다).
- 로그인 무관(공개 페이지). 상태 없음. 문서가 바뀌면 다시 생성하면 된다 — 구현도 같은 방식(빌드 때 md → 페이지).

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_changelog.py ../docs/recommender/changelog.md ../docs/design/prototypes/changelog-final.html
검증: gen_changelog.py --check ../docs/design/prototypes/changelog-final.html
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_results_final import CSS as FINAL_CSS  # noqa: E402
from gen_login import nav  # noqa: E402

CSS = FINAL_CSS + r"""
html, body { background:#faf9f7 } .wrap { padding-bottom:140px }
.nav .cta { border-bottom:1px solid #141414; color:#141414 }
.head { border-bottom:1px solid #141414; padding-bottom:20px } .head h1 { font-size:32px; letter-spacing:-0.035em; margin-bottom:10px }
.head .lead { font-size:14.5px; line-height:1.7; color:#333; max-width:760px; margin:0 } .head .lead + .lead { margin-top:8px } .head .lead b { font-weight:650 }
.cols { display:grid; grid-template-columns:220px minmax(0,1fr); gap:0 44px; align-items:start; margin-top:22px }
/* 목차 — 날짜는 회색, 제목은 먹. 현재 항목은 왼쪽 괘선 2px 먹 */
.toc { position:sticky; top:20px; font-size:13px; padding-top:6px } .toc .k { display:block; margin-bottom:10px }
.toc a { display:block; padding:6px 0 6px 12px; border-left:2px solid #ececea; color:#55554f; line-height:1.45 } .toc a .d { display:block; font-size:11.5px; color:#9b9a95; font-variant-numeric:tabular-nums }
.toc a.on { border-left-color:#141414; color:#141414; font-weight:600 } .toc a:hover { color:#141414 }
.toc .sum { margin-top:16px; padding-top:12px; border-top:1px solid #ececea; font-size:12.5px; color:#6b6b67; line-height:1.6 }
/* 본문 판 */
.doc { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:10px 36px 36px }
.doc h2 { font-size:19px; font-weight:650; letter-spacing:-0.02em; margin:38px 0 10px; padding-top:30px; border-top:1px solid #ececea; scroll-margin-top:24px } .doc h2:first-child { margin-top:14px; padding-top:18px; border-top:0 }
.doc h2 .d { color:#737370; font-weight:450; font-size:13.5px; margin-right:12px; font-variant-numeric:tabular-nums; letter-spacing:0 }
.doc p { font-size:14.5px; line-height:1.75; color:#333; margin:10px 0; max-width:760px } .doc p b { color:#141414; font-weight:650 } .doc code { font-family:ui-monospace,Consolas,monospace; font-size:13px; background:#f6f5f2; padding:1px 5px; border-radius:4px }
.doc table { border-collapse:collapse; margin:14px 0 6px; font-size:14px; font-variant-numeric:tabular-nums } .doc th, .doc td { padding:8px 14px 8px 0; text-align:right; border-bottom:1px solid #ececea; vertical-align:top }
.doc th { font-size:12px; color:#6b6b67; font-weight:600; border-bottom:1px solid #141414 } .doc th:first-child, .doc td:first-child { text-align:left; padding-right:22px; color:#141414 } .doc td:first-child { font-weight:500 }
.doc tr.now td { font-weight:650 }
.doc hr { border:0; border-top:1px solid #ececea; margin:30px 0 }
.foot { margin-top:28px }
@media screen and (max-width:720px){
  .head h1 { font-size:24px } .cols { grid-template-columns:minmax(0,1fr); gap:0 } .toc { position:static; display:none } .doc { min-width:0 }   /* 1fr 만 두면 nowrap 표가 단을 665px 로 벌린다 */
  .doc { padding:0 16px 20px; border-radius:12px } .doc h2 { font-size:17px; margin-top:28px; padding-top:22px } .doc h2 .d { display:block; margin:0 0 4px }
  .doc table { display:block; overflow-x:auto; white-space:nowrap; max-width:100% }
}
"""

JS = r"""
const links = [...document.querySelectorAll('.toc a')], hs = links.map(a => document.getElementById(a.getAttribute('href').slice(1)));
const spy = () => { let cur = 0; hs.forEach((h, i) => { if (h.getBoundingClientRect().top <= 80) cur = i; }); links.forEach((a, i) => a.classList.toggle('on', i === cur)); };
addEventListener('scroll', spy, { passive: true }); spy();
"""


def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def md(text):
    """## · 문단 · 표 · --- 만. 반환: (lead 문단들, [(id, 날짜, 제목, html)])"""
    lines = text.splitlines()
    assert lines[0].startswith("# ")
    lead, entries, cur, buf, tbl = [], [], None, [], []

    def flush_p():
        if buf:
            (cur[3] if cur else lead).append(f"<p>{inline(' '.join(buf))}</p>"); buf.clear()

    def flush_t():
        if tbl:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl if not re.match(r"^\|?\s*-", r)]
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join(f'<tr class="{"now" if r[0] in ("후", "지금") else ""}">' + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            cur[3].append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"); tbl.clear()

    for ln in lines[1:]:
        if ln.startswith("## "):
            flush_p(); flush_t()
            title = ln[3:].strip(); m = re.match(r"(\d{4}-\d{2}-\d{2}) · (.+)", title)
            date, name = (m.group(1), m.group(2)) if m else (None, title)
            cur = (f"e{len(entries) + 1}", date, name, []); entries.append(cur)
        elif ln.startswith("|"):
            flush_p(); tbl.append(ln)
        elif ln.strip() == "---":
            flush_p(); flush_t()
        elif ln.strip() == "":
            flush_p(); flush_t()
        else:
            flush_t(); buf.append(ln.strip())
    flush_p(); flush_t()
    return lead, entries


def page(text):
    lead, entries = md(text)
    toc = "".join(f'<a href="#{i}">{f"<span class=d>{d}</span>" if d else ""}{esc(n)}</a>' for i, d, n, _ in entries)
    dated = [e for e in entries if e[1]]
    body = "".join(f'<h2 id="{i}">{f"<span class=d>{d}</span>" if d else ""}{esc(n)}</h2>{"".join(h)}' for i, d, n, h in entries)
    lead_html = "".join(p.replace("<p>", '<p class="lead">', 1) for p in lead)
    sum_ = f'<div class="sum">변경 {len(dated)}건 · {dated[0][1]} ~ {dated[-1][1]}<br>원문 <code>docs/recommender/changelog.md</code></div>'
    html = (f'{nav("guest", "log")}<div class="head"><h1>개선 기록</h1>{lead_html}</div>'
            f'<div class="cols"><nav class="toc"><span class="k">차례</span>{toc}{sum_}</nav><article class="doc">{body}</article></div>'
            f'<div class="foot">개선 기록 최종 시안 — <code>docs/recommender/changelog.md</code> 를 그대로 렌더링(## · 문단 · 표 · 굵게). 왼쪽 차례는 스크롤 스파이, 표의 "후"·"지금" 행만 굵게. 로그인 무관. {TODAY.isoformat()} 기준 원문.</div>')
    return (f'<!doctype html><html lang="ko" class="v-panel"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 개선 기록</title>{FONT}'
            f'<style>{CSS}</style></head><body class="done"><div class="wrap">{html}</div><script>{JS}</script></body></html>')


BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in p.read_text(encoding="utf-8")
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(400)
        # 금지어는 페이지 틀에만 — 본문은 원문 그대로(원문 마지막 줄이 폐기한 버튼 이름 '안 맞아요'를 인용한다)
        txt = pg.evaluate("[...document.querySelectorAll('.head, .toc, .foot, .nav')].map(e => e.innerText).join(' ')"); bad = [w for w in BANNED if w in txt]; assert not bad, bad
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e); return { h2: document.querySelectorAll('.doc h2').length, toc: document.querySelectorAll('.toc a').length, tbl: document.querySelectorAll('.doc table').length,
            sticky: cs(document.querySelector('.toc')).position, on: document.querySelector('.toc a.on') && document.querySelector('.toc a.on').textContent, nowRows: document.querySelectorAll('.doc tr.now').length,
            raw: document.querySelector('.doc').innerText.includes('**') || document.querySelector('.doc').innerText.includes('|'), b: document.querySelector('.nav .links b').textContent } }""")
        assert s["h2"] == s["toc"] >= 15 and s["tbl"] >= 10 and s["sticky"] == "sticky" and s["on"] and s["nowRows"] >= 3 and not s["raw"] and s["b"] == "개선 기록", s
        pg.screenshot(path=str(out / "_shot_changelog.png"), full_page=False)
        pg.evaluate("document.querySelectorAll('.doc h2')[6].scrollIntoView()"); pg.wait_for_timeout(300)
        on = pg.evaluate("[...document.querySelectorAll('.toc a')].findIndex(a => a.classList.contains('on'))"); assert on == 6, on
        pg.screenshot(path=str(out / "_shot_changelog_mid.png"), full_page=False)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390") and pg.evaluate("getComputedStyle(document.querySelector('.toc')).display") == "none"
        pg.screenshot(path=str(out / "_shot_changelog_390.png"), full_page=False)
        b.close()
    print(f"ok entries {s['h2']}, tables {s['tbl']}, toc sticky + spy, no raw markdown, 390 one column")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(open(sys.argv[1], encoding="utf-8").read()))
    print("written", sys.argv[2])

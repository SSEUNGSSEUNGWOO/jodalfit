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
/* 머리 — 제목 + 한 줄, 그 아래 '처음 → 지금' 숫자 셋 + 다음에 할 것. 계속 올라가는 페이지라는 걸 숫자로 */
.head { border-bottom:1px solid #141414; padding-bottom:22px } .head h1 { font-size:32px; letter-spacing:-0.035em; margin-bottom:8px }
.head .lead { font-size:14.5px; line-height:1.7; color:#55554f; max-width:720px; margin:0 }
.now { display:grid; grid-template-columns:repeat(3,1fr) 1.3fr; gap:0 40px; margin-top:24px; background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:24px 28px 22px }
.now .st .k { display:block; margin-bottom:10px } .now .st .v { display:flex; align-items:baseline; gap:10px } .now .st .v b { font-size:34px; font-weight:650; letter-spacing:-0.04em; line-height:1; font-variant-numeric:tabular-nums }
.now .st .v .from { font-size:14px; color:#737370; font-variant-numeric:tabular-nums } .now .st .v .from::after { content:"→"; margin-left:6px; color:#c9c9c4 }
.now .st .v .dl { font-size:13px; font-weight:600; color:#141414; border-bottom:2px solid #f97316; padding-bottom:1px; font-variant-numeric:tabular-nums }
.now .st .bar { position:relative; height:3px; background:#ececea; margin-top:14px; border-radius:2px } .now .st .bar i { position:absolute; left:0; top:0; height:100%; width:100%; background:#141414; border-radius:2px; transform-origin:left; transition:transform 1s cubic-bezier(.3,.7,.2,1) .2s; transform:scaleX(var(--from)) }
.done2 .now .st .bar i { transform:scaleX(var(--to)) } .now .st .bar em { position:absolute; top:-3px; width:1px; height:9px; background:#9b9a95; left:calc(var(--from) * 100%) }
.now .next { border-left:1px solid #ececea; padding-left:32px } .now .next .k { display:block; margin-bottom:8px } .now .next p { margin:0; font-size:14px; line-height:1.65; color:#333 } .now .next p b { font-weight:650 }
.now .next .meta { margin-top:12px; font-size:12.5px; color:#737370 } .now .next .meta span { white-space:nowrap } .now .next .meta span + span::before { content:"·"; margin:0 7px; color:#c9c9c4 }
.now .next .live { display:inline-block; width:7px; height:7px; border-radius:50%; border:2px solid #f97316; vertical-align:1px; margin-right:7px }
/* 재는 방법 — 접힘 한 줄 */
.how { margin-top:14px; font-size:13.5px; color:#55554f } .how summary { cursor:pointer; list-style:none; display:inline-block; border-bottom:1px solid #d8d6d0; color:#141414 } .how summary::-webkit-details-marker { display:none } .how p { margin:10px 0 0; line-height:1.7; max-width:760px }
/* 타임라인 — 왼쪽 날짜 레일(sticky) + 세로선·점, 오른쪽 항목 판. 최신이 위 */
.tl { margin-top:28px } .grp { display:grid; grid-template-columns:150px minmax(0,1fr); gap:0 36px; align-items:start; position:relative; padding-bottom:26px }
.grp::before { content:""; position:absolute; left:118px; top:0; bottom:0; width:1px; background:#e3e1dc } .grp:last-child::before { bottom:auto; height:22px }
.grp .dt { position:sticky; top:22px; padding:14px 0 0; font-size:13.5px; color:#55554f; display:flex; justify-content:space-between; align-items:center; padding-right:26px }
.grp .dt b { font-size:15px; color:#141414; font-weight:650; letter-spacing:-0.01em; font-variant-numeric:tabular-nums } .grp .dt small { display:block; color:#9b9a95; font-size:12px; margin-top:2px }
.grp .dt .dot { width:9px; height:9px; border-radius:50%; background:#faf9f7; border:2px solid #141414; margin-right:-31px; flex:none } .grp.first .dt .dot { border-color:#f97316 } .grp.start .dt .dot { border-color:#b8b6b0 }
.ent { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:22px 28px 24px; margin-bottom:14px; opacity:0; transform:translateY(14px); transition:opacity .5s ease, transform .6s cubic-bezier(.3,.7,.2,1) }
.ent.in { opacity:1; transform:none } .ent h2 { margin:0 0 8px; font-size:18px; font-weight:650; letter-spacing:-0.02em; scroll-margin-top:24px }
.ent p { font-size:14.5px; line-height:1.75; color:#333; margin:8px 0; max-width:760px } .ent p b { color:#141414; font-weight:650 } .ent code { font-family:ui-monospace,Consolas,monospace; font-size:13px; background:#f6f5f2; padding:1px 5px; border-radius:4px }
.ent table { border-collapse:collapse; margin:14px 0 8px; font-size:14px; font-variant-numeric:tabular-nums } .ent th, .ent td { padding:8px 16px 8px 0; text-align:right; border-bottom:1px solid #ececea; vertical-align:baseline; white-space:nowrap }
.ent th { font-size:12px; color:#6b6b67; font-weight:600; border-bottom:1px solid #141414 } .ent th:first-child, .ent td:first-child { text-align:left; padding-right:24px; color:#141414; white-space:normal } .ent td:first-child { font-weight:500 }
.ent tr.now td { font-weight:650 } .ent td .dl { font-size:11.5px; font-weight:600; color:#141414; margin-left:6px; border-bottom:1px solid #f97316 } .ent td .dl.neg { border-bottom-color:#b8b6b0; color:#737370 }
.grp.start .ent { background:transparent; border-style:dashed } .grp.start .ent h2 .tag { font-size:12px; color:#737370; font-weight:500; margin-left:10px; letter-spacing:0 }
.tail { margin-top:6px; padding:18px 0 0 186px; font-size:13.5px; color:#6b6b67; line-height:1.7 } .tail code { font-family:ui-monospace,Consolas,monospace; font-size:12.5px }
.foot { margin-top:28px }
@media (prefers-reduced-motion: reduce) { .ent { opacity:1; transform:none; transition:none } .now .st .bar i { transition:none } }
@media screen and (max-width:720px){
  .head h1 { font-size:24px } .now { grid-template-columns:1fr 1fr; gap:18px 20px; padding:18px 16px } .now .st .v b { font-size:26px } .now .next { grid-column:1/-1; border-left:0; padding:14px 0 0; border-top:1px solid #ececea }
  .grp { grid-template-columns:minmax(0,1fr); gap:0; padding-bottom:12px } .grp::before { display:none } .grp .dt { position:static; padding:8px 0 8px; justify-content:flex-start; gap:10px } .grp .dt .dot { margin:0 } .grp .dt small { display:inline; margin-left:8px }
  .ent { padding:16px 16px 18px; border-radius:12px } .ent h2 { font-size:16px } .ent table { display:block; overflow-x:auto; max-width:100% } .ent td:first-child { white-space:nowrap }
  .tail { padding-left:0 }
}
"""

JS = r"""
requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.add('done2')));
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -8% 0px' });
document.querySelectorAll('.ent').forEach(e => io.observe(e));
if (matchMedia('(prefers-reduced-motion: reduce)').matches) document.querySelectorAll('.ent').forEach(e => e.classList.add('in'));
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
            cur[3].append(table(rows)); tbl.clear()

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


def num(c):
    m = re.fullmatch(r"([\d.,]+)\s*(%|%p|건|곳|초)?", c.strip())
    return (float(m.group(1).replace(",", "")), m.group(2) or "") if m else None


def delta(a, b):
    """전 → 후 차이 표기. % 는 p 로. 내린 건 회색."""
    d = b[0] - a[0]
    if abs(d) < 1e-9: return ""
    unit = "p" if b[1] == "%" else ""
    txt = (f"{d:+.1f}" if not float(d).is_integer() else f"{d:+,.0f}") + unit
    return f'<span class="dl {"neg" if d < 0 else ""}">{txt}</span>'


def table(rows):
    """행이 전/후면 '후' 칸마다 같은 열의 '전'과 비교, 열이 전/후(또는 처음/지금)면 각 행에서 비교."""
    head, body = rows[0], [list(r) for r in rows[1:]]
    labels = [r[0] for r in body]
    done = set()
    if "전" in labels and "후" in labels:
        a, b = body[labels.index("전")], body[labels.index("후")]
        for j in range(1, min(len(a), len(b))):
            x, y = num(a[j]), num(b[j])
            if x and y: b[j] = inline(b[j]) + delta(x, y); done.add(id(b))
    else:
        for i_lab, j_lab in (("전", "후"), ("처음", "지금")):
            if i_lab in head and j_lab in head:
                i, j = head.index(i_lab), head.index(j_lab)
                for r in body:
                    x, y = (num(r[i]) if i < len(r) else None), (num(r[j]) if j < len(r) else None)
                    if x and y: r[j] = inline(r[j]) + delta(x, y)
    def cell(c):
        return c if '<span class="dl' in c else inline(c)
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    bd = "".join(f'<tr class="{"now" if r[0] in ("후", "지금") else ""}">' + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{bd}</tbody></table>"


def hero(now_entry, n_changes, last_date):
    """'지금' 항목의 표(처음/지금 세 줄)와 '다음 병목' 문단으로 머리 숫자 판."""
    html = "".join(now_entry[3])
    rows = re.findall(r"<tr[^>]*><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", html)
    sts = ""
    for lab, a, b in rows:
        strip = lambda t: re.sub("<.*?>", "", re.sub(r"<span.*?</span>", "", t))   # 표 단계에서 붙은 차이 표기는 떼고 숫자만
        x, y = num(strip(a)), num(strip(b))
        sts += (f'<div class="st" style="--from:{x[0] / 100:.3f};--to:{y[0] / 100:.3f}"><span class="k">{lab}</span><div class="v"><span class="from">{strip(a)}</span><b>{strip(b)}</b>{delta(x, y)}</div>'
                f'<div class="bar"><i></i><em></em></div></div>')
    nxt = next((p for p in now_entry[3] if p.startswith("<p>") and "다음" in p), "")
    nxt = re.sub(r"^<b>다음 병목</b>:\s*", "", nxt.replace("<p>", "", 1).replace("</p>", ""))   # 칸 제목이 이미 "다음에 할 것"
    return (f'<div class="now">{sts}<div class="next"><span class="k">다음에 할 것</span><p>{nxt}</p>'
            f'<div class="meta"><span><i class="live"></i>계속 갱신</span><span>변경 {n_changes}건</span><span>마지막 {last_date[5:7]}.{last_date[8:]}</span><span>8/1 기준</span></div></div></div>')


def page(text):
    lead, entries = md(text)
    now = next(e for e in entries if e[2].startswith("지금")); start = next(e for e in entries if e[2].startswith("처음"))
    dated = [e for e in entries if e[1]]
    by_date = {}
    for e in dated: by_date.setdefault(e[1], []).insert(0, e)   # 최신이 위. 같은 날 안도 문서가 시간순이라 뒤집는다
    dates = sorted(by_date, reverse=True)
    def ent(e, tag=""):
        return f'<article class="ent" id="{e[0]}"><h2>{esc(e[2])}{tag}</h2>{"".join(e[3])}</article>'
    groups = "".join(f'<section class="grp {"first" if k == 0 else ""}"><div class="dt"><div><b>{d[5:7]}.{d[8:]}</b><small>{d[:4]} · {len(by_date[d])}건</small></div><span class="dot"></span></div><div>{"".join(ent(e) for e in by_date[d])}</div></section>'
                     for k, d in enumerate(dates))
    sd = re.search(r"\d{4}-\d{2}-\d{2}", start[2]); sd = sd.group(0) if sd else ""
    groups += (f'<section class="grp start"><div class="dt"><div><b>{sd[5:7]}.{sd[8:]}</b><small>{sd[:4]} · 시작점</small></div><span class="dot"></span></div>'
               f'<div>{ent(start, "<span class=tag>처음 잰 숫자</span>")}</div></section>')
    how = f'<details class="how"><summary>재는 방법</summary>{"".join(lead[1:])}</details>'
    html = (f'{nav("guest", "log")}<div class="head"><h1>개선 기록</h1>{lead[0].replace("<p>", "<p class=lead>", 1)}{hero(now, len(dated), dates[0])}{how}</div>'
            f'<div class="tl">{groups}</div>'
            f'<div class="tail">측정 방법과 숫자는 바꾸지 않고 쌓습니다. 원문 <code>docs/recommender/changelog.md</code>.</div>'
            f'<div class="foot">개선 기록 최종 시안 2차 — 최신순 타임라인(날짜 레일 sticky, 같은 날 묶음), 머리에 처음 → 지금 숫자 셋(막대는 처음 눈금에서 지금까지 차오름) + 다음에 할 것. 표의 전→후 차이는 주황 밑줄 숫자. 항목은 스크롤에 따라 떠오른다. 원문 {TODAY.isoformat()} 기준.</div>')
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
        txt = pg.evaluate("[...document.querySelectorAll('.head h1, .head .lead, .now .k, .now .meta, .how summary, .grp .dt, .tail, .nav, .foot')].map(e => e.innerText).join(' ')"); bad = [w for w in BANNED if w in txt]; assert not bad, bad
        pg.wait_for_timeout(1500)
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e); const dts = [...document.querySelectorAll('.grp .dt b')].map(e => e.textContent); return { ents: document.querySelectorAll('.ent').length, grps: document.querySelectorAll('.grp').length, dts,
            sts: document.querySelectorAll('.now .st').length, big: [...document.querySelectorAll('.now .st .v b')].map(e => e.textContent), dl: document.querySelectorAll('.head .now .dl').length, tdl: document.querySelectorAll('.ent td .dl').length,
            bar: cs(document.querySelector('.now .st .bar i')).transform, sticky: cs(document.querySelector('.grp .dt')).position, firstDot: cs(document.querySelector('.grp.first .dot')).borderColor,
            inView: document.querySelectorAll('.ent.in').length, raw: document.querySelector('.tl').innerText.includes('**') || document.querySelector('.tl').innerText.includes('|'), b: document.querySelector('.nav .links b').textContent, start: !!document.querySelector('.grp.start .ent') } }""")
        assert s["ents"] == 17 and s["grps"] == 4 and s["dts"] == ["10.16", "10.15", "10.14", "10.13"], s
        assert s["sts"] == 3 and s["big"] == ["49%", "28%", "38%"] and s["dl"] == 3 and s["tdl"] >= 15 and s["bar"] != "none" and s["sticky"] == "sticky" and s["firstDot"] == "rgb(249, 115, 22)", s
        assert s["inView"] >= 1 and not s["raw"] and s["b"] == "개선 기록" and s["start"], s
        pg.screenshot(path=str(out / "_shot_changelog.png"), full_page=False)
        pg.evaluate("document.querySelectorAll('.ent')[8].scrollIntoView({block:'center'})"); pg.wait_for_timeout(700)
        assert pg.evaluate("document.querySelectorAll('.ent')[8].classList.contains('in')")
        pg.screenshot(path=str(out / "_shot_changelog_mid.png"), full_page=False)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(600)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390") and pg.evaluate("getComputedStyle(document.querySelector('.grp .dt')).position") == "static"
        pg.screenshot(path=str(out / "_shot_changelog_390.png"), full_page=False)
        b.close()
    print(f"ok timeline {s['ents']} entries / {s['grps']} date groups newest first + start, hero {s['big']}, deltas {s['tdl']}, reveal, 390 ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(open(sys.argv[1], encoding="utf-8").read()))
    print("written", sys.argv[2])

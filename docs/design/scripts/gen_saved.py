"""검토함 최종 시안(`prototypes/saved-final.html`) — `/saved`. 탭 둘: 공고(검토 표시, 마감 순) / 저장한 회사(★).

- 공고: 결과 표와 같은 격자(제목 · 기관 · 어느 회사 결과에서 검토했는지 / 마감 / 추정가) + 검토 해제. 마감 지난 공고는 아래 회색 묶음, 30일 뒤 자동 정리.
- 저장한 회사: 회사 · 지역 · 등록업종 / 오늘 검토할 공고 N건 · 가장 빠른 마감 / 결과 보기 · ★ 해제.
- 상태: 비로그인(로그인·회원가입 두 버튼) / 빈 상태 / 채움. 데이터는 A 한종산업개발(sample.json)·B 금강환경(company_b.json)의 실제 추천 결과, 마감 지난 건은 A 의 실제 낙찰 공고.
- 메모·폴더·정렬 옵션 없음.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_saved.py ../docs/design/data ../docs/design/prototypes/saved-final.html
검증: gen_saved.py --check ../docs/design/prototypes/saved-final.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc, won, dleft  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_results_v2 import strongest  # noqa: E402
from gen_split import rgn_base  # noqa: E402
from gen_results_final import CSS as FINAL_CSS  # noqa: E402
from gen_login import nav, EMAIL, gate_auth  # noqa: E402

CSS = FINAL_CSS + r"""
html, body { background:#faf9f7 } .wrap { padding-bottom:140px }
.nav .cta { border-bottom:1px solid #141414; color:#141414 } .nav .me { position:relative; color:#141414; font-weight:600; cursor:pointer; border-bottom:1px solid #141414 }
.nav .me .menu { display:none }
.head { border-bottom:1px solid #141414; padding-bottom:0 } .head h1 { font-size:32px; letter-spacing:-0.035em; margin-bottom:14px }
/* 탭 — 머리 괘선 위에 앉는다. 선택은 먹 밑줄 2px */
.tabs2 { display:flex; gap:24px; font-size:15px } .tabs2 a { padding:0 0 12px; color:#55554f; border-bottom:2px solid transparent; margin-bottom:-1px } .tabs2 a.on { color:#141414; font-weight:650; border-bottom-color:#141414 }
.tabs2 a small { color:#737370; font-weight:450; margin-left:6px; font-size:13.5px }
.pane { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:6px 28px 28px; margin-top:22px }
.tab { display:none } .tab.on { display:block }
/* 공고 행 — 결과 표 격자 + 해제 */
.sh, .sr { display:grid; grid-template-columns:minmax(0,1fr) 84px 84px 64px; gap:0 12px; align-items:start }
.sh { padding:18px 0 8px; border-bottom:1px solid #141414; font-size:12px; color:#6b6b67; font-weight:600 }
.sr { padding:16px 0; border-bottom:1px solid #ececea; font-size:14px } .sr .t { font-size:16px; font-weight:600; line-height:1.4 } .sr .t a:hover { border-bottom:1px solid #f97316 }
.sr .sub { display:block; margin-top:4px; font-size:13.5px; color:#4a4a46 } .sr .sub .co { color:#141414 } .sr .sub .co::before { content:"★"; color:#f97316; font-size:11px; margin-right:5px } .sr .sub .why { color:#6b6b67 } .sr .sub span + span::before { content:"·"; margin:0 7px; color:#c9c9c4 }
.sr .sub span.co + span::before { content:"·"; margin:0 7px; color:#c9c9c4 }
.sr .r { text-align:right; font-size:15px } .sr .d { font-weight:600 } .sr .d.hot { color:#f97316 } .sr .d small { display:block; font-size:12.5px; color:#737370; font-weight:450 }
.sr .un { text-align:right; font-size:13px; color:#55554f } .sr .un a { border-bottom:1px solid #d8d6d0 } .sr .un a:hover { border-bottom-color:#f97316 }
.sr.rm { opacity:.35; transition:opacity .3s } .sr.rm .un a { border-bottom:0; color:#141414 }
/* 마감 지남 — 아래 회색 묶음 */
.past { margin-top:22px } .past .k { display:block; padding:0 0 8px; border-bottom:1px solid #e6e4df } .past .sr { color:#737370 } .past .sr .t, .past .sr .d, .past .sr .r, .past .sr .sub .co { color:#737370; font-weight:500 } .past .sr .sub .co::before { color:#b8b6b0 }
.past .sr .d small { color:#9b9a95 }
/* 회사 행 */
.ch, .cr { display:grid; grid-template-columns:minmax(0,1fr) 150px 110px 110px; gap:0 12px; align-items:start }
.ch { padding:18px 0 8px; border-bottom:1px solid #141414; font-size:12px; color:#6b6b67; font-weight:600 }
.cr { padding:16px 0; border-bottom:1px solid #ececea; font-size:14px } .cr .t { font-size:16px; font-weight:600; line-height:1.4 } .cr .t::before { content:"★"; color:#f97316; font-size:13px; margin-right:7px; vertical-align:1px }
.cr .sub { display:block; margin-top:4px; font-size:13.5px; color:#4a4a46 } .cr .sub span + span::before { content:"·"; margin:0 7px; color:#c9c9c4 }
.cr .n { font-size:15px } .cr .n b { font-weight:650; font-size:18px; letter-spacing:-0.02em } .cr .n small { display:block; font-size:12.5px; color:#737370; margin-top:2px }
.cr .n .d { font-weight:600 } .cr .n .d.hot { color:#f97316 }
.cr .go a.bt { height:32px } .cr .un { text-align:right; font-size:13px; color:#55554f } .cr .un a { border-bottom:1px solid #d8d6d0 }
.cr.rm { opacity:.35 }
/* 빈 상태·비로그인 */
.empty { padding:30px 0 10px; font-size:14px; color:#55554f; line-height:1.7 } .empty b { display:block; color:#141414; font-size:16px; font-weight:650; margin-bottom:4px } .empty a { color:#141414; border-bottom:1px solid #141414 }
.gateline { border-bottom:0; padding:26px 0 10px }
.foot { margin-top:28px }
.cases { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; align-items:center; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap; z-index:9 }
.cases span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .cases span.on { background:#141414; color:#fff } .cases i { width:1px; height:18px; background:#e6e4df; margin:0 4px }
.vw { display:none } .vw.on { display:block }
@media screen and (max-width:720px){
  .head h1 { font-size:24px } .pane { padding:0 16px 20px; border-radius:12px; margin-top:16px }
  .sh, .sr { grid-template-columns:minmax(0,1fr) 72px } .sh span:nth-child(3), .sh span:nth-child(4), .sr .r:not(.d), .sr .un { display:none } .sr .t { font-size:15px } .sr .sub { font-size:13px }
  .sr .d { font-size:14px }
  .ch, .cr { grid-template-columns:minmax(0,1fr) auto } .ch span:nth-child(3), .ch span:nth-child(4), .cr .go, .cr .un { display:none } .cr .n b { font-size:16px }
  .tabs2 { gap:18px; font-size:14px }
  .nav .links span.me { display:inline-block }   /* SHEET_CSS 가 390 에서 span 링크를 숨긴다 — 로그인된 이메일은 보여야 한다 */
  .cases { font-size:11.5px; padding:2px; white-space:normal; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px } .cases span { padding:5px 8px } .cases i { display:none }
}
"""

JS = r"""
const cs = document.querySelector('.cases');
function show(k){ document.querySelectorAll('.vw').forEach(v => v.classList.toggle('on', v.dataset.c === k)); cs.querySelectorAll('[data-c]').forEach(x => x.classList.toggle('on', x.dataset.c === k)); location.hash = k; }
cs.querySelectorAll('[data-c]').forEach(s => s.onclick = () => show(s.dataset.c));
document.querySelectorAll('.tabs2 a').forEach(a => a.addEventListener('click', e => { e.preventDefault(); const v = a.closest('.vw'); v.querySelectorAll('.tabs2 a').forEach(x => x.classList.toggle('on', x === a)); v.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.t === a.dataset.t)); }));
document.querySelectorAll('.un a').forEach(a => a.addEventListener('click', e => { e.preventDefault(); const r = a.closest('.sr, .cr'); const on = r.classList.toggle('rm'); a.textContent = on ? '되돌리기' : a.dataset.l; }));
if (location.hash.length > 1 && cs.querySelector(`[data-c="${location.hash.slice(1)}"]`)) show(location.hash.slice(1));
"""


def pick(data):
    """검토한 공고 — A 3건 + B 2건(진행 중), A 의 실제 낙찰 공고 2건(마감 지남). 저장한 회사 — A·B."""
    a, b = data["a"], data["b"]
    live = [(r, a["company"]["corp_nm"]) for r in a["reco"]["results"][:3]] + [(r, b["company"]["corp_nm"]) for r in b["reco"]["results"][:2]]
    live.sort(key=lambda x: x[0]["bid_clse_date"])
    past = [(dict(bid_ntce_nm=w["bid_ntce_nm"], dmnd_instt_nm=w["dmnd_instt_nm"], bid_clse_date=str(w["bid_clse_date"]), presmpt_prce=w["presmpt_prce"], score_breakdown=[]), a["company"]["corp_nm"])
            for w in a["awards"] if w["is_winner"] and w["bid_ntce_nm"] and w["bid_clse_date"]]
    cos = []
    for d in (a, b):
        res = d["reco"]["results"]; n0, d0 = min(dleft(r["bid_clse_date"]) for r in res)
        prof = d["profile"]; cos.append(dict(nm=d["company"]["corp_nm"], rgn=rgn_base(d["company"]["rgn_nm"]), n_ind=len(prof["industries"][0] + prof["industries"][1]), n=len(res), wk=sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7), d=(n0, d0)))
    return live, past, cos


def srow(r, co, past=False):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""; n, dd = dleft(r["bid_clse_date"]); s = strongest(r) if r.get("score_breakdown") else None
    why = f'<span class="why">{esc(s["label"])}</span>' if s else ""
    d = f'<span class="r d">마감<small>{dd.month}.{dd.day:02d}</small></span>' if past else f'<span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
    return (f'<div class="sr"><span><span class="t"><a href="#">{esc(r["bid_ntce_nm"])}</a></span><span class="sub"><span class="co">{esc(co)}</span><span>{esc(org)}</span>{why}</span></span>'
            f'{d}<span class="r">{won(r.get("presmpt_prce"))}</span><span class="un"><a href="#" data-l="해제">해제</a></span></div>')


def crow(c):
    n0, d0 = c["d"]
    return (f'<div class="cr"><span><span class="t">{esc(c["nm"])}</span><span class="sub"><span>{esc(c["rgn"])}</span><span>등록업종 {c["n_ind"]}</span></span></span>'
            f'<span class="n"><b>{c["n"]}건</b> 검토할 공고<small>이번 주 마감 {c["wk"]}건</small></span>'
            f'<span class="n"><span class="d {"hot" if n0 <= 7 else ""}">D-{n0}</span><small>가장 빠른 마감 {d0.month}.{d0.day:02d}</small></span>'
            f'<span class="un"><a class="bt" href="#" style="height:32px;border-bottom:1px solid #e3e1dc">결과</a> &nbsp; <a href="#" data-l="★ 해제">★ 해제</a></span></div>')


def head(state, n_live, n_cos):
    tabs = (f'<div class="tabs2"><a href="#" class="on" data-t="n">공고<small>{n_live}</small></a><a href="#" data-t="c">저장한 회사<small>{n_cos}</small></a></div>' if state == "in" else "")
    return f'<div class="head"><h1>검토함</h1>{tabs}</div>'


def view_in(live, past, cos):
    rows = "".join(srow(r, co) for r, co in live)
    prows = "".join(srow(r, co, past=True) for r, co in past)
    tab_n = (f'<div class="tab on" data-t="n"><div class="sh"><span>공고 · 결과를 본 회사 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span><span></span></div>{rows}'
             + (f'<div class="past"><span class="k">마감 지남 {len(past)}건 — 마감 30일 뒤 자동 정리</span>{prows}</div>' if past else "") + '</div>')
    tab_c = f'<div class="tab" data-t="c"><div class="ch"><span>회사</span><span>오늘</span><span>마감</span><span></span></div>{"".join(crow(c) for c in cos)}</div>'
    return f'{nav("in", "saved")}{head("in", len(live), len(cos))}<div class="pane">{tab_n}{tab_c}</div>'


def view_empty():
    tab_n = '<div class="tab on" data-t="n"><div class="empty"><b>검토 표시한 공고가 없습니다</b>결과 표의 행을 펼쳐 <a href="#">검토</a>를 누르면 여기에 보관됩니다.</div></div>'
    tab_c = '<div class="tab" data-t="c"><div class="empty"><b>저장한 회사가 없습니다</b>회사 페이지 또는 결과 머리의 ☆ 로 저장합니다.</div></div>'
    return f'{nav("in", "saved")}{head("in", 0, 0)}<div class="pane">{tab_n}{tab_c}</div>'


def view_guest():
    return f'{nav("guest", "saved")}{head("guest", 0, 0)}<div class="pane">{gate_auth(5).replace("나머지 0건은 로그인 후 공개", "검토함은 로그인 후 사용").replace("상위 5건은 로그인 없이 공개", "검토 표시한 공고와 저장한 회사를 보관")}</div>'


def page(data):
    live, past, cos = pick(data)
    scenes = [("in", "채움", view_in(live, past, cos)), ("empty", "빈 상태", view_empty()), ("guest", "비로그인", view_guest())]
    vws = "".join(f'<div class="vw {"on" if k == "in" else ""}" data-c="{k}">{h}</div>' for k, _, h in scenes)
    pills = "".join(f'<span data-c="{k}" class="{"on" if k == "in" else ""}">{l}</span>' for k, l, _ in scenes)
    foot = (f'<div class="foot">검토함 최종 시안 — 공고(검토 표시, 마감 순, 어느 회사 결과에서 검토했는지 ★ 표시) / 저장한 회사(오늘 검토할 공고 N건 · 가장 빠른 마감 · 결과). 마감 지난 공고는 아래 회색, 30일 뒤 자동 정리. 해제는 되돌리기 가능. '
            f'공고·회사는 {TODAY.isoformat()} 실제 추천 결과(data/sample.json · company_b.json), 마감 지난 건은 한종산업개발의 실제 낙찰 공고.</div>')
    return (f'<!doctype html><html lang="ko" class="v-panel"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 검토함</title>{FONT}'
            f'<style>{CSS}</style></head><body class="done"><div class="wrap">{vws}{foot}</div><div class="cases">{pills}</div><script>{JS}</script></body></html>')


BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요", "검토 인장", "낼 수 있", "메모", "폴더"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in p.read_text(encoding="utf-8")
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        txt = pg.evaluate("[...document.querySelectorAll('.vw')].map(v => v.innerText).join('\\n')"); bad = [w for w in BANNED if w in txt]; assert not bad, bad
        s = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); const d = [...v.querySelectorAll('.tab[data-t="n"] > .sr .d')].map(e => e.firstChild.textContent); return { live: v.querySelectorAll('.tab[data-t="n"] > .sr').length,
            past: v.querySelectorAll('.past .sr').length, order: d, cos: v.querySelectorAll('.sr .sub .co').length, tabc: cs(v.querySelector('.tab[data-t="c"]')).display, star: getComputedStyle(v.querySelector('.sr .sub .co'), '::before').color, bg: cs(document.body).backgroundColor } }""")
        assert s["live"] == 5 and s["past"] == 2 and s["cos"] == 7 and s["tabc"] == "none" and s["star"] == "rgb(249, 115, 22)" and s["bg"] == "rgb(250, 249, 247)", s
        nums = [int(x[2:]) for x in s["order"]]; assert nums == sorted(nums), nums
        pg.screenshot(path=str(out / "_shot_saved_notices.png"), full_page=True)
        pg.click('.vw.on .tab[data-t="n"] > .sr .un a'); pg.wait_for_timeout(150)
        u = pg.evaluate("""() => { const r = document.querySelector('.vw.on .sr'); return { rm: r.classList.contains('rm'), t: r.querySelector('.un a').textContent } }"""); assert u["rm"] and u["t"] == "되돌리기", u
        pg.click('.vw.on .tab[data-t="n"] > .sr .un a'); assert not pg.evaluate("document.querySelector('.vw.on .sr').classList.contains('rm')")
        pg.click('.vw.on .tabs2 a[data-t="c"]'); pg.wait_for_timeout(150)
        c = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { on: cs(v.querySelector('.tab[data-t="c"]')).display, n: v.querySelectorAll('.cr').length, nums: [...v.querySelectorAll('.cr .n b')].map(e => e.textContent) } }""")
        assert c["on"] == "block" and c["n"] == 2 and c["nums"] == ["12건", "12건"], c
        pg.screenshot(path=str(out / "_shot_saved_companies.png"), full_page=True)
        pg.click('.cases [data-c="empty"]'); pg.wait_for_timeout(150); assert pg.evaluate("document.querySelectorAll('.vw.on .empty').length") == 2
        pg.screenshot(path=str(out / "_shot_saved_empty.png"), full_page=False)
        pg.click('.cases [data-c="guest"]'); pg.wait_for_timeout(150)
        g = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { btns: v.querySelectorAll('.gateline .bt').length, tabs: v.querySelectorAll('.tabs2').length, cta: v.querySelector('.nav .cta').textContent } }"""); assert g["btns"] == 2 and g["tabs"] == 0 and g["cta"] == "로그인", g
        pg.screenshot(path=str(out / "_shot_saved_guest.png"), full_page=False)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri() + "#in"); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)   # 해시만 바뀌면 goto 가 다시 안 읽는다
        assert not pg.evaluate("document.documentElement.scrollWidth > 390") and pg.evaluate("getComputedStyle(document.querySelector('.vw.on .sr .un')).display") == "none"
        pg.screenshot(path=str(out / "_shot_saved_390.png"), full_page=True)
        b.close()
    print("ok notices 5 (마감 순) + past 2, ★ company chips, 해제/되돌리기, companies tab 2 × 12건, empty ×2, guest gate 2 buttons, 390 ok, banned 0")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    src = Path(sys.argv[1])
    data = {k: json.load(open(src / f"company_{k}.json", encoding="utf-8")) for k in ("a", "b")}
    data["a"]["reco"] = json.load(open(src / "sample.json", encoding="utf-8"))
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(data))
    print("written", sys.argv[2])

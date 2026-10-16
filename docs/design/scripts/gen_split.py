"""결과 페이지 두 단 시안(`prototypes/split.html`) — 위에 회사 이름, 왼쪽 회사 정보 세로(고정), 오른쪽 공고.
"한 페이지에 보고서처럼"(2026-10-16 승우님)은 PDF 가 아니라 **판**을 바꿔 보자는 뜻이었다 — 기준 띠를 가로로 눌러 넣는 대신 왼쪽 단에 풀어 쓰고, 공고는 오른쪽에.

오른쪽은 두 모양을 스위치로 비교한다: 블록(자격·근거 항상 노출, 한 건 3~4줄) / 표(한 건 1줄, 펼쳐서 자격·근거).
머리 장면(선 캔버스)은 넣지 않는다 — flow.html 에서 결정됐고 여기서는 그 아래 판만 본다. 걸러낸 경로 줄은 회사 이름 아래 전체 폭.
문장은 gen_flow.why_lines/qual_lines(공문 톤), 데이터는 기준 띠(gen_results_v6.crit)와 같은 prof. 주황은 마지막 12 · D-day ≤ 7 · 검토 버튼 테두리 · 로고 타일뿐.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_split.py ../docs/design/data/sample.json ../docs/design/data/funnel.json ../docs/design/prototypes/split.html
검증: 같은 환경에서 gen_split.py --check ../docs/design/prototypes/split.html → 1280px 블록·표, 390px 캡처 3장, 행 수·고정 단·주황만 확인.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc, won, dleft  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v2 import strongest  # noqa: E402
from gen_flow import ORANGE, nav, why_lines, qual_lines  # noqa: E402
from gen_report import qual_line, LABELS  # noqa: E402

SPLIT_CSS = r"""
.wrap { width:auto; max-width:1120px; margin:0 auto; padding:0 20px 120px }
.brand { font-weight:800; font-size:16px; letter-spacing:-0.035em; gap:8px } .brand svg { display:block }
.ok::after { color:#141414 }
/* 머리 — 회사 이름 + 한 줄 + 걸러낸 경로. 전체 폭 */
.head { padding:26px 0 18px; border-bottom:1px solid #141414 }
.head h1 { margin:0; font-size:24px; letter-spacing:-0.03em; font-weight:650; line-height:1.2 } .head h1 small { font-size:13px; color:#737370; font-weight:450; letter-spacing:0; margin-left:12px }
.head .meta { margin-top:6px; font-size:13.5px; color:#55554f } .head .meta span + span::before { content:"·"; margin:0 8px; color:#c9c9c4 }
.sum { display:flex; justify-content:space-between; align-items:flex-end; gap:24px; padding-top:16px }
.chain { display:flex; align-items:flex-start; gap:12px; font-size:13px; color:#737370 } .chain .k { padding-top:3px; margin-right:4px }
.chain .n { font-size:20px; font-weight:650; color:#141414; letter-spacing:-0.02em; line-height:1.15 } .chain .n.acc { color:#f97316 } .chain .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:4px }
.chain .l { font-size:11.5px; color:#737370; margin-top:3px; line-height:1.3 } .chain i { font-style:normal; color:#c9c9c4; font-size:16px; padding-top:2px }
.tabs { text-align:right; font-size:13px; color:#55554f; line-height:1.9 } .tabs b { color:#141414; font-weight:650; border-bottom:1px solid #141414; padding-bottom:1px } .tabs span + span::before, .tabs b + span::before { content:"·"; margin:0 8px; color:#c9c9c4 }
.tabs .due .d { font-weight:650; color:#141414 } .tabs .due .d.hot { color:#f97316 }
/* 두 단 */
.cols { display:grid; grid-template-columns:240px minmax(0,1fr); gap:0 44px; align-items:start }
.side { position:sticky; top:0; padding:22px 0 20px; font-size:13px }
.side summary { list-style:none; cursor:default } .side summary::-webkit-details-marker { display:none }
.side summary .k { display:block } .side summary .h { display:none }
.side .sec { padding:14px 0 0 } .side .sec .k { display:block; margin-bottom:6px }
.side .txt { font-size:13px; line-height:1.65; color:#333 } .side .txt b { font-weight:600 } .side .txt .dim { color:#737370 }
.side ul { margin:0; padding:0; list-style:none } .side li { padding:2px 0; line-height:1.5; color:#333; border-bottom:1px solid #f1f0ec }
.side li.rep { font-weight:600 } .side li.rep::after { content:"대표"; font-size:10.5px; color:#737370; font-weight:500; margin-left:6px; letter-spacing:.02em }
.side .act { display:flex; gap:10px; align-items:center; margin-top:18px; padding-top:14px; border-top:1px solid #141414 } .side .act .bt { height:32px }
.side .mute { display:block; margin-top:10px; font-size:11.5px }
/* 오른쪽 머리 + 스위치 */
.main { padding-top:22px }
.mh { display:flex; align-items:center; justify-content:space-between; padding-bottom:10px; border-bottom:1px solid #141414 }
.mh .k { display:block } .mh .k b { color:#141414; font-size:13px; font-weight:650; letter-spacing:0; text-transform:none; margin-right:6px }
.sw { display:flex; gap:2px; border:1px solid #e3e1dc; border-radius:999px; padding:2px; font-size:12px } .sw span { padding:4px 12px; border-radius:999px; color:#55554f; cursor:pointer } .sw span.on { background:#141414; color:#fff }
.v-table, [data-v="table"] .v-block { display:none } [data-v="table"] .v-table { display:block }
/* 블록 — 보고서 행을 화면 크기로 */
.bk { display:grid; grid-template-columns:28px 1fr; gap:0 10px; padding:14px 0 15px; border-bottom:1px solid #ececea; font-size:13.5px }
.bk .no { font-size:12px; color:#8f8f8b; padding-top:3px }
.bk .t { font-weight:600; font-size:15px; letter-spacing:-0.01em; line-height:1.4 }
.bk .m { margin-top:3px; color:#55554f; font-size:13px } .bk .m .d { font-weight:650; color:#141414 } .bk .m .d.hot { color:#f97316 }
.bk .q, .bk .w { display:grid; grid-template-columns:58px 1fr; gap:0 8px; margin-top:7px; line-height:1.6; color:#333 } .bk .q { margin-top:9px }
.bk .q b, .bk .w b { font-weight:650; font-size:12.5px; color:#141414 }
.bk .acts { display:flex; gap:14px; align-items:center; margin-top:10px; font-size:12.5px } .bk .acts a.u { color:#55554f; border-bottom:1px solid #d8d6d0 }
.bt.rv { border-color:#f97316; height:30px; padding:0 12px; font-size:12.5px }
/* 표 — 번호·공고(2줄: 제목 / 기관 · 근거)·마감·추정가. 근거는 열이 아니라 제목 아래 둘째 줄 — 폭을 안 쓰고 늘 보인다 */
.th, .tr { grid-template-columns:28px minmax(0,1fr) 84px 72px; gap:0 12px }
.tr { padding:12px 0; align-items:start } .tr .no { padding-top:3px } .tr .t { font-size:14.5px; display:block }
.tr .sub { display:block; margin-top:3px; font-size:12.5px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .tr .sub .why { color:#6b6b67 } .tr .sub .why::before { content:"·"; margin:0 6px; color:#c9c9c4 }
.tr .d, .tr .r { padding-top:2px }
/* 펼침 — display 토글 대신 grid-template-rows 0fr → 1fr. 높이를 모르는 내용을 부드럽게 여는 유일한 CSS 방법 */
.x { display:grid; grid-template-rows:0fr; grid-template-columns:1fr; gap:0; padding:0 0 0 40px; border-bottom:0; opacity:0;
     transition:grid-template-rows .4s cubic-bezier(.3,.7,.2,1), padding .4s cubic-bezier(.3,.7,.2,1), opacity .3s ease }
.x.on { grid-template-rows:1fr; padding:16px 0 20px 40px; border-bottom:1px solid #ececea; opacity:1; transition-delay:0s, 0s, .1s }
.x > .xi { min-height:0; overflow:hidden; display:grid; grid-template-columns:1fr 1.2fr; gap:28px }
.x li { font-size:13px; line-height:1.6; padding:3px 0 } .x .acts { grid-column:1/-1; margin-top:0 }
.tr .t { transition:color .15s ease } .bt { transition:background .15s ease, border-color .15s ease, color .15s ease }
@media (prefers-reduced-motion: reduce) { .x, .tr .t, .bt { transition:none !important } }
.fade .bk { opacity:.32; filter:blur(1.5px); pointer-events:none }
.gateline { font-size:13.5px; flex-wrap:wrap } .gateline .in span:first-child { width:220px }
.foot { margin-top:28px; font-size:12px; color:#737370; line-height:1.6; max-width:880px }
/* 390 — 한 단. 회사 정보는 접힌 한 줄, 공고는 블록만 */
@media screen and (max-width:720px){
  .wrap { padding:0 16px 90px } .nav .links span:not(.cta) { display:none }
  .head h1 { font-size:20px } .head h1 small { display:block; margin:4px 0 0 } .sum { flex-direction:column; align-items:flex-start; gap:10px }
  .chain { gap:8px } .chain .k { display:none } .chain .n { font-size:16px } .chain .l { font-size:10.5px } .tabs { text-align:left }
  .cols { grid-template-columns:1fr } .side { position:static; padding:14px 0; border-bottom:1px solid #ececea }
  .side summary { cursor:pointer; display:flex; justify-content:space-between; align-items:center } .side summary .h { display:inline; font-size:12.5px; color:#55554f; border-bottom:1px solid #d8d6d0 }
  .side[open] summary .h.o, .side:not([open]) summary .h.c { display:none }
  .main { padding-top:14px } .sw { display:none } .v-table { display:none !important } .v-block { display:block !important }
  .bk .q, .bk .w { grid-template-columns:1fr; gap:0 } .bk .m { line-height:1.5 }
  .gateline .in { width:100%; flex-wrap:wrap } .gateline .in span:first-child { flex:1; width:auto }
}
"""
CSS = SHEET_CSS.replace("#e8431b", ORANGE) + SPLIT_CSS

JS = r"""
document.querySelectorAll('.sw span').forEach(s => s.onclick = () => { document.body.dataset.v = s.dataset.v;
  document.querySelectorAll('.sw span').forEach(x => x.classList.toggle('on', x === s)); });
document.querySelectorAll('.v-table .tr').forEach(t => t.onclick = () => t.nextElementSibling.classList.toggle('on'));
if (matchMedia('(max-width:720px)').matches) document.querySelector('details.side').open = false;
"""


def rgn_base(rgn):
    """표시용 지역 — 기초자치단체까지(시·도 + 시·군·구). 일반구(마산합포구·분당구)·동은 지역 제한 단위가 아니라 뺀다.
    제한 공고의 42% 가 시·군·구 단위라 시·도만으론 모자라고, 그 아래는 소음(2026-10-16 실측)."""
    return " ".join((rgn or "").split()[:2])


def side(co, prof):
    rep, rest = prof["industries"]
    names = {x.split("(")[0] for x in rep}
    seen, lis = set(), [f'<li class="rep">{esc(n)}</li>' for n in sorted(names)]
    for x in rest:   # 괄호 뒤 세부만 다른 이름(엔지니어링사업(…) ×3)은 한 줄로 — 기준 띠의 ind_txt 와 같은 자름
        n = x.split("(")[0]
        if n in names or n in seen: continue
        seen.add(n); lis.append(f"<li>{esc(n)}</li>")
    inds = "".join(lis)
    return (f'<details class="side" open><summary><span class="k">회사 정보 <span class="h o">펼치기</span><span class="h c">접기</span></span></summary>'
            f'<div class="sec"><span class="k">등록업종 {len(rep) + len(rest)}</span><ul>{inds}</ul></div>'
            f'<div class="sec"><span class="k">공급물품</span><div class="txt"><span class="dim">등록 없음</span> — 물품 공고 추천에는 등록 필요</div></div>'
            f'<div class="sec"><span class="k">지역</span><div class="txt">본사 <b>{esc(rgn_base(co["rgn_nm"]))}</b><br><span class="dim">제한 공고가 적은 단위(시·도 또는 시·군·구)까지 판정</span></div></div>'
            f'<div class="sec"><span class="k">면허</span><div class="txt">공고 요구 면허 그룹마다 등록업종 중 하나 포함 시 통과</div></div>'
            f'<div class="sec"><span class="k">규모</span><div class="txt"><span class="dim">미입력</span> — 소기업·중소기업 제한 공고 판정 기준</div></div>'
            f'<div class="sec"><span class="k">사업자 상태</span><div class="txt">계속사업자 · 제재 없음</div></div>'
            f'<div class="act"><a class="bt dark" href="#">확인</a><a class="bt txt" href="#"><u>수정 요청</u></a></div>'
            f'<span class="mute">나라장터 업체정보 · 10.14 갱신</span></details>')


def _meta(r):
    n, dd = dleft(r["bid_clse_date"])
    return n, f'마감 <span class="d {"hot" if n <= 7 else ""}">D-{n}</span> ({dd.month}.{dd.day:02d}) · 추정가 {won(r.get("presmpt_prce"))}'


def block(i, r, prof):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    _, meta = _meta(r)
    return (f'<div class="bk"><span class="no">{i:02d}</span><div><div class="t">{esc(r["bid_ntce_nm"])}</div><div class="m">{esc(org)} · {meta}</div>'
            f'<div class="q"><b>참가 자격</b><span>{qual_line(r, prof)}</span></div>'
            f'<div class="w"><b>추천 근거</b><span>{"<br>".join(why_lines(r, org))}</span></div>'   # 전부, 한 줄에 하나 — 2개로 자르면 근거가 빈약해 보인다(실제 2~3개, 최대 5)
            f'<div class="acts"><a class="u" href="{esc(r["bid_ntce_url"])}">나라장터 원문</a><a class="bt rv" href="#">검토</a></div></div></div>')


def trow(i, r, prof, open_=False):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    n, dd = dleft(r["bid_clse_date"])
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r, prof)); wl = "".join(f"<li>{w}</li>" for w in why_lines(r, org))
    s = strongest(r); why = f'<span class="why">{esc(s["label"])}</span>' if s else ""
    return (f'<div class="tr" data-no="{esc(r["bid_ntce_no"])}"><span class="no">{i:02d}</span><span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="sub">{esc(org)}{why}</span></span>'
            f'<span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span><span class="r">{won(r.get("presmpt_prce"))}</span></div>'
            f'<div class="x {"on" if open_ else ""}"><div class="xi"><div><span class="k">참가 자격</span><ul>{ql}</ul></div><div><span class="k">추천 근거</span><ul>{wl}</ul></div>'
            f'<div class="acts"><a class="bt dark" href="{esc(r["bid_ntce_url"])}">나라장터 원문</a><a class="bt rv" href="#">검토</a></div></div></div>')


def gate(n):
    return (f'<div class="gateline"><b>나머지 {n - 5}건은 이메일 등록 후 공개</b><span class="dim">상위 5건은 등록 없이 공개 · 비밀번호 없음</span><span class="sp"></span>'
            f'<span class="in"><span>you@company.co.kr</span><span class="bt dark">이메일 등록</span></span></div>')


def page(d, prof, f):
    res, co = d["results"], d["company"]
    n_ind = len(prof["industries"][0] + prof["industries"][1])
    bks = [block(i, r, prof) for i, r in enumerate(res, 1)]
    trs = [trow(i, r, prof, i == 1) for i, r in enumerate(res, 1)]
    vals = [f'{f["total"]:,}', str(f["industry"]), str(f["qualified"]), str(len(res))]
    chain = "".join(f'<div><div class="n {"acc" if k == 3 else ""}">{v}{"<small>건</small>" if k == 3 else ""}</div><div class="l">{l}</div></div>' + ("<i>→</i>" if k < 3 else "")
                    for k, (v, l) in enumerate(zip(vals, LABELS)))
    dues = sorted(dleft(r["bid_clse_date"]) for r in res); wk = sum(1 for n, _ in dues if n <= 7); n0, d0 = dues[0]
    tabs = (f'<div class="tabs"><div><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span></div>'
            f'<div class="due">이번 주 마감 {wk}건 · 가장 빠른 마감 <span class="d {"hot" if n0 <= 7 else ""}">D-{n0}</span> ({d0.month}.{d0.day:02d})</div></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="head"><h1>{esc(co["corp_nm"])}<small>{co["bizrno"][:6]}*****</small></h1>'
            f'<div class="meta"><span>{esc(rgn_base(co["rgn_nm"]))}</span><span>등록업종 {n_ind}</span><span>공급물품 없음</span><span>기준일 {TODAY.isoformat()}</span></div>'
            f'<div class="sum"><div class="chain"><span class="k">걸러낸 경로</span>{chain}</div>{tabs}</div></div>'
            f'<div class="cols">{side(co, prof)}<div class="main">'
            f'<div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span><div class="sw"><span class="on" data-v="block">블록</span><span data-v="table">표</span></div></div>'
            f'<div class="v-block">{"".join(bks[:5])}{gate(len(res))}<div class="fade">{"".join(bks[5:])}</div></div>'
            f'<div class="v-table"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>'
            f'{"".join(trs[:5])}{gate(len(res))}<div class="fade">{"".join(trs[5:])}</div></div>'
            f'</div></div>'
            f'<div class="foot">두 단 시안 — 왼쪽 회사 정보(기준 띠를 세로로, 스크롤해도 고정) / 오른쪽 공고. 게이트는 5건 바로 뒤, 흐린 7건은 그 아래(flow 는 흐림 뒤에 게이트 — 블록은 흐림이 1,000px 라 순서를 바꿨다). 스위치로 블록(자격·근거 상시) / 표(1줄, 행 클릭 펼침)를 비교. '
            f'머리 장면(선 캔버스)은 flow.html 결정 그대로 이 위에 얹는다. 720px 이하는 한 단, 회사 정보는 접힌 한 줄, 공고는 블록만. 숫자·공고명은 {TODAY.isoformat()} 실제 추천 결과(data/).</div></div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 결과 — 두 단</title>{FONT}'
            f'<style>{CSS}</style></head><body data-v="block">{body}<script>{JS}</script></body></html>')


def check(path):
    """Playwright: 블록·표 각 12건, 왼쪽 단 sticky, 주황만(인주 0), 1280px 두 장 + 390px 한 장 캡처."""
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in CSS
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e); return { bk: document.querySelectorAll('.bk').length, tr: document.querySelectorAll('.v-table .tr').length,
            sticky: cs(document.querySelector('.side')).position, tbl: cs(document.querySelector('.v-table')).display, acc: cs(document.querySelector('.chain .n.acc')).color, labs: document.querySelectorAll('.chain .l').length, subs: document.querySelectorAll('.v-table .tr .sub .why').length,
            sideW: document.querySelector('.side').getBoundingClientRect().width, mainW: document.querySelector('.main').getBoundingClientRect().width } }""")
        assert s["bk"] == 12 and s["tr"] == 12 and s["sticky"] == "sticky" and s["tbl"] == "none" and s["acc"] == "rgb(249, 115, 22)" and s["labs"] == 4 and s["subs"] >= 10, s
        pg.screenshot(path=str(out / "_shot_split_block.png"), full_page=True)
        pg.click('.sw [data-v="table"]'); pg.wait_for_timeout(100)
        t = pg.evaluate("""() => ({ blk: getComputedStyle(document.querySelector('.v-block')).display, open: document.querySelectorAll('.x.on').length })""")
        assert t["blk"] == "none" and t["open"] == 1, t
        pg.locator('.v-table > .tr').nth(2).click(); pg.wait_for_timeout(100)   # 셋째 행 펼침 — 두 개 열린 채 캡처
        assert pg.evaluate("document.querySelectorAll('.x.on').length") == 2
        pg.screenshot(path=str(out / "_shot_split_table.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        m = pg.evaluate("""() => ({ open: document.querySelector('details.side').open, cols: getComputedStyle(document.querySelector('.cols')).gridTemplateColumns.split(' ').length,
            sw: getComputedStyle(document.querySelector('.sw')).display, overflow: document.documentElement.scrollWidth > 390 })""")
        assert m["open"] is False and m["cols"] == 1 and m["sw"] == "none" and not m["overflow"], m
        pg.screenshot(path=str(out / "_shot_split_390.png"), full_page=True)
        b.close()
    print(f"ok blocks={s['bk']} rows={s['tr']} side={s['sideW']:.0f}px main={s['mainW']:.0f}px; 390: side closed, 1 col")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    from jobs.evaluate_recommender import connect, fetch_company_profile
    src, fsrc, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc))
    prof = fetch_company_profile(connect(), "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, f))
    print("written", out)

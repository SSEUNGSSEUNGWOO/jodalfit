"""결과 페이지 최종 시안(`prototypes/results-final.html`) = flow 의 머리 장면·네 상태 + split 의 두 단 표형 본문.

- 머리: 회사 이름·사업자번호 마스킹·한 줄 → 선 캔버스(gen_flow 엔진 그대로) → 접히면 걸러낸 경로(숫자 + 단계 라벨) 와 종류 탭·마감 요약 한 줄.
- 본문: 왼쪽 240px 회사 정보(sticky) / 오른쪽 표(제목 / 기관 · 근거 둘째 줄, 행 클릭 펼침). 블록 스위치는 split.html 에만(비교용). 화면 = 표, 메일·인쇄 = 블록(report.html).
- 네 상태(알약): 0건 — 오른쪽 단만 비고 왼쪽 회사 정보가 이유 / 오류·지연 — 머리 정지 + 다시 시도(본문은 안 뜸) / 이메일 뒤 — 게이트 없이 12건 / 검토 뒤 — 행 왼쪽 주황 괘선.
- 720px 이하: 한 단, 회사 정보 접힘, 표는 제목·둘째 줄 + 마감.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_results_final.py ../docs/design/data/sample.json ../docs/design/data/funnel.json ../docs/design/data/scene_titles.json ../docs/design/prototypes/results-final.html
검증: gen_results_final.py --check ../docs/design/prototypes/results-final.html → 캡처 6장(기본·0건·오류·이메일 뒤·검토 뒤·390), 금지어·인주 0, 행 12.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc, dleft  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_flow import CSS as FLOW_CSS, JS, labels, field, cfg, nav, ZERO, ERR  # noqa: E402
from gen_split import SPLIT_CSS, side, trow, gate  # noqa: E402
from gen_report import LABELS  # noqa: E402

CSS = FLOW_CSS + SPLIT_CSS + r"""
/* 머리 — split 의 .head 를 캔버스 위에. 괘선은 .stage 가 긋는다 */
.head { padding:26px 0 0; border-bottom:0 }
/* 걸러낸 경로 — flow 의 접힘(height 0 → 보임)은 유지하고 모양은 split: 숫자 + 단계 라벨, 오른쪽 종류 탭·마감 요약 */
.chain { justify-content:space-between; align-items:flex-start; gap:24px } .chain .k { padding-top:3px }
.chain .fun { display:flex; align-items:flex-start; gap:12px } .chain .fun > div { display:flex; flex-direction:column }
.chain b { font-size:20px; line-height:1.15 } .chain b.acc { color:#f97316 } .chain .l { font-size:11.5px; color:#737370; margin-top:3px; line-height:1.3 }
.chain i { font-size:16px; padding-top:2px } .chain .nl { display:flex; align-items:baseline } .chain .un { font-size:11.5px; color:#6b6b67; margin-left:4px }
.st-zero .tabs { display:none }   /* 0건이면 종류 탭·마감 요약은 거짓말이 된다(결과 12건 기준 계산) */
.done .chain { height:auto; padding-top:16px }
.tabs em { font-style:normal; color:#141414; font-weight:650; border-bottom:1px solid #141414; padding-bottom:1px } .tabs em + span::before { content:"·"; margin:0 8px; color:#c9c9c4 }
/* 본문은 두 단. 0건이면 오른쪽 단만 비고 왼쪽은 그대로 — 기준이 곧 이유 */
.res .cols { border-top:0 }
.st-zero .sheet, .st-zero .mh { display:none } .zero { border-bottom:0; padding-top:22px }
.okline { padding:13px 0 } .st-email .fade .tr { cursor:pointer }
.rvn { padding-left:40px } .tr.rvd::before { left:-16px }
@media screen and (max-width:720px){
  .head h1 { font-size:20px } .chain { flex-direction:column; gap:10px } .chain .k { display:none } .chain b { font-size:16px } .chain .l { font-size:10.5px } .tabs { text-align:left }
  /* flow 의 390 표 규칙(.org/.why 열)은 두 줄 표에 안 맞는다 — 제목 묶음 + 마감만 */
  .tr { grid-template-columns:minmax(0,1fr) auto; grid-template-areas:none; gap:0 12px; padding:12px 0 } .tr .no, .tr .r:not(.d) { display:none } .tr .t { white-space:normal; font-size:14px }
  .tr .d { grid-area:auto }                 /* flow 의 grid-area:d 는 areas 가 없으면 새 줄로 밀린다 */
  .tr .sub { white-space:normal } .tr .sub .why { display:inline }   /* flow 의 .tr .why{display:none} 은 열용 — 둘째 줄 칩은 보인다 */
  .x { padding-left:0 } .rvn { padding-left:0 } .tr.rvd::before { left:-16px }
}
"""

# flow 의 RUN_JS 는 .ctl 알약·검토·상태를 다 처리한다. 여기선 표 행 펼침 하나만 더한다(펼침 안 버튼 클릭은 행으로 전파되지 않게 .x 는 형제라 무관).
JS_EXTRA = r"""
document.querySelectorAll('.sheet .tr').forEach(t => t.addEventListener('click', () => t.nextElementSibling.classList.toggle('on')));
if (matchMedia('(max-width:720px)').matches) document.querySelector('details.side').open = false;
"""


def chain(f, d, res):
    vals = [f'{f["total"]:,}', str(f["industry"]), str(f["qualified"]), str(len(res))]
    # 숫자는 <b> 하나 — flow 의 setCounts 가 .chain b 의 textContent 를 갈아 끼우므로 '건' 은 b 밖에
    fun = "".join(f'<div><span class="nl"><b class="{"acc" if k == 3 else ""}">{v}</b>{"<span class=un>건</span>" if k == 3 else ""}</span><span class="l">{l}</span></div>' + ("<i>→</i>" if k < 3 else "")
                  for k, (v, l) in enumerate(zip(vals, LABELS)))
    dues = sorted(dleft(r["bid_clse_date"]) for r in res); wk = sum(1 for n, _ in dues if n <= 7); n0, d0 = dues[0]
    tabs = (f'<div class="tabs"><div><em>공고 {len(res)}</em><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span></div>'
            f'<div class="due">이번 주 마감 {wk}건 · 가장 빠른 마감 <span class="d {"hot" if n0 <= 7 else ""}">D-{n0}</span> ({d0.month}.{d0.day:02d})</div></div>')
    return f'<div class="chain"><div class="fun"><span class="k">걸러낸 경로</span>{fun}</div>{tabs}</div>'


def main_col(res, prof):
    trs = [trow(i, r, prof, i == 1) for i, r in enumerate(res, 1)]
    return (f'<div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span></div>'
            f'<div class="okline"><b>이메일 등록 완료</b> · 전체 결과 공개</div>{ZERO}'
            f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>'
            f'{"".join(trs[:5])}{gate(len(res))}<div class="fade">{"".join(trs[5:])}</div></div></div>')


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    c = dict(cfg(), CNT=[f["total"], f["industry"], f["qualified"], len(res)])
    n_ind = len(prof["industries"][0] + prof["industries"][1])
    body = (f'<div class="wrap">{nav()}'
            f'<div class="head"><h1>{esc(co["corp_nm"])}<small>{co["bizrno"][:6]}*****</small></h1>'
            f'<div class="meta"><span>{esc(co["rgn_nm"])}</span><span>등록업종 {n_ind}</span><span>공급물품 없음</span><span>기준일 {TODAY.isoformat()}</span></div></div>'
            f'<div class="stage">{labels(f, len(res))}{field(titles)}{chain(f, d, res)}</div>{ERR}'
            f'<div class="res"><div class="cols">{side(co, prof)}{main_col(res, prof)}</div></div>'
            f'<div class="foot">결과 페이지 최종 시안 — flow 의 머리 장면(계산 대기 가림막)·네 상태 + split 의 두 단 표형. 화면은 표, 메일·인쇄는 블록(report.html). '
            f'게이트는 5건 바로 뒤. 0건은 오른쪽 단만 비고 왼쪽 회사 정보가 이유. 숫자·공고명은 {TODAY.isoformat()} 실제 추천 결과(data/).</div></div>'
            f'<div class="ctl"><span data-run="full">처음 방문</span><span data-run="fast">재방문</span><span data-run="still">움직임 줄이기</span><i></i>'
            f'<span data-st="zero">0건</span><span data-st="err">오류·지연</span><span data-st="email">이메일 뒤</span><span data-st="reviewed">검토 뒤</span></div>'
            f'<script type="application/json" id="cfg">{json.dumps(c)}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 결과</title>{FONT}'
            f'<style>{CSS}</style></head><body>{body}<script>{JS}{JS_EXTRA}</script></body></html>')


BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요"]   # README 표현 결정(2026-10-15/16)


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in CSS
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        txt = pg.evaluate("document.body.innerText")
        bad = [w for w in BANNED if w in txt]; assert not bad, bad
        pg.click(".stage"); pg.wait_for_timeout(1000)   # 건너뛰기 → done (.res 페이드 .5s + .2s 지연)
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e); return { done: document.body.classList.contains('done'), tr: document.querySelectorAll('.sheet .tr').length,
            sticky: cs(document.querySelector('.side')).position, labs: document.querySelectorAll('.chain .l').length, nums: [...document.querySelectorAll('.chain b')].map(e => e.textContent),
            acc: cs(document.querySelector('.chain b.acc')).color, res: cs(document.querySelector('.res')).opacity } }""")
        assert s["done"] and s["tr"] == 12 and s["sticky"] == "sticky" and s["labs"] == 4 and s["nums"] == ["9,374", "835", "372", "12"] and s["acc"] == "rgb(249, 115, 22)" and s["res"] == "1", s
        pg.screenshot(path=str(out / "_shot_final_default.png"), full_page=True)
        for st in ["zero", "err", "email", "reviewed"]:
            pg.click(f'.ctl [data-st="{st}"]'); pg.wait_for_timeout(300)
            if st == "zero": pg.click(".stage"); pg.wait_for_timeout(700)      # 건너뛰기 → done
            if st == "err": pg.wait_for_timeout(5500)                          # 건너뛰기는 오류 연출을 취소한다(settle → done). 3.6초 진행 + 1.2초 정지 대기
            v = pg.evaluate("""() => { const cs = e => getComputedStyle(e), vis = s => { const e = document.querySelector(s); return e && cs(e).display !== 'none' && cs(e).opacity !== '0' }; return {
                nums: [...document.querySelectorAll('.chain b')].map(e => e.textContent), zero: vis('.zero'), sheet: vis('.sheet'), err: vis('.err'), side: vis('.side'),
                res: cs(document.querySelector('.res')).opacity, gate: vis('.gateline'), ok: vis('.okline'), rvd: document.querySelectorAll('.tr.rvd').length, rvn: document.querySelectorAll('.rvn').length } }""")
            if st == "zero": assert v["nums"][2:] == ["0", "0"] and v["zero"] and not v["sheet"] and v["side"] and v["res"] == "1", v
            if st == "err": assert v["err"] and v["res"] == "0", v
            if st == "email": assert v["ok"] and not v["gate"] and v["sheet"], v
            if st == "reviewed": assert v["rvd"] == 1 and v["rvn"] == 1, v
            pg.screenshot(path=str(out / f"_shot_final_{st}.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.click(".stage"); pg.wait_for_timeout(700)
        m = pg.evaluate("""() => ({ open: document.querySelector('details.side').open, cols: getComputedStyle(document.querySelector('.cols')).gridTemplateColumns.split(' ').length,
            overflow: document.documentElement.scrollWidth > 390, no: getComputedStyle(document.querySelector('.sheet .tr .no')).display })""")
        assert m["open"] is False and m["cols"] == 1 and not m["overflow"] and m["no"] == "none", m
        pg.screenshot(path=str(out / "_shot_final_390.png"), full_page=True)
        b.close()
    print("ok rows=12, states zero/err/email/reviewed, 390 one column; banned words 0")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    from jobs.evaluate_recommender import connect, fetch_company_profile
    src, fsrc, tsrc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src, encoding="utf-8")); fn = json.load(open(fsrc))
    tt = {k: [esc(x.strip()) for x in v] for k, v in json.load(open(tsrc, encoding="utf-8")).items()}
    prof = fetch_company_profile(connect(), "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, fn, tt))
    print("written", out)

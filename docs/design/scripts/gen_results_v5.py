"""결과 페이지 — 깔때기 디벨롭 (2026-10-15 결정: 깔때기 머리로 간다).
- 회사 카드 제거 → 깔때기 2·3단계가 '걸러낸 기준' 자체. 단계를 누르면 기준(등록업종 / 지역·면허·규모)이 펼쳐지고 거기서 수정 요청.
- 숫자 아래 9,285→12 로 좁아지는 띠(SVG) — 흐름을 한 번에.
- 상태: 비로그인(5건 게이트) / 로그인(전부 + 새로 N + 검토함).
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_results_v5.py <sample.json> <funnel.json> ../docs/design/prototypes/results-funnel-v2.html
"""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, dleft  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import table, nav, JS as JS4  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

CSS = r"""
.nav { padding:22px 0 }
.reveal { opacity:0; transform:translateY(10px); transition:opacity .6s ease var(--d,0s), transform .6s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .in .reveal { opacity:1; transform:none }
@media (prefers-reduced-motion: reduce) { .reveal, .fun .bar i, .rib path { transition:none !important; animation:none !important; opacity:1 !important; transform:none !important } }
.fh { padding:26px 0 6px } .fh .co { font-size:14px; color:#55554f; display:flex; align-items:baseline; gap:10px } .fh .co b { color:#141414; font-size:17px; font-weight:650; letter-spacing:-0.01em } .fh .co .sp { flex:1 } .fh .co .new { color:#e8431b; font-weight:600 }
.fun { display:grid; grid-template-columns:1.5fr 1fr 1fr 1.1fr; margin-top:18px; border-top:1px solid #141414 }
.fun > div { padding:20px 20px 18px 0; position:relative; cursor:default } .fun > div.step { cursor:pointer } .fun > div + div { border-left:1px solid #e6e4df; padding-left:22px }
.fun .k { display:block } .fun .n { margin-top:8px; font-size:50px; letter-spacing:-0.045em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums } .fun .n small { font-size:14px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:8px }
.fun .last .n { color:#e8431b } .fun .why { margin-top:8px; font-size:13px; color:#55554f; line-height:1.5; max-width:260px }
.fun .step .why u { text-decoration:none; border-bottom:1px solid #d8d6d0; color:#141414 } .fun .step:hover .why u { border-color:#141414 }
.fun .step.open { background:#faf9f6; margin-left:-22px; padding-left:22px; border-radius:6px 6px 0 0 } .fun .step.open + div { border-left-color:transparent }
.rib { height:54px; margin-top:-2px } .rib svg { width:100%; height:100%; display:block; overflow:visible }
.rib path { fill:#f1f0ec } .rib path.on { fill:#141414; opacity:.08 } .rib path.last { fill:#e8431b; opacity:.9 }
.crit { display:none; border-top:1px solid #141414; border-bottom:1px solid #e6e4df; padding:18px 0 16px; grid-template-columns:1.2fr 1fr auto; gap:28px; align-items:start } .crit.open { display:grid }
.crit .k { display:block; margin-bottom:8px } .crit .txt { font-size:13.5px; line-height:1.75; color:#333 } .crit .txt b { font-weight:600 } .crit .txt .dim { color:#8f8f8b }
.crit .act { display:flex; flex-direction:column; gap:8px; align-items:flex-end } .crit .act .mute { font-size:11.5px }
.crit li { list-style:none; padding:3px 0; font-size:13.5px } .crit ul { margin:0; padding:0 }
.count { padding:22px 0 10px } .count .f { font-size:13px; color:#6b6b67 } .count .f b { color:#141414; font-weight:600; border-bottom:1px solid #141414; padding-bottom:2px } .count .f span + span { margin-left:16px }
.sw { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:50; display:flex; gap:4px; padding:6px 8px; background:#141414; color:#c9c9c4; border-radius:999px; box-shadow:0 20px 40px -20px rgba(0,0,0,.6); font-size:12.5px } .sw span { padding:6px 11px; border-radius:999px; cursor:pointer } .sw span.on { background:#fff; color:#141414; font-weight:600 }
.vs { display:none } .vs.on { display:block }
"""

JS = JS4 + r"""
document.querySelectorAll('.fun .step').forEach(s=>s.addEventListener('click',()=>{const k=s.dataset.k; const wasOpen=s.classList.contains('open');
  document.querySelectorAll('.fun .step').forEach(x=>x.classList.remove('open')); document.querySelectorAll('.crit').forEach(c=>c.classList.remove('open'));
  if(!wasOpen){ s.classList.add('open'); document.querySelector('.crit[data-k="'+k+'"]').classList.add('open'); }}));
document.querySelectorAll('[data-ss]').forEach(e=>e.onclick=()=>{document.querySelectorAll('[data-ss]').forEach(x=>x.classList.toggle('on',x===e)); document.querySelectorAll('.vs').forEach(v=>v.classList.toggle('on',v.dataset.s===e.dataset.ss));});
"""


def ribbon(vals):
    """9,285 → 12 띠. 높이는 log 스케일, 4개 구간 폭은 깔때기 컬럼과 맞춤(1.5:1:1:1.1)."""
    w = [1.5, 1, 1, 1.1]; tot = sum(w); xs = [0]
    for ww in w: xs.append(xs[-1] + ww / tot * 100)
    h = lambda v: 6 + 42 * (math.log10(max(v, 1)) / math.log10(vals[0]))  # noqa: E731
    pts_top = []; pts_bot = []
    for i, v in enumerate(vals):
        hh = h(v); x0, x1 = xs[i], xs[i + 1]
        pts_top += [(x0, 27 - hh / 2), (x1 - 0.5, 27 - hh / 2)]; pts_bot += [(x0, 27 + hh / 2), (x1 - 0.5, 27 + hh / 2)]
    d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts_top[:6]) + " L " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in reversed(pts_bot[:6])) + " Z"
    hh = h(vals[3]); dl = f"M {xs[3]:.2f},{27 - hh / 2:.2f} L 99.5,{27 - hh / 2:.2f} L 99.5,{27 + hh / 2:.2f} L {xs[3]:.2f},{27 + hh / 2:.2f} Z"
    return f'<div class="rib"><svg viewBox="0 0 100 54" preserveAspectRatio="none"><path d="{d}"/><path class="last" d="{dl}"/></svg></div>'


def head(co, prof, f, n_res, login):
    inds = prof["industries"][0] + prof["industries"][1]; rep = prof["industries"][0]
    steps = [("오늘 올라온 공고", f["total"], "나라장터 전체, 마감 90일 이내", None),
             ("업종이 맞는 공고", f["industry"], f'등록업종 {len(inds)}개 중 하나 허용<br><u>기준 보기</u>', "ind"),
             ("자격이 되는 공고", f["qualified"], "면허·지역 제한 통과<br><u>기준 보기</u>", "qual"),
             ("검토할 공고", n_res, "회사 설명·이력과 가장 가까운 순", None)]
    cells = "".join(
        f'<div class="{"last" if i == 3 else ""}{" step" if k else ""}" {f"data-k={k}" if k else ""}><span class="k">{lab}</span><div class="n"><span class="cnt" data-to="{v}" data-d="{i * 0.25:.2f}">0</span><small>건</small></div><div class="why">{w}</div></div>'
        for i, (lab, v, w, k) in enumerate(steps))
    ind_txt = ", ".join(esc(x.split("(")[0]) for x in inds[:10]) + (f' <span class="dim">외 {len(inds) - 10}</span>' if len(inds) > 10 else "")
    crit_ind = (f'<div class="crit" data-k="ind"><div><span class="k">등록업종 {len(inds)} · 대표 {esc(rep[0].split("(")[0]) if rep else "-"}</span><div class="txt">{ind_txt}</div></div>'
                f'<div><span class="k">공급물품</span><div class="txt"><span class="dim">등록 없음</span> — 물품 공고를 받으려면 추가가 필요합니다</div></div>'
                f'<div class="act"><a class="bt dark" href="#">맞아요</a><a class="bt txt" href="#"><u>업종·물품 수정 요청</u></a><span class="mute">나라장터 업체정보 · 10.14 갱신 · 수정은 내 화면에 바로, 공유 반영은 확인 뒤</span></div></div>')
    crit_qual = (f'<div class="crit" data-k="qual"><div><span class="k">지역</span><div class="txt">본사 <b>{esc(co["rgn_nm"])}</b> · 지역 제한 공고는 경상남도 기준으로 통과 여부 판정</div>'
                 f'<span class="k" style="margin-top:12px">면허</span><div class="txt">공고가 요구하는 면허 그룹마다 위 등록업종 중 하나가 들어가면 통과</div></div>'
                 f'<div><span class="k">규모</span><div class="txt"><span class="dim">미입력</span> — 소기업·중소기업 제한 공고 판정에 쓰입니다<br><span class="dim">제재</span> 없음 · <span class="dim">사업자 상태</span> 계속사업자</div></div>'
                 f'<div class="act"><a class="bt dark" href="#">맞아요</a><a class="bt txt" href="#"><u>지역·규모 수정 요청</u></a></div></div>')
    co_line = (f'<div class="co reveal"><b>{esc(co["corp_nm"])}</b><span>{esc(co["rgn_nm"])}</span>'
               + (f'<span class="sp"></span><span class="new">어제 이후 새로 3건</span><span>검토함 3</span>' if login else '<span class="sp"></span><span class="dim">처음 오셨나요? 아래 기준이 맞는지 한 번만 확인해 주세요</span>') + '</div>')
    return f'<div class="fh">{co_line}<div class="fun">{cells}</div>{ribbon([f["total"], f["industry"], f["qualified"], n_res])}{crit_ind}{crit_qual}</div>'


def page(d, prof, f):
    res, co = d["results"], d["company"]
    vs = ""
    for state in ("guest", "login"):
        login = state == "login"
        tb = table(res, prof) if not login else table(res, prof).replace('<div class="fade">', '<div>').split('<div class="gateline">')[0]
        count = (f'<div class="count"><div class="f"><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span>'
                 f'<span class="mute">|</span><span>이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span>적합 순</span></div></div>')
        vs += f'<div class="vs {"on" if not login else ""}" data-s="{state}">{head(co, prof, f, len(res), login)}{count}{tb}</div>'
    body = (f'<div class="wrap">{nav()}{vs}<div class="foot">깔때기 v2 — 회사 카드를 단계 안으로. 숫자·공고명은 2026-10-15 실제 추천 결과, 깔때기 숫자는 실제 집계.</div></div>'
            f'<div class="sw"><span class="on" data-ss="guest">비로그인</span><span data-ss="login">로그인</span></div>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 결과 — 깔때기 v2</title>{FONT}<style>{SHEET_CSS}{CSS}</style></head><body>{body}<script>{JS}</script></body></html>'


if __name__ == "__main__":
    src, fsrc, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc))
    conn = connect(); prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, f)); print("written", out)

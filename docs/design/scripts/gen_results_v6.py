"""결과 페이지 — 깔때기 v3 + 게이트 B안 (2026-10-15 결정).
게이트 B: 분량은 다 보여주고 '가치'만 가둔다.
  - 1건은 완전 공개(근거·자격·진행까지 펼친 상태)
  - 나머지 11건은 제목만 흐리게, 순위 번호·근거·마감·금액·적합은 가림(■ 처리)
  - "순서와 근거는 이메일 하나로" 한 줄 게이트
깔때기 손질: 12건이 주인공(크기 차등), 띠는 곡선 한 줄, 숫자 사이 가는 연결선.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_results_v6.py <sample.json> <funnel.json> ../docs/design/prototypes/results-gate-b.html
"""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, won, dleft  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS, why_lines, qual_lines  # noqa: E402
from gen_results_v4 import nav, JS as JS4  # noqa: E402
from gen_results_v2 import strongest  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

CSS = r"""
.tr .fit i { margin-right:0 }
.nav { padding:22px 0 }
.reveal { opacity:0; transform:translateY(10px); transition:opacity .6s ease var(--d,0s), transform .6s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .in .reveal { opacity:1; transform:none }
@media (prefers-reduced-motion: reduce) { .reveal, .rib path { transition:none !important; opacity:1 !important; transform:none !important } }
.fh { padding:26px 0 0 } .fh .co { font-size:14px; color:#55554f; display:flex; align-items:baseline; gap:10px } .fh .co b { color:#141414; font-size:17px; font-weight:650; letter-spacing:-0.01em } .fh .co .sp { flex:1 } .fh .co .new { color:#e8431b; font-weight:600 }
/* 깔때기 — 마지막 칸이 주인공 */
.fun { display:grid; grid-template-columns:1fr 1fr 1fr 1.5fr; margin-top:20px; border-top:1px solid #141414; align-items:end }
.fun > div { padding:18px 18px 16px 0; position:relative } .fun > div + div { padding-left:20px } .fun > div.step { cursor:pointer }
.fun .k { display:block } .fun .n { margin-top:6px; font-size:30px; letter-spacing:-0.035em; font-weight:600; line-height:1; font-variant-numeric:tabular-nums; color:#55554f }
.fun .n small { font-size:12.5px; color:#8f8f8b; font-weight:450; letter-spacing:0; margin-left:5px }
.fun .last { padding-left:26px; border-left:1px solid #141414 } .fun .last .n { font-size:72px; letter-spacing:-0.05em; font-weight:700; color:#e8431b } .fun .last .n small { font-size:16px; color:#6b6b67 }
.fun .why { margin-top:7px; font-size:12.5px; color:#6b6b67; line-height:1.5; max-width:230px } .fun .last .why { font-size:13.5px; color:#55554f; max-width:320px }
.fun .step .why u { text-decoration:none; border-bottom:1px solid #d8d6d0; color:#141414 } .fun .step:hover .why u { border-color:#141414 }
.fun .step.open { background:#faf9f6; border-radius:6px 6px 0 0 }
.fun .arw { position:absolute; right:8px; bottom:22px; color:#c9c9c4; font-size:13px }
.rib { height:26px; margin-top:0 } .rib svg { width:100%; height:100%; display:block } .rib path { fill:none; stroke:#141414; stroke-width:1; opacity:.25 } .rib path.acc { stroke:#e8431b; opacity:1; stroke-width:1.5 }
.count { padding:20px 0 10px } .count .f { font-size:13px; color:#6b6b67 } .count .f b { color:#141414; font-weight:600; border-bottom:1px solid #141414; padding-bottom:2px } .count .f span + span { margin-left:16px }
/* 게이트 B — 분량은 보이고 가치는 가림 */
.lead { border-top:1px solid #141414; padding:0 }
.lead .tr { background:#faf9f6; margin:0 -14px; padding:15px 14px; border-radius:6px 6px 0 0; border-bottom:0 }
.lead .x { background:#faf9f6; margin:0 -14px; padding:18px 14px 22px 52px; border-radius:0 0 6px 6px; border-bottom:0 }
.lead .tag1 { display:inline-block; margin-bottom:8px; font-size:11px; letter-spacing:.06em; font-weight:600; color:#e8431b }
.locked .tr { cursor:default } .locked .tr .t { color:#8f8f8b; filter:blur(0.35px) }
.locked .tr span:not(.t) { color:transparent !important; position:relative }
.locked .tr span:not(.t) > * { visibility:hidden }
.locked .tr span:not(.t)::after { content:""; position:absolute; left:0; right:0; top:50%; transform:translateY(-50%); height:9px; background:#ececea; border-radius:2px }
.locked .tr .r::after { left:auto; width:58px; right:0 }
.locked .tr .no::after { width:18px } .locked .tr .fit::after { width:44px }
.gate2 { display:flex; align-items:center; gap:16px; padding:20px 0 22px; border-top:1px solid #141414; margin-top:-1px }
.gate2 b { font-size:15.5px; font-weight:650; letter-spacing:-0.01em } .gate2 .dim { font-size:13px } .gate2 .sp { flex:1 }
.gate2 .in { display:flex; gap:6px } .gate2 .in span:first-child { width:280px; height:38px; border:1px solid #e3e1dc; border-radius:8px; display:flex; align-items:center; padding:0 12px; color:#8f8f8b; font-size:13px }
.sw { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:50; display:flex; gap:4px; padding:6px 8px; background:#141414; color:#c9c9c4; border-radius:999px; box-shadow:0 20px 40px -20px rgba(0,0,0,.6); font-size:12.5px } .sw span { padding:6px 11px; border-radius:999px; cursor:pointer } .sw span.on { background:#fff; color:#141414; font-weight:600 }
.vs { display:none } .vs.on { display:block }
"""

JS = JS4 + r"""
document.querySelectorAll('.fun .step').forEach(s=>s.addEventListener('click',()=>{const k=s.dataset.k, was=s.classList.contains('open');
  const root=s.closest('.vs'); root.querySelectorAll('.fun .step').forEach(x=>x.classList.remove('open')); root.querySelectorAll('.crit').forEach(c=>c.classList.remove('open'));
  if(!was){ s.classList.add('open'); root.querySelector('.crit[data-k="'+k+'"]').classList.add('open'); }}));
document.querySelectorAll('[data-ss]').forEach(e=>e.onclick=()=>{document.querySelectorAll('[data-ss]').forEach(x=>x.classList.toggle('on',x===e)); document.querySelectorAll('.vs').forEach(v=>v.classList.toggle('on',v.dataset.s===e.dataset.ss));});
"""


def ribbon(vals):
    """숫자 사이를 잇는 가는 곡선 한 줄. 마지막 구간만 인주색."""
    w = [1, 1, 1, 1.5]; tot = sum(w); xs = [0.0]
    for ww in w:
        xs.append(xs[-1] + ww / tot * 100)
    cx = [(xs[i] + xs[i + 1]) / 2 for i in range(4)]
    y = lambda v: 24 - 20 * (math.log10(max(v, 1)) / math.log10(vals[0]))  # noqa: E731
    seg = []
    for i in range(3):
        x0, y0, x1, y1 = cx[i], y(vals[i]), cx[i + 1], y(vals[i + 1])
        mx = (x0 + x1) / 2
        seg.append((f'<path class="{"acc" if i == 2 else ""}" d="M {x0:.2f},{y0:.2f} C {mx:.2f},{y0:.2f} {mx:.2f},{y1:.2f} {x1:.2f},{y1:.2f}"/>'))
    return f'<div class="rib"><svg viewBox="0 0 100 26" preserveAspectRatio="none">{"".join(seg)}</svg></div>'


def head(co, prof, f, n_res, login):
    inds = prof["industries"][0] + prof["industries"][1]
    rep = prof["industries"][0]
    steps = [("지금 입찰 가능한 공고", f["total"], "나라장터 전체, 마감 90일 이내", None),
             ("업종이 맞는 공고", f["industry"], f"등록업종 {len(inds)}개 중 하나 허용", None),
             ("자격이 되는 공고", f["qualified"], "면허·지역 제한 통과", None),
             ("검토할 공고", n_res, "회사 설명과 과거 수주 이력에 가장 가까운 순서", None)]
    cells = "".join(
        f'<div class="{"last" if i == 3 else ""}">'
        f'<span class="k">{lab}</span><div class="n"><span class="cnt" data-to="{v}" data-d="{i * 0.22:.2f}">0</span><small>건</small></div>'
        f'<div class="why">{w}</div>{"" if i == 3 else "<span class=arw>→</span>"}</div>'
        for i, (lab, v, w, k) in enumerate(steps))
    co_line = (f'<div class="co reveal"><b>{esc(co["corp_nm"])}</b><span>{esc(co["rgn_nm"])}</span>'
               + (f'<span class="sp"></span><span class="new">어제 이후 신규 3건</span><span>검토함 3</span>' if login
                  else '<span class="sp"></span><span class="dim">걸러낸 기준 확인 필요</span>') + '</div>')
    return f'<div class="fh">{co_line}<div class="fun">{cells}</div>{ribbon([f["total"], f["industry"], f["qualified"], n_res])}{crit(co, prof)}</div>'


# 걸러낸 기준은 눌러야 보이면 아무도 안 본다 — 제품의 주장이므로 항상 펼쳐 둔다(2026-10-15 승우님). flow.html(gen_flow.py)도 같이 쓴다.
CRIT_CSS = r"""
.crit { display:grid; border-top:1px solid #141414; border-bottom:1px solid #e6e4df; padding:16px 0 14px; grid-template-columns:1.35fr 1fr 1fr auto; gap:26px; align-items:start }
.crit .k { display:block; margin-bottom:6px } .crit .txt { font-size:13px; line-height:1.7; color:#333 } .crit .txt b { font-weight:600 } .crit .txt .dim { color:#737370 }
.crit .k + .k { margin-top:10px }
.crit .act { display:flex; flex-direction:column; gap:8px; align-items:flex-end } .crit .act .mute { font-size:11.5px }
@media (max-width:900px){ .crit { grid-template-columns:1fr 1fr; gap:18px } .crit .act { grid-column:1/-1; flex-direction:row; align-items:center; justify-content:flex-start } }
"""


def crit(co, prof):
    """걸러낸 기준 띠 — 등록업종·공급물품 / 지역·면허 / 규모·상태 / 확인·수정 요청. 공문 톤(2026-10-16)."""
    inds = prof["industries"][0] + prof["industries"][1]
    rep = prof["industries"][0]
    ind_txt = ", ".join(esc(x.split("(")[0]) for x in inds[:5]) + (f' <span class="dim">외 {len(inds) - 5}</span>' if len(inds) > 5 else "")
    return (f'<div class="crit"><div><span class="k">등록업종 {len(inds)} · 대표 {esc(rep[0].split("(")[0]) if rep else "-"}</span><div class="txt">{ind_txt}</div>'
            f'<span class="k">공급물품</span><div class="txt"><span class="dim">등록 없음</span> — 물품 공고 추천에는 등록 필요</div></div>'
            f'<div><span class="k">지역</span><div class="txt">본사 <b>{esc(co["rgn_nm"])}</b> · 지역 제한 공고 판정 기준</div>'
            f'<span class="k">면허</span><div class="txt">공고 요구 면허 그룹마다 등록업종 중 하나 포함 시 통과</div></div>'
            f'<div><span class="k">규모</span><div class="txt"><span class="dim">미입력</span> — 소기업·중소기업 제한 공고 판정 기준</div>'
            f'<span class="k">사업자 상태</span><div class="txt">계속사업자 · 제재 없음</div></div>'
            f'<div class="act"><a class="bt dark" href="#">확인</a><a class="bt txt" href="#"><u>수정 요청</u></a><span class="mute">나라장터 업체정보 · 10.14 갱신</span></div></div>')


def row(i, r, locked=False):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    s = strongest(r)
    n, dd = dleft(r["bid_clse_date"])
    return (f'<div class="tr"><span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="org">{esc(org)}</span>'
            f'<span class="why">{esc(s["label"]) if s else ""}</span><span class="r d {"hot" if n <= 7 and not locked else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
            f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r fit"><i><b style="width:{round(float(r["score"]) * 100)}%"></b></i></span></div>')


def detail(r, prof):
    org = r.get("dmnd_instt_nm") or ""
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r, prof))
    wl = "".join(f"<li>{w}</li>" for w in why_lines(r, org))
    return (f'<div class="x"><div><span class="k">참가 자격</span><ul>{ql}</ul></div><div><span class="k">추천 근거</span><ul>{wl}</ul></div>'
            f'<div><span class="k">진행</span><div class="life"><span class="on">사전규격</span><span class="on">공고</span><span>입찰</span><span>개찰</span><span>낙찰</span><span>계약</span></div>'
            f'<div class="acts"><a class="bt dark" href="{esc(r["bid_ntce_url"])}">나라장터 원문</a><a class="bt" href="#">검토</a></div></div></div>')


def body_table(res, prof, login):
    th = ('<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>')
    if login:
        rows = [row(i, r) for i, r in enumerate(res, 1)]
        return th + rows[0] + detail(res[0], prof) + "".join(rows[1:])
    lead = (f'<div class="lead"><span class="tag1">오늘의 한 건 — 근거까지 공개</span>{row(1, res[0])}{detail(res[0], prof)}</div>')
    locked = '<div class="locked">' + "".join(row(i, r, locked=True) for i, r in enumerate(res[1:], 2)) + "</div>"
    gate = (f'<div class="gate2"><div><b>나머지 {len(res) - 1}건의 순서와 근거는 이메일 하나로.</b><br>'
            f'<span class="dim">공고 제목은 지금도 보입니다. 어느 것이 먼저이고 왜 남았는지, 마감과 추정가는 메일 주소를 넣으면 바로 열립니다. 비밀번호 없음.</span></div>'
            f'<span class="sp"></span><span class="in"><span>you@company.co.kr</span><span class="bt dark">순서·근거 보기</span></span></div>')
    return th + lead + locked + gate


def page(d, prof, f):
    res, co = d["results"], d["company"]
    vs = ""
    for state in ("guest", "login"):
        login = state == "login"
        count = (f'<div class="count"><div class="f"><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span>'
                 f'<span class="mute">|</span><span>이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span>적합 순</span></div></div>')
        vs += (f'<div class="vs {"on" if not login else ""}" data-s="{state}">{head(co, prof, f, len(res), login)}{count}{body_table(res, prof, login)}</div>')
    body = (f'<div class="wrap">{nav()}{vs}<div class="foot">게이트 B — 분량은 전부 보이고 순서·근거·마감만 가립니다. 숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>'
            f'<div class="sw"><span class="on" data-ss="guest">비로그인</span><span data-ss="login">로그인</span></div>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 결과 — 게이트 B</title>{FONT}<style>{SHEET_CSS}{CSS}{CRIT_CSS}</style></head><body>{body}<script>{JS}</script></body></html>'


if __name__ == "__main__":
    src, fsrc, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(src, encoding="utf-8"))
    f = json.load(open(fsrc))
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, f))
    print("written", out)

"""결과 페이지 머리 3안 — 표(시트)는 같고 머리만 다름. 임팩트는 '이 제품만 보여줄 수 있는 것' 하나를 크게.
  funnel  : 오늘 9,285건 → 업종 통로 831 → 자격 385 → 남은 12. 숫자 카운트업 + 단계 선.
  timeline: 마감일 축(이번 주/다음 주/그 뒤)에 12건이 점으로 찍힘.
  block   : 회사명 거대 타이포 + '남은 12건' 인주 블록.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_results_v4.py <sample.json> <funnel.json> ../docs/design/prototypes/
"""
import json
import sys
from datetime import date, timedelta

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, won, dleft  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS, why_lines, qual_lines, strongest  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

TODAY = date(2026, 10, 15)

COMMON = r"""
.nav { padding:22px 0 }
.motion .cnt { display:inline-block; min-width:1ch }
@media (prefers-reduced-motion: reduce) { .reveal { transition:none !important; opacity:1 !important; transform:none !important } }
.reveal { opacity:0; transform:translateY(10px); transition:opacity .6s ease var(--d,0s), transform .6s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .in .reveal { opacity:1; transform:none }
"""

FUNNEL_CSS = COMMON + r"""
.fh { padding:30px 0 10px } .fh .co { font-size:14px; color:#55554f } .fh .co b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.fun { display:grid; grid-template-columns:1.6fr 1fr 1fr 1.1fr; gap:0; margin-top:22px; border-top:1px solid #141414 }
.fun > div { padding:22px 20px 24px 0; position:relative } .fun > div + div { border-left:1px solid #e6e4df; padding-left:22px }
.fun .k { display:block } .fun .n { margin-top:10px; font-size:52px; letter-spacing:-0.045em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums } .fun .n small { font-size:15px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:8px }
.fun .last .n { color:#e8431b } .fun .why { margin-top:10px; font-size:13px; color:#55554f; line-height:1.55; max-width:260px }
.fun .bar { position:absolute; left:0; right:0; bottom:0; height:3px; background:#ececea } .fun .bar i { display:block; height:100%; background:#141414; width:0; transition:width 1.1s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .in .fun .bar i { width:var(--w) } .fun .last .bar i { background:#e8431b }
.fh .act { margin-top:14px; display:flex; gap:14px; align-items:center; font-size:13px; color:#55554f } .fh .act u { text-decoration:none; border-bottom:1px solid #d8d6d0; color:#141414 }
"""

TIMELINE_CSS = COMMON + r"""
.th2 { padding:30px 0 0 } .th2 .co { font-size:14px; color:#55554f } .th2 .co b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.tl { margin-top:22px; border-top:1px solid #141414; padding-top:18px }
.tl .lab { display:flex; justify-content:space-between; font-size:11px; letter-spacing:.06em; color:#737370; font-weight:600 }
.tl .axis { position:relative; height:120px; margin-top:8px; border-bottom:1px solid #e6e4df }
.tl .wk { position:absolute; top:0; bottom:0; border-left:1px dashed #e6e4df } .tl .wk span { position:absolute; top:-2px; left:6px; font-size:11px; color:#737370 }
.tl .dot { position:absolute; width:12px; height:12px; border-radius:50%; background:#141414; transform:translate(-50%,-50%); transition:transform .5s cubic-bezier(.2,.7,.2,1) var(--d,0s), opacity .5s ease var(--d,0s); opacity:0; cursor:pointer } .in .tl .dot { opacity:1 } .tl .dot.hot { background:#e8431b } .tl .dot:hover { transform:translate(-50%,-50%) scale(1.35) }
.tl .dot b { position:absolute; left:16px; top:-6px; font-size:12px; font-weight:550; white-space:nowrap; color:#141414; background:rgba(255,255,255,.9); padding:1px 4px; border-radius:3px }
.tl .sum { display:flex; gap:28px; margin-top:12px; font-size:13px; color:#55554f } .tl .sum b { font-size:22px; letter-spacing:-0.02em; font-weight:650; color:#141414; margin-right:6px } .tl .sum b.hot { color:#e8431b }
"""

BLOCK_CSS = COMMON + r"""
.bh { padding:26px 0 0 } .bh h1 { margin:0; font-size:clamp(48px, 7.2vw, 88px); letter-spacing:-0.05em; font-weight:700; line-height:.98; max-width:1120px } .bh h1 .dim { color:#c9c9c4; font-weight:450 }
.bh .row { display:grid; grid-template-columns:1fr 360px; gap:40px; align-items:end; margin-top:26px; padding-bottom:26px; border-bottom:1px solid #141414 }
.bh .meta { font-size:14px; line-height:1.75; color:#55554f; max-width:640px } .bh .meta b { color:#141414; font-weight:600 } .bh .meta .k { display:inline-block; margin-right:8px }
.blk { background:#e8431b; color:#fff; padding:22px 24px 20px; border-radius:6px } .blk .k { color:rgba(255,255,255,.75) } .blk .n { font-size:64px; letter-spacing:-0.05em; font-weight:700; line-height:1; margin-top:6px } .blk .n small { font-size:15px; font-weight:450; letter-spacing:0; margin-left:8px; color:rgba(255,255,255,.85) } .blk p { margin:12px 0 0; font-size:12.5px; color:rgba(255,255,255,.85); line-height:1.5 }
.bh .act { margin-top:12px; font-size:13px; color:#55554f } .bh .act u { text-decoration:none; border-bottom:1px solid #d8d6d0; color:#141414; margin-left:8px }
"""

JS = r"""
document.documentElement.classList.add('motion');
requestAnimationFrame(()=>requestAnimationFrame(()=>document.body.classList.add('in')));
document.querySelectorAll('.cnt').forEach(el=>{const to=+el.dataset.to; const d=+el.dataset.d||0; const t0=performance.now()+d*1000; const dur=1100;
  const tick=now=>{const p=Math.min(1,Math.max(0,(now-t0)/dur)); const e=1-Math.pow(1-p,3); el.textContent=Math.round(to*e).toLocaleString('ko-KR'); if(p<1) requestAnimationFrame(tick);}; requestAnimationFrame(tick);});
"""


def table(res, prof):
    rows = []
    for i, r in enumerate(res, 1):
        org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""; s = strongest(r); n, dd = dleft(r["bid_clse_date"])
        rows.append((f'<div class="tr"><span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="org">{esc(org)}</span>'
                     f'<span class="why">{esc(s["label"]) if s else ""}</span><span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
                     f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r fit"><i><b style="width:{round(float(r["score"]) * 100)}%"></b></i>{round(float(r["score"]) * 100)}</span></div>'))
    r0 = res[0]; org0 = r0.get("dmnd_instt_nm") or ""
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r0, prof)); wl = "".join(f"<li>{w}</li>" for w in why_lines(r0, org0))
    x = (f'<div class="x"><div><span class="k">낼 수 있나</span><ul>{ql}</ul></div><div><span class="k">왜 남았나</span><ul>{wl}</ul></div>'
         f'<div><span class="k">진행</span><div class="life"><span class="on">사전규격</span><span class="on">공고</span><span>입찰</span><span>개찰</span><span>낙찰</span><span>계약</span></div>'
         f'<div class="acts"><a class="bt dark" href="{esc(r0["bid_ntce_url"])}">나라장터 원문</a><a class="bt" href="#">검토 인장</a><a class="bt txt" href="#"><u>안 맞아요</u></a></div></div></div>')
    gate = (f'<div class="gateline"><b>나머지 {len(res) - 5}건은 이메일로.</b><span class="dim">처음 5건은 누구나, 전부는 이메일 하나로. 비밀번호 없음.</span><span class="sp"></span>'
            f'<span class="in"><span>you@company.co.kr</span><span class="bt dark">전부 보기</span></span></div>')
    return (f'<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>'
            f'{rows[0]}{x}{"".join(rows[1:5])}<div class="fade">{"".join(rows[5:])}</div>{gate}')


def nav():
    return '<div class="nav"><div class="brand"><i></i>조달핏</div><div class="links"><b>추천</b><span>검토함</span><span>개선 기록</span><span class="cta">이메일로 전부 보기</span></div></div>'


def head_funnel(co, prof, f, n_res):
    inds = prof["industries"][0] + prof["industries"][1]
    steps = [("오늘 올라온 공고", f["total"], "나라장터 전체, 마감 90일 이내", 1.0),
             ("업종이 맞는 공고", f["industry"], f"등록업종 {len(inds)}개 중 하나를 허용", f["industry"] / f["total"]),
             ("자격이 되는 공고", f["qualified"], "면허·지역 제한 통과", f["qualified"] / f["total"]),
             ("검토할 공고", n_res, "회사 설명·이력과 가장 가까운 순", n_res / f["total"])]
    cells = "".join(
        f'<div class="{"last" if i == 3 else ""}"><span class="k">{k}</span><div class="n"><span class="cnt" data-to="{v}" data-d="{i * 0.25:.2f}">0</span>{"<small>건</small>"}</div>'
        f'<div class="why">{w}</div><div class="bar"><i style="--w:{max(w2 * 100, 1.2):.1f}%;--d:{i * 0.25:.2f}s"></i></div></div>'
        for i, (k, v, w, w2) in enumerate(steps))
    return (f'<div class="fh"><div class="co reveal"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(inds)} · 공급물품 없음 · 규모 미입력</div>'
            f'<div class="fun">{cells}</div>'
            f'<div class="act reveal" style="--d:.9s">이 기준이 맞나요? <u>맞아요</u> <u>수정 요청</u> <span class="mute">나라장터 업체정보 · 10.14 갱신</span></div></div>')


def head_timeline(co, res):
    start = TODAY; span = 45
    dots = []
    for i, r in enumerate(res, 1):
        n, dd = dleft(r["bid_clse_date"]); x = min(max(n, 0), span) / span * 100; y = 22 + (i % 5) * 18
        dots.append(f'<div class="dot {"hot" if n <= 7 else ""}" style="left:{x:.1f}%;top:{y}px;--d:{0.1 + i * 0.06:.2f}s" title="{esc(r["bid_ntce_nm"])}">{f"<b>{esc(r[chr(98)+chr(105)+chr(100)+chr(95)+chr(110)+chr(116)+chr(99)+chr(101)+chr(95)+chr(110)+chr(109)][:18])}</b>" if i <= 3 else ""}</div>')
    wks = "".join(f'<div class="wk" style="left:{k * 7 / span * 100:.1f}%"><span>{(start + timedelta(days=k * 7)).month}.{(start + timedelta(days=k * 7)).day:02d}</span></div>' for k in range(0, 7))
    this_wk = sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7); next_wk = sum(1 for r in res if 7 < dleft(r["bid_clse_date"])[0] <= 14)
    return (f'<div class="th2"><div class="co reveal"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 오늘 9,285건 중 남은 {len(res)}건 · 자격 통과</div>'
            f'<div class="tl"><div class="lab"><span>오늘</span><span>마감까지 →</span><span>45일</span></div><div class="axis">{wks}{"".join(dots)}</div>'
            f'<div class="sum"><span><b class="hot">{this_wk}</b>이번 주 마감</span><span><b>{next_wk}</b>다음 주</span><span><b>{len(res) - this_wk - next_wk}</b>그 뒤</span><span class="dim" style="margin-left:auto">점을 누르면 아래 표에서 열립니다</span></div></div></div>')


def head_block(co, prof, n_res, f):
    inds = prof["industries"][0] + prof["industries"][1]
    return (f'<div class="bh"><h1 class="reveal">{esc(co["corp_nm"].replace(" 주식회사", ""))}<span class="dim">에 남은 공고</span></h1>'
            f'<div class="row"><div class="meta reveal" style="--d:.15s"><span class="k">기준</span>{esc(co["rgn_nm"])} · 등록업종 <b>{esc(inds[0].split("(")[0])}</b> 외 {len(inds) - 1} · 공급물품 없음 · 규모 미입력<br>'
            f'오늘 공고 <b>{f["total"]:,}건</b> 중 업종이 맞는 {f["industry"]}건, 자격이 되는 {f["qualified"]}건을 거쳐 남았습니다.<div class="act">이 기준이 맞나요? <u>맞아요</u><u>수정 요청</u></div></div>'
            f'<div class="blk reveal" style="--d:.3s"><span class="k">검토할 공고</span><div class="n"><span class="cnt" data-to="{n_res}" data-d="0.3">0</span><small>건</small></div><p>이번 주 마감 3 · 새로 3 · 적합 순</p></div></div></div>')


def page(title, css, head, body_table):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title>{FONT}<style>{SHEET_CSS}{css}</style></head>'
            f'<body><div class="wrap">{nav()}{head}{body_table}<div class="foot">숫자·공고명은 2026-10-15 실제 추천 결과. 깔때기 숫자는 실제 집계.</div></div><script>{JS}</script></body></html>')


if __name__ == "__main__":
    src, fsrc, outdir = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/\\")
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc))
    conn = connect(); prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    res, co = d["results"], d["company"]; tb = table(res, prof)
    for name, title, css, head in (("results-funnel.html", "조달핏 결과 — 깔때기", FUNNEL_CSS, head_funnel(co, prof, f, len(res))),
                                   ("results-timeline.html", "조달핏 결과 — 타임라인", TIMELINE_CSS, head_timeline(co, res)),
                                   ("results-block.html", "조달핏 결과 — 블록", BLOCK_CSS, head_block(co, prof, len(res), f))):
        open(f"{outdir}/{name}", "w", encoding="utf-8", newline="\n").write(page(title, css, head, tb)); print("written", name)

"""결과 페이지 시안 v3 — 같은 내용(회사 확인 → 남은 공고 → 펼침)을 두 생김새로. 상자·칩을 걷어내고 타이포·괘선·여백으로.
  sheet: 넓은 표. 괘선만, 큰 숫자, 근거는 회색 문장.
  brief: 좁은 단(760px), 항목 목록. 문서를 읽듯.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_results_v3.py <sample.json> ../docs/design/prototypes/
"""
import json
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, won, dleft  # noqa: E402
from gen_results_v2 import strongest  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

FONT = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
BASE = r"""
* { box-sizing:border-box } body { margin:0; background:#fff; color:#141414; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased }
a { color:inherit; text-decoration:none } .dim { color:#6b6b67 } .mute { color:#8f8f8b } .acc { color:#e8431b }
.nav { display:flex; align-items:center; justify-content:space-between; padding:22px 0; font-size:13px; color:#55554f } .brand { display:flex; align-items:center; gap:8px; color:#141414; font-weight:700; font-size:14.5px } .brand i { width:7px; height:7px; border-radius:50%; background:#e8431b; display:inline-block }
.nav .links { display:flex; gap:22px } .nav .links b { color:#141414; font-weight:600 } .nav .cta { border-bottom:1px solid #141414; color:#141414 }
.k { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#737370; font-weight:600 }
.ok::after { content:"✓"; color:#1f5f3a; font-weight:700; margin-left:6px } .warn::after { content:"!"; color:#e8431b; font-weight:700; margin-left:6px }
.bt { display:inline-flex; align-items:center; height:36px; padding:0 14px; border-radius:8px; border:1px solid #e3e1dc; font-size:13px; font-weight:600; background:#fff } .bt.dark { background:#141414; color:#fff; border-color:#141414 } .bt.txt { border:0; padding:0 4px; color:#55554f; font-weight:500 } .bt.txt u { text-decoration:none; border-bottom:1px solid #d8d6d0 }
"""


def why_lines(r, org):
    out = []
    for b in r["score_breakdown"]:
        k = b["key"]
        if k == "institution": out.append(f"{esc(org)}와 과거 거래 이력이 있다.")
        elif k == "region": out.append(f"공고의 지역 제한이 본사 소재지 {esc(b.get('rgn'))}와 맞는다.")
        elif k == "industry_tokens": out.append("등록업종 표현이 허용업종과 겹친다 — " + ", ".join(esc(m) for m in b.get("matched", [])[:3]) + ".")
        elif k == "budget": out.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배로 비슷한 체급이다.")
        elif k == "budget_mismatch": out.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배라 체급 차이가 크다.")
        elif k == "instt_closed": out.append(f"이 기관은 최근 낙찰의 {int(b.get('repeat_ratio', 0) * 100)}%를 같은 회사가 가져갔다.")
    vec = next((b for b in r["score_breakdown"] if b["key"] == "vector"), None)
    if vec: out.append(f"공고 내용과 회사 업종 설명의 {esc(vec['label'])}.")
    return out


def qual_lines(r, prof):
    allowed = [a.strip() for a in (r.get("bidprc_psbl_indstryty_nm") or "").split(",") if a.strip()]
    mine = set(prof["industries"][0] + prof["industries"][1])
    hit = [a for a in allowed if any(m.split("(")[0] in a or a.split("(")[0] in m for m in mine)]
    q = r.get("qualification") or {}
    if hit: lic = ("ok", f"면허 — 허용업종 {len(allowed)}개 중 {esc(hit[0].split('(')[0])}{' 외' if len(hit) > 1 else ''} 보유")
    elif "면허 제한 없음" in q.get("reasons", []): lic = ("ok", "면허 — 제한 없음")
    else: lic = ("warn", "면허 — 일치하는 등록업종을 찾지 못함, 회사 정보 확인")
    rgn = r.get("prtcpt_psbl_rgn_nm"); sido = (prof["rgn"] or "").split()[0] if prof["rgn"] else ""
    if rgn and sido and sido in rgn: rg = ("ok", f"지역 — {esc(rgn)} 제한, 본사 {esc(sido)}")
    elif not rgn: rg = ("ok", "지역 — 제한 없음")
    else: rg = ("warn", f"지역 — {esc(rgn)} 제한, 본사 {esc(sido)}")
    return [lic, rg, ("todo", "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력")]


# ---------- sheet ----------
SHEET_CSS = BASE + r"""
.wrap { width:1120px; margin:0 auto; padding:0 0 120px }
.head { padding:28px 0 22px; border-bottom:1px solid #141414 }
.head h1 { margin:0; font-size:30px; letter-spacing:-0.035em; font-weight:650; line-height:1.15 } .head h1 small { font-size:13px; color:#737370; font-weight:450; letter-spacing:0; margin-left:12px }
.head .meta { margin-top:8px; font-size:13.5px; color:#55554f } .head .meta span + span::before { content:"·"; margin:0 8px; color:#c9c9c4 }
.head .ind { margin-top:14px; font-size:13.5px; line-height:1.7; max-width:880px } .head .ind b { font-weight:600 } .head .ind .k { margin-right:10px }
.head .act { margin-top:14px; display:flex; align-items:center; gap:14px; font-size:13px; color:#55554f } .head .act .q { color:#e8431b; font-weight:600 }
.count { display:flex; align-items:flex-end; justify-content:space-between; padding:26px 0 14px }
.count .n { font-size:44px; letter-spacing:-0.04em; font-weight:650; line-height:1 } .count .n small { font-size:14px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:10px }
.count .f { display:flex; gap:20px; font-size:13px; color:#6b6b67 } .count .f b { color:#141414; font-weight:600; border-bottom:1px solid #141414; padding-bottom:2px }
.th, .tr { display:grid; grid-template-columns:36px minmax(0,1fr) 200px 180px 92px 88px 60px; gap:0 16px; align-items:baseline }
.th { padding:10px 0 8px; border-bottom:1px solid #141414; font-size:11px; letter-spacing:.06em; color:#737370; font-weight:600 }
.tr { padding:15px 0; border-bottom:1px solid #ececea; font-size:14px; cursor:pointer } .tr:hover .t { color:#e8431b }
.tr .no { font-size:12px; color:#8f8f8b } .tr .t { font-weight:550; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; letter-spacing:-0.01em }
.tr .org, .tr .why { font-size:13px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .tr .why { color:#6b6b67 }
.tr .r { text-align:right } .tr .d { font-weight:600 } .tr .d.hot { color:#e8431b } .tr .d small { color:#737370; font-weight:450; margin-left:6px }
.tr .fit { font-weight:600 } .tr .fit i { display:inline-block; width:26px; height:3px; background:#e6e4df; margin-right:8px; vertical-align:middle; position:relative } .tr .fit i b { position:absolute; left:0; top:0; height:100%; background:#141414 }
.x { padding:22px 0 26px 52px; border-bottom:1px solid #ececea; display:grid; grid-template-columns:1.1fr 1.2fr .8fr; gap:40px }
.x .k { display:block; margin-bottom:10px } .x ul { margin:0; padding:0; list-style:none } .x li { font-size:13.5px; line-height:1.65; padding:4px 0; color:#333 } .x li.todo { color:#737370 }
.x .life { display:flex; gap:0; margin-top:4px } .x .life span { flex:1; font-size:11.5px; color:#8f8f8b; padding-top:8px; border-top:2px solid #ececea } .x .life span.on { color:#141414; border-top-color:#141414 }
.x .acts { margin-top:18px; display:flex; gap:8px; flex-wrap:wrap }
.fade .tr { opacity:.32; filter:blur(1.5px); pointer-events:none }
.gateline { display:flex; align-items:center; gap:14px; padding:22px 0; border-bottom:1px solid #141414; font-size:14px } .gateline b { font-weight:650 } .gateline .sp { flex:1 } .gateline .in { display:flex; gap:6px } .gateline .in span:first-child { width:260px; height:36px; border:1px solid #e3e1dc; border-radius:8px; display:flex; align-items:center; padding:0 12px; color:#737370; font-size:13px }
.foot { margin-top:28px; font-size:12px; color:#737370 }
"""


def sheet(d, prof, row_db):
    res, co = d["results"], d["company"]
    emp, mnf, hq, status, restricted, hp = row_db
    inds = prof["industries"][0] + prof["industries"][1]
    ind_txt = " · ".join(esc(i.split("(")[0]) for i in inds[:7]) + (f' <span class="dim">외 {len(inds) - 7}</span>' if len(inds) > 7 else "")
    rows = []
    for i, r in enumerate(res, 1):
        org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""; s = strongest(r); n, dd = dleft(r["bid_clse_date"])
        rows.append((f'<div class="tr"><span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="org">{esc(org)}</span>'
                     f'<span class="why">{esc(s["label"]) if s else ""}</span><span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
                     f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r fit"><i><b style="width:{round(float(r["score"]) * 100)}%"></b></i>{round(float(r["score"]) * 100)}</span></div>'))
    r0 = res[0]; org0 = r0.get("dmnd_instt_nm") or r0.get("ntce_instt_nm") or ""
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r0, prof)); wl = "".join(f"<li>{w}</li>" for w in why_lines(r0, org0))
    life = "".join(f'<span class="{"on" if k <= 1 else ""}">{s}</span>' for k, s in enumerate(["사전규격", "공고", "입찰", "개찰", "낙찰", "계약"]))
    x = (f'<div class="x"><div><span class="k">낼 수 있나</span><ul>{ql}</ul></div><div><span class="k">왜 남았나</span><ul>{wl}</ul></div>'
         f'<div><span class="k">진행</span><div class="life">{life}</div><div class="acts"><a class="bt dark" href="{esc(r0["bid_ntce_url"])}">나라장터 원문</a><a class="bt" href="#">검토 인장</a><a class="bt txt" href="#"><u>안 맞아요</u></a></div></div></div>')
    gate = (f'<div class="gateline"><b>나머지 {len(res) - 5}건은 이메일로.</b><span class="dim">처음 5건은 누구나, 전부는 이메일 하나로. 비밀번호 없음.</span><span class="sp"></span>'
            f'<span class="in"><span>you@company.co.kr</span><span class="bt dark">전부 보기</span></span></div>')
    body = (f'<div class="wrap"><div class="nav"><div class="brand"><i></i>조달핏</div><div class="links"><b>추천</b><span>검토함</span><span>개선 기록</span><span class="cta">이메일로 전부 보기</span></div></div>'
            f'<div class="head"><h1>{esc(co["corp_nm"])}<small>{co["bizrno"][:6]}***** · {esc(status)}</small></h1>'
            f'<div class="meta"><span>{esc(co["rgn_nm"])}</span><span>{esc(hq)}</span><span>종업원 {emp}명</span><span>{esc(mnf)}</span><span class="dim">규모 분류 미입력</span></div>'
            f'<div class="ind"><span class="k">등록업종 {len(inds)}</span>{ind_txt}<br><span class="k">공급물품</span><span class="dim">등록 없음</span></div>'
            f'<div class="act"><span class="q">이 정보로 공고를 걸렀습니다.</span><span>맞나요?</span><a class="bt dark" href="#" style="height:32px">맞아요</a><a class="bt txt" href="#"><u>수정 요청</u></a><span class="mute">나라장터 업체정보 · 10.14 갱신</span></div></div>'
            f'<div class="count"><div class="n">남은 {len(res)}건<small>오늘 10,484건 중 · 자격 통과 · 적합 순</small></div><div class="f"><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span><span class="mute">|</span><span>이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span>새로 3</span></div></div>'
            f'<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>'
            f'{rows[0]}{x}{"".join(rows[1:5])}<div class="fade">{"".join(rows[5:])}</div>{gate}'
            f'<div class="foot">시안 "시트" — 상자·칩 없이 괘선과 타이포만. 숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 결과 — 시트</title>{FONT}<style>{SHEET_CSS}</style></head><body>{body}</body></html>'


# ---------- brief ----------
BRIEF_CSS = BASE + r"""
body { background:#faf9f7 } .wrap { width:760px; margin:0 auto; padding:0 0 140px }
.head { padding:34px 0 26px } .head .k { display:block; margin-bottom:10px }
.head h1 { margin:0; font-size:34px; letter-spacing:-0.04em; font-weight:650; line-height:1.1 } .head p { margin:12px 0 0; font-size:14.5px; line-height:1.7; color:#55554f; max-width:640px } .head p b { color:#141414; font-weight:600 }
.head .act { margin-top:16px; display:flex; align-items:center; gap:14px; font-size:13.5px }
.lede { padding:26px 0 18px; border-top:1px solid #141414; display:flex; align-items:baseline; justify-content:space-between } .lede .n { font-size:22px; font-weight:650; letter-spacing:-0.02em } .lede .n small { font-size:13px; color:#6b6b67; font-weight:450; margin-left:10px } .lede .f { font-size:13px; color:#6b6b67 } .lede .f b { color:#141414; border-bottom:1px solid #141414 } .lede .f > * + * { margin-left:14px }
.e { display:grid; grid-template-columns:40px 1fr auto; gap:0 14px; padding:18px 0; border-top:1px solid #e6e4df } .e .no { font-size:12.5px; color:#8f8f8b; padding-top:4px }
.e .t { font-size:17px; font-weight:600; letter-spacing:-0.015em; line-height:1.35 } .e .m { margin-top:5px; font-size:13px; color:#55554f } .e .m span + span::before { content:"·"; margin:0 7px; color:#c9c9c4 }
.e .w { margin-top:6px; font-size:13.5px; color:#6b6b67; line-height:1.55 }
.e .side { text-align:right; font-size:13px; color:#55554f; padding-top:4px; white-space:nowrap } .e .side b { display:block; font-size:18px; font-weight:650; letter-spacing:-0.02em; color:#141414 } .e .side b.hot { color:#e8431b } .e .side small { color:#737370 }
.x { grid-column:2 / span 2; margin-top:14px; padding:16px 0 4px; border-top:1px dashed #e6e4df; display:grid; grid-template-columns:1fr 1fr; gap:28px }
.x .k { display:block; margin-bottom:8px } .x ul { margin:0; padding:0; list-style:none } .x li { font-size:13.5px; line-height:1.6; padding:3px 0; color:#333 } .x li.todo { color:#737370 }
.x .acts { grid-column:1 / span 2; display:flex; gap:8px; align-items:center; margin-top:12px }
.fade .e { opacity:.3; filter:blur(1.5px) }
.gate { padding:24px 0; border-top:1px solid #141414; font-size:14.5px; line-height:1.6 } .gate b { font-weight:650 } .gate .in { display:flex; gap:6px; margin-top:12px } .gate .in span:first-child { width:300px; height:38px; border:1px solid #e3e1dc; border-radius:8px; background:#fff; display:flex; align-items:center; padding:0 12px; color:#737370; font-size:13px }
.foot { margin-top:30px; font-size:12px; color:#737370 }
"""


def brief(d, prof, row_db):
    res, co = d["results"], d["company"]
    emp, mnf, hq, status, restricted, hp = row_db
    inds = prof["industries"][0] + prof["industries"][1]
    ents = []
    for i, r in enumerate(res, 1):
        org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""; n, dd = dleft(r["bid_clse_date"]); ws = why_lines(r, org)
        ents.append((f'<div class="e"><span class="no">{i:02d}</span><div><div class="t">{esc(r["bid_ntce_nm"])}</div>'
                     f'<div class="m"><span>{esc(org)}</span><span>{esc(r.get("bsns_div_nm"))}</span><span>추정가 {won(r.get("presmpt_prce"))}</span><span>적합 {round(float(r["score"]) * 100)}</span></div>'
                     f'<div class="w">{ws[0] if ws else ""}</div>{{X}}</div><div class="side"><b class="{"hot" if n <= 7 else ""}">D-{n}</b><small>{dd.month}.{dd.day:02d} 마감</small></div></div>'))
    r0 = res[0]
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r0, prof)); wl = "".join(f"<li>{w}</li>" for w in why_lines(r0, r0.get("dmnd_instt_nm") or ""))
    x = (f'<div class="x"><div><span class="k">낼 수 있나</span><ul>{ql}</ul></div><div><span class="k">왜 남았나</span><ul>{wl}</ul></div>'
         f'<div class="acts"><a class="bt dark" href="{esc(r0["bid_ntce_url"])}">나라장터 원문</a><a class="bt" href="#">검토 인장</a><a class="bt txt" href="#"><u>안 맞아요</u></a><span class="dim" style="font-size:12px;margin-left:6px">단계: 공고 중 (2/6)</span></div></div>')
    ents = [e.replace("{X}", x if i == 0 else "") for i, e in enumerate(ents)]
    gate = f'<div class="gate"><b>나머지 {len(res) - 5}건은 이메일로.</b><br><span class="dim">처음 5건은 누구나, 전부는 이메일 하나로. 비밀번호 없이 링크 한 번. 검토 인장과 회사가 기억됩니다.</span><div class="in"><span>you@company.co.kr</span><span class="bt dark">전부 보기</span></div></div>'
    body = (f'<div class="wrap"><div class="nav"><div class="brand"><i></i>조달핏</div><div class="links"><b>추천</b><span>검토함</span><span>개선 기록</span><span class="cta">이메일로 전부 보기</span></div></div>'
            f'<div class="head"><span class="k">{esc(co["rgn_nm"])} · {esc(status)} · 종업원 {emp}명</span><h1>{esc(co["corp_nm"])}</h1>'
            f'<p>등록업종 <b>{esc(inds[0].split("(")[0])}</b> 외 {len(inds) - 1}개, 공급물품 등록 없음, 규모 분류 미입력. 이 정보로 오늘 공고 10,484건을 걸렀습니다. <b>맞나요?</b></p>'
            f'<div class="act"><a class="bt dark" href="#" style="height:34px">맞아요</a><a class="bt txt" href="#"><u>수정 요청</u></a><span class="mute" style="font-size:12px">나라장터 업체정보 · 10.14 갱신</span></div></div>'
            f'<div class="lede"><div class="n">남은 {len(res)}건<small>자격 통과 · 적합 순</small></div><div class="f"><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span><span>이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span></div></div>'
            f'{"".join(ents[:5])}<div class="fade">{"".join(ents[5:])}</div>{gate}'
            f'<div class="foot">시안 "브리프" — 좁은 단, 항목마다 근거 한 문장. 숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 결과 — 브리프</title>{FONT}<style>{BRIEF_CSS}</style></head><body>{body}</body></html>'


if __name__ == "__main__":
    src, outdir = sys.argv[1], sys.argv[2].rstrip("/\\")
    d = json.load(open(src, encoding="utf-8"))
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    row_db = conn.execute("select emp_count, mnfctr_div_nm, hd_off_div_nm, biz_status_nm, is_restricted, hmpg_addr from companies where bizrno=%s", (d["company"]["bizrno"],)).fetchone()
    for name, fn in (("results-sheet.html", sheet), ("results-brief.html", brief)):
        open(f"{outdir}/{name}", "w", encoding="utf-8", newline="\n").write(fn(d, prof, row_db)); print("written", name)

"""결과 페이지 시안 v2 — 2026-10-15 결정 반영: 회사 카드(걸러낸 기준, 맞아요/수정 요청) → 결과 창(근거 칩) → 펼침(자격 먼저, 안 맞아요).
상태 3개: 비로그인 첫 방문(카드 펼침) / 로그인(카드 접힘, 검토함) / 회사 정보 수정 중.
사용: cd backend && PYTHONPATH=. uv run python ../docs/design/scripts/gen_results_v2.py <sample.json> ../docs/design/prototypes/results-v2.html
"""
import html
import json
import sys
from datetime import date, datetime

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import CSS as CSS1, esc, won, dpill, fit, qual, gate_card, dleft  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

TODAY = date(2026, 10, 15)
ACCOUNT = "jansseung@gmail.com"


def strongest(r):
    """행에 보여줄 근거 한 개 — 벡터 제외 가장 큰 양수 시그널."""
    best = None
    for b in r["score_breakdown"]:
        if b["key"] == "vector" or b["points"] <= 0:
            continue
        if best is None or b["points"] > best["points"]:
            best = b
    return best


def row(i, r, sel=False, stamp=False):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    s = strongest(r)
    chip = f'<span class="rc">{esc(s["label"])}</span>' if s else ""
    return (f'<div class="tr {"sel" if sel else ""}"><span class="no">{i:02d}</span>'
            f'<span class="t">{esc(r["bid_ntce_nm"])}{" <em class=stamp>검토</em>" if stamp else ""}</span>'
            f'<span class="org"><i></i>{esc(org)}</span><span>{chip}</span><span class="r">{dpill(r["bid_clse_date"])}</span>'
            f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r">{fit(r["score"])}</span></div>')


def detail(r, prof):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    n, d = dleft(r["bid_clse_date"])
    # 자격 — 공고 허용업종 중 회사 등록업종과 겹치는 것
    allowed = [a.strip() for a in (r.get("bidprc_psbl_indstryty_nm") or "").split(",") if a.strip()]
    mine = set(prof["industries"][0] + prof["industries"][1])
    hit = [a for a in allowed if any(m.split("(")[0] in a or a.split("(")[0] in m for m in mine)]
    q = r.get("qualification") or {}
    lic_line = (f'<li class="ok"><b>면허</b> 허용업종 {len(allowed)}개 중 등록업종과 일치: {esc(", ".join(hit[:2]))}{" 외" if len(hit) > 2 else ""}</li>'
                if hit else ('<li class="ok"><b>면허</b> 제한 없음</li>' if "면허 제한 없음" in q.get("reasons", []) else '<li class="warn"><b>면허</b> 일치하는 등록업종을 찾지 못함 — 회사 정보 확인</li>'))
    rgn = r.get("prtcpt_psbl_rgn_nm")
    rgn_line = (f'<li class="ok"><b>지역</b> {esc(rgn)} 제한 · 본사 {esc(prof["rgn"].split()[0])} 해당</li>' if rgn and prof["rgn"] and prof["rgn"].split()[0] in rgn
                else ('<li class="ok"><b>지역</b> 제한 없음</li>' if not rgn else f'<li class="warn"><b>지역</b> {esc(rgn)} 제한 — 본사 {esc(prof["rgn"].split()[0])}</li>'))
    size_line = '<li class="todo"><b>규모</b> 중소기업 확인서 요구 여부는 문서 조건에서 확인 · 회사 카드에 규모 미입력</li>'
    # 근거 문장
    why = []
    for b in r["score_breakdown"]:
        k = b["key"]
        if k == "institution": why.append(f"<b>{esc(org)}</b>와 과거 거래 이력이 있다")
        elif k == "region": why.append(f"공고 지역 제한이 본사 소재지 <b>{esc(b.get('rgn'))}</b>와 맞다")
        elif k == "industry_tokens": why.append("등록업종·물품 표현이 공고 허용업종과 겹친다: " + ", ".join(esc(m) for m in b.get("matched", [])[:3]))
        elif k == "budget": why.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배 — 비슷한 체급")
        elif k == "budget_mismatch": why.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배 — 체급 차이 큼")
        elif k == "instt_closed": why.append(f"이 기관은 최근 낙찰의 {int(b.get('repeat_ratio', 0) * 100)}%가 같은 회사 — 고정 거래처 경향")
    vec = next((b for b in r["score_breakdown"] if b["key"] == "vector"), None)
    if vec: why.append(f"공고 내용과 회사 업종 설명의 {esc(vec['label'])}")
    why_html = "".join(f"<li>{w}</li>" for w in why)
    life = ["사전규격", "공고", "입찰", "개찰", "낙찰", "계약"]; cur = 1
    life_html = "".join(f'<div class="{"on" if k <= cur else ""}"><b>{k + 1}</b>{s}</div>' for k, s in enumerate(life))
    return (f'<div class="det"><div class="dh"><span class="tag">{esc(r.get("bsns_div_nm"))}</span><span class="m">{esc(org)}</span><span class="sp"></span>'
            f'<span class="m">마감 {d.month}.{d.day:02d} · D-{n} · 추정가 {won(r.get("presmpt_prce"))}</span></div>'
            f'<div class="dt2">{esc(r["bid_ntce_nm"])}</div>'
            f'<div class="cols"><div><div class="sub">낼 수 있나</div><ul class="ql">{lic_line}{rgn_line}{size_line}</ul></div>'
            f'<div><div class="sub">왜 남았나</div><ul class="wl">{why_html}</ul></div></div>'
            f'<div class="sub">진행 단계</div><div class="life">{life_html}</div>'
            f'<div class="acts"><a class="bt dark" href="{esc(r.get("bid_ntce_url"))}" target="_blank" rel="noopener">나라장터 원문</a><a class="bt" href="#">검토 인장</a><a class="bt ghost" href="#">안 맞아요</a>'
            f'<span class="hint">"안 맞아요"는 왜 아닌지 한 줄 받아 추천에 반영합니다</span></div></div>')


def company_card(co, row_db, prof, state):
    rep_i, rest_i = prof["industries"]
    inds = rep_i + rest_i
    emp, mnf, hq, status, restricted, hp = row_db
    biz = co["bizrno"][:6] + "*****"
    chips = "".join(f'<span class="ic{" rep" if i in rep_i else ""}">{esc(i.split("(")[0])}{"<i>×</i>" if state == "edit" else ""}</span>' for i in inds[:8])
    more = f'<span class="ic more">외 {len(inds) - 8}</span>' if len(inds) > 8 and state != "edit" else ""
    if state == "edit":
        chips += "".join(f'<span class="ic">{esc(i.split("(")[0])}<i>×</i></span>' for i in inds[8:]) + '<span class="ic add">+ 업종 추가</span>'
    prods = prof["products"][0] + prof["products"][1]
    prod_html = ", ".join(esc(p) for p in prods[:6]) if prods else '<span class="dim">등록 없음</span>' + ('<span class="ic add">+ 물품 추가</span>' if state == "edit" else "")
    size_html = ('<span class="seg"><span>소기업</span><span>중소기업</span><span>중견</span><span>대기업</span></span>' if state == "edit"
                 else '<span class="dim">미입력 — 중소기업 제한 공고 판별에 쓰입니다</span>')
    foot = {
        "guest": '<div class="cf"><span class="src">출처 나라장터 업체정보 · 2026-10-14 갱신</span><span class="sp"></span><span class="bt dark sm">맞아요</span><span class="bt sm">수정 요청</span></div>',
        "login": "",
        "edit": '<div class="cf edit"><span class="src">수정은 내 화면에만 바로 적용됩니다. 공유 정보 반영은 회사 도메인 이메일 또는 확인 뒤.</span><span class="sp"></span><span class="bt dark sm">이 정보로 다시 찾기</span><span class="bt sm">취소</span></div>',
    }[state]
    if state == "login":
        return (f'<div class="cc line"><b>{esc(co["corp_nm"])}</b><span class="dim">{biz}</span><span>{esc(co["rgn_nm"])}</span>'
                f'<span>등록업종 {len(inds)}</span><span class="dim">확인됨 10.14</span><span class="sp"></span><span class="lk">회사 정보 보기 · 수정</span></div>')
    return (f'<div class="cc{" editing" if state == "edit" else ""}"><div class="ch"><div><b>{esc(co["corp_nm"])}</b><span class="dim">{biz}</span>'
            f'<span class="tagc">{esc(status)}</span>{"<span class=tagc>제재 중</span>" if restricted else ""}</div>'
            f'<span class="cap">이 정보로 공고를 걸렀습니다{" — 맞는지 확인해 주세요" if state == "guest" else ""}</span></div>'
            f'<div class="cg"><div><b>소재지</b>{esc(co["rgn_nm"])} · {esc(hq)}</div><div><b>규모</b>종업원 {emp}명 · {esc(mnf)}</div><div><b>규모 분류</b>{size_html}</div></div>'
            f'<div class="cr"><b>등록업종 {len(inds)}</b><div class="chips">{chips}{more}</div></div>'
            f'<div class="cr"><b>공급물품</b><div class="chips">{prod_html}</div></div>'
            f'{foot}</div>')


def prespec_tab(pre):
    rows = []
    for i, p in enumerate(pre[:8], 1):
        dl = date.fromisoformat(p["opnin_rgst_clse_dt"][:10]); n = (dl - TODAY).days
        rows.append(f'<div class="tr ps"><span class="no">{i:02d}</span><span class="t">{esc(p["prdct_clsfc_no_nm"])}</span><span class="org"><i></i>{esc(p.get("order_instt_nm"))}</span>'
                    f'<span><span class="rc gold">의견 D-{n}</span></span><span class="r"><span class="dt">{dl.month}.{dl.day:02d} 의견 마감</span></span><span class="r">{won(p.get("asign_bdgt_amt"))}</span><span class="r"><span class="fit">{round(float(p["similarity"]) * 100)}</span></span></div>')
    return ('<div class="win"><div class="th"><span>#</span><span>사전규격 (공고 전)</span><span>발주기관</span><span>골든타임</span><span class="r">의견 마감</span><span class="r">예산</span><span class="r">적합</span></div>'
            + "".join(rows) + '<div class="note in">공고 전 단계입니다. 의견을 내면 규격이 유리하게 잡힐 수 있고, 본공고가 뜨면 자동으로 "공고" 탭에 올라옵니다.</div></div>')


CSS2 = r"""
.th, .tr { grid-template-columns:28px minmax(0,1fr) 170px 110px 96px 76px 64px }
.rc { display:inline-flex; padding:3px 8px; border-radius:999px; font-size:11.5px; font-weight:600; background:#eef3ec; color:#1f5f3a; white-space:nowrap } .rc.gold { background:#fbf3d6; color:#8a6a00 }
.cc { background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 24px 48px -28px rgba(0,0,0,.18); padding:16px 20px 12px; margin-bottom:16px }
.cc.editing { border-color:#141414; box-shadow:0 0 0 3px rgba(20,20,20,.06) }
.cc .ch { display:flex; align-items:baseline; justify-content:space-between; gap:12px } .cc .ch b { font-size:20px; letter-spacing:-0.02em; margin-right:10px } .cc .dim { color:#9a9a96; font-size:12.5px; margin-right:8px }
.cc .cap { font-size:12.5px; color:#c8381a; font-weight:600 } .tagc { display:inline-block; padding:2px 7px; border-radius:6px; background:#f1f0ec; color:#444; font-size:11px; margin-left:6px; vertical-align:middle }
.cc .cg { display:grid; grid-template-columns:1fr 1fr 1.4fr; gap:8px; margin-top:12px } .cc .cg div { background:#faf9f6; border-radius:8px; padding:8px 11px; font-size:12.5px } .cc .cg b, .cc .cr > b { display:block; font-size:11px; color:#9a9a96; font-weight:500; margin-bottom:3px }
.cc .cr { margin-top:12px } .chips { display:flex; flex-wrap:wrap; gap:6px; align-items:center; font-size:12.5px }
.ic { display:inline-flex; align-items:center; gap:4px; padding:3px 9px; border-radius:999px; border:1px solid #e6e4df; font-size:12px; color:#333; background:#fff } .ic.rep { background:#141414; color:#fff; border-color:#141414 } .ic.more { color:#9a9a96; border-style:dashed } .ic.add { border-style:dashed; color:#c8381a; border-color:#f3c9bd; cursor:pointer } .ic i { font-style:normal; color:#9a9a96; margin-left:2px }
.seg { display:inline-flex; border:1px solid #e6e4df; border-radius:8px; overflow:hidden } .seg span { padding:4px 10px; font-size:12px; border-right:1px solid #e6e4df; cursor:pointer } .seg span:last-child { border-right:0 }
.cc .cf { display:flex; align-items:center; gap:8px; margin-top:14px; padding-top:12px; border-top:1px solid #f1f0ec } .cc .src { font-size:11.5px; color:#9a9a96 } .cc .cf.edit .src { color:#5c5c58 }
.bt.sm { height:32px; padding:0 12px; font-size:12.5px } .bt.ghost { border-style:dashed; color:#5c5c58 }
.cc.line { display:flex; align-items:center; gap:14px; padding:10px 16px; font-size:12.5px; color:#5c5c58 } .cc.line b { font-size:14px; color:#141414 } .cc.line .lk { color:#141414; border-bottom:1px solid #d8d6d0 }
.tabs { display:flex; gap:4px; padding:4px; border:1px solid #e8e6e1; border-radius:999px; background:#fff; width:max-content; margin:0 0 12px } .tabs span { padding:6px 12px; border-radius:999px; font-size:12.5px; cursor:pointer } .tabs span.on { background:#141414; color:#fff }
.det .cols { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:12px } .det ul { margin:6px 0 0; padding:0; list-style:none } .det li { padding:6px 0; border-top:1px solid #eeece7; font-size:12.5px; line-height:1.5 }
.ql li b { display:inline-block; width:34px; color:#9a9a96; font-weight:500 } .ql li.ok::after { content:"✓"; color:#1f5f3a; float:right; font-weight:700 } .ql li.warn::after { content:"!"; color:#c8381a; float:right; font-weight:700 } .ql li.todo { color:#8a8a86 }
.wl li b { font-weight:600 } .hint { font-size:11.5px; color:#9a9a96; margin-left:6px }
.note.in { padding:10px 18px 14px; font-size:12px; color:#8a8a86 }
.tab-c { display:none } .tab-c.on { display:block }
"""

JS2 = r"""
const root=document.getElementById('root');
function setS(k){document.querySelectorAll('[data-ss]').forEach(e=>e.classList.toggle('on',e.dataset.ss===k));document.querySelectorAll('.vs').forEach(e=>e.style.display=e.dataset.s===k?'block':'none');root.classList.toggle('login',k==='login');}
document.querySelectorAll('[data-ss]').forEach(e=>e.onclick=()=>setS(e.dataset.ss));
document.querySelectorAll('.tabs span').forEach(t=>t.onclick=()=>{const w=t.closest('.vs');w.querySelectorAll('.tabs span').forEach(x=>x.classList.toggle('on',x===t));w.querySelectorAll('.tab-c').forEach(c=>c.classList.toggle('on',c.dataset.t===t.dataset.t));});
setS('guest');
"""


def page(d, prof, row_db):
    res, co, pre = d["results"], d["company"], d["pre_spec_results"]
    n_total = 10484
    vs = []
    for state in ("guest", "login", "edit"):
        login = state == "login"
        vis = res if login else res[:5]; hid = [] if login else res[5:]
        parts = [row(i, r, sel=(i == 1), stamp=(login and i == 2)) for i, r in enumerate(vis, 1)]
        parts.insert(1, detail(res[0], prof))
        gated = f'<div class="gate"><div class="rows">{"".join(row(i, r) for i, r in enumerate(hid, 6))}</div>{gate_card(len(hid))}</div>' if hid else ""
        table = (f'<div class="win"><div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>{"".join(parts)}{gated}</div>')
        tabs = (f'<div class="tabs"><span class="on" data-t="n">공고 {len(res)}</span><span data-t="p">사전규격 {len(pre)}</span><span data-t="o">발주계획 {len(d["order_plan_results"])}</span></div>'
                f'<div class="tab-c on" data-t="n">{table}</div><div class="tab-c" data-t="p">{prespec_tab(pre)}</div><div class="tab-c" data-t="o"><div class="win"><div class="note in">발주계획(연간 계획 단계)도 같은 표. 생략.</div></div></div>')
        vs.append(f'<div class="vs" data-s="{state}" style="display:none">{company_card(co, row_db, prof, state)}'
                  f'<div class="fbar"><span class="today">오늘 {n_total:,}건 중 <b>남은 {len(res)}건</b> · 자격 통과 · 적합 순</span><span class="sp"></span>'
                  f'<span class="chip">이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span class="chip">새로 3</span></div>{tabs}</div>')
    body = f"""
<div id="root" class="page"><div class="wash"></div>
<div class="nav"><div class="brand"><i></i>조달핏</div><div class="pillnav"><span class="on">추천</span><span>검토함</span><span>개선 기록</span></div>
<div class="acct"><span class="chip only-guest">이메일로 전부 보기</span><span class="chip only-login"><i>J</i>{ACCOUNT}</span><span class="chip only-login">검토함 3</span></div></div>
<div class="wrap">{"".join(vs)}
<div class="note"><b>흐름</b> 검색 → 회사 카드(걸러낸 기준 · 맞아요/수정) → 남은 공고(근거 칩) → 펼침(낼 수 있나 → 왜 남았나 → 단계 → 검토/안 맞아요) · 비로그인 5건 게이트 · 사전규격·발주계획은 탭 · 숫자·공고명은 2026-10-15 실제 추천 결과</div>
</div></div>
<div class="sw"><div class="g"><em>상태</em><span data-ss="guest">비로그인 첫 방문</span><span data-ss="login">로그인</span><span data-ss="edit">회사 정보 수정 중</span></div></div>
"""
    css = CSS1 + CSS2 + "\n.fbar .today { font-size:13px; color:#5c5c58 } .fbar .today b { color:#141414; font-size:15px; font-weight:650 }"
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 결과 페이지 시안 v2</title>'
            f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><style>{css}</style></head><body>{body}<script>{JS2}</script></body></html>')


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    conn = connect()
    biz_norm = "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit())
    prof = fetch_company_profile(conn, biz_norm)
    row_db = conn.execute("select emp_count, mnfctr_div_nm, hd_off_div_nm, biz_status_nm, is_restricted, hmpg_addr from companies where bizrno=%s", (d["company"]["bizrno"],)).fetchone()
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, row_db))
    print("written", out)

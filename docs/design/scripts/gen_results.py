"""결과 페이지 시안 생성기 — 실제 추천 API 응답(JSON)으로 3 레이아웃 × 2 상태(비로그인/로그인)를 한 HTML에 만든다.

사용:
  cd backend && PYTHONPATH=. uv run python -c "import json,sys; from app.services.recommend import recommend; \
      sys.stdout.reconfigure(encoding='utf-8'); print(json.dumps(recommend('한종산업개발', limit=12, candidate_pool=100, mode='company', algorithm='v2'), ensure_ascii=False, default=str))" > /tmp/sample.json
  python docs/design/scripts/gen_results.py /tmp/sample.json docs/design/prototypes/results.html
"""
import html
import json
import sys
from datetime import date

TODAY = date(2026, 10, 16)  # data/sample.json 생성일 — D-day 기준
ACCOUNT = "jansseung@gmail.com"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def won(v):
    if not v:
        return "—"
    v = int(v)
    if v >= 100_000_000:
        return f"{v / 100_000_000:,.1f}억".replace(".0억", "억")
    return f"{v // 10_000:,}만"


def dleft(s):
    d = date.fromisoformat(str(s)[:10])
    return (d - TODAY).days, d


def dpill(s):
    n, d = dleft(s)
    cls = "hot" if n <= 1 else ("warm" if n <= 7 else "")
    return f'<span class="pill {cls}">D-{n}</span><span class="dt">{d.month}.{d.day:02d}</span>'


def fit(score):
    p = round(float(score) * 100)
    return f'<span class="fit"><i><b style="width:{p}%"></b></i>{p}</span>'


def ev_items(r):
    out = []
    for b in r["score_breakdown"]:
        if b["key"] == "vector":
            continue
        pts = b["points"]
        sign = "+" if pts > 0 else "−"
        out.append(f'<span class="ev {"neg" if pts < 0 else ""}"><i>{sign}{abs(pts):g}</i>{esc(b["label"])}</span>')
    return out


def qual(r):
    q = r.get("qualification") or {}
    return [esc(x) for x in (q.get("reasons") or [])]


def row_a(i, r, sel=False, stamp=False):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    return (f'<div class="tr {"sel" if sel else ""}" data-i="{i}">'
            f'<span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}{" <em class=stamp>검토</em>" if stamp else ""}</span>'
            f'<span class="org"><i></i>{esc(org)}</span><span class="r">{dpill(r["bid_clse_date"])}</span>'
            f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r">{fit(r["score"])}</span></div>')


def detail(r, compact=False):
    vec = next((b for b in r["score_breakdown"] if b["key"] == "vector"), {"points": 0, "label": "유사도"})
    bars = [(vec["label"], vec["points"])] + [(b["label"], b["points"]) for b in r["score_breakdown"] if b["key"] != "vector"]
    mx = max(abs(p) for _, p in bars) or 1
    bar_html = "".join(
        f'<div class="bar"><span>{esc(l)}</span><i><b class="{"neg" if p < 0 else ""}" style="width:{abs(p) / mx * 100:.0f}%"></b></i><em>{"+" if p > 0 else "−"}{abs(p):g}</em></div>'
        for l, p in bars)
    q = " · ".join(qual(r)) or "자격 정보 없음"
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    n, d = dleft(r["bid_clse_date"])
    life = ["사전규격", "공고", "입찰", "개찰", "낙찰", "계약"]
    cur = 1 if n > 2 else 2
    life_html = "".join(f'<div class="{"on" if k <= cur else ""}"><b>{k + 1}</b>{s}</div>' for k, s in enumerate(life))
    return (f'<div class="det{" compact" if compact else ""}">'
            f'<div class="dh"><span class="tag">{esc(r.get("bsns_div_nm"))}</span><span class="m">{esc(org)}</span></div>'
            f'<div class="dt2">{esc(r["bid_ntce_nm"])}</div>'
            f'<div class="kv"><div><b>마감</b>{d.month}.{d.day:02d} · D-{n}</div><div><b>추정가</b>{won(r.get("presmpt_prce"))}</div>'
            f'<div><b>자격</b>{q}</div><div><b>적합</b>{round(float(r["score"]) * 100)} / 100</div></div>'
            f'<div class="sub">추천 근거</div><div class="bars">{bar_html}</div>'
            f'<div class="sub">진행 단계</div><div class="life">{life_html}</div>'
            f'<div class="acts"><a class="bt dark" href="{esc(r.get("bid_ntce_url"))}" target="_blank" rel="noopener">나라장터에서 보기</a><a class="bt" href="#">검토 인장</a></div>'
            f'</div>')


def gate_card(n_hidden):
    return (f'<div class="cover"><div class="gcard"><b>나머지 {n_hidden}건은 이메일로</b>'
            f'<p>처음 5건은 누구나, 전부는 이메일 하나로. 비밀번호 없이 링크 한 번으로 열립니다.</p>'
            f'<div class="in"><span>you@company.co.kr</span><span class="bt dark">전부 보기</span></div>'
            f'<small>검토 인장 보관 · 회사 기억 · 비밀번호 없음</small></div></div>')


def layout_a(res, login):
    vis = res if login else res[:5]
    hid = [] if login else res[5:]
    parts = [row_a(i, r, sel=(i == 1), stamp=(login and i == 2)) for i, r in enumerate(vis, 1)]
    parts.insert(1, detail(res[0]))  # 1행 펼침: '추천 근거'
    rows = "".join(parts)
    gated = ""
    if hid:
        gated = f'<div class="gate"><div class="rows">{"".join(row_a(i, r) for i, r in enumerate(hid, 6))}</div>{gate_card(len(hid))}</div>'
    return (f'<div class="win"><div class="th"><span>#</span><span>공고</span><span>발주기관</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>'
            f'{rows}{gated}</div>')


def layout_b(res, login):
    vis = res if login else res[:5]
    hid = [] if login else res[5:]

    def li(i, r, sel=False):
        n, d = dleft(r["bid_clse_date"])
        return (f'<div class="li {"sel" if sel else ""}"><span class="no">{i:02d}</span><div class="lb"><b>{esc(r["bid_ntce_nm"])}</b>'
                f'<span>{esc(r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "")}</span></div>'
                f'<div class="lr">{dpill(r["bid_clse_date"])}<em>{round(float(r["score"]) * 100)}</em></div></div>')
    items = "".join(li(i, r, sel=(i == 1)) for i, r in enumerate(vis, 1))
    gated = f'<div class="gate"><div class="rows">{"".join(li(i, r) for i, r in enumerate(hid, 6))}</div>{gate_card(len(hid))}</div>' if hid else ""
    return f'<div class="split"><div class="list win">{items}{gated}</div><div class="side win">{detail(res[0])}</div></div>'


def layout_c(res, login):
    vis = res if login else res[:5]
    hid = [] if login else res[5:]

    def card(i, r, stamp=False):
        evs = "".join(ev_items(r)[:3])
        return (f'<div class="cd"><div class="ch"><span class="no">{i:02d}</span><span class="tag">{esc(r.get("bsns_div_nm"))}</span><span class="sp"></span>{dpill(r["bid_clse_date"])}</div>'
                f'<div class="ct">{esc(r["bid_ntce_nm"])}{" <em class=stamp>검토</em>" if stamp else ""}</div><div class="co">{esc(r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "")}</div>'
                f'<div class="cf">{fit(r["score"])}<span class="won">{won(r.get("presmpt_prce"))}</span></div><div class="evs">{evs}</div></div>')
    cards = "".join(card(i, r, stamp=(login and i == 2)) for i, r in enumerate(vis, 1))
    gated = f'<div class="gate wide"><div class="rows cards">{"".join(card(i, r) for i, r in enumerate(hid, 6))}</div>{gate_card(len(hid))}</div>' if hid else ""
    return f'<div class="cards">{cards}</div>{gated}'


CSS = r"""
* { box-sizing:border-box } body { margin:0; background:#fff; color:#141414; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif; font-variant-numeric:tabular-nums; font-size:13.5px }
a { color:inherit; text-decoration:none }
.sw { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:50; display:flex; gap:14px; padding:8px 10px; background:#141414; color:#fff; border-radius:999px; box-shadow:0 20px 40px -20px rgba(0,0,0,.6); font-size:12.5px }
.sw .g { display:flex; gap:4px; align-items:center } .sw .g em { color:#9a9a96; font-style:normal; margin:0 6px 0 4px } .sw span { padding:6px 11px; border-radius:999px; cursor:pointer; color:#c9c9c4 } .sw span.on { background:#fff; color:#141414; font-weight:600 }
.page { position:relative; min-height:100vh; overflow:clip }
.wash { position:absolute; left:0; right:0; top:0; height:520px; pointer-events:none; background:radial-gradient(900px 420px at 50% -10%, #f3efe9 0%, rgba(243,239,233,0) 70%), radial-gradient(14px 14px at 7px 7px, #ebe9e3 1px, transparent 1.5px); background-size:auto, 28px 28px; -webkit-mask-image:linear-gradient(#000 40%, transparent); mask-image:linear-gradient(#000 40%, transparent) }
.nav { position:relative; display:flex; align-items:center; justify-content:space-between; padding:18px 48px; font-size:13px; color:#555 }
.brand { display:flex; align-items:center; gap:8px; color:#141414; font-weight:700; font-size:14.5px } .brand i { width:7px; height:7px; border-radius:50%; background:#e8431b; display:inline-block }
.pillnav { display:flex; gap:4px; padding:4px; border:1px solid #e8e6e1; border-radius:999px; background:rgba(255,255,255,.7) } .pillnav span { padding:6px 12px; border-radius:999px } .pillnav span.on { background:#141414; color:#fff }
.acct { display:flex; align-items:center; gap:8px } .acct .chip { padding:5px 10px 5px 6px; display:inline-flex; align-items:center; gap:7px } .acct .chip i { width:18px; height:18px; border-radius:50%; background:#fdeae4; color:#c8381a; font-size:10px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; font-style:normal }
.chip { padding:4px 10px; border-radius:999px; font-size:12px; border:1px solid #ebe9e4; color:#444; background:#fff } .chip.on { background:#141414; color:#fff; border-color:#141414 } .chip.cta { background:#e8431b; color:#fff; border-color:#e8431b; font-weight:600 }
.wrap { position:relative; width:1080px; margin:0 auto; padding:10px 0 120px }
.cbar { display:flex; align-items:flex-end; justify-content:space-between; padding:14px 4px 18px }
.cbar h1 { margin:0; font-size:26px; letter-spacing:-0.03em; font-weight:650; line-height:1.2 } .cbar h1 small { font-size:13px; color:#9a9a96; font-weight:450; margin-left:10px; letter-spacing:0 }
.cbar .meta { margin-top:8px; display:flex; gap:8px; align-items:center; font-size:12.5px; color:#5c5c58 } .cbar .meta .tagc { padding:3px 8px; border-radius:6px; background:#f1f0ec; color:#444; font-size:11.5px }
.cbar .today { text-align:right; font-size:12.5px; color:#8a8a86 } .cbar .today b { display:block; font-size:22px; color:#141414; font-weight:650; letter-spacing:-0.02em } .cbar .today b small { font-size:13px; color:#9a9a96; font-weight:450; margin-left:6px }
.fbar { display:flex; align-items:center; gap:8px; padding:0 4px 14px } .fbar .sp { flex:1 } .fbar .sort { font-size:12.5px; color:#8a8a86 } .fbar .sort b { color:#141414; font-weight:550; margin-left:4px }
.mail { display:inline-flex; align-items:center; gap:8px; font-size:12.5px; color:#444; padding:4px 10px 4px 4px; border:1px solid #ebe9e4; border-radius:999px; background:#fff } .mail i { width:28px; height:16px; border-radius:999px; background:#141414; position:relative } .mail i::after { content:""; position:absolute; right:2px; top:2px; width:12px; height:12px; border-radius:50%; background:#fff }
.win { background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 24px 48px -28px rgba(0,0,0,.22); overflow:hidden }
.th, .tr { display:grid; grid-template-columns:28px minmax(0,1fr) 190px 96px 80px 70px; gap:0 14px; align-items:center; padding:0 18px }
.th { font-size:11px; color:#9a9a96; padding-top:10px; padding-bottom:8px; border-bottom:1px solid #eeece7; letter-spacing:.02em }
.tr { height:48px; border-bottom:1px solid #f3f2ee; cursor:pointer } .tr:hover { background:#fbfaf8 } .tr.sel { background:#faf9f6 }
.tr .no, .li .no, .cd .no { color:#b0afab; font-size:11.5px } .tr .t { font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
.org { display:flex; align-items:center; gap:8px; color:#5c5c58; font-size:12.5px; white-space:nowrap; overflow:hidden } .org i { flex:none; width:18px; height:18px; border-radius:6px; background:#ecebe6 }
.r { text-align:right; display:flex; justify-content:flex-end; align-items:center; gap:6px }
.pill { display:inline-flex; padding:3px 8px; border-radius:999px; font-size:11.5px; font-weight:600; background:#f1f0ec; color:#555 } .pill.hot { background:#fdeae4; color:#c8381a } .pill.warm { background:#fbf3d6; color:#8a6a00 } .dt { color:#9a9a96; font-size:12px }
.fit { display:inline-flex; align-items:center; gap:8px; font-size:12.5px; color:#444 } .fit i { width:40px; height:5px; border-radius:3px; background:#eeece7; overflow:hidden; display:inline-block } .fit i b { display:block; height:100%; background:#141414 }
.stamp { display:inline-block; margin-left:8px; padding:1px 6px; border:1.5px solid #e8431b; color:#c8381a; border-radius:4px; font-size:10.5px; font-style:normal; font-weight:700; letter-spacing:.06em; transform:rotate(-4deg) }
.gate { position:relative } .gate .rows { filter:blur(3px); opacity:.55; pointer-events:none } .gate .cover { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:linear-gradient(rgba(255,255,255,0), rgba(255,255,255,.75) 40%) }
.gcard { width:440px; background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 24px 48px -24px rgba(0,0,0,.3); padding:18px 20px; text-align:center } .gcard b { display:block; font-size:16px; letter-spacing:-0.02em } .gcard p { margin:6px 0 0; font-size:12.5px; color:#5c5c58; line-height:1.55 } .gcard small { display:block; margin-top:10px; color:#9a9a96; font-size:11.5px }
.gcard .in { display:flex; gap:6px; margin-top:14px } .gcard .in span:first-child { flex:1; height:40px; border:1px solid #e6e4df; border-radius:9px; display:flex; align-items:center; padding:0 12px; color:#9a9a96; font-size:13px }
.bt { display:inline-flex; align-items:center; justify-content:center; height:40px; padding:0 16px; border-radius:9px; border:1px solid #e6e4df; font-weight:600; font-size:13px; background:#fff } .bt.dark { background:#141414; color:#fff; border-color:#141414 }
/* detail */
.det { padding:18px 22px 20px; background:#faf9f6; border-bottom:1px solid #eeece7 } .side .det { background:#fff; border:0 }
.det .dh { display:flex; align-items:center; gap:10px; font-size:12.5px; color:#8a8a86 } .tag { display:inline-block; padding:3px 8px; border-radius:6px; background:#fdeae4; color:#c8381a; font-size:11.5px; font-weight:600 }
.det .dt2 { margin-top:8px; font-size:16px; font-weight:650; letter-spacing:-0.02em; line-height:1.4 }
.kv { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:12px } .side .kv { grid-template-columns:1fr 1fr } .kv div { background:#fff; border:1px solid #eeece7; border-radius:8px; padding:9px 11px; font-size:12.5px } .side .kv div { background:#faf9f6; border:0 } .kv b { display:block; font-size:11px; color:#9a9a96; font-weight:500; margin-bottom:3px }
.det .sub { margin-top:16px; font-size:11px; color:#9a9a96; letter-spacing:.02em } .bars { margin-top:8px; display:grid; gap:6px }
.bar { display:grid; grid-template-columns:120px 1fr 44px; gap:10px; align-items:center; font-size:12.5px; color:#444 } .bar i { height:6px; border-radius:3px; background:#eeece7; overflow:hidden; display:block } .bar i b { display:block; height:100%; background:#141414 } .bar i b.neg { background:#e8431b } .bar em { text-align:right; font-style:normal; font-weight:600; color:#141414 }
.life { display:grid; grid-template-columns:repeat(6,1fr); margin-top:8px } .life div { padding:10px 10px 0; border-top:2px solid #eeece7; font-size:12px; color:#9a9a96 } .life div.on { border-top-color:#141414; color:#141414 } .life div b { display:block; font-size:10.5px; margin-bottom:3px; color:#b0afab } .life div.on b { color:#e8431b }
.acts { display:flex; gap:8px; margin-top:16px }
/* split */
.split { display:grid; grid-template-columns:minmax(0,1fr) 420px; gap:18px; align-items:start } .side { position:sticky; top:18px }
.li { display:grid; grid-template-columns:28px minmax(0,1fr) auto; gap:12px; align-items:center; padding:12px 16px; border-bottom:1px solid #f3f2ee; cursor:pointer } .li.sel { background:#faf9f6; box-shadow:inset 3px 0 #e8431b } .li:hover { background:#fbfaf8 }
.li .lb b { display:block; font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:13.5px } .li .lb span { display:block; margin-top:3px; color:#8a8a86; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
.li .lr { display:flex; align-items:center; gap:8px } .li .lr em { font-style:normal; font-weight:650; font-size:13px; min-width:24px; text-align:right }
/* cards */
.cards { display:grid; grid-template-columns:1fr 1fr; gap:14px } .gate .rows.cards { margin-top:14px }
.cd { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:16px 18px; box-shadow:0 1px 2px rgba(0,0,0,.04) } .cd .ch { display:flex; align-items:center; gap:8px } .cd .ch .sp { flex:1 }
.cd .ct { margin-top:10px; font-size:15px; font-weight:600; letter-spacing:-0.01em; line-height:1.4 } .cd .co { margin-top:4px; font-size:12.5px; color:#8a8a86 }
.cd .cf { display:flex; justify-content:space-between; align-items:center; margin-top:12px } .cd .won { font-size:12.5px; color:#5c5c58 }
.evs { display:flex; flex-wrap:wrap; gap:6px; margin-top:12px } .ev { display:inline-flex; align-items:center; gap:6px; padding:3px 8px 3px 4px; border-radius:999px; background:#f1f0ec; font-size:11.5px; color:#444 } .ev i { font-style:normal; font-weight:700; padding:1px 5px; border-radius:999px; background:#141414; color:#fff; font-size:10.5px } .ev.neg i { background:#e8431b }
.gate.wide .cover { align-items:center }
/* states */
.page:not(.login) .only-login { display:none !important } .login .only-guest { display:none !important }
.v { display:none } .v.on { display:block }
.v .tr, .v .li, .v .cd { opacity:0; transform:translateY(8px); animation:rise .5s cubic-bezier(.2,.7,.2,1) forwards } .v .tr:nth-child(n+2) { animation-delay:.04s } .v .tr:nth-child(n+4) { animation-delay:.1s } .v .tr:nth-child(n+6) { animation-delay:.16s } .v .cd:nth-child(even) { animation-delay:.06s }
@keyframes rise { to { opacity:1; transform:none } }
.note { margin-top:14px; font-size:12px; color:#9a9a96; padding:0 4px } .note b { color:#5c5c58; font-weight:600 }
"""

JS = r"""
const root=document.getElementById('root');
function setV(k){document.querySelectorAll('.v').forEach(e=>e.classList.toggle('on',e.dataset.v===k));document.querySelectorAll('[data-sv]').forEach(e=>e.classList.toggle('on',e.dataset.sv===k));}
function setS(k){root.classList.toggle('login',k==='login');document.querySelectorAll('[data-ss]').forEach(e=>e.classList.toggle('on',e.dataset.ss===k));document.querySelectorAll('.v').forEach(e=>{const show=e.dataset.s===k;});document.querySelectorAll('.vs').forEach(e=>e.style.display=e.dataset.s===k?'block':'none');}
document.querySelectorAll('[data-sv]').forEach(e=>e.onclick=()=>setV(e.dataset.sv));document.querySelectorAll('[data-ss]').forEach(e=>e.onclick=()=>setS(e.dataset.ss));
setV('a');setS('guest');
"""


def page(d):
    res = d["results"]
    co = d["company"]
    biz = co["bizrno"][:6] + "*****"
    divs = [x for x in (co.get("corp_bsns_div_nm") or "").split(",") if x][:3]
    n_total = 10484
    vs = []
    for state in ("guest", "login"):
        login = state == "login"
        for key, fn in (("a", layout_a), ("b", layout_b), ("c", layout_c)):
            vs.append(f'<div class="vs" data-s="{state}" style="display:none"><div class="v" data-v="{key}">{fn(res, login)}</div></div>')
    body = f"""
<div id="root" class="page"><div class="wash"></div>
<div class="nav"><div class="brand"><i></i>조달핏</div><div class="pillnav"><span class="on">추천</span><span>사전규격</span><span>발주계획</span><span>탐색 지도</span></div>
<div class="acct"><span class="chip only-guest">이메일로 전부 보기</span><span class="chip only-login"><i>J</i>{ACCOUNT}</span><span class="chip only-login">검토함 3</span></div></div>
<div class="wrap">
<div class="cbar"><div><h1>{esc(co["corp_nm"])}<small>{biz}</small></h1><div class="meta"><span>{esc(co.get("rgn_nm"))}</span>{"".join(f'<span class="tagc">{esc(x)}</span>' for x in divs)}<span class="mail only-login"><i></i>아침 7시 메일</span></div></div>
<div class="today">오늘 {n_total:,}건 중<b>남은 {len(res)}건<small>자격 통과 · 가까운 순</small></b></div></div>
<div class="fbar"><span class="chip on">전체 {len(res)}</span><span class="chip">용역 {sum(1 for r in res if r.get("bsns_div_nm") == "용역")}</span><span class="chip">공사 {sum(1 for r in res if r.get("bsns_div_nm") == "공사")}</span><span class="chip">물품 {sum(1 for r in res if r.get("bsns_div_nm") == "물품")}</span><span class="chip">이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span class="sp"></span><span class="sort">정렬<b>적합 순</b> · 마감 순</span></div>
{"".join(vs)}
<div class="note"><b>규칙</b> 비로그인은 상위 5건 근거까지 공개, 6건째부터 흐림 + 이메일 게이트 · 로그인(매직링크) = 알림 구독 + 검토 인장 보관 · 숫자·공고명은 2026-10-15 실제 추천 결과</div>
</div></div>
<div class="sw"><div class="g"><em>시안</em><span data-sv="a">A 표 + 펼침</span><span data-sv="b">B 목록 + 상세</span><span data-sv="c">C 카드</span></div><div class="g"><em>상태</em><span data-ss="guest">비로그인</span><span data-ss="login">로그인</span></div></div>
"""
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 결과 페이지 시안</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>"""


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d))
    print("written", out)

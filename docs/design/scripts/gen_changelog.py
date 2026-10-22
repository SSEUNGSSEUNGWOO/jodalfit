"""개선 기록 최종 시안(`prototypes/final/changelog-final.html`) — `/changelog`. `docs/recommender/changelog.md` 를 그대로 렌더링하는 읽기 페이지.

- 머리: 제목 + 재는 방법(문서 첫 문단 그대로). 왼쪽 목차(날짜·제목, sticky, 스크롤 스파이) / 오른쪽 흰 판에 글 순서 그대로(처음 → 변경 → 지금).
- 마크다운 부분집합만 변환: ## · 문단 · 표 · **굵게** · `코드` · ---. 표 숫자는 tabular, 전/후 열은 그대로(화살표·색 안 입힘 — 숫자가 말한다).
- 로그인 무관(공개 페이지). 상태 없음. 문서가 바뀌면 다시 생성하면 된다 — 구현도 같은 방식(빌드 때 md → 페이지).

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_changelog.py ../docs/recommender/changelog.md ../docs/design/prototypes/final/changelog-final.html
검증: gen_changelog.py --check ../docs/design/prototypes/final/changelog-final.html
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
.ent tr.after td { font-weight:650 } .ent td .dl { font-size:11.5px; font-weight:600; color:#141414; margin-left:6px; border-bottom:1px solid #f97316 } .ent td .dl.neg { border-bottom-color:#b8b6b0; color:#737370 }
.grp.start .ent { background:transparent; border-style:dashed } .grp.start .ent h2 .tag { font-size:12px; color:#737370; font-weight:500; margin-left:10px; letter-spacing:0 }
.tail { margin-top:6px; padding:18px 0 0 186px; font-size:13.5px; color:#6b6b67; line-height:1.7 } .tail code { font-family:ui-monospace,Consolas,monospace; font-size:12.5px }
.now .frame { grid-column:1/-1; margin-top:18px; padding-top:14px; border-top:1px solid #ececea; font-size:13.5px; color:#55554f; line-height:1.6 } .now .frame b { color:#141414; font-weight:650 }
/* 어떻게 고르는가 — 네 단계 깔때기(실제 수치) + 점수표(코드 값 그대로) */
.how2 { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:22px 28px 24px; margin-top:16px }
.how2 .ph { display:flex; justify-content:space-between; align-items:baseline; gap:20px; padding-bottom:12px; border-bottom:1px solid #141414 } .how2 .ph h2 { margin:0; font-size:16px; font-weight:650 } .how2 .ph span { font-size:12.5px; color:#737370 }
.steps { display:grid; grid-template-columns:repeat(4,1fr); gap:0 24px; margin-top:6px } .steps > div { padding:16px 0 4px; border-right:1px solid #ececea; padding-right:20px } .steps > div:last-child { border-right:0 }
.steps .n { font-size:26px; font-weight:650; letter-spacing:-0.035em; line-height:1; font-variant-numeric:tabular-nums } .steps .n small { font-size:12px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:4px } .steps > div:last-child .n { color:#f97316 }
.steps .k { display:block; margin:10px 0 6px } .steps p { margin:0; font-size:13.5px; line-height:1.6; color:#333 } .steps p b { font-weight:600 }
.score { display:grid; grid-template-columns:1fr 1fr; gap:0 40px; margin-top:18px; padding-top:16px; border-top:1px solid #ececea }
.score .k { display:block; margin-bottom:6px } .score ul { margin:0; padding:0; list-style:none } .score li { display:flex; justify-content:space-between; gap:12px; padding:6px 0; border-bottom:1px solid #f1f0ec; font-size:13.5px; color:#333 }
.score li b { font-variant-numeric:tabular-nums; font-weight:600; color:#141414; white-space:nowrap } .score li b.m { color:#737370; font-weight:500 } .score li .d { color:#6b6b67; margin-left:6px; font-size:12.5px }
.score .note { grid-column:1/-1; margin-top:10px; font-size:12.5px; color:#6b6b67; line-height:1.6 }
.ent p.tried { margin-top:14px; padding:10px 14px; border-left:2px solid #d8d6d0; background:#faf9f7; border-radius:0 8px 8px 0; color:#55554f; font-size:13.5px } .ent p.tried b { color:#141414 }
.ent h2 .tag { font-size:11.5px; color:#737370; font-weight:500; margin-left:10px; letter-spacing:0; border:1px solid #e3e1dc; border-radius:999px; padding:2px 8px; vertical-align:2px }
@media screen and (max-width:720px){ .steps { grid-template-columns:1fr 1fr; gap:0 16px } .steps > div:nth-child(2) { border-right:0 } .score { grid-template-columns:1fr } }
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
            txt = " ".join(buf); cls = ' class="tried"' if txt.startswith("**해 보고 뺀 것**") else ""   # 실패한 실험 — 회색 블록
            (cur[3] if cur else lead).append(f"<p{cls}>{inline(txt)}</p>"); buf.clear()

    def flush_t():
        if tbl:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl if not re.match(r"^\|?\s*-", r)]
            cur[3].append(table(rows)); tbl.clear()

    for ln in lines[1:]:
        if ln.startswith("## "):
            flush_p(); flush_t()
            title = ln[3:].strip(); m = re.match(r"(\d{4}-\d{2}-\d{2}) · (.+)", title)
            if m: date, name = m.group(1), m.group(2)
            else:
                m2 = re.search(r"\((\d{4}-\d{2}-\d{2}) 측정\)", title)   # '처음 (2026-10-13 측정)'
                date, name = (m2.group(1), title[:m2.start()].strip()) if m2 else (None, title)
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
    if not m: return None
    raw = m.group(1); dec = len(raw.split(".")[1]) if "." in raw else 0
    return (float(raw.replace(",", "")), m.group(2) or "", dec)


def delta(a, b):
    """전 → 후 차이 표기. % 는 p 로. 내린 건 회색."""
    d = b[0] - a[0]
    if abs(d) < 1e-9: return ""
    unit = "p" if b[1] == "%" else ""
    dec = max(a[2], b[2])
    txt = f"{d:+,.{dec}f}" + unit
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
    bd = "".join(f'<tr class="{"after" if r[0] in ("후", "지금") else ""}">' + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{bd}</tbody></table>"


HIDE = ["재는 회사 수를 300곳에서 3,000곳으로", "\"성공인데 0건\"을 잡는 건강 점검", "프론트 검사 오류 4개 정리", "조건 검색에 키워드·발주기관을 더하는 바탕"]   # 내부 작업 — 입찰 담당자에게 뜻이 없다
MEASURED_FROM = "2026-10-13"   # 채점표가 생긴 날. 그 전 항목은 '측정 전'
ACTIVE_0801, POOL = 8628, 30   # baseline-2026-10-16-big: 8/1 활성 공고 수. 무작위 30건이면 30/8,628 = 0.3%


def how_panel():
    """어떻게 고르는가 — 깔때기는 data/funnel.json(한종산업개발, 10-16 실측), 점수표는 app/recommender/score.py 값 그대로."""
    import json
    f = json.load(open(Path(__file__).resolve().parents[1] / "data" / "funnel.json"))
    steps = [("지금 입찰 가능한 공고", f["total"], "마감 90일 이내 전부", "여기서 시작합니다. 글의 뜻이 비슷한 공고, 회사 <b>등록업종을 허용하는</b> 공고, 회사 <b>공급물품 분류가 맞는</b> 공고 세 통로로 후보를 모읍니다."),
             ("등록업종 허용 공고", f["industry"], f'전체의 {f["industry"] / f["total"] * 100:.1f}%', "공고가 요구하는 업종에 회사가 등록돼 있는 공고만 남깁니다."),
             ("참가 자격 통과", f["qualified"], f'면허·지역 {f["qualified"] / f["industry"] * 100:.0f}% 통과', "면허(허용업종) · 지역 제한(시·도 또는 시·군·구) · 참가자격 등록 마감을 대조해 <b>낼 수 없는 공고는 뺍니다.</b>"),
             ("검토할 공고", f["result"], "점수 순 · 다양성 반영", "아래 점수표로 줄 세우고, 비슷한 공고가 상위를 독점하지 않게 섞은 뒤 보여줍니다.")]
    st = "".join(f'<div><div class="n">{v:,}<small>건</small></div><span class="k">{k}</span><p>{d}</p><p class="dim" style="margin-top:4px;font-size:12.5px">{sub}</p></div>' for k, v, sub, d in steps)
    pos = [("공고 내용과 회사 업종 설명의 유사도", "0 ~ 100", "기본 점수"), ("과거 거래한 기관의 공고", "+12", ""), ("유사 회사가 수주한 기관", "+9", "2건 이상"), ("지역 제한이 본사와 일치", "+9", ""),
           ("등록업종·물품 표현이 공고와 겹침", "+3 / 개", "최대 9"), ("추정가가 회사 평균 수주가의 0.7~1.5배", "+2", "")]
    neg = [("추정가가 평균의 1/10 이하 또는 10배 이상", "−2", ""), ("최근 낙찰의 절반 이상을 같은 회사가 가져간 기관", "−3", "10건 이상 기관만"), ("마감 1일 이내", "−9", "")]
    li = lambda rows: "".join(f'<li><span>{t}{f"<span class=d>{d}</span>" if d else ""}</span><b class="{"m" if v.startswith("−") else ""}">{v}</b></li>' for t, v, d in rows)
    return (f'<section class="how2"><div class="ph"><h2>어떻게 고르는가</h2><span>숫자는 한 회사(창원 · 환경설비 용역)의 {TODAY.month}.{TODAY.day:02d} 실제 결과 · 점수표는 운영 코드 값</span></div>'
            f'<div class="steps">{st}</div>'
            f'<div class="score"><div><span class="k">점수를 올리는 것</span><ul>{li(pos)}</ul></div><div><span class="k">점수를 내리는 것</span><ul>{li(neg)}</ul></div>'
            f'<div class="note">회사 벡터 = 등록업종·공급물품 설명(메인) + 과거 수주 이력(보조). 섞는 비율은 수주 건수에 따라 — 0건이면 업종만, 1~5건 0.65 : 0.30, 6건 이상 0.50 : 0.45. '
            f'점수는 "낙찰 확률"이 아니라 검토 순서입니다. 자격 판정은 공고 필드(허용업종·지역·등록 마감)만 — 문서 속 면허·증명 요구는 판정하지 않고 보여만 줍니다.</div></div></section>')


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
            f'<div class="meta"><span><i class="live"></i>계속 갱신</span><span>변경 {n_changes}건</span><span>마지막 {last_date[5:7]}.{last_date[8:]}</span><span>8/1 기준</span></div></div>'
            f'<div class="frame">8월 1일에 입찰 가능했던 공고 <b>{ACTIVE_0801:,}건</b>을 <b>{POOL}건</b>으로 좁혔을 때 그 안에 뒤에 실제로 낙찰받은 공고가 들어 있던 비율입니다. 무작위로 {POOL}건을 고르면 <b>{POOL / ACTIVE_0801 * 100:.1f}%</b>.</div></div>')


def page(text):
    lead, entries = md(text)
    now = next(e for e in entries if e[2].startswith("지금"))
    dated = [e for e in entries if e[1] and e[2] not in HIDE]
    by_date = {}
    for e in dated: by_date.setdefault(e[1], []).insert(0, e)   # 최신이 위. 같은 날 안도 문서가 시간순이라 뒤집는다
    dates = sorted(by_date, reverse=True)
    def ent(e):
        tag = '<span class="tag">처음 측정</span>' if e[2].startswith("처음") else ('<span class="tag">측정 전</span>' if e[1] < MEASURED_FROM else "")
        return f'<article class="ent" id="{e[0]}"><h2>{esc(e[2])}{tag}</h2>{"".join(e[3])}</article>'
    groups = "".join(f'<section class="grp {"first" if k == 0 else ""}"><div class="dt"><div><b>{d[5:7]}.{d[8:]}</b><small>{d[:4]}{" · " + str(len(by_date[d])) + "건" if len(by_date[d]) > 1 else ""}</small></div><span class="dot"></span></div><div>{"".join(ent(e) for e in by_date[d])}</div></section>'
                     for k, d in enumerate(dates))
    how = f'<details class="how"><summary>재는 방법</summary>{"".join(lead[1:])}</details>'
    html = (f'{nav("guest", "log")}<div class="head"><h1>개선 기록</h1>{lead[0].replace("<p>", "<p class=lead>", 1)}{hero(now, len([e for e in dated if e[1] >= MEASURED_FROM and not e[2].startswith("처음")]), dates[0])}{how}</div>'
            f'{how_panel()}<div class="tl">{groups}</div>'
            f'<div class="tail">측정 방법과 숫자는 바꾸지 않고 쌓습니다. 원문 <code>docs/recommender/changelog.md</code>.</div>'
            f'<div class="foot">개선 기록 최종 시안 3차 — 최신순 타임라인 {dates[0]} ~ {dates[-1]}, 머리에 처음 → 지금 숫자 셋 + 그 숫자의 뜻(8,628건 → 30건, 무작위 0.3%) + 다음에 할 것, "어떻게 고르는가" 판(실제 깔때기·운영 점수표). '
            f'내부 작업 항목 {len(HIDE)}건은 숨김(원문엔 있음). 채점표 이전(5~9월) 항목은 git 이력으로 거슬러 적고 "측정 전" 표시. 원문 {TODAY.isoformat()} 기준.</div>')
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
            inView: document.querySelectorAll('.ent.in').length, raw: document.querySelector('.tl').innerText.includes('**') || document.querySelector('.tl').innerText.includes('|'), b: document.querySelector('.nav .links b').textContent, start: true } }""")
        assert s["ents"] == 21 and s["grps"] == 12 and s["dts"][:4] == ["10.16", "10.15", "10.14", "10.13"] and s["dts"][-1] == "05.24", s
        h = pg.evaluate("""() => ({ steps: document.querySelectorAll('.how2 .steps > div').length, nums: [...document.querySelectorAll('.how2 .steps .n')].map(e => e.firstChild.textContent), pos: document.querySelectorAll('.how2 .score li').length,
            tags: [...document.querySelectorAll('.ent h2 .tag')].map(e => e.textContent), hidden: [...document.querySelectorAll('.ent h2')].some(e => /린트|검사 오류|건강 점검|3,000곳/.test(e.textContent)), frame: document.querySelector('.now .frame').textContent })""")
        assert pg.evaluate("document.querySelectorAll('.ent p.tried').length") == 3 and h["steps"] == 4 and h["nums"] == ["9,374", "835", "372", "12"] and h["pos"] == 9 and h["tags"].count("측정 전") == 8 and h["tags"].count("처음 측정") == 1 and not h["hidden"] and "0.3%" in h["frame"], h
        assert s["sts"] == 3 and s["big"] == ["49%", "28%", "38%"] and s["dl"] == 3 and s["tdl"] >= 15 and s["bar"] != "none" and s["sticky"] == "sticky" and s["firstDot"] == "rgb(249, 115, 22)", s
        assert not s["raw"] and s["b"] == "개선 기록" and s["start"], s
        pg.screenshot(path=str(out / "_shot_changelog.png"), full_page=False)
        pg.evaluate("document.querySelectorAll('.ent')[8].scrollIntoView({block:'center'})"); pg.wait_for_timeout(700)
        assert pg.evaluate("document.querySelectorAll('.ent')[8].classList.contains('in')")
        pg.screenshot(path=str(out / "_shot_changelog_mid.png"), full_page=False)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(600)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390") and pg.evaluate("getComputedStyle(document.querySelector('.grp .dt')).position") == "static"
        pg.screenshot(path=str(out / "_shot_changelog_390.png"), full_page=False)
        b.close()
    print(f"ok timeline {s['ents']} entries / {s['grps']} dates {s['dts'][0]}..{s['dts'][-1]} newest first, hero {s['big']} + frame, how-panel 4 steps + 9 factors, 측정 전 8 · hidden 4, deltas {s['tdl']}, 390 ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(open(sys.argv[1], encoding="utf-8").read()))
    print("written", sys.argv[2])

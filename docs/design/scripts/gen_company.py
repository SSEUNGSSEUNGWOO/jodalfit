"""회사 페이지 최종 시안(`prototypes/company-final.html`) — `/companies/[bizrno]` 를 결과 페이지 문법으로.

결정(2026-10-17 승우님): 추천 먼저, 머리 장면(선 캔버스) 없음. 회사 페이지는 SSR 문서이고 추천은 대부분 캐시 히트라
"계산이 안 걸리면 안 보여준다" 원칙상 캔버스가 설 자리가 없다. 걸러낸 경로는 숫자 한 줄로만 남긴다.

구성: nav → 머리(회사 이름 · 사업자번호 마스킹 · 다른 회사 / 지역·등록업종·공급물품·구분·기준일 / 걸러낸 경로 한 줄 + 종류·마감 요약)
 → 판 1 검토할 공고(결과 페이지의 두 단 표형 그대로: 왼쪽 회사 정보 sticky, 오른쪽 표 5건 + 이메일 게이트 + 흐림 7건)
 → 판 2 수주 이력(요약 한 줄 + 계약 표 10) → 판 3 낙찰(요약 + 투찰률 눈금 + 낙찰 표) + 같은 시장 낙찰 회사.
사례 넷(실제 DB 행): A 한종산업개발(결과 시안과 같은 회사) / B (유)금강환경(계약 61·낙찰 22·참가 37, 물품·용역·공사) /
 C 인서트유(벡터·업종·이력 없음 → 색인 제외 대상) / D 늘푸른임업(국세청 폐업). 상태: 비로그인 / 이메일 뒤 / 계산 중.

데이터: cd backend && KURE_BACKEND=torch PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_company.py --data ../docs/design/data
생성:   cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_company.py ../docs/design/data ../docs/design/prototypes/company-final.html
검증:   gen_company.py --check ../docs/design/prototypes/company-final.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc, dleft  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_flow import ORANGE, nav, ZERO  # noqa: E402
from gen_split import SPLIT_CSS, trow, gate, rgn_base  # noqa: E402
from gen_results_final import CSS as FINAL_CSS, chain  # noqa: E402
from gen_report import LABELS  # noqa: E402

CASES = [  # (키, 사업자번호 norm, 추천 계산 여부)
    ("a", "1248177731", True),    # 한종산업개발 — data/sample.json 과 같은 회사. 추천은 sample.json 재사용
    ("b", "4128113667", True),    # (유)금강환경 — 계약 61 · 낙찰 22 · 참가 37 · 물품/용역/공사
    ("c", "3072104519", False),   # 인서트유 — 벡터·등록업종·이력 없음
    ("d", "7328601508", False),   # 주식회사 늘푸른임업 — 국세청 폐업 2026-08-14
]


# ────────────────────────────── 데이터 ──────────────────────────────
def fetch_case(conn, biz, with_reco):
    from jobs.evaluate_recommender import fetch_company_profile
    co = dict(zip("bizrno corp_nm rgn_nm corp_bsns_div_nm emp_count hd_off_div_nm mnfctr_div_nm opng_dt biz_status_cd biz_status_nm biz_closed_dt is_restricted embedded updated".split(),
                  conn.execute("""select bizrno, corp_nm, rgn_nm, corp_bsns_div_nm, emp_count, hd_off_div_nm, mnfctr_div_nm, opng_dt, biz_status_cd, biz_status_nm, biz_closed_dt,
                                  is_restricted, embedded_k_at is not null, updated_at::date from companies where bizrno_norm = %s order by embedded_k_at desc nulls last limit 1""", (biz,)).fetchone()))
    prof = fetch_company_profile(conn, biz)
    cts = [dict(zip("cntrct_nm cntrct_cncls_date cntrct_amt dmnd_instt_nm cntrct_instt_nm bsns_div_nm cntrct_cncls_mthd_nm bid_ntce_no".split(), r)) for r in conn.execute(
        """select cntrct_nm, cntrct_cncls_date, cntrct_amt, dmnd_instt_nm, cntrct_instt_nm, bsns_div_nm, cntrct_cncls_mthd_nm, bid_ntce_no
           from contracts where rprsnt_corp_bizrno_norm = %s order by cntrct_cncls_date desc, cntrct_no limit 10""", (biz,))]
    ct_sum = dict(zip("n total first last".split(), conn.execute(
        "select count(*), coalesce(sum(cntrct_amt),0), min(cntrct_cncls_date), max(cntrct_cncls_date) from contracts where rprsnt_corp_bizrno_norm = %s", (biz,)).fetchone()))
    ct_sum["top_instt"] = [r[0] for r in conn.execute(
        "select dmnd_instt_nm from contracts where rprsnt_corp_bizrno_norm = %s and dmnd_instt_nm is not null group by 1 order by count(*) desc, sum(cntrct_amt) desc limit 3", (biz,))]
    aws = [dict(zip("bid_ntce_no bid_ntce_ord bid_ntce_nm dmnd_instt_nm bid_clse_date openg_date presmpt_prce bid_amt bid_rate openg_rank is_winner bsns_div_nm".split(), r)) for r in conn.execute(
        """select a.bid_ntce_no, a.bid_ntce_ord, b.bid_ntce_nm, coalesce(b.dmnd_instt_nm, b.ntce_instt_nm), b.bid_clse_date, b.openg_date, b.presmpt_prce,
                  a.bid_amt, a.bid_rate, a.openg_rank, a.is_winner, coalesce(b.bsns_div_nm, a.bsns_div_nm)
           from award_results a left join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where a.bizrno_norm = %s order by a.is_winner desc, b.bid_clse_date desc nulls last, a.bid_ntce_no desc limit 60""", (biz,))]
    n_part = conn.execute("select count(*) from award_results where bizrno_norm = %s", (biz,)).fetchone()[0]
    peers = [dict(zip("bizrno corp_nm encounter_count sample_notice_names".split(), r[:4])) for r in conn.execute(
        "select * from similar_notice_awardees_k(%s, 10, 60, 30)", (biz,))]
    out = dict(company=co, profile={k: v for k, v in prof.items() if k in ("rgn", "industries", "products")}, contracts=cts, contract_summary=ct_sum,
               awards=aws, n_participations=n_part, peers=peers, reco=None, funnel=None)
    if with_reco:
        from gen_data import funnel, strip
        from app.services.recommend import recommend
        d = strip(json.loads(json.dumps(recommend(co["corp_nm"], limit=12, candidate_pool=100, mode="company", algorithm="v2"), default=str)))
        f, _ = funnel(conn, prof, len(d["results"]))
        out["reco"], out["funnel"] = d, f
    return out


def write_data(out_dir):
    from jobs.evaluate_recommender import connect
    conn = connect(); out = Path(out_dir)
    for key, biz, with_reco in CASES:
        d = fetch_case(conn, biz, with_reco)
        (out / f"company_{key}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8", newline="\n")
        print(key, d["company"]["corp_nm"], "계약", d["contract_summary"]["n"], "낙찰", sum(1 for a in d["awards"] if a["is_winner"]), "참가", d["n_participations"],
              "유사", len(d["peers"]), "추천", len(d["reco"]["results"]) if d["reco"] else "-")


# ────────────────────────────── 화면 ──────────────────────────────
CSS = FINAL_CSS + r"""
/* 회사 페이지 — 머리 장면 없음. .stage 를 쓰지 않으므로 flow 의 접힘 규칙은 .done 으로 처음부터 펴 둔다 */
.head { border-bottom:1px solid #141414; padding-bottom:18px }
.done .chain { height:auto; padding-top:18px }
.res { max-height:none; overflow:visible }
.head .meta .st { color:#141414; font-weight:600; border-left:2px solid #f97316; padding-left:8px }   /* 폐업·제재 — 면이 아니라 괘선 */
.head .meta .st.gray { border-left-color:#d8d6d0; font-weight:500 } .head .meta .st::before { content:none !important } .head .meta .st { margin-left:14px }
/* 판 — 결과 페이지 .res .cols 와 같은 판을 아래로 반복. 판 사이 28px */
.pane { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:6px 28px 28px; margin-top:28px }
.pane .ph { display:flex; align-items:baseline; justify-content:space-between; gap:20px; padding:22px 0 12px; border-bottom:1px solid #141414; flex-wrap:wrap }
.pane .ph h2 { margin:0; font-size:16px; font-weight:650; letter-spacing:-0.01em } .pane .ph h2 small { font-size:13.5px; color:#6b6b67; font-weight:450; margin-left:8px }
.pane .ph .sum { font-size:13.5px; color:#55554f; padding:0; display:flex; gap:0; align-items:baseline } .pane .ph .sum span + span::before { content:"·"; margin:0 8px; color:#c9c9c4 }
.pane .ph .sum b { color:#141414; font-weight:650 }
/* 이력 표 — 결과 표와 같은 격자(번호 없음). 금액은 숫자만, 막대 없음 */
.ht { display:grid; gap:0 12px; align-items:start; padding:12px 0; border-bottom:1px solid #ececea; font-size:14px }
.ht.th { padding:10px 0 8px; border-bottom:1px solid #e6e4df; font-size:12px; color:#6b6b67; font-weight:600 }
.ct.ht { grid-template-columns:84px minmax(0,1fr) 220px 136px } .aw.ht { grid-template-columns:minmax(0,1fr) 200px 136px 80px }
.ht .short, .ht .sub .m { display:none }   /* 축약 금액·둘째 줄 발주기관은 390 전용 */
.ht .r { text-align:right } .ht .dt { color:#55554f; font-variant-numeric:tabular-nums } .ht .t { font-weight:550; line-height:1.45 } .ht .org { color:#55554f }
.ht .t a:hover { border-bottom:1px solid #f97316 } .ht .sub { display:block; font-size:12.5px; color:#6b6b67; margin-top:2px }
.ht .rate { font-weight:600 } .ht .rate.none { color:#8f8f8b; font-weight:450 }
.more { display:block; padding:12px 0 0; font-size:13px; color:#55554f } .more a { color:#141414; border-bottom:1px solid #d8d6d0 } .more a:hover { border-bottom-color:#f97316 }
/* 투찰률 눈금 — 60~100% 5% 칸. 막대 높이는 건수, 색은 먹. 평균 자리에 주황 세로선 하나 */
.hist { display:grid; grid-template-columns:200px 1fr; gap:28px; padding:18px 0 6px; border-bottom:1px solid #ececea; align-items:start }
.hist .k { display:block; margin-bottom:6px } .hist .big { font-size:28px; font-weight:650; letter-spacing:-0.03em; line-height:1.1 } .hist .big small { font-size:13px; color:#6b6b67; font-weight:450; margin-left:6px; letter-spacing:0 }
.hist .rng { margin-top:6px; font-size:13px; color:#55554f } .hist .rng b { color:#141414; font-weight:600 }
.bars { position:relative; display:grid; grid-template-columns:repeat(9,1fr); gap:6px; align-items:end; height:88px; padding-top:14px }
.bars .b { position:relative; display:flex; flex-direction:column; justify-content:flex-end; height:100% }
.bars .b i { display:block; background:#141414; min-height:2px; border-radius:1px 1px 0 0 } .bars .b.z i { background:#ececea }
.bars .b em { position:absolute; left:0; right:0; bottom:100%; text-align:center; font-style:normal; font-size:11.5px; font-weight:600; color:#141414; padding-bottom:3px } .bars .b.z em { display:none }
.bars .avg { position:absolute; top:0; bottom:0; width:2px; background:#f97316; pointer-events:none }
.axis { display:grid; grid-template-columns:repeat(9,1fr); gap:6px; font-size:11px; color:#8f8f8b; margin-top:6px; text-align:center } .axis span:first-child { text-align:left }
.hist .note { grid-column:1/-1; font-size:12.5px; color:#6b6b67; padding:4px 0 10px }
/* 같은 시장 낙찰 회사 — 표 세 칸 */
.pr.ht { grid-template-columns:minmax(0,1fr) 110px 1.3fr } .pr .n { font-weight:600; text-align:right } .pr .ex { color:#55554f; font-size:13px; line-height:1.5 }
/* 계산 중 — 표 자리에 조용한 한 줄. 가짜 진행률 없음 */
.calc { display:none; padding:26px 0 8px; font-size:14px; color:#55554f } .calc b { color:#141414; font-weight:600; display:block; margin-bottom:4px }
.mh .k i { font-style:normal }
.st-search .pane, .st-search .chain { opacity:.22; filter:blur(1px); pointer-events:none } .pane, .chain { transition:opacity .3s ease, filter .3s ease }
.st-calc .calc { display:block } .st-calc .sheet, .st-calc .mh .k i, .st-calc .tabs { display:none } .st-calc .chain b { color:#b8b6b0 } .st-calc .chain b.acc { color:#b8b6b0 }
/* 벡터·이력 없음(C) — 추천 판은 기준 없음 안내 + 키워드. 수주·낙찰 판은 없음 */
.none-reco { padding:26px 0 8px; font-size:14px; color:#55554f; max-width:640px; line-height:1.7 } .none-reco b { color:#141414; font-weight:600; display:block; font-size:16px; margin-bottom:6px }
.none-reco .acts { display:flex; gap:8px; align-items:center; margin-top:16px; flex-wrap:wrap } .none-reco .in { display:flex; gap:6px }
.none-reco .in span:first-child { width:300px; max-width:100%; height:36px; border:1px solid #e3e1dc; border-radius:8px; display:flex; align-items:center; padding:0 12px; color:#737370; font-size:13px }
.side .txt .dim { color:#737370 }
/* 분석 요청 — 칸 둘 + 버튼 한 줄. 접수 뒤는 지금/다음/조건 세 줄 */
.req { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) auto; gap:10px; align-items:end; margin-top:18px }
.req label { display:flex; flex-direction:column; gap:6px } .req input { height:38px; border:1px solid #e3e1dc; border-radius:8px; padding:0 12px; font:inherit; font-size:14px; color:#141414; background:#fff; outline:none; transition:border-color .15s, box-shadow .15s }
.req input:focus { border-color:#f97316; box-shadow:0 0 0 4px rgba(249,115,22,.14) } .req input::placeholder { color:#9b9a95 } .req .bt { height:38px; cursor:pointer }
.reqn { margin-top:10px; font-size:12.5px; color:#6b6b67; line-height:1.6 }
.reqd { display:none; margin-top:18px; border-top:1px solid #141414; padding-top:14px } .reqd > b { display:block; font-size:15px; margin-bottom:8px }
.reqd .row { display:grid; grid-template-columns:96px 1fr; gap:12px; padding:6px 0; border-bottom:1px solid #ececea; font-size:14px; line-height:1.6 } .reqd .row .k { padding-top:3px }
.reqd a { color:#141414; border-bottom:1px solid #141414 } .reqd em { font-style:normal; font-weight:600 }
.req-done .req, .req-done .reqn { display:none } .req-done .reqd { display:block }
@media screen and (max-width:720px){ .req { grid-template-columns:1fr } .reqd .row { grid-template-columns:1fr; gap:2px } }
/* 사례·상태 스위치(시안용) — split 의 .sw(블록/표)와 이름이 겹쳐 .cases */
.cases { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; align-items:center; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap; z-index:9 }
.cases span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .cases span.on { background:#141414; color:#fff } .cases i { width:1px; height:18px; background:#e6e4df; margin:0 4px }
.vw { display:none } .vw.on { display:block }
@media screen and (max-width:720px){
  .pane { padding:0 16px 20px; border-radius:12px; margin-top:18px } .pane .ph { padding:16px 0 10px } .pane .ph .sum { font-size:13px }
  .ct.ht { grid-template-columns:minmax(0,1fr) 72px } .ct.ht .dt, .ct.ht .org { display:none } .ht .full { display:none } .ht .short, .ht .sub .m { display:inline }
  .aw.ht { grid-template-columns:minmax(0,1fr) 72px } .aw.ht .org, .aw.ht .amt { display:none }
  .hist { grid-template-columns:1fr; gap:12px } .pr.ht { grid-template-columns:minmax(0,1fr) 80px } .pr .ex { display:none }
  .cases { font-size:11.5px; padding:2px; white-space:normal; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px } .cases span { padding:5px 8px } .cases i { display:none }
  .head .meta .st { display:inline-block; margin-top:4px }
}
"""

JS = r"""
document.querySelectorAll('.sheet .tr').forEach(t => t.addEventListener('click', () => t.nextElementSibling.classList.toggle('on')));
if (matchMedia('(max-width:720px)').matches) document.querySelectorAll('details.side').forEach(d => d.open = false);
function openSearch(){ document.body.classList.add('st-search'); const i = document.querySelector('.vw.on .box input'); i.value = ''; i.focus(); }
function closeSearch(){ document.body.classList.remove('st-search'); }
document.querySelectorAll('.req').forEach(f => f.addEventListener('submit', () => f.closest('.none-reco').classList.add('req-done')));
document.querySelectorAll('.sw-co').forEach(a => a.onclick = e => { e.preventDefault(); openSearch(); });
document.querySelectorAll('.rc .esc').forEach(a => a.onclick = e => { e.preventDefault(); closeSearch(); });
addEventListener('keydown', e => { if (e.key === 'Escape') closeSearch(); });
const sw = document.querySelector('.cases');
sw.querySelectorAll('[data-c]').forEach(s => s.onclick = () => { document.querySelectorAll('.vw').forEach(v => v.classList.toggle('on', v.dataset.c === s.dataset.c));
  sw.querySelectorAll('[data-c]').forEach(x => x.classList.toggle('on', x === s)); location.hash = s.dataset.c; });
sw.querySelectorAll('[data-st]').forEach(s => s.onclick = () => { document.body.classList.remove('st-email', 'st-calc'); if (s.dataset.st !== 'guest') document.body.classList.add('st-' + s.dataset.st);
  sw.querySelectorAll('[data-st]').forEach(x => x.classList.toggle('on', x === s)); });
if (location.hash.length === 2) { const s = sw.querySelector(`[data-c="${location.hash.slice(1)}"]`); if (s) s.click(); }
"""


def won_full(v):
    return f'<span class="full">{int(float(v)):,}원</span><span class="short">{won_short(v)}</span>' if v else "—"


def won_short(v):
    v = int(float(v or 0))
    if v >= 100_000_000: return f"{v / 100_000_000:,.1f}억".replace(".0억", "억")
    return f"{v // 10_000:,}만" if v else "—"


def mask(b):
    """운영 maskBizrno 와 같은 규칙 — 137-XX-X4567. results-final 의 124-81-***** 보다 덜 드러낸다(README §12)."""
    b = "".join(ch for ch in (b or "") if ch.isdigit())
    return f"{b[:3]}-XX-X{b[7:]}" if len(b) == 10 else "—"


def ymd(s):
    return f"{s[:4]}.{s[5:7]}.{s[8:10]}" if s else "—"


def head(d):
    co, prof = d["company"], d["profile"]
    n_ind = len(prof["industries"][0] + prof["industries"][1]); n_prd = len(prof["products"][0] + prof["products"][1])
    st = ""
    if co["biz_status_cd"] == "03": st = f'<span class="st">국세청 폐업{" · " + ymd(co["biz_closed_dt"]) if co["biz_closed_dt"] else ""}</span>'
    elif co["biz_status_cd"] == "02": st = '<span class="st gray">휴업</span>'
    if co["is_restricted"]: st += '<span class="st">부정당 제재 중</span>'
    meta = (f'<span>{esc(rgn_base(co["rgn_nm"])) or "<span class=dim>소재지 미등록</span>"}</span><span>등록업종 {n_ind}</span>'
            f'<span>공급물품 {n_prd if n_prd else "없음"}</span>' + (f'<span>{esc(co["corp_bsns_div_nm"])}</span>' if co["corp_bsns_div_nm"] else "")
            + f'<span>기준일 {TODAY.isoformat()}</span>{st}')
    search = (f'<div class="search"><div class="box"><input type="text" autocomplete="off" spellcheck="false" placeholder="회사명 · 사업자등록번호 · 업종 또는 품목"><button class="go" type="button"><span class="t">찾기</span></button></div>'
              f'<div class="rc"><span class="k">최근 조회</span><a href="#">{esc(co["corp_nm"])}</a><a class="esc" href="#">취소 · Esc</a></div></div>')
    return (f'<div class="head"><h1>{esc(co["corp_nm"])}<small>{mask(co["bizrno"])}</small><a class="sw-co" href="#">다른 회사</a></h1>'
            f'<div class="meta">{meta}</div>{search}</div>')


def side_col(d):
    """결과 페이지 side() 와 같은 칸이되 실제 값으로 — 공급물품 목록, 종업원·개업, 사업자 상태."""
    co, prof = d["company"], d["profile"]
    rep, rest = prof["industries"]; names = {x.split("(")[0] for x in rep}
    seen, lis = set(), [f'<li class="rep">{esc(n)}</li>' for n in sorted(names)]
    for x in rest:
        n = x.split("(")[0]
        if n in names or n in seen: continue
        seen.add(n); lis.append(f"<li>{esc(n)}</li>")
    prep, prest = prof["products"]; plis = "".join(f'<li class="{"rep" if i < len(prep) else ""}">{esc(p)}</li>' for i, p in enumerate(prep + prest))
    inds = f"<ul>{''.join(lis)}</ul>" if lis else '<div class="txt"><span class="dim">등록 없음</span> — 업종 허용 공고 판정 불가</div>'
    prods = f"<ul>{plis}</ul>" if plis else '<div class="txt"><span class="dim">등록 없음</span> — 물품 공고 추천에는 등록 필요</div>'
    status = {"03": f'국세청 폐업{" · " + ymd(co["biz_closed_dt"]) if co["biz_closed_dt"] else ""}', "02": "휴업"}.get(co["biz_status_cd"], "계속사업자")
    status += " · 부정당 제재 중" if co["is_restricted"] else " · 제재 없음"
    facts = []
    if co["emp_count"]: facts.append(f"종업원 {co['emp_count']}명")
    if co["opng_dt"]: facts.append(f"개업 {co['opng_dt'][:4]}년")
    if co["mnfctr_div_nm"]: facts.append(esc(co["mnfctr_div_nm"]))
    rgn = f'본사 <b>{esc(rgn_base(co["rgn_nm"]))}</b><br><span class="dim">제한 공고가 적은 단위(시·도 또는 시·군·구)까지 판정</span>' if co["rgn_nm"] else '<span class="dim">소재지 미등록</span> — 지역 제한 공고 판정 불가'
    return (f'<details class="side" open><summary><span class="k">회사 정보 <span class="h o">펼치기</span><span class="h c">접기</span></span></summary>'
            f'<div class="sec"><span class="k">등록업종 {len(rep) + len(rest)}</span>{inds}</div>'
            f'<div class="sec"><span class="k">공급물품{" " + str(len(prep) + len(prest)) if plis else ""}</span>{prods}</div>'
            f'<div class="sec"><span class="k">지역</span><div class="txt">{rgn}</div></div>'
            f'<div class="sec"><span class="k">면허</span><div class="txt">공고 요구 면허 그룹마다 등록업종 중 하나 포함 시 통과</div></div>'
            f'<div class="sec"><span class="k">규모</span><div class="txt"><span class="dim">미입력</span> — 소기업·중소기업 제한 공고 판정 기준</div></div>'
            f'<div class="sec"><span class="k">사업자 상태</span><div class="txt">{status}' + (f'<br><span class="dim">{" · ".join(facts)}</span>' if facts else "") + '</div></div>'
            f'<div class="act"><a class="bt dark" href="#">확인</a><a class="bt txt" href="#"><u>수정 요청</u></a></div>'
            f'<span class="mute">나라장터 업체정보 · {ymd(co["updated"])} 갱신</span></details>')


def reco_pane(d):
    co, prof, reco, f = d["company"], d["profile"], d["reco"], d["funnel"]
    if co["biz_status_cd"] == "03":
        body = (f'<div class="none-reco"><b>국세청 기준 폐업 사업자 — 공고를 추천하지 않습니다</b>'
                f'폐업일 {ymd(co["biz_closed_dt"])}. 사업자 상태가 바뀌면 다음 갱신(매일 05:00)부터 다시 추천합니다. 재개업 또는 정보 오류는 수정 요청으로 접수합니다.'
                f'<div class="acts"><a class="bt" href="#">수정 요청</a></div></div>')
    elif not reco:
        # 분석 요청(승우님 2026-10-17 "벡터·이력 안 잡히는 데는 요청") — 막다른 '수정 요청' 대신 주요 사업·품목 한 줄 + 이메일.
        # 즉시: 입력한 설명으로 키워드 추천. 저장: 설명을 회사에 묶어 다음 회사명 검색부터 바로 표시. 재조회 약속은 안 한다 —
        # 나라장터에 업종이 있는 회사는 자동 등록 잡(매시)이 요청 없이 풀고, C 는 나라장터에도 업종이 없어 재조회로 못 푸는 회사다(2026-10-17 실측 30일 16곳).
        body = (f'<div class="none-reco"><b>추천 기준이 없는 회사입니다</b>'
                f'나라장터 업체정보에 등록업종·공급물품이 없고 수주 이력도 없어 참가 자격과 적합도를 판정할 수 없습니다. 이 회사 담당자는 아래에서 분석을 요청합니다.'
                f'<form class="req" onsubmit="return false"><label><span class="k">주요 사업 · 취급 품목</span><input type="text" placeholder="예: 학교 급식 식자재 납품, 정수기 임대"></label>'
                f'<label><span class="k">이메일</span><input type="email" placeholder="you@company.co.kr"></label><button class="bt dark" type="submit">분석 요청</button></form>'
                f'<div class="reqn">요청 즉시 입력한 설명 기준의 공고를 보여드리고, 설명은 이 회사에 저장되어 다음 검색부터 바로 표시됩니다. 이메일은 설명 수정·삭제 요청 확인용. 비밀번호 없음.</div>'
                f'<div class="reqd"><b>분석 요청 접수 · {TODAY.isoformat()} 14:02</b>'
                f'<div class="row"><span class="k">지금</span><span>입력한 설명 기준 <a href="#">공고 12건 보기</a> — 참가 자격 판정 없음</span></div>'
                f'<div class="row"><span class="k">저장됨</span><span>이 회사명으로 다시 검색하면 설명 기준 추천이 바로 표시. 수정·삭제는 <em>you@company.co.kr</em>로 확인 후 반영</span></div>'
                f'<div class="row"><span class="k">참가 자격 판정</span><span>나라장터 업체등록(업종·물품) 후 가능. 등록되면 다음 갱신부터 회사 기준 추천으로 전환</span></div></div></div>')
    else:
        res = reco["results"]
        prof_full = dict(prof, names=set(), terms=set(), codes=set())
        trs = [trow(i, r, prof_full, i == 1) for i, r in enumerate(res, 1)]
        body = (f'<div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b><i>적합 순</i></span></div>'
                f'<div class="calc"><b>참가 자격이 있는 공고를 선별하고 있습니다</b>회사 모드 평균 2초, 길면 10초. 끝나면 이 자리에 표가 들어옵니다.</div>'
                f'<div class="okline"><b>이메일 등록 완료</b> · 전체 결과 공개</div>{ZERO}'
                f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>'
                f'{"".join(trs[:5])}{gate(len(res))}<div class="fade">{"".join(trs[5:])}</div></div></div>')
        return f'<div class="res"><div class="cols">{side_col(d)}{body}</div></div>'
    return f'<div class="res"><div class="cols">{side_col(d)}<div class="main">{body}</div></div></div>'


def chain_line(d):
    reco, f = d["reco"], d["funnel"]
    if not reco: return ""
    return chain(f, reco, reco["results"])


def contracts_pane(d):
    s, cts = d["contract_summary"], d["contracts"]
    if not s["n"]: return ""
    rows = "".join(f'<div class="ct ht"><span class="dt">{ymd(str(c["cntrct_cncls_date"]))}</span><span class="t">{esc(c["cntrct_nm"])}<span class="sub"><span class="m">{esc(c["dmnd_instt_nm"] or c["cntrct_instt_nm"] or "")}{" · " if c["cntrct_cncls_mthd_nm"] else ""}</span>{esc(c["cntrct_cncls_mthd_nm"] or "")}</span></span><span class="org">{esc(c["dmnd_instt_nm"] or c["cntrct_instt_nm"] or "—")}</span>'
                   f'<span class="r">{won_full(c["cntrct_amt"])}</span></div>' for c in cts)
    top = " · ".join(esc(t) for t in s["top_instt"][:3])
    more = f'<span class="more">최근 {len(cts)}건 표시 · <a href="#">전체 {s["n"]}건</a></span>' if s["n"] > len(cts) else ""
    return (f'<div class="pane"><div class="ph"><h2>수주 이력<small>계약 {s["n"]}건 · {ymd(str(s["first"]))} ~ {ymd(str(s["last"]))}</small></h2>'
            f'<div class="sum"><span>누적 <b>{won_short(s["total"])}</b></span>' + (f'<span>주요 발주기관 {top}</span>' if top else "") + '</div></div>'
            f'<div class="ct ht th"><span class="dt">계약일</span><span>사업명 · 계약 방식</span><span class="org">발주기관</span><span class="r">계약금액</span></div>{rows}{more}</div>')


def awards_pane(d):
    aws = [a for a in d["awards"] if a["is_winner"]]
    if not aws: return ""
    rates = sorted(float(a["bid_rate"]) for a in aws if a["bid_rate"] is not None)
    n_part = d["n_participations"]; n_win = len(aws)
    avg = sum(rates) / len(rates) if rates else None
    summ = [f'<span>입찰 참가 <b>{n_part}건</b> 중 낙찰 <b>{n_win}건</b></span>'] if n_part > n_win else [f'<span>낙찰 <b>{n_win}건</b></span>']
    summ.append(f'<span>낙찰 총액 <b>{won_short(sum(int(a["bid_amt"] or 0) for a in aws))}</b></span>')
    hist = ""
    if len(rates) >= 3:
        edges = [(0, 60), (60, 65), (65, 70), (70, 75), (75, 80), (80, 85), (85, 90), (90, 95), (95, 101)]
        cnt = [sum(1 for r in rates if lo <= r < hi) for lo, hi in edges]; mx = max(cnt)
        bars = "".join(f'<div class="b {"z" if not c else ""}"><em>{c or ""}</em><i style="height:{max(2, c / mx * 100) if c else 2:.0f}%"></i></div>' for c in cnt)
        # 평균 위치 — 첫 칸(<60)은 폭 하나로 두고 60~100 을 8칸에 선형
        pos = (1 + (min(max(avg, 60), 100) - 60) / 40 * 8) / 9 * 100
        axis = "".join(f"<span>{l}</span>" for l in ["<60", "60", "65", "70", "75", "80", "85", "90", "95+"])
        hist = (f'<div class="hist"><div><span class="k">평균 투찰률</span><div class="big">{avg:.1f}%<small>{len(rates)}건 기준</small></div>'
                f'<div class="rng">범위 <b>{rates[0]:.1f}%</b> ~ <b>{rates[-1]:.1f}%</b></div></div>'
                f'<div><div class="bars">{bars}<span class="avg" style="left:{pos:.1f}%"></span></div><div class="axis">{axis}</div></div>'
                f'<div class="note">투찰률 = 낙찰가 ÷ 추정가. 5% 단위 건수, 주황 선은 평균. 낮을수록 가격 경쟁이 센 시장.</div></div>')
    elif rates:
        summ.insert(1, f'<span>평균 투찰률 <b>{avg:.1f}%</b> ({len(rates)}건 기준)</span>')
    rows = ""
    for a in aws[:10]:
        nm = f'<a href="#">{esc(a["bid_ntce_nm"])}</a>' if a["bid_ntce_nm"] else f'<span class="dim">{esc(a["bid_ntce_no"])}</span><span class="sub">공고 원문 미수집</span>'
        sub = f'<span class="sub"><span class="m">{esc(a["dmnd_instt_nm"] or "")}{" · " if a["openg_date"] else ""}</span>{"개찰 " + ymd(str(a["openg_date"])) if a["openg_date"] else ""}</span>' if a["bid_ntce_nm"] else ""
        rate = f'<span class="r rate">{float(a["bid_rate"]):.1f}%</span>' if a["bid_rate"] is not None else '<span class="r rate none">—</span>'
        rows += f'<div class="aw ht"><span class="t">{nm}{sub}</span><span class="org">{esc(a["dmnd_instt_nm"] or "—")}</span><span class="r amt">{won_full(a["bid_amt"])}</span>{rate}</div>'
    more = f'<span class="more">최근 {min(10, n_win)}건 표시 · <a href="#">전체 {n_win}건</a></span>' if n_win > 10 else ""
    peers = ""
    if d["peers"]:
        prs = "".join(f'<div class="pr ht"><span class="t">{esc(p["corp_nm"])}<span class="sub">{mask(p["bizrno"])}</span></span>'
                      f'<span class="n">{p["encounter_count"]}건</span><span class="ex">{esc((p["sample_notice_names"] or [""])[0])}</span></div>' for p in d["peers"][:6])
        peers = (f'<div class="ph" style="margin-top:8px"><h2>같은 시장에서 낙찰받는 회사<small>이 회사의 낙찰 공고와 유사한 공고의 낙찰자</small></h2></div>'
                 f'<div class="pr ht th"><span>회사</span><span class="r">유사 공고 낙찰</span><span class="ex">예시 공고</span></div>{prs}')
    return (f'<div class="pane"><div class="ph"><h2>낙찰<small>최근 {min(10, n_win)}건</small></h2><div class="sum">{"".join(summ)}</div></div>{hist}'
            f'<div class="aw ht th"><span>공고 · 개찰일</span><span class="org">발주기관</span><span class="r amt">낙찰가</span><span class="r">투찰률</span></div>{rows}{more}{peers}</div>')


def view(key, d):
    return (f'<div class="vw" data-c="{key}">{head(d)}{chain_line(d)}{reco_pane(d)}{contracts_pane(d)}{awards_pane(d)}</div>')


def page(data):
    vws = "".join(view(k, data[k]) for k, _, _ in CASES)
    labels = {"a": "A 표준", "b": "B 이력 많음", "c": "C 벡터·이력 없음", "d": "D 폐업"}
    sw = ('<div class="cases">' + "".join(f'<span data-c="{k}" class="{"on" if k == "a" else ""}">{labels[k]}</span>' for k, _, _ in CASES) +
          '<i></i><span data-st="guest" class="on">비로그인</span><span data-st="email">이메일 뒤</span><span data-st="calc">계산 중</span></div>')
    foot = (f'<div class="foot">회사 페이지 최종 시안 — 결과 페이지 문법(판·두 단 표·5건 게이트·주황은 선·공문 톤) + 수주 이력·낙찰 판. 머리 장면 없음(계산이 안 걸리면 안 보여준다). '
            f'회사·계약·낙찰·유사 낙찰자는 {TODAY.isoformat()} 기준 실제 DB 행. A 의 추천은 results-final 과 같은 data/sample.json, B 는 같은 날 recommend() 결과.</div>')
    body = f'<div class="wrap">{nav().replace("<b>추천</b>", "<span>추천</span>")}{vws}{foot}</div>{sw}'
    html = (f'<!doctype html><html lang="ko" class="v-panel"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 회사</title>{FONT}'
            f'<style>{CSS}</style></head><body class="done">{body}<script>{JS}</script></body></html>')
    return html.replace('<div class="vw" data-c="a">', '<div class="vw on" data-c="a">', 1)


BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일로 전부 보기", "해드려요", "골라드려요", "예요", "에요"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in p.read_text(encoding="utf-8")
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
        txt = pg.evaluate("[...document.querySelectorAll('.vw')].map(v => v.innerText).join('\\n')")
        bad = [w for w in BANNED if w in txt]; assert not bad, bad
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e), v = document.querySelector('.vw.on'); return { bg: cs(document.body).backgroundColor, canvas: document.querySelectorAll('canvas').length,
            panel: cs(v.querySelector('.res .cols')).backgroundColor, panes: v.querySelectorAll('.pane').length, sticky: cs(v.querySelector('.side')).position, rule: cs(v.querySelector('.head')).borderBottomColor,
            tr: v.querySelectorAll('.sheet .tr').length, fade: v.querySelectorAll('.fade .tr').length, gate: cs(v.querySelector('.gateline')).display, nums: [...v.querySelectorAll('.chain b')].map(e => e.textContent),
            chainH: v.querySelector('.chain').getBoundingClientRect().height, resOp: cs(v.querySelector('.res')).opacity, ct: v.querySelectorAll('.ct.ht:not(.th)').length, aw: v.querySelectorAll('.aw.ht:not(.th)').length } }""")
        assert s["bg"] == "rgb(250, 249, 247)" and s["canvas"] == 0 and s["panel"] == "rgb(255, 255, 255)" and s["panes"] == 2 and s["sticky"] == "sticky" and s["rule"] == "rgb(20, 20, 20)", s
        assert s["tr"] == 12 and s["fade"] == 7 and s["gate"] != "none" and s["nums"][-1] == "12" and s["chainH"] > 30 and s["resOp"] == "1" and s["ct"] == 7 and s["aw"] == 5, s
        pg.screenshot(path=str(out / "_shot_cfinal_a_guest.png"), full_page=True)
        pg.click('.cases [data-st="email"]'); pg.wait_for_timeout(300)
        assert pg.evaluate("getComputedStyle(document.querySelector('.vw.on .gateline')).display") == "none"
        pg.click('.cases [data-st="calc"]'); pg.wait_for_timeout(300)
        c = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { sheet: cs(v.querySelector('.sheet')).display, calc: cs(v.querySelector('.calc')).display, num: cs(v.querySelector('.chain b.acc')).color } }""")
        assert c["sheet"] == "none" and c["calc"] == "block" and c["num"] == "rgb(184, 182, 176)", c
        pg.screenshot(path=str(out / "_shot_cfinal_a_calc.png"), full_page=False)
        pg.click('.cases [data-st="guest"]'); pg.click('.cases [data-c="b"]'); pg.wait_for_timeout(400)
        bb = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { hist: !!v.querySelector('.hist'), bars: v.querySelectorAll('.bars .b').length, avg: cs(v.querySelector('.bars .avg')).backgroundColor,
            peers: v.querySelectorAll('.pr.ht:not(.th)').length, prods: v.querySelectorAll('.side .sec:nth-child(3) li').length, tr: v.querySelectorAll('.sheet .tr').length, more: v.querySelectorAll('.more').length } }""")
        assert bb["hist"] and bb["bars"] == 9 and bb["avg"] == "rgb(249, 115, 22)" and bb["peers"] >= 2 and bb["prods"] >= 1 and bb["tr"] == 12 and bb["more"] == 2, bb
        pg.screenshot(path=str(out / "_shot_cfinal_b_guest.png"), full_page=True)
        pg.click('.cases [data-c="c"]'); pg.wait_for_timeout(300)
        cc = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { none: !!v.querySelector('.none-reco'), sheet: v.querySelectorAll('.sheet').length, panes: v.querySelectorAll('.pane').length, chain: v.querySelectorAll('.chain').length } }""")
        assert cc["none"] and cc["sheet"] == 0 and cc["panes"] == 0 and cc["chain"] == 0, cc
        pg.screenshot(path=str(out / "_shot_cfinal_c.png"), full_page=True)
        pg.click('.vw.on .req .bt'); pg.wait_for_timeout(200)   # 분석 요청 → 접수 상태
        rq = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { form: cs(v.querySelector('.req')).display, done: cs(v.querySelector('.reqd')).display, rows: v.querySelectorAll('.reqd .row').length } }""")
        assert rq["form"] == "none" and rq["done"] == "block" and rq["rows"] == 3, rq
        pg.screenshot(path=str(out / "_shot_cfinal_c_req.png"), full_page=True)
        pg.click('.cases [data-c="d"]'); pg.wait_for_timeout(300)
        dd = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); const st = v.querySelector('.head .st'); return { st: st && st.textContent, rule: st && cs(st).borderLeftColor, none: !!v.querySelector('.none-reco') } }""")
        assert dd["st"] and dd["st"].startswith("국세청 폐업") and dd["rule"] == "rgb(249, 115, 22)" and dd["none"], dd
        pg.screenshot(path=str(out / "_shot_cfinal_d.png"), full_page=True)
        pg.click('.cases [data-c="a"]'); pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        m = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { open: v.querySelector('details.side').open, cols: getComputedStyle(v.querySelector('.cols')).gridTemplateColumns.split(' ').length,
            overflow: document.documentElement.scrollWidth > 390, dt: getComputedStyle(v.querySelector('.ct.ht .dt')).display } }""")
        assert m["open"] is False and m["cols"] == 1 and not m["overflow"] and m["dt"] == "none", m
        pg.screenshot(path=str(out / "_shot_cfinal_390.png"), full_page=True)
        b.close()
    print("ok A: panes 2, rows 12 (5 + gate + 7), chain", s["nums"], "| B: hist 9 bars, peers", bb["peers"], "| C none-reco | D closed | 390 one column; banned 0; canvas 0")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    if sys.argv[1:2] == ["--data"]:
        write_data(sys.argv[2]); sys.exit()
    src, out = Path(sys.argv[1]), sys.argv[2]
    data = {k: json.load(open(src / f"company_{k}.json", encoding="utf-8")) for k, _, _ in CASES}
    # A 의 추천은 results-final 과 같은 표본을 쓴다 — 두 시안의 숫자·공고가 어긋나지 않게
    data["a"]["reco"] = json.load(open(src / "sample.json", encoding="utf-8")); data["a"]["funnel"] = json.load(open(src / "funnel.json"))
    open(out, "w", encoding="utf-8", newline="\n").write(page(data))
    print("written", out)

"""공고 상세 페이지 시안 3안 — 같은 실제 공고 3건 × (비로그인 / 회사 확인됨) 을 세 가지 순서로.
  verdict : 제목 바로 아래 '참가 자격' 판정 밴드를 크게. 참가 자격 → 과업 → 조건 → 단계 → 기관.
  brief   : 좁은 단. 문서 요약을 리드 문단으로 가장 크게 — 우리만 가진 것이 먼저. 자격은 한 줄 띠.
  rail    : 2단. 오른쪽 고정 레일에 마감·자격·수치가 늘 붙어 있고, 본문은 과업 → 조건 → 단계 → 기관.
공고 3건은 실제 DB 행이다: 조건 많고 낙찰·계약까지 끝난 건 / 인사이트·사전규격 없는 빈약한 건 / 정정 3차.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_notice.py ../docs/design/prototypes/
"""
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, dleft, TODAY  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

# 시안에 쓰는 실제 공고 — (번호, 차수, 키, 왜 골랐나)
NOTICES = [
    ("R26BK01729372", "000", "full", "필수 조건 8개 · 개찰 8사 · 계약 체결까지 끝난 건"),
    ("R26BK01772872", "000", "thin", "첨부문서 인사이트 없음 · 사전규격 없음 · 지역·업종 제한만 있는 건"),
    ("R26BK01765318", "003", "amend", "정정 3차 · 마감이 당겨진 건 · 일정에 납품기한까지 있는 건"),
]
COMPANY = "416-81-43839"  # 용산건설(주) — 보성군 복내면. 공고 B 발주지와 같은 면.
VER_COLS = [("bid_ntce_nm", "제목"), ("bid_clse_date", "마감"), ("openg_date", "개찰"),
            ("presmpt_prce", "추정가"), ("asign_bdgt_amt", "배정예산"), ("prtcpt_psbl_rgn_nm", "지역"),
            ("bidprc_psbl_indstryty_nm", "업종"), ("cntrct_cncls_mthd_nm", "계약방식"),
            ("bidwinr_dcsn_mthd_nm", "낙찰방법")]
N_COLS = ("bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,dmnd_instt_nm,ntce_instt_nm,bid_ntce_date,"
          "bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,bidprc_psbl_indstryty_nm,prtcpt_psbl_rgn_nm,"
          "cntrct_cncls_mthd_nm,bidwinr_dcsn_mthd_nm,rgn_lmt_yn,indstryty_lmt_yn,bid_ntce_url,attachments")


# ---------------------------------------------------------------- 데이터
def fetch(conn, no, od):
    n = dict(zip(N_COLS.split(","), conn.execute(
        f"select {N_COLS} from bid_notices where bid_ntce_no=%s and bid_ntce_ord=%s", (no, od)).fetchone()))
    ins = conn.execute("select summary,scope,requirements,evaluation,schedule,keywords from bid_notice_insights"
                       " where bid_ntce_no=%s and bid_ntce_ord=%s", (no, od)).fetchone()
    insight = dict(zip(("summary", "scope", "requirements", "evaluation", "schedule", "keywords"), ins)) if ins else None
    vcols = ",".join(c for c, _ in VER_COLS)
    vers = [dict(zip(["bid_ntce_ord", "bid_ntce_date"] + [c for c, _ in VER_COLS], r)) for r in conn.execute(
        f"select bid_ntce_ord,bid_ntce_date,{vcols} from bid_notices where bid_ntce_no=%s order by bid_ntce_ord", (no,))]
    inst = n["dmnd_instt_nm"] or n["ntce_instt_nm"]
    cnt, med = conn.execute("select count(*), percentile_disc(0.5) within group (order by cntrct_amt)"
                            " from contracts where dmnd_instt_nm=%s", (inst,)).fetchone()
    return {
        "n": n, "insight": insight, "versions": vers,
        "awards": conn.execute("select openg_rank,corp_nm,bid_amt,bid_rate,is_winner from award_results"
                               " where bid_ntce_no=%s order by openg_rank", (no,)).fetchall(),
        "contracts": conn.execute("select cntrct_nm,cntrct_cncls_date,cntrct_amt,rprsnt_corp_nm,rprsnt_corp_bizrno"
                                  " from contracts where bid_ntce_no=%s order by cntrct_cncls_date desc", (no,)).fetchall(),
        "pre_specs": conn.execute("select bf_spec_rgst_no,prdct_clsfc_no_nm,rgst_dt,opnin_rgst_clse_dt,asign_bdgt_amt"
                                  " from pre_specs where bid_ntce_no_list like %s", (f"%{no}%",)).fetchall(),
        "order_plans": conn.execute("select biz_nm,order_year,order_mnth,sum_order_amt from order_plans"
                                    " where bid_ntce_no_list like %s", (f"%{no}%",)).fetchall(),
        "inst": inst, "inst_n": cnt, "inst_med": med,
        "inst_top": conn.execute("select rprsnt_corp_nm, count(*) from contracts where dmnd_instt_nm=%s"
                                 " group by 1 order by 2 desc limit 3", (inst,)).fetchall(),
        "mine_inst": conn.execute("select count(*), max(cntrct_cncls_date), max(cntrct_nm) from contracts"
                                  " where dmnd_instt_nm=%s and rprsnt_corp_bizrno_norm=%s",
                                  (inst, COMPANY.replace("-", ""))).fetchone(),
    }


KIND_KO = {"region": "지역", "license": "면허", "certification": "증명", "performance": "실적",
           "company_size": "기업 규모", "other": "기타", "experience": "경력", "equipment": "장비",
           "personnel": "인력", "financial": "재무"}


def wn(v):
    """금액은 페이지 전체에서 원 단위 그대로. 억/만 줄임과 섞으면 같은 수가 두 모양으로 보인다."""
    return f"{int(v):,}원" if v else "—"


def ro(s):
    """받침에 따라 '으로/로' — 'ㄹ' 받침과 받침 없음은 '로'."""
    c = s.strip()[-1:]
    if not c or not ("가" <= c <= "힣"):
        return "으로"
    return "로" if (ord(c) - 0xAC00) % 28 in (0, 8) else "으로"


def mask(biz):
    d = "".join(c for c in str(biz or "") if c.isdigit())
    return f"{d[:3]}-XX-X{d[7:]}" if len(d) == 10 else "—"


def dstr(v):
    return f"{v.month}.{v.day:02d}" if isinstance(v, date) else "—"


def amendments(vers):
    """차수 사이에 바뀐 항목만. notice-diff.ts 와 같은 비교 컬럼."""
    out = []
    for prev, cur in zip(vers, vers[1:]):
        ch = [(lab, prev[c], cur[c]) for c, lab in VER_COLS if str(prev[c]) != str(cur[c])]
        out.append({"ord": cur["bid_ntce_ord"], "date": cur["bid_ntce_date"], "changes": ch})
    return out[::-1]


def reqs(d):
    rs = (d["insight"] or {}).get("requirements") or []
    return [r for r in rs if r.get("mandatory")], [r for r in rs if not r.get("mandatory")]


def _sv(s, k):
    # 모델이 문자열 "null" 을 넣어 두는 칸이 있다 — 없는 것으로 본다.
    v = s.get(k)
    return str(v).strip() if v and str(v).strip().lower() != "null" else None


def sched_rows(d):
    """일정을 표가 아니라 문장으로 — '착수 계약체결일 / 기간 180일' 은 읽는 사람이 다시 조립해야 한다.
    조합이 되면 한 줄('계약 체결일부터 180일'), 안 되면 남은 항목만 (라벨, 값) 으로."""
    s = (d["insight"] or {}).get("schedule") or {}
    start, end, dur, dl = (_sv(s, k) for k in ("start", "end", "duration", "delivery_deadline"))
    out = []
    if start and dur:
        out.append(("기간", f"{start}부터 {dur}"))
    elif start and end:
        out.append(("기간", f"{start} ~ {end}"))
    elif dur:
        out.append(("기간", dur))
    else:
        if start:
            out.append(("착수", start))
        if end:
            out.append(("종료", end))
    if dl and dl != end:
        out.append(("납품기한", dl))
    return out


def eval_text(d):
    """낙찰 방식 한 줄. 기술 비율이 없으면 '가격 100' 은 방식 이름과 중복이라 빼고,
    제안 발표는 '없음' 이 기본이므로 있을 때만 말한다. note 는 비고로 따로."""
    e = (d["insight"] or {}).get("evaluation") or {}
    out = []
    if e.get("method"):
        out.append(esc(e["method"]))
    if e.get("technical_pct") is not None and e.get("price_pct") is not None:
        out.append(f'기술 {e["technical_pct"]}% : 가격 {e["price_pct"]}%')
    if e.get("presentation"):
        out.append("제안 발표 있음")
    return " · ".join(out) or '<span class="mute">문서에서 낙찰 방식을 찾지 못했습니다</span>', esc(e.get("note") or "")


# ---------------------------------------------------------------- 자격 판정
def qual(d, prof, login=True):
    """공고 필드의 제한만 판정한다 — (상태, 항목, 내용, 근거, 레일용 짧은 판정, 레일용 짧은 원문).
    문서에서 읽은 면허·증명은 판정하지 않으므로 여기 들어오지 않는다(qual_docs 로 분리).
    비로그인(login=False)이면 판정 대신 공고에 적힌 것을 그대로만 보여 준다."""
    n = d["n"]
    mine = prof["industries"][0] + prof["industries"][1]
    allowed = [a.strip() for a in (n["bidprc_psbl_indstryty_nm"] or "").split(",") if a.strip()]
    rows = []
    if not allowed:
        rows.append(("s-ok", "허용 업종", "제한 없음", "공고 업종제한 N", "제한 없음", "제한 없음"))
    else:
        hit = [a for a in allowed if any(m.split("(")[0] in a or a.split("(")[0] in m for m in mine)]
        txt = ", ".join(esc(a) for a in allowed[:3]) + (f' <span class="mute">외 {len(allowed) - 3}</span>' if len(allowed) > 3 else "")
        rows.append(("s-ok" if hit else "s-warn", "허용 업종", txt,
                     f'등록업종 {len(mine)}개 중 {esc(hit[0])} 보유' if hit
                     else f"등록업종 {len(mine)}개 중 일치 없음",
                     f'{esc(hit[0])} 보유' if hit else f"등록업종 {len(mine)}개에 없음",
                     f"{len(allowed)}개 업종으로 제한"))
    rgn = (n["prtcpt_psbl_rgn_nm"] or "").strip()
    mysido = (prof["rgn"] or "").split()[0] if prof["rgn"] else ""
    mygun = (prof["rgn"] or "").split()[1] if len((prof["rgn"] or "").split()) > 1 else ""
    if not rgn:
        rows.append(("s-ok", "지역 제한", "제한 없음", "공고 지역제한 N", "제한 없음", "제한 없음"))
    else:
        parts = [p.strip() for p in rgn.split(",")]
        ok = any(mygun and mygun in p for p in parts) or (not mygun and any(mysido and mysido in p for p in parts))
        rows.append(("s-ok" if ok else "s-warn", "지역 제한",
                     ", ".join(esc(p) for p in parts[:2]) + (f' <span class="mute">외 {len(parts) - 2}</span>' if len(parts) > 2 else ""),
                     f'본사 {esc(prof["rgn"])}',
                     f'본사 {esc(mygun or mysido)} ' + ("포함" if ok else "제외"),
                     esc(parts[0]) + (f" 외 {len(parts) - 1}곳{ro('곳')} 제한" if len(parts) > 1
                                      else f"{ro(parts[0])} 제한")))
    return rows


def qual_docs(d):
    """문서에서 읽은 면허·증명 — 판정하지 않는다. 서류로만 증빙되는 층.
    (이전 시안의 '4건 중 등록업종으로 확인되는 것 0건' 은 text.split()[0] 부분일치라 양방향으로 틀릴 수 있었다.
     시스템이 아는 것은 '문서에 이런 요구가 적혀 있다'까지다 — 거기까지만 말한다.)"""
    man, opt = reqs(d)
    if not d["insight"]:
        att = len(d["n"]["attachments"] or [])
        return 0, f'첨부 {att}건을 아직 읽지 않았습니다', "어떤 조건이 적혀 있는지 모릅니다"
    if not man and not opt:
        return 0, "문서에 참가 조건 없음", "첨부문서에서 읽음"
    # 아래 목록과 숫자가 맞아야 한다 — 면허·증명만 세면 '6건' 머리에 8줄 목록이 붙는다.
    kinds = {}
    for r in man:
        kinds[r.get("kind")] = kinds.get(r.get("kind"), 0) + 1
    txt = " · ".join(f'{KIND_KO.get(k, k)} {v}' for k, v in kinds.items()) + (f' · 우대 {len(opt)}' if opt else "")
    return len(man) + len(opt), txt, "서류로 증빙 — 자동 판정하지 않습니다"


def qual_block(d, prof, login, gate=True):
    """판정층(공고 제한) + 증빙층(문서 면허·증명)을 한 표에 쌓는다.
    gate=False 는 레일 안내가 이미 같은 말을 하는 rail 레이아웃용."""
    rows = qual(d, prof, login)
    dn, dtxt, dbas = qual_docs(d)
    if login:
        body = "".join(
            f'<div class="qr {st}"><span class="qk">{lab}</span><span class="qv">{txt}</span>'
            f'<span class="qb">{bas}</span></div>' for st, lab, txt, bas, _s, _r in rows)
        foot = (f'<div class="qf">판정 근거는 나라장터 업체정보(등록업종 {len(prof["industries"][0] + prof["industries"][1])}개 · '
                f'본사 {esc(prof["rgn"])}, 10.14 갱신)와 공고의 제한 필드뿐입니다. '
                f'서류로만 증빙되는 조건은 판정하지 않습니다. <a href="#">기준 보기</a></div>')
        return f'<div class="qual">{body}{doc_rows(d)}{docs_tier(dn, dtxt, dbas)}{foot}</div>'
    raw = "".join(
        f'<div class="qr raw"><span class="qk">{lab}</span><span class="qv">{txt}</span>'
        f'<span class="qb">공고에 적힌 제한</span></div>' for st, lab, txt, bas, _s, _r in rows)
    gate_html = ('<div class="qf gate"><b>회사명을 넣으면 위 두 줄에 판정이 붙습니다.</b> '
            '등록업종·본사 소재지를 나라장터 업체정보에서 읽어 허용업종·지역 제한과 맞춰 보고, '
            '이 기관과의 과거 계약 건수도 같이 나옵니다. '
            '<span class="in"><span>회사명 또는 사업자번호</span><span class="bt dark">자격 확인</span></span></div>')
    return f'<div class="qual">{raw}{doc_rows(d)}{docs_tier(dn, dtxt, dbas)}{gate_html if gate else ""}</div>'


def docs_tier(dn, dtxt, dbas):
    """문서 조건 머리줄 — 바로 아래 목록(cond_block)의 제목 역할. 숫자는 목록 줄 수와 같다."""
    lab = f"문서에 적힌 조건 {dn}" if dn else "문서에 적힌 조건"
    return (f'<div class="qr s-doc"><span class="qk">{lab}</span>'
            f'<span class="qv">{dtxt}</span><span class="qb">{dbas}</span></div>')


def doc_rows(d):
    """낙찰 방식·일정 — 공고 제한과 같은 표에 두 줄로. 따로 옆에 두면 허공에 뜬다."""
    if not d["insight"]:
        return ""
    et, note = eval_text(d)
    sr = sched_rows(d)
    ev = et + (f' <span class="dim">— {note}</span>' if note else "")
    sc = " · ".join(f"{esc(v)}" if lab == "기간" else f"{lab} {esc(v)}" for lab, v in sr) \
        or '<span class="dim">문서에서 찾지 못함 — 마감·개찰일은 위에</span>'
    return (f'<div class="qr s-info"><span class="qk">낙찰 방식</span><span class="qv">{ev}</span><span class="qb">첨부문서에서 읽음</span></div>'
            f'<div class="qr s-info"><span class="qk">일정</span><span class="qv">{sc}</span><span class="qb">첨부문서에서 읽음</span></div>')


# ---------------------------------------------------------------- 블록
def stages(d):
    n = d["n"]
    ps, op = d["pre_specs"], d["order_plans"]
    cl = n["bid_clse_date"]
    done_cl = isinstance(cl, date) and cl <= TODAY
    st = [("발주 계획", f'{op[0][1]}.{op[0][2]} 예정' if op else "", bool(op)),
          ("사전 규격", dstr(ps[0][2].date() if ps and hasattr(ps[0][2], "date") else None) if ps else "", bool(ps)),
          ("의견 수렴", "", False),
          ("입찰 공고", dstr(n["bid_ntce_date"]), True),
          ("낙찰", f'{len(d["awards"])}사 개찰' if d["awards"] else "", bool(d["awards"])),
          ("계약 체결", dstr(d["contracts"][0][1]) if d["contracts"] else "", bool(d["contracts"]))]
    cells = "".join(f'<div class="sg {"on" if on else ""}"><span class="sn">{lab}</span>'
                    f'<span class="sd">{sub or ("기록 없음" if not on else "")}</span></div>' for lab, sub, on in st)
    dl = ""
    if isinstance(cl, date):
        k, _ = dleft(cl)
        dl = (f'<span class="sclose {"hot" if 0 <= k <= 7 else ""}">마감 {cl.month}.{cl.day:02d}'
              f'{f" · D-{k}" if k >= 0 else " · 지남"}</span>')
    return (f'<div class="stages">{cells}</div>'
            f'<div class="sfoot">{dl}<span class="mute">발주계획·사전규격은 나라장터가 공고와 번호로 이어 준 것만 표시합니다 — '
            f'{"이 공고는 연결된 기록이 없습니다" if not (ps or op) else "연결된 기록이 있습니다"}.</span></div>'
            + ("" if done_cl else ""))


def clse_move(d):
    """정정으로 마감일이 움직였나 — (처음, 지금, 당겨짐). 레일 D-day 바로 아래에 띄운다.
    마감이 당겨지는 건 돈이고, 나라장터에서는 차수를 하나씩 열어 눈으로 비교해야 보인다."""
    v = d["versions"]
    mv = [(p["bid_clse_date"], c["bid_clse_date"]) for p, c in zip(v, v[1:])
          if str(p["bid_clse_date"]) != str(c["bid_clse_date"])]
    if not mv:
        return None
    first, last = mv[0][0], mv[-1][1]
    if not (isinstance(first, date) and isinstance(last, date)):
        return None
    return first, last, last < first


def lifecycle(d):
    """진행 단계 + 개찰·계약을 한 섹션으로 합친다.
    사전규격→계약은 거의 모든 공고에서 비어 있다(README: 빈 칸이 기본값) — 그래서 빈 상태를 기본 모양으로 만든다.
    한 줄로 지금 단계와 앞으로 들어올 것을 말하고, 6단계 표는 펼쳐서 볼 수 있게 남긴다. 숨기지는 않는다."""
    if d["awards"] or d["contracts"]:
        return stages(d) + result_block(d)
    n, cl = d["n"], d["n"]["bid_clse_date"]
    k = dleft(cl)[0] if isinstance(cl, date) else None
    if k is not None and k >= 0:
        now = f'지금은 <b>입찰 공고</b> 단계 — 마감까지 {k}일, 개찰 {dstr(n["openg_date"])}.'
    else:
        now = '지금은 <b>입찰 공고</b> 단계 — 마감은 지났고 개찰 결과가 아직 수집되지 않았습니다.'
    link = "연결된 사전규격·발주계획 기록 없음" if not (d["pre_specs"] or d["order_plans"]) else "사전규격·발주계획 기록 있음"
    return (f'<details class="lc"><summary><span class="lcn">{now}</span>'
            f'<span class="lcx">개찰 뒤 참가 업체·투찰금액·낙찰률, 계약 체결 뒤 계약 상대·금액이 이 자리에 들어옵니다. '
            f'{link}.</span><span class="lcm">6단계 전체</span></summary>'
            f'<div class="lcb">{stages(d)}</div></details>')


def work_block(d):
    ins = d["insight"]
    if not ins or not ins.get("summary"):
        att = len(d["n"]["attachments"] or [])
        return ('<div class="empty"><b>첨부문서를 아직 읽지 않았습니다.</b>'
                f'<p>이 공고의 첨부 {att}건은 분석 대기 중입니다. 과업 내용·범위·필수 조건은 원문에서 확인하세요. '
                f'문서를 읽은 공고에서는 이 자리에 요약과 범위, 필수/우대 조건이 들어갑니다.</p>'
                f'<span class="mute">첨부문서 분석은 공고 전체가 아니라 제안요청서·공고문이 붙은 건에만 돌아갑니다.</span></div>')
    scope = "".join(f"<li>{esc(s)}</li>" for s in (ins.get("scope") or []))
    kw = " · ".join(esc(k) for k in (ins.get("keywords") or [])[:6])
    return (f'<p class="sum">{esc(ins["summary"])}</p>'
            + (f'<ul class="scope">{scope}</ul>' if scope else "")
            + (f'<div class="kw"><span class="k">문서에서 뽑은 말</span>{kw}</div>' if kw else "")
            + '<div class="src mute">첨부 제안요청서·공고문을 읽어 정리한 것입니다. 원문 확인은 필수.</div>')


def cond_block(d):
    man, opt = reqs(d)
    if not d["insight"]:
        return '<div class="empty small">첨부문서를 아직 읽지 않아 문서에서 읽은 조건이 없습니다. 공고 필드의 제한은 위에 있습니다.</div>'
    if not man and not opt:
        return '<div class="empty small">문서에 명시된 참가 조건을 찾지 못했습니다.</div>'
    def kd(r):
        k = r.get("kind") or ""
        return esc(KIND_KO.get(k, k))

    li = "".join(f'<li><span class="rq">필수</span>{esc(r["text"])}<span class="rk">{kd(r)}</span></li>' for r in man)
    li += "".join(f'<li><span class="rq o">우대</span>{esc(r["text"])}<span class="rk">{kd(r)}</span></li>' for r in opt)
    return f'<div class="cond"><ul class="reqs">{li}</ul></div>'


def inst_block(d, login):
    cnt, med, top = d["inst_n"], d["inst_med"], d["inst_top"]
    mine_n, mine_d, mine_nm = d["mine_inst"]
    if not cnt:
        return ('<div class="empty"><b>이 기관의 계약 기록이 아직 없습니다.</b>'
                f'<p>발주기관은 9,923곳이고 상위 100곳으로도 전체 공고의 20%뿐입니다. '
                f'<b>{esc(d["inst"])}</b>은 그 바깥이라 과거 경향을 말할 근거가 없습니다. 없는 경향을 지어내지 않습니다.</p>'
                '<span class="mute">근거: contracts 테이블의 수요기관명 일치 건수 0</span></div>')
    share = top[0][1] / cnt if top else 0
    lines = (f'<div class="ist"><div><b>{cnt:,}</b><span>수집된 계약</span></div>'
             f'<div><b>{wn(med)}</b><span>계약금액 중앙값</span></div>'
             f'<div><b>{top[0][1]}건</b><span>가장 많이 받은 곳 — {esc(top[0][0])} ({share * 100:.1f}%)</span></div></div>'
             f'<div class="src mute">근거: 수요기관명이 <b>{esc(d["inst"])}</b>와 같은 계약 {cnt:,}건. '
             f'기관명이 바뀌거나 사업소가 따로 잡히면 이 수가 쪼개집니다. <a href="#">계약 목록</a></div>')
    if login and mine_n:
        lines += (f'<div class="imine">이 기관과 <b>{mine_n}건</b> 계약했습니다 — 가장 최근 {dstr(mine_d)} '
                  f'{esc((mine_nm or "")[:34])}. <span class="mute">근거: 계약 대표사 사업자번호 일치</span></div>')
    elif login:
        lines += '<div class="imine mute">이 기관과의 계약 기록은 없습니다.</div>'
    return lines


def result_block(d):
    aw, ct = d["awards"], d["contracts"]
    if not aw and not ct:
        n, cl = d["n"], d["n"]["bid_clse_date"]
        k = dleft(cl)[0] if isinstance(cl, date) else None
        return ('<div class="empty small">아직 개찰 전입니다.'
                + (f' 개찰은 {dstr(n["openg_date"])}, 마감까지 {k}일.' if k is not None and k >= 0 else "")
                + ' 개찰 뒤에는 참가 업체·투찰금액·낙찰률이 이 자리에 들어옵니다.</div>')
    out = ""
    if aw:
        rows = "".join(
            f'<tr class="{"win" if w else ""}"><td>{r}{"<i>낙찰</i>" if w else ""}</td><td>{esc(nm)}</td>'
            f'<td class="r">{wn(amt)}</td><td class="r">{f"{float(rt):.2f}%" if rt else "—"}</td></tr>'
            for r, nm, amt, rt, w in aw[:10])
        out += (f'<div class="scrollx"><table class="aw"><thead><tr><th>순위</th><th>업체</th>'
                f'<th class="r">투찰금액</th><th class="r">낙찰률</th></tr></thead><tbody>{rows}</tbody></table></div>'
                f'<div class="src mute">{len(aw)}사 참가{" · 상위 10사만" if len(aw) > 10 else ""}. 나라장터 개찰결과 그대로.</div>')
    for nm, cd, amt, corp, biz in ct:
        out += (f'<div class="ctr"><span class="k">계약 체결</span><b>{esc(corp)}</b>'
                f'<span class="mute">{mask(biz)}</span><span>{dstr(cd)}</span><b class="r">{wn(amt)}</b></div>')
    return out


def amend_block(d):
    am = amendments(d["versions"])
    if not am:
        return '<div class="empty small">정정 없는 원공고입니다.</div>'
    out = ""
    for a in am:
        ch = ("".join(f'<div class="ch"><span class="chk">{lab}</span>'
                      f'<span class="chb">{esc(str(b)[:40]) or "—"}</span><span class="cha">→ {esc(str(c)[:40])}</span></div>'
                      for lab, b, c in a["changes"])
              or '<div class="ch mute">비교 항목엔 변화 없음 — 본문·서식 변경은 원문에서</div>')
        out += f'<div class="am"><span class="amn">정정 {int(a["ord"])}차</span><span class="mute">{dstr(a["date"])} 공고</span>{ch}</div>'
    return out + ('<div class="src mute">제목·마감·개찰·금액·지역·업종·계약방식을 이전 차수와 비교한 결과입니다. '
                  '본문 문구 변경은 잡지 못합니다.</div>')


def heads(d):
    n = d["n"]
    cl = n["bid_clse_date"]
    k = dleft(cl)[0] if isinstance(cl, date) else None
    dd = (f'<span class="dd {"hot" if k is not None and 0 <= k <= 7 else ""}">'
          f'{f"D-{k}" if k is not None and k >= 0 else "마감 지남"}</span>')
    ord_i = int(n["bid_ntce_ord"])
    tags = (f'<span class="tg">{esc(n["bsns_div_nm"])}</span>'
            + (f'<span class="tg am">정정 {ord_i}차</span>' if ord_i else "")
            + f'<span class="no">{esc(n["bid_ntce_no"])}</span>{dd}')
    meta = " ".join(f"<span>{v}</span>" for v in [
        f'<b>{esc(n["dmnd_instt_nm"] or n["ntce_instt_nm"])}</b>',
        f'마감 {dstr(cl)}', f'개찰 {dstr(n["openg_date"])}', esc(n["cntrct_cncls_mthd_nm"] or ""),
        esc(n["bidwinr_dcsn_mthd_nm"] or "")] if v)
    nums = "".join(f'<div class="nb"><span class="k">{lab}</span><b>{v}</b></div>' for lab, v in [
        ("추정가", wn(n["presmpt_prce"])), ("배정 예산", wn(n["asign_bdgt_amt"])), ("개찰일", dstr(n["openg_date"]))])
    att = "".join(f'<li><a href="{esc(f["url"])}">{esc(f.get("name") or f"첨부 {f["seq"]}")}</a></li>'
                  for f in (n["attachments"] or [])[:6])
    acts = (f'<a class="bt dark" href="{esc(n["bid_ntce_url"])}">나라장터 원문</a><a class="bt" href="#">검토</a>')
    return {"tags": tags, "h1": esc(n["bid_ntce_nm"]), "meta": meta, "nums": nums, "dd": dd,
            "att": f'<div class="att"><span class="k">첨부 {len(n["attachments"] or [])}</span><ul>{att}</ul></div>' if att else "",
            "acts": acts, "k": k}


# ---------------------------------------------------------------- CSS
CSS = r"""
body { background:#fdfcfa }
/* BASE 의 .mute(#8f8f8b)는 이 배경에서 4.5:1 에 못 미친다 — 검증된 회색으로 덮는다 */
.mute { color:#737370 }
.vw { display:none } .vw.on { display:block }
.reveal { opacity:0; transform:translateY(8px); transition:opacity .5s ease var(--d,0s), transform .5s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .in .reveal { opacity:1; transform:none }
@media (prefers-reduced-motion: reduce) { .reveal { transition:none !important; opacity:1 !important; transform:none !important } }
.sec { padding:30px 0 0; border-top:1px solid #141414; margin-top:34px }
.sec > h2 { margin:0 0 4px; font-size:19px; letter-spacing:-0.02em; font-weight:650 }
.sec > .lead { margin:0 0 18px; font-size:13px; color:#6b6b67; line-height:1.6; max-width:640px }
.scrollx { overflow-x:auto; max-width:100% }
/* 머리 — SHEET_CSS 의 .head 는 아래 괘선을 긋는다. 여기선 첫 .sec 의 괘선과 겹치므로 지운다 */
.head { border-bottom:0; padding:28px 0 0 }
.tags { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:12px }
.tg { font-weight:600; letter-spacing:.02em } .tg.am { color:#e8431b } .tags .no { color:#737370; font-size:11.5px }
.dd { font-weight:700; letter-spacing:-0.01em } .dd.hot { color:#e8431b }
h1.t { margin:12px 0 0; font-size:30px; letter-spacing:-0.035em; font-weight:650; line-height:1.3; max-width:34ch; word-break:keep-all }
.meta { margin-top:12px; font-size:13.5px; color:#55554f } .meta span + span::before { content:"·"; margin:0 8px; color:#737370 }
.nums { display:flex; gap:0; margin-top:22px; border-top:1px solid #e6e4df } .nb { padding:12px 28px 12px 0; border-right:1px solid #e6e4df; padding-right:28px; margin-right:28px }
.nb:last-child { border-right:0 } .nb b { display:block; margin-top:5px; font-size:22px; letter-spacing:-0.025em; font-weight:650 }
.acts { margin-top:20px; display:flex; gap:8px }
.att { margin-top:20px; font-size:13px } .att ul { margin:7px 0 0; padding:0; list-style:none } .att li { padding:2px 0 } .att a { border-bottom:1px solid #d8d6d0 }
/* 참가 자격 */
.qual { border-top:1px solid #141414 }
.qr { display:grid; grid-template-columns:130px minmax(0,1fr) 260px; gap:0 20px; padding:14px 0; border-bottom:1px solid #ececea; align-items:baseline; position:relative }
.qr .qk { font-size:12.5px; color:#55554f; font-weight:600; padding-left:16px }
.qr .qv { font-size:14.5px; line-height:1.5 } .qr .qb { font-size:12px; color:#6b6b67; line-height:1.5 }
.qr.s-ok .qk::before, .qr.s-warn .qk::before, .qr.s-raw .qk::before { position:absolute; left:0; font-weight:700 }
/* ✓ 는 먹, 어긋난 것만 인주 하나 — 색은 먹 4단계 + 인주 하나가 전부다 */
.qr.s-ok .qk::before { content:"✓"; color:#141414 } .qr.s-warn .qk::before { content:"✕"; color:#e8431b }
.qr.s-raw .qk::before { content:"·"; color:#737370 }
.qr.s-doc { background:#faf9f6; margin-top:14px } .qr.s-doc .qk { color:#141414; font-weight:600 } .qr.s-info .qv .dim { color:#6b6b67 } .qr.s-doc .qv { font-size:13.5px; color:#55554f }
.qf { padding:16px 0 0; font-size:12.5px; color:#6b6b67; line-height:1.7; max-width:720px } .qf a { border-bottom:1px solid #d8d6d0; color:#141414 }
.qf.gate { font-size:13.5px; color:#55554f } .qf.gate b { color:#141414; font-weight:650 }
.qf.gate .in { display:flex; gap:6px; margin-top:12px } .qf.gate .in span:first-child { width:260px; height:36px; border:1px solid #e3e1dc; border-radius:8px; background:#fff; display:flex; align-items:center; padding:0 12px; color:#737370; font-size:13px }
/* 과업 */
p.sum { margin:0; font-size:17px; line-height:1.75; letter-spacing:-0.012em; max-width:62ch; word-break:keep-all }
ul.scope { margin:18px 0 0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:0 }
ul.scope li { font-size:13px; color:#333; padding:4px 14px 4px 0; margin-right:14px; border-right:1px solid #e6e4df }
ul.scope li:last-child { border-right:0 }
.kw { margin-top:18px; font-size:13px; color:#55554f } .kw .k { display:inline-block; margin-right:10px }
.src { margin-top:14px; font-size:12px; line-height:1.6 } .src a { border-bottom:1px solid #d8d6d0; color:#141414 } .src b { font-weight:600; color:#55554f }
.empty { border:1px solid #e6e4df; border-radius:6px; padding:18px 20px; background:#faf9f6; max-width:640px }
.empty b { font-size:14.5px; font-weight:650 } .empty p { margin:7px 0 10px; font-size:13.5px; line-height:1.7; color:#55554f } .empty .mute { font-size:12px }
.empty.small { padding:14px 18px; font-size:13.5px; color:#55554f }
/* 조건 */
.cond { display:block }
ul.reqs { margin:0; padding:0; list-style:none } ul.reqs li { display:grid; grid-template-columns:40px minmax(0,1fr) 92px; gap:12px; padding:9px 0; border-bottom:1px solid #ececea; font-size:14px; align-items:baseline }
.rq { font-size:10.5px; font-weight:700; letter-spacing:.04em; color:#e8431b } .rq.o { color:#737370 }
.rk { font-size:11px; color:#737370; text-align:right }
/* 단계 */
.stages { display:grid; grid-template-columns:repeat(6,1fr); gap:0 }
.sg { padding:12px 10px 12px 0; border-top:2px solid #ececea } .sg.on { border-top-color:#141414 }
.sg .sn { display:block; font-size:12.5px; color:#737370; font-weight:600 } .sg.on .sn { color:#141414 }
.sg .sd { display:block; margin-top:3px; font-size:12px; color:#737370 }
.sfoot { margin-top:14px; font-size:12px; color:#6b6b67; display:flex; gap:16px; flex-wrap:wrap; align-items:baseline }
.sclose { font-weight:650; color:#141414; font-size:13px } .sclose.hot { color:#e8431b }
/* 진행 단계 — 빈 상태가 기본 모양. 접힌 한 줄이 지금 단계와 앞으로 들어올 것을 말한다 */
.lc { border-top:1px solid #e6e4df; padding-top:14px } .lc > summary { list-style:none; cursor:pointer; display:block; max-width:640px }
.lc > summary::-webkit-details-marker { display:none }
.lc .lcn { display:block; font-size:14.5px; line-height:1.6 } .lc .lcn b { font-weight:650 }
.lc .lcx { display:block; margin-top:6px; font-size:12.5px; color:#6b6b67; line-height:1.65 }
.lc .lcm { display:inline-block; margin-top:9px; font-size:12px; color:#141414; border-bottom:1px solid #d8d6d0 }
.lc .lcm::after { content:" ↓"; color:#737370 } .lc[open] .lcm::after { content:" ↑" }
.lc .lcb { margin-top:20px } .lc:hover .lcm { border-bottom-color:#141414 }
/* 기관 */
.ist { display:flex; gap:0; border-top:1px solid #e6e4df; flex-wrap:wrap }
.ist > div { padding:14px 28px 14px 0; margin-right:28px; border-right:1px solid #e6e4df } .ist > div:last-child { border-right:0; margin-right:0 }
.ist b { display:block; font-size:24px; letter-spacing:-0.03em; font-weight:650 } .ist span { display:block; margin-top:4px; font-size:12.5px; color:#55554f }
.imine { margin-top:14px; padding:13px 16px; background:#faf9f6; border-left:2px solid #141414; font-size:13.5px; line-height:1.6 }
/* 결과 */
table.aw { width:100%; min-width:520px; border-collapse:collapse; font-size:13.5px }
table.aw th { text-align:left; font-size:11px; letter-spacing:.06em; color:#737370; font-weight:600; padding:8px 10px 8px 0; border-bottom:1px solid #141414 }
table.aw td { padding:10px 10px 10px 0; border-bottom:1px solid #ececea } table.aw .r { text-align:right }
table.aw tr.win td { font-weight:600 } table.aw i { font-style:normal; margin-left:8px; font-size:10.5px; font-weight:700; color:#e8431b; letter-spacing:.04em }
.ctr { display:flex; gap:14px; align-items:baseline; padding:14px 0; border-bottom:1px solid #ececea; font-size:13.5px; flex-wrap:wrap }
.ctr .k { width:72px } .ctr b { font-weight:650 } .ctr b.r { margin-left:auto }
/* 정정 */
.am { padding:14px 0; border-bottom:1px solid #ececea } .amn { font-size:13px; font-weight:650; color:#e8431b; margin-right:10px }
.ch { display:grid; grid-template-columns:72px minmax(0,1fr) minmax(0,1fr); gap:0 14px; margin-top:7px; font-size:13px; align-items:baseline }
.chk { color:#55554f; font-weight:600; font-size:12px } .chb { color:#737370; text-decoration:line-through } .cha { font-weight:600 }
/* 전환 스위치 */
.sw { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:50; display:flex; gap:14px; align-items:center; padding:7px 10px; background:#141414; color:#c9c9c4; border-radius:999px; box-shadow:0 20px 40px -20px rgba(0,0,0,.6); font-size:12.5px; max-width:94vw; overflow-x:auto }
.sw .g { display:flex; gap:3px } .sw span[data-n], .sw span[data-s] { padding:5px 10px; border-radius:999px; cursor:pointer; white-space:nowrap }
.sw .on { background:#fff; color:#141414; font-weight:600 } .sw .sep { width:1px; height:16px; background:#3a3a37 }
.foot { margin-top:40px; padding-top:18px; border-top:1px solid #e6e4df; font-size:12px; color:#737370; line-height:1.7 }
@media screen and (max-width:1140px) { .wrap, .wrap2 { width:auto !important; padding-left:20px; padding-right:20px } }
@media screen and (max-width:820px) {
  .qr { grid-template-columns:minmax(0,1fr); gap:4px } .qr .qb { padding-left:16px }
  .stages { grid-template-columns:repeat(2,1fr) } h1.t { font-size:24px } .nums { flex-wrap:wrap }
}
"""

L2_CSS = r"""
body { background:#faf9f7 } .wrap { width:720px; margin:0 auto; padding:0 0 130px }
h1.t { font-size:28px; max-width:30ch }
p.sum { font-size:19px; line-height:1.8 }
.qr { grid-template-columns:118px minmax(0,1fr); gap:0 18px } .qr .qb { grid-column:2; padding-left:0; margin-top:3px }
.stages { grid-template-columns:repeat(3,1fr) }
.ist > div { padding-right:20px; margin-right:20px }
"""

L3_CSS = r"""
.wrap2 { width:1180px; margin:0 auto; padding:0 0 130px }
.cols { display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:56px; align-items:start }
.rail { position:sticky; top:22px; border-top:1px solid #141414; padding-top:18px }
.rail .rdd { font-size:46px; letter-spacing:-0.045em; font-weight:700; line-height:1 } .rail .rdd.hot { color:#e8431b }
.rail .rsub { margin-top:6px; font-size:12.5px; color:#55554f }
.rail .rn { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid #ececea; font-size:13px } .rail .rn:first-of-type { border-top:1px solid #ececea } .rail .rn b { font-weight:650 }
/* 레일은 판정만 — 조건 전체 목록·근거는 본문 '참가 조건'이 갖는다 */
.rail .rqwrap { margin-top:22px }
.rail .rv { margin-top:8px; font-size:15px; letter-spacing:-0.02em; font-weight:650; line-height:1.45 }
.rail .rv.no { color:#e8431b } .rail .rv.yes::before { content:"✓ "; color:#141414 }
.rail .rqr { display:flex; gap:8px; padding:7px 0 7px 11px; border-left:2px solid #d8d6d0; margin-top:6px; font-size:12.5px; line-height:1.5 }
.rail .rqr.s-ok { border-left-color:#141414 } .rail .rqr.s-warn { border-left-color:#e8431b }
.rail .rqr span:first-child { width:62px; color:#55554f; flex:none; font-weight:600 }
.rail .rdoc { margin-top:12px; padding-top:11px; border-top:1px solid #ececea; font-size:12px; color:#6b6b67; line-height:1.6 }
.rail .rdoc b { color:#55554f; font-weight:600 }
.rail .rmore { display:inline-block; margin-top:12px; font-size:12.5px; border-bottom:1px solid #d8d6d0 }
.rail .rmore::after { content:" ↓"; color:#737370 }
/* 마감이 움직인 공고 — 나라장터에서는 차수를 열어 눈으로 비교해야 보인다. 놓치면 돈이다 */
.rail .ramd { display:block; margin-top:14px; padding:11px 12px; border-left:2px solid #e8431b; background:#fdf3f0; font-size:12.5px; line-height:1.55; color:#141414 }
.rail .ramd b { color:#e8431b; font-weight:700 } .rail .ramd span { display:block; margin-top:4px; font-size:11.5px; color:#6b6b67 }
.rail .racts { margin-top:18px; display:flex; flex-direction:column; gap:7px } .rail .bt { justify-content:center }
.rail .rnote { margin-top:14px; font-size:11.5px; color:#6b6b67; line-height:1.6 }
.rail .rin { margin-top:10px } .rail .rin span:first-child { display:flex; align-items:center; height:34px; border:1px solid #e3e1dc; border-radius:8px; background:#fff; padding:0 11px; color:#737370; font-size:12.5px; margin-bottom:6px }
.cols .sec:first-child { border-top:0; margin-top:0; padding-top:0 }
/* 좁은 화면에선 고정할 자리가 없다 — 레일을 본문 위로 올려 한 번은 보이게 한다(고정은 포기) */
@media screen and (max-width:980px) {
  .cols { grid-template-columns:minmax(0,1fr); gap:30px } .rail { position:static; order:-1 }
  .rail .rdd { font-size:34px } .rail .racts { flex-direction:row } .rail .racts .bt { flex:1 }
}
"""

JS = r"""
requestAnimationFrame(()=>requestAnimationFrame(()=>document.body.classList.add('in')));
const S={n:'full',s:'guest'};
function sync(){document.querySelectorAll('.vw').forEach(v=>v.classList.toggle('on',v.dataset.n===S.n&&v.dataset.s===S.s));
  document.querySelectorAll('.sw [data-n]').forEach(e=>e.classList.toggle('on',e.dataset.n===S.n));
  document.querySelectorAll('.sw [data-s]').forEach(e=>e.classList.toggle('on',e.dataset.s===S.s));}
document.querySelectorAll('.sw [data-n]').forEach(e=>e.onclick=()=>{S.n=e.dataset.n;sync()});
document.querySelectorAll('.sw [data-s]').forEach(e=>e.onclick=()=>{S.s=e.dataset.s;sync()});
sync();
"""


# ---------------------------------------------------------------- 레이아웃
def sec(title, lead, body, anchor=""):
    aid = ' id="%s"' % anchor if anchor else ""
    return (f'<div class="sec reveal"{aid}><h2>{title}</h2>'
            + (f'<p class="lead">{lead}</p>' if lead else "") + body + "</div>")


def l1(d, prof, login):
    """verdict — 자격 판정이 제목 바로 아래."""
    h = heads(d)
    return (f'<div class="head reveal"><div class="tags">{h["tags"]}</div><h1 class="t">{h["h1"]}</h1>'
            f'<div class="meta">{h["meta"]}</div><div class="nums">{h["nums"]}</div><div class="acts">{h["acts"]}</div></div>'
            + sec("참가 자격", "공고에 적힌 제한과, 문서에서 읽어낸 요구 조건을 나눠 둡니다.", qual_block(d, prof, login))
            + sec("과업 내용", "첨부문서를 읽어 정리한 과업 내용과 범위.", work_block(d))
            + sec("참가 조건", "필수와 우대를 나누고, 낙찰 방식·일정을 옆에.", cond_block(d))
            + sec("진행 단계", "", stages(d))
            + sec("발주기관 이력", "과거 계약 기록으로만 말합니다.", inst_block(d, login))
            + sec("개찰·계약", "", result_block(d))
            + sec("정정 이력", "", amend_block(d))
            + h["att"])


def l2(d, prof, login):
    """brief — 문서 요약이 리드."""
    h = heads(d)
    n = d["n"]
    return (f'<div class="head reveal"><div class="tags">{h["tags"]}</div><h1 class="t">{h["h1"]}</h1>'
            f'<div class="meta">{h["meta"]}</div></div>'
            + sec("과업 내용", "다른 데는 없는 것 — 첨부 제안요청서·공고문을 읽어 정리했습니다.", work_block(d))
            + sec("참가 자격", "", qual_block(d, prof, login))
            + sec("참가 조건", "", cond_block(d))
            + sec("일정·진행", "", f'<div class="nums">{h["nums"]}</div>' + stages(d))
            + sec("발주기관 이력", "", inst_block(d, login))
            + sec("개찰·계약", "", result_block(d))
            + sec("정정 이력", "", amend_block(d))
            + f'<div class="sec reveal"><h2>원문</h2><div class="acts">{h["acts"]}</div>{h["att"]}</div>')


def l3(d, prof, login):
    """rail — 오른쪽 고정 레일은 '낼 수 있나'의 판정만 갖는다(늘 화면에 있으므로 짧게).
    조건 전체 목록·근거·기준은 본문 '참가 조건'이 갖는다 — 같은 말을 두 번 하지 않는다."""
    h = heads(d)
    n = d["n"]
    rows = qual(d, prof, login)
    dn, dtxt, _ = qual_docs(d)
    # 같은 파일에 6개 뷰가 들어 있으므로 앵커는 뷰마다 달라야 한다
    aid = f'{n["bid_ntce_no"]}-{"l" if login else "g"}'
    if login:
        bad = [r for r in rows if r[0] == "s-warn"]
        if all(r[2] == "제한 없음" for r in rows):
            head, hcls = "공고에 업종·지역 제한 없음", ""
        elif bad:
            head = (f"공고 제한 {len(rows)}건 모두 불충족" if len(bad) == len(rows)
                    else f"공고 제한 {len(rows)}건 중 {len(bad)}건 불충족")
            hcls = "no"
            # ponytail: 불충족 사유가 여러 개여도 레일은 한 줄로만 말한다 — 느낌표를 줄 세우면 오류 화면이 된다
        else:
            head, hcls = f"공고 제한 {len(rows)}건 충족", "yes"
        rq = "".join(f'<div class="rqr {st}"><span>{lab}</span><span>{short}</span></div>'
                     for st, lab, _t, _b, short, _r in rows)
        rdoc = (f'<div class="rdoc">그 밖에 문서에 적힌 <b>{dtxt}</b> — 서류로 증빙합니다. 판정하지 않습니다.</div>'
                if dn else f'<div class="rdoc">{dtxt}</div>')
        rin = ""
    else:
        head, hcls = "공고에 적힌 제한", ""
        rq = "".join(f'<div class="rqr raw"><span>{lab}</span><span>{rawshort}</span></div>'
                     for _st, lab, _t, _b, _s, rawshort in rows)
        rdoc = f'<div class="rdoc">{dtxt}</div>'
        rin = '<div class="rin"><span>회사명 또는 사업자번호</span><span class="bt dark">자격 확인</span></div>'
    rn = "".join(f'<div class="rn"><span>{lab}</span><b>{v}</b></div>' for lab, v in [
        ("추정가", wn(n["presmpt_prce"])), ("배정 예산", wn(n["asign_bdgt_amt"])),
        ("계약방식", esc(n["cntrct_cncls_mthd_nm"] or "—")),
        ("낙찰방법", esc(n["bidwinr_dcsn_mthd_nm"] or "—"))])
    k = h["k"]
    mv = clse_move(d)
    ramd = ""
    if mv:
        o, c, pulled = mv
        ramd = (f'<a class="ramd" href="#amend">마감이 {dstr(o)} → <b>{dstr(c)}</b> 로 '
                f'{"당겨졌습니다" if pulled else "늦춰졌습니다"}<span>정정 {int(n["bid_ntce_ord"])}차 · 바뀐 항목 보기</span></a>')
    rail = (f'<div class="rail reveal" style="--d:.1s"><div class="rdd {"hot" if k is not None and 0 <= k <= 7 else ""}">'
            f'{f"D-{k}" if k is not None and k >= 0 else "마감"}</div>'
            f'<div class="rsub">마감 {dstr(n["bid_clse_date"])} · 개찰 {dstr(n["openg_date"])}</div>{ramd}'
            f'{rn}<div class="rqwrap"><span class="k">참가 자격</span>'
            f'<div class="rv {hcls}">{head}</div>{rq}{rdoc}{rin}'
            f'<a class="rmore" href="#cond">조건 전체와 판정 근거</a></div>'
            f'<div class="racts">{h["acts"]}</div>{h["att"]}</div>')
    main = ((sec("정정 이력", "이전 차수와 달라진 항목만. 나라장터에서는 차수를 하나씩 열어 눈으로 비교해야 보입니다.",
                 amend_block(d), aid + "-amend") if amendments(d["versions"]) else "")
            + sec("과업 내용", "첨부문서를 읽어 정리한 과업 내용과 범위.", work_block(d))
            + sec("참가 조건", "공고에 적힌 제한과 첨부문서에서 읽은 조건.",
                  qual_block(d, prof, login, gate=False) + cond_block(d), aid + "-cond")
            + sec("진행 단계", "", lifecycle(d))
            + sec("발주기관 이력", "과거 계약 기록으로만 말합니다.", inst_block(d, login)))
    return (f'<div class="head reveal"><div class="tags">{h["tags"]}</div><h1 class="t">{h["h1"]}</h1>'
            f'<div class="meta">{h["meta"]}</div></div>'
            f'<div class="cols" style="margin-top:30px"><div>{main}</div>{rail}</div>')


LAYOUTS = {
    "notice-verdict.html": ("판정 먼저", "wrap", CSS, l1,
                            "제목 다음이 참가 자격. 참가 자격 → 과업 내용 → 참가 조건 → 진행 단계 → 발주기관 순서."),
    "notice-brief.html": ("브리프", "wrap", CSS + L2_CSS, l2,
                          "좁은 단. 문서 요약을 가장 큰 글로 먼저 — 우리만 가진 것이 입구."),
    "notice-rail.html": ("고정 레일", "wrap2", CSS + L3_CSS, l3,
                         "오른쪽 레일에 마감·자격·수치가 늘 붙어 있고, 본문은 과업부터."),
}


def page(name, data, prof):
    label, wrap, css, fn, note = LAYOUTS[name]
    vws = ""
    for key, _, _ in [(k, 0, 0) for k in ("full", "thin", "amend")]:
        for state in ("guest", "login"):
            vws += (f'<div class="vw" data-n="{key}" data-s="{state}">'
                    f'{fn(data[key], prof, state == "login")}</div>')
    nbtn = "".join(f'<span data-n="{k}">{lab}</span>' for k, lab in
                   (("full", "A 조건 많음·계약까지"), ("thin", "B 빈약"), ("amend", "C 정정 3차")))
    sw = (f'<div class="sw"><div class="g">{nbtn}</div><span class="sep"></span>'
          f'<div class="g"><span data-s="guest">비로그인</span><span data-s="login">회사 확인됨</span></div></div>')
    foot = (f'<div class="foot">시안 "{label}" — {note}<br>'
            f'공고 3건·기관 통계·개찰·계약은 모두 {TODAY.isoformat()} 기준 실제 DB 행입니다. '
            f'회사 확인됨 상태의 회사는 용산건설(주)(전남 보성군 복내면, 등록업종 11)입니다.</div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 공고 상세 — {label}</title>{FONT}<style>{SHEET_CSS}{css}</style></head>'
            f'<body><div class="{wrap}">{nav()}{vws}{foot}</div>{sw}<script>{JS}</script></body></html>')


if __name__ == "__main__":
    outdir = sys.argv[1].rstrip("/\\")
    conn = connect()
    prof = fetch_company_profile(conn, COMPANY.replace("-", ""))
    data = {key: fetch(conn, no, od) for no, od, key, _ in NOTICES}
    for name in LAYOUTS:
        open(f"{outdir}/{name}", "w", encoding="utf-8", newline="\n").write(page(name, data, prof))
        print("written", name)

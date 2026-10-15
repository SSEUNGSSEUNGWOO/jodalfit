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
from gen_results import esc, won, dleft, TODAY  # noqa: E402
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


def sched_rows(d):
    s = (d["insight"] or {}).get("schedule") or {}
    labs = [("start", "착수"), ("end", "종료"), ("duration", "기간"), ("delivery_deadline", "납품기한")]
    # 모델이 문자열 "null" 을 넣어 두는 칸이 있다 — 없는 것으로 본다.
    return [(lab, s[k]) for k, lab in labs if s.get(k) and str(s[k]).strip().lower() != "null"]


def eval_text(d):
    e = (d["insight"] or {}).get("evaluation") or {}
    out = []
    if e.get("method"):
        out.append(esc(e["method"]))
    if e.get("technical_pct") is not None and e.get("price_pct") is not None:
        out.append(f'기술 {e["technical_pct"]} : 가격 {e["price_pct"]}')
    elif e.get("price_pct") is not None:
        out.append(f'가격 {e["price_pct"]}')
    out.append("제안 발표 있음" if e.get("presentation") else "제안 발표 없음")
    return " · ".join(out), esc(e.get("note") or "")


# ---------------------------------------------------------------- 자격 판정
def qual(d, prof, login=True):
    """(상태, 항목, 내용, 근거) — 상태는 ok/warn/raw. 공고 필드상 제한과 문서에서 읽은 요구를 나눠 둔다.
    비로그인(login=False)이면 판정 대신 공고·문서에 적힌 것을 그대로만 보여 준다."""
    n = d["n"]
    mine = prof["industries"][0] + prof["industries"][1]
    allowed = [a.strip() for a in (n["bidprc_psbl_indstryty_nm"] or "").split(",") if a.strip()]
    rows = []
    if not allowed:
        rows.append(("s-ok", "허용 업종", "제한 없음", "공고 업종제한 N"))
    else:
        hit = [a for a in allowed if any(m.split("(")[0] in a or a.split("(")[0] in m for m in mine)]
        txt = ", ".join(esc(a) for a in allowed[:3]) + (f' <span class="mute">외 {len(allowed) - 3}</span>' if len(allowed) > 3 else "")
        rows.append(("s-ok" if hit else "s-warn", "허용 업종", txt,
                     f'등록업종 {len(mine)}개 중 {esc(hit[0])} 보유' if hit
                     else f"등록업종 {len(mine)}개 중 일치 없음"))
    rgn = (n["prtcpt_psbl_rgn_nm"] or "").strip()
    mysido = (prof["rgn"] or "").split()[0] if prof["rgn"] else ""
    mygun = (prof["rgn"] or "").split()[1] if len((prof["rgn"] or "").split()) > 1 else ""
    if not rgn:
        rows.append(("s-ok", "지역 제한", "제한 없음", "공고 지역제한 N"))
    else:
        parts = [p.strip() for p in rgn.split(",")]
        ok = any(mygun and mygun in p for p in parts) or (not mygun and any(mysido and mysido in p for p in parts))
        rows.append(("s-ok" if ok else "s-warn", "지역 제한",
                     ", ".join(esc(p) for p in parts[:2]) + (f' <span class="mute">외 {len(parts) - 2}</span>' if len(parts) > 2 else ""),
                     f'본사 {esc(prof["rgn"])}'))
    man, _ = reqs(d)
    docs = [r for r in man if r.get("kind") in ("license", "certification")]
    if not d["insight"]:
        rows.append(("s-raw", "문서 요구 조건", '<span class="mute">첨부문서를 아직 읽지 않았습니다</span>',
                     f'첨부 {len((n["attachments"] or []))}건 — 분석 대기'))
    elif not docs:
        rows.append(("s-raw", "문서 요구 조건", '<span class="mute">문서에 면허·증명 요구 없음</span>', f"필수 조건 {len(man)}개"))
    elif not login:
        rows.append(("s-raw", "문서 요구 면허·증명",
                     ", ".join(esc(r["text"]) for r in docs[:3])
                     + (f' <span class="mute">외 {len(docs) - 3}</span>' if len(docs) > 3 else ""),
                     "첨부문서에서 읽은 것"))
    else:
        hit = [r for r in docs if any(r["text"].split()[0] in m for m in mine)]
        rows.append(("s-ok" if len(hit) == len(docs) else "s-warn", "문서 요구 면허·증명",
                     f"{len(docs)}건 중 등록업종으로 확인되는 것 {len(hit)}건",
                     "나머지는 서류로만 증빙 — 자동 판정 안 함"))
    return rows


def qual_block(d, prof, login):
    rows = qual(d, prof, login)
    if login:
        body = "".join(
            f'<div class="qr {st}"><span class="qk">{lab}</span><span class="qv">{txt}</span>'
            f'<span class="qb">{bas}</span></div>' for st, lab, txt, bas in rows)
        foot = (f'<div class="qf">판정 근거는 나라장터 업체정보(등록업종 {len(prof["industries"][0] + prof["industries"][1])}개 · '
                f'본사 {esc(prof["rgn"])}, 10.14 갱신)와 공고의 제한 필드뿐입니다. '
                f'서류로만 증빙되는 조건은 판정하지 않습니다. <a href="#">기준 보기</a></div>')
        return f'<div class="qual">{body}{foot}</div>'
    raw = "".join(
        f'<div class="qr raw"><span class="qk">{lab}</span><span class="qv">{txt}</span>'
        f'<span class="qb">{bas if lab.startswith("문서") else "공고에 적힌 제한"}</span></div>'
        for st, lab, txt, bas in rows)
    gate = ('<div class="qf gate"><b>회사명을 넣으면 이 세 줄에 판정이 붙습니다.</b> '
            '등록업종·본사 소재지를 나라장터 업체정보에서 읽어 허용업종·지역 제한과 맞춰 보고, '
            '이 기관과의 과거 계약 건수도 같이 나옵니다. '
            '<span class="in"><span>회사명 또는 사업자번호</span><span class="bt dark">자격 확인</span></span></div>')
    return f'<div class="qual">{raw}{gate}</div>'


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
        return '<div class="empty small">문서 조건이 아직 없습니다. 공고에 적힌 제한(업종·지역)은 위 참가 자격에 있습니다.</div>'
    if not man and not opt:
        return '<div class="empty small">문서에 명시된 참가 조건을 찾지 못했습니다.</div>'
    li = "".join(f'<li><span class="rq">필수</span>{esc(r["text"])}<span class="rk">{esc(r.get("kind") or "")}</span></li>' for r in man)
    li += "".join(f'<li><span class="rq o">우대</span>{esc(r["text"])}<span class="rk">{esc(r.get("kind") or "")}</span></li>' for r in opt)
    et, note = eval_text(d)
    sr = sched_rows(d)
    side = (f'<div class="cs"><span class="k">낙찰 방식</span><div class="cv">{et}</div>'
            + (f'<div class="cn">{note}</div>' if note else "")
            + '<span class="k" style="margin-top:16px">일정</span>'
            + (f'<div class="cv">{"".join(f"<i>{lab}</i>{esc(v)}<br>" for lab, v in sr)}</div>'
               if sr else '<div class="cv mute">문서에서 일정을 찾지 못했습니다 — 마감·개찰일은 위에 있습니다</div>')
            + "</div>")
    return f'<div class="cond"><ul class="reqs">{li}</ul>{side}</div>'


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
             f'<div><b>{won(med)}</b><span>계약금액 중앙값</span></div>'
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
            f'<td class="r">{won(amt)}</td><td class="r">{f"{float(rt):.2f}%" if rt else "—"}</td></tr>'
            for r, nm, amt, rt, w in aw[:10])
        out += (f'<div class="scrollx"><table class="aw"><thead><tr><th>순위</th><th>업체</th>'
                f'<th class="r">투찰금액</th><th class="r">낙찰률</th></tr></thead><tbody>{rows}</tbody></table></div>'
                f'<div class="src mute">{len(aw)}사 참가{" · 상위 10사만" if len(aw) > 10 else ""}. 나라장터 개찰결과 그대로.</div>')
    for nm, cd, amt, corp, biz in ct:
        out += (f'<div class="ctr"><span class="k">계약 체결</span><b>{esc(corp)}</b>'
                f'<span class="mute">{mask(biz)}</span><span>{dstr(cd)}</span><b class="r">{won(amt)}</b></div>')
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
        ("추정가", won(n["presmpt_prce"])), ("배정 예산", won(n["asign_bdgt_amt"])), ("개찰일", dstr(n["openg_date"]))])
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
.qr.s-ok .qk::before { content:"✓"; color:#1f5f3a } .qr.s-warn .qk::before { content:"!"; color:#e8431b } .qr.s-raw .qk::before { content:"·"; color:#737370 }
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
.cond { display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:40px }
ul.reqs { margin:0; padding:0; list-style:none } ul.reqs li { display:grid; grid-template-columns:40px minmax(0,1fr) 92px; gap:12px; padding:9px 0; border-bottom:1px solid #ececea; font-size:14px; align-items:baseline }
.rq { font-size:10.5px; font-weight:700; letter-spacing:.04em; color:#e8431b } .rq.o { color:#737370 }
.rk { font-size:11px; color:#737370; text-align:right }
.cs .k { display:block } .cs .cv { margin-top:7px; font-size:14px; line-height:1.7 } .cs .cv i { display:inline-block; width:62px; font-style:normal; font-size:12px; color:#6b6b67 }
.cs .cn { margin-top:6px; font-size:12.5px; color:#6b6b67 }
/* 단계 */
.stages { display:grid; grid-template-columns:repeat(6,1fr); gap:0 }
.sg { padding:12px 10px 12px 0; border-top:2px solid #ececea } .sg.on { border-top-color:#141414 }
.sg .sn { display:block; font-size:12.5px; color:#737370; font-weight:600 } .sg.on .sn { color:#141414 }
.sg .sd { display:block; margin-top:3px; font-size:12px; color:#737370 }
.sfoot { margin-top:14px; font-size:12px; color:#6b6b67; display:flex; gap:16px; flex-wrap:wrap; align-items:baseline }
.sclose { font-weight:650; color:#141414; font-size:13px } .sclose.hot { color:#e8431b }
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
@media (max-width:1140px) { .wrap, .wrap2 { width:auto !important; padding-left:20px; padding-right:20px } }
@media (max-width:820px) {
  .cond { grid-template-columns:minmax(0,1fr); gap:24px } .qr { grid-template-columns:minmax(0,1fr); gap:4px } .qr .qb { padding-left:16px }
  .stages { grid-template-columns:repeat(2,1fr) } h1.t { font-size:24px } .nums { flex-wrap:wrap }
}
"""

L2_CSS = r"""
body { background:#faf9f7 } .wrap { width:720px; margin:0 auto; padding:0 0 130px }
h1.t { font-size:28px; max-width:30ch }
p.sum { font-size:19px; line-height:1.8 }
.qr { grid-template-columns:118px minmax(0,1fr); gap:0 18px } .qr .qb { grid-column:2; padding-left:0; margin-top:3px }
.cond { grid-template-columns:minmax(0,1fr); gap:26px } .cs { border-top:1px solid #e6e4df; padding-top:18px }
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
.rail .rqwrap { margin-top:20px } .rail .rqr { display:flex; gap:8px; padding:8px 0; border-bottom:1px solid #ececea; font-size:12.5px; line-height:1.5; position:relative; padding-left:16px }
.rail .rqr::before { position:absolute; left:0; top:8px; font-weight:700 }
.rail .rqr.s-ok::before { content:"✓"; color:#1f5f3a } .rail .rqr.s-warn::before { content:"!"; color:#e8431b } .rail .rqr.s-raw::before { content:"·"; color:#737370 }
.rail .rqr span:first-child { width:78px; color:#55554f; flex:none; font-weight:600 }
.rail .racts { margin-top:18px; display:flex; flex-direction:column; gap:7px } .rail .bt { justify-content:center }
.rail .rnote { margin-top:14px; font-size:11.5px; color:#6b6b67; line-height:1.6 }
.rail .rin { margin-top:10px } .rail .rin span:first-child { display:flex; align-items:center; height:34px; border:1px solid #e3e1dc; border-radius:8px; background:#fff; padding:0 11px; color:#737370; font-size:12.5px; margin-bottom:6px }
.cols .sec:first-child { border-top:0; margin-top:0; padding-top:0 }
@media (max-width:980px) { .cols { grid-template-columns:minmax(0,1fr); gap:32px } .rail { position:static } }
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
def sec(title, lead, body):
    return f'<div class="sec reveal"><h2>{title}</h2>' + (f'<p class="lead">{lead}</p>' if lead else "") + body + "</div>"


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
    """rail — 오른쪽 고정 레일에 마감·자격·수치."""
    h = heads(d)
    n = d["n"]
    rows = qual(d, prof, login)
    if login:
        rq = "".join(f'<div class="rqr {st}"><span>{lab}</span><span>{txt}</span></div>' for st, lab, txt, _ in rows)
        rnote = ('<div class="rnote">근거: 나라장터 업체정보(등록업종 '
                 f'{len(prof["industries"][0] + prof["industries"][1])}개 · 본사 {esc(prof["rgn"])}, 10.14) + 공고 제한 필드. '
                 '서류로만 증빙되는 조건은 판정하지 않습니다.</div>')
        rin = ""
    else:
        rq = "".join(f'<div class="rqr raw"><span>{lab}</span><span>{txt}</span></div>' for _, lab, txt, _ in rows)
        rnote = '<div class="rnote">회사명을 넣으면 세 줄에 ✓/확인 필요가 붙고, 이 기관과의 과거 계약 건수도 나옵니다.</div>'
        rin = '<div class="rin"><span>회사명 또는 사업자번호</span><span class="bt dark">자격 확인</span></div>'
    rn = "".join(f'<div class="rn"><span>{lab}</span><b>{v}</b></div>' for lab, v in [
        ("추정가", won(n["presmpt_prce"])), ("배정 예산", won(n["asign_bdgt_amt"])),
        ("개찰일", dstr(n["openg_date"])), ("계약방식", esc(n["cntrct_cncls_mthd_nm"] or "—")),
        ("낙찰방법", esc(n["bidwinr_dcsn_mthd_nm"] or "—"))])
    k = h["k"]
    rail = (f'<div class="rail reveal" style="--d:.1s"><div class="rdd {"hot" if k is not None and 0 <= k <= 7 else ""}">'
            f'{f"D-{k}" if k is not None and k >= 0 else "마감"}</div>'
            f'<div class="rsub">마감 {dstr(n["bid_clse_date"])} · 개찰 {dstr(n["openg_date"])}</div>'
            f'{rn}<div class="rqwrap"><span class="k">참가 자격</span>{rq}{rin}{rnote}</div>'
            f'<div class="racts">{h["acts"]}</div>{h["att"]}</div>')
    main = (sec("과업 내용", "첨부문서를 읽어 정리한 과업 내용과 범위.", work_block(d))
            + sec("참가 조건", "", cond_block(d))
            + sec("진행 단계", "", stages(d))
            + sec("발주기관 이력", "과거 계약 기록으로만 말합니다.", inst_block(d, login))
            + sec("개찰·계약", "", result_block(d))
            + sec("정정 이력", "", amend_block(d)))
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

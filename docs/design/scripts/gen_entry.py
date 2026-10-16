"""검색 입구 시안 3안 — 회사명·사업자번호·하는 일을 한 칸에 받아 결과 페이지(flow.html 머리)로 넘기는 화면.
  line    : 한 줄. 입력 괘선 하나뿐, 치는 대로 그 아래에 목록이 자란다. 재방문 칩은 입력 위 한 줄 글자.
  desk    : 숫자 먼저. "지금 입찰 가능한 N건"이 제목, 그 아래 입력, 그 아래 두 길(회사로 / 하는 일로)이 같은 무게.
            재방문이면 두 길 자리에 최근 회사 카드. 목록은 입력 아래 패널로 뜬다.
  confirm : 두 단계. 고르면 바로 가지 않고 확인 카드(지역·등록업종·수주)를 보여 준 뒤 간다. 재방문은 지난 회사 카드가 미리 차 있다.
세 안 모두 같은 콤보박스(↑↓ Enter Esc, role=combobox/listbox/option, aria-activedescendant)와 같은 실제 행을 쓴다.
상태 전환(빈 입력 / 타이핑 중 / 못 찾음 / 재방문)은 화면 아래 알약으로, 입력란에 직접 쳐도 같은 데이터로 움직인다.

왜 키워드 길이 회사 길과 같은 무게인가 (2026-10-16 실측, search_logs source='user' 7일):
  395건 중 205건(52%)이 회사로 풀리지 않았다 — 163건은 처음부터 키워드 모드, 42건은 회사 모드인데 '회사를 찾을 수 없습니다'.
  친 문자열은 "감리" "주차" "MIS" "ADATA" 같은 낱말·브랜드다. 사람들은 등록된 회사명이 아니라 자기가 하는 일을 친다.
  그래서 입력은 첫 글자부터 두 해석을 같이 보여 준다 — 회사 목록 옆에 "이 말로 공고 찾기" 행이 항상 같이 선다.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_entry.py ../docs/design/prototypes/
"""
import json
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav  # noqa: E402
from jobs.evaluate_recommender import connect  # noqa: E402

# 동명 회사 묶음 — 이름이 같고 사업자번호·지역·업종이 다른 실제 회사들. 치는 글자가 이 안에 있으면 목록이 자란다.
# "신성건설"처럼 법인 표기만 다른 8곳이 전부 수주 이력이 있는 묶음도 넣었다 — 수주 건수만으로는 못 고른다.
COLLISIONS = ["대신네트웍스", "주식회사 한결", "주식회사 다온엔지니어링", "주식회사 신성건설"]
# 7일 로그에서 실제로 쳐진 낱말. 회사명이 아니라 '하는 일'이다. 사람·회사를 가리키는 문자열은 넣지 않는다.
TYPED = ["감리", "주차", "MIS", "ADATA", "태양광", "설계감리", "시각화"]
RETURN_CO = "한종산업개발 주식회사"  # flow.html 의 회사 — 재방문 상태에서 지난번 회사로 쓴다


# ---------------------------------------------------------------- 데이터
def mask(biz):
    """README §12: 137-81-54567 → 137-XX-X4567. 하이픈 없는 10자리도 같은 꼴로."""
    d = "".join(ch for ch in (biz or "") if ch.isdigit())
    return f"{d[:3]}-XX-X{d[-4:]}" if len(d) == 10 else "번호 없음"


def short_rgn(r):
    t = (r or "").split()
    return " ".join(t[:2]) if t else ""


def companies_like(conn, core):
    rows = conn.execute("""
      select distinct on (co.bizrno_norm) co.bizrno, co.corp_nm, co.rgn_nm,
        (select indstryty_nm from company_industries ci where ci.bizrno=co.bizrno and ci.rprsnt_indstryty_yn='Y' and ci.indstryty_nm<>'' limit 1),
        (select count(*) from company_industries ci where ci.bizrno=co.bizrno),
        (select count(*) from contracts k where k.rprsnt_corp_bizrno_norm=co.bizrno_norm)
      from companies co where co.corp_nm ilike %s and co.rgn_nm is not null
      order by co.bizrno_norm, length(co.bizrno) desc""", (f"%{core}%",)).fetchall()
    out = [dict(biz=mask(b), nm=nm, rgn=short_rgn(rgn), rep=rep or "", nind=nind, ncon=ncon) for b, nm, rgn, rep, nind, ncon in rows]
    out.sort(key=lambda r: (-r["ncon"], -r["nind"], r["nm"]))
    return out


def fetch(conn):
    active = conn.execute("select count(*) from bid_notices where bid_clse_date between current_date and current_date + 90").fetchone()[0]
    groups = {}
    for nm in COLLISIONS:
        core = nm.replace("주식회사", "").strip()
        groups[core] = companies_like(conn, core)
    # 로그 낱말의 실제 회사 수 — "감리" 는 수백, "ADATA" 는 0. 목록 머리글 숫자가 이것.
    counts = {w: conn.execute("select count(distinct bizrno_norm) from companies where corp_nm ilike %s", (f"%{w}%",)).fetchone()[0] for w in TYPED}
    # 재방문 상태의 최근 회사 2곳: flow.html 의 회사 + 동명 묶음에서 하나 (브라우저 localStorage 에 심는다)
    ret = companies_like(conn, RETURN_CO)[:1] + groups[COLLISIONS[0]][1:2]
    # 7일 사용자 검색의 미해결 비율 — 이 시안의 전제. 바뀌면 각주 숫자도 같이 바뀐다.
    tot, miss, kw, nf = conn.execute("""select count(*), count(*) filter (where matched_bizrno is null),
        count(*) filter (where mode='keywords'), count(*) filter (where mode='company' and matched_bizrno is null)
        from search_logs where source='user' and created_at >= now() - interval '7 days'""").fetchone()
    for w in TYPED:  # 예시 낱말은 실제 로그에 있어야 한다 — 꾸며낸 입력을 시안에 넣지 않는다
        assert conn.execute("select 1 from search_logs where source='user' and query=%s and created_at >= now() - interval '30 days' limit 1", (w,)).fetchone(), w
    return dict(active=active, groups=groups, counts=counts, ret=ret, log=dict(tot=tot, miss=miss, kw=kw, nf=nf))


# ---------------------------------------------------------------- 공통 CSS / JS
CSS = SHEET_CSS + r"""
.wrap { min-height:100vh; display:flex; flex-direction:column }
@media (max-width:1140px) { .wrap { width:auto; padding-left:20px; padding-right:20px } }
.ctl { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; z-index:9; white-space:nowrap }
.ctl span { padding:6px 13px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.sr { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap }
/* 입력 — 상자가 아니라 괘선. 글자는 제목 크기. */
.in { position:relative }
.in input { width:100%; border:0; border-bottom:1px solid #141414; border-radius:0; background:transparent; padding:10px 0 12px; font:inherit; font-size:30px; letter-spacing:-0.03em; font-weight:550; color:#141414; outline:none }
.in input::placeholder { color:#8f8f8b; font-weight:450 } .in input:focus { border-bottom-width:2px; padding-bottom:11px }
/* 목록 — 행은 표의 행. 회사 행과 키워드 행이 같은 격자, 같은 글자 크기. */
.ls { margin:0; padding:0; list-style:none }
.ls li { display:grid; grid-template-columns:minmax(0,1.4fr) 150px minmax(0,1fr) 84px 118px; gap:0 14px; align-items:baseline; padding:12px 8px; margin:0 -8px; border-bottom:1px solid #ececea; font-size:14px; cursor:pointer; border-radius:6px }
.ls li[aria-selected="true"], .ls li:hover { background:#f6f5f2 } .ls li[aria-selected="true"] { box-shadow:inset 2px 0 0 #141414 }
.ls li .nm { font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .ls li .nm mark { background:none; color:inherit; border-bottom:1px solid #e8431b }
.ls li .rg, .ls li .rp { font-size:13px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .ls li .rp.none { color:#8f8f8b }
.ls li .nc { font-size:13px; text-align:right; font-variant-numeric:tabular-nums } .ls li .nc.none { color:#8f8f8b } .ls li .bz { font-size:12px; color:#737370; text-align:right }
.ls li.kw .nm::before { content:""; display:inline-block; width:7px; height:7px; border-radius:50%; background:#e8431b; margin-right:9px; vertical-align:1px }
.ls li.kw .rg { grid-column:2 / -1; color:#141414 } .ls li.kw .rg small { color:#6b6b67; margin-left:8px }
.ls .hd { display:flex; justify-content:space-between; padding:14px 0 6px; font-size:12px; color:#737370 } .ls .hd b { color:#141414; font-weight:600 }
.ls .hd.first { padding-top:10px }
.ls .more { padding:10px 0 0; font-size:12.5px; color:#6b6b67 }
.ls .miss { padding:16px 0 4px; font-size:13.5px; color:#55554f; line-height:1.6 } .ls .miss b { color:#141414; font-weight:600 }
/* 약속 한 줄 */
.pr { font-size:13.5px; color:#55554f; line-height:1.6 } .pr b { color:#141414; font-weight:600; font-variant-numeric:tabular-nums }
/* 최근 회사 */
.rc { display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:#6b6b67; align-items:baseline }
.rc a { color:#141414; font-weight:550; border-bottom:1px solid #d8d6d0; padding-bottom:1px; cursor:pointer } .rc a small { color:#737370; font-weight:450; margin-left:6px }
/* 넘김 — 머리(flow.html 의 .q + .labs)는 처음부터 DOM 에 있고 높이 0. 보낼 때 입력 영역이 접히고 머리가 펴진다. */
.entry { overflow:hidden; transition:height .5s cubic-bezier(.3,.7,.2,1), padding .5s cubic-bezier(.3,.7,.2,1), opacity .3s ease }
.go .entry { opacity:0; pointer-events:none; padding-top:0 !important; padding-bottom:0 !important }
.head2 { height:0; overflow:hidden; opacity:0; transition:height .55s cubic-bezier(.3,.7,.2,1), opacity .3s ease .1s }
.go .head2 { opacity:1 }
.head2 .q { padding:26px 0 0; font-size:13.5px; color:#55554f } .head2 .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px; display:inline-block; will-change:transform }
.head2 .q .back { margin-left:14px; color:#737370; border-bottom:1px solid #d8d6d0; cursor:pointer }
.head2 .stage { margin-top:20px; border-top:1px solid #141414; transform:scaleX(0); transform-origin:0 0; transition:transform .5s cubic-bezier(.3,.7,.2,1) .15s } .go .head2 .stage { transform:none }
.head2 .labs { display:grid; grid-template-columns:repeat(4,1fr); gap:0 16px; height:56px; margin-top:4px }
.head2 .lab { padding-top:4px } .head2 .lab + .lab { border-left:1px solid #d8d6d0; padding-left:12px }
.head2 .lab .k { display:block; font-size:12px; color:#55554f; white-space:nowrap; text-transform:none; letter-spacing:0 } .head2 .lab .n { margin-top:5px; font-size:26px; letter-spacing:-0.04em; font-weight:650; line-height:1; color:#141414; display:inline-block; will-change:transform }
.head2 .lab .n.wait { color:#c9c9c4 } .head2 .lab .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:5px }
.head2 .field { height:392px; border-bottom:1px solid #ececea; display:flex; align-items:center; justify-content:center; font-size:12.5px; color:#8f8f8b; text-align:center; line-height:1.7 }
.foot { margin-top:auto; padding:40px 0 70px; font-size:12.5px; color:#6b6b67; line-height:1.7; max-width:880px } .foot b { color:#141414; font-weight:600 }
@media (max-width:640px) {
  .in input { font-size:22px } .ctl { font-size:11.5px } .ctl span { padding:6px 9px }
  .ls li { grid-template-columns:minmax(0,1fr) 96px; grid-template-areas:"nm nc" "rg rg" "rp bz"; gap:3px 10px; padding:11px 8px } .ls li .bz { white-space:nowrap }
  .ls li .nm { grid-area:nm } .ls li .rg { grid-area:rg } .ls li .rp { grid-area:rp } .ls li .nc { grid-area:nc } .ls li .bz { grid-area:bz }
  .ls li.kw .rg { grid-column:auto } .ls li.kw .bz, .ls li.kw .rp, .ls li.kw .nc { display:none }
  .head2 .labs { grid-template-columns:1fr 1fr; height:auto; row-gap:10px } .head2 .lab + .lab { border-left:0; padding-left:0 } .head2 .field { height:220px }
}
@media (prefers-reduced-motion: reduce) { .entry, .head2, .head2 .stage, .ls li { transition:none !important } }
"""

# 콤보박스 하나로 세 안을 돌린다. 데이터는 #data 의 JSON — 실제 회사 행.
JS = r"""
const D = JSON.parse(document.getElementById('data').textContent);
const ROWS = Object.values(D.groups).flat();
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = s => document.querySelector(s);
const inp = $('#q'), ls = $('#ls'), live = $('#live'), hint = $('#hint');
let items = [], act = -1, picked = null;
const num = n => n.toLocaleString('ko-KR');
const hi = (s, q) => { const i = s.toLowerCase().indexOf(q.toLowerCase()); return i < 0 ? s : s.slice(0,i) + '<mark>' + s.slice(i, i+q.length) + '</mark>' + s.slice(i+q.length); };
const isBiz = q => q.replace(/\D/g,'').length === 10;

/* ---- 최근 회사: 브라우저만 기억한다. 로그인 없음. -------------------------------- */
const KEY = 'jf.recent';
const recent = () => { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { return []; } };
const remember = r => { try { localStorage.setItem(KEY, JSON.stringify([r, ...recent().filter(x => x.biz !== r.biz)].slice(0, 3))); } catch {} };

/* ---- 목록 만들기 ------------------------------------------------------------- */
function query(q) {
  q = q.trim();
  if (q.length < 2) return { rows: [], total: 0, q };
  // 사업자번호: 시안의 행은 가린 번호뿐이라 앞 3·뒤 4자리로만 맞춘다
  if (isBiz(q)) { const d = q.replace(/\D/g,''); return { rows: ROWS.filter(r => r.biz.slice(0,3) === d.slice(0,3) && r.biz.slice(-4) === d.slice(-4)), total: 0, q, biz: true }; }
  const rows = ROWS.filter(r => r.nm.toLowerCase().includes(q.toLowerCase()));
  const total = D.counts[q] ?? rows.length;      // 로그 낱말이면 DB 전체의 실제 수, 아니면 묶음 안의 수
  return { rows, total, q };
}

function row(r, i) {
  return `<li role="option" id="o${i}" data-i="${i}"><span class="nm">${hi(r.nm, inp.value.trim())}</span><span class="rg">${r.rgn || '<span class="none">지역 없음</span>'}</span>`
       + `<span class="rp ${r.rep ? '' : 'none'}">${r.rep ? r.rep + (r.nind > 1 ? ` 외 ${r.nind-1}` : '') : '등록업종 없음'}</span>`
       + `<span class="nc ${r.ncon ? '' : 'none'}">${r.ncon ? `수주 ${r.ncon}건` : '수주 없음'}</span><span class="bz">${r.biz}</span></li>`;
}
function kwrow(q, i, lead) {
  return `<li role="option" class="kw" id="o${i}" data-i="${i}"><span class="nm">이 말로 공고 찾기</span><span class="rg">"${q}"<small>${lead ? '회사 없이 — 이 일을 하는 공고만' : '회사가 아니라 하는 일이라면'}</small></span></li>`;
}

function render() {
  const { rows, total, q, biz } = query(inp.value);
  items = []; act = -1;
  if (!q || q.length < 2) { ls.innerHTML = ''; ls.hidden = true; inp.setAttribute('aria-expanded', 'false'); live.textContent = ''; return; }
  // total 은 DB 의 실제 회사 수. 30곳을 넘으면 낱말로는 못 고르는 것이라 키워드 행이 앞선다("감리" 61곳).
  const shown = rows.slice(0, 8), generic = total > 30, miss = total === 0;
  let h = '';
  const kwFirst = (generic || miss) && !biz;
  if (kwFirst) { h += `<div class="hd first"><span>하는 일로</span></div>` + kwrow(q, items.length, true); items.push({ kw: q }); }
  if (miss) {
    h += `<div class="miss">${biz ? `<b>${q}</b> 번호로 등록된 회사가 없습니다.` : `<b>${q}</b> 이름의 회사를 나라장터 등록에서 찾지 못했습니다.`}<br>`
       + `사업자번호 10자리로 다시 찾거나, 회사가 없어도(예비창업·해외·개인) 위 행으로 공고를 볼 수 있습니다.</div>`;
  } else {
    h += `<div class="hd ${kwFirst ? '' : 'first'}"><span>회사 <b>${num(total)}</b>곳${generic ? ' — 회사명을 더 치면 좁혀집니다' : ''}</span><span>지역 · 대표업종 · 수주</span></div>`;
    for (const r of (generic ? shown.slice(0, 3) : shown)) { h += row(r, items.length); items.push({ co: r }); }
    if (!rows.length) h += `<div class="miss">시안에는 이 낱말의 회사 행을 싣지 않았다 — 실제 화면에선 ${num(total)}곳 중 수주 많은 순 3곳.</div>`;
    if (total > items.length - (kwFirst ? 1 : 0)) h += `<div class="more">비슷한 이름 ${num(total - (items.length - (kwFirst ? 1 : 0)))}곳 더 — 지역이나 글자를 더 치면 좁혀집니다</div>`;
  }
  if (!kwFirst && !biz) { h += `<div class="hd"><span>하는 일로</span></div>` + kwrow(q, items.length, false); items.push({ kw: q }); }
  ls.innerHTML = h; ls.hidden = false; inp.setAttribute('aria-expanded', 'true');
  live.textContent = miss ? `회사 없음. 키워드로 찾기 1개` : `회사 ${items.filter(x => x.co).length}곳, 키워드로 찾기 1개. 화살표로 고르고 Enter`;
}

function setAct(i) {
  act = i;
  [...ls.querySelectorAll('[role=option]')].forEach((o, k) => o.setAttribute('aria-selected', k === i ? 'true' : 'false'));
  const o = ls.querySelector(`#o${i}`);
  inp.setAttribute('aria-activedescendant', o ? o.id : '');
  o && o.scrollIntoView({ block: 'nearest' });
}

inp.addEventListener('input', render);
inp.addEventListener('keydown', e => {
  if (ls.hidden) { if (e.key === 'Enter' && inp.value.trim().length >= 2) { render(); } return; }
  if (e.key === 'ArrowDown') { e.preventDefault(); setAct((act + 1) % items.length); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); setAct((act - 1 + items.length) % items.length); }
  else if (e.key === 'Escape') { ls.hidden = true; inp.setAttribute('aria-expanded', 'false'); act = -1; }
  else if (e.key === 'Enter') { e.preventDefault(); choose(act >= 0 ? act : (items.findIndex(x => x.co) >= 0 && items.filter(x => x.co).length === 1 ? items.findIndex(x => x.co) : items.findIndex(x => x.kw))); }
});
ls.addEventListener('mousedown', e => { const o = e.target.closest('[role=option]'); if (o) { e.preventDefault(); choose(+o.dataset.i); } });

/* ---- 고르기 → 넘김. confirm 안은 window.onPick 이 가로채 확인 카드로 보낸다. ----- */
function choose(i) {
  const it = items[i]; if (!it) return;
  if (window.onPick && window.onPick(it)) return;
  go(it);
}

function flip(el, from) {
  if (reduce || !from) return;
  const to = el.getBoundingClientRect();
  el.animate([{ transform: `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${from.height / to.height})`, transformOrigin: '0 0' }, { transform: 'none' }],
             { duration: 520, easing: 'cubic-bezier(.3,.7,.2,1)' });
}

function go(it, fromEl) {
  picked = it;
  const src = fromEl || inp, a = src.getBoundingClientRect();
  const pn = $('#pn'), b = pn.getBoundingClientRect();
  if (it.co) { remember(it.co); $('#hq').innerHTML = `<b>${it.co.nm}</b>${it.co.rgn} · ${it.co.rep ? '등록업종 ' + it.co.nind : '등록업종 없음'} · ${it.co.ncon ? '수주 ' + it.co.ncon + '건' : '수주 이력 없음'}<span class="back" id="back">다시 입력</span>`;
    $('#hl').innerHTML = lab('지금 입찰 가능 · 마감 90일 이내', D.active) + lab('업종이 맞는 공고', null) + lab('자격이 되는 공고 · 면허·지역', null) + lab('검토할 공고', null, true); }
  else { $('#hq').innerHTML = `<b>"${it.kw}"</b>회사 없이 · 이 말과 가까운 공고<span class="back" id="back">다시 입력</span>`;
    $('#hl').innerHTML = lab('지금 입찰 가능 · 마감 90일 이내', D.active) + lab('이 말과 가까운 공고', null) + lab('검토할 공고', null, true); }
  const entry = $('.entry'); entry.style.height = entry.offsetHeight + 'px';
  const head = $('.head2'); head.style.height = 'auto'; const hh = head.offsetHeight; head.style.height = '0px';
  requestAnimationFrame(() => { entry.style.height = '0px'; head.style.height = hh + 'px'; document.body.classList.add('go');
    flip($('#hq b'), a); flip($('#hl .n'), b); });
  $('#back').onclick = reset;
  ls.hidden = true; inp.setAttribute('aria-expanded', 'false');
}
function lab(k, v, last) { return `<div class="lab ${last ? 'last' : ''}"><span class="k">${k}</span><div class="n ${v == null ? 'wait' : ''}">${v == null ? '…' : num(v)}<small>건</small></div></div>`; }
function reset() { document.body.classList.remove('go'); $('.entry').style.height = ''; $('.head2').style.height = '0px'; picked = null; window.onReset && window.onReset(); inp.focus(); }

/* ---- 상태 알약 — 입력란에 값을 넣고 같은 render 를 돌린다. 꾸민 화면이 아니라 같은 경로. ---- */
const STATES = { empty: '', typing: D.typing, miss: 'ADATA', return: '' };
function state(s) {
  document.querySelectorAll('.ctl span').forEach(x => x.classList.toggle('on', x.dataset.s === s));
  reset();
  if (s === 'return') { try { localStorage.setItem(KEY, JSON.stringify(D.ret)); } catch {} } else if (s === 'empty') { try { localStorage.removeItem(KEY); } catch {} }
  inp.value = STATES[s]; render(); window.onState && window.onState(s); paintRecent();
  if (s !== 'return') inp.focus();
}
function paintRecent() {
  const r = recent(), el = $('#rc'); if (!el) return;
  el.innerHTML = r.length ? `<span>최근</span>` + r.map((c, i) => `<a data-i="${i}">${c.nm}<small>${c.rgn}${c.ncon ? ' · 수주 ' + c.ncon + '건' : ''}</small></a>`).join('') : '';
  el.querySelectorAll('a').forEach(a => a.onclick = () => go({ co: r[+a.dataset.i] }, a));
  window.onRecent && window.onRecent(r);
}
document.querySelectorAll('.ctl span').forEach(x => x.onclick = () => state(x.dataset.s));
document.addEventListener('click', e => { if (!e.target.closest('.in') && !e.target.closest('#ls') && !e.target.closest('.ctl')) { ls.hidden = true; inp.setAttribute('aria-expanded', 'false'); } });
state(recent().length ? 'return' : 'empty');
"""


def combobox(placeholder):
    return (f'<div class="in"><input id="q" type="text" autocomplete="off" spellcheck="false" placeholder="{placeholder}" '
            f'role="combobox" aria-expanded="false" aria-controls="ls" aria-autocomplete="list" aria-label="회사명, 사업자번호, 또는 하는 일" enterkeyhint="search"></div>'
            f'<ul id="ls" role="listbox" class="ls" hidden aria-label="회사 또는 키워드"></ul><div id="live" class="sr" aria-live="polite"></div>')


def head2():
    return ('<div class="head2"><div class="q" id="hq"></div><div class="stage"><div class="labs" id="hl"></div>'
            '<div class="field">여기서 flow.html 의 캔버스가 이어진다 — 후보 검색이 끝나면 두 번째 칸이, 자격 거르기가 끝나면 세 번째 칸이 찬다.<br>'
            '가짜 진행률 없음. 캐시 히트면 이 머리를 건너뛰고 결과가 바로 뜬다.</div></div></div>')


def ctl():
    return ('<div class="ctl" role="group" aria-label="시안 상태"><span data-s="empty">빈 입력</span><span data-s="typing">타이핑 중</span>'
            '<span data-s="miss">못 찾음</span><span data-s="return">재방문</span></div>')


def foot(d):
    lg = d["log"]
    return (f'<div class="foot"><b>왜 키워드 길이 회사 길과 같은 무게인가.</b> 최근 7일 사용자 검색 {lg["tot"]}건 중 {lg["miss"]}건({lg["miss"] / lg["tot"] * 100:.0f}%)이 회사로 풀리지 않았다 — '
            f'{lg["kw"]}건은 처음부터 키워드 모드, {lg["nf"]}건은 회사 모드에서 "회사를 찾을 수 없습니다". 친 문자열은 '
            + " · ".join(f'"{w}"' for w in TYPED[:5]) + ' 같은 낱말·브랜드다. '
            f'동명 회사 목록의 회사·지역·업종·수주는 실제 행이고, 사업자번호는 가운데를 가린다. 지금 입찰 가능 {d["active"]:,}건은 {date.today()} 마감 90일 이내 공고 수. '
            f'목록은 ↑↓ Enter Esc, role=combobox/listbox, aria-activedescendant. 아래 알약은 입력란에 값을 넣고 같은 코드를 돌린다 — 입력란에 직접 쳐도 된다 '
            f'(묶음: {", ".join(COLLISIONS)}).</div>')


def promise(d):
    return (f'<p class="pr">지금 입찰 가능한 공고 <b>{d["active"]:,}</b>건. 회사명이나 사업자번호를 넣으면 <b>이 회사가 낼 수 있는 것만</b>, '
            f'하는 일을 넣으면 <b>그 일을 하는 공고만</b> 남깁니다.</p>')


def page(title, css, body, js, d):
    data = dict(groups=d["groups"], counts=d["counts"], active=d["active"], ret=d["ret"], typing=COLLISIONS[0])
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 입구 — {title}</title>{FONT}<style>{CSS}{css}</style></head><body>'
            f'<div class="wrap">{nav()}{body}{foot(d)}</div>{ctl()}'
            f'<script type="application/json" id="data">{json.dumps(data, ensure_ascii=False)}</script><script>{js}{JS}</script></body></html>')


# ---------------------------------------------------------------- line — 한 줄
LINE_CSS = r"""
.entry { padding:14vh 0 40px } .entry .rc { min-height:22px; margin-bottom:18px } .entry .pr { margin:14px 0 0; max-width:640px }
.entry .pr b:first-child { display:inline-block; will-change:transform }
@media (max-width:640px) { .entry { padding-top:28px } }
"""


def line(d):
    body = (f'<div class="entry"><div class="rc" id="rc"></div>{combobox("회사명 · 사업자번호 · 하는 일")}'
            f'{promise(d).replace("<b>", "<b id=\"pn\">", 1)}</div>{head2()}')
    return page("한 줄", LINE_CSS, body, "", d)


# ---------------------------------------------------------------- desk — 숫자 먼저, 두 길
DESK_CSS = r"""
.entry { padding:9vh 0 40px }
.big { font-size:15px; color:#55554f } .big .n { display:block; font-size:64px; letter-spacing:-0.045em; font-weight:650; line-height:1; color:#141414; margin:8px 0 6px; font-variant-numeric:tabular-nums; will-change:transform }
.big .n small { font-size:15px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:8px }
.desk .in { margin-top:34px; position:relative } .desk .in input { font-size:26px }
.desk #ls { position:absolute; left:0; right:0; z-index:5; background:#fff; border:1px solid #e3e1dc; border-radius:12px; padding:4px 14px 12px; margin-top:10px; box-shadow:0 12px 40px -18px rgba(20,20,20,.25) }
.desk #ls li { margin:0 -6px; padding-left:6px; padding-right:6px }
.lanes { display:grid; grid-template-columns:1fr 1fr; gap:0 40px; margin-top:34px }
.lane { border-top:1px solid #141414; padding-top:14px } .lane .k { display:block; margin-bottom:8px } .lane h3 { margin:0; font-size:17px; font-weight:650; letter-spacing:-0.02em }
.lane p { margin:8px 0 0; font-size:13.5px; color:#55554f; line-height:1.65 } .lane .ex { margin-top:12px; font-size:12.5px; color:#737370 } .lane .ex a { color:#141414; border-bottom:1px solid #d8d6d0; margin-right:12px; cursor:pointer }
.lane.kw h3::before { content:""; display:inline-block; width:8px; height:8px; border-radius:50%; background:#e8431b; margin-right:9px }
.cards[hidden], .lanes[hidden] { display:none } .cards { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:34px }
.card { border:1px solid #e3e1dc; border-radius:12px; padding:16px 18px; cursor:pointer; transition:border-color .2s, transform .35s cubic-bezier(.3,.7,.2,1) } .card:hover { border-color:#141414; transform:translateY(-2px) }
.card .k { display:block; margin-bottom:8px } .card b { font-size:16px; font-weight:650; letter-spacing:-0.02em; display:block } .card p { margin:6px 0 0; font-size:13px; color:#55554f; line-height:1.6 }
.card .bt { margin-top:14px; height:32px } .cards .other { display:flex; align-items:center; font-size:13.5px; color:#55554f } .cards .other a { color:#141414; border-bottom:1px solid #d8d6d0; margin-left:6px; cursor:pointer }
@media (max-width:640px) { .entry { padding-top:24px } .big .n { font-size:44px } .lanes, .cards { grid-template-columns:1fr; gap:22px } .desk .in { margin-top:24px } }
"""
DESK_JS = r"""
window.onRecent = r => {
  const c = document.getElementById('cards'), l = document.getElementById('lanes');
  c.hidden = !r.length; l.hidden = !!r.length;
  c.innerHTML = r.map((x, i) => `<div class="card" data-i="${i}" tabindex="0" role="button"><span class="k">${i ? '최근' : '지난번'}</span><b>${x.nm}</b><p>${x.rgn}<br>${x.rep ? '등록업종 ' + x.rep + (x.nind > 1 ? ' 외 ' + (x.nind-1) : '') : '등록업종 없음'}<br>${x.ncon ? '수주 ' + x.ncon + '건' : '수주 이력 없음'} · ${x.biz}</p><span class="bt dark">바로 보기</span></div>`).join('')
              + `<div class="other">다른 회사면<a id="oth">위에 입력</a></div>`;
  c.querySelectorAll('.card').forEach(el => { const f = () => go({ co: r[+el.dataset.i] }, el.querySelector('b')); el.onclick = f; el.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); f(); } }; });
  const o = document.getElementById('oth'); if (o) o.onclick = () => inp.focus();
};
document.querySelectorAll('.lane .ex a').forEach(a => a.onclick = () => { inp.value = a.textContent; inp.focus(); render(); });
"""


def desk(d):
    ex_co = f"<a>{esc(COLLISIONS[0])}</a>"
    ex_kw = "".join(f"<a>{esc(w)}</a>" for w in TYPED[1:4])
    body = (f'<div class="entry desk"><div class="big">지금 입찰 가능한 공고 · 마감 90일 이내<span class="n" id="pn">{d["active"]:,}<small>건</small></span>'
            f'회사를 넣으면 이 회사가 낼 수 있는 것만, 하는 일을 넣으면 그 일을 하는 공고만 남습니다.</div>'
            f'{combobox("회사명 · 사업자번호 · 하는 일 — 한 칸에")}'
            f'<div class="lanes" id="lanes"><div class="lane"><span class="k">회사로</span><h3>낼 수 있는 것만</h3><p>등록업종·면허·지역 제한으로 거르고, 수주 이력이 있으면 그 기관·체급을 더 봅니다. 같은 이름이 여럿이면 지역·업종으로 고릅니다.</p><div class="ex">예 {ex_co}</div></div>'
            f'<div class="lane kw"><span class="k">하는 일로</span><h3>그 일을 하는 공고만</h3><p>회사가 없어도 됩니다 — 예비창업·해외·개인. 하는 일을 낱말로 치면 그 말과 가까운 공고를 찾습니다. 자격 거르기는 하지 않습니다.</p><div class="ex">예 {ex_kw}</div></div></div>'
            f'<div class="cards" id="cards" hidden></div><div id="rc" hidden></div></div>{head2()}')
    return page("두 길", DESK_CSS, body, DESK_JS, d)


# ---------------------------------------------------------------- confirm — 두 단계
CONF_CSS = r"""
.entry { padding:10vh 0 40px } .steps { display:flex; gap:18px; font-size:12px; color:#8f8f8b; margin-bottom:26px } .steps b { color:#141414; font-weight:600 } .steps span + span::before { content:"→"; margin-right:18px; color:#c9c9c4 }
.conf .in input { font-size:26px } .conf .pr { margin:14px 0 0 } .conf .pr b:first-child { display:inline-block }
.cf { margin-top:30px; border-top:1px solid #141414; padding-top:18px; display:none } .cf.on { display:block }
.cf .k { display:block; margin-bottom:10px } .cf h2 { margin:0; font-size:26px; letter-spacing:-0.03em; font-weight:650; line-height:1.2; display:inline-block } .cf h2 small { font-size:13px; color:#737370; font-weight:450; letter-spacing:0; margin-left:12px }
.cf dl { margin:16px 0 0; display:grid; grid-template-columns:max-content 1fr; gap:8px 22px; font-size:14px } .cf dt { color:#6b6b67 } .cf dd { margin:0 } .cf dd.none { color:#8f8f8b }
.cf .ask { margin-top:18px; font-size:14px; line-height:1.6 } .cf .ask b { font-weight:600 }
.cf .acts { margin-top:16px; display:flex; gap:8px; flex-wrap:wrap; align-items:center } .cf .acts .bt.dark { height:40px; padding:0 18px } .cf .acts .sep { color:#c9c9c4; margin:0 4px }
.cf .acts .bt.txt { cursor:pointer } .cf .acts .bt { cursor:pointer }
.rc2 { margin-top:22px } .rc2 .rc { margin-top:8px }
@media (max-width:640px) { .entry { padding-top:24px } .cf h2 { font-size:22px } .cf dl { grid-template-columns:1fr; gap:4px } .cf dt { font-size:12px } }
"""
CONF_JS = r"""
let held = null;
const cf = document.getElementById('cf');
window.onPick = it => { held = it; show(); return true; };
function show() {
  const it = held; if (!it) { cf.classList.remove('on'); return; }
  ls.hidden = true; inp.setAttribute('aria-expanded', 'false');
  if (it.co) { const c = it.co;
    cf.innerHTML = `<span class="k">2 · 확인</span><h2 id="cfn">${c.nm}<small>${c.biz}</small></h2>`
      + `<dl><dt>지역</dt><dd class="${c.rgn ? '' : 'none'}">${c.rgn || '등록 없음'}</dd><dt>등록업종</dt><dd class="${c.rep ? '' : 'none'}">${c.rep ? c.rep + (c.nind > 1 ? ` 외 ${c.nind-1}개` : '') : '등록 없음 — 업종으로 거르지 못해 키워드 길이 낫습니다'}</dd><dt>수주 이력</dt><dd class="${c.ncon ? '' : 'none'}">${c.ncon ? c.ncon + '건' : '없음 — 등록업종만으로 거릅니다'}</dd></dl>`
      + `<p class="ask">이 정보로 지금 입찰 가능한 <b>${num(D.active)}</b>건을 거릅니다. 맞나요?</p>`
      + `<div class="acts"><span class="bt dark" id="ok" tabindex="0" role="button">맞습니다, 공고 보기</span><span class="bt" id="no" tabindex="0" role="button">다른 회사</span>${inp.value.trim() ? `<span class="sep">·</span><span class="bt txt" id="kw" tabindex="0" role="button"><u>회사 없이 "${inp.value.trim()}" 로 찾기</u></span>` : ''}</div>`;
  } else {
    cf.innerHTML = `<span class="k">2 · 확인</span><h2 id="cfn">"${it.kw}"<small>회사 없이</small></h2>`
      + `<dl><dt>찾는 방식</dt><dd>이 말과 가까운 공고. 등록업종·면허·지역 거르기 없음</dd><dt>회사가 있다면</dt><dd>회사명으로 다시 치면 낼 수 있는 것만 남습니다</dd></dl>`
      + `<p class="ask">지금 입찰 가능한 <b>${num(D.active)}</b>건에서 이 말과 가까운 순으로 보여 드립니다.</p>`
      + `<div class="acts"><span class="bt dark" id="ok" tabindex="0" role="button">이 말로 공고 보기</span><span class="bt" id="no" tabindex="0" role="button">다시 입력</span></div>`;
  }
  cf.classList.add('on');
  const btn = (id, f) => { const b = document.getElementById(id); if (b) { b.onclick = f; b.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); f(); } }; } };
  btn('ok', () => go(held, document.getElementById('cfn')));
  btn('no', () => { held = null; show(); inp.focus(); inp.select(); });
  btn('kw', () => { held = { kw: inp.value.trim() }; show(); });
  document.getElementById('ok').focus();
}
window.onReset = () => { held = null; show(); };
window.onState = s => { held = null; show(); };
window.onRecent = r => { if (r.length && !held && !inp.value) { held = { co: r[0] }; show(); cf.querySelector('.k').textContent = '지난번 회사'; const a = document.querySelector('#rc a'); if (a) a.hidden = true; } };
"""


def confirm(d):
    body = (f'<div class="entry conf"><div class="steps"><span><b>1</b> 회사 또는 하는 일</span><span><b>2</b> 확인</span><span><b>3</b> 공고</span></div>'
            f'{combobox("회사명 · 사업자번호 · 하는 일")}{promise(d).replace("<b>", "<b id=\"pn\">", 1)}'
            f'<div class="cf" id="cf"></div><div class="rc2"><div class="rc" id="rc"></div></div></div>{head2()}')
    return page("확인", CONF_CSS, body, CONF_JS, d)


if __name__ == "__main__":
    out = sys.argv[1].rstrip("/\\")
    d = fetch(connect())
    for name, fn in (("entry-line", line), ("entry-desk", desk), ("entry-confirm", confirm)):
        with open(f"{out}/{name}.html", "w", encoding="utf-8") as f:
            f.write(fn(d))
    lg = d["log"]
    print(f'active={d["active"]:,}  7d user searches={lg["tot"]} unresolved={lg["miss"]} ({lg["miss"] / lg["tot"] * 100:.1f}%) '
          f'keyword-mode={lg["kw"]} company-mode-not-found={lg["nf"]}')
    for k, v in d["groups"].items():
        print(f'  {k}: {len(v)} rows, {sum(1 for r in v if r["ncon"])} with contracts')
    print("  typed counts:", d["counts"])

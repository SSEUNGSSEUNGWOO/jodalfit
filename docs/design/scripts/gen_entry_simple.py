"""검색 입구 — 단순 검색창 하나 (2026-10-16 결정: entry-flow 는 "별로", 상자 하나, 상자는 주황).
위에 아무것도 없다. 상자(주황 테두리 2px, 안은 흰색, 글자는 먹) + 그 아래 회색 한 줄. 치면 entry-line 과 같은 격자의 목록이 상자 아래로 자란다.
흐름 머리(flow.html)는 이제 결과 페이지의 것이라 여기엔 전환이 없다.
데이터·목록 구조는 gen_entry.py 의 것(대신네트웍스 17곳, 실제 입찰 가능 건수, 7일 로그 낱말, 52% 각주)을 그대로 쓴다. gen_entry_flow.py 는 쓰지 않는다.

주황 #f97316 은 이 파일에서만 — SHEET_CSS 의 #e8431b 는 상수가 아니라 선택자마다 박혀 있어 공통을 바꾸면 옛 시안 전부가 물든다. 로고 점·.acc 는 아래서 덮어쓴다.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_entry_simple.py ../docs/design/prototypes/
"""
import json
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_entry import COLLISIONS, TYPED, ctl, fetch  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav  # noqa: E402
from jobs.evaluate_recommender import connect  # noqa: E402


def clse(d):
    """올해면 M.DD, 아니면 YYYY.M.DD — 2037 마감 같은 장기 단가계약이 실제로 있다."""
    return f"{d.month}.{d.day:02d}" if d.year == date.today().year else f"{d.year}.{d.month}.{d.day:02d}"


def fetch_today(conn):
    """오늘 등록된 공고 전부(90일 지평선 안), 최신순. 오전 이른 시간엔 오늘 수집분이 얇아(수집 05:00·12:30) 50건 미만이면 어제로 간다.
    순서는 bid_ntce_date desc, bid_ntce_no desc — 게시 시각(시·분)이 없어 같은 날 안에서는 공고번호 순이 선후를 대신한다."""
    for label, day in (("오늘", "current_date"), ("어제", "current_date - 1")):
        n = conn.execute(f"select count(*) from bid_notices where bid_ntce_date = {day}").fetchone()[0]
        if n >= 50 or label == "어제":
            rows = conn.execute(f"""select distinct on (bid_ntce_no) bid_ntce_no, bid_ntce_nm, ntce_instt_nm, bid_clse_date, presmpt_prce
                from bid_notices where bid_ntce_date = {day} and bid_clse_date <= current_date + 90  -- 추천과 같은 지평선: 2037 마감 단가계약(종합쇼핑몰)은 뺀다
                order by bid_ntce_no, bid_ntce_ord desc""").fetchall()
            rows.sort(key=lambda r: r[0], reverse=True)
            return dict(label=label, n=n, rows=[dict(no=a, nm=b, org=c, clse=clse(d), prc=int(e) if e else None) for a, b, c, d, e in rows])

# ponytail: 둘째 블록 "이번 주 가장 많은 회사에 추천된 공고"는 만들지 않는다 —
#   notice_events(source='user', 7d) impressions 를 bid_ntce_no 로 묶어 count(distinct target_bizrno) 가 '인기' 신호인데,
#   오늘 사용자 클릭이 7일 139건이라 너무 얇다. 일일 사용자가 수백이 되면 그때 켠다.


# 주황이 쓰이는 곳(전부 선): 로고 점 · 상자 테두리 · 포커스 링(18%) · 찾기 밑줄 2px · 일치 글자 밑줄 · 키워드 행 점 · 고른 행 왼쪽 괘선 · 최근 칩 hover 테두리 · 390px 화살표
CSS = SHEET_CSS + r"""
.brand i { background:#f97316 } .acc { color:#f97316 }
.wrap { min-height:100vh; display:flex; flex-direction:column }
@media screen and (max-width:1140px) { .wrap { width:auto; padding-left:20px; padding-right:20px } }
.ctl { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; z-index:9; white-space:nowrap }
.ctl span { padding:6px 13px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.sr { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap }
.entry { width:100%; max-width:720px; margin:0 auto; padding:22vh 0 40px; min-height:84vh } /* 각주는 접힘선 아래로 */
/* 상자 — 주황은 테두리뿐. 안은 흰색, 글자는 먹. */
.box { display:flex; align-items:stretch; border:2px solid #f97316; border-radius:6px; background:#fff; transition:box-shadow .15s }
.box:focus-within { box-shadow:0 0 0 4px rgba(249,115,22,.18) }
.box input { flex:1; min-width:0; border:0; background:transparent; padding:16px 18px; font:inherit; font-size:20px; letter-spacing:-0.02em; font-weight:500; color:#141414; outline:none }
.box input::placeholder { color:#8f8f8b; font-weight:450 }
/* 찾기 — 글자는 먹(주황/흰 2.8:1 이라 글자로는 못 쓴다), 주황은 밑줄 2px. hover/focus 는 밑줄이 3px 로. */
.box .go { border:0; border-left:1px solid #ececea; background:#fff; color:#141414; font:inherit; font-size:15px; font-weight:650; padding:0 20px; cursor:pointer; border-radius:0 4px 4px 0 }
.box .go .t, .box .go .ar { border-bottom:2px solid #f97316; padding-bottom:1px }
.box .go:hover .t, .box .go:focus-visible .t, .box .go:hover .ar, .box .go:focus-visible .ar { border-bottom-width:3px; padding-bottom:0 }
.box .go:focus-visible { outline:2px solid #f97316; outline-offset:-2px }
.box .go .ar { display:none }
.pr { margin:12px 0 0; font-size:13.5px; color:#55554f; line-height:1.6 } .pr b { font-weight:600; font-variant-numeric:tabular-nums }
/* 최근 회사 칩 — 먹 글자, 헤어라인. hover/focus 에서 테두리만 주황. */
.rc { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; font-size:13px; align-items:center } .rc:empty { display:none }
.rc .l { color:#6b6b67 }
.rc a { display:inline-flex; align-items:baseline; gap:6px; padding:6px 11px; border:1px solid #e3e1dc; border-radius:6px; color:#141414; font-weight:550; cursor:pointer; transition:border-color .15s }
.rc a small { color:#737370; font-weight:450 } .rc a:hover, .rc a:focus-visible { border-color:#f97316; outline:none }
/* 목록 — entry-line 과 같은 격자. 고른 행은 면이 아니라 왼쪽 괘선. */
.ls { margin:10px 0 0; padding:0; list-style:none }
.ls li { display:grid; grid-template-columns:minmax(0,1.4fr) 150px minmax(0,1fr) 84px 118px; gap:0 14px; align-items:baseline; padding:12px 8px; margin:0 -8px; border-bottom:1px solid #ececea; font-size:14px; cursor:pointer; border-radius:6px }
.ls li:hover { background:#f6f5f2 } .ls li[aria-selected="true"] { box-shadow:inset 2px 0 0 #f97316; border-radius:0 }
.ls li .nm { font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .ls li .nm mark { background:none; color:inherit; border-bottom:1px solid #f97316 }
.ls li .rg, .ls li .rp { font-size:13px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .ls li .rp.none { color:#8f8f8b }
.ls li .nc { font-size:13px; text-align:right; font-variant-numeric:tabular-nums } .ls li .nc.none { color:#8f8f8b } .ls li .bz { font-size:12px; color:#737370; text-align:right }
.ls li.kw .nm::before { content:""; display:inline-block; width:7px; height:7px; border-radius:50%; background:#f97316; margin-right:9px; vertical-align:1px }
.ls li.kw .rg { grid-column:2 / -1; color:#141414 } .ls li.kw .rg small { color:#6b6b67; margin-left:8px }
.ls .hd { display:flex; justify-content:space-between; padding:14px 0 6px; font-size:12px; color:#737370 } .ls .hd b { color:#141414; font-weight:600 }
.ls .hd.first { padding-top:6px }
.ls .more { padding:10px 0 0; font-size:12.5px; color:#6b6b67 }
.ls .miss { padding:16px 0 4px; font-size:13.5px; color:#55554f; line-height:1.6 } .ls .miss b { color:#141414; font-weight:600 }
/* 오늘 등록된 공고 — 상자보다 조용해야 한다. 주황 없음, 헤어라인 행, 먹 제목 13.5px, 회색 메타 12.5px.
   세로 틱: 바깥 .tk 는 5행 높이로 고정된 클립(JS 가 잰다), 안쪽 .tki 를 translateY(-행) → 0 으로 민다 — 레이아웃이 아니라 transform 이라 layout-shift 0.
   새 행은 opacity 0→1 로 위에서 들어오고 맨 아래 행은 클립 밖으로 밀려나며 opacity 1→0. 들어온 행은 0.6초 동안 먹 650 이었다가 500 으로. */
.today { margin-top:48px } .today .k { display:block; margin-bottom:6px } .today .tk { overflow:hidden }
.today .tki { transition:transform var(--tk,320ms) cubic-bezier(.3,.7,.2,1) }
.today a.row { display:grid; grid-template-columns:minmax(0,1fr) 150px 76px 128px; gap:0 14px; align-items:baseline; padding:10px 0; border-top:1px solid #ececea; font-size:13.5px; transition:opacity var(--tk,320ms) ease }
.today a.row:last-of-type { border-bottom:1px solid #ececea } .today a.row.out { pointer-events:none }
.today .t { color:#141414; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; transition:font-weight .4s } .today a.row.new .t { font-weight:650 }
.today a.row:hover .t { text-decoration:underline; text-underline-offset:3px }
.today .o, .today .d { font-size:12.5px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .today .d { text-align:right; font-variant-numeric:tabular-nums }
.today .w { font-size:12.5px; color:#55554f; text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap } .today .w.none { color:#8f8f8b }
.today .all { display:inline-block; margin-top:10px; font-size:13px; color:#141414 } .today .all:hover, .today .all:focus-visible { text-decoration:underline; text-underline-offset:3px }
.sent { margin-top:14px; font-size:13px; color:#55554f } .sent:empty { display:none }
.foot { margin-top:auto; padding:40px 0 70px; font-size:12.5px; color:#6b6b67; line-height:1.7; max-width:880px } .foot b { color:#141414; font-weight:600 }
@media screen and (max-width:640px) {
  .entry { padding-top:28px } .ctl { font-size:11.5px } .ctl span { padding:6px 9px }
  .box input { font-size:17px; padding:14px 14px; text-overflow:ellipsis } .box .go { padding:0 14px } .box .go .t { display:none } .box .go .ar { display:inline; font-size:20px; line-height:1 }
  #ls { max-height:calc(100dvh - 230px); overflow:auto } .ls li.kw { position:sticky; bottom:0; background:#fff } /* 목록이 스크롤돼도 키워드 행은 보인다 */
  .ls li { grid-template-columns:minmax(0,1fr) 96px; grid-template-areas:"nm nc" "rg rg" "rp bz"; gap:3px 10px; padding:11px 8px } .ls li .bz { white-space:nowrap }
  .ls li .nm { grid-area:nm } .ls li .rg { grid-area:rg } .ls li .rp { grid-area:rp } .ls li .nc { grid-area:nc } .ls li .bz { grid-area:bz }
  .ls li.kw .rg { grid-column:auto } .ls li.kw .bz, .ls li.kw .rp, .ls li.kw .nc { display:none }
  .today a.row { grid-template-columns:minmax(0,1fr) 64px; grid-template-areas:"t t" "o d"; gap:3px 10px } .today .t { grid-area:t } .today .o { grid-area:o } .today .d { grid-area:d } .today .w { display:none }
}
@media (prefers-reduced-motion: reduce) { .box, .rc a, .today .tki, .today a.row, .today .t { transition:none } }
"""

# 목록 기계는 gen_entry.JS 와 같다(query/render/setAct/키). 다른 것은 넘김뿐 — 전환 없음.
JS = r"""
const D = JSON.parse(document.getElementById('data').textContent);
const ROWS = Object.values(D.groups).flat();
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = s => document.querySelector(s);
const inp = $('#q'), ls = $('#ls'), live = $('#live'), sent = $('#sent');
let items = [], act = -1;
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
  if (isBiz(q)) { const d = q.replace(/\D/g,''); return { rows: ROWS.filter(r => r.biz.slice(0,3) === d.slice(0,3) && r.biz.slice(-4) === d.slice(-4)), total: 0, q, biz: true }; }
  const rows = ROWS.filter(r => r.nm.toLowerCase().includes(q.toLowerCase()));
  const total = D.counts[q] ?? rows.length;
  return { rows, total, q };
}
function row(r, i) {
  return `<li role="option" id="o${i}" data-i="${i}"><span class="nm">${hi(r.nm, inp.value.trim())}</span><span class="rg">${r.rgn || '<span class="none">지역 없음</span>'}</span>`
       + `<span class="rp ${r.rep ? '' : 'none'}">${r.rep ? r.rep + (r.nind > 1 ? ` 외 ${r.nind-1}` : '') : '등록업종 없음'}</span>`
       + `<span class="nc ${r.ncon ? '' : 'none'}">${r.ncon ? `수주 ${r.ncon}건` : '수주 없음'}</span><span class="bz">${r.biz}</span></li>`;
}
function kwrow(q, i, lead) {
  return `<li role="option" class="kw" id="o${i}" data-i="${i}"><span class="nm">키워드로 공고 검색</span><span class="rg">"${q}"<small>${lead ? '회사 없이 — 업종·품목 기준' : '업종·품목 기준'}</small></span></li>`;
}
function close() { ls.hidden = true; inp.setAttribute('aria-expanded', 'false'); inp.setAttribute('aria-activedescendant', ''); act = -1; }
function render() {
  const { rows, total, q, biz } = query(inp.value);
  items = []; act = -1; sent.textContent = '';
  if (!q || q.length < 2) { ls.innerHTML = ''; close(); live.textContent = ''; return; }
  const shown = rows.slice(0, 8), generic = total > 30, miss = total === 0;
  let h = '';
  const kwFirst = (generic || miss) && !biz;
  if (kwFirst) { h += `<div class="hd first"><span>키워드</span></div>` + kwrow(q, items.length, true); items.push({ kw: q }); }
  if (miss) {
    h += `<div class="miss">${biz ? `<b>${q}</b> 번호로 등록된 회사 없음.` : `<b>${q}</b> 명칭의 회사가 나라장터 등록에 없음.`}<br>`
       + `사업자등록번호 10자리로 재검색하거나, 회사 등록 없이(예비창업·해외·개인) 위 행에서 키워드로 검색합니다.</div>`;
  } else {
    h += `<div class="hd ${kwFirst ? '' : 'first'}"><span>회사 <b>${num(total)}</b>곳${generic ? ' — 추가 입력으로 좁혀집니다' : ''}</span><span>지역 · 대표업종 · 수주</span></div>`;
    for (const r of (generic ? shown.slice(0, 3) : shown)) { h += row(r, items.length); items.push({ co: r }); }
    if (!rows.length) h += `<div class="miss">시안에는 이 낱말의 회사 행을 싣지 않음 — 실제 화면에서는 ${num(total)}곳 중 수주 많은 순 3곳.</div>`;
    if (total > items.length - (kwFirst ? 1 : 0)) h += `<div class="more">유사 명칭 ${num(total - (items.length - (kwFirst ? 1 : 0)))}곳 — 지역 또는 추가 입력으로 좁혀집니다</div>`;
  }
  if (!kwFirst && !biz) { h += `<div class="hd"><span>키워드</span></div>` + kwrow(q, items.length, false); items.push({ kw: q }); }
  ls.innerHTML = h; ls.hidden = false; inp.setAttribute('aria-expanded', 'true');
  live.textContent = miss ? `회사 없음. 키워드 검색 1개` : `회사 ${items.filter(x => x.co).length}곳, 키워드 검색 1개. 화살표로 선택, Enter 로 확정`;
}
function setAct(i) {
  act = i;
  [...ls.querySelectorAll('[role=option]')].forEach((o, k) => o.setAttribute('aria-selected', k === i ? 'true' : 'false'));
  const o = ls.querySelector(`#o${i}`);
  inp.setAttribute('aria-activedescendant', o ? o.id : '');
  o && o.scrollIntoView({ block: 'nearest' });
}
/* Enter/찾기: 고른 행 → 회사가 딱 하나면 그 회사 → 아니면 키워드 행 */
function submit() {
  if (ls.hidden) { render(); if (ls.hidden) return; }
  const cos = items.filter(x => x.co);
  choose(act >= 0 ? act : (cos.length === 1 ? items.findIndex(x => x.co) : items.findIndex(x => x.kw)));
}
inp.addEventListener('input', render);
inp.addEventListener('keydown', e => {
  if (ls.hidden) { if (e.key === 'Enter' && inp.value.trim().length >= 2) { e.preventDefault(); render(); } return; }
  if (e.key === 'ArrowDown') { e.preventDefault(); setAct((act + 1) % items.length); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); setAct((act - 1 + items.length) % items.length); }
  else if (e.key === 'Escape') { close(); }
  else if (e.key === 'Enter') { e.preventDefault(); submit(); }
});
ls.addEventListener('mousedown', e => { const o = e.target.closest('[role=option]'); if (o) { e.preventDefault(); choose(+o.dataset.i); } });
$('#go').addEventListener('click', () => { inp.focus(); submit(); });

/* ---- 넘김 — 여기서는 전환을 만들지 않는다. 결과 페이지가 별도 페이지이고, 그 머리(flow.html 의 관문 장면)가
   도착 즉시 이어받는다. 실제 구현은 location 하나. 시안은 고른 것을 입력란에 남기고 한 줄만 적는다. ---- */
function choose(i) { const it = items[i]; if (it) go(it); }
function go(it) {
  if (it.co) remember(it.co);
  close();
  inp.value = it.co ? it.co.nm : it.kw;
  sent.textContent = it.co ? `${it.co.nm} · ${it.co.rgn} — 결과 페이지로 이동. 머리 장면(flow.html)이 이어받음.` : `"${it.kw}" 키워드 — 회사 없이 결과 페이지로 이동.`;
  paintRecent();
}

/* ---- 상태 알약 — 입력란에 값을 설정하고 같은 render 를 실행. ---- */
const STATES = { empty: '', typing: D.typing, miss: 'ADATA', return: '' };
function state(s) {
  document.querySelectorAll('.ctl span').forEach(x => x.classList.toggle('on', x.dataset.s === s));
  if (s === 'return') { try { localStorage.setItem(KEY, JSON.stringify(D.ret)); } catch {} } else if (s === 'empty') { try { localStorage.removeItem(KEY); } catch {} }
  inp.value = STATES[s]; render(); paintRecent();
  if (s !== 'return') inp.focus();
}
function paintRecent() {
  const r = recent(), el = $('#rc');
  el.innerHTML = r.length ? `<span class="l">최근 조회</span>` + r.map((c, i) => `<a data-i="${i}" tabindex="0" role="button">${c.nm}<small>${c.rgn}${c.ncon ? ' · 수주 ' + c.ncon + '건' : ''}</small></a>`).join('') : '';
  el.querySelectorAll('a').forEach(a => { const f = () => go({ co: r[+a.dataset.i] }); a.onclick = f; a.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); f(); } }; });
}
/* ---- 오늘 등록된 공고 — 세로 틱. 4.5초마다 맨 위에 한 행이 들어오고 맨 아래 행이 나간다. rAF 루프 없음, setTimeout 사슬 하나.
   멈춤: hover · focus-within(링크를 Tab 으로 지나갈 수 있게) · 입력에 글자 · 목록 열림 · 탭 숨김. 움직임 줄이기면 아예 안 돌고 최신 5건 고정. ---- */
const T = JSON.parse($('#tdata').textContent), td = $('#today'), tk = $('#tk'), ki = $('#tki');
let ti = 0;
function trow(r) {
  const a = document.createElement('a'); a.className = 'row'; a.href = '/notices/' + r.no;
  for (const [c, t] of [['t', r.nm], ['o', r.org], ['d', '마감 ' + r.clse], [r.prc ? 'w' : 'w none', r.prc ? r.prc.toLocaleString('ko-KR') + '원' : '추정가 없음']]) { const s = document.createElement('span'); s.className = c; s.textContent = t; a.appendChild(s); }
  return a;
}
for (; ti < Math.min(5, T.length); ti++) ki.appendChild(trow(T[ti]));
function fixH() { tk.style.height = ''; tk.style.height = tk.offsetHeight + 'px'; }   // 블록 높이 = 5행. 틱이 "전체 보기" 를 밀지 않는다
fixH(); addEventListener('resize', fixH);
const paused = () => document.hidden || td.matches(':hover, :focus-within') || inp.value.trim() !== '' || !ls.hidden;
function doTick() {
  if (T.length <= 5) return;
  const a = trow(T[ti++ % T.length]), z = [...ki.querySelectorAll('a.row:not(.out)')].pop();
  a.classList.add('new'); a.style.opacity = '0'; ki.prepend(a);
  const h = a.offsetHeight, ms = parseFloat(getComputedStyle(ki).transitionDuration) * 1000;
  ki.style.transition = 'none'; ki.style.transform = `translateY(-${h}px)`; ki.offsetHeight;   // 새 행만큼 올려 둔 채 reflow
  ki.style.transition = ''; ki.style.transform = ''; a.style.opacity = '';                     // 0 으로 미끄러지며 새 행이 드러남
  z.style.opacity = '0'; z.classList.add('out');                                              // 맨 아래 행은 클립 밖으로 밀려나며 사라짐
  setTimeout(() => z.remove(), ms + 20);
  setTimeout(() => a.classList.remove('new'), 600);
}
function tick() { setTimeout(() => { if (!paused()) doTick(); tick(); }, 4500); }
if (!reduce) tick();

document.querySelectorAll('.ctl span').forEach(x => x.onclick = () => state(x.dataset.s));
document.addEventListener('click', e => { if (!e.target.closest('.box') && !e.target.closest('#ls') && !e.target.closest('.ctl')) close(); });
state(recent().length ? 'return' : 'empty');
"""


def today(t):
    # 행은 JS 가 그린다(처음 5건도) — 틱에서 들어오는 행과 같은 코드.
    return (f'<div class="today" id="today"><span class="k">{t["label"]} 등록된 공고 {t["n"]:,}건</span><div class="tk" id="tk"><div class="tki" id="tki"></div></div><a class="all" href="/notices">전체 보기 →</a>'
            f'<script type="application/json" id="tdata">{json.dumps(t["rows"], ensure_ascii=False)}</script></div>')


def foot(d):
    """gen_entry.foot 과 같은 내용을 공문 톤으로. 공통 함수는 옛 시안이 쓰므로 두고 여기서만 다시 쓴다."""
    lg = d["log"]
    return (f'<div class="foot"><b>키워드 검색이 회사 검색과 같은 무게인 이유.</b> 최근 7일 사용자 검색 {lg["tot"]}건 중 {lg["miss"]}건({lg["miss"] / lg["tot"] * 100:.0f}%)이 회사로 해석되지 않음 — '
            f'{lg["kw"]}건은 처음부터 키워드 모드, {lg["nf"]}건은 회사 모드에서 "회사를 찾을 수 없습니다". 입력 문자열은 '
            + " · ".join(f'"{w}"' for w in TYPED[:5]) + ' 등 업종·품목·브랜드. '
            f'동명 회사 목록의 회사·지역·업종·수주는 실제 행이며 사업자등록번호는 가운데를 가림. 입찰 가능 {d["active"]:,}건은 {date.today()} 기준 마감 90일 이내 공고 수. '
            f'목록은 ↑↓ Enter Esc, role=combobox/listbox, aria-activedescendant. 아래 알약은 입력란에 값을 설정하고 같은 코드를 실행 — 입력란에 직접 입력해도 동일 '
            f'(동명 묶음: {", ".join(COLLISIONS)}).</div>')


def page(d):
    data = dict(groups=d["groups"], counts=d["counts"], active=d["active"], ret=d["ret"], typing=COLLISIONS[0])
    body = (f'<div class="entry"><div class="box"><input id="q" type="text" autocomplete="off" spellcheck="false" placeholder="회사명 · 사업자등록번호 · 업종 또는 품목" '
            f'role="combobox" aria-expanded="false" aria-controls="ls" aria-autocomplete="list" aria-label="회사명, 사업자등록번호, 업종 또는 품목" enterkeyhint="search">'
            f'<button type="button" class="go" id="go" aria-label="찾기"><span class="t">찾기</span><span class="ar" aria-hidden="true">→</span></button></div>'
            f'<ul id="ls" role="listbox" class="ls" hidden aria-label="회사 또는 키워드"></ul><div id="live" class="sr" aria-live="polite"></div>'
            f'<p class="pr">입찰 가능 공고 <b>{d["active"]:,}</b>건 중 참가 자격이 있는 공고만 선별합니다</p>'
            f'<div class="rc" id="rc"></div><div class="sent" id="sent"></div>{today(d["today"])}</div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 입구 — 검색창 하나</title>{FONT}<style>{CSS}</style></head><body>'
            f'<div class="wrap">{nav()}{body}{foot(d)}</div>{ctl()}'
            f'<script type="application/json" id="data">{json.dumps(data, ensure_ascii=False)}</script><script>{JS}</script></body></html>')


if __name__ == "__main__":
    out = sys.argv[1].rstrip("/\\")
    conn = connect()
    d = fetch(conn); d["today"] = fetch_today(conn)
    with open(f"{out}/entry-simple.html", "w", encoding="utf-8") as f:
        f.write(page(d))
    lg = d["log"]
    print(f'active={d["active"]:,}  7d user searches={lg["tot"]} unresolved={lg["miss"]} ({lg["miss"] / lg["tot"] * 100:.1f}%)  {d["today"]["label"]} {d["today"]["n"]} rows={len(d["today"]["rows"])}')

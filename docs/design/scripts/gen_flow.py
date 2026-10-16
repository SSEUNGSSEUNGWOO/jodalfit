"""결과 페이지(`prototypes/flow.html`) — 머리 장면 "흐름" + 걸러낸 기준 띠 + 표, 그리고 네 상태(0건 / 오류·지연 / 이메일 뒤 / 검토 뒤).

머리 장면: 공고 하나가 선 하나. 지금 입찰 가능한 공고 전부를 그린다.
핵심은 '셀 수 없음 → 셀 수 있음'으로 넘어가는 순간이다.
  9,374 : 선 간격이 1px 한참 아래 — 덩어리로 보인다(세어볼 생각조차 안 든다)
    835 : 벌어지기 시작한다
    372 : 선이 하나하나 보인다
     12 : 센다
이 변화를 띠 두께나 퍼센트 글자로 흉내낼 수 없어서, 진짜로 전부를 캔버스에 그린다.
관문은 통로만 뚫린 세로 벽 3개. 막힌 선은 떨어지지 않고 벽면에서 눌려 흩어진다 —
그 공고들이 나쁜 게 아니라 '이 회사'에 해당되지 않을 뿐이라서.
흐름이 끝나면 캔버스는 접히고 '9,374 → 835 → 372 → 12' 한 줄, 걸러낸 기준 띠, 표가 남는다.

선 기하는 JS에서 씨앗 고정 PRNG로 한 번만 만들고(Float32Array), 매 프레임은
코호트별 Path2D 4개를 clip 안에서 stroke 만 한다 — 9,000여 개를 60fps로 유지하는 유일한 방법.

2026-10-16 결정 반영: 주황 #f97316(선으로만, 로고 타일 예외) · 공문 톤 · 로고 lockup(brand/) · 기준 띠 상시 노출.
원천 JSON 은 `data/`(gen_data.py 가 만든다 — 임시 파일에 두지 않는다).
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_flow.py ../docs/design/data/sample.json ../docs/design/data/funnel.json ../docs/design/data/scene_titles.json ../docs/design/prototypes/flow.html
"""
import html
import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import won, dleft  # noqa: E402
from gen_results_v2 import strongest  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v6 import crit, CRIT_CSS  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

ORANGE = "#f97316"
W, H, CY = 1120, 392, 196
XS = [0, 288, 576, 864]      # 구간 시작 x — 벽은 288 / 576 / 864 에 같은 간격
FAN_X, FAN_SP = 936, 150     # 살아남은 선이 표의 줄 위치로 펼쳐지는 지점
# 통로 반높이. 이번엔 두께가 아니라 **선 간격**이 비율을 말한다 — 372개가 눈에 하나씩 보이려면
# 통로가 충분히 높아야 하고(간격 0.8px ≈ retina 1.6device px), 그래서 통로는 조금씩만 좁아진다.
HH = [180, 160, 150, 100]
CONV, PRESS = 44, 44         # 통로 폭으로 모이는 거리 / 벽 앞에서 눌렸다 흩어지는 거리
LABS = 56                    # 캔버스 위 라벨 줄 높이

# (출처, 왼쪽 x, 기준선 y) — 1구간 6개, 2구간 3개. 각자 자기 줄을 쓰고 벽을 넘지 않는다.
TW = XS[1] - 32              # 제목 최대폭
SPOTS = ([("drop_ind", 16, 58), ("drop_ind", 16, 108), ("drop_ind", 16, 158),
          ("drop_ind", 16, 208), ("drop_ind", 16, 258), ("drop_ind", 16, 308)]
         + [("drop_rgn", 304, 96), ("drop_rgn", 304, 188), ("drop_rgn", 304, 280)])

# 벽마다 '왜 막혔나' 한 줄(공문 톤). 막힌 쪽(벽 왼쪽)에 오른쪽 끝을 벽에 붙이고,
# 그 벽이 실제로 막기 시작할 때 나타난다. 그림이 주장이고 글자는 캡션이라 작고 조용하게.
RSN_Y = 346
REASONS = [(XS[1], "등록업종 미허용"),
           (XS[2], "면허·지역 제한 미충족"),
           (XS[3], "회사와의 유사도 낮음")]

# brand/tile.svg 그대로(22px) — 주황 면 + 흰 마크는 로고 타일에서만 허용되는 예외
TILE = ('<svg viewBox="0 0 64 64" width="22" height="22" aria-hidden="true"><rect width="64" height="64" rx="14.08" fill="#f97316"/>'
        '<path d="M30 14 H50 V34 M14 30 V50 H34" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>')


CSS = SHEET_CSS.replace("#e8431b", ORANGE) + CRIT_CSS + r"""
.wrap { width:auto; max-width:1120px; padding:0 20px 120px }
.brand { font-weight:800; font-size:16px; letter-spacing:-0.035em; gap:8px } .brand svg { display:block }
.ok::after { color:#141414 }   /* ✓ 는 먹 — 초록 폐기(공고 시안 결정) */
.q { padding:26px 0 0; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.stage { margin-top:20px; border-top:1px solid #141414; cursor:pointer } .done .stage, .st-err .stage { cursor:auto }
.labs { position:relative; height:56px; overflow:hidden; transition:height .5s cubic-bezier(.3,.7,.2,1) }
.field { position:relative; height:392px; overflow:hidden; transition:height .55s cubic-bezier(.3,.7,.2,1) }
.field canvas { display:block; width:100%; height:392px; transition:transform .55s cubic-bezier(.3,.7,.2,1) }
.lab { position:absolute; top:4px; opacity:0; transition:opacity .4s ease } .lab.on { opacity:1 }
.lab.g { border-left:1px solid #d8d6d0; padding-left:12px }
.lab .k { display:block; font-size:12px; color:#55554f; white-space:nowrap; line-height:1.3 }
.lab .n { margin-top:5px; font-size:26px; letter-spacing:-0.04em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums; color:#141414 }
.lab .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:5px }
.lab.last .n { color:#f97316 }
/* 덩어리 위에 글자를 얹으려면 판을 깔아야 읽힌다 — 흰 판 + 회색 글자(대비 5.1:1) */
.ttl { position:absolute; font-size:11.5px; line-height:1.45; color:#6b6b67; letter-spacing:-0.015em; white-space:nowrap;
       overflow:hidden; text-overflow:ellipsis; background:#fff; padding:1px 5px; opacity:0; transition:opacity .35s ease }
.ttl.on { opacity:1 }
/* 탈락 이유는 같은 흰 판을 쓰지만 벽에 오른쪽을 붙이고 한 톤 진하다 — 공고명과 섞이지 않게 */
.ttl.rsn { text-align:right; color:#55554f } .st-zero .rsn[data-w="3"] { display:none }
.chain { display:flex; align-items:baseline; flex-wrap:wrap; gap:10px; font-size:13px; color:#737370; height:0; opacity:0; overflow:hidden; transition:opacity .4s ease .15s, height .4s ease }
.chain b { font-size:17px; font-weight:650; color:#141414; letter-spacing:-0.02em; font-variant-numeric:tabular-nums } .chain b.acc { color:#f97316 } .chain i { font-style:normal; color:#c9c9c4 }
.done .field, .done .labs { height:0 } .done .field canvas { transform:translateY(-150px) }
.done .chain { height:48px; opacity:1; padding-top:16px }
.res { opacity:0; max-height:0; overflow:hidden; transition:opacity .5s ease .2s } .done .res { opacity:1; max-height:none }
/* 오류·지연 — 머리는 셋째 관문 앞에서 멈추고, 받은 숫자는 남긴다 */
.err { display:none; align-items:center; gap:14px; padding:16px 0; border-top:1px solid #141414; font-size:13.5px; color:#141414 } .err .sp { flex:1 }
.st-err .err { display:flex }
/* 0건 — 깔때기 마지막 0 + 기준 띠 + 다음 단계 한 줄 */
.zero { display:none; padding:30px 0 34px; border-bottom:1px solid #141414 }
.zero b { display:block; font-size:17px; font-weight:650; letter-spacing:-0.015em } .zero .dim { display:block; margin-top:6px; font-size:13.5px }
.zero .acts { display:flex; gap:8px; align-items:center; margin-top:18px; flex-wrap:wrap } .zero .in { display:flex; gap:6px }
.zero .in span:first-child { width:300px; max-width:100%; height:36px; border:1px solid #e3e1dc; border-radius:8px; display:flex; align-items:center; padding:0 12px; color:#737370; font-size:13px }
.st-zero .zero { display:block } .st-zero .sheet, .st-zero .okline { display:none }
/* 이메일 뒤 — 게이트 없음, 12건 전부, 확인 한 줄(다음 방문부터 표시하지 않음) */
.okline { display:none; padding:13px 0; border-bottom:1px solid #ececea; font-size:13.5px; color:#55554f } .okline b { color:#141414; font-weight:650 }
.st-email .okline { display:block } .st-email .fade .tr { opacity:1; filter:none; pointer-events:auto } .st-email .gateline { display:none }
.st-email .nav .cta { border:0; color:#55554f }
/* 검토 — 버튼은 주황 헤어라인, 누르면 행 왼쪽 괘선 + "검토함" + 조용한 안내 한 줄 */
.tr { position:relative } .tr.rvd::before { content:""; position:absolute; left:-20px; top:0; bottom:0; width:2px; background:#f97316 }
.rvm { font-style:normal; font-size:11px; font-weight:600; color:#141414; margin-left:8px; letter-spacing:.02em; vertical-align:2px }
.bt.rv { border-color:#f97316 } .bt.rv.on { color:#55554f; border-color:#e3e1dc; cursor:default }
.rvn { padding:9px 0 10px 52px; border-bottom:1px solid #ececea; font-size:12.5px; color:#6b6b67 } .rvn a { color:#141414; border-bottom:1px solid #141414 }
.tr .fit i { margin-right:0 }
.ctl { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap }
.ctl span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff } .ctl i { width:1px; background:#e6e4df; margin:4px 4px }
.foot { max-width:880px; line-height:1.6 }
@media (prefers-reduced-motion: reduce) { .field, .field canvas, .labs, .lab, .ttl, .chain, .res { transition:none !important } }
/* 390 — 번호·근거·추정가·적합 열 생략, 제목 / 기관·마감 두 줄. 머리는 220px */
@media screen and (max-width:520px){
  .wrap { padding:0 16px 90px } .nav .links { gap:14px } .nav .links span:not(.cta) { display:none }
  .q { font-size:12.5px } .q b { font-size:15px; display:block; margin-bottom:2px }
  .labs { height:auto; display:grid; grid-template-columns:repeat(4,1fr); gap:0 10px; padding:10px 0 8px } .lab { position:static; border-left:0; padding-left:0 }
  .lab .k { white-space:normal; font-size:11px } .lab .k .sub { display:none } .lab .n { font-size:18px } .lab .n small { font-size:10.5px; margin-left:3px }
  .done .labs { padding:0 } .field, .field canvas { height:220px } .ttl { display:none }
  .chain { font-size:12px; gap:7px } .chain b { font-size:15px }
  .th { display:none } .tr { grid-template-columns:minmax(0,1fr) auto; grid-template-areas:"t t" "o d"; gap:3px 12px; padding:12px 0 }
  .tr .no, .tr .why, .tr .r:not(.d) { display:none } .tr .t { grid-area:t; white-space:normal; font-size:14px; line-height:1.4 } .tr .org { grid-area:o } .tr .d { grid-area:d; font-size:13px }
  .tr.rvd::before { left:-16px }
  .x { padding-left:0; grid-template-columns:1fr; gap:18px } .rvn { padding-left:0 }
  .gateline { flex-wrap:wrap; gap:10px } .gateline .in { width:100%; flex-wrap:wrap } .gateline .in span:first-child { flex:1; width:auto }
  .crit { grid-template-columns:1fr; gap:14px } .crit .act { flex-direction:row; align-items:center }
  .ctl { font-size:11.5px; padding:2px; white-space:normal; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px } .ctl span { padding:5px 8px } .ctl i { display:none }
}
"""

# 엔진 — 선 기하·오프스크린 렌더·blit·라벨 칠하기. flow.html 과 entry-flow.html(gen_entry_flow.py)이 같이 쓴다.
# 벽 수는 cfg 의 XS 길이에서 온다(flow 3, 키워드 모드 2). 3벽이면 쪼개기 전과 같은 그림.
ENGINE_JS = r"""
/* Engine(C, cv, L, T, mat): C=cfg, cv=그릴 캔버스, L=구간 라벨(.lab), T=전진선에 묶인 글자(.ttl)
   mat(선택) = { nb: 불투명도 버킷 수, of(i): 선 i 의 버킷, pen(g, c, b, dflt): 코호트 c·버킷 b 의 [strokeStyle, lineWidth] }
   — entry-flow 가 상태 0 의 재료(선마다 다른 불투명도)를 체에도 그대로 쓰기 위한 것. 없으면 flow.html 과 같은 그림. */
function Engine(C, cv, L, T, mat){
const {W, H, CY, XS, HH, CNT, FAN_X, FAN_SP, CONV, PRESS} = C;
const NW = XS.length - 1, S = NW + 1, N = CNT[0];   // 벽 수 / 구간 수(=코호트 수) / 선 수
const NB = mat && mat.nb || 1, bucketOf = mat && mat.of || (() => 0);
const ctx = cv.getContext('2d');

/* ---- 선 기하: 한 번만 계산한다 ---------------------------------------- */
function rng(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }

// 살아남는 선은 씨앗 고정으로 고른다 — 그림이 매번 같아야 비교가 된다.
// 뒤섞은 뒤 앞에서 835 / 372 / 12 를 잘라 쓰면 자동으로 부분집합이 된다. (어느 칸이 0 이어도 된다 — 0건 상태)
const rnd = rng(7), idx = new Int32Array(N);
for (let i=0;i<N;i++) idx[i]=i;
for (let i=N-1;i>0;i--){ const j=(rnd()*(i+1))|0, t=idx[i]; idx[i]=idx[j]; idx[j]=t; }

const fate = new Uint8Array(N).fill(1);          // 1=1번 벽에서 막힘 … S=끝까지 통과
const alive = [];
for (let s=1;s<=NW;s++){
  const a = Int32Array.from(idx.slice(0, CNT[s])).sort();
  for (const i of a) fate[i] = s+1;
  alive.push(a);
}

// Y[i*S+s] = s 구간에서의 y. 각 구간마다 생존자를 통로 전체에 고르게 다시 편다 —
// 간격이 벌어지는 것이 곧 '몇 개가 남았나'이다.
// 간격이 1px 아래로 내려가면 '고르게 배치'가 장치 픽셀 격자와 맞물려 굵은 무아레 띠를 만든다.
// 0.45px 지터로 위상을 흩는다 — 공고가 실제로 고른 간격일 리도 없다.
const Y = new Float32Array(N*S);
const jit = p => p < 1.2 ? (rnd()*2-1)*0.45 : 0;
const pitch = s => 2*HH[s] / Math.max(1, CNT[s]-1);
for (let i=0;i<N;i++) Y[i*S] = CY + (i/(N-1)*2-1)*HH[0] + jit(pitch(0));
for (let s=1;s<=NW;s++){
  const a = alive[s-1], m = a.length, pj = pitch(s);
  for (let r=0;r<m;r++) Y[a[r]*S+s] = CY + (m===1?0:r/(m-1)*2-1)*HH[s] + jit(pj);
}

// 코호트(×버킷)별 Path2D. 매 프레임 새로 만들지 않는다 — 이게 60fps 의 전부다.
// mat.wander(i, x) 가 있으면 직선 구간이 결 있는 폴리라인이 된다(entry-flow — 체 안의 선이 자유 구간과 같은 재료여야 이음새가 없다).
const wand = mat && mat.wander, STEP = 22.5;
function run(p, i, x0, x1, y){
  if (!wand){ p.lineTo(x1, y); return y; }
  for (let x = x0 + STEP*((i*0.618034)%1); x < x1; x += STEP) p.lineTo(x, y + wand(i, x));   // 꺾이는 x 를 선마다 어긋나게
  const ye = y + wand(i, x1); p.lineTo(x1, ye); return ye;
}
const P = Array.from({length: S}, () => Array.from({length: NB}, () => new Path2D()));
for (let i=0;i<N;i++){
  const f = fate[i], p = P[f-1][bucketOf(i)];
  let y = Y[i*S], x = 0;
  p.moveTo(0, y + (wand ? wand(i, 0) : 0));
  for (let s=1;s<f;s++){                          // 통과한 벽마다 통로 폭으로 모인다
    const g = XS[s], ny = Y[i*S+s], ye = run(p, i, x, g-CONV, y);
    p.bezierCurveTo(g-20, ye, g-16, ny, g, ny);
    y = ny; x = g;
  }
  if (f < S) run(p, i, x, XS[f], y);              // 벽까지 가서 멈춘다 (아래로 새지 않는다)
  else {
    const ye = run(p, i, x, FAN_X, y), row = CY + (y-CY)/HH[NW]*FAN_SP;
    p.bezierCurveTo(FAN_X+70, ye, W-70, row, W, row);
  }
}

/* ---- 그리기 ------------------------------------------------------------ */
// 막힌 코호트는 '벽 앞에서 눌렸다 벽면에서 흩어진다'. 벽면에서 0 이 아니라 옅게 남겨야
// 잉크가 벽에 닿아 '막혔다'로 읽힌다 — 벽 앞에서 끊기면 그냥 사라진 것이 된다.
function fade(c, x1, a, pressed, tail){
  const g = c.createLinearGradient(0,0,x1,0);
  g.addColorStop(0, `rgba(20,20,20,${a})`);
  g.addColorStop((x1-PRESS)/x1, `rgba(20,20,20,${a})`);
  g.addColorStop((x1-6)/x1, `rgba(20,20,20,${pressed})`);
  g.addColorStop(1, `rgba(20,20,20,${tail})`);
  return g;
}
// 벽 1·2·3 에서 막히는 코호트의 (불투명도, 눌림, 꼬리, 굵기). 남은 선이 적을수록 진하게 — 372개가 하나씩 보여야 한다.
// (알려진 결함: 이 차이가 덩어리 안에 가로 얼룩을 만든다 — README '머리 장면' 참조)
const PEN = [[.055, .16, .03, .30], [.30, .60, .08, .35], [.34, .65, .09, .35]];
// 9,000여 개를 매 프레임 다시 래스터화하면 소프트웨어 래스터라이저에서 70ms 가 넘는다.
// 그림 자체는 움직이지 않고 '어디까지 보이나'만 움직이므로, 한 번 그려서 오프스크린에
// 넣어두고 매 프레임은 왼쪽 일부만 blit 한다 — 선은 하나도 줄이지 않는다.
let off = null, sx = 1, sy = 1, ms = 0;

function defaultPen(g, c){
  if (c < NW){ const a = PEN[c]; return [fade(g, XS[c+1], a[0], a[1], a[2]), a[3]]; }
  const last = g.createLinearGradient(0,0,W,0);   // 마지막 12개만 주황
  last.addColorStop(0, 'rgba(20,20,20,.8)');
  last.addColorStop((XS[NW]-20)/W, 'rgba(20,20,20,.8)');
  last.addColorStop((XS[NW]+30)/W, 'rgba(249,115,22,.9)');
  last.addColorStop(1, 'rgba(249,115,22,.9)');
  return [last, .9];
}
// 벽 k. dy 만큼 위에서 내려오는 중일 수 있다(entry-flow 의 '벽이 떨어진다').
function wall(g, k, dy){
  const x = XS[k]; dy = dy || 0;
  g.strokeStyle = '#141414';
  for (const sg of [-1, 1]){
    g.lineWidth = 2.5; g.beginPath();              // 벽은 화면 끝까지, 통로만 뚫려 있다
    g.moveTo(x, (sg<0 ? 0 : CY+HH[k]) + dy); g.lineTo(x, (sg<0 ? CY-HH[k] : H) + dy); g.stroke();
    g.lineWidth = 1.5; g.beginPath();              // 통로 입술 — 구멍임을 분명히
    g.moveTo(x-7, CY+sg*HH[k]+dy); g.lineTo(x+7, CY+sg*HH[k]+dy); g.stroke();
  }
}

function render(){
  const g = off.getContext('2d'), dpr = devicePixelRatio || 1;
  g.setTransform(sx*dpr, 0, 0, sy*dpr, 0, 0);     // 설계 좌표 그대로 쓰고 레티나는 dpr 로. sy 는 390px 의 낮은 머리
  g.clearRect(0, 0, W, H);
  g.lineCap = 'butt';
  for (let c=0;c<S;c++) for (let b=0;b<NB;b++){
    const d = defaultPen(g, c), pen = mat && mat.pen ? mat.pen(g, c, b, d) : d;
    g.strokeStyle = pen[0]; g.lineWidth = pen[1]; g.stroke(P[c][b]);
  }
  for (let k=1;k<=NW;k++) wall(g, k, 0);
}

function setup(){
  const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
  sx = r.width / W; sy = r.height ? r.height / H : 1;
  cv.width = Math.round(r.width*dpr); cv.height = Math.round(H*sy*dpr);
  off = Object.assign(document.createElement('canvas'), {width: cv.width, height: cv.height});
  ctx.setTransform(1, 0, 0, 1, 0, 0);              // blit 는 장치 픽셀로
  render();
}

// front 왼쪽은 체(off), 오른쪽은 behind(있으면 — entry-flow 의 멈춘 덩어리) 아니면 빈 캔버스.
function draw(front, behind){
  const t0 = performance.now();
  const fw = Math.max(1, Math.round(front * sx * (devicePixelRatio || 1)));
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.drawImage(off, 0, 0, fw, cv.height, 0, 0, fw, cv.height);
  if (behind && fw < cv.width) ctx.drawImage(behind, fw, 0, cv.width-fw, cv.height, fw, 0, cv.width-fw, cv.height);
  ms = ms ? ms*.85 + (performance.now()-t0)*.15 : performance.now()-t0;
  window.__ms = ms;
}

// 전진선 x 기준 라벨·글자: 벽을 지나 150px 동안 카운트업, 글자는 제 폭을 다 지나야 뜬다.
function labels(x){
  T.forEach(t => t.classList.toggle('on', x >= +t.dataset.x));
  L.forEach(g => {
    g.classList.toggle('on', x >= +g.dataset.x);
    const span = g.querySelector('.cnt'), to = +span.dataset.to;
    const p = Math.min(1, Math.max(0, (x - g.dataset.x) / 150));
    span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString('ko-KR');
  });
}
function paint(x, settled, behind){
  draw(x, behind);
  labels(x);
  document.body.classList.toggle('done', settled);
}

return {setup, draw, paint, labels, wall, Y, alive, N, S, NW, get sx(){ return sx; }, get off(){ return off; }, get ms(){ return ms; }};
}
"""

# flow.html 전용 실행부 — 고정 타임라인(처음 방문 3.6초 / 재방문 1.1초 / 정지) + 상태 전환(0건 / 오류 / 이메일 뒤 / 검토 뒤).
RUN_JS = r"""
const C = JSON.parse(document.getElementById('cfg').textContent), W = C.W;
const cv = document.getElementById('cv'), $ = s => document.querySelector(s);
const L = [...document.querySelectorAll('.lab')], T = [...document.querySelectorAll('.ttl')];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let E = Engine(C, cv, L, T), cnt = C.CNT;

/* ---- 깔때기 숫자 바꾸기(0건 상태) — 엔진을 다시 만든다. 라벨·경로 줄도 같이 ---- */
function setCounts(c){
  if (c === cnt) return;
  cnt = c; E = Engine(Object.assign({}, C, {CNT: c}), cv, L, T); E.setup();
  L.forEach((g, i) => { g.querySelector('.cnt').dataset.to = c[i]; const s = g.querySelector('.sub'); s.textContent = c[i] === 0 ? (i === 3 ? ' · 없음' : ' · 면허·지역 0% 통과') : s.dataset.k; });
  document.querySelectorAll('.chain b').forEach((b, i) => b.textContent = c[i].toLocaleString('ko-KR'));
}

/* ---- 진행 -------------------------------------------------------------- */
let raf = 0, tmo = 0;
function finish(){ E.paint(W, true); document.body.classList.remove('running'); }
function run(mode){
  cancelAnimationFrame(raf); clearTimeout(tmo);
  document.body.classList.remove('done', 'st-err'); document.body.classList.add('running');
  document.querySelectorAll('.ctl [data-run]').forEach(s => s.classList.toggle('on', s.dataset.run === mode));
  if (mode === 'still') { finish(); return; }
  const dur = mode === 'fast' ? 1100 : 3600, t0 = performance.now();
  const stop = mode === 'err' ? C.XS[3] - 30 : W;      // 오류·지연: 셋째 관문 앞에서 멈춘다 — 받은 숫자(둘)는 남는다
  const tick = now => {
    const p = Math.min(1, (now - t0) / dur), x = Math.min(stop, W * (1 - Math.pow(1 - p, 2.2)));
    E.paint(x, false);
    if (x >= stop && mode === 'err'){ tmo = setTimeout(() => { document.body.classList.add('st-err'); document.body.classList.remove('running'); }, 1200); return; }
    if (p < 1) raf = requestAnimationFrame(tick);
    else tmo = setTimeout(finish, mode === 'fast' ? 150 : 480);
  };
  raf = requestAnimationFrame(tick);
}

// 스테이지 아무 곳이나 누르면(키 아무거나도) 끝 상태로 건너뛴다 — 사용자는 애니메이션이 아니라
// 공고를 보러 왔다. 이미 끝났거나 오류면 아무 일도 하지 않는다. .ctl 은 .stage 밖(fixed)이라 안 걸린다.
function settle(){
  if (document.body.classList.contains('done') || document.body.classList.contains('st-err')) return;
  cancelAnimationFrame(raf); clearTimeout(tmo);
  finish();
}

/* ---- 검토 — 브라우저에 저장(localStorage). 로그인하면 기기 간 유지 ---- */
const RK = 'jf_reviewed';
const reviewed = () => { try { return JSON.parse(localStorage.getItem(RK) || '[]'); } catch (e) { return []; } };
function mark(no){
  const tr = $('.tr[data-no="' + no + '"]'); if (!tr || tr.classList.contains('rvd')) return;
  tr.classList.add('rvd'); tr.querySelector('.t').insertAdjacentHTML('beforeend', '<em class="rvm">검토함</em>');
  const x = tr.nextElementSibling; if (!x || !x.classList.contains('x')) return;
  const b = x.querySelector('.bt.rv'); b.textContent = '검토함'; b.classList.add('on');
  x.insertAdjacentHTML('afterend', '<div class="rvn">검토함은 브라우저에 저장됩니다 · <a href="#">로그인</a> 시 기기 간 유지</div>');
}
function unmark(){
  document.querySelectorAll('.tr.rvd').forEach(tr => { tr.classList.remove('rvd'); tr.querySelector('.rvm').remove(); });
  document.querySelectorAll('.rvn').forEach(n => n.remove());
  document.querySelectorAll('.bt.rv.on').forEach(b => { b.textContent = '검토'; b.classList.remove('on'); });
}
document.querySelectorAll('.bt.rv').forEach(b => b.onclick = e => {
  e.preventDefault(); const no = b.closest('.x').previousElementSibling.dataset.no;
  mark(no); try { localStorage.setItem(RK, JSON.stringify([...new Set([...reviewed(), no])])); } catch (e) {}
});

/* ---- 상태 알약 ---------------------------------------------------------- */
const ST = ['st-zero', 'st-err', 'st-email'];
function setState(st){
  document.body.classList.remove(...ST); document.querySelectorAll('.ctl [data-st]').forEach(s => s.classList.toggle('on', s.dataset.st === st));
  $('.nav .cta').textContent = '이메일 구독';
  if (st !== 'reviewed'){ unmark(); try { localStorage.removeItem(RK); } catch (e) {} }
  setCounts(st === 'zero' ? [C.CNT[0], C.CNT[1], 0, 0] : C.CNT);
  if (st === 'zero'){ document.body.classList.add('st-zero'); run('full'); }
  else if (st === 'err') run('err');
  else if (st === 'email'){ document.body.classList.add('st-email'); $('.nav .cta').textContent = 'you@company.co.kr'; run('still'); }
  else if (st === 'reviewed'){ run('still'); mark($('.tr[data-no]').dataset.no); }
  if (st) document.querySelectorAll('.ctl [data-run]').forEach(s => s.classList.remove('on'));   // 상태 알약이 켜지면 진행 알약은 끈다
}

E.setup();
$('.stage').onclick = settle;
addEventListener('keydown', e => { if (!e.target.closest('.ctl')) settle(); });
document.querySelectorAll('.ctl [data-run]').forEach(s => s.onclick = () => { setState(null); run(s.dataset.run); });
document.querySelectorAll('.ctl [data-st]').forEach(s => s.onclick = () => setState(s.dataset.st));
$('.err .bt').onclick = e => { e.preventDefault(); setState(null); run('full'); };
addEventListener('resize', () => { E.setup(); E.paint(document.body.classList.contains('st-err') ? C.XS[3] - 30 : W, document.body.classList.contains('done')); });
reviewed().forEach(mark);
run(reduce ? 'still' : 'full');
"""
JS = ENGINE_JS + RUN_JS


def esc(s):
    return html.escape(s or "")


def labels(f, n, extra=""):
    steps = [("지금 입찰 가능한 공고", "마감 90일 이내", f["total"]),
             ("등록업종 허용 공고", f'전체의 {f["industry"] / f["total"] * 100:.1f}%', f["industry"]),
             ("참가 자격 통과 공고", f'면허·지역 {f["qualified"] / f["industry"] * 100:.0f}% 통과', f["qualified"]),
             ("검토할 공고", f'앞 단계의 {n / f["qualified"] * 100:.1f}%', n)]
    return '<div class="labs">' + "".join(
        f'<div class="lab {"g" if i else ""} {"last" if i == 3 else ""}" data-x="{XS[i]}" style="left:{XS[i] / W * 100:.3f}%">'
        f'<span class="k">{k}<span class="sub" data-k=" · {s}"> · {s}</span></span><div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div></div>'
        for i, (k, s, v) in enumerate(steps)) + extra + "</div>"


def field(titles):
    # 글자는 전진선이 제 폭을 다 지나간 뒤에만 나타난다 — 잉크보다 앞서 나가면 계측이 아니다
    tx = "".join(f'<div class="ttl" data-x="{x + TW}" style="left:{x / W * 100:.3f}%;top:{y}px;max-width:{TW / W * 100:.3f}%">{titles[src][k if src == "drop_ind" else k - 6]}</div>'
                 for k, (src, x, y) in enumerate(SPOTS))
    # 이유도 .ttl 이다 — 전진선 기준 등장 로직(JS 의 T)을 그대로 쓴다. +14 는 '막히는 걸 본 뒤'.
    rx = "".join(f'<div class="ttl rsn" data-w="{w}" data-x="{x + 14}" style="right:{(W - x) / W * 100:.3f}%;top:{RSN_Y}px">{t}</div>'
                 for w, (x, t) in enumerate(REASONS, 1))
    return f'<div class="field"><canvas id="cv" height="{H}" aria-hidden="true"></canvas>{tx}{rx}</div>'


def cfg():
    return dict(W=W, H=H, CY=CY, XS=XS, HH=HH, FAN_X=FAN_X, FAN_SP=FAN_SP, CONV=CONV, PRESS=PRESS)


def nav():
    return (f'<div class="nav"><a class="brand" href="#">{TILE}조달핏</a>'
            '<div class="links"><b>추천</b><span>검토함</span><span>개선 기록</span><span class="cta">이메일 구독</span></div></div>')


def why_lines(r, org):
    """추천 근거 — 공문 톤(명사형 종결). gen_results_v3.why_lines 의 해라체를 이 페이지에서만 바꾼다."""
    out = []
    for b in r["score_breakdown"]:
        k = b["key"]
        if k == "institution": out.append(f"{esc(org)} — 과거 거래 이력 있음")
        elif k == "region": out.append(f"공고의 지역 제한이 본사 소재지 {esc(b.get('rgn'))}와 일치")
        elif k == "industry_tokens": out.append("등록업종 표현이 허용업종과 중복 — " + ", ".join(esc(m) for m in b.get("matched", [])[:3]))
        elif k == "budget": out.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배 — 유사한 규모")
        elif k == "budget_mismatch": out.append(f"추정가가 회사 평균 수주가의 {b.get('ratio')}배 — 규모 차이 큼")
        elif k == "instt_closed": out.append(f"해당 기관 최근 낙찰의 {int(b.get('repeat_ratio', 0) * 100)}%를 같은 회사가 수주")
    vec = next((b for b in r["score_breakdown"] if b["key"] == "vector"), None)
    if vec: out.append(f"공고 내용과 회사 업종 설명 {esc(vec['label'])}")
    return out


def qual_lines(r, prof):
    """참가 자격 — 파이프라인의 판정(qualification.reasons/failures)을 그대로. 공고 필드 prtcpt_psbl_rgn_nm 으로 다시 추정하지 않는다
    (v3 helper 는 그렇게 해서 '지역 제한 없음' 판정에 '!' 를 붙였다)."""
    q = r.get("qualification") or {}
    fails = set(q.get("failures") or [])
    out = [("warn" if t in fails else "ok", esc(t.replace("면허 ", "면허 — ", 1).replace("지역 ", "지역 — ", 1))) for t in (q.get("reasons") or [])]
    return out + [("todo", "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력")]


def row(i, r):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    s = strongest(r); n, dd = dleft(r["bid_clse_date"])
    return (f'<div class="tr" data-no="{esc(r["bid_ntce_no"])}"><span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="org">{esc(org)}</span>'
            f'<span class="why">{esc(s["label"]) if s else ""}</span><span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
            f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r fit"><i><b style="width:{round(float(r["score"]) * 100)}%"></b></i></span></div>')


def sheet(res, prof):
    """표 — 5건 공개 + 흐림 + 이메일 게이트(비로그인). 첫 행은 참가 자격·추천 근거·진행까지 펼친다. 적합은 숫자 없이 막대만."""
    rows = [row(i, r) for i, r in enumerate(res, 1)]
    r0 = res[0]; org0 = r0.get("dmnd_instt_nm") or r0.get("ntce_instt_nm") or ""
    ql = "".join(f'<li class="{c}">{t}</li>' for c, t in qual_lines(r0, prof)); wl = "".join(f"<li>{w}</li>" for w in why_lines(r0, org0))
    x = (f'<div class="x"><div><span class="k">참가 자격</span><ul>{ql}</ul></div><div><span class="k">추천 근거</span><ul>{wl}</ul></div>'
         f'<div><span class="k">진행</span><div class="life"><span class="on">사전규격</span><span class="on">공고</span><span>입찰</span><span>개찰</span><span>낙찰</span><span>계약</span></div>'
         f'<div class="acts"><a class="bt dark" href="{esc(r0["bid_ntce_url"])}">나라장터 원문</a><a class="bt rv" href="#">검토</a></div></div></div>')
    gate = (f'<div class="gateline"><b>나머지 {len(res) - 5}건은 이메일 등록 후 공개</b><span class="dim">상위 5건은 등록 없이 공개 · 비밀번호 없음</span><span class="sp"></span>'
            f'<span class="in"><span>you@company.co.kr</span><span class="bt dark">이메일 등록</span></span></div>')
    return (f'<div class="sheet"><div class="okline"><b>이메일 등록 완료</b> · 전체 결과 공개</div>'
            f'<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>'
            f'{rows[0]}{x}{"".join(rows[1:5])}<div class="fade">{"".join(rows[5:])}</div>{gate}</div>')


ZERO = ('<div class="zero"><b>참가 자격이 있는 공고가 없습니다</b><span class="dim">기준 확인 또는 키워드 검색</span>'
        '<div class="acts"><span class="in"><span>키워드 · 업종 또는 품목</span><span class="bt dark">키워드로 공고 검색</span></span><a class="bt" href="#">업종·물품 수정 요청</a></div></div>')
ERR = '<div class="err"><span>결과를 불러오지 못했습니다</span><span class="sp"></span><a class="bt" href="#">다시 시도</a></div>'


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    c = dict(cfg(), CNT=[f["total"], f["industry"], f["qualified"], len(res)])
    chain = (f'<div class="chain"><span class="k">걸러낸 경로</span><b>{f["total"]:,}</b><i>→</i><b>{f["industry"]}</b><i>→</i>'
             f'<b>{f["qualified"]}</b><i>→</i><b class="acc">{len(res)}</b><span>건</span></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(prof["industries"][0] + prof["industries"][1])} · 공급물품 없음</div>'
            f'<div class="stage">{labels(f, len(res))}{field(titles)}{chain}</div>{ERR}'
            f'<div class="res">{crit(co, prof)}{ZERO}{sheet(res, prof)}</div>'
            f'<div class="foot">선 하나가 공고 하나 — {f["total"]:,}개 전부를 그린 머리 장면은 계산 대기 시간을 메우는 가림막(README 머리 장면). '
            f'걸러낸 경로 아래 기준 띠는 상시 노출. 상태 알약: 0건(셋째 칸 0 — 기준 띠가 이유, 키워드 검색·수정 요청), 오류·지연(셋째 관문 앞 정지 — 실제는 8초 초과 시, 받은 숫자 유지, 다시 시도), '
            f'이메일 뒤(게이트 없음, 확인 줄은 다음 방문부터 비표시), 검토 뒤(행 왼쪽 주황 괘선 + 검토함, 브라우저 저장 안내). '
            f'숫자·공고명은 2026-10-16 실제 추천 결과(data/).</div></div>'
            f'<div class="ctl"><span data-run="full">처음 방문</span><span data-run="fast">재방문</span><span data-run="still">움직임 줄이기</span><i></i>'
            f'<span data-st="zero">0건</span><span data-st="err">오류·지연</span><span data-st="email">이메일 뒤</span><span data-st="reviewed">검토 뒤</span></div>'
            f'<script type="application/json" id="cfg">{json.dumps(c)}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 결과 — 흐름</title>{FONT}'
            f'<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>')


def demo():
    cnt = [9374, 835, 372, 12]
    gap = [2 * HH[i] / (cnt[i] - 1) for i in range(4)]
    # 이 시안의 전부: 간격이 '셀 수 없음 → 셀 수 있음'을 넘어가야 한다.
    assert gap[0] < 0.1, f"{cnt[0]}개가 덩어리로 안 보인다 {gap[0]}"
    assert gap[2] * 2 > 1.4, f"{cnt[2]}개가 레티나에서 한 개씩 안 보인다 (device px {gap[2] * 2:.2f})"
    assert gap[3] > 8, f"마지막 {cnt[3]}개를 눈으로 셀 수 없다 {gap[3]}"
    assert gap[0] < gap[1] < gap[2] < gap[3], gap
    assert HH[0] > HH[1] > HH[2] > HH[3], HH        # 통로는 좁아진다 — 체로 읽혀야
    # 캔버스 밖으로 새는 것이 없다 (아래로 흘리는 그림을 쓰지 않는다)
    assert CY + HH[0] <= H and CY - HH[0] >= 0 and CY + FAN_SP <= H and CY - FAN_SP >= 0
    # 제목은 자기 구간 통로 안, 각자 제 줄, 벽을 넘지 않는다
    for src, x, y in SPOTS:
        s = 0 if x < XS[1] else 1
        assert CY - HH[s] + 8 < y < CY + HH[s] - 8, (x, y)
        assert x + TW <= XS[s + 1], (x, y)
    for a in range(len(SPOTS)):
        for b in range(a + 1, len(SPOTS)):
            assert SPOTS[a][1] != SPOTS[b][1] or abs(SPOTS[a][2] - SPOTS[b][2]) >= 26, (a, b)
    # 탈락 이유: 벽 셋에 하나씩, 막힌 쪽에 붙고, 캔버스 안이며 공고명 줄과 겹치지 않는다
    assert [x for x, _ in REASONS] == XS[1:], REASONS
    assert CY - HH[0] < RSN_Y < CY + HH[0] and RSN_Y + 20 <= H, RSN_Y
    for _, _, y in SPOTS:
        assert abs(y - RSN_Y) >= 26, y
    # 색: 인주는 없다, 주황은 선(로고 타일만 면)
    assert "#e8431b" not in CSS and "232,67,27" not in ENGINE_JS
    print("ok gap(px) =", [round(g, 3) for g in gap], "통로", HH, "이유 y", RSN_Y)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo(); sys.exit()
    if sys.argv[1:2] == ["--rejs"]:   # 원천 JSON 없이 기존 flow.html 의 JS 만 교체 (데이터는 그대로)
        p = sys.argv[2]; h = open(p, encoding="utf-8").read()
        i = h.rindex("<script>") + len("<script>"); j = h.rindex("</script>")
        open(p, "w", encoding="utf-8", newline="\n").write(h[:i] + JS + h[j:]); print("rejs", p); sys.exit()
    src, fsrc, tsrc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src, encoding="utf-8"))
    fn = json.load(open(fsrc))
    tt = {k: [esc(x.strip()) for x in v] for k, v in json.load(open(tsrc, encoding="utf-8")).items()}
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, fn, tt))
    print("written", out)

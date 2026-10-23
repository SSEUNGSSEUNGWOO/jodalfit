"""깔때기 머리 장면 네 안 비교(`prototypes/funnel-variants.html`) — 현행 / 비율 / 띠 / 점 격자.

승우님 지적 둘:
  1. 현행은 건수가 9,900 → 12(99.9%)인데 통로는 180 → 100(44%)만 좁아져 깔때기로 읽히지 않는다.
  2. "단순 줄"뿐이라 디자인이라 할 게 없다.

네 숫자의 **모수가 같지 않다**는 것이 이 비교의 핵심이다. 9,900(마감 90일 이내 전체)과
845(그중 등록업종 허용)는 전수 집계지만, 85 는 **후보 풀 200건 중** 자격 통과 수이고 12 는 최종 결과다.
845 → 85 를 그대로 기하로 그리면 "10배 걸러졌다"는 거짓이 된다. 그래서 C·D 는 모수가 바뀌는
지점(845 → 후보 200)을 **눈에 보이게** 그린다 — 벽이 아니라 점선, 탈락이 아니라 추출.

안: A 현행(gen_flow 엔진 그대로, 비교 기준) / B 통로 높이를 건수에 로그 비례
    / C 회색 띠 하나 + 떨어져 나가는 가는 선 / D 공고 하나 = 점 하나(9,900점 전부).
시안이므로 네 안 모두 **고정 타임라인 2.4초**로 돈다. 구현은 README '머리 장면' 결정대로
실제 진행 이벤트(stageDone)에 묶고 가짜 진행률을 만들지 않는다.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_funnel_variants.py ../docs/design/prototypes/funnel-variants.html
검증: 같은 자리에서 gen_funnel_variants.py --check ../docs/design/prototypes/funnel-variants.html
      (--demo 는 브라우저 없이 로그 비례 수치만 점검)
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_flow import ENGINE_JS, TILE, W, H, CY, XS, HH as HH_A, FAN_X, FAN_SP, CONV, PRESS  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402

# 2026-10-23 실측 — 한종산업개발 주식회사
TOTAL, IND, POOL, PASSED, RESULT = 9900, 845, 200, 85, 12
LABS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "참가 자격 통과 공고", "검토할 공고"]
SUBS = ["마감 90일 이내", "전체의 8.5%", "후보 풀 200건 중", "자격 통과분의 14.1%"]
POOL_LAB = "후보 풀 추출"
ORANGE = "#f97316"


def loghh(counts, lo, hi):
    """건수를 log(n+1) 로 눌러 통로 반높이 [lo, hi] 에 선형 사상. 선형 비례면 마지막 통로가 0.2px 가 된다."""
    ls = [math.log(c + 1) for c in counts]
    a, b = min(ls), max(ls)
    return [round(lo + (x - a) / (b - a) * (hi - lo)) for x in ls]


CNT4 = [TOTAL, IND, PASSED, RESULT]
HH_B = loghh(CNT4, 48, 180)                         # ≈ 180 / 131 / 86 / 48
# C 띠 — 다섯 구간(모수가 바뀌는 200 이 제 칸을 갖는다). 같은 로그 비례를 얇은 범위로 눌렀다.
CXS = [0, 240, 470, 700, 930, W]
CCNT = [TOTAL, IND, POOL, PASSED, RESULT]
CHH = loghh(CCNT, 26, 99)                           # ≈ 99 / 72 / 56 / 47 / 26
CCY, CDROP = 140, 312                               # 띠 중심 / 떨어져 나간 선이 닿는 바닥
# D 점 격자 — 공고 하나 = 점 하나. 칸마다 열 수·간격만 정하면 점 수가 곧 크기다.
DBLK = [{"cx": 130, "cols": 80, "pitch": 2.6}, {"cx": 390, "cols": 24, "pitch": 4.2},
        {"cx": 565, "cols": 14, "pitch": 6.6}, {"cx": 720, "cols": 9, "pitch": 8.4},
        {"cx": 1010, "cols": 1, "pitch": 26}]
DGATE = [292, 480, 647, 880]
# A·B 는 벽 셋(gen_flow 와 같은 말). C·D 는 넷 — 둘째(845 → 후보 200)는 탈락이 아니라 추출이라
# 벽이 아니라 점선이고 글자도 다르다.
LINE_RSN = ["등록업종 미허용", "면허·지역 제한 미충족", "회사와의 유사도 낮음"]
BAND_RSN = ["등록업종 미허용", "후보 풀 200건 추출 — 여기서 모수가 바뀝니다", "면허·지역 제한 미충족", "회사와의 유사도 낮음"]
POOL_GATE = 1

NOTES = {
    "a": "보이는 것 — 선 다발이 벽 셋을 지난다. 통로는 180 → 100 으로 44% 만 좁아진다. "
         "모수 — 처리하지 않는다(네 숫자를 같은 모수로 늘어놓는다). "
         "약한 곳 — 건수가 99.9% 줄어드는데 통로가 거의 그대로여서 깔때기로 읽히지 않고, 85 를 845 와 같은 모수로 보이게 한다.",
    "b": "보이는 것 — 같은 선 다발이되 통로가 180 / 131 / 86 / 48 로 좁아진다(건수의 로그 비례). 마지막 통로에서 12선이 8.7px 간격으로 세어진다. "
         "모수 — 처리하지 않는다. 비율만 바로잡은 안이다. "
         "약한 곳 — 845 → 85 가 '열 배 걸러짐'으로 읽히는 거짓이 그대로 남는다. 형태는 여전히 선 다발 하나다.",
    "c": "보이는 것 — 회색 띠 하나가 관문마다 얇아지고, 떨어져 나가는 몫이 아래로 가는 선들로 흩어진다(이유는 그 아래). "
         "모수 — 둘째 관문은 벽이 아니라 점선이고, 띠가 845 두께에서 후보 200 두께로 줄 때 떨어지는 선을 그리지 않는다. 탈락이 아니라 추출임을 형태로 구분한다. "
         "약한 곳 — 면을 쓰므로 가는 괘선 기조에서 혼자 무겁고, 띠는 공고 하나를 가리키지 않는다(건수는 글자로만 믿어야 한다).",
    "d": "보이는 것 — 공고 하나가 점 하나. 9,900점 격자가 관문마다 통과분만 다음 칸으로 옮겨 가고, 마지막 12점이 표 행 간격으로 내려앉는다(오른쪽 주황 눈금). "
         "모수 — 둘째 관문에서 선택되지 않은 645점은 떨어지지 않고 흐린 채 제자리에 남는다. 후보 200 은 '걸러낸 것'이 아니라 '꺼내 본 것'이다. "
         "약한 곳 — 점 크기가 건수에 비례하지 않아(칸마다 간격이 다르다) 면적으로 비율을 읽을 수 없다. 390px 에서 9,900 칸은 회색 얼룩이 된다.",
}

CSS = r"""
* { box-sizing:border-box }
body { margin:0; background:#faf9f7; color:#141414; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif;
       font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; font-size:14px }
a { color:inherit; text-decoration:none }
.wrap { max-width:1160px; margin:0 auto; padding:0 20px 120px }
.nav { display:flex; align-items:center; justify-content:space-between; padding:18px 0; border-bottom:1px solid #141414 }
.brand { display:flex; align-items:center; gap:8px; font-weight:800; font-size:16px; letter-spacing:-0.035em } .brand svg { display:block }
.nav .r { font-size:12px; color:#6b6b67 }
.q { padding:26px 0 2px; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.q .src { display:block; margin-top:8px; font-size:12px; color:#7a7a76 }
.v { display:none; margin-top:22px } .v.on { display:block }
.vh { display:flex; align-items:baseline; gap:12px; padding-bottom:14px; border-bottom:1px solid #141414 }
.vh b { font-size:16px; font-weight:650; letter-spacing:-0.02em } .vh span { font-size:12.5px; color:#6b6b67 }
.labs { position:relative; height:56px }
.lab { position:absolute; top:4px } .lab.g { border-left:1px solid #d8d6d0; padding-left:12px }
.lab.pool { border-left:1px dashed #b8b6b0 }
.lab .k { display:block; font-size:12px; color:#55554f; white-space:nowrap; line-height:1.3 }
.lab .k .sub { color:#8f8f8b }
.lab .n { margin-top:5px; font-size:26px; letter-spacing:-0.04em; font-weight:650; line-height:1; color:#141414 }
.lab .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:5px }
.lab.last .n { color:#f97316 }
.lab.pool .n { font-size:17px; color:#6b6b67 } .lab.pool .n small { color:#8f8f8b }
.field { position:relative; height:392px }
.field canvas { display:block; width:100%; height:392px }
.rsn { position:absolute; font-size:12px; line-height:1.45; color:#4a4a46; letter-spacing:-0.015em; white-space:nowrap;
       text-align:right; background:#faf9f7; padding:1px 5px; opacity:0; transition:opacity .35s ease }
.rsn.on { opacity:1 } .rsn.pool { color:#6b6b67; text-align:left }
.note { max-width:980px; margin-top:4px; padding:14px 0 0; border-top:1px solid #ececea; font-size:13px; line-height:1.75; color:#55554f }
.foot { max-width:980px; margin-top:40px; padding-top:16px; border-top:1px solid #ececea; font-size:12px; line-height:1.7; color:#7a7a76 }
.ctl { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; background:#fff;
       border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap }
.ctl span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.ctl i { width:1px; background:#e6e4df; margin:4px 4px }
@media (prefers-reduced-motion: reduce) { .rsn { transition:none !important } }
@media screen and (max-width:520px){
  .wrap { padding:0 16px 96px }
  .q b { display:block; margin-bottom:2px }
  /* 칸 수가 안(4 또는 5)마다 다르다 — 열을 고정하지 않고 항상 한 줄에 편다 */
  .labs { height:auto; display:grid; grid-auto-flow:column; grid-auto-columns:minmax(0,1fr); gap:0 8px; padding:10px 0 8px }
  .lab { position:static; border-left:0; padding-left:0 } .lab.pool { border-left:0 }
  .lab .k { white-space:normal; font-size:10.5px } .lab .k .sub { display:none }
  .lab .n { font-size:17px } .lab.pool .n { font-size:14px } .lab .n small { font-size:10px; margin-left:3px }
  .field, .field canvas { height:220px } .rsn { display:none }
  .ctl { font-size:11.5px; padding:2px; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px }
  .ctl span { padding:5px 9px } .ctl i { display:none }
}
"""

RUN_JS = r"""
const C = JSON.parse(document.getElementById('cfg').textContent);
const W = C.W, H = C.H, DUR = 2400;
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const ez = p => 1 - Math.pow(1 - p, 2.2);            // 전진 가속 — 네 안이 같은 곡선을 쓴다
const sstep = p => p <= 0 ? 0 : p >= 1 ? 1 : p*p*(3-2*p);
const lerp = (a, b, p) => a + (b-a)*p;

/* 칸 라벨 — 0..1 진행도를 받아 숫자를 센다. 네 안이 같은 함수를 쓴다(진행도만 제 방식으로 준다). */
function paintLabs(L, prog){
  L.forEach((g, i) => {
    g.classList.toggle('on', prog[i] > 0);
    const s = g.querySelector('.cnt'), to = +s.dataset.to, p = Math.min(1, Math.max(0, prog[i]));
    // 아직 안 받은 칸은 0 이 아니라 '…' — 0 은 "없다"는 실제 값이다(README 숫자 규칙)
    s.textContent = p <= 0 ? '…' : Math.round(to * (1 - Math.pow(1-p, 3))).toLocaleString('ko-KR');
  });
}
function reveal(R, prog){ R.forEach((e, i) => e.classList.toggle('on', prog[i] > 0.35)); }

/* ---- A·B : gen_flow 엔진 그대로. 다른 것은 통로 높이(HH)뿐 ---------------- */
function lines(key, HH){
  const sec = document.querySelector('.v[data-v="'+key+'"]');
  const cv = sec.querySelector('canvas'), L = [...sec.querySelectorAll('.lab')], R = [...sec.querySelectorAll('.rsn')];
  let E = null;
  return {
    setup(){ E = Engine(Object.assign({}, C.base, {HH: HH, CNT: C.cnt4}), cv, L, []); E.setup(); },
    frame(t){
      const x = W * ez(t);
      E.draw(x);
      paintLabs(L, C.base.XS.map(g => (x - g) / 150));
      reveal(R, C.base.XS.slice(1).map(g => (x - g - 14) / 60));
    }
  };
}

/* ---- C 띠 : 두께가 로그 비례. 떨어져 나가는 몫은 아래로 흩어진다 ---------- */
function band(){
  const sec = document.querySelector('.v[data-v="c"]');
  const cv = sec.querySelector('canvas'), L = [...sec.querySelectorAll('.lab')], R = [...sec.querySelectorAll('.rsn')];
  const XS = C.CXS, HH = C.CHH, CY = C.CCY, DROP = C.CDROP, NS = HH.length, TAPER = 56;
  const ctx = cv.getContext('2d');
  let sx = 1, sy = 1;
  function hhAt(x){
    for (let s=0;s<NS;s++){
      if (x > XS[s+1]) continue;
      if (s === NS-1) return HH[s];
      const g = XS[s+1];
      return x > g-TAPER ? lerp(HH[s], HH[s+1], sstep((x-(g-TAPER))/TAPER)) : HH[s];
    }
    return HH[NS-1];
  }
  function setup(){
    const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    sx = r.width / W; sy = (r.height || H) / H;
    cv.width = Math.round(r.width*dpr); cv.height = Math.round(H*sy*dpr);
  }
  function frame(t){
    const front = Math.max(2, W * ez(t)), dpr = devicePixelRatio || 1;
    ctx.setTransform(sx*dpr, 0, 0, sy*dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    // 띠 — 윤곽을 따라 한 번에. 면은 회색이라 '주황은 선' 규칙과 무관하다.
    ctx.beginPath();
    for (let x=0;x<=front;x+=4) ctx.lineTo(x, CY - hhAt(x));
    ctx.lineTo(front, CY - hhAt(front)); ctx.lineTo(front, CY + hhAt(front));
    for (let x=front;x>=0;x-=4) ctx.lineTo(x, CY + hhAt(x));
    ctx.closePath();
    ctx.fillStyle = '#ececea'; ctx.fill();
    ctx.strokeStyle = '#d8d6d0'; ctx.lineWidth = 1; ctx.stroke();
    // 관문
    for (let k=1;k<NS;k++){
      const g = XS[k]; if (front < g) continue;        // 띠가 닿기 전에 관문 표시가 떠 있지 않게
      const h0 = HH[k-1], h1 = HH[k], pool = (k-1) === C.POOL_GATE;
      ctx.save();
      if (pool){                                   // 추출 — 벽이 아니다. 점선 하나, 떨어지는 선 없음
        ctx.setLineDash([4, 4]); ctx.strokeStyle = '#9a9a95'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(g, CY-h0-14); ctx.lineTo(g, CY+h0+14); ctx.stroke();
      } else {
        ctx.strokeStyle = '#141414'; ctx.lineWidth = 1.5;   // 통로 입술 — 띠가 지나는 구멍
        for (const sg of [-1, 1]){
          ctx.beginPath(); ctx.moveTo(g-9, CY+sg*h1); ctx.lineTo(g+9, CY+sg*h1); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(g, CY+sg*h1); ctx.lineTo(g, CY+sg*h0); ctx.stroke();
        }
        const vis = Math.min(1, Math.max(0, (front - g) / 90));   // 떨어져 나가는 몫
        if (vis > 0){
          ctx.strokeStyle = 'rgba(20,20,20,.30)'; ctx.lineWidth = .6;
          for (let i=0;i<18;i++){
            const u = i/17, y0 = CY + lerp(h1, h0, 0.1+0.9*u), x1 = g + 34 + u*86, y1 = DROP - u*10;
            ctx.beginPath(); ctx.moveTo(g-2, y0);
            ctx.bezierCurveTo(g+16, y0, x1-26, y1, g + (x1-g)*vis, lerp(y0, y1, vis));
            ctx.stroke();
          }
        }
      }
      ctx.restore();
    }
    paintLabs(L, XS.slice(0, NS).map(g => (front - g) / 150));
    reveal(R, XS.slice(1, NS).map(g => (front - g - 14) / 60));
  }
  return {setup, frame};
}

/* ---- D 점 격자 : 공고 하나 = 점 하나. 9,900점을 전부 그린다 --------------- */
function dots(){
  const sec = document.querySelector('.v[data-v="d"]');
  const cv = sec.querySelector('canvas'), L = [...sec.querySelectorAll('.lab')], R = [...sec.querySelectorAll('.rsn')];
  const BLK = C.DBLK, CNT = C.CCNT, NS = CNT.length, N = CNT[0], NT = NS-1;
  const ctx = cv.getContext('2d');
  let sx = 1, sy = 1;

  // 씨앗 고정 — 그림이 매번 같아야 비교가 된다(gen_flow 와 같은 PRNG·같은 방식)
  function rng(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a);
    t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
  const rnd = rng(7), idx = new Int32Array(N);
  for (let i=0;i<N;i++) idx[i]=i;
  for (let i=N-1;i>0;i--){ const j=(rnd()*(i+1))|0, t=idx[i]; idx[i]=idx[j]; idx[j]=t; }
  const ends = new Uint8Array(N);                   // 이 점이 마지막으로 서는 칸
  const rank = new Int32Array(N*NS).fill(-1);
  for (let i=0;i<N;i++) rank[i*NS] = i;
  for (let s=1;s<NS;s++){
    const a = Int32Array.from(idx.slice(0, CNT[s])).sort();
    a.forEach((i, r) => { ends[i] = s; rank[i*NS+s] = r; });
  }
  // 칸 안 자리 — 열 수·간격만 주면 점 수가 곧 덩어리 크기다
  const pos = new Float32Array(N*NS*2);
  for (let s=0;s<NS;s++){
    const b = BLK[s], cols = b.cols, p = b.pitch, rows = Math.ceil(CNT[s]/cols);
    const x0 = b.cx - (cols-1)*p/2, y0 = C.CY - (rows-1)*p/2;
    for (let i=0;i<N;i++){
      const r = rank[i*NS+s]; if (r < 0) continue;
      pos[(i*NS+s)*2] = x0 + (r % cols)*p;
      pos[(i*NS+s)*2+1] = y0 + Math.floor(r/cols)*p;
    }
  }
  const T0 = 0.10, TL = 0.18, TG = 0.22;            // 관문 넷의 시작·길이·간격
  const NB = 6;

  function setup(){
    const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    sx = r.width / W; sy = (r.height || H) / H;
    cv.width = Math.round(r.width*dpr); cv.height = Math.round(H*sy*dpr);
  }
  function frame(t){
    const dpr = devicePixelRatio || 1;
    ctx.setTransform(sx*dpr, 0, 0, sy*dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    let done = 0, act = -1, lp = 0;
    for (let k=0;k<NT;k++){
      const a = T0 + k*TG;
      if (t >= a + TL) done = k+1;
      else if (t >= a){ act = k; lp = sstep((t-a)/TL); }
    }
    // 관문 자리 — 추출(둘째)만 점선, 나머지는 먹 헤어라인
    for (let k=0;k<NT;k++){
      if (t < T0 + k*TG) continue;
      const g = C.DGATE[k], pool = k === C.POOL_GATE;
      ctx.save(); ctx.lineWidth = 1;
      if (pool){ ctx.setLineDash([4, 4]); ctx.strokeStyle = '#9a9a95'; } else ctx.strokeStyle = '#d8d6d0';
      ctx.beginPath(); ctx.moveTo(g, 40); ctx.lineTo(g, H-52); ctx.stroke(); ctx.restore();
    }
    // 점 — 불투명도 버킷으로 묶어 한 번에 칠한다(9,900번 fillStyle 을 바꾸지 않는다).
    // Path2D 는 비울 수 없어 매 프레임 새로 만든다(6개뿐).
    const B = Array.from({length: NB}, () => new Path2D());
    // 390px 에서는 설계 좌표가 0.33 배로 눌려 2px 점이 사라진다 — 장치 픽셀로 1.5px 는 되게 키운다
    const sz = Math.max(2, 1.5 / Math.min(sx, sy));
    for (let i=0;i<N;i++){
      const e = ends[i];
      let s, a, dy = 0;
      if (act >= 0 && e > act){ s = -1; a = .85; }                       // 옮겨 가는 중
      else if (act >= 0 && e === act){                                   // 이 관문에서 떨어진다
        s = act; a = lerp(.85, e === C.POOL_GATE ? .22 : .12, lp);
        dy = e === C.POOL_GATE ? 0 : lp*16;                              // 추출은 제자리, 탈락은 아래로
      }
      // 떨어진 점도 사라지지 않는다 — 그 공고가 나쁜 게 아니라 이 회사에 해당되지 않을 뿐이다
      else if (e < done){ s = e; a = e === C.POOL_GATE ? .22 : .12; dy = e === C.POOL_GATE ? 0 : 16; }
      else { s = Math.min(e, done); a = .85; }
      if (a <= 0.02) continue;
      let x, y;
      if (s < 0){ const o=(i*NS+act)*2, n=(i*NS+act+1)*2; x = lerp(pos[o], pos[n], lp); y = lerp(pos[o+1], pos[n+1], lp); }
      else { x = pos[(i*NS+s)*2]; y = pos[(i*NS+s)*2+1] + dy; }
      const b = Math.min(NB-1, Math.max(0, Math.round(a*(NB-1))));
      B[b].rect(x - sz/2, y - sz/2, sz, sz);
    }
    for (let b=1;b<NB;b++){ ctx.fillStyle = 'rgba(20,20,20,' + (b/(NB-1)*.85).toFixed(3) + ')'; ctx.fill(B[b]); }
    // 마지막 12점은 표 행 자리에 앉는다 — 오른쪽에 주황 눈금(면이 아니라 선)
    if (done >= NT){
      ctx.strokeStyle = 'rgba(249,115,22,.9)'; ctx.lineWidth = 1.5;
      for (let i=0;i<N;i++){
        if (ends[i] !== NS-1) continue;
        const o = (i*NS+NS-1)*2;
        ctx.beginPath(); ctx.moveTo(pos[o]+7, pos[o+1]); ctx.lineTo(pos[o]+44, pos[o+1]); ctx.stroke();
      }
    }
    const prog = [];
    for (let s=0;s<NS;s++) prog.push(s === 0 ? (t-0.02)/0.06 : (t - (T0+(s-1)*TG+TL) + 0.012)/0.06);
    paintLabs(L, prog);
    reveal(R, prog.slice(1).map(p => p*2));
  }
  return {setup, frame};
}

const V = {a: lines('a', C.HH_A), b: lines('b', C.HH_B), c: band(), d: dots()};

/* ---- 공통 타임라인 ------------------------------------------------------- */
// 시안이라 2.4초 고정. 구현은 README '머리 장면' 결정대로 실제 진행 이벤트(stageDone)에 묶는다 — 가짜 진행률 없음.
let cur = 'a', raf = 0;
function play(){
  cancelAnimationFrame(raf);
  const v = V[cur];
  if (reduce){ v.frame(1); return; }
  const t0 = performance.now();
  const tick = now => {
    const t = Math.min(1, (now - t0) / DUR);
    v.frame(t);
    if (t < 1) raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
}
function show(k){
  cur = k;
  document.querySelectorAll('.v').forEach(s => s.classList.toggle('on', s.dataset.v === k));
  document.querySelectorAll('.ctl [data-v]').forEach(s => s.classList.toggle('on', s.dataset.v === k));
  V[k].setup(); play();
}
document.querySelectorAll('.ctl [data-v]').forEach(s => s.onclick = () => show(s.dataset.v));
document.querySelector('.ctl .again').onclick = () => play();
addEventListener('resize', () => { V[cur].setup(); V[cur].frame(1); });
show('a');
window.__seek = t => { cancelAnimationFrame(raf); V[cur].frame(t); };   /* --check 용 */
"""

JS = ENGINE_JS + RUN_JS


def lab(i, x, count, label, sub, pct, cls=""):
    return (f'<div class="lab {cls}" data-x="{x}" style="left:{pct:.3f}%">'
            f'<span class="k">{label}<span class="sub"> · {sub}</span></span>'
            f'<div class="n"><span class="cnt" data-to="{count}">0</span><small>건</small></div></div>')


def labrow(kind):
    """A·B 는 네 칸, C·D 는 후보 200 이 제 칸을 갖는 다섯 칸."""
    if kind == "line":
        return "".join(lab(i, XS[i], CNT4[i], LABS[i], SUBS[i], XS[i] / W * 100, ("g " if i else "") + ("last" if i == 3 else ""))
                       for i in range(4))
    xs = CXS[:5]
    out = []
    for i, (x, c) in enumerate(zip(xs, CCNT)):
        if i == 2:
            out.append(lab(i, x, POOL, POOL_LAB, "845건에서 추출 · 모수 변경", x / W * 100, "g pool"))
        else:
            j = i if i < 2 else i - 1
            out.append(lab(i, x, c, LABS[j], SUBS[j], x / W * 100, ("g " if i else "") + ("last" if i == 4 else "")))
    return "".join(out)


def rsnrow(gates, texts, pool_at):
    out = []
    for k, (x, t) in enumerate(zip(gates, texts)):
        pool = k == pool_at
        st = f"left:{x / W * 100:.3f}%" if pool else f"right:{(W - x) / W * 100:.3f}%"
        out.append(f'<div class="rsn {"pool" if pool else ""}" style="{st};top:{362 if pool else 338}px">{t}</div>')
    return "".join(out)


def variant(key, title, sub, kind, gates):
    texts, pool_at = (LINE_RSN, -1) if kind == "line" else (BAND_RSN, POOL_GATE)
    return (f'<section class="v" data-v="{key}"><div class="vh"><b>{title}</b><span>{sub}</span></div>'
            f'<div class="labs">{labrow(kind)}</div>'
            f'<div class="field"><canvas height="{H}" aria-hidden="true"></canvas>{rsnrow(gates, texts, pool_at)}</div>'
            f'<div class="note">{NOTES[key]}</div></section>')


def page():
    c = dict(W=W, H=H, CY=CY, HH_A=HH_A, HH_B=HH_B, cnt4=CNT4, CXS=CXS, CHH=CHH, CCY=CCY, CDROP=CDROP,
             CCNT=CCNT, DBLK=DBLK, DGATE=DGATE, POOL_GATE=POOL_GATE,
             base=dict(W=W, H=H, CY=CY, XS=XS, HH=HH_A, FAN_X=FAN_X, FAN_SP=FAN_SP, CONV=CONV, PRESS=PRESS))
    body = (f'<div class="wrap"><div class="nav"><a class="brand" href="#">{TILE}조달핏</a>'
            f'<span class="r">머리 장면 비교 — 깔때기 네 안</span></div>'
            f'<div class="q"><b>한종산업개발 주식회사</b>지금 입찰 가능한 공고 {TOTAL:,} · 등록업종 허용 {IND} · '
            f'후보 풀 {POOL} · 참가 자격 통과 {PASSED} · 검토할 공고 {RESULT}'
            f'<span class="src">모수가 같지 않다 — {TOTAL:,}·{IND} 는 전수 집계, {PASSED} 는 후보 풀 {POOL}건 중 자격 통과 수, '
            f'{RESULT} 는 최종 결과. {IND} → {PASSED} 를 그대로 기하로 그리면 거짓이 된다. 네 안이 이 지점을 어떻게 다루는지가 비교의 핵심이다.</span></div>'
            + variant("a", "A 현행", f"통로 {' / '.join(map(str, HH_A))} — 비교 기준(gen_flow 엔진 그대로)", "line", XS[1:])
            + variant("b", "B 비율 깔때기", f"통로 {' / '.join(map(str, HH_B))} — 건수의 로그 비례", "line", XS[1:])
            + variant("c", "C 띠", f"두께 {' / '.join(map(str, CHH))} — 같은 로그 비례, 탈락은 아래로", "band", CXS[1:5])
            + variant("d", "D 점 격자", f"공고 하나 = 점 하나 · {TOTAL:,}점 전부", "band", DGATE)
            + f'<div class="foot">네 안 모두 같은 실측 숫자({TOTAL:,} · {IND} · {POOL} · {PASSED} · {RESULT})와 같은 2.4초 타임라인을 쓴다. '
              f'고정 타임라인은 시안 장치다 — 구현에서는 README 「머리 장면」 결정대로 실제 진행 이벤트에 묶고 가짜 진행률을 만들지 않는다. '
              f'주황은 선·글자뿐(로고 타일만 예외), 띠와 점은 회색. 움직임 줄이기 설정이면 애니메이션 없이 최종 상태만 그린다.</div></div>'
            f'<div class="ctl"><span data-v="a">A 현행</span><span data-v="b">B 비율</span><span data-v="c">C 띠</span><span data-v="d">D 점 격자</span>'
            f'<i></i><span class="again">다시 재생</span></div>'
            f'<script type="application/json" id="cfg">{json.dumps(c)}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 — 머리 장면 깔때기 네 안</title>{FONT}<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>')


def demo():
    # B 의 전부: 벽 사이가 눈에 띄게 좁아지고, 마지막 통로에서 12선을 셀 수 있어야 한다
    gap = [2 * HH_B[i] / (CNT4[i] - 1) for i in range(4)]
    assert HH_B[0] > HH_B[1] > HH_B[2] > HH_B[3], HH_B
    assert gap[3] > 8, f"마지막 12개를 눈으로 셀 수 없다 {gap[3]}"
    assert HH_B[3] / HH_B[0] < 0.3, HH_B                      # 현행 0.56 → 깔때기로 읽히는 비율
    assert HH_A[3] / HH_A[0] > 0.5                            # 현행이 실제로 안 좁아진다는 것
    assert CY + HH_B[0] <= H and CY - HH_B[0] >= 0
    # C 띠 — 다섯 칸이 단조 감소하고 떨어지는 선이 캔버스 안에 있다
    assert CHH == sorted(CHH, reverse=True) and len(set(CHH)) == 5, CHH
    assert CCY + CHH[0] < CDROP < H - 60, (CCY, CHH[0], CDROP)
    # D 점 격자 — 칸마다 점이 다 들어가고 칸이 겹치지 않는다
    prev = 0
    for b, n in zip(DBLK, CCNT):
        rows = math.ceil(n / b["cols"])
        w, h = (b["cols"] - 1) * b["pitch"], (rows - 1) * b["pitch"]
        assert CY + h / 2 <= H - 20 and CY - h / 2 >= 20, (n, h)
        assert b["cx"] - w / 2 > prev, (n, b["cx"], prev)
        prev = b["cx"] + w / 2
    assert prev < W, prev
    for k, g in enumerate(DGATE):
        rows = math.ceil(CCNT[k] / DBLK[k]["cols"])
        assert DBLK[k]["cx"] + (DBLK[k]["cols"] - 1) * DBLK[k]["pitch"] / 2 < g < DBLK[k + 1]["cx"] - (DBLK[k + 1]["cols"] - 1) * DBLK[k + 1]["pitch"] / 2, (k, g)
    # 색: 인주 없음, 주황 면 없음
    assert "#e8431b" not in CSS and "#e8431b" not in RUN_JS
    assert "background:#f97316" not in CSS and "background:" + ORANGE not in CSS
    print("ok HH_B =", HH_B, "gap(px) =", [round(g, 2) for g in gap], "/ CHH =", CHH)


SHOTS = ["a", "b", "c", "d"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    want = ["9,900", "845", "85", "12"]
    rules = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
      return { orange: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
        injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderBottomColor, c.borderLeftColor, c.borderRightColor].includes('rgb(232, 67, 27)'); }),
        overflow: document.documentElement.scrollWidth > window.innerWidth } }"""
    ink = """() => { const cv = document.querySelector('.v.on canvas'), g = cv.getContext('2d');
      const d = g.getImageData(0, 0, cv.width, cv.height).data; let n = 0;
      for (let i=3;i<d.length;i+=4) if (d[i] > 8) n++;
      return n / (cv.width*cv.height); }"""
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 1000}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        for k in SHOTS:
            pg.click(f'.ctl [data-v="{k}"]'); pg.wait_for_timeout(120)
            pg.evaluate("t => window.__seek(t)", 1.2 / 2.4)                     # 진행 중(1.2초)
            mid = pg.evaluate(ink)
            assert mid > 0.002, f"{k} 진행 중 캔버스가 비었다 {mid}"
            pg.screenshot(path=str(out / f"_shot_funnel_{k}_mid.png"), full_page=True)
            pg.evaluate("window.__seek(1)")                                     # 끝난 뒤
            end = pg.evaluate(ink)
            assert end > mid, f"{k} 끝이 진행 중보다 비었다 {mid} → {end}"
            nums = pg.evaluate("""() => [...document.querySelectorAll('.v.on .lab:not(.pool) .cnt')].map(e => e.textContent)""")
            assert nums == want, (k, nums)
            s = pg.evaluate(rules)
            assert s["orange"] == 0 and not s["injuk"] and not s["overflow"], (k, s)
            pg.screenshot(path=str(out / f"_shot_funnel_{k}_end.png"), full_page=True)
            print(f"  {k}: 덮임 {mid * 100:.2f}% → {end * 100:.2f}%, 숫자 {nums}")
        # 390 — 라벨 넉 칸 격자, 캔버스 220px, 가로 넘침 없음
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        pg.click('.ctl [data-v="d"]'); pg.wait_for_timeout(120); pg.evaluate("window.__seek(1)")
        m = pg.evaluate("""() => ({ h: document.querySelector('.v.on canvas').getBoundingClientRect().height,
            overflow: document.documentElement.scrollWidth > 390, rsn: getComputedStyle(document.querySelector('.v.on .rsn')).display })""")
        assert round(m["h"]) == 220 and not m["overflow"] and m["rsn"] == "none", m
        assert pg.evaluate(ink) > 0.002
        pg.screenshot(path=str(out / "_shot_funnel_390.png"), full_page=True)
        b.close()
    print("ok 네 안 전환·캔버스 비지 않음·숫자 실제값·인주 0·주황 면 0·390 넘침 없음")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo(); sys.exit()
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    dst = sys.argv[1]
    open(dst, "w", encoding="utf-8", newline="\n").write(page())
    print("written", dst)

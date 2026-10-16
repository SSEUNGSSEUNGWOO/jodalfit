"""시안 "흐름" — 공고 하나가 선 하나. 지금 입찰 가능한 9,285개를 전부 그린다.

핵심은 '셀 수 없음 → 셀 수 있음'으로 넘어가는 순간이다.
  9,285 : 선 간격이 1px 한참 아래 — 덩어리로 보인다(세어볼 생각조차 안 든다)
    831 : 벌어지기 시작한다
    385 : 선이 하나하나 보인다
     12 : 센다
이 변화를 띠 두께나 퍼센트 글자로 흉내낼 수 없어서, 진짜로 9,285개를 캔버스에 그린다.
관문은 통로만 뚫린 세로 벽 3개. 막힌 선은 떨어지지 않고 벽면에서 눌려 흩어진다 —
그 공고들이 나쁜 게 아니라 '이 회사'에 해당되지 않을 뿐이라서.
흐름이 끝나면 캔버스는 접히고 '9,285 → 831 → 385 → 12' 한 줄만 표 위에 남는다.

선 기하는 JS에서 씨앗 고정 PRNG로 한 번만 만들고(Float32Array), 매 프레임은
코호트별 Path2D 4개를 clip 안에서 stroke 만 한다 — 9,285개를 60fps로 유지하는 유일한 방법.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_flow.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/flow.html
"""
import html
import json
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav, table  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

W, H, CY = 1120, 392, 196
XS = [0, 288, 576, 864]      # 구간 시작 x — 벽은 288 / 576 / 864 에 같은 간격
FAN_X, FAN_SP = 936, 150     # 살아남은 선이 표의 줄 위치로 펼쳐지는 지점
# 통로 반높이. 이번엔 두께가 아니라 **선 간격**이 비율을 말한다 — 385개가 눈에 하나씩 보이려면
# 통로가 충분히 높아야 하고(간격 0.78px ≈ retina 1.6device px), 그래서 통로는 조금씩만 좁아진다.
HH = [180, 160, 150, 100]
CONV, PRESS = 44, 44         # 통로 폭으로 모이는 거리 / 벽 앞에서 눌렸다 흩어지는 거리
LABS = 56                    # 캔버스 위 라벨 줄 높이

# (출처, 왼쪽 x, 기준선 y) — 1구간 6개, 2구간 3개. 각자 자기 줄을 쓰고 벽을 넘지 않는다.
TW = XS[1] - 32              # 제목 최대폭
SPOTS = ([("drop_ind", 16, 58), ("drop_ind", 16, 108), ("drop_ind", 16, 158),
          ("drop_ind", 16, 208), ("drop_ind", 16, 258), ("drop_ind", 16, 308)]
         + [("drop_rgn", 304, 96), ("drop_rgn", 304, 188), ("drop_rgn", 304, 280)])

# 벽마다 '왜 막혔나' 한 줄. 막힌 쪽(벽 왼쪽)에 오른쪽 끝을 벽에 붙이고,
# 그 벽이 실제로 막기 시작할 때 나타난다. 그림이 주장이고 글자는 캡션이라 작고 조용하게.
RSN_Y = 346
REASONS = [(XS[1], "등록업종이 허용되지 않음"),
           (XS[2], "면허·지역 제한에 걸림"),
           (XS[3], "회사와 덜 가까움")]


CSS = SHEET_CSS + r"""
.q { padding:26px 0 0; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.stage { margin-top:20px; border-top:1px solid #141414; cursor:pointer } .done .stage { cursor:auto }
.labs { position:relative; height:56px; overflow:hidden; transition:height .5s cubic-bezier(.3,.7,.2,1) }
.field { position:relative; height:392px; overflow:hidden; transition:height .55s cubic-bezier(.3,.7,.2,1) }
.field canvas { display:block; width:100%; height:392px; transition:transform .55s cubic-bezier(.3,.7,.2,1) }
.lab { position:absolute; top:4px; opacity:0; transition:opacity .4s ease } .lab.on { opacity:1 }
.lab.g { border-left:1px solid #d8d6d0; padding-left:12px }
.lab .k { display:block; font-size:12px; color:#55554f; white-space:nowrap; line-height:1.3 }
.lab .n { margin-top:5px; font-size:26px; letter-spacing:-0.04em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums; color:#141414 }
.lab .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:5px }
.lab.last .n { color:#e8431b }
/* 덩어리 위에 글자를 얹으려면 판을 깔아야 읽힌다 — 흰 판 + 회색 글자(대비 5.1:1) */
.ttl { position:absolute; font-size:11.5px; line-height:1.45; color:#6b6b67; letter-spacing:-0.015em; white-space:nowrap;
       overflow:hidden; text-overflow:ellipsis; background:#fff; padding:1px 5px; opacity:0; transition:opacity .35s ease }
.ttl.on { opacity:1 }
/* 탈락 이유는 같은 흰 판을 쓰지만 벽에 오른쪽을 붙이고 한 톤 진하다 — 공고명과 섞이지 않게 */
.ttl.rsn { text-align:right; color:#55554f }
.chain { display:flex; align-items:baseline; gap:10px; font-size:13px; color:#737370; height:0; opacity:0; overflow:hidden; transition:opacity .4s ease .15s, height .4s ease }
.chain b { font-size:17px; font-weight:650; color:#141414; letter-spacing:-0.02em; font-variant-numeric:tabular-nums } .chain b.acc { color:#e8431b } .chain i { font-style:normal; color:#c9c9c4 }
.done .field, .done .labs { height:0 } .done .field canvas { transform:translateY(-150px) }
.done .chain { height:48px; opacity:1; padding-top:16px }
.res { opacity:0; max-height:0; overflow:hidden; transition:opacity .5s ease .2s } .done .res { opacity:1; max-height:none }
.ctl { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px }
.ctl span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.foot { max-width:880px; line-height:1.6 }
/* 적합은 숫자 없이 막대만 (docs/design/README.md 표현·요소 결정 2026-10-15) */
.tr .fit i { margin-right:0 }
@media (prefers-reduced-motion: reduce) { .field, .field canvas, .labs, .lab, .ttl, .chain, .res { transition:none !important } }
"""

# 엔진 — 선 기하·오프스크린 렌더·blit·라벨 칠하기. flow.html 과 entry-flow.html(gen_entry_flow.py)이 같이 쓴다.
# 벽 수는 cfg 의 XS 길이에서 온다(flow 3, 키워드 모드 2). 3벽이면 쪼개기 전과 같은 그림.
ENGINE_JS = r"""
/* Engine(C, cv, L, T): C=cfg, cv=그릴 캔버스, L=구간 라벨(.lab), T=전진선에 묶인 글자(.ttl) */
function Engine(C, cv, L, T){
const {W, H, CY, XS, HH, CNT, FAN_X, FAN_SP, CONV, PRESS} = C;
const NW = XS.length - 1, S = NW + 1, N = CNT[0];   // 벽 수 / 구간 수(=코호트 수) / 선 수
const ctx = cv.getContext('2d');

/* ---- 선 기하: 한 번만 계산한다 ---------------------------------------- */
function rng(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }

// 살아남는 선은 씨앗 고정으로 고른다 — 그림이 매번 같아야 비교가 된다.
// 뒤섞은 뒤 앞에서 831 / 385 / 12 를 잘라 쓰면 자동으로 부분집합이 된다.
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
const pitch = s => 2*HH[s] / (CNT[s]-1);
for (let i=0;i<N;i++) Y[i*S] = CY + (i/(N-1)*2-1)*HH[0] + jit(pitch(0));
for (let s=1;s<=NW;s++){
  const a = alive[s-1], m = a.length, pj = pitch(s);
  for (let r=0;r<m;r++) Y[a[r]*S+s] = CY + (m===1?0:r/(m-1)*2-1)*HH[s] + jit(pj);
}

// 코호트별 Path2D. 매 프레임 새로 만들지 않는다 — 이게 60fps 의 전부다.
const P = Array.from({length: S}, () => new Path2D());
for (let i=0;i<N;i++){
  const f = fate[i], p = P[f-1];
  let y = Y[i*S];
  p.moveTo(0, y);
  for (let s=1;s<f;s++){                          // 통과한 벽마다 통로 폭으로 모인다
    const g = XS[s], ny = Y[i*S+s];
    p.lineTo(g-CONV, y);
    p.bezierCurveTo(g-20, y, g-16, ny, g, ny);
    y = ny;
  }
  if (f < S) p.lineTo(XS[f], y);                  // 벽까지 가서 멈춘다 (아래로 새지 않는다)
  else {
    p.lineTo(FAN_X, y);
    const row = CY + (y-CY)/HH[NW]*FAN_SP;
    p.bezierCurveTo(FAN_X+70, y, W-70, row, W, row);
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
// 벽 1·2·3 에서 막히는 코호트의 (불투명도, 눌림, 꼬리, 굵기). 남은 선이 적을수록 진하게 — 385개가 하나씩 보여야 한다.
// (알려진 결함: 이 차이가 덩어리 안에 가로 얼룩을 만든다 — README '머리 장면' 참조)
const PEN = [[.055, .16, .03, .30], [.30, .60, .08, .35], [.34, .65, .09, .35]];
// 9,285개를 매 프레임 다시 래스터화하면 소프트웨어 래스터라이저에서 70ms 가 넘는다.
// 그림 자체는 움직이지 않고 '어디까지 보이나'만 움직이므로, 한 번 그려서 오프스크린에
// 넣어두고 매 프레임은 왼쪽 일부만 blit 한다 — 선은 하나도 줄이지 않는다.
let off = null, sx = 1, ms = 0;

function render(){
  const g = off.getContext('2d'), dpr = devicePixelRatio || 1;
  g.setTransform(sx*dpr, 0, 0, dpr, 0, 0);        // 설계 좌표 그대로 쓰고 레티나는 dpr 로
  g.clearRect(0, 0, W, H);
  g.lineCap = 'butt';
  const last = g.createLinearGradient(0,0,W,0);   // 마지막 12개만 인주
  last.addColorStop(0, 'rgba(20,20,20,.8)');
  last.addColorStop((XS[NW]-20)/W, 'rgba(20,20,20,.8)');
  last.addColorStop((XS[NW]+30)/W, 'rgba(232,67,27,.9)');
  last.addColorStop(1, 'rgba(232,67,27,.9)');
  const pen = PEN.slice(0, NW).map((a, c) => [fade(g, XS[c+1], a[0], a[1], a[2]), a[3]]);
  pen.push([last, .9]);
  for (let c=0;c<S;c++){ g.strokeStyle = pen[c][0]; g.lineWidth = pen[c][1]; g.stroke(P[c]); }
  g.strokeStyle = '#141414';
  for (let k=1;k<=NW;k++){
    const x = XS[k];
    for (const sg of [-1, 1]){
      g.lineWidth = 2.5; g.beginPath();            // 벽은 화면 끝까지, 통로만 뚫려 있다
      g.moveTo(x, sg<0 ? 0 : CY+HH[k]); g.lineTo(x, sg<0 ? CY-HH[k] : H); g.stroke();
      g.lineWidth = 1.5; g.beginPath();            // 통로 입술 — 구멍임을 분명히
      g.moveTo(x-7, CY+sg*HH[k]); g.lineTo(x+7, CY+sg*HH[k]); g.stroke();
    }
  }
}

function setup(){
  const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
  sx = r.width / W;
  cv.width = Math.round(r.width*dpr); cv.height = Math.round(H*dpr);
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

function paint(x, settled, behind){
  draw(x, behind);
  T.forEach(t => t.classList.toggle('on', x >= +t.dataset.x));
  L.forEach(g => {
    g.classList.toggle('on', x >= +g.dataset.x);
    const span = g.querySelector('.cnt'), to = +span.dataset.to;
    const p = Math.min(1, Math.max(0, (x - g.dataset.x) / 150));
    span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString('ko-KR');
  });
  document.body.classList.toggle('done', settled);
}

return {setup, draw, paint, Y, N, S, NW, get sx(){ return sx; }, get off(){ return off; }, get ms(){ return ms; }};
}
"""

# flow.html 전용 실행부 — 고정 타임라인(처음 방문 3.6초 / 재방문 1.1초 / 정지).
RUN_JS = r"""
const C = JSON.parse(document.getElementById('cfg').textContent), W = C.W;
const cv = document.getElementById('cv');
const L = [...document.querySelectorAll('.lab')], T = [...document.querySelectorAll('.ttl')];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const E = Engine(C, cv, L, T);

/* ---- 진행 -------------------------------------------------------------- */
let raf = 0;
function run(mode){
  cancelAnimationFrame(raf);
  document.querySelectorAll('.ctl span').forEach(s => s.classList.toggle('on', s.dataset.run === mode));
  if (mode === 'still') { E.paint(W, true); return; }
  const dur = mode === 'fast' ? 1100 : 3600, t0 = performance.now();
  const tick = now => {
    const p = Math.min(1, (now - t0) / dur);
    E.paint(W * (1 - Math.pow(1 - p, 2.2)), false);
    if (p < 1) raf = requestAnimationFrame(tick);
    else setTimeout(() => document.body.classList.add('done'), mode === 'fast' ? 150 : 480);
  };
  raf = requestAnimationFrame(tick);
}

// 스테이지 아무 곳이나 누르면(키 아무거나도) 끝 상태로 건너뛴다 — 사용자는 애니메이션이 아니라
// 공고를 보러 왔다. 이미 끝났으면 아무 일도 하지 않는다. .ctl 은 .stage 밖(fixed)이라 안 걸린다.
function settle(){
  if (document.body.classList.contains('done')) return;
  cancelAnimationFrame(raf);
  E.paint(W, true);
}

E.setup();
document.querySelector('.stage').onclick = settle;
addEventListener('keydown', settle);
document.querySelectorAll('.ctl span').forEach(s => s.onclick = () => run(s.dataset.run));
addEventListener('resize', () => { E.setup(); E.paint(W, document.body.classList.contains('done')); });
run(reduce ? 'still' : 'full');
"""
JS = ENGINE_JS + RUN_JS


def labels(f, n):
    steps = [("지금 입찰 가능한 공고 · 마감 90일 이내", f["total"]),
             (f'업종이 맞는 공고 · 전체의 {f["industry"] / f["total"] * 100:.1f}%', f["industry"]),
             (f'자격이 되는 공고 · 면허·지역 {f["qualified"] / f["industry"] * 100:.0f}% 통과', f["qualified"]),
             (f'검토할 공고 · 앞 단계의 {n / f["qualified"] * 100:.1f}%', n)]
    return '<div class="labs">' + "".join(
        f'<div class="lab {"g" if i else ""} {"last" if i == 3 else ""}" data-x="{XS[i]}" style="left:{XS[i] / W * 100:.3f}%">'
        f'<span class="k">{k}</span><div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div></div>'
        for i, (k, v) in enumerate(steps)) + "</div>"


def field(titles):
    # 글자는 전진선이 제 폭을 다 지나간 뒤에만 나타난다 — 잉크보다 앞서 나가면 계측이 아니다
    tx = "".join(f'<div class="ttl" data-x="{x + TW}" style="left:{x / W * 100:.3f}%;top:{y}px;max-width:{TW / W * 100:.3f}%">{titles[src][k]}</div>'
                 for k, (src, x, y) in enumerate(SPOTS))
    # 이유도 .ttl 이다 — 전진선 기준 등장 로직(JS 의 T)을 그대로 쓴다. +14 는 '막히는 걸 본 뒤'.
    rx = "".join(f'<div class="ttl rsn" data-x="{x + 14}" style="right:{(W - x) / W * 100:.3f}%;top:{RSN_Y}px">{t}</div>'
                 for x, t in REASONS)
    return f'<div class="field"><canvas id="cv" height="{H}" aria-hidden="true"></canvas>{tx}{rx}</div>'


def cfg():
    return dict(W=W, H=H, CY=CY, XS=XS, HH=HH, FAN_X=FAN_X, FAN_SP=FAN_SP, CONV=CONV, PRESS=PRESS)


def sheet(res, prof):
    """gen_results_v4.table() 결과를 이 시안의 표현 결정에 맞게 깎는다.
    (gen_results_v3/v4 는 다른 작업자가 쓰는 중이라 건드리지 않고 문자열에서 뺀다 — README 2026-10-15)
    적합 점수 숫자는 빼고 막대만, '안 맞아요' 는 없애고 '검토 인장' 은 '검토' 로."""
    h = re.sub(r'(<i><b style="width:\d+%"></b></i>)\d+(</span>)', r"\1\2", table(res, prof))
    h = h.replace('<a class="bt" href="#">검토 인장</a><a class="bt txt" href="#"><u>안 맞아요</u></a>',
                  '<a class="bt" href="#">검토</a>')
    assert "안 맞아요" not in h and "검토 인장" not in h, "표 버튼 치환 실패 — gen_results_v4 마크업이 바뀌었다"
    assert not re.search(r"</b></i>\d", h), "적합 숫자가 남았다"
    return h


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    c = dict(cfg(), CNT=[f["total"], f["industry"], f["qualified"], len(res)])
    gap = [2 * HH[i] / (c["CNT"][i] - 1) for i in range(4)]
    chain = (f'<div class="chain"><span class="k">걸러낸 경로</span><b>{f["total"]:,}</b><i>→</i><b>{f["industry"]}</b><i>→</i>'
             f'<b>{f["qualified"]}</b><i>→</i><b class="acc">{len(res)}</b><span>건</span></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(prof["industries"][0] + prof["industries"][1])} · 공급물품 없음</div>'
            f'<div class="stage">{labels(f, len(res))}{field(titles)}{chain}</div>'
            f'<div class="res">{sheet(res, prof)}</div>'
            f'<div class="foot"><b>선 하나가 공고 하나다. {f["total"]:,}개를 전부 그렸다</b> — 줄여 그리거나 띠로 뭉뚱그리지 않았다. '
            f'왼쪽 끝 선 간격은 {gap[0]:.3f}px 라 덩어리로 보이고, 관문을 지날 때마다 {gap[1]:.2f} → {gap[2]:.2f} → {gap[3]:.1f}px 로 벌어져 '
            f'마지막엔 {len(res)}개가 눈으로 세어진다. <b>비율을 말하는 건 두께가 아니라 이 간격</b>이고, 퍼센트 글자는 그걸 확인해줄 뿐이다. '
            f'세로 벽 셋이 관문이고, 통로에 못 든 선은 아래로 떨어지는 게 아니라 벽면에서 눌려 흩어진다 — '
            f'그 공고가 나쁜 게 아니라 이 회사에 해당되지 않을 뿐이고, 같은 공고가 다른 회사에서는 통과한다. '
            f'숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>'
            f'<div class="ctl"><span data-run="full">처음 방문</span><span data-run="fast">재방문(짧게)</span><span data-run="still">움직임 줄이기</span></div>'
            f'<script type="application/json" id="cfg">{json.dumps(c)}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 — 흐름</title>{FONT}'
            f'<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>')


def esc(s):
    return html.escape(s or "")


def demo():
    cnt = [9285, 831, 385, 12]
    gap = [2 * HH[i] / (cnt[i] - 1) for i in range(4)]
    # 이 시안의 전부: 간격이 '셀 수 없음 → 셀 수 있음'을 넘어가야 한다.
    assert gap[0] < 0.1, f"9,285개가 덩어리로 안 보인다 {gap[0]}"
    assert gap[2] * 2 > 1.4, f"385개가 레티나에서 한 개씩 안 보인다 (device px {gap[2] * 2:.2f})"
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

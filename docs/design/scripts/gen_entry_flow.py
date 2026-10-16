"""입구 = 흐름의 첫 장면 (2026-10-16). 검색 입구가 별도 페이지가 아니라 flow.html 머리 장면의 첫 컷이다.

도착하면 지금 입찰 가능한 공고 전부(9,117개 — 실제 수)가 벽 없이 선으로 흐르고 있고, 그 앞에 입력 한 칸.
회사명(또는 사업자번호·하는 일)을 넣고 Enter 치면 **그 회사가 열쇠**다 — 물이 멎고, 같은 캔버스·같은 선 위에
벽 셋이 파이프라인 단계가 끝날 때마다 하나씩 내려앉아 제자리에서 걸러진다. 입구와 결과 머리가 한 장면이 된다.
입구가 말하는 건 "뭘 찾으세요?"가 아니라 "이게 지금 전부입니다. 당신 거만 남겨 드릴게요."

그리기는 gen_flow.ENGINE_JS(선 기하·오프스크린·blit)를 그대로 쓰고, 콤보박스·동명 회사 목록·최근 회사는
gen_entry.JS 를 그대로 쓴다(go/reset 만 이 파일에서 덮어쓴다 — 같은 스크립트 안의 뒤쪽 function 선언이 이긴다).
덩어리는 '재료' 하나로 그린다 — 선마다 불투명도 버킷(매끈한 띠 + 드문 진한 올)과 y 를 따라 위상이 도는 결(다발이 모였다 벌어짐).
자유 구간도 체 안의 막힌 선도 같은 재료(엔진의 mat 훅)라 이음새가 없다. 흐름은 결 있는 띠를 한 번 그려 CSS translateX 로만 민다(JS 0/프레임).
열쇠가 돌면 띠의 현재 위상(transform)을 읽어 캔버스가 같은 그림을 이어받고, 벽은 전진선으로 쓸어 드러내지 않고 위에서 떨어진 뒤 그 구간을 크로스페이드한다.

데이터: 회사 목록·9,117·7일 로그 수치는 gen_entry.fetch(DB). 체의 831·385·12 와 표·공고명은 flow.html 에서 떼 온다 —
flow.html 의 원천 JSON(sample/funnel/scene_titles)은 임시 파일이라 남아 있지 않다. 그래서 9,117(오늘) 과 831(10-15, 모수 9,285) 이
하루 어긋난다. 키워드 길은 벽 둘: 후보 풀 100(프런트가 보내는 candidate_pool 기본값) → 12. 실제 키워드 결과 표본은 없어 표는 싣지 않는다.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_entry_flow.py ../docs/design/prototypes/entry-flow.html
"""
import json
import re
import sys

HERE = __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE)
import gen_entry  # noqa: E402
import gen_flow  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav  # noqa: E402
from jobs.evaluate_recommender import connect  # noqa: E402

FLOW_HTML = f"{HERE}/../prototypes/flow.html"
W, H = gen_flow.W, gen_flow.H
LAM = 360                                 # 결의 파장(px). 띠는 W+LAM 이고 CSS 가 한 파장을 밀어 이음새 없이 돈다
# 재료 — 상태 0 의 덩어리와 벽 사이 자유 구간, 체 안의 막힌 선이 전부 같은 함수를 쓴다(이음새 없음).
MAT = dict(
    A0=.011,                              # 기준 불투명도. 실측 덮임(getImageData 평균) ≈ 22% — 종이에 회색 결. .018 은 38% 로 회색 판이었다
    BF=[.4, .7, 1.1, 1.8, 3.0, 9.0],      # 선마다 다른 불투명도 버킷(배율). 마지막은 3% 만 — 드문 진한 올(.1)
    W1=2.5, T0=2, A1=.6, F1=3.7, A2=.25, F2=8.3,   # (정수 아닌 F 로 띠의 반복을 깬다) 결 1: 진폭, 위상이 y 를 따라 T0 회전 + 매끈한 요동(A·sin(2πF·t)) — 다발이 모였다 벌어진다
    W2=.9,                                # 결 2: 파장 LAM/3, 선마다 무작위 위상 — 올이 서로 넘나든다
    GAMMA=1.0,                            # 살아남은 구간의 불투명도 이득 = (간격비)^GAMMA. 831개가 .018 이면 안 보인다
    LW=.3,                                # 헤어라인(≤ .35)
    DROP=300, FADE=350,                   # 벽이 떨어지는 시간 / 그 구간이 자유→체로 바뀌는 시간 (ms, 재방문 칩은 ×.5)
)
KW_XS, KW_HH = [0, 432, 864], [180, 150, 100]   # 키워드 모드: 벽 둘. 마지막 벽은 회사 모드와 같은 자리라 부채가 같다
KW_POOL, KW_N = 100, 12                   # 후보 풀 = frontend/src/lib/api.ts candidate_pool 기본값 / 검토할 공고 = 회사 표본과 같은 12
FULL_MS, FAST_MS = [700, 1500, 2300], [120, 400, 700]   # 단계 완료 시뮬레이션(처음 방문 / 재방문 칩). 실제 구현은 API 진행 이벤트가 stageDone(k) 를 부른다


# ---------------------------------------------------------------- flow.html 에서 떼 오는 것
def flow_bits(path=FLOW_HTML):
    h = open(path, encoding="utf-8").read()
    cnt = json.loads(re.search(r'id="cfg">(.*?)</script>', h).group(1))["CNT"]
    titles = re.findall(r'<div class="ttl" [^>]*>([^<]*)</div>', h)          # .ttl.rsn 은 class="ttl rsn" 이라 안 걸린다
    i = h.index('<div class="res">') + len('<div class="res">'); j = h.index('<div class="foot">')
    res = h[i:j]
    assert res.endswith("</div>") and len(titles) == len(gen_flow.SPOTS) and cnt[3] == 12, (len(titles), cnt)
    return dict(cnt=cnt, titles=titles, res=res[:-len("</div>")])


# ---------------------------------------------------------------- CSS
for mod in (gen_flow, gen_entry):
    assert mod.CSS.startswith(SHEET_CSS)
CSS = SHEET_CSS + gen_flow.CSS[len(SHEET_CSS):] + gen_entry.CSS[len(SHEET_CSS):] + r"""
.q:empty { padding:0 } .q .back { margin-left:14px; color:#737370; border-bottom:1px solid #d8d6d0; cursor:pointer }
.stage { position:relative; margin-top:14px }
/* 라벨 줄은 회사가 정해진 뒤에만 선다. .done 이 다시 0 으로 접는다(flow CSS) */
.labs { height:0 } body.go:not(.done) .labs { height:56px }
.set { position:absolute; inset:0 } body.kw .co-only, body:not(.kw) .kw-only, body.kw .ttl { display:none }   /* 공고명·탈락 이유는 회사 표본의 것 */
/* 두 캔버스가 한 자리: #drift 는 결 있는 띠를 CSS 로 미는 살아 있는 덩어리, #cv 는 열쇠가 돌면 같은 그림으로 이어받아 벽을 세운다 */
#drift, #cv { position:absolute; left:0; top:0 }
#drift { width:132.143%; animation:drift 15s linear infinite; transition:opacity .45s ease }   /* (W+LAM)/W */
#cv { opacity:0; transition:opacity .45s ease }
.go #drift { opacity:0; animation-play-state:paused } .go #cv { opacity:1 }
@keyframes drift { to { transform:translateX(-24.3243%) } }                                     /* LAM/(W+LAM) — 한 파장이면 이음새가 없다 */
/* 입력은 판 위가 아니라 흐르는 종이 위의 글자다. 상자·그림자 없음 — 글자 뒤에만 종이색 스크림(85%, 번진 가장자리). 선은 그 뒤로 지나간다 */
.plate { position:absolute; left:50%; top:64px; transform:translateX(-50%); width:min(680px,100%); z-index:3; transition:opacity .3s ease, transform .5s cubic-bezier(.3,.7,.2,1) }
.go .plate { opacity:0; pointer-events:none; transform:translate(-50%,-16px) }
.plate .rc, .plate .in, .plate .pr, .plate .ls { background:rgba(255,255,255,.85); box-shadow:0 0 14px 12px rgba(255,255,255,.85) }
.plate .rc { margin-bottom:16px; width:max-content; max-width:100% } .plate .rc:empty { display:none }
.plate .pr { margin:18px 0 0; width:max-content; max-width:100% } .plate .ls { margin-top:16px; max-height:min(52vh,460px); overflow:hidden auto }
.plate .ls li { margin:0; padding-left:8px; padding-right:8px }
/* 목록이 스크롤돼도 키워드 행은 늘 보인다 — 회사 길과 같은 무게라는 약속이 스크롤 아래로 숨으면 거짓이 된다 */
.plate .ls li.kw { position:sticky; bottom:0; background:#fff; border-top:1px solid #141414; z-index:1 }
.field .ttl { z-index:2 }
.kwnote { padding:22px 0; font-size:13.5px; color:#55554f; line-height:1.6; border-bottom:1px solid #ececea }
.foot b { color:#141414; font-weight:600 }
@media (max-width:640px) {
  .field, .field canvas, #drift, #cv { height:280px } .ttl { display:none }
  .plate { left:0; right:0; width:auto; transform:none; top:14px } .go .plate { transform:translateY(-12px) }
  .plate .ls { max-height:44vh }
  body.go:not(.done) .labs { height:66px } .lab .k { white-space:normal; font-size:10.5px; line-height:1.25; max-width:88px } .lab .n { font-size:18px; margin-top:3px }
  .chain { flex-wrap:wrap }
}
@media (prefers-reduced-motion: reduce) { #drift { animation:none } .plate, #drift, #cv { transition:none !important } }
"""

# ---------------------------------------------------------------- JS — 엔진(gen_flow) + 장면 선언 + 콤보박스(gen_entry) + 도착
# 순서가 중요하다: 같은 스크립트에서 function 선언은 **뒤쪽이 이기므로** go/reset 덮어쓰기는 gen_entry.JS 뒤(POST)에,
# gen_entry.JS 끝의 state() → reset() 이 쓰는 const/let 은 그보다 앞(PRE)에 둔다(TDZ).
# $·inp·ls·live·remember·flip·reduce·picked 는 gen_entry.JS 의 것 — 함수 안에서만 쓴다(호출 시점엔 있다).
PRE_JS = r"""
/* ---- 입구 = 첫 장면. 덩어리는 처음부터 흐르고, 회사가 열쇠다. ------------------------------------
   52%: 최근 7일 사용자 검색 395건 중 205건이 회사로 풀리지 않았다(gen_entry.py 머리말) — 키워드 행은 회사 행과 같은 무게로 목록에 선다. */
const J = id => JSON.parse(document.getElementById(id).textContent);
const CFG = { co: J('cfg'), kw: J('cfgkw') }, MAT = J('mat');
const W = CFG.co.W, H = CFG.co.H, N0 = CFG.co.CNT[0];
const cv = document.getElementById('cv'), drift = document.getElementById('drift'), ctx = cv.getContext('2d');
const has2d = !location.search.includes('nocanvas') && !!ctx;        // ?nocanvas — 캔버스 없는 경로 점검
const manual = location.search.includes('manual');                   // ?manual — 단계 이벤트를 밖에서 stageDone(k) 로 준다
let E = null, mode = 'co', phase = 'idle', raf = 0, timers = [];
let landed = 0, drop = null, fade = 1, fadeT0 = 0, spd = 1, jobs = [], FREE = [], srcOff = 0, ox = 0;

/* ---- 재료: 선 i 의 불투명도 버킷과 결. 덩어리·자유 구간·체가 전부 이 함수다 — 그래서 이음새가 없다 ---- */
const hash = i => { let h = Math.imul(i ^ 0x9E3779B9, 2654435761) >>> 0; h ^= h >>> 15; h = Math.imul(h, 2246822519) >>> 0; h ^= h >>> 13; return h / 4294967296; };
function bucket(i){                                                  // y 를 따라 매끈한 띠(진한 다발·옅은 틈) + 선마다 흔들림 + 3% 진한 올
  if (hash(i + 77) < .03) return MAT.BF.length - 1;
  const t = i/N0, n = (Math.sin(2*Math.PI*(7*t+.1)) + Math.sin(2*Math.PI*(17*t+.45)) + Math.sin(2*Math.PI*(41*t+.8)))/3;
  const u = (n+1)/2 + (hash(i)-.5)*.35;
  return Math.max(0, Math.min(MAT.BF.length-2, Math.round(u*(MAT.BF.length-2))));
}
function wander(i, x){                                               // 결 1 은 위상이 y 를 따라 매끈히 돌아 다발을 만들고, 결 2 는 올을 섞는다
  const t = i/N0, p1 = 2*Math.PI*(MAT.T0*t + MAT.A1*Math.sin(2*Math.PI*MAT.F1*t) + MAT.A2*Math.sin(2*Math.PI*MAT.F2*t+1));
  return MAT.W1*Math.sin(2*Math.PI*x/MAT.LAM + p1) + MAT.W2*Math.sin(6*Math.PI*x/MAT.LAM + 2*Math.PI*hash(i+11));
}
const gain = (C, s) => Math.pow((C.HH[s]/(C.CNT[s]-1)) / (C.HH[0]/(C.CNT[0]-1)), MAT.GAMMA);   // 남은 선이 적을수록 진하게
const ink = v => `rgba(20,20,20,${Math.min(.6, v)})`;
// 체(오프스크린)의 펜: 코호트 c 는 구간 0..c 를 지나며 구간마다 gain(s), 벽 앞 PRESS 에서 눌렸다 꼬리로. 마지막 12 는 엔진 기본(먹→인주).
function pen(C){
  const S = C.XS.length;
  return (g, c, b, dflt) => {
    if (c === S-1) return dflt;
    const x1 = C.XS[c+1], a = s => MAT.A0*MAT.BF[b]*gain(C, s), gr = g.createLinearGradient(0, 0, x1, 0);
    for (let s=0;s<=c;s++){ gr.addColorStop(C.XS[s]/x1, ink(a(s))); gr.addColorStop((s<c ? C.XS[s+1]-.01 : x1-C.PRESS)/x1, ink(a(s))); }
    gr.addColorStop((x1-6)/x1, ink(a(c)*3)); gr.addColorStop(1, ink(a(c)*.5));
    return [gr, MAT.LW];
  };
}
// 결 있는 선들을 캔버스 c 에 그린다. lines=null 이면 전부. ox 는 결의 x 오프셋(멈춘 띠의 위상과 맞추기 위해).
function material(c, lines, yOf, ww, ox, gn, sx){
  const dpr = devicePixelRatio || 1;
  c.width = Math.round(ww*sx*dpr); c.height = Math.round(H*dpr);
  const g = c.getContext('2d'); g.setTransform(sx*dpr, 0, 0, dpr, 0, 0); g.lineCap = 'butt'; g.lineWidth = MAT.LW;
  const P = MAT.BF.map(() => new Path2D()), step = MAT.LAM/16, M = lines ? lines.length : N0;
  for (let r=0;r<M;r++){
    const i = lines ? lines[r] : r, y = yOf(i), p = P[bucket(i)], f = x => y + wander(i, x + ox);
    p.moveTo(0, f(0));
    for (let x = hash(i+5)*step; x < ww; x += step) p.lineTo(x, f(x));   // 꺾이는 x 를 선마다 어긋나게 — 같은 x 에서 9천 개가 꺾이면 세로 이음이 보인다
    p.lineTo(ww, f(ww));
  }
  MAT.BF.forEach((bf, b) => { g.strokeStyle = ink(MAT.A0*bf*gn); g.stroke(P[b]); });
  return c;
}
// 엔진은 열쇠가 돌 때마다 새로 만든다 — 체 안의 결은 멈춘 띠의 위상(ox)과 맞아야 하고, 그건 그 순간에야 안다.
function engine(m){
  return Engine(CFG[m], cv, [...document.querySelectorAll(`.set.${m}-only .lab`)], m === 'co' ? [...document.querySelectorAll('.ttl')] : [],
                { nb: MAT.BF.length, of: bucket, pen: pen(CFG[m]), wander: (i, x) => wander(i, x + ox) });
}
const sx0 = () => cv.getBoundingClientRect().width / W;
// 벽 s 오른쪽의 자유 구간(s=1..NW-1): 살아남은 선을 새 y 에서 같은 재료로. FREE[0] 은 멈춘 띠 그 자체(오프셋은 blit 때).
function buildFree(){
  const C = CFG[mode], F = [drift];
  for (let s=1;s<E.NW;s++) F.push(material(document.createElement('canvas'), E.alive[s-1], i => E.Y[i*E.S+s], W, ox, gain(C, s), E.sx));
  return F;
}

/* ---- 그리기: 선 벽까지는 체, 그 오른쪽은 자유 재료. 막 선 벽의 왼쪽 구간은 자유→체 크로스페이드. ---- */
function blit(src, x0, x1, so){ const w = x1-x0; if (w > 0) ctx.drawImage(src, x0+(so||0), 0, w, cv.height, x0, 0, w, cv.height); }
function draw(){
  const C = CFG[mode], dpr = devicePixelRatio || 1, px = x => Math.round(x*E.sx*dpr)+2, k = landed;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, cv.width, cv.height);
  const xk = k === E.NW ? cv.width : k ? px(C.XS[k]) : 0;
  if (k){
    const xa = px(C.XS[k-1]);
    if (fade < 1){ blit(E.off, 0, xa); ctx.globalAlpha = fade; blit(E.off, xa, xk); ctx.globalAlpha = 1-fade; blit(FREE[k-1], xa, xk, k > 1 ? 0 : srcOff); ctx.globalAlpha = 1; }
    else blit(E.off, 0, xk);
  }
  if (k < E.NW) blit(FREE[k], xk, cv.width, k ? 0 : srcOff);
  ctx.setTransform(E.sx*dpr, 0, 0, dpr, 0, 0);
  if (k && fade < 1) E.wall(ctx, k, 0);
  if (drop) E.wall(ctx, drop.k, -(H+8)*(1-drop.e));                    // 위에서 떨어지는 중
}
// 파이프라인 k 단계 끝 → k 번째 벽이 떨어진다(DROP) → 그 왼쪽 구간이 벽 둘레로 재편된다(FADE). 단계는 순서대로 줄 선다.
function stageDone(k){ if (phase !== 'go' || !has2d) return; jobs.push(k); if (!raf) next(); }
function next(){ const k = jobs.shift(); if (k == null){ raf = 0; return; } drop = { k, t0: performance.now(), e: 0 }; raf = requestAnimationFrame(tick); }
function tick(now){
  const C = CFG[mode];
  if (drop){
    const p = Math.min(1, (now - drop.t0) / (MAT.DROP*spd)); drop.e = 1 - Math.pow(1-p, 2.2); draw();
    if (p < 1){ raf = requestAnimationFrame(tick); return; }
    landed = drop.k; drop = null; fade = 0; fadeT0 = now;
  }
  const p = Math.min(1, (now - fadeT0) / (MAT.FADE*spd)); fade = 1 - Math.pow(1-p, 2);
  draw(); E.labels(C.XS[landed] + 150*fade);
  if (p < 1){ raf = requestAnimationFrame(tick); return; }
  if (landed === E.NW){ raf = 0; timers.push(setTimeout(settle, 480*spd)); return; }
  next();
}
"""

POST_JS = r"""
/* ---- 열쇠가 돈다: gen_entry 의 go/reset 을 덮어쓴다(목록·Enter·최근 칩이 전부 여기로 온다) ---- */
function go(it, fromEl){
  if (phase !== 'idle' || !it) return;
  picked = it; mode = it.co ? 'co' : 'kw';
  if (it.co) remember(it.co);
  const a = (fromEl || inp).getBoundingClientRect();
  $('#hq').innerHTML = (it.co
    ? `<b>${it.co.nm}</b>${it.co.rgn} · ${it.co.rep ? '등록업종 ' + it.co.nind : '등록업종 없음'} · ${it.co.ncon ? '수주 ' + it.co.ncon + '건' : '수주 이력 없음'}`
    : `<b>"${it.kw}"</b>회사 없이 · 이 말과 가까운 공고`) + `<span class="back" id="back" tabindex="0" role="button">다시 입력</span>`;
  const back = $('#back'); back.onclick = reset; back.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); reset(); } };
  ls.hidden = true; inp.setAttribute('aria-expanded', 'false'); inp.blur();
  phase = 'go'; spd = fromEl ? .5 : 1; landed = 0; drop = null; fade = 1; jobs = [];   // 재방문 칩은 캐시 경로 — 짧게
  if (has2d){
    // 물이 멎는다: 흐르던 띠의 현재 위상을 읽어 #cv 가 똑같은 그림으로 이어받는다 — 선은 다시 시작하지 않는다
    const tx = new DOMMatrix(getComputedStyle(drift).transform).e, t0 = performance.now();   // CSS px, ≤ 0
    srcOff = Math.round(-tx * (devicePixelRatio || 1)); ox = -tx / sx0();
    E = engine(mode); E.setup(); FREE = buildFree(); draw(); E.labels(150);
    window.__build = performance.now() - t0;                          // 열쇠 순간의 멈칫(기하+체 래스터) — 보고용
  }
  document.body.classList.toggle('kw', mode === 'kw'); document.body.classList.add('go');
  flip($('#hq b'), a);                                   // 회사명이 입력 자리에서 머리 자리로 난다 (gen_entry.flip)
  live.textContent = it.co ? `${it.co.nm} 확인. 공고를 거르는 중` : `"${it.kw}" 로 공고를 찾는 중`;
  back.focus({ preventScroll: true });                   // 초점은 캔버스에 가지 않는다 — 캔버스는 aria-hidden
  if (reduce || !has2d){ settle(); return; }             // 움직임 줄이기 / 캔버스 없음: 바로 표
  // 벽은 고정 타임라인이 아니라 단계 완료가 세운다 — 시안은 타이머로 흉내낸다.
  if (!manual) (fromEl ? MAT.FAST : MAT.FULL).slice(0, E.NW).forEach((ms, k) => timers.push(setTimeout(() => stageDone(k + 1), ms)));
}
function settle(){                                       // 건너뛰기(스테이지 클릭·Esc)와 정상 종료가 같은 곳으로 온다
  if (phase !== 'go') return;
  cancelAnimationFrame(raf); raf = 0; timers.forEach(clearTimeout); timers = []; jobs = []; drop = null; fade = 1;
  phase = 'done';
  if (E && E.off){ landed = E.NW; E.paint(W, true); } else document.body.classList.add('done');
  live.textContent = `${CFG[mode].CNT.at(-1)}건 남음`;
}
function reset(){
  cancelAnimationFrame(raf); raf = 0; timers.forEach(clearTimeout); timers = []; jobs = [];
  phase = 'idle'; picked = null; landed = 0; drop = null; fade = 1;
  document.body.classList.remove('go', 'done', 'kw');
  $('#hq').innerHTML = ''; document.querySelectorAll('.lab, .ttl').forEach(l => l.classList.remove('on'));
  if (has2d) ctx.clearRect(0, 0, cv.width, cv.height);
  inp.focus();
}
// 건너뛰기. 판(.plate) 안에서 난 클릭은 제외 — 목록 행·최근 칩을 누른 그 클릭이 .stage 로 올라와 방금 돈 열쇠를 바로 건너뛰게 한다.
document.querySelector('.stage').addEventListener('click', e => { if (phase === 'go' && !e.target.closest('.plate')) settle(); });
addEventListener('keydown', e => { if (e.key === 'Escape' && phase === 'go') settle(); });

/* ---- 도착: 기하만 만들고 결 있는 띠를 그린다(JS 0/프레임 — 흐름은 CSS). 체(오프스크린)는 한 박자 뒤 — 도착 화면엔 벽이 없다. ---- */
if (has2d){
  E = engine('co');                                                  // 도착: 기하(Y)만 쓴다. 체는 열쇠가 돌 때 — 도착 화면엔 벽이 없다
  const strip = () => material(drift, null, i => E.Y[i*E.S], W + MAT.LAM, 0, 1, sx0());
  strip();
  let rz = 0;
  addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => {
    strip();
    if (phase === 'go'){ E.setup(); FREE = buildFree(); draw(); } else if (phase === 'done'){ E.setup(); E.paint(W, true); }
  }, 150); });
}
"""


# ---------------------------------------------------------------- 마크업
def labels_kw(active):
    steps = [("지금 입찰 가능한 공고 · 마감 90일 이내", active), ("이 말과 가까운 공고 · 후보 풀", KW_POOL), ("검토할 공고", KW_N)]
    return "".join(
        f'<div class="lab {"g" if i else ""} {"last" if i == 2 else ""}" data-x="{KW_XS[i]}" style="left:{KW_XS[i] / W * 100:.3f}%">'
        f'<span class="k">{k}</span><div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div></div>'
        for i, (k, v) in enumerate(steps))


def chain(nums):
    b = "<i>→</i>".join(f'<b class="{"acc" if i == len(nums) - 1 else ""}">{n:,}</b>' for i, n in enumerate(nums))
    return f'<div class="chain"><span class="k">걸러낸 경로</span>{b}<span>건</span></div>'


def page(d, fb):
    active, cnt = d["active"], fb["cnt"]
    f = dict(total=active, industry=cnt[1], qualified=cnt[2])
    labs_co = gen_flow.labels(f, cnt[3])[len('<div class="labs">'):-len("</div>")]
    titles = {"drop_ind": fb["titles"][:6] + [""] * 3, "drop_rgn": [""] * 6 + fb["titles"][6:]}
    field = gen_flow.field(titles).replace('<canvas id="cv"', '<canvas id="drift" aria-hidden="true"></canvas><canvas id="cv"', 1)
    assert 'id="drift"' in field
    plate = (f'<div class="plate"><div class="rc" id="rc"></div>{gen_entry.combobox("회사명 · 사업자번호 · 하는 일")}'
             f'<p class="pr">지금 입찰 가능한 공고 <b>{active:,}</b>건 · 회사명이나 하는 일을 넣으면 낼 수 있는 것만 남습니다</p></div>')
    stage = (f'<div class="stage"><div class="labs"><div class="set co-only">{labs_co}</div><div class="set kw-only">{labels_kw(active)}</div></div>'
             f'{field}{plate}'
             f'<div class="co-only">{chain([active, cnt[1], cnt[2], cnt[3]])}</div><div class="kw-only">{chain([active, KW_POOL, KW_N])}</div></div>')
    res = (f'<div class="res co-only">{fb["res"]}</div>'
           f'<div class="res kw-only"><div class="kwnote">키워드 길의 실제 결과 표본은 이 시안에 없다 — 실제 화면에서는 여기에 같은 표 {KW_N}건. '
           f'후보 풀 {KW_POOL} 은 프런트가 보내는 candidate_pool 기본값이고, 자격 거르기는 하지 않는다.</div></div>')
    lg = d["log"]
    cov = coverage()
    foot = (gen_entry.foot(d)[:-len("</div>")]
            + f'<br><br><b>입구가 흐름의 첫 장면이다.</b> 도착하면 {active:,}개 선이 벽 없이 흐르고 있다 — 선마다 불투명도가 다르고(버킷 {len(MAT["BF"])}개, 평균 덮임 {cov * 100:.0f}%) 결이 y 를 따라 다발로 모였다 벌어진다. '
            f'흐름은 결 있는 띠를 한 번 그려 CSS translateX 로만 민다(JS 0/프레임). 회사를 고르면 띠의 현재 위상을 읽어 캔버스가 같은 그림을 이어받고(물이 멎고), '
            f'벽이 위에서 {MAT["DROP"]}ms 에 떨어진 뒤 그 왼쪽 구간이 {MAT["FADE"]}ms 에 벽 둘레로 재편된다 — 전진선으로 쓸지 않는다. 벽 사이 자유 구간과 체 안의 막힌 선이 같은 재료라 이음새가 없다. '
            f'벽은 고정 타임라인이 아니라 <code>stageDone(k)</code> 가 세운다(시안은 타이머로 흉내: 처음 {"/".join(str(m / 1000) for m in FULL_MS)}초, 재방문 칩 {"/".join(str(m / 1000) for m in FAST_MS)}초). '
            f'{cnt[1]}·{cnt[2]}·{cnt[3]} 과 표는 2026-10-15 한종산업개발 표본(모수 {cnt[0]:,}) — {active:,} 은 오늘 수라 하루 어긋난다. 어떤 회사를 골라도 체와 표는 이 표본 하나다(시안). '
            f'키워드 길은 벽 둘({KW_POOL} → {KW_N}), 표본 없음. 미해결 {lg["miss"]}/{lg["tot"]} 는 위 문단.</div>')
    data = dict(groups=d["groups"], counts=d["counts"], active=active, ret=d["ret"], typing=gen_entry.COLLISIONS[0])
    cfg_co = dict(gen_flow.cfg(), CNT=[active, cnt[1], cnt[2], cnt[3]])
    cfg_kw = dict(gen_flow.cfg(), XS=KW_XS, HH=KW_HH, CNT=[active, KW_POOL, KW_N])
    mat = dict(MAT, LAM=LAM, FULL=FULL_MS, FAST=FAST_MS)
    body = (f'<div class="wrap">{nav()}<div class="q" id="hq"></div>{stage}{res}{foot}</div>{gen_entry.ctl()}'
            f'<script type="application/json" id="cfg">{json.dumps(cfg_co)}</script>'
            f'<script type="application/json" id="cfgkw">{json.dumps(cfg_kw)}</script>'
            f'<script type="application/json" id="mat">{json.dumps(mat)}</script>'
            f'<script type="application/json" id="data">{json.dumps(data, ensure_ascii=False)}</script>'
            f'<script>{gen_flow.ENGINE_JS}{PRE_JS}{gen_entry.JS}{POST_JS}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 — 입구가 첫 장면</title>{FONT}<style>{CSS}</style></head><body>{body}</body></html>')


def coverage():
    """장치 픽셀 한 줄의 평균 덮임(상태 0) — 간격당 선 수 × 굵기 × 평균 불투명도."""
    bf = MAT["BF"]; mean_bf = sum(bf[:-1]) / (len(bf) - 1) * .97 + bf[-1] * .03
    return (1 / (2 * gen_flow.HH[0] / 9117)) * MAT["LW"] * MAT["A0"] * mean_bf


def demo():
    fb = flow_bits()
    assert fb["cnt"][:1] == [9285] and fb["res"].count('class="tr"') == 12 and "안 맞아요" not in fb["res"], fb["cnt"]
    # 키워드 벽 둘: 간격이 '셀 수 없음 → 셀 수 있음' 을 넘고, 마지막 벽은 회사 모드와 같은 자리(부채 공유)
    gap = [2 * KW_HH[i] / (c - 1) for i, c in enumerate([9117, KW_POOL, KW_N])]
    assert gap[0] < 0.1 < gap[1] < gap[2] and KW_XS[-1] == gen_flow.XS[-1] and KW_HH[-1] == gen_flow.HH[-1], gap
    # 재료: 종이 위 회색 결(평균 덮임 12~30%), 헤어라인 ≤ .35
    cov = coverage(); assert 0.12 < cov < 0.30 and MAT["LW"] <= .35, cov
    # 결 1 의 다발: 이웃 선의 위상 차 × 진폭이 간격과 같은 자릿수여야 밀도가 눈에 띄게 변한다(0.6~2× — 그 위면 접혀서 지저분)
    pitch = 2 * gen_flow.HH[0] / 9117; m = MAT["W1"] * 2 * 3.141593 * (MAT["T0"] + MAT["A1"] * 2 * 3.141593 * MAT["F1"] + MAT["A2"] * 2 * 3.141593 * MAT["F2"]) / 9117
    assert 0.6 < m / pitch < 2.0, m / pitch
    assert abs(LAM / (W + LAM) * 100 - 24.3243) < 1e-3 and abs((W + LAM) / W * 100 - 132.143) < 1e-3, "CSS 의 drift 수치가 LAM 과 어긋난다"
    assert len(FULL_MS) == len(FAST_MS) == 3 and all(a > b for a, b in zip(FULL_MS, FAST_MS))
    print("ok kw gap(px) =", [round(g, 3) for g in gap], "덮임 %.0f%%" % (cov * 100), "다발 변조 %.2f×간격" % (m / pitch))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo(); sys.exit()
    out = sys.argv[1]
    d = gen_entry.fetch(connect())
    fb = flow_bits()
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, fb))
    print("written", out, f'active={d["active"]:,} funnel(10-15)={fb["cnt"]} kw={[d["active"], KW_POOL, KW_N]}')

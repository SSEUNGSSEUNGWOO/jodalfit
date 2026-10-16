"""입구 = 흐름의 첫 장면 (2026-10-16). 검색 입구가 별도 페이지가 아니라 flow.html 머리 장면의 첫 컷이다.

도착하면 지금 입찰 가능한 공고 전부(9,117개 — 실제 수)가 벽 없이 선으로 흐르고 있고, 그 앞에 입력 한 칸.
회사명(또는 사업자번호·하는 일)을 넣고 Enter 치면 **그 회사가 열쇠**다 — 물이 멎고, 같은 캔버스·같은 선 위에
벽 셋이 파이프라인 단계가 끝날 때마다 하나씩 내려앉아 제자리에서 걸러진다. 입구와 결과 머리가 한 장면이 된다.
입구가 말하는 건 "뭘 찾으세요?"가 아니라 "이게 지금 전부입니다. 당신 거만 남겨 드릴게요."

그리기는 gen_flow.ENGINE_JS(선 기하·오프스크린·blit)를 그대로 쓰고, 콤보박스·동명 회사 목록·최근 회사는
gen_entry.JS 를 그대로 쓴다(go/reset 만 이 파일에서 덮어쓴다 — 같은 스크립트 안의 뒤쪽 function 선언이 이긴다).
상태 0 의 덩어리는 코호트가 없으므로 불투명도 하나로 그린다 — flow.html 의 가로 얼룩(코호트 불투명도 차이)이 도착 화면엔 없다.
흐름감은 매 프레임 다시 그리지 않는다: 결(sin)을 넣은 띠를 한 번 그려 두고 CSS translateX 로만 민다(JS 0/프레임).

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
LAM, AMP, TURNS = 360, 2.2, 2.0          # 덩어리 결: 파장 / 진폭 / 띠 높이당 위상 회전 수 — 밀도 ±(AMP·TURNS·2π/360) ≈ ±8% — 더 세면 헤어라인 금속처럼 보인다(3.5·2.5 = ±15% 는 과했다)
KW_XS, KW_HH = [0, 432, 864], [180, 150, 100]   # 키워드 모드: 벽 둘. 마지막 벽은 회사 모드와 같은 자리라 부채가 같다
KW_POOL, KW_N = 100, 12                   # 후보 풀 = frontend/src/lib/api.ts candidate_pool 기본값 / 검토할 공고 = 회사 표본과 같은 12
FULL_MS, FAST_MS = [700, 1500, 2300], [120, 260, 400]   # 단계 완료 시뮬레이션(처음 방문 / 재방문 칩). 실제 구현은 API 진행 이벤트가 stageDone(k) 를 부른다


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
/* 두 캔버스가 한 자리: #drift 는 결 있는 띠를 CSS 로 미는 살아 있는 덩어리, #cv 는 열쇠가 돌면 그 위에 뜨는 멈춘 덩어리 + 체 */
#drift, #cv { position:absolute; left:0; top:0 }
#drift { width:132.143%; animation:drift 15s linear infinite; transition:opacity .45s ease }   /* (W+LAM)/W */
#cv { opacity:0; transition:opacity .45s ease }
.go #drift { opacity:0; animation-play-state:paused } .go #cv { opacity:1 }
@keyframes drift { to { transform:translateX(-24.3243%) } }                                     /* LAM/(W+LAM) — 한 파장이면 이음새가 없다 */
/* 입력은 전경, 덩어리는 배경 — 흰 판 위에 괘선 입력. 판이 없으면 글자가 덩어리에 묻힌다 */
.plate { position:absolute; left:50%; top:72px; transform:translateX(-50%); width:min(680px,100%); z-index:3; background:rgba(255,255,255,.97); border-radius:12px;
         padding:20px 26px 16px; box-shadow:0 0 0 1px rgba(20,20,20,.07), 0 24px 60px -30px rgba(20,20,20,.4); transition:opacity .3s ease, transform .5s cubic-bezier(.3,.7,.2,1) }
.go .plate { opacity:0; pointer-events:none; transform:translate(-50%,-16px) }
.plate .rc { margin-bottom:10px } .plate .rc:empty { margin:0 }
.plate .pr { margin:12px 0 0 } .plate .ls { max-height:min(52vh,460px); overflow:hidden auto } .plate .ls li { margin:0; padding-left:8px; padding-right:8px }
/* 목록이 스크롤돼도 키워드 행은 늘 보인다 — 회사 길과 같은 무게라는 약속이 스크롤 아래로 숨으면 거짓이 된다 */
.plate .ls li.kw { position:sticky; bottom:0; background:#fff; border-top:1px solid #141414; z-index:1 }
.field .ttl { z-index:2 }
.kwnote { padding:22px 0; font-size:13.5px; color:#55554f; line-height:1.6; border-bottom:1px solid #ececea }
.foot b { color:#141414; font-weight:600 }
@media (max-width:640px) {
  .field, .field canvas, #drift, #cv { height:280px } .ttl { display:none }
  .plate { left:0; right:0; width:auto; transform:none; top:14px; padding:12px 14px 10px; border-radius:10px } .go .plate { transform:translateY(-12px) }
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
const CFG = { co: J('cfg'), kw: J('cfgkw') }, MASS = J('mass');
const W = CFG.co.W, H = CFG.co.H;
const cv = document.getElementById('cv'), drift = document.getElementById('drift');
const has2d = !location.search.includes('nocanvas') && !!(cv.getContext && cv.getContext('2d'));   // ?nocanvas — 캔버스 없는 경로 점검
const manual = location.search.includes('manual');                                                   // ?manual — 단계 이벤트를 밖에서 stageDone(k) 로 준다
const ENG = {};                      // 모드별 엔진: 벽 셋(회사) / 둘(키워드). 선 기하·오프스크린은 gen_flow 의 Engine 그대로.
let E = null, mode = 'co', phase = 'idle', front = 0, target = 0, raf = 0, timers = [], still = null;

function engine(m){
  if (!ENG[m]) ENG[m] = Engine(CFG[m], cv, [...document.querySelectorAll(`.set.${m}-only .lab`)], m === 'co' ? [...document.querySelectorAll('.ttl')] : []);
  return ENG[m];
}
const sx0 = () => cv.getBoundingClientRect().width / W;

// 덩어리: 9,117개 전부, 불투명도 하나 — 아직 코호트가 없다(README 결함: 코호트 불투명도 차이가 가로 얼룩을 만든다. 여기엔 없다).
// wavy 면 LAM 만큼 더 넓은 띠에 sin 결을 넣는다 — CSS 가 한 파장 밀면 이음새 없이 돈다. 아니면 멈춘 덩어리(체 오른쪽에 깔린다).
function mass(E, c, wavy, sx){
  const dpr = devicePixelRatio || 1, ww = wavy ? W + MASS.LAM : W;
  c.width = Math.round(ww*sx*dpr); c.height = Math.round(H*dpr);
  const g = c.getContext('2d'); g.setTransform(sx*dpr, 0, 0, dpr, 0, 0);
  g.lineCap = 'butt'; g.lineWidth = .3; g.strokeStyle = 'rgba(20,20,20,.075)';
  const p = new Path2D(), step = MASS.LAM/16, k = 2*Math.PI/MASS.LAM;
  for (let i=0;i<E.N;i++){
    const y = E.Y[i*E.S];
    if (!wavy){ p.moveTo(0, y); p.lineTo(W, y); continue; }
    const ph = i/E.N*2*Math.PI*MASS.TURNS, f = x => y + MASS.AMP*Math.sin(k*x + ph);
    p.moveTo(0, f(0));                                      // 꺾이는 x 를 선마다 어긋나게(황금비) — 같은 x 에서 9천 개가 꺾이면 세로 이음이 보인다
    for (let x=((i*0.6180339887)%1)*step; x<ww; x+=step) p.lineTo(x, f(x));
    p.lineTo(ww, f(ww));
  }
  g.stroke(p); return c;
}
function ready(){ if (!E.off){ E.setup(); } if (!still) still = mass(E, document.createElement('canvas'), false, E.sx); }

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
  document.body.classList.toggle('kw', mode === 'kw'); document.body.classList.add('go'); phase = 'go';
  flip($('#hq b'), a);                                   // 회사명이 입력 자리에서 머리 자리로 난다 (gen_entry.flip)
  live.textContent = it.co ? `${it.co.nm} 확인. 공고를 거르는 중` : `"${it.kw}" 로 공고를 찾는 중`;
  back.focus({ preventScroll: true });                   // 초점은 캔버스에 가지 않는다 — 캔버스는 aria-hidden
  if (has2d){ E = engine(mode); ready(); }
  if (reduce || !has2d){ settle(); return; }             // 움직임 줄이기 / 캔버스 없음: 바로 표
  front = 0; target = 0; E.paint(0, false, still);       // 물이 멎는다: #drift → #cv 크로스페이드는 CSS
  // 벽은 고정 타임라인이 아니라 단계 완료가 세운다 — 시안은 타이머로 흉내낸다. 재방문 칩(fromEl)은 캐시 경로라 짧게.
  if (!manual) (fromEl ? MASS.FAST : MASS.FULL).slice(0, E.NW).forEach((ms, k) => timers.push(setTimeout(() => stageDone(k + 1), ms)));
}
// 파이프라인 k 단계 끝 → k 번째 벽이 선다. 전진선은 벽을 지나 150px(라벨 카운트업 거리) 더 가서 다음 단계를 기다린다. 마지막이면 끝까지(부채).
function stageDone(k){
  if (phase !== 'go' || !E) return;
  target = k >= E.NW ? W : CFG[mode].XS[k] + 150;
  if (!raf){ last = 0; raf = requestAnimationFrame(tick); }
}
let last = 0;
function tick(now){
  const dt = last ? Math.min(100, now - last) : 16.7; last = now;   // 시간 기준 — 120Hz 폰에서 두 배로 빨라지거나 느린 탭에서 멈추지 않게
  front += (target - front) * (1 - Math.pow(.84, dt / 16.7));      // 지수 완화 — 벽이 내려앉는 데 0.6초쯤
  if (Math.abs(target - front) < .6) front = target;
  E.paint(front, false, still);
  if (front !== target){ raf = requestAnimationFrame(tick); return; }
  raf = 0;
  if (target === W) timers.push(setTimeout(settle, 480));
}
function settle(){                                       // 건너뛰기(스테이지 클릭·Esc)와 정상 종료가 같은 곳으로 온다
  if (phase !== 'go') return;
  cancelAnimationFrame(raf); raf = 0; timers.forEach(clearTimeout); timers = [];
  phase = 'done';
  if (E) E.paint(W, true); else document.body.classList.add('done');
  live.textContent = `${CFG[mode].CNT.at(-1)}건 남음`;
}
function reset(){
  cancelAnimationFrame(raf); raf = 0; timers.forEach(clearTimeout); timers = [];
  phase = 'idle'; picked = null; front = target = 0;
  document.body.classList.remove('go', 'done', 'kw');
  $('#hq').innerHTML = ''; document.querySelectorAll('.lab, .ttl').forEach(l => l.classList.remove('on'));
  if (has2d) cv.getContext('2d').clearRect(0, 0, cv.width, cv.height);
  inp.focus();
}
// 건너뛰기. 판(.plate) 안에서 난 클릭은 제외 — 목록 행·최근 칩을 누른 그 클릭이 .stage 로 올라와 방금 돈 열쇠를 바로 건너뛰게 한다.
document.querySelector('.stage').addEventListener('click', e => { if (phase === 'go' && !e.target.closest('.plate')) settle(); });
addEventListener('keydown', e => { if (e.key === 'Escape' && phase === 'go') settle(); });
/* ---- 도착: 기하만 만들고(≈수십 ms) 결 있는 띠를 그린다. 체(오프스크린)는 한 박자 뒤 — 도착 화면엔 벽이 없다. ---- */
if (has2d){
  E = engine('co'); mass(E, drift, true, sx0());
  setTimeout(ready, 80);
  let rz = 0;
  addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => {
    mass(E, drift, true, sx0()); still = null; E.off && (E.setup(), ready());
    if (phase === 'go') E.paint(front, false, still); else if (phase === 'done') E.paint(W, true);
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
    foot = (gen_entry.foot(d)[:-len("</div>")]
            + f'<br><br><b>입구가 흐름의 첫 장면이다.</b> 도착하면 {active:,}개 선이 벽 없이 흐르고 있고(코호트 없음 — 불투명도 하나, 결은 CSS translateX 로만 민다), '
            f'회사를 고르는 순간 물이 멎고 벽 셋이 단계 완료마다 하나씩 내려앉는다. 같은 캔버스·같은 선 — 다시 시작하지 않는다. '
            f'벽은 고정 타임라인이 아니라 <code>stageDone(k)</code> 가 세운다(시안은 타이머로 흉내: 처음 {"/".join(str(m / 1000) for m in FULL_MS)}초, 재방문 칩 {"/".join(str(m / 1000) for m in FAST_MS)}초). '
            f'{cnt[1]}·{cnt[2]}·{cnt[3]} 과 표는 2026-10-15 한종산업개발 표본(모수 {cnt[0]:,}) — {active:,} 은 오늘 수라 하루 어긋난다. 어떤 회사를 골라도 체와 표는 이 표본 하나다(시안). '
            f'키워드 길은 벽 둘({KW_POOL} → {KW_N}), 표본 없음. 미해결 {lg["miss"]}/{lg["tot"]} 는 위 문단.</div>')
    data = dict(groups=d["groups"], counts=d["counts"], active=active, ret=d["ret"], typing=gen_entry.COLLISIONS[0])
    cfg_co = dict(gen_flow.cfg(), CNT=[active, cnt[1], cnt[2], cnt[3]])
    cfg_kw = dict(gen_flow.cfg(), XS=KW_XS, HH=KW_HH, CNT=[active, KW_POOL, KW_N])
    mass = dict(LAM=LAM, AMP=AMP, TURNS=TURNS, FULL=FULL_MS, FAST=FAST_MS)
    body = (f'<div class="wrap">{nav()}<div class="q" id="hq"></div>{stage}{res}{foot}</div>{gen_entry.ctl()}'
            f'<script type="application/json" id="cfg">{json.dumps(cfg_co)}</script>'
            f'<script type="application/json" id="cfgkw">{json.dumps(cfg_kw)}</script>'
            f'<script type="application/json" id="mass">{json.dumps(mass)}</script>'
            f'<script type="application/json" id="data">{json.dumps(data, ensure_ascii=False)}</script>'
            f'<script>{gen_flow.ENGINE_JS}{PRE_JS}{gen_entry.JS}{POST_JS}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 — 입구가 첫 장면</title>{FONT}<style>{CSS}</style></head><body>{body}</body></html>')


def demo():
    fb = flow_bits()
    assert fb["cnt"][:1] == [9285] and fb["res"].count('class="tr"') == 12 and "안 맞아요" not in fb["res"], fb["cnt"]
    # 키워드 벽 둘: 간격이 '셀 수 없음 → 셀 수 있음' 을 넘고, 마지막 벽은 회사 모드와 같은 자리(부채 공유)
    gap = [2 * KW_HH[i] / (c - 1) for i, c in enumerate([9117, KW_POOL, KW_N])]
    assert gap[0] < 0.1 < gap[1] < gap[2] and KW_XS[-1] == gen_flow.XS[-1] and KW_HH[-1] == gen_flow.HH[-1], gap
    # 결: 밀도 변조가 보일 만큼(±10% 이상)이되 선이 서로 넘나들 만큼(진폭 > 통로 반높이의 5%) 크진 않다
    mod = AMP * TURNS * 2 * 3.141593 / (2 * gen_flow.HH[0])
    assert 0.04 < mod < 0.12 and AMP < gen_flow.HH[0] * 0.05, mod
    assert abs(LAM / (W + LAM) * 100 - 24.3243) < 1e-3 and abs((W + LAM) / W * 100 - 132.143) < 1e-3, "CSS 의 drift 수치가 LAM 과 어긋난다"
    assert len(FULL_MS) == len(FAST_MS) == 3 and all(a > b for a, b in zip(FULL_MS, FAST_MS))
    print("ok kw gap(px) =", [round(g, 3) for g in gap], "결 변조 ±%.0f%%" % (mod * 100))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo(); sys.exit()
    out = sys.argv[1]
    d = gen_entry.fetch(connect())
    fb = flow_bits()
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, fb))
    print("written", out, f'active={d["active"]:,} funnel(10-15)={fb["cnt"]} kw={[d["active"], KW_POOL, KW_N]}')

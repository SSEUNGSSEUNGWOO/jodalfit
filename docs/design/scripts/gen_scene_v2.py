"""장면(gen_scene) + 결과·게이트B(gen_results_v6) 통합 — 2026-10-15 승우님 지시.
종이 애니메이션이 진행되는 동안 그 아래의 깔때기(네 칸)가 같이 채워지고, 마지막 장면이 끝나면
종이가 결과 표의 행 위치로 날아가 앉고, 무대는 접히고, 깔때기는 그대로 결과 페이지 머리(gen_results_v6)가 된다.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_scene_v2.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/scene-v2.html
"""
import html
import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc, dleft  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav  # noqa: E402
from gen_results_v6 import CSS as CSS6, ribbon, body_table  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

# ---------- 무대(종이) CSS — gen_scene.py 에서 가져와 다듬음 ----------
STAGE_CSS = r"""
.fh { padding:26px 0 0 }
.stage { position:relative; height:330px; margin-top:18px; border-top:1px solid #141414; overflow:hidden; transition:height .44s cubic-bezier(.2,.7,.2,1) }
.stage.done { height:0; border-top:0 }
.stage.done .cap { visibility:hidden }
.stage.fly { overflow:visible; z-index:30 }
.cap { position:absolute; left:0; top:22px; z-index:5 }
.cap .k { font-size:11px; letter-spacing:.08em; color:#737370; font-weight:600; display:block }
.cap .n { font-size:64px; letter-spacing:-0.05em; font-weight:700; line-height:1; margin-top:6px } .cap .n small { font-size:15px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:8px }
.cap .n.done { color:#e8431b }
.cap .sub { margin-top:8px; font-size:13.5px; color:#55554f; min-height:20px }
.p { position:absolute; width:116px; height:150px; background:#fff; border:1px solid #e3e1dc; border-radius:3px; box-shadow:0 1px 2px rgba(0,0,0,.05), 0 10px 24px -16px rgba(0,0,0,.3); padding:10px 11px; overflow:hidden;
     transition:transform .55s cubic-bezier(.2,.7,.2,1), opacity .45s ease; will-change:transform, opacity }
.p .ttl { font-size:8.5px; line-height:1.35; color:#55554f; height:34px; overflow:hidden; font-weight:550 }
.p .ln { height:2px; background:#ececea; border-radius:1px; margin-top:5px } .p .ln.s { width:62% } .p .ln.m { width:84% }
.p .stamp, .box .stamp { --sr:-8deg; position:absolute; right:6px; bottom:6px; font-size:11.5px; font-weight:700; letter-spacing:.02em; white-space:nowrap; padding:2px 5px; border-radius:3px; opacity:0; transform:rotate(var(--sr)); transform-origin:center }
.p .stamp.no, .box .stamp.no { color:#6b6b67; border:1px solid #ddd9d2; background:rgba(255,255,255,.9) } .p .stamp.yes { color:#c8381a; border:1.5px solid #e8431b; background:rgba(255,255,255,.9) }
.p.show .stamp, .box.show .stamp { opacity:1 }
.p .stamp.punch, .box .stamp.punch { animation:stampPunch .12s cubic-bezier(.2,.8,.3,1) }
.p.gone, .box.gone { opacity:0 }
@keyframes stampPunch { 0% { transform:scale(1.25) rotate(var(--sr)); opacity:0 } 35% { opacity:1 } 100% { transform:scale(1) rotate(var(--sr)); opacity:1 } }

/* 1막 — 서류 상자. 종이는 DOM 노드가 아니라 반복 그라디언트의 '단면'으로 그린다(한 상자에 60여 겹) */
.box { position:absolute; width:168px; height:128px; transition:transform .5s cubic-bezier(.2,.7,.2,1), opacity .4s ease; will-change:transform, opacity }
.box i { display:block }
.box .pap { position:absolute; bottom:48px; transform-origin:50% 100%; border:1px solid #cfc9bc; border-bottom:0; border-radius:2px 2px 0 0;
            background:repeating-linear-gradient(to bottom, #fff 0 1.6px, #c6c0b3 1.6px 2.9px) }
.box .pap.a { left:4px;   width:54px; height:76px; transform:rotate(-2.2deg) }
.box .pap.b { left:41px;  width:52px; height:90px; transform:rotate(1.4deg) }
.box .pap.c { left:80px;  width:50px; height:80px; transform:rotate(-1deg) }
.box .pap.d { left:116px; width:48px; height:70px; transform:rotate(2.4deg) }
.box .bd { position:absolute; left:0; right:0; bottom:0; height:92px; border-radius:2px 2px 3px 3px;
           background:linear-gradient(#d7cdb9, #e8e1d4 22%, #e1d9c9); border:1px solid #c3b8a2;
           box-shadow:inset 0 9px 11px -8px rgba(20,20,20,.6), 0 1px 2px rgba(0,0,0,.05), 0 18px 32px -20px rgba(0,0,0,.45) }
.box .bd::after { content:''; position:absolute; left:0; right:0; top:24px; border-top:1px solid #cabfa8 }
.box .bd::before { content:''; position:absolute; left:50%; margin-left:-23px; bottom:16px; width:46px; height:10px;
                   border:1px solid #bcb099; border-radius:2px; background:#cfc5b0 }
.box .stamp { left:40px; top:62px; right:auto; bottom:auto; font-size:12px }

/* 2~3막 — 묶음. 두께가 곧 수량 */
.stk { position:absolute; width:164px; transition:transform .5s cubic-bezier(.2,.7,.2,1), height .5s cubic-bezier(.2,.7,.2,1), opacity .4s ease; will-change:transform, height, opacity }
.stk .edges { height:100%; border:1px solid #ddd9d2; border-radius:2px; background:var(--ream);
              box-shadow:0 1px 2px rgba(0,0,0,.05), 0 18px 32px -18px rgba(0,0,0,.42) }
.stk .top { position:absolute; left:-5px; right:-5px; top:-7px; height:8px; background:#fff; border:1px solid #ddd9d2; border-radius:2px 2px 0 0 }
.stk i { display:block }
.slab { position:absolute; width:164px; border:1px solid #ddd9d2; border-radius:2px; background:var(--ream);
        box-shadow:0 8px 16px -12px rgba(0,0,0,.45);
        transition:transform .46s cubic-bezier(.4,.03,.78,.5), opacity .34s ease .1s; will-change:transform, opacity }
.stk, .slab { --ream:repeating-linear-gradient(to bottom, rgba(255,255,255,0) 0 1.05px, #d2ccc1 1.05px 1.7px), linear-gradient(90deg, #efece6, #fff 16%, #fff 84%, #eae6df) }
"""

# ---------- 깔때기 채워짐 상태 + 결과 노출 + 토글 + reduced-motion ----------
EXTRA_CSS = r"""
.fun > div:not(.filled) .n, .fun > div:not(.filled) .n small { color:#8f8f8b }
.fun > div:not(.filled) .why, .fun > div:not(.filled) .arw { opacity:0 }
.fun > div.filled .why, .fun > div.filled .arw { opacity:1; transition:opacity .45s ease }
.fun > div.step:not(.filled) { pointer-events:none }
body:not(.login) .only-login { display:none } body.login .only-guest { display:none }
#resultsWrap { visibility:hidden; opacity:0; transform:translateY(14px); transition:opacity .6s ease, transform .6s cubic-bezier(.2,.7,.2,1) }
body.revealed #resultsWrap, body.placing #resultsWrap { visibility:visible; opacity:1; transform:none }
#resultsWrap .tr { transition:opacity .3s ease, transform .3s cubic-bezier(.2,.7,.2,1) }
#resultsWrap .tr.pending { opacity:0; transform:translateY(7px) }
.rib { opacity:0; transition:opacity .6s ease }
body.revealed .rib { opacity:1 }
.sw { gap:14px; padding:8px 10px }
.sw .g { display:flex; gap:4px; align-items:center } .sw .g em { color:#9a9a96; font-style:normal; margin:0 6px 0 4px }
body.reduced *, body.reduced *::before, body.reduced *::after { transition:none !important; animation:none !important }
@media (prefers-reduced-motion: reduce) {
  .p, .box, .stk, .slab { display:none }
  .stage { height:0 !important; border-top:0 !important }
  #resultsWrap { opacity:1 !important; transform:none !important; visibility:visible !important }
  .rib { opacity:1 !important }
}
"""

CSS_ALL = SHEET_CSS + CSS6 + STAGE_CSS + EXTRA_CSS

JS = r"""
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const stage = document.getElementById('stage'), capK = document.getElementById('capK'), capN = document.getElementById('capN'), capV = document.getElementById('capV'), capS = document.getElementById('capS');
const funCells = document.querySelectorAll('#fun > div');
const T = JSON.parse(document.getElementById('titles').textContent);
const F = JSON.parse(document.getElementById('funnel').textContent);
const W = 1120, PW = 116, PH = 150;
let papers = [], boxes = [], stack = null;
const rnd = (a,b)=>a+Math.random()*(b-a);
const fmt = n => Math.round(n).toLocaleString('ko-KR');
const wait = ms => new Promise(r=>setTimeout(r, ms));

function place(el, x, y, rot){              // 위치를 dataset 에도 남겨 둔다(무대 접힐 때 고정용)
  el.dataset.x = x; el.dataset.y = y; el.dataset.rot = rot;
  el.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg)`;
}
function makePaper(title, x, y, rot, z){
  const el = document.createElement('div'); el.className='p';
  el.innerHTML = `<div class="ttl">${title}</div><div class="ln m"></div><div class="ln s"></div><div class="ln m"></div><div class="ln s"></div><span class="stamp no"></span>`;
  place(el, x, y, rot); el.style.zIndex = z;
  const st = el.querySelector('.stamp');    // 도장은 조금씩 비뚤게 — 찍은 느낌
  st.style.setProperty('--sr', rnd(-11,-5).toFixed(1)+'deg');
  st.style.right = rnd(4,10).toFixed(0)+'px'; st.style.bottom = rnd(4,11).toFixed(0)+'px';
  stage.appendChild(el); return el;
}
function stampSet(el, cls, text){
  el.classList.add('show');
  const st = el.querySelector('.stamp'); st.className = 'stamp ' + cls; st.textContent = text;
  st.classList.remove('punch'); void st.offsetWidth; st.classList.add('punch');
}
function count(to, ms, cls){ const from = +capN.dataset.v || 0; const t0 = performance.now();
  capN.classList.toggle('done', !!cls);
  const tick = now => { const p = Math.min(1,(now-t0)/ms), e = 1-Math.pow(1-p,3);
    capV.textContent = fmt(from + (to-from)*e); if(p<1) requestAnimationFrame(tick); else capN.dataset.v = to; };
  requestAnimationFrame(tick);
}
function fillFunnel(i, to, ms){
  const cell = funCells[i]; if(!cell) return; cell.classList.add('filled');
  const el = cell.querySelector('.cnt'); if(!el) return;
  if(!ms){ el.textContent = fmt(to); return; }
  const t0 = performance.now();
  const tick = now => { const p = Math.min(1,(now-t0)/ms), e = 1-Math.pow(1-p,3);
    el.textContent = fmt(to*e); if(p<1) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}

function makeBox(x, y, z){
  const el = document.createElement('div'); el.className='box';
  el.innerHTML = '<i class="pap a"></i><i class="pap b"></i><i class="pap c"></i><i class="pap d"></i><i class="bd"></i><span class="stamp no"></span>';
  place(el, x, y, rnd(-1.4,1.4)); el.style.zIndex = z;
  stage.appendChild(el); boxes.push(el); return el;
}
function makeStack(x, y, h, z){
  const el = document.createElement('div'); el.className='stk';
  el.innerHTML = '<i class="top"></i><i class="edges"></i>';
  el.style.height = h+'px'; el.style.zIndex = z; el.style.opacity = '0';
  place(el, x, y, 0); stage.appendChild(el); return el;
}
function setStack(x, y, h){ stack.style.opacity='1'; stack.style.height = h+'px'; place(stack, x, y, 0); }
function makeSlab(x, y, h, z){
  const el = document.createElement('div'); el.className='slab';
  el.style.height = h+'px'; el.style.zIndex = z; place(el, x, y, 0);
  stage.appendChild(el); return el;
}

async function scene1(my){            // 상자 — 셀 수 없는 양. 상자마다 종이 단면 60여 겹
  capK.textContent='지금 입찰 가능한 공고'; capS.textContent='나라장터 전체 · 마감 90일 이내 · 매시간 갱신';
  const spots = [[420,116,1],[600,116,2],[780,116,3],[510,178,6],[690,178,7]];
  for(const [x,y,z] of spots){
    const el = makeBox(x, y-170, z);
    el.style.transition = 'transform .4s cubic-bezier(.45,.02,.3,1.07), opacity .3s ease';
    requestAnimationFrame(()=>place(el, x, y, rnd(-1.4,1.4)));
    await wait(78); if(my !== runId) return;
  }
  count(F.total, 760); fillFunnel(0, F.total, 760);
  await wait(430);
}
async function scene2(my){            // 업종 안 맞는 상자는 도장 찍고 치우고, 남은 상자에서 두꺼운 묶음을 꺼낸다
  capK.textContent='업종이 맞는 공고'; capS.textContent='등록업종 15개 중 하나를 허용하는 공고만';
  const keep = boxes[4];
  boxes.forEach((el,i)=>{ if(el===keep) return;
    setTimeout(()=>{
      stampSet(el, 'no', '업종 안 맞음');
      setTimeout(()=>{
        const left = i % 2 === 0;
        el.style.transition = 'transform .46s cubic-bezier(.4,.03,.78,.5), opacity .36s ease .12s';
        place(el, left ? -340 : W+140, +el.dataset.y + rnd(0,50), left ? rnd(-13,-4) : rnd(4,13));
        el.classList.add('gone');
      }, 150);
    }, i*68);
  });
  await wait(690); if(my !== runId) return;
  boxes.filter(el=>el!==keep).forEach(el=>el.remove()); boxes=[keep];
  keep.style.transition = 'transform .5s cubic-bezier(.2,.7,.2,1), opacity .4s ease';
  place(keep, 800, 178, 0);
  stack = makeStack(814, 218, 28, 4);        // 상자 안에서 시작해 위로 빠져나온다
  await wait(70); if(my !== runId) return;
  setStack(560, 146, 92);
  count(F.industry, 700); fillFunnel(1, F.industry, 700);
  await wait(370); if(my !== runId) return;
  keep.style.opacity = '0';
  await wait(230);
  keep.remove(); boxes = [];
}
async function scene3(my){            // 묶음 위에서 몇 겹이 미끄러져 빠져나가고, 남은 묶음은 얇아진다
  capK.textContent='자격이 되는 공고'; capS.textContent='면허·지역 제한을 통과한 공고만';
  const cx = +stack.dataset.x, cy = +stack.dataset.y, peel = [14,12,8,6];
  let top = cy;
  peel.forEach((h,i)=>{
    const el = makeSlab(cx + rnd(-2,4), top, h, 20+i); top += h;
    const left = i % 2 === 0, ty = +el.dataset.y;
    setTimeout(()=>{ place(el, left ? rnd(-420,-260) : rnd(W-20, W+180), ty + rnd(10,90), left ? rnd(-26,-8) : rnd(8,26)); el.style.opacity='0'; }, 40 + i*58);
  });
  setStack(cx, cy + 40, 48);
  count(F.qualified, 620); fillFunnel(2, F.qualified, 620);
  await wait(640); if(my !== runId) return;
  document.querySelectorAll('.slab').forEach(el=>el.remove());
}
async function scene4(my){          // 얇은 묶음이 정확히 12장으로 펼쳐지고, 표의 행으로 날아가 앉는다
  capK.textContent='검토할 공고'; capS.textContent='회사 설명과 과거 수주 이력에 가장 가까운 순서';
  const n = F.result, span = 760, cx = W/2 - PW/2, sx = +stack.dataset.x, sy = +stack.dataset.y;
  for(let i=0;i<n;i++){
    const t = T.keep[i % T.keep.length] || '';
    const el = makePaper(t.slice(0,34), sx + rnd(-6,16), sy - 12 + rnd(-3,3), rnd(-2.2,2.2), i);
    el.style.transition = 'transform .5s cubic-bezier(.2,.75,.25,1.02), opacity .3s ease';
    papers.push(el);
  }
  stack.style.opacity = '0';
  await wait(40); if(my !== runId) return;
  papers.forEach((el,i)=>{ const f = (i-(n-1)/2);
    place(el, cx + f*(span/n), 118 + Math.abs(f)*5, f*2.4); el.style.zIndex = 50-Math.abs(f);
    setTimeout(()=>stampSet(el, 'yes', '검토'), 300 + i*26); });
  count(F.result, 600, true); fillFunnel(3, F.result, 600);
  await wait(760);
  stack.remove(); stack = null;
  await flyToTable();
  if(my === runId) revealResults();
}
async function flyToTable(){
  // 1) 종이를 화면 좌표에 못 박아 두고 무대를 접는다 — 접힌 뒤의 행 위치로 날아가야 "행을 놓은" 것처럼 보인다
  const sr = stage.getBoundingClientRect();
  papers.forEach(el=>{
    el.style.transition = 'none'; el.style.position = 'fixed';
    el.style.left = (sr.left + +el.dataset.x) + 'px'; el.style.top = (sr.top + +el.dataset.y) + 'px';
    el.style.transform = `rotate(${el.dataset.rot}deg)`;
    document.body.appendChild(el);
  });
  const rows = Array.from(document.querySelectorAll('#resultsWrap .vs.on .tr'));
  rows.forEach(r=>r.classList.add('pending'));
  stage.classList.add('done'); document.body.classList.add('placing');
  await wait(440);                   // 무대 접힘이 끝나 행 위치가 확정될 때까지
  // 2) 행마다 하나씩 — 종이는 그 행의 y 로 내려가 작아지며 사라지고, 같은 순간 행이 떠오른다
  papers.forEach((el,i)=>{
    const row = rows[i];
    setTimeout(()=>{
      el.style.transition = 'transform .44s cubic-bezier(.3,.7,.22,1), opacity .3s ease .14s';
      if(row){
        const tr = row.getBoundingClientRect();
        const dx = tr.left + 46 - (parseFloat(el.style.left) + PW/2);
        const dy = tr.top + tr.height/2 - (parseFloat(el.style.top) + PH/2);
        el.style.transform = `translate(${dx}px, ${dy}px) rotate(0deg) scale(.2)`;
        setTimeout(()=>row.classList.remove('pending'), 170);
      } else { el.style.transform = 'translate(0,-60px) scale(.5)'; }
      el.style.opacity = '0'; el.classList.add('gone');
    }, i*38);
  });
  await wait(papers.length*38 + 420);
  rows.forEach(r=>r.classList.remove('pending'));
  document.querySelectorAll(".p").forEach(el=>el.remove()); papers = [];
}
function revealResults(){ document.body.classList.remove('placing'); document.body.classList.add('revealed'); }

function resetAll(){
  papers = []; boxes = []; stack = null;
  document.querySelectorAll('.p, .box, .stk, .slab').forEach(el=>el.remove());
  document.querySelectorAll('#resultsWrap .tr.pending').forEach(r=>r.classList.remove('pending'));
  document.body.classList.remove('placing');
  stage.classList.remove('done','fly');
  funCells.forEach(c=>{ c.classList.remove('filled'); const cnt=c.querySelector('.cnt'); if(cnt) cnt.textContent='0'; });
  document.querySelectorAll('.fun .step').forEach(s=>s.classList.remove('open'));
  document.querySelectorAll('.crit').forEach(c=>c.classList.remove('open'));
  document.body.classList.remove('revealed');
  capK.textContent=''; capS.textContent=''; capV.textContent='0'; capN.dataset.v=0; capN.classList.remove('done');
}
function instantFinish(){
  stage.classList.add('done');
  fillFunnel(0, F.total, 0); fillFunnel(1, F.industry, 0); fillFunnel(2, F.qualified, 0); fillFunnel(3, F.result, 0);
  revealResults();
}
async function quickRun(){
  stage.classList.add('done');
  const seq = [F.total, F.industry, F.qualified, F.result];
  for(let i=0;i<4;i++){ fillFunnel(i, seq[i], 260); await wait(150); }
  await wait(200);
  revealResults();
}
let runId = 0;
async function run(mode){
  const my = ++runId;
  resetAll();
  document.body.classList.toggle('reduced', mode==='reduced');
  if(mode==='reduced'){ instantFinish(); return; }
  if(mode==='revisit'){ await quickRun(); return; }
  await scene1(my); if(my!==runId) return;
  await scene2(my); if(my!==runId) return;
  await scene3(my); if(my!==runId) return;
  await scene4(my);
}

document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>{ document.querySelectorAll('[data-run]').forEach(x=>x.classList.toggle('on',x===b)); run(b.dataset.run); });
document.querySelectorAll('[data-ss]').forEach(e=>e.onclick=()=>{
  const k = e.dataset.ss;
  document.querySelectorAll('[data-ss]').forEach(x=>x.classList.toggle('on',x===e));
  document.body.classList.toggle('login', k==='login');
  document.querySelectorAll('#resultsWrap .vs').forEach(v=>v.classList.toggle('on', v.dataset.s===k));
});
document.querySelectorAll('.fun .step').forEach(s=>s.addEventListener('click',()=>{
  if(!s.classList.contains('filled')) return;
  const k = s.dataset.k, was = s.classList.contains('open');
  document.querySelectorAll('.fun .step').forEach(x=>x.classList.remove('open'));
  document.querySelectorAll('.crit').forEach(c=>c.classList.remove('open'));
  if(!was){ s.classList.add('open'); document.querySelector('.crit[data-k="'+k+'"]').classList.add('open'); }
}));

if(RM){ document.querySelector('[data-run="reduced"]').classList.add('on'); document.querySelector('[data-run="full"]').classList.remove('on'); run('reduced'); }
else { run('full'); }
"""


def fun_header(co, prof, f, n_res):
    """gen_results_v6.head() 와 같은 네 칸(라벨·숫자·근거·기준 보기)을 만들되, 숫자는 0에서 시작."""
    inds = prof["industries"][0] + prof["industries"][1]
    rep = prof["industries"][0]
    steps = [("지금 입찰 가능한 공고", f["total"], "나라장터 전체, 마감 90일 이내", None),
             ("업종이 맞는 공고", f["industry"], f'등록업종 {len(inds)}개 중 하나 허용<br><u>기준 보기</u>', "ind"),
             ("자격이 되는 공고", f["qualified"], "면허·지역 제한 통과<br><u>기준 보기</u>", "qual"),
             ("검토할 공고", n_res, "회사 설명과 과거 수주 이력에 가장 가까운 순서", None)]
    cells = "".join(
        f'<div class="{"last" if i == 3 else ""}{" step" if k else ""}" {f"data-k={k}" if k else ""}>'
        f'<span class="k">{lab}</span><div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div>'
        f'<div class="why">{w}</div>{"" if i == 3 else "<span class=arw>→</span>"}</div>'
        for i, (lab, v, w, k) in enumerate(steps))
    ind_txt = ", ".join(esc(x.split("(")[0]) for x in inds[:10]) + (f' <span class="dim">외 {len(inds) - 10}</span>' if len(inds) > 10 else "")
    crit_ind = (f'<div class="crit" data-k="ind"><div><span class="k">등록업종 {len(inds)} · 대표 {esc(rep[0].split("(")[0]) if rep else "-"}</span><div class="txt">{ind_txt}</div></div>'
                f'<div><span class="k">공급물품</span><div class="txt"><span class="dim">등록 없음</span> — 물품 공고를 받으려면 추가가 필요합니다</div></div>'
                f'<div class="act"><a class="bt dark" href="#">맞아요</a><a class="bt txt" href="#"><u>업종·물품 수정 요청</u></a><span class="mute">나라장터 업체정보 · 10.14 갱신</span></div></div>')
    crit_qual = (f'<div class="crit" data-k="qual"><div><span class="k">지역</span><div class="txt">본사 <b>{esc(co["rgn_nm"])}</b> · 지역 제한 공고는 경상남도 기준으로 판정</div>'
                 f'<span class="k" style="margin-top:12px">면허</span><div class="txt">공고가 요구하는 면허 그룹마다 등록업종 중 하나가 들어가면 통과</div></div>'
                 f'<div><span class="k">규모</span><div class="txt"><span class="dim">미입력</span> — 소기업·중소기업 제한 공고 판정에 쓰입니다<br><span class="dim">사업자 상태</span> 계속사업자 · <span class="dim">제재</span> 없음</div></div>'
                 f'<div class="act"><a class="bt dark" href="#">맞아요</a><a class="bt txt" href="#"><u>지역·규모 수정 요청</u></a></div></div>')
    co_line = (f'<div class="co"><b>{esc(co["corp_nm"])}</b><span>{esc(co["rgn_nm"])}</span><span class="sp"></span>'
               f'<span class="only-login new">어제 이후 새로 3건</span><span class="only-login">검토함 3</span>'
               f'<span class="only-guest dim">처음 오셨나요? 걸러낸 기준이 맞는지 한 번만 확인해 주세요</span></div>')
    rib_html = ribbon([f["total"], f["industry"], f["qualified"], n_res])
    return co_line, cells, rib_html, crit_ind, crit_qual


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    f = dict(f); f["result"] = len(res)
    co_line, cells, rib_html, crit_ind, crit_qual = fun_header(co, prof, f, len(res))
    count_html = (f'<div class="count"><div class="f"><b>공고 {len(res)}</b><span>사전규격 {len(d["pre_spec_results"])}</span><span>발주계획 {len(d["order_plan_results"])}</span>'
                  f'<span class="mute">|</span><span>이번 주 마감 {sum(1 for r in res if dleft(r["bid_clse_date"])[0] <= 7)}</span><span>적합 순</span></div></div>')
    vs = "".join(f'<div class="vs {"on" if state == "guest" else ""}" data-s="{state}">{body_table(res, prof, state == "login")}</div>' for state in ("guest", "login"))
    body = (f'<div class="wrap">{nav()}<div class="fh">{co_line}'
            f'<div class="stage" id="stage"><div class="cap"><span class="k" id="capK"></span>'
            f'<div class="n" id="capN" data-v="0"><span id="capV">0</span><small>건</small></div><div class="sub" id="capS"></div></div></div>'
            f'<div class="fun" id="fun">{cells}</div>{rib_html}{crit_ind}{crit_qual}</div>'
            f'<div id="resultsWrap">{count_html}{vs}</div>'
            f'<div class="foot">장면은 서버 단계 신호에 맞춰 넘어갑니다(여기선 모의). 깔때기는 그 결과로 채워집니다. 재방문·움직임 줄이기 설정에서는 짧은 버전. 숫자·공고명은 2026-10-15 실제 데이터.</div></div>'
            f'<div class="sw"><div class="g"><em>방문</em><span class="on" data-run="full">처음 방문</span><span data-run="revisit">재방문</span><span data-run="reduced">움직임 줄이기</span></div>'
            f'<div class="g"><em>상태</em><span class="on" data-ss="guest">비로그인</span><span data-ss="login">로그인</span></div></div>'
            f'<script type="application/json" id="titles">{json.dumps(titles, ensure_ascii=False)}</script>'
            f'<script type="application/json" id="funnel">{json.dumps(f)}</script>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 — 일하는 장면 + 결과</title>{FONT}<style>{CSS_ALL}</style></head><body>{body}<script>{JS}</script></body></html>'


if __name__ == "__main__":
    src, fsrc, tsrc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc)); t = json.load(open(tsrc, encoding="utf-8"))
    t = {k: [html.escape(x) for x in v] for k, v in t.items()}
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, f, t))
    print("written", out)

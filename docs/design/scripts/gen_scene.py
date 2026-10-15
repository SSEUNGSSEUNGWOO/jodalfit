"""검색 → 결과 사이의 '일하는 장면' 프로토타입 (2026-10-15 승우님 제안).
비유가 아니라 묘사다: 실제로 공고 9,285건을 받아 → 업종으로 거르고 → 자격으로 거르고 → 12건을 고른다.
  1 쌓임   : 종이가 떨어져 쌓인다. 9,285
  2 훑기   : 업종 안 맞는 것이 왼쪽으로 버려진다. 831 남음
  3 거르기 : 면허·지역 미충족이 버려진다. 385 남음
  4 고르기 : 남은 것이 부채로 펼쳐졌다가 12장만 앞으로 → 그대로 표의 행이 된다.
규칙: 각 장면은 서버 단계 신호(stage)를 기다린다(여기선 모의 지연). 재방문은 짧게. reduced-motion 이면 숫자만.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_scene.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/scene.html
"""
import html
import json
import random
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import esc  # noqa: E402

FONT = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'

CSS = r"""
* { box-sizing:border-box } body { margin:0; background:#fff; color:#141414; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif; font-variant-numeric:tabular-nums }
.wrap { width:1120px; margin:0 auto; padding:0 0 80px }
.nav { display:flex; align-items:center; justify-content:space-between; padding:22px 0; font-size:13px; color:#55554f } .brand { display:flex; align-items:center; gap:8px; color:#141414; font-weight:700; font-size:14.5px } .brand i { width:7px; height:7px; border-radius:50%; background:#e8431b; display:inline-block }
.q { padding:26px 0 0; font-size:14px; color:#55554f } .q b { color:#141414; font-size:17px; font-weight:650; margin-right:10px }

/* 무대 */
.stage { position:relative; height:330px; margin-top:18px; border-top:1px solid #141414; overflow:hidden; transition:height .6s cubic-bezier(.2,.7,.2,1) }
.stage.done { height:132px }
.cap { position:absolute; left:0; top:22px; z-index:5 }
.cap .k { font-size:11px; letter-spacing:.08em; color:#737370; font-weight:600; display:block }
.cap .n { font-size:64px; letter-spacing:-0.05em; font-weight:700; line-height:1; margin-top:6px } .cap .n small { font-size:15px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:8px }
.cap .n.done { color:#e8431b }
.cap .sub { margin-top:8px; font-size:13.5px; color:#55554f; min-height:20px }

/* 종이 */
.p { position:absolute; width:116px; height:150px; background:#fff; border:1px solid #e3e1dc; border-radius:3px; box-shadow:0 1px 2px rgba(0,0,0,.05), 0 10px 24px -16px rgba(0,0,0,.3); padding:10px 11px; overflow:hidden;
     transition:transform .55s cubic-bezier(.2,.7,.2,1), opacity .45s ease; will-change:transform, opacity }
.p .ttl { font-size:8.5px; line-height:1.35; color:#55554f; height:34px; overflow:hidden; font-weight:550 }
.p .ln { height:2px; background:#ececea; border-radius:1px; margin-top:5px } .p .ln.s { width:62% } .p .ln.m { width:84% }
.p .stamp { position:absolute; right:8px; bottom:8px; font-size:8px; font-weight:700; letter-spacing:.04em; padding:2px 5px; border-radius:3px; opacity:0; transition:opacity .25s ease }
.p .stamp.no { color:#8f8f8b; border:1px solid #e3e1dc } .p .stamp.yes { color:#c8381a; border:1.5px solid #e8431b }
.p.show .stamp { opacity:1 }
.p.gone { opacity:0 }

/* 결과 표 */
.res { margin-top:10px; opacity:0; transform:translateY(14px); transition:opacity .6s ease, transform .6s cubic-bezier(.2,.7,.2,1) } .res.in { opacity:1; transform:none }
.th, .tr { display:grid; grid-template-columns:34px minmax(0,1fr) 190px 170px 86px 84px 58px; gap:0 16px; align-items:baseline }
.th { padding:10px 0 8px; border-bottom:1px solid #141414; font-size:11px; letter-spacing:.06em; color:#737370; font-weight:600 }
.tr { padding:14px 0; border-bottom:1px solid #ececea; font-size:14px } .tr .no { font-size:12px; color:#8f8f8b } .tr .t { font-weight:550; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; letter-spacing:-0.01em }
.tr .org, .tr .why { font-size:13px; color:#55554f; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .tr .why { color:#6b6b67 }
.tr .r { text-align:right } .tr .d { font-weight:600 } .tr .d.hot { color:#e8431b } .tr .d small { color:#737370; font-weight:450; margin-left:6px }
.tr .fit { font-weight:600 }
.foot { margin-top:26px; font-size:12px; color:#737370 }
.ctl { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); display:flex; gap:4px; padding:6px 8px; background:#141414; color:#c9c9c4; border-radius:999px; font-size:12.5px; z-index:20 } .ctl span { padding:6px 11px; border-radius:999px; cursor:pointer } .ctl span.on { background:#fff; color:#141414; font-weight:600 }
@media (prefers-reduced-motion: reduce) { .p { display:none } .res { opacity:1 !important; transform:none !important } }
"""

JS = r"""
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const stage = document.getElementById('stage'), capN = document.getElementById('capN'), capV = document.getElementById('capV'), capK = document.getElementById('capK'), capS = document.getElementById('capS');
const T = JSON.parse(document.getElementById('titles').textContent);
const F = JSON.parse(document.getElementById('funnel').textContent);
const W = 1120, H = 330, PW = 116, PH = 150;
let papers = [];
const rnd = (a,b)=>a+Math.random()*(b-a);
const fmt = n => Math.round(n).toLocaleString('ko-KR');

function makePaper(title, x, y, rot, z){
  const el = document.createElement('div'); el.className='p';
  el.innerHTML = `<div class="ttl">${title}</div><div class="ln m"></div><div class="ln s"></div><div class="ln m"></div><div class="ln s"></div><span class="stamp no"></span>`;
  el.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg)`; el.style.zIndex = z;
  stage.appendChild(el); return el;
}
function count(to, ms, cls){ const from = +capN.dataset.v || 0; const t0 = performance.now();
  capN.classList.toggle('done', !!cls);
  const tick = now => { const p = Math.min(1,(now-t0)/ms), e = 1-Math.pow(1-p,3);
    capV.textContent = fmt(from + (to-from)*e); if(p<1) requestAnimationFrame(tick); else capN.dataset.v = to; };
  requestAnimationFrame(tick);
}
const wait = ms => new Promise(r=>setTimeout(r, ms));

async function scene1(){            // 쌓임
  capK.textContent='오늘 올라온 공고'; capS.textContent='나라장터 전체 · 마감 90일 이내';
  const n = 26, cx = W/2 - PW/2;
  for(let i=0;i<n;i++){
    const t = [...T.drop_ind, ...T.drop_rgn, ...T.keep][i % 38] || '';
    const el = makePaper(t.slice(0,34), cx + rnd(-14,14), -PH, rnd(-7,7), i);
    papers.push(el);
    requestAnimationFrame(()=>{ el.style.transform = `translate(${cx + rnd(-16,16)}px, ${rnd(120,150)}px) rotate(${rnd(-6,6)}deg)`; });
    await wait(26);
  }
  count(F.total, 900);
  await wait(650);
}
async function scene2(){            // 훑기 — 업종 안 맞는 것 버림
  capK.textContent='업종이 맞는 공고'; capS.textContent='등록업종 15개 중 하나를 허용하는 공고만';
  const keepN = 14;
  papers.forEach((el,i)=>{
    const keep = i >= papers.length - keepN;
    el.querySelector('.stamp').textContent = keep ? '' : '업종 안 맞음';
    el.classList.add('show');
    setTimeout(()=>{
      if(keep){ el.style.transform = `translate(${W/2 - PW/2 + rnd(-10,10)}px, ${rnd(120,145)}px) rotate(${rnd(-4,4)}deg)`; }
      else { el.style.transform = `translate(${rnd(-260,-120)}px, ${rnd(150,260)}px) rotate(${rnd(-26,-8)}deg)`; el.classList.add('gone'); }
    }, i*22);
  });
  count(F.industry, 800);
  await wait(900);
  papers = papers.filter(el=>!el.classList.contains('gone'));
}
async function scene3(){            // 거르기 — 자격
  capK.textContent='자격이 되는 공고'; capS.textContent='면허·지역 제한을 통과한 공고만';
  const keepN = 10;
  papers.forEach((el,i)=>{
    const keep = i >= papers.length - keepN;
    const st = el.querySelector('.stamp'); st.textContent = keep ? '' : (i%2 ? '지역 제한' : '면허 미충족'); st.className = 'stamp no';
    setTimeout(()=>{
      if(!keep){ el.style.transform = `translate(${rnd(-240,-110)}px, ${rnd(140,250)}px) rotate(${rnd(-24,-6)}deg)`; el.classList.add('gone'); }
    }, i*26);
  });
  count(F.qualified, 700);
  await wait(800);
  papers = papers.filter(el=>!el.classList.contains('gone'));
}
async function scene4(){            // 고르기 — 부채로 펼쳤다가 12장
  capK.textContent='검토할 공고'; capS.textContent='회사 설명과 과거 수주 이력에 가장 가까운 순서';
  const n = papers.length, span = 760, cx = W/2 - PW/2;
  papers.forEach((el,i)=>{ const f = (i-(n-1)/2);
    el.style.transform = `translate(${cx + f*(span/n)}px, ${118 + Math.abs(f)*5}px) rotate(${f*2.4}deg)`; el.style.zIndex = 50-Math.abs(f);
    const st = el.querySelector('.stamp'); st.className='stamp yes'; st.textContent='검토'; });
  count(F.result, 650, true);
  await wait(640);
  papers.forEach((el,i)=>setTimeout(()=>{ el.style.transform = `translate(${cx}px, ${-PH-20}px) rotate(0deg)`; el.classList.add('gone'); }, i*18));
  await wait(360);
  stage.classList.add('done');
  document.getElementById('res').classList.add('in');
  capS.textContent = '아래 12건. 첫 한 건은 근거까지 공개합니다.';
}
async function run(fast){
  papers.forEach(el=>el.remove()); papers=[]; stage.classList.remove('done'); capN.dataset.v=0; capV.textContent='0'; document.getElementById('res').classList.remove('in');
  if(RM || fast){ stage.classList.add('done'); capK.textContent='검토할 공고'; capS.textContent='오늘 9,285건 중 업종 831 → 자격 385 → 12건'; count(F.result, 500, true); await wait(260); document.getElementById('res').classList.add('in'); return; }
  await scene1(); await scene2(); await scene3(); await scene4();
}
document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>{ document.querySelectorAll('[data-run]').forEach(x=>x.classList.toggle('on',x===b)); run(b.dataset.run==='fast'); });
run(false);
"""


def rows_html(res):
    from gen_results import won, dleft
    from gen_results_v2 import strongest
    out = []
    for i, r in enumerate(res, 1):
        org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
        s = strongest(r); n, dd = dleft(r["bid_clse_date"])
        out.append(f'<div class="tr"><span class="no">{i:02d}</span><span class="t">{esc(r["bid_ntce_nm"])}</span><span class="org">{esc(org)}</span>'
                   f'<span class="why">{esc(s["label"]) if s else ""}</span><span class="r d {"hot" if n <= 7 else ""}">D-{n}<small>{dd.month}.{dd.day:02d}</small></span>'
                   f'<span class="r">{won(r.get("presmpt_prce"))}</span><span class="r fit">{round(float(r["score"]) * 100)}</span></div>')
    return "".join(out)


def page(d, f, titles):
    res, co = d["results"], d["company"]
    f = dict(f); f["result"] = len(res)
    body = (f'<div class="wrap"><div class="nav"><div class="brand"><i></i>조달핏</div><div>추천 · 검토함 · 개선 기록</div></div>'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 15 · 공급물품 없음</div>'
            f'<div class="stage" id="stage"><div class="cap"><span class="k" id="capK">오늘 올라온 공고</span>'
            f'<div class="n" id="capN" data-v="0"><span id="capV">0</span><small>건</small></div><div class="sub" id="capS"></div></div></div>'
            f'<div class="res" id="res"><div class="th"><span>#</span><span>공고</span><span>발주기관</span><span>근거</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>{rows_html(res)}</div>'
            f'<div class="foot">장면은 서버 단계 신호에 맞춰 넘어갑니다(여기선 모의). 종이에 적힌 공고명·숫자는 2026-10-15 실제 데이터. 재방문·움직임 줄이기 설정에서는 짧은 버전.</div></div>'
            f'<div class="ctl"><span class="on" data-run="full">처음 방문</span><span data-run="fast">재방문·움직임 줄이기</span></div>'
            f'<script type="application/json" id="titles">{json.dumps(titles, ensure_ascii=False)}</script>'
            f'<script type="application/json" id="funnel">{json.dumps(f)}</script>')
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 — 고르는 장면</title>{FONT}<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>'


if __name__ == "__main__":
    src, fsrc, tsrc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc)); t = json.load(open(tsrc, encoding="utf-8"))
    t = {k: [html.escape(x) for x in v] for k, v in t.items()}
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, f, t))
    print("written", out)

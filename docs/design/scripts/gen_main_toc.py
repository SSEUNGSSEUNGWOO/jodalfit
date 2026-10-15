"""메인: 히어로 → 플랫폼 섹션(왼쪽 고정 목차 + 오른쪽 5블록, 스크롤 스파이) → CTA → 푸터."""
import sys, io, contextlib, importlib.util
out = sys.argv[1]
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.argv = [sys.argv[0], f"./_tmp_{name}.html"]
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    return m
MOTION_CSS = '\n.lg .hero { padding-top:36px } .lg h1 { font-size:52px; margin-top:14px } .lg .lede { margin-top:12px } .lg .search { margin-top:20px } .lg .peek { margin-top:30px; height:440px }\n' + '\n/* ---- motion v2 ---- */\n.lg .hero { perspective:1400px }\n.lg .peek { height:420px; transform-origin:50% 0; will-change:transform }\n.lg .peek .win { transform:rotateX(8deg) scale(.96); transform-origin:50% 0; transition:transform 1.1s cubic-bezier(.2,.7,.2,1), box-shadow 1.1s ease }\n.lg .peek .win.in { transform:none; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 40px 80px -36px rgba(0,0,0,.35) }\n.lg h1 .ln { display:inline-block; overflow:hidden; vertical-align:bottom } .lg h1 .ln span { display:inline-block; transform:translateY(110%); animation:up .9s cubic-bezier(.2,.7,.2,1) forwards } .lg h1 .ln:nth-child(2) span { animation-delay:.12s }\n@keyframes up { to { transform:none } }\n.lg .lede, .lg .search, .lg .sub, .lg .eyebrow { animation:fade .9s ease both } .lg .eyebrow { animation-delay:.05s } .lg .lede { animation-delay:.3s } .lg .search { animation-delay:.42s } .lg .sub { animation-delay:.55s }\n@keyframes fade { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:none } }\n.lg .blk .shot.rv { transform:translateY(60px) scale(.94); transition-duration:1s } .lg .blk.in .shot.rv { transform:none }\n.lg .blk h3.rv { transform:translateY(30px) } .lg .blk h3 { transition-duration:.9s }\n.lg .blk.in .win { box-shadow:0 1px 2px rgba(0,0,0,.04), 0 40px 80px -36px rgba(0,0,0,.35) }\n.lg .toc { overflow:visible } .lg .toc .bar { position:absolute; left:0; top:0; width:2px; height:100%; background:#ececea } .lg .toc .bar i { position:absolute; left:0; top:0; width:100%; height:0; background:#141414; transition:height .15s linear }\n.lg .plat .head h2 .w { display:inline-block; opacity:0; transform:translateY(14px); transition:opacity .6s ease var(--d,0s), transform .6s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .lg .plat .head.in h2 .w { opacity:1; transform:none }\n.lg .cta { transition:opacity .9s ease, transform .9s cubic-bezier(.2,.7,.2,1), border-radius .9s ease; transform:translateY(40px) scale(.97) } .lg .cta.in { transform:none }\n.lg .cta h2 .w { display:inline-block; opacity:0; transform:translateY(16px); transition:opacity .6s ease var(--d,0s), transform .6s ease var(--d,0s) } .lg .cta.in h2 .w { opacity:1; transform:none }\n/* demo cursor */\n.lg .cur { position:absolute; left:0; top:0; width:22px; height:22px; z-index:5; pointer-events:none; opacity:0; transition:transform .9s cubic-bezier(.3,.7,.2,1), opacity .3s ease; filter:drop-shadow(0 2px 4px rgba(0,0,0,.25)) }\n.lg .cur.show { opacity:1 } .lg .cur.click { animation:clk .25s ease } @keyframes clk { 50% { transform:var(--t) scale(.8) } }\n.lg .search.focus { box-shadow:0 0 0 3px rgba(232,67,27,.18), 0 12px 32px -16px rgba(0,0,0,.18) }\n.lg .search .bt.press { transform:scale(.96); background:#333 }\n.lg .pop { position:absolute; z-index:4; width:360px; background:#fff; border:1px solid #e6e4df; border-radius:12px; box-shadow:0 24px 48px -24px rgba(0,0,0,.3); padding:14px 16px; font-size:12.5px; line-height:1.55; color:#5c5c58; opacity:0; transform:translateY(8px) scale(.98); transition:opacity .35s ease, transform .35s cubic-bezier(.2,.7,.2,1) }\n.lg .pop.show { opacity:1; transform:none } .lg .pop b { display:block; color:#141414; font-size:13px; margin-bottom:4px }\n.lg .pop .tags { display:flex; gap:6px; margin-top:8px } .lg .pop .tags span { padding:3px 8px; border-radius:999px; background:#fdeae4; color:#c8381a; font-size:11px; font-weight:600 }\n' + '\n/* ---- motion ---- */\n.lg .rv { opacity:0; transform:translateY(22px); transition:opacity .7s cubic-bezier(.2,.7,.2,1), transform .7s cubic-bezier(.2,.7,.2,1); transition-delay:var(--d,0s) }\n.lg .in .rv, .lg .rv.in { opacity:1; transform:none }\n.lg .win .tr { opacity:0; transform:translateX(-10px); transition:opacity .45s ease, transform .45s cubic-bezier(.2,.7,.2,1) }\n.lg .win.in .tr { opacity:1; transform:none }\n.lg .win .gate .cover { opacity:0; transition:opacity .6s ease 1.9s } .lg .win.in .gate .cover { opacity:1 }\n.lg .win .gate .rows { filter:blur(0); opacity:1; transition:filter .8s ease 1.6s, opacity .8s ease 1.6s } .lg .win.in .gate .rows { filter:blur(3px); opacity:.55 }\n.lg .win .gcard { transform:translateY(16px) scale(.97); transition:transform .6s cubic-bezier(.2,.7,.2,1) 1.9s } .lg .win.in .gcard { transform:none }\n.lg .type::after { content:"|"; margin-left:1px; color:#141414; animation:blink 1s steps(1) infinite } .lg .type.done::after { content:"" }\n@keyframes blink { 50% { opacity:0 } }\n.lg .cn { stroke-dasharray:1; stroke-dashoffset:1; transition:stroke-dashoffset .9s cubic-bezier(.4,0,.2,1) var(--d,0s) } .lg .in .cn { stroke-dashoffset:0 }\n.lg .nd { opacity:0; transform:translateY(8px); transition:opacity .5s ease var(--d,0s), transform .5s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .lg .in .nd { opacity:1; transform:none }\n.lg .ev { opacity:0; transform:translateX(-8px); transition:opacity .45s ease var(--d,0s), transform .45s ease var(--d,0s) } .lg .in .ev { opacity:1; transform:none }\n.lg .life div { opacity:.35; transition:opacity .4s ease var(--d,0s) } .lg .in .life div { opacity:1 }\n.lg .kv div { opacity:0; transform:scale(.97); transition:opacity .4s ease var(--d,0s), transform .4s ease var(--d,0s) } .lg .in .kv div { opacity:1; transform:none }\n.lg .cta { opacity:0; transform:translateY(26px); transition:opacity .8s ease, transform .8s cubic-bezier(.2,.7,.2,1) } .lg .cta.in { opacity:1; transform:none }\n.lg .toc a { transition:color .25s ease, transform .25s ease } .lg .toc a.on { transform:translateX(4px) }\n.lg .blk h3 b { background:linear-gradient(#141414,#141414) no-repeat 0 100%/0 2px; transition:background-size .8s cubic-bezier(.2,.7,.2,1) .2s } .lg .blk.in h3 b { background-size:100% 2px }\n'
gl = load("./gen_long.py", "gl")
cv = load("./gen_canvas_min.py", "cv")
N, TOP, CO = gl.N, gl.TOP, gl.CO

CSS = gl.CSS.replace('.lg .page { position:relative; background:#fff; color:#141414; overflow:hidden }', '.lg .page { position:relative; background:#fff; color:#141414; overflow:clip }') + MOTION_CSS + '''
.lg .plat { position:relative; border-top:1px solid #ececea; margin-top:72px }
.lg .plat .head { padding:64px 48px 56px; border-bottom:1px solid #ececea }
.lg .tag { display:inline-block; padding:4px 10px; border-radius:6px; background:#fdeae4; color:#c8381a; font-size:12.5px; font-weight:600 }
.lg .plat h2 { margin:22px 0 0; font-size:40px; line-height:1.18; letter-spacing:-0.04em; font-weight:650; max-width:820px } .lg .plat h2 .dim { color:#8a8a86; font-weight:450 }
.lg .grid { display:grid; grid-template-columns:300px 1fr }
.lg .toc { position:sticky; top:0; align-self:start; height:100vh; display:flex; flex-direction:column; justify-content:center; padding:0 0 0 48px; border-right:1px solid #ececea }
.lg .toc a { display:block; position:relative; padding:9px 0; font-size:17px; color:#c9c9c4; text-decoration:none; letter-spacing:-0.01em; transition:color .2s }
.lg .toc a.on { color:#141414; font-weight:500 } .lg .toc a.on::before { content:""; position:absolute; left:-48px; top:10px; bottom:10px; width:2px; background:#e8431b }
.lg .blk { padding:88px 48px 56px; border-bottom:1px solid #ececea }
.lg .blk h3 { margin:0; font-size:22px; line-height:1.45; letter-spacing:-0.02em; font-weight:600; max-width:620px } .lg .blk h3 .dim { color:#8a8a86; font-weight:450 }
.lg .blk .shot { margin-top:34px; background:#f6f6f4; border-radius:16px; padding:28px }
.lg .blk .shot.flat { background:none; padding:0 }
'''
blocks = [
 ("read", "읽기", f'<b>전부 읽고, 볼 것만.</b> <span class="dim">회사명 하나로 등록업종·공급물품·수주 이력을 읽어 오늘 {N:,}건을 걸러냅니다. 처음 5건은 누구나, 나머지는 이메일 하나로.</span>', gl.window().replace(f"<b>{CO}</b>", f"<b class=\"type\" data-text=\"{CO}\"></b>", 1)),
 ("how", "어떻게", f'<b>회사 하나를 벡터로.</b> <span class="dim">같은 공간에 놓인 오늘 공고 중 가까운 것을 고르고, 자격·기관·지역·마감으로 다시 정렬합니다.</span>', f'<div style="border-radius:12px;overflow:hidden;border:1px solid #e6e4df">{cv.canvas}</div>'),
 ("why", "근거", '<b>점수가 아니라 왜 남았는지.</b> <span class="dim">등록업종·공급물품·수주 이력 중 어디가 겹쳤는지, 기관이 이 분야를 반복 발주하는지, 자격 제한에 걸리는지. 행마다 붙습니다.</span>', f'<div style="max-width:640px">{gl.why}</div>'),
 ("golden", "골든타임", '<b>사전규격부터 개찰까지.</b> <span class="dim">본공고가 뜨면 이미 늦은 경우가 많습니다. 의견을 낼 수 있는 단계에서 먼저 알려드립니다.</span>', gl.life),
 ("mail", "알림", '<b>새로 남으면 아침 7시에.</b> <span class="dim">비밀번호 없이 이메일 하나로. 회사를 기억하고, 검토 인장을 보관하고, 새로 남은 공고만 보냅니다. 없는 날은 보내지 않습니다.</span>', f'<div style="max-width:640px">{gl.mail}</div>'),
]
toc = "".join(f'<a href="#{k}" data-k="{k}" class="{"on" if i==0 else ""}">{t}</a>' for i,(k,t,_,_) in enumerate(blocks))
body = "".join(f'<div class="blk" id="{k}"><h3 class="rv">{h}</h3><div class="shot rv {"flat" if k in ("why","mail","golden") else ""}" style="--d:.15s">{s}</div></div>' for k,t,h,s in blocks)

page = f'''<div class="page"><div class="wash"></div>
<div class="nav"><span class="brand"><i></i>조달핏</span><div class="pillnav"><span class="on">추천</span><span>공고</span><span>기업</span><span>인사이트</span></div><span>문의</span></div>
<div class="hero"><span class="eyebrow"><b>오늘</b> <span id="cnt">{N:,}</span>건 진행 중 · 05:00 갱신</span>
<h1><span class="ln"><span>오늘의 나라장터를</span></span><br><span class="ln"><span>우리 회사 기준으로, <span class="dim">볼 것만.</span></span></span></h1>
<p class="lede">회사명 하나면 등록업종·공급물품·수주 이력을 읽어 오늘 공고 전부를 걸러냅니다. 회원가입 없이 바로.</p>
<div class="search" id="hs"><span class="ph" id="hph">회사명 또는 사업자번호 10자리</span><span class="bt" id="hbt">읽기</span></div>
<div class="sub">회사가 없으면 <u>키워드로</u></div>
<svg class="cur" id="cur" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.5L10 20z" fill="#141414" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg><div class="pop" id="pop"><b>추천 근거 · 적합 77</b>공고의 과업(교육 콘텐츠·이러닝 유지관리)이 등록업종·공급물품과 겹칩니다. 조달청은 이 분야 반복 발주 기관입니다.<div class="tags"><span>업종 겹침 +28</span><span>물품 겹침 +22</span><span>반복 기관 +12</span></div></div>
<div class="peek">{gl.window(gate=False, n_clear=5)}</div></div>

<div class="plat"><div class="head"><span class="tag">플랫폼</span>
<h2><span class="w" style="--d:0.00s">매일</span> <span class="w" style="--d:0.06s">새벽,</span> <span class="w" style="--d:0.12s">전부</span> <span class="w" style="--d:0.18s">읽어두는</span> <span class="w" style="--d:0.24s">시스템.</span><br><span class="dim"><span class="w" style="--d:0.40s">공고가</span> <span class="w" style="--d:0.45s">올라오면</span> <span class="w" style="--d:0.50s">읽고,</span> <span class="w" style="--d:0.55s">회사</span> <span class="w" style="--d:0.60s">기준으로</span> <span class="w" style="--d:0.65s">남기고,</span> <span class="w" style="--d:0.70s">아침에</span> <span class="w" style="--d:0.75s">알려줍니다.</span></span></h2></div>
<div class="grid"><div class="toc"><div class="bar"><i id="tbar"></i></div>{toc}</div><div>{body}</div></div></div>

<div class="cta"><h2><span class="w" style="--d:0.20s">처음</span> <span class="w" style="--d:0.28s">5건은</span> <span class="w" style="--d:0.36s">누구나,</span><br><span class="w" style="--d:0.50s">전부는</span> <span class="w" style="--d:0.58s">이메일</span> <span class="w" style="--d:0.66s">하나로.</span></h2><p>가입은 이메일 입력이 전부입니다. 결제 없음, 비밀번호 없음.</p><div class="in"><span>name@company.co.kr</span><span>시작하기</span></div></div>
<div class="footer"><span>조달핏 · 나라장터 공공데이터 기반 · 낙찰을 보장하지 않습니다</span><span>개인정보처리방침 · 기업 정보 비공개 요청 · 문의</span></div></div>''' + r'''<script>
(function(){
const root=document.querySelector('.main')||null;
const links=[...document.querySelectorAll('.lg .toc a')];const blks=[...document.querySelectorAll('.lg .blk')];
document.querySelectorAll('.lg .win').forEach(w=>{w.querySelectorAll('.tr').forEach((r,i)=>r.style.transitionDelay=(0.35+i*0.12)+'s');});
document.querySelectorAll('.lg .nd').forEach((n,i)=>n.style.setProperty('--d',(0.15+i*0.22)+'s'));
document.querySelectorAll('.lg .cn').forEach((c,i)=>c.style.setProperty('--d',(0.3+i*0.22)+'s'));
document.querySelectorAll('.lg .card .ev, .lg .mail .ev').forEach((e,i)=>e.style.setProperty('--d',(0.3+i*0.14)+'s'));
document.querySelectorAll('.lg .kv div').forEach((e,i)=>e.style.setProperty('--d',(0.9+i*0.1)+'s'));
document.querySelectorAll('.lg .life div').forEach((e,i)=>e.style.setProperty('--d',(0.2+i*0.18)+'s'));
function typeIn(el){if(el.dataset.done)return;el.dataset.done=1;const t=el.dataset.text;let i=0;const id=setInterval(()=>{el.textContent=t.slice(0,++i);if(i>=t.length){clearInterval(id);el.classList.add('done');}},70);}
const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');e.target.querySelectorAll('.win').forEach(w=>{w.classList.add('in');const ty=w.querySelector('.type');if(ty)typeIn(ty);});}});},{root:root,rootMargin:'0px 0px -18% 0px',threshold:0.12});
blks.forEach(b=>io.observe(b));document.querySelectorAll('.lg .cta').forEach(c=>io.observe(c));
const spy=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){links.forEach(l=>l.classList.toggle('on',l.dataset.k===e.target.id));}});},{root:root,rootMargin:'-35% 0px -55% 0px',threshold:0});
blks.forEach(b=>spy.observe(b));
links.forEach(l=>l.addEventListener('click',ev=>{ev.preventDefault();document.getElementById(l.dataset.k).scrollIntoView({behavior:'smooth',block:'start'});}));
const peek=document.querySelector('.lg .peek .win');if(peek)setTimeout(()=>peek.classList.add('in'),300);
const cnt=document.getElementById('cnt');if(cnt){const target=parseInt(cnt.textContent.replace(/,/g,''));const t0=performance.now();const dur=1400;(function f(now){const p=Math.min(1,(now-t0)/dur);cnt.textContent=Math.round(target*(1-Math.pow(1-p,3))).toLocaleString();if(p<1)requestAnimationFrame(f);})(t0);}

// ---- scroll effects v2 ----
const scroller=root||document.scrollingElement; const peekEl=document.querySelector('.lg .peek'); const wash=document.querySelector('.lg .wash'); const tbar=document.getElementById('tbar'); const plat=document.querySelector('.lg .plat'); const grid=document.querySelector('.lg .grid'); const head=document.querySelector('.lg .plat .head');
function onScroll(){const y=scroller.scrollTop; if(peekEl){peekEl.style.transform='translateY('+(-y*0.12)+'px)';} if(wash){wash.style.transform='translateY('+(y*0.25)+'px)';}
 if(tbar&&grid){const r=grid.getBoundingClientRect(); const vh=(root?root.clientHeight:innerHeight); const p=Math.max(0,Math.min(1,(vh*0.5-r.top)/(r.height-vh*0.2))); tbar.style.height=(p*100)+'%';}
 if(head){const r=head.getBoundingClientRect(); const vh=(root?root.clientHeight:innerHeight); if(r.top<vh*0.8)head.classList.add('in');}}
scroller.addEventListener('scroll',onScroll,{passive:true}); onScroll();
// ---- hero demo loop ----
const cur=document.getElementById('cur'), hs=document.getElementById('hs'), hph=document.getElementById('hph'), hbt=document.getElementById('hbt'), pop=document.getElementById('pop'), heroEl=document.querySelector('.lg .hero');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function moveTo(el,dx,dy){const hr=heroEl.getBoundingClientRect(), r=el.getBoundingClientRect(); const x=r.left-hr.left+(dx??r.width/2), y=r.top-hr.top+(dy??r.height/2); cur.style.setProperty('--t','translate('+x+'px,'+y+'px)'); cur.style.transform='translate('+x+'px,'+y+'px)';}
async function click(el){cur.classList.add('click'); await wait(260); cur.classList.remove('click');}
async function demo(){ if(!cur||!peekEl) return; const win=peekEl.querySelector('.win'); const rows=[...win.querySelectorAll('.tr')]; const hdr=win.querySelector('.wbar b'); const name='케이브레인컴퍼니';
 while(true){
  // reset
  pop.classList.remove('show'); rows.forEach(r=>{r.classList.remove('sel'); r.style.transition='none'; r.style.opacity=0; r.style.transform='translateX(-10px)';}); hph.textContent='회사명 또는 사업자번호 10자리'; hph.style.color='#9a9a96'; hdr.textContent='—';
  await wait(600); cur.classList.add('show'); moveTo(hs,24); await wait(1000); await click(); hs.classList.add('focus'); hph.textContent=''; hph.style.color='#141414';
  for(let i=1;i<=name.length;i++){hph.textContent=name.slice(0,i); await wait(80);} await wait(350);
  moveTo(hbt); await wait(800); hbt.classList.add('press'); await click(); hbt.classList.remove('press'); hs.classList.remove('focus');
  hdr.textContent=name; rows.forEach((r,i)=>{r.style.transition=''; setTimeout(()=>{r.style.opacity=1; r.style.transform='none';},120+i*110);}); await wait(120+rows.length*110+400);
  moveTo(rows[0],160); await wait(900); await click(); rows[0].classList.add('sel');
  const hr=heroEl.getBoundingClientRect(), rr=rows[0].getBoundingClientRect(); pop.style.left=(rr.left-hr.left+150)+'px'; pop.style.top=(rr.bottom-hr.top+8)+'px'; pop.classList.add('show');
  await wait(3200); pop.classList.remove('show'); cur.classList.remove('show'); await wait(900);
 }}
setTimeout(demo,1400);
})();
</script>'''

html = f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS} .lg .frame {{ border:1px solid #d8d7d2; box-shadow:0 1px 0 #d8d7d2 }}</style>
<div class="lg"><h2 style="font-size:20px">메인 — 목차형 + 모션</h2><p class="subtitle">히어로 → 플랫폼(태그 + 두 톤 제목 + 왼쪽 고정 목차 + 오른쪽 5블록, 스크롤하면 목차가 따라감) → CTA → 푸터. 직접 스크롤해 보세요.</p>
<div class="frame">{page}</div></div>'''
open(out, "w", encoding="utf-8").write(html); print("written", len(html))

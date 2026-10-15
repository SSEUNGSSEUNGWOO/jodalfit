# 히어로 자동 데모 루프(가짜 커서) + 스크롤 이펙트 강화
p = "./gen_main_toc.py"; s = open(p, encoding="utf-8").read()

CSS2 = r"""
/* ---- motion v2 ---- */
.lg .hero { perspective:1400px }
.lg .peek { height:420px; transform-origin:50% 0; will-change:transform }
.lg .peek .win { transform:rotateX(8deg) scale(.96); transform-origin:50% 0; transition:transform 1.1s cubic-bezier(.2,.7,.2,1), box-shadow 1.1s ease }
.lg .peek .win.in { transform:none; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 40px 80px -36px rgba(0,0,0,.35) }
.lg h1 .ln { display:inline-block; overflow:hidden; vertical-align:bottom } .lg h1 .ln span { display:inline-block; transform:translateY(110%); animation:up .9s cubic-bezier(.2,.7,.2,1) forwards } .lg h1 .ln:nth-child(2) span { animation-delay:.12s }
@keyframes up { to { transform:none } }
.lg .lede, .lg .search, .lg .sub, .lg .eyebrow { animation:fade .9s ease both } .lg .eyebrow { animation-delay:.05s } .lg .lede { animation-delay:.3s } .lg .search { animation-delay:.42s } .lg .sub { animation-delay:.55s }
@keyframes fade { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:none } }
.lg .blk .shot.rv { transform:translateY(60px) scale(.94); transition-duration:1s } .lg .blk.in .shot.rv { transform:none }
.lg .blk h3.rv { transform:translateY(30px) } .lg .blk h3 { transition-duration:.9s }
.lg .blk.in .win { box-shadow:0 1px 2px rgba(0,0,0,.04), 0 40px 80px -36px rgba(0,0,0,.35) }
.lg .toc { overflow:visible } .lg .toc .bar { position:absolute; left:0; top:0; width:2px; height:100%; background:#ececea } .lg .toc .bar i { position:absolute; left:0; top:0; width:100%; height:0; background:#141414; transition:height .15s linear }
.lg .plat .head h2 .w { display:inline-block; opacity:0; transform:translateY(14px); transition:opacity .6s ease var(--d,0s), transform .6s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .lg .plat .head.in h2 .w { opacity:1; transform:none }
.lg .cta { transition:opacity .9s ease, transform .9s cubic-bezier(.2,.7,.2,1), border-radius .9s ease; transform:translateY(40px) scale(.97) } .lg .cta.in { transform:none }
.lg .cta h2 .w { display:inline-block; opacity:0; transform:translateY(16px); transition:opacity .6s ease var(--d,0s), transform .6s ease var(--d,0s) } .lg .cta.in h2 .w { opacity:1; transform:none }
/* demo cursor */
.lg .cur { position:absolute; left:0; top:0; width:22px; height:22px; z-index:5; pointer-events:none; opacity:0; transition:transform .9s cubic-bezier(.3,.7,.2,1), opacity .3s ease; filter:drop-shadow(0 2px 4px rgba(0,0,0,.25)) }
.lg .cur.show { opacity:1 } .lg .cur.click { animation:clk .25s ease } @keyframes clk { 50% { transform:var(--t) scale(.8) } }
.lg .search.focus { box-shadow:0 0 0 3px rgba(232,67,27,.18), 0 12px 32px -16px rgba(0,0,0,.18) }
.lg .search .bt.press { transform:scale(.96); background:#333 }
.lg .pop { position:absolute; z-index:4; width:360px; background:#fff; border:1px solid #e6e4df; border-radius:12px; box-shadow:0 24px 48px -24px rgba(0,0,0,.3); padding:14px 16px; font-size:12.5px; line-height:1.55; color:#5c5c58; opacity:0; transform:translateY(8px) scale(.98); transition:opacity .35s ease, transform .35s cubic-bezier(.2,.7,.2,1) }
.lg .pop.show { opacity:1; transform:none } .lg .pop b { display:block; color:#141414; font-size:13px; margin-bottom:4px }
.lg .pop .tags { display:flex; gap:6px; margin-top:8px } .lg .pop .tags span { padding:3px 8px; border-radius:999px; background:#fdeae4; color:#c8381a; font-size:11px; font-weight:600 }
"""
s = s.replace("MOTION_CSS = ", "MOTION_CSS = " + repr(CSS2) + " + ", 1)

# 히어로 마크업: 제목 줄 분리, 커서, 팝오버
s = s.replace('<h1>오늘의 나라장터를<br>우리 회사 기준으로, <span class="dim">볼 것만.</span></h1>',
              '<h1><span class="ln"><span>오늘의 나라장터를</span></span><br><span class="ln"><span>우리 회사 기준으로, <span class="dim">볼 것만.</span></span></span></h1>')
s = s.replace('<div class="search"><span class="ph">회사명 또는 사업자번호 10자리</span><span class="bt">읽기</span></div>\n<div class="sub">회사가 없으면 <u>키워드로</u></div>\n<div class="peek">',
              '<div class="search" id="hs"><span class="ph" id="hph">회사명 또는 사업자번호 10자리</span><span class="bt" id="hbt">읽기</span></div>\n<div class="sub">회사가 없으면 <u>키워드로</u></div>\n<svg class="cur" id="cur" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.5L10 20z" fill="#141414" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg><div class="pop" id="pop"><b>추천 근거 · 적합 77</b>공고의 과업(교육 콘텐츠·이러닝 유지관리)이 등록업종·공급물품과 겹칩니다. 조달청은 이 분야 반복 발주 기관입니다.<div class="tags"><span>업종 겹침 +28</span><span>물품 겹침 +22</span><span>반복 기관 +12</span></div></div>\n<div class="peek">')
# 목차 진행 바
s = s.replace('<div class="grid"><div class="toc">{toc}</div>', '<div class="grid"><div class="toc"><div class="bar"><i id="tbar"></i></div>{toc}</div>')
# 플랫폼 제목/CTA 제목 단어 분리
s = s.replace('<h2>매일 새벽, 전부 읽어두는 시스템.<br><span class="dim">공고가 올라오면 읽고, 회사 기준으로 남기고, 아침에 알려줍니다.</span></h2></div>',
              '<h2>' + " ".join(f'<span class="w" style="--d:{i*0.06:.2f}s">{w}</span>' for i, w in enumerate("매일 새벽, 전부 읽어두는 시스템.".split())) + '<br><span class="dim">' + " ".join(f'<span class="w" style="--d:{0.4+i*0.05:.2f}s">{w}</span>' for i, w in enumerate("공고가 올라오면 읽고, 회사 기준으로 남기고, 아침에 알려줍니다.".split())) + '</span></h2></div>')
s = s.replace('<div class="cta"><h2>처음 5건은 누구나,<br>전부는 이메일 하나로.</h2>',
              '<div class="cta"><h2>' + " ".join(f'<span class="w" style="--d:{0.2+i*0.08:.2f}s">{w}</span>' for i, w in enumerate("처음 5건은 누구나,".split())) + '<br>' + " ".join(f'<span class="w" style="--d:{0.5+i*0.08:.2f}s">{w}</span>' for i, w in enumerate("전부는 이메일 하나로.".split())) + '</h2>')

JS2 = r"""
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
"""
s = s.replace("})();\n</script>", JS2 + "})();\n</script>", 1)
open(p, "w", encoding="utf-8").write(s); print("patched v2")

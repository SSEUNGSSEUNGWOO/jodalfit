# 캔버스 노드 그룹화 + pathLength, 메인 sticky 수정 + 모션 추가
p = "./gen_canvas_min.py"; s = open(p, encoding="utf-8").read()
s = s.replace('''    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#fff" stroke="{"#e6e6e2" if not muted else "#ececea"}" stroke-width="1"/>\'''',
              '''    s = f'<g class="nd"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#fff" stroke="{"#e6e6e2" if not muted else "#ececea"}" stroke-width="1"/>\'''')
s = s.replace('''        s += f'<text x="{x+w-14}" y="{y+22}" font-size="11" fill="{MUTE}" text-anchor="end" {F}>{status}</text>'
    return s''', '''        s += f'<text x="{x+w-14}" y="{y+22}" font-size="11" fill="{MUTE}" text-anchor="end" {F}>{status}</text>'
    return s + "</g>"''')
s = s.replace('''return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.2"{mk}/>\'''',
              '''return f'<path class="cn" pathLength="1" d="{d}" fill="none" stroke="{color}" stroke-width="1.2"{mk}/>\'''')
open(p, "w", encoding="utf-8").write(s)

p = "./gen_main_toc.py"; s = open(p, encoding="utf-8").read()
MOTION_CSS = r"""
/* ---- motion ---- */
.lg .rv { opacity:0; transform:translateY(22px); transition:opacity .7s cubic-bezier(.2,.7,.2,1), transform .7s cubic-bezier(.2,.7,.2,1); transition-delay:var(--d,0s) }
.lg .in .rv, .lg .rv.in { opacity:1; transform:none }
.lg .win .tr { opacity:0; transform:translateX(-10px); transition:opacity .45s ease, transform .45s cubic-bezier(.2,.7,.2,1) }
.lg .win.in .tr { opacity:1; transform:none }
.lg .win .gate .cover { opacity:0; transition:opacity .6s ease 1.9s } .lg .win.in .gate .cover { opacity:1 }
.lg .win .gate .rows { filter:blur(0); opacity:1; transition:filter .8s ease 1.6s, opacity .8s ease 1.6s } .lg .win.in .gate .rows { filter:blur(3px); opacity:.55 }
.lg .win .gcard { transform:translateY(16px) scale(.97); transition:transform .6s cubic-bezier(.2,.7,.2,1) 1.9s } .lg .win.in .gcard { transform:none }
.lg .type::after { content:"|"; margin-left:1px; color:#141414; animation:blink 1s steps(1) infinite } .lg .type.done::after { content:"" }
@keyframes blink { 50% { opacity:0 } }
.lg .cn { stroke-dasharray:1; stroke-dashoffset:1; transition:stroke-dashoffset .9s cubic-bezier(.4,0,.2,1) var(--d,0s) } .lg .in .cn { stroke-dashoffset:0 }
.lg .nd { opacity:0; transform:translateY(8px); transition:opacity .5s ease var(--d,0s), transform .5s cubic-bezier(.2,.7,.2,1) var(--d,0s) } .lg .in .nd { opacity:1; transform:none }
.lg .ev { opacity:0; transform:translateX(-8px); transition:opacity .45s ease var(--d,0s), transform .45s ease var(--d,0s) } .lg .in .ev { opacity:1; transform:none }
.lg .life div { opacity:.35; transition:opacity .4s ease var(--d,0s) } .lg .in .life div { opacity:1 }
.lg .kv div { opacity:0; transform:scale(.97); transition:opacity .4s ease var(--d,0s), transform .4s ease var(--d,0s) } .lg .in .kv div { opacity:1; transform:none }
.lg .cta { opacity:0; transform:translateY(26px); transition:opacity .8s ease, transform .8s cubic-bezier(.2,.7,.2,1) } .lg .cta.in { opacity:1; transform:none }
.lg .toc a { transition:color .25s ease, transform .25s ease } .lg .toc a.on { transform:translateX(4px) }
.lg .blk h3 b { background:linear-gradient(#141414,#141414) no-repeat 0 100%/0 2px; transition:background-size .8s cubic-bezier(.2,.7,.2,1) .2s } .lg .blk.in h3 b { background-size:100% 2px }
"""
s = s.replace("CSS = gl.CSS + '''", "CSS = gl.CSS.replace('.lg .page { position:relative; background:#fff; color:#141414; overflow:hidden }', '.lg .page { position:relative; background:#fff; color:#141414; overflow:clip }') + MOTION_CSS + '''")
s = s.replace("gl = load(", "MOTION_CSS = " + repr(MOTION_CSS) + "\ngl = load(", 1)
s = s.replace("gl.window()),", 'gl.window().replace(f"<b>{CO}</b>", f"<b class=\\"type\\" data-text=\\"{CO}\\"></b>", 1)),')
s = s.replace('''body = "".join(f'<div class="blk" id="{k}"><h3>{h}</h3><div class="shot {"flat" if k in ("why","mail","golden") else ""}">{s}</div></div>' for k,t,h,s in blocks)''',
              '''body = "".join(f'<div class="blk" id="{k}"><h3 class="rv">{h}</h3><div class="shot rv {"flat" if k in ("why","mail","golden") else ""}" style="--d:.15s">{s}</div></div>' for k,t,h,s in blocks)''')
a = s.index("<script>"); b = s.index("</script>") + len("</script>")
SCRIPT = r"""<script>
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
document.querySelectorAll('.lg .eyebrow').forEach(eb=>{const m=eb.innerHTML.match(/([\d,]+)건/);if(!m)return;const target=parseInt(m[1].replace(/,/g,''));const t0=performance.now();const dur=1400;(function f(now){const p=Math.min(1,(now-t0)/dur);const v=Math.round(target*(1-Math.pow(1-p,3)));eb.innerHTML=eb.innerHTML.replace(/[\d,]+건/,v.toLocaleString()+'건');if(p<1)requestAnimationFrame(f);})(t0);});
})();
</script>"""
s = s[:a] + SCRIPT + s[b:]
s = s.replace("메인 — 플랫폼 목차형", "메인 — 목차형 + 모션")
open(p, "w", encoding="utf-8").write(s); print("patched")

"""히어로: 가운데는 실제 조달핏 웹(결과 페이지), 주변은 메일·새벽 실행·공고 상세. 패럴랙스 없음."""
import sys, io, contextlib, importlib.util
out = sys.argv[1]
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.argv = [sys.argv[0], f"./_tmp_{name}.html"]
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    return m
gl = load("./gen_long.py", "gl")
N, TOP, CO, rows, top, days, sims, fmt, dd = gl.N, gl.TOP, gl.CO, gl.rows, gl.top, gl.days, gl.sims, gl.fmt, gl.dd
i0, i1, i2 = top[0], top[1], top[2]
n7 = sum(1 for i in top if days[i] <= 7); nB = sum(1 for i in top if float(rows[i][4] or 0) >= 1e8)

CSS = gl.CSS + r'''
.hw .scene { position:relative; height:720px; overflow:hidden; background:linear-gradient(135deg,#f3f1fb 0%,#e9ecfb 45%,#e3e8fb 100%); border-radius:8px }
.hw .scene::before { content:""; position:absolute; inset:0; background:radial-gradient(14px 14px at 7px 7px, rgba(20,20,20,.05) 1px, transparent 1.6px) 0 0/22px 22px }
.hw .w { position:absolute; background:#fff; border:1px solid #e3e3ea; border-radius:14px; box-shadow:0 1px 2px rgba(20,20,40,.04), 0 30px 60px -30px rgba(20,20,60,.35); overflow:hidden }
.hw .tb { display:flex; align-items:center; gap:6px; padding:9px 12px; border-bottom:1px solid #eeeef2; background:#fbfbfd; font-size:11.5px; color:#8a8a92 } .hw .tb i { width:10px; height:10px; border-radius:50%; display:inline-block } .hw .tb i:nth-child(1){background:#ff5f57} .hw .tb i:nth-child(2){background:#febc2e} .hw .tb i:nth-child(3){background:#28c840} .hw .tb .url { flex:1; margin:0 60px; height:22px; border-radius:6px; background:#f1f0ec; display:flex; align-items:center; justify-content:center }
/* main web */
.hw .main { left:330px; top:60px; width:880px; height:660px }
.hw .web { font-size:13px; color:#141414 }
.hw .web .nav { display:flex; align-items:center; gap:18px; padding:10px 20px; border-bottom:1px solid #eeeef2 }
.hw .web .brand { display:flex; align-items:center; gap:7px; font-weight:700; font-size:14px } .hw .web .brand i { width:7px; height:7px; border-radius:50%; background:#e8431b; display:inline-block }
.hw .web .sch { display:flex; border:1px solid #e6e4df; border-radius:8px; height:34px; width:360px; overflow:hidden } .hw .web .sch span:first-child { padding:0 10px; display:flex; align-items:center; font-size:11.5px; font-weight:600; background:#faf9f6; border-right:1px solid #e6e4df; color:#5c5c58 } .hw .web .sch .v { flex:1; padding:0 10px; display:flex; align-items:center; font-weight:600; color:#9a9a96 } .hw .web .sch .v.on { color:#141414 } .hw .web .sch .go { padding:0 12px; display:flex; align-items:center; background:#141414; color:#fff; font-weight:600; font-size:12px }
.hw .web .nav .m { margin-left:auto; color:#5c5c58; display:flex; gap:14px }
.hw .web .h { padding:18px 20px 0; display:flex; justify-content:space-between; align-items:baseline } .hw .web .h h1 { margin:0; font-size:20px; letter-spacing:-0.03em; font-weight:700 } .hw .web .h h1 span { color:#e8431b } .hw .web .h small { color:#9a9a96; font-size:11.5px }
.hw .web .chips { display:flex; gap:5px; padding:10px 20px 8px } .hw .web .chips span { padding:3px 9px; border:1px solid #e6e4df; border-radius:999px; font-size:11.5px } .hw .web .chips span.on { background:#141414; color:#fff; border-color:#141414 }
.hw .web .th, .hw .web .tr { display:grid; grid-template-columns:26px minmax(0,1fr) 130px 52px 66px 44px; gap:0 12px; align-items:center; padding:0 20px } .hw .web .th { font-size:10.5px; color:#9a9a96; padding-bottom:6px; border-bottom:1px solid #141414 }
.hw .web .tr { height:40px; border-bottom:1px solid #f1f1ef; font-size:12.5px; opacity:0; transform:translateX(-8px); transition:opacity .4s, transform .4s } .hw .web .tr.in { opacity:1; transform:none } .hw .web .tr.sel { background:#faf9f6; box-shadow:inset 3px 0 0 #e8431b }
.hw .web .tr .no { color:#b0afab; font-size:11px } .hw .web .tr .t { font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .hw .web .tr .o { color:#5c5c58; font-size:11.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis } .hw .web .r { text-align:right } .hw .web .pill { display:inline-block; padding:2px 7px; border-radius:999px; font-size:10.5px; font-weight:600; background:#f1f0ec; color:#555 } .hw .web .pill.hot { background:#fdeae4; color:#c8381a } .hw .web .pill.warm { background:#fff4e0; color:#9a5b00 } .hw .web .fit { color:#e8431b; font-weight:600 }
.hw .web .why { margin:0 20px; max-height:0; overflow:hidden; transition:max-height .6s cubic-bezier(.2,.7,.2,1) } .hw .web .why.open { max-height:140px } .hw .web .why div { margin:8px 0 10px 38px; padding:10px 12px; border-left:2px solid #e8431b; background:#faf9f6; font-size:12px; line-height:1.55; color:#444 } .hw .web .why b { color:#141414 } .hw .web .why .acts { display:flex; gap:6px; margin-top:8px } .hw .web .why .acts span { padding:4px 9px; border:1px solid #e6e4df; border-radius:5px; font-size:11px; color:#141414 } .hw .web .why .acts span.p { background:#141414; color:#fff; border-color:#141414 }
.hw .web .gate { position:relative } .hw .web .gate .rows { filter:blur(3px); opacity:.5 } .hw .web .gate .cover { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:linear-gradient(rgba(255,255,255,0), rgba(255,255,255,.7) 40%, #fff) }
.hw .web .gcard { width:380px; background:#fff; border:1px solid #e6e4df; border-radius:12px; box-shadow:0 20px 40px -20px rgba(0,0,0,.3); padding:14px 16px; text-align:center } .hw .web .gcard b { display:block; font-size:14px } .hw .web .gcard p { margin:4px 0 10px; font-size:11.5px; color:#5c5c58 } .hw .web .gcard .in { display:flex; gap:5px } .hw .web .gcard .in span:first-child { flex:1; height:34px; border:1px solid #e6e4df; border-radius:7px; display:flex; align-items:center; padding:0 10px; color:#9a9a96; font-size:12px } .hw .web .gcard .in span:last-child { height:34px; padding:0 12px; border-radius:7px; background:#141414; color:#fff; font-weight:600; font-size:12px; display:flex; align-items:center }
.hw .cur { position:absolute; width:20px; height:20px; z-index:9; pointer-events:none; opacity:0; transition:transform .8s cubic-bezier(.3,.7,.2,1), opacity .3s; filter:drop-shadow(0 2px 4px rgba(0,0,0,.25)) } .hw .cur.show { opacity:1 }
/* satellites */
.hw .mail { left:36px; top:70px; width:270px } .hw .mail .mh { padding:9px 12px; border-bottom:1px solid #eeeef2; background:#fbfaf8; font-size:11px; color:#5c5c58; display:flex; gap:10px } .hw .mail .mh b { color:#141414 } .hw .mail .mb { padding:12px 14px 14px; font-size:12px } .hw .mail .mb h4 { margin:0 0 8px; font-size:13px }
.hw .mail .ev { display:flex; align-items:center; gap:8px; padding:7px 0; border-top:1px solid #f1f0ec; opacity:0; transform:translateX(-6px); transition:opacity .4s, transform .4s } .hw .mail .ev.in { opacity:1; transform:none } .hw .mail .ev i { width:18px; height:18px; border-radius:5px; background:#fdeae4; color:#c8381a; font-size:10px; font-weight:700; font-style:normal; display:inline-flex; align-items:center; justify-content:center; flex:none } .hw .mail .ev span { margin-left:auto; color:#9a9a96; font-size:10.5px; flex:none }
.hw .mail .badge { position:absolute; right:12px; top:8px; background:#e8431b; color:#fff; font-size:10px; font-weight:700; border-radius:999px; padding:1px 7px; opacity:0; transform:scale(.6); transition:opacity .3s, transform .3s cubic-bezier(.3,1.5,.5,1) } .hw .mail .badge.in { opacity:1; transform:none }
.hw .runw { left:56px; top:400px; width:270px } .hw .runw .b { padding:12px 14px 14px; font-size:12px } .hw .runw .hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px } .hw .runw .hd b { font-size:13px } .hw .runw .live { display:flex; align-items:center; gap:5px; color:#1a8a4a; font-weight:600; font-size:11px } .hw .runw .live i { width:7px; height:7px; border-radius:50%; background:#1a8a4a; animation:pulse 1.4s ease infinite } @keyframes pulse { 50% { opacity:.3 } }
.hw .runw .st { display:flex; align-items:center; gap:8px; padding:6px 0; color:#5c5c58 } .hw .runw .st i { width:14px; height:14px; border-radius:50%; border:1.5px solid #d9d9e2; display:inline-block; position:relative; flex:none } .hw .runw .st.run i { border-color:#c9c9d2; border-top-color:#141414; animation:spin 1s linear infinite } .hw .runw .st.done i { border-color:#5dc08a; background:#e9f8ef } .hw .runw .st.done i::after { content:""; position:absolute; left:4px; top:1.5px; width:3px; height:6px; border:solid #1a8a4a; border-width:0 1.5px 1.5px 0; transform:rotate(45deg) } .hw .runw .st.done { color:#141414 } .hw .runw .st span { margin-left:auto; color:#9a9a96; font-size:10.5px } @keyframes spin { to { transform:rotate(360deg) } }
.hw .det { right:16px; top:120px; width:260px } .hw .det .b { padding:12px 14px 14px; font-size:12px } .hw .det h5 { margin:0; font-size:13px; line-height:1.4 } .hw .det .m { color:#8a8a92; margin:4px 0 10px } .hw .det .lc { display:grid; grid-template-columns:repeat(6,1fr); gap:3px; margin-bottom:4px } .hw .det .lc i { height:4px; border-radius:2px; background:#e9e9ee; display:block } .hw .det .lc i.on { background:#141414 } .hw .det .lc i.hot { background:#e8431b } .hw .det .lb { display:flex; justify-content:space-between; font-size:10px; color:#8a8a92; margin-bottom:10px } .hw .det .kv { display:flex; gap:6px } .hw .det .kv span { flex:1; padding:7px 8px; border:1px solid #e9e9ee; border-radius:7px; font-size:10.5px; color:#8a8a92 } .hw .det .kv b { display:block; font-size:13px; color:#141414 }
.hw .det .peer { margin-top:10px; border-top:1px solid #f1f0ec; padding-top:8px } .hw .det .peer div { display:flex; justify-content:space-between; padding:4px 0; color:#444 } .hw .det .peer div span:last-child { color:#9a9a96 }
'''
def tr(k, i):
    d = days[i]; pill = f'<span class="pill hot">{dd(d)}</span>' if d <= 1 else (f'<span class="pill warm">{dd(d)}</span>' if d <= 7 else f'<span class="pill">{dd(d)}</span>')
    return f'<div class="tr" id="row{k}"><span class="no">{k:02d}</span><span class="t">{rows[i][0]}</span><span class="o">{rows[i][1]}</span><span class="r">{pill}</span><span class="r">{fmt(rows[i][4])}</span><span class="r fit">{int(sims[i]*100)}</span></div>'
main = f'''<div class="w main"><div class="tb"><i></i><i></i><i></i><span class="url">jodalfit.co.kr/recommendations</span></div>
<div class="web"><div class="nav"><span class="brand"><i></i>조달핏</span><div class="sch"><span>회사</span><span class="v" id="sv">회사명 또는 사업자번호</span><span class="go" id="sgo">읽기</span></div><span class="m"><span>공고</span><span>기업</span><span>지도</span><span>인사이트</span></span></div>
<div class="h"><h1 id="h1">오늘 {N:,}건. <span style="color:#8a8a86;font-weight:450">회사명을 넣으면 볼 것만 남깁니다.</span></h1><small>05:00 갱신</small></div>
<div class="chips" id="chips" style="opacity:0"><span class="on">전체 {TOP}</span><span>7일 내 마감 {n7}</span><span>1억 이상 {nB}</span><span>검토 인장 1</span></div>
<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>
{tr(1,i0)}<div class="why" id="why"><div><b>추천 근거</b> — 교육 콘텐츠·이러닝 유지관리 과업이 등록업종·공급물품과 겹칩니다. {rows[i0][1]}은 이 분야 반복 발주 기관(최근 1년 3건).<div class="acts"><span id="stamp">검토 인장</span><span>상세 분석</span><span class="p">나라장터 원문 ↗</span></div></div></div>
{"".join(tr(k+2,i) for k,i in enumerate(top[1:5]))}
<div class="gate" id="gate" style="opacity:0"><div class="rows">{"".join(tr(k+6,i) for k,i in enumerate(top[5:8]))}</div><div class="cover"><div class="gcard"><b>나머지 {TOP-5}건은 이메일로 열립니다</b><p>비밀번호 없음 · 메일 링크가 로그인 · 아침 7시에 새로 남은 것만</p><div class="in"><span>name@company.co.kr</span><span>{TOP-5}건 열기</span></div></div></div></div>
</div><svg class="cur" id="cur" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.5L10 20z" fill="#141414" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg></div>'''

mail = f'''<div class="w mail" id="mailw"><div class="tb"><i></i><i></i><i></i></div><span class="badge" id="mbadge">1</span><div class="mh"><span>보낸사람 <b>조달핏</b></span><span style="margin-left:auto">07:00</span></div>
<div class="mb"><h4>{CO}, 오늘 새로 남은 공고 2건</h4>
<div class="ev"><i>1</i><span style="margin:0;color:#141414;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{rows[i1][0]}</span><span>{dd(days[i1])}</span></div>
<div class="ev"><i>2</i><span style="margin:0;color:#141414;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{rows[i2][0]}</span><span>{dd(days[i2])}</span></div>
<div class="ev"><i>!</i><span style="margin:0;color:#141414">내일 마감 1건 — 인장 찍힌 공고</span><span>오늘</span></div>
<div style="margin-top:10px;font-size:10.5px;color:#9a9a96">새로 남은 것만 보냅니다 · 없는 날은 안 보냄 · 한 번에 해지</div></div></div>'''

runw = f'''<div class="w runw"><div class="tb"><i></i><i></i><i></i></div><div class="b"><div class="hd"><b>오늘 05:00 실행</b><span class="live"><i></i>Live</span></div>
<div class="st" id="s1"><i></i>공고 수집 · 나라장터 API<span>1,537건</span></div>
<div class="st" id="s2"><i></i>임베딩 · text-embedding-3-small<span>41s</span></div>
<div class="st" id="s3"><i></i>회사 벡터 갱신<span>312곳</span></div>
<div class="st" id="s4"><i></i>{CO} 매칭 · 자격 · 정렬<span>1.2s</span></div>
<div class="st" id="s5"><i></i>아침 7시 메일 예약<span>2건</span></div></div></div>'''

det = f'''<div class="w det"><div class="tb"><i></i><i></i><i></i><span class="url">jodalfit.co.kr/notices/…</span></div><div class="b">
<h5>{rows[i0][0]}</h5><div class="m">{rows[i0][1]} · {dd(days[i0])} · {fmt(rows[i0][4])}</div>
<div class="lc"><i class="on"></i><i class="on"></i><i class="hot"></i><i class="on"></i><i></i><i></i></div><div class="lb"><span>발주계획</span><span>사전규격</span><span>의견</span><span>본공고</span><span>개찰</span><span>계약</span></div>
<div class="kv"><span><b>{int(sims[i0]*100)}</b>적합</span><span><b>87.2%</b>평균 투찰률</span><span><b>3건</b>기관 1년 발주</span></div>
<div class="peer"><div><span>비슷한 공고 낙찰사</span><span>최근 1년</span></div><div><span>주식회사 ○○○정보</span><span>2건 · 86.1%</span></div><div><span>(주)△△△에듀</span><span>1건 · 88.9%</span></div></div></div></div>'''

JS = r'''<script>
(function(){
const wait=ms=>new Promise(r=>setTimeout(r,ms)); const CO='__CO__', N=__N__, TOP=__TOP__;
const main=document.querySelector('.hw .main'), cur=document.getElementById('cur'), sv=document.getElementById('sv'), sgo=document.getElementById('sgo'), h1=document.getElementById('h1'), chips=document.getElementById('chips'), gate=document.getElementById('gate'), why=document.getElementById('why');
const rowsEl=[...document.querySelectorAll('.hw .web .tr')].filter(r=>!r.closest('.gate'));
function moveTo(el,dx,dy){const mr=main.getBoundingClientRect(), r=el.getBoundingClientRect(); cur.style.transform='translate('+(r.left-mr.left+(dx??r.width/2))+'px,'+(r.top-mr.top+(dy??r.height/2))+'px)';}
const sts=[1,2,3,4,5].map(k=>document.getElementById('s'+k)); const evs=[...document.querySelectorAll('.hw .mail .ev')]; const badge=document.getElementById('mbadge');
async function runSteps(){sts.forEach(s=>s.className='st'); for(const s of sts){s.className='st run'; await wait(650); s.className='st done';}}
async function loop(){ while(true){
  // reset
  rowsEl.forEach(r=>{r.classList.remove('in','sel');}); why.classList.remove('open'); chips.style.opacity=0; gate.style.opacity=0; sv.textContent='회사명 또는 사업자번호'; sv.classList.remove('on'); h1.innerHTML='오늘 '+N.toLocaleString()+'건. <span style="color:#8a8a86;font-weight:450">회사명을 넣으면 볼 것만 남깁니다.</span>'; evs.forEach(e=>e.classList.remove('in')); badge.classList.remove('in');
  runSteps();
  await wait(700); cur.classList.add('show'); moveTo(sv,30); await wait(900); sv.textContent=''; sv.classList.add('on');
  for(let i=1;i<=CO.length;i++){sv.textContent=CO.slice(0,i); await wait(75);} await wait(300);
  moveTo(sgo); await wait(700); sgo.style.background='#333'; await wait(150); sgo.style.background='';
  h1.innerHTML=CO+', 오늘 '+N.toLocaleString()+'건 중 <span>볼 것은 '+TOP+'건</span>.'; chips.style.opacity=1;
  for(let i=0;i<rowsEl.length;i++){rowsEl[i].classList.add('in'); await wait(140);} gate.style.opacity=1; await wait(500);
  moveTo(rowsEl[0],180); await wait(800); rowsEl[0].classList.add('sel'); why.classList.add('open'); await wait(1600);
  moveTo(document.getElementById('stamp')); await wait(700); const st=document.getElementById('stamp'); st.style.background='#141414'; st.style.color='#fff'; st.textContent='✓ 인장'; await wait(1200); st.style.background=''; st.style.color=''; st.textContent='검토 인장';
  cur.classList.remove('show'); badge.classList.add('in'); for(const e of evs){e.classList.add('in'); await wait(260);}
  await wait(3800);
 }}
loop();
})();
</script>'''.replace("__CO__", CO).replace("__N__", str(N)).replace("__TOP__", str(TOP))

html = f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS} .hw h2 {{ margin:0 0 4px; font-size:20px }} .hw p.sub {{ margin:0 0 16px; font-size:13px; color:#555; line-height:1.6 }}</style>
<div class="lg hw"><h2>히어로 — 실제 웹이 가운데</h2><p class="sub">가운데: 실제 조달핏 결과 페이지(헤더 검색 → 회사명 타이핑 → 읽기 → 5건 + 게이트 → 1행 펼쳐 "추천 근거" → 검토 인장). 왼쪽 위: 아침 7시 메일이 도착. 왼쪽 아래: 오늘 05:00 실행이 단계별로 완료. 오른쪽: 1위 공고의 상세 페이지. 패럴랙스 없음, 약 16초 주기 반복.</p>
<div class="scene">{main}{mail}{runw}{det}</div>{JS}</div>'''
open(out, "w", encoding="utf-8").write(html); print("written", len(html))

"""Attio식 롱 스크롤 메인: 히어로 → 섹션별(제목 + 제품 화면) → CTA → 푸터. 실제 데이터."""
import sys, json, random, datetime as dt
import numpy as np, psycopg
random.seed(1)
out = sys.argv[1]
OLD = [l.split("=",1)[1].strip() for l in open("C:/Dev/personal/jodalfit/backend/.env", encoding="utf-8") if l.startswith("DATABASE_URL=")][0]
conn = psycopg.connect(OLD, connect_timeout=20, options="-c statement_timeout=300000"); conn.execute("set client_encoding to 'UTF8'")
rows = conn.execute("""select bid_ntce_nm, ntce_instt_nm, coalesce(bsns_div_nm,''), bid_clse_date, presmpt_prce, embedding::text, bid_ntce_date
  from bid_notices where bid_clse_date >= current_date and embedding is not null""").fetchall()
X = np.array([json.loads(r[5]) for r in rows], dtype=np.float32); X /= np.linalg.norm(X, axis=1, keepdims=True)
comp = conn.execute("select corp_nm, embedding::text from companies where corp_nm ilike %s and embedding is not null limit 1", ("%케이브레인컴퍼니%",)).fetchone()
c = np.array(json.loads(comp[1]), dtype=np.float32); c /= np.linalg.norm(c)
sims = X @ c; today = dt.date.today(); days = np.array([(r[3]-today).days for r in rows]); N = len(rows)
seen=set(); top=[]
for i in np.argsort(-sims):
    if rows[i][0] in seen: continue
    seen.add(rows[i][0]); top.append(i)
    if len(top)==30: break
TOP=len(top); CO="케이브레인컴퍼니"
def fmt(p):
    if p is None: return "—"
    p=float(p); return f"{p/1e8:.1f}억" if p>=1e8 else f"{p/1e4:,.0f}만"
def dd(d): return "오늘" if d==0 else f"D-{d}"
n7=sum(1 for i in top if days[i]<=7); nB=sum(1 for i in top if float(rows[i][4] or 0)>=1e8)

CSS='''
.lg * { box-sizing:border-box; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif; font-variant-numeric:tabular-nums }
.lg .page { position:relative; background:#fff; color:#141414; overflow:hidden }
.lg .wash { position:absolute; left:0; right:0; top:0; height:900px; background:radial-gradient(900px 480px at 50% -8%, #f3efe9 0%, rgba(243,239,233,0) 70%), radial-gradient(14px 14px at 7px 7px, #ebebe8 1.1px, transparent 1.6px) 0 0/22px 22px; -webkit-mask-image:linear-gradient(#000 60%, transparent); mask-image:linear-gradient(#000 60%, transparent) }
.lg .nav { position:relative; display:flex; align-items:center; justify-content:space-between; padding:18px 48px; font-size:13px; color:#555 }
.lg .brand { display:flex; align-items:center; gap:8px; color:#141414; font-weight:700; font-size:14.5px } .lg .brand i { width:7px; height:7px; border-radius:50%; background:#e8431b; display:inline-block }
.lg .pillnav { display:flex; gap:4px; padding:4px; border:1px solid #e8e6e1; border-radius:999px; background:rgba(255,255,255,.7) } .lg .pillnav span { padding:6px 12px; border-radius:999px } .lg .pillnav span.on { background:#141414; color:#fff }
.lg .hero { position:relative; text-align:center; padding:64px 48px 0 }
.lg .eyebrow { display:inline-flex; align-items:center; gap:8px; padding:5px 12px 5px 6px; border:1px solid #e8e6e1; border-radius:999px; background:#fff; font-size:12px; color:#555 } .lg .eyebrow b { background:#141414; color:#fff; border-radius:999px; padding:2px 8px; font-size:11px; font-weight:600 }
.lg h1 { margin:18px auto 0; font-size:56px; line-height:1.06; letter-spacing:-0.045em; font-weight:650; max-width:800px } .lg h1 .dim { color:#8a8a86; font-weight:450 }
.lg .lede { margin:18px auto 0; font-size:16.5px; line-height:1.6; color:#5c5c58; max-width:560px }
.lg .search { margin:28px auto 0; width:560px; height:54px; border:1px solid #e3e1dc; border-radius:14px; background:#fff; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 12px 32px -16px rgba(0,0,0,.18); display:flex; align-items:center; padding:6px 6px 6px 18px }
.lg .search .ph { flex:1; color:#9a9a96; font-size:15px; text-align:left } .lg .search .bt { height:42px; padding:0 18px; border-radius:10px; background:#141414; color:#fff; font-weight:600; font-size:14px; display:flex; align-items:center }
.lg .sub { margin-top:12px; font-size:12.5px; color:#9a9a96 } .lg .sub u { text-decoration:none; border-bottom:1px solid #d8d6d0; color:#5c5c58 }
.lg .peek { text-align:left; position:relative; margin:52px auto 0; width:1000px; height:260px; overflow:hidden; -webkit-mask-image:linear-gradient(#000 55%, transparent); mask-image:linear-gradient(#000 55%, transparent) }
.lg .win { background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 30px 60px -30px rgba(0,0,0,.28); overflow:hidden }
.lg .chrome { display:flex; align-items:center; gap:14px; padding:10px 14px; border-bottom:1px solid #eeece7; background:#fbfaf8 } .lg .dots i { display:inline-block; width:10px; height:10px; border-radius:50%; background:#e6e4df; margin-right:5px } .lg .url { flex:1; max-width:380px; margin:0 auto; height:26px; border-radius:7px; background:#f1f0ec; font-size:11.5px; color:#8a8a86; display:flex; align-items:center; justify-content:center }
.lg .wbar { display:flex; align-items:center; gap:10px; padding:14px 18px 10px; font-size:13px } .lg .wbar b { font-size:15px; font-weight:650 } .lg .wbar .m { color:#8a8a86; font-size:12.5px } .lg .wbar .sp { flex:1 }
.lg .chip { padding:4px 10px; border-radius:999px; font-size:12px; border:1px solid #ebe9e4; color:#444; background:#fff } .lg .chip.on { background:#141414; color:#fff; border-color:#141414 }
.lg .th, .lg .tr { display:grid; grid-template-columns:28px minmax(0,1fr) 150px 70px 84px 70px; gap:0 14px; align-items:center; padding:0 18px }
.lg .th { font-size:11px; color:#9a9a96; padding-top:6px; padding-bottom:8px; border-bottom:1px solid #eeece7; letter-spacing:.02em }
.lg .tr { height:46px; border-bottom:1px solid #f3f2ee; font-size:13.5px } .lg .tr.sel { background:#faf9f6 }
.lg .tr .no { color:#b0afab; font-size:11.5px } .lg .tr .t { font-weight:550; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
.lg .org { display:flex; align-items:center; gap:8px; color:#5c5c58; font-size:12.5px; white-space:nowrap; overflow:hidden } .lg .org i { width:18px; height:18px; border-radius:6px; background:#ecebe6; color:#5c5c58; font-size:10px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none; font-style:normal }
.lg .pill { display:inline-flex; padding:3px 8px; border-radius:999px; font-size:11.5px; font-weight:600; background:#f1f0ec; color:#555 } .lg .pill.hot { background:#fdeae4; color:#c8381a } .lg .pill.warm { background:#fff4e0; color:#9a5b00 }
.lg .r { text-align:right } .lg .fit { display:flex; align-items:center; gap:8px; justify-content:flex-end; font-size:12.5px; color:#444 } .lg .fit i { width:40px; height:5px; border-radius:3px; background:#eeece7; overflow:hidden; display:block } .lg .fit i b { display:block; height:100%; background:#141414; border-radius:3px }
.lg .gate { position:relative } .lg .gate .rows { filter:blur(3px); opacity:.55 } .lg .gate .cover { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:linear-gradient(rgba(255,255,255,0), rgba(255,255,255,.65) 40%, #fff) }
.lg .gcard { width:440px; background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 24px 48px -24px rgba(0,0,0,.3); padding:18px 20px; text-align:center } .lg .gcard b { display:block; font-size:16px; font-weight:650 } .lg .gcard p { margin:6px 0 12px; font-size:12.5px; color:#5c5c58; line-height:1.55 }
.lg .gcard .in { display:flex; gap:6px } .lg .gcard .in span:first-child { flex:1; height:40px; border:1px solid #e6e4df; border-radius:9px; display:flex; align-items:center; padding:0 12px; color:#9a9a96; font-size:13px } .lg .gcard .in span:last-child { height:40px; padding:0 16px; border-radius:9px; background:#141414; color:#fff; font-weight:600; font-size:13px; display:flex; align-items:center }
.lg .sec { position:relative; padding:96px 48px 0 }
.lg .sec .lab { display:inline-flex; align-items:center; gap:8px; font-size:12px; font-weight:600; color:#e8431b; letter-spacing:.02em } .lg .sec .lab i { width:6px; height:6px; border-radius:50%; background:#e8431b; display:inline-block }
.lg .sec h2 { margin:14px 0 0; font-size:38px; line-height:1.12; letter-spacing:-0.04em; font-weight:650; max-width:680px } .lg .sec h2 .dim { color:#8a8a86; font-weight:450 }
.lg .sec p.l { margin:14px 0 0; font-size:15.5px; line-height:1.65; color:#5c5c58; max-width:560px }
.lg .shot { margin-top:36px }
.lg .two { display:grid; grid-template-columns:1fr 1fr; gap:48px; align-items:center } .lg .two .txt h2 { font-size:34px }
.lg .card { background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 1px 2px rgba(0,0,0,.04), 0 24px 48px -24px rgba(0,0,0,.25); padding:18px 20px }
.lg .card .h { display:flex; align-items:center; gap:10px; font-size:12px; color:#8a8a86 } .lg .card .h i { width:26px; height:26px; border-radius:8px; background:#141414; color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; font-style:normal }
.lg .card .t { font-size:15px; font-weight:650; margin-top:10px; line-height:1.4 } .lg .card p { margin:8px 0 0; font-size:13px; line-height:1.65; color:#5c5c58 }
.lg .card .kv { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:12px } .lg .card .kv div { background:#faf9f6; border-radius:8px; padding:9px 11px } .lg .card .kv b { display:block; font-size:15px; font-weight:650 } .lg .card .kv span { font-size:11px; color:#8a8a86 }
.lg .ev { display:flex; align-items:center; gap:10px; padding:9px 0; border-top:1px solid #f1f0ec; font-size:13px } .lg .ev i { width:22px; height:22px; border-radius:6px; background:#fdeae4; color:#c8381a; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; font-style:normal; flex:none } .lg .ev span { color:#8a8a86; margin-left:auto; font-size:12px }
.lg .life { display:grid; grid-template-columns:repeat(6,1fr); gap:0; margin-top:8px } .lg .life div { padding:14px 12px 12px; border-top:2px solid #eeece7; font-size:12.5px } .lg .life div b { display:block; font-size:13.5px; font-weight:650; margin-bottom:3px } .lg .life div span { color:#8a8a86; font-size:11.5px } .lg .life div.on { border-top-color:#141414 } .lg .life div.hot { border-top-color:#e8431b } .lg .life div.hot b { color:#c8381a }
.lg .mail { background:#fff; border:1px solid #e6e4df; border-radius:14px; box-shadow:0 24px 48px -24px rgba(0,0,0,.25); overflow:hidden } .lg .mail .mh { padding:14px 18px; border-bottom:1px solid #eeece7; background:#fbfaf8; font-size:12.5px; color:#5c5c58; display:flex; gap:14px } .lg .mail .mh b { color:#141414 } .lg .mail .mb { padding:18px } .lg .mail .mb h4 { margin:0 0 10px; font-size:16px; letter-spacing:-0.01em }
.lg .cta { position:relative; margin:96px 48px 0; padding:52px 48px; border-radius:20px; background:#141414; color:#fff; text-align:center } .lg .cta h2 { margin:0; font-size:36px; letter-spacing:-0.04em; font-weight:650; line-height:1.12; color:#fff } .lg .cta p { margin:12px auto 0; font-size:15px; color:#b5b5b0; max-width:520px; line-height:1.6 }
.lg .cta .in { display:flex; gap:6px; width:460px; margin:24px auto 0 } .lg .cta .in span:first-child { flex:1; height:48px; border-radius:10px; background:#fff; display:flex; align-items:center; padding:0 14px; color:#9a9a96; font-size:13.5px } .lg .cta .in span:last-child { height:48px; padding:0 20px; border-radius:10px; background:#e8431b; color:#fff; font-weight:650; font-size:13.5px; display:flex; align-items:center }
.lg .footer { position:relative; display:flex; justify-content:space-between; padding:36px 48px 30px; font-size:12px; color:#9a9a96 }
'''
def org(n): return f'<span class="org"><i>{n.replace("주식회사","").replace("(주)","").strip()[:1]}</i>{n}</span>'
def tr(k,i,sel=False):
    d=days[i]; fit=int(sims[i]*100); pill = f'<span class="pill hot">{dd(d)}</span>' if d<=1 else (f'<span class="pill warm">{dd(d)}</span>' if d<=7 else f'<span class="pill">{dd(d)}</span>')
    return f'<div class="tr {"sel" if sel else ""}"><span class="no">{k:02d}</span><span class="t">{rows[i][0]}</span>{org(rows[i][1])}<span class="r">{pill}</span><span class="r">{fmt(rows[i][4])}</span><span class="fit"><i><b style="width:{fit}%"></b></i>{fit}</span></div>'
def window(n_clear=5, gate=True, n_blur=6, head=True):
    body = "".join(tr(k+1,i,sel=(k==0)) for k,i in enumerate(top[:n_clear]))
    if gate:
        body += f'<div class="gate"><div class="rows">{"".join(tr(k+n_clear+1,i) for k,i in enumerate(top[n_clear:n_clear+n_blur]))}</div><div class="cover"><div class="gcard"><b>나머지 {TOP-n_clear}건은 이메일로 열립니다</b><p>비밀번호 없음. 메일의 링크가 로그인이고, 내일부터 새로 남는 공고만 아침 7시에 받습니다.</p><div class="in"><span>name@company.co.kr</span><span>{TOP-n_clear}건 열기</span></div></div></div></div>'
    return f'''<div class="win"><div class="chrome"><span class="dots"><i></i><i></i><i></i></span><span class="url">jodalfit.co.kr/recommendations?company={CO}</span></div>
{f'<div class="wbar"><b>{CO}</b><span class="m">오늘 {N:,}건 중 남은 {TOP}건 · 가까운 순</span><span class="sp"></span><span class="chip on">전체 {TOP}</span><span class="chip">7일 내 마감 {n7}</span><span class="chip">1억 이상 {nB}</span></div>' if head else ''}
<div class="th"><span>#</span><span>공고</span><span>발주기관</span><span class="r">마감</span><span class="r">추정가</span><span class="r">적합</span></div>{body}</div>'''
i0=top[0]
why = f'''<div class="card"><div class="h"><i>왜</i>왜 남았나 · 적합 {int(sims[i0]*100)}</div><div class="t">{rows[i0][0]}</div>
<p>공고의 과업(교육 콘텐츠·이러닝 유지관리)이 이 회사의 등록업종·공급물품과 겹칩니다. {rows[i0][1]}은 이 분야 반복 발주 기관입니다.</p>
<div style="margin-top:12px"><div class="ev"><i>업</i>등록업종 겹침 — 소프트웨어개발업<span>+28</span></div><div class="ev"><i>물</i>공급물품 겹침 — 이러닝 콘텐츠<span>+22</span></div><div class="ev"><i>기</i>반복 발주 기관 — 최근 1년 3건<span>+12</span></div><div class="ev"><i>자</i>자격 제한 없음<span>통과</span></div></div>
<div class="kv"><div><b>{dd(days[i0])}</b><span>마감</span></div><div><b>{fmt(rows[i0][4])}</b><span>추정가</span></div><div><b>87.2%</b><span>비슷한 공고 평균 투찰률 (n=14)</span></div><div><b>3건</b><span>이 기관 최근 1년 발주</span></div></div></div>'''
life = f'''<div class="card" style="padding:18px 20px 14px"><div class="h"><i>공</i>공고 라이프사이클 · {rows[i0][0][:28]}…</div>
<div class="life"><div class="on"><b>발주계획</b><span>2026.07</span></div><div class="on"><b>사전규격 공개</b><span>10.02</span></div><div class="hot"><b>의견 마감</b><span>10.09 · 의견 2건</span></div><div class="on"><b>본공고</b><span>{rows[i0][6]} ● 지금</span></div><div><b>개찰</b><span>{rows[i0][3]}</span></div><div><b>계약</b><span>—</span></div></div>
<p style="margin:14px 0 0;font-size:12.5px;color:#5c5c58">사전규격 단계에서 이 공고를 봤다면 과업 범위에 의견을 낼 수 있었습니다. 다음 공고는 그 단계에서 알려드립니다.</p></div>'''
mail = f'''<div class="mail"><div class="mh"><span>보낸사람 <b>조달핏</b></span><span>받는사람 <b>jansseung@gmail.com</b></span><span style="margin-left:auto">내일 07:00</span></div>
<div class="mb"><h4>{CO}, 오늘 새로 남은 공고 2건</h4>{"".join(f'<div class="ev"><i>{k+1}</i>{rows[i][0]}<span>{rows[i][1]} · {dd(days[i])}</span></div>' for k,i in enumerate(top[1:3]))}<div class="ev"><i>!</i>내일 마감 — {rows[min(top,key=lambda i:days[i])][0][:30]}…<span>{dd(days[min(top,key=lambda i:days[i])])}</span></div>
<div style="margin-top:14px;font-size:12px;color:#9a9a96">새로 남은 것만 보냅니다. 없는 날은 보내지 않습니다. · 한 번에 해지</div></div></div>'''

page = f'''<div class="page"><div class="wash"></div>
<div class="nav"><span class="brand"><i></i>조달핏</span><div class="pillnav"><span class="on">추천</span><span>공고</span><span>기업</span><span>인사이트</span></div><span>문의</span></div>
<div class="hero"><span class="eyebrow"><b>오늘</b> {N:,}건 진행 중 · 05:00 갱신</span>
<h1>오늘의 나라장터를<br>우리 회사 기준으로, <span class="dim">볼 것만.</span></h1>
<p class="lede">회사명 하나면 등록업종·공급물품·수주 이력을 읽어 오늘 공고 전부를 걸러냅니다. 회원가입 없이 바로.</p>
<div class="search"><span class="ph">회사명 또는 사업자번호 10자리</span><span class="bt">읽기</span></div>
<div class="sub">회사가 없으면 <u>키워드로</u></div>
<div class="peek">{window(gate=False, n_clear=5)}</div></div>

<div class="sec"><span class="lab"><i></i>01 · 읽기</span><h2>{N:,}건을 전부 읽고, <span class="dim">검토할 것만 남깁니다.</span></h2>
<p class="l">예시 회사 {CO}의 오늘입니다. 처음 5건은 누구나 근거까지 볼 수 있고, 나머지는 이메일 하나로 열립니다.</p>
<div class="shot">{window()}</div></div>

<div class="sec"><div class="two"><div class="txt"><span class="lab"><i></i>02 · 근거</span><h2>점수가 아니라 <span class="dim">왜 남았는지.</span></h2><p class="l">등록업종·공급물품·수주 이력 중 어디가 겹쳤는지, 발주기관이 이 분야를 반복 발주하는지, 자격 제한에 걸리는지. 행마다 붙습니다.</p></div>{why}</div></div>

<div class="sec"><span class="lab"><i></i>03 · 골든타임</span><h2>사전규격부터 개찰까지, <span class="dim">한 공고의 여섯 단계.</span></h2>
<p class="l">본공고가 뜨면 이미 늦은 경우가 많습니다. 사전규격 단계에서 의견을 낼 수 있는 기간을 놓치지 않게 합니다.</p>
<div class="shot">{life}</div></div>

<div class="sec"><div class="two"><div class="txt"><span class="lab"><i></i>04 · 알림</span><h2>새로 남으면 <span class="dim">아침 7시에.</span></h2><p class="l">비밀번호 없이 이메일 하나로 시작합니다. 회사를 기억하고, 검토 인장을 보관하고, 새로 남은 공고만 보냅니다. 없는 날은 보내지 않습니다.</p></div>{mail}</div></div>

<div class="cta"><h2>처음 5건은 누구나,<br>전부는 이메일 하나로.</h2><p>가입은 이메일 입력이 전부입니다. 결제 없음, 비밀번호 없음.</p><div class="in"><span>name@company.co.kr</span><span>시작하기</span></div></div>
<div class="footer"><span>조달핏 · 나라장터 공공데이터 기반 · 낙찰을 보장하지 않습니다</span><span>개인정보처리방침 · 기업 정보 비공개 요청 · 문의</span></div></div>'''

html=f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS} .lg .frame {{ border:1px solid #d8d7d2; box-shadow:0 1px 0 #d8d7d2 }}</style>
<div class="lg"><h2 style="font-size:20px">메인 — 롱 스크롤</h2><p class="subtitle">히어로(제목·검색 + 살짝 보이는 제품 창) → 01 읽기(결과 창, 5건 + 게이트) → 02 근거 → 03 골든타임 → 04 알림 → CTA → 푸터. 섹션마다 제목 하나, 제품 화면 하나.</p>
<div class="frame">{page}</div></div>'''
open(out,"w",encoding="utf-8").write(html); print("written",len(html))

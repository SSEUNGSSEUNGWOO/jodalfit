"""로그인·회원가입 흐름 최종 시안(`prototypes/login-final.html`) — 이메일 + 비밀번호.
결정(2026-10-17 승우님): 비밀번호 있어야 한다 · 회사 연결 대신 **저장한 회사**(즐겨찾기, 여러 곳) · nav 라벨 '로그인' · 흐름 전체.

가입 = 이메일 + 비밀번호(8자 이상) + 이용약관(필수)·개인정보(필수)·알림 수신(선택) → 확인 메일 1회 → 로그인됨.
로그인 = 이메일 + 비밀번호. 재설정은 메일 링크. 이름·연락처·사업자번호는 받지 않는다.
회사는 회사·결과 페이지 머리의 ☆ 로 여러 곳 저장 — nav 메뉴와 검토함에서 바로 연다.

장면: 1 로그인 → 2 회원가입 → 3 확인 메일 보냄 → 4 메일 → 5 가입 완료·로그인됨(☆ 회사 저장) → 6 재설정(6a 보냄 · 6b 메일 · 6c 새 비밀번호)
   → 게이트(결과·회사 페이지 표 안: 로그인 / 회원가입 두 버튼) → 7 로그아웃.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_login.py ../docs/design/data/sample.json ../docs/design/prototypes/login-final.html
검증: gen_login.py --check ../docs/design/prototypes/login-final.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_flow import TILE  # noqa: E402
from gen_split import trow  # noqa: E402
from gen_results_final import CSS as FINAL_CSS  # noqa: E402

EMAIL = "you@company.co.kr"
TTL = 60   # 이메일 확인·비밀번호 재설정 링크 유효 분. 1회.
SAVED = ["한종산업개발 주식회사", "(유)금강환경"]   # 저장한 회사(즐겨찾기) 예시

CSS = FINAL_CSS + r"""
html, body { background:#faf9f7 }
.wrap { padding-bottom:140px }
/* nav — 비로그인 '로그인' / 로그인됨 이메일 앞부분 + 메뉴(저장한 회사·검토함·설정·로그아웃) */
.nav .cta { border-bottom:1px solid #141414; color:#141414 } .nav .me { position:relative; color:#141414; font-weight:600; cursor:pointer; border-bottom:1px solid #141414 }
.nav .me .menu { display:none; position:absolute; right:0; top:28px; background:#fff; border:1px solid #e6e4df; border-radius:10px; padding:6px; min-width:240px; font-weight:450; z-index:5; box-shadow:0 8px 24px rgba(20,20,20,.06); text-align:left }
.nav .me.open .menu { display:block } .menu a { display:block; padding:9px 12px; border-radius:6px; color:#141414; font-size:13.5px } .menu a:hover { background:#f6f5f2 } .menu a.dim { color:#737370 } .menu .sep { height:1px; background:#ececea; margin:6px 4px }
.menu a small { display:block; color:#737370; font-size:12px; margin-top:1px } .menu .k { display:block; padding:8px 12px 2px }
.menu a.co { padding:7px 12px } .menu a.co::before { content:"★"; color:#f97316; font-size:11px; margin-right:8px; vertical-align:1px }
/* 좁은 판 — 입구와 같은 폭 */
.narrow { max-width:520px; margin:48px auto 0 } .narrow h1 { margin:0 0 6px; font-size:28px; letter-spacing:-0.03em; font-weight:650 } .narrow .lead { font-size:14.5px; color:#55554f; line-height:1.65; margin:0 0 22px }
.pane { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:26px 28px 28px }
.f label { display:block } .f .k { display:block; margin-bottom:6px } .f .fld + .fld { margin-top:14px }
.f input[type=email], .f input[type=password], .f input[type=text] { width:100%; height:46px; border:1px solid #e3e1dc; border-radius:8px; padding:0 14px; font:inherit; font-size:16px; color:#141414; background:#fff; outline:none; transition:border-color .15s, box-shadow .15s }
.f input:focus { border-color:#f97316; box-shadow:0 0 0 4px rgba(249,115,22,.14) } .f input::placeholder { color:#9b9a95 } .f input[disabled] { color:#737370; background:#faf9f7 }
.f .pw { position:relative } .f .pw input { padding-right:56px } .f .pw .eye { position:absolute; right:12px; top:34px; font-size:12.5px; color:#55554f; border:0; border-bottom:1px solid #d8d6d0; cursor:pointer; background:none; padding:0; font-family:inherit }
.f .hint { font-size:12.5px; color:#6b6b67; margin-top:6px; line-height:1.55 } .f .hint[data-min] { display:none } .f .hint.bad { display:block; color:#141414; border-left:2px solid #f97316; padding-left:8px }
.f .row2 { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px } .f .row2 .k { margin:0 } .f .row2 a { font-size:12.5px; color:#55554f; border-bottom:1px solid #d8d6d0 }
.f .cs { margin:16px 0 18px; display:flex; flex-direction:column; gap:8px } .f .cs label { display:flex; gap:8px; align-items:flex-start; font-size:13px; line-height:1.55; color:#333; cursor:pointer }
.f .cs input { margin:3px 0 0; accent-color:#141414 } .f .cs a { border-bottom:1px solid #d8d6d0 } .f .cs .opt { color:#55554f } .f .cs .opt .k { display:inline; margin:0 6px 0 0; color:#737370 }
.f .bt.dark { width:100%; height:46px; justify-content:center; font-size:15px; cursor:pointer; margin-top:16px } .f .cs + .bt.dark { margin-top:0 } .f .bt.dark[disabled] { background:#e3e1dc; border-color:#e3e1dc; color:#8f8f8b; cursor:default }
.f .note { margin-top:14px; font-size:12.5px; color:#6b6b67; line-height:1.6 }
.alt { margin-top:18px; padding-top:16px; border-top:1px solid #ececea; font-size:14px; color:#55554f; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px } .alt a { color:#141414; border-bottom:1px solid #141414 }
.gain { margin-top:22px; border-top:1px solid #ececea; padding-top:16px } .gain .k { display:block; margin-bottom:8px }
.gain ul { margin:0; padding:0; list-style:none } .gain li { font-size:14px; line-height:1.6; padding:5px 0; border-bottom:1px solid #f1f0ec; display:grid; grid-template-columns:96px 1fr; gap:12px } .gain li b { font-weight:600 }
/* 보냄 — 주황은 이메일 밑줄에만 */
.sent b.em { border-bottom:2px solid #f97316; font-weight:600 } .sent h2 { margin:0 0 8px; font-size:20px; font-weight:650; letter-spacing:-0.02em } .sent p { margin:0; font-size:14.5px; line-height:1.65; color:#333 }
.sent .steps { margin:18px 0 0; padding:0; list-style:none } .sent .steps li { display:grid; grid-template-columns:72px 1fr; gap:12px; padding:8px 0; border-top:1px solid #ececea; font-size:14px; line-height:1.6 } .sent .steps li .k { padding-top:3px }
.sent .acts { display:flex; gap:16px; align-items:center; margin-top:18px; font-size:13.5px; flex-wrap:wrap } .sent .acts a { color:#141414; border-bottom:1px solid #d8d6d0 } .sent .acts .wait { color:#737370; border:0 }
/* 메일 본문 — 받은편지함 프레임 안. 버튼은 먹(주황 면 금지) */
.mail { max-width:640px; margin:48px auto 0 } .mail .hdr { font-size:13px; color:#55554f; border:1px solid #e6e4df; border-bottom:0; border-radius:14px 14px 0 0; background:#fff; padding:14px 22px; display:grid; grid-template-columns:56px 1fr; gap:4px 10px }
.mail .hdr b { color:#141414; font-weight:600 } .mail .body { border:1px solid #e6e4df; border-radius:0 0 14px 14px; background:#fff; padding:30px 34px 30px }
.mail .brand { font-weight:800; font-size:15px; letter-spacing:-0.035em; display:flex; align-items:center; gap:8px; margin-bottom:22px }
.mail h2 { margin:0 0 10px; font-size:20px; font-weight:650; letter-spacing:-0.02em } .mail p { margin:0 0 10px; font-size:14.5px; line-height:1.7; color:#333 }
.mail .btn { display:inline-flex; align-items:center; height:44px; padding:0 22px; border-radius:8px; background:#141414; color:#fff; font-weight:600; font-size:15px; margin:10px 0 18px }
.mail .raw { font-size:12.5px; color:#6b6b67; word-break:break-all; line-height:1.6 } .mail .raw code { font-family:ui-monospace,Consolas,monospace; font-size:12px }
.mail .ft { margin-top:22px; padding-top:14px; border-top:1px solid #ececea; font-size:12px; color:#737370; line-height:1.6 }
/* 로그인됨 — 결과 페이지 조각 + ☆ 회사 저장 */
.piece .head { padding-top:26px } .piece .res .cols { grid-template-columns:1fr } .piece .mh { margin-top:0 }
.piece .okline { display:block; border-bottom:1px solid #ececea } .piece .okline .em { font-weight:600 } .piece .okline .x2 { color:#55554f; margin-left:10px }
.piece .tail { padding:14px 0 0; font-size:13px; color:#6b6b67 }
.star { display:inline-flex; align-items:center; gap:6px; height:30px; padding:0 12px; border:1px solid #e3e1dc; border-radius:8px; font-size:13px; font-weight:600; color:#141414; margin-left:14px; vertical-align:middle; cursor:pointer; background:#fff; font-family:inherit; letter-spacing:0; transition:border-color .15s }
.star::before { content:"☆"; font-size:14px; color:#737370 } .star:hover { border-color:#f97316 } .star.on { border-color:#f97316 } .star.on::before { content:"★"; color:#f97316 }
.savedn { display:none; padding:9px 0 10px; border-bottom:1px solid #ececea; font-size:12.5px; color:#6b6b67 } .savedn a { color:#141414; border-bottom:1px solid #141414 } .savedn.on { display:block }
/* 재설정·오류 — 주황 괘선 안내 */
.notice { font-size:13.5px; color:#55554f; margin:0 0 18px; line-height:1.6; border-left:2px solid #f97316; padding-left:10px } .notice b { color:#141414 }   /* .why 는 표의 근거 칩 클래스라 못 쓴다 */
/* 게이트 — 로그인 / 회원가입 두 버튼 */
.gateline .in .bt { height:36px } .gateline .in .bt + .bt { margin-left:6px }
/* 장면 알약 */
.cases { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; align-items:center; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap; z-index:9 }
.cases span { padding:6px 12px; border-radius:999px; color:#55554f; cursor:pointer } .cases span.on { background:#141414; color:#fff } .cases i { width:1px; height:18px; background:#e6e4df; margin:0 4px }
.vw { display:none } .vw.on { display:block }
@media screen and (max-width:720px){
  .narrow { margin-top:20px } .pane { padding:20px 16px 22px; border-radius:12px } .narrow h1 { font-size:22px } .gain li { grid-template-columns:1fr; gap:2px }
  .mail { margin-top:20px } .mail .body { padding:22px 18px } .mail .hdr { grid-template-columns:1fr; gap:0 }
  .sent .steps li { grid-template-columns:1fr; gap:0 } .star { margin:8px 0 0 } .gateline .in { flex-wrap:wrap }
  .cases { font-size:11.5px; padding:2px; white-space:normal; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px } .cases span { padding:5px 8px } .cases i { display:none }
  .nav .me .menu { right:-8px }
  .nav .links span.me { display:inline-block }   /* SHEET_CSS 가 390 에서 span 링크를 숨긴다 — 로그인된 이메일은 보여야 한다 */
}
"""

JS = r"""
document.querySelectorAll('.sheet .tr').forEach(t => t.addEventListener('click', () => t.nextElementSibling.classList.toggle('on')));
document.querySelectorAll('form.f').forEach(f => { const em = f.querySelector('input[type=email]:not([disabled])'), pws = [...f.querySelectorAll('.pw input')], musts = [...f.querySelectorAll('input.must')], bt = f.querySelector('.bt.dark'), hint = f.querySelector('.hint[data-min]');
  const ok = () => (!em || (em.validity.valid && em.value)) && pws.every(p => p.value.length >= (+p.dataset.min || 1)) && musts.every(m => m.checked) && (pws.length < 2 || pws[0].value === pws[1].value);
  const upd = () => { bt.disabled = !ok(); if (hint) { const p = pws[0]; hint.classList.toggle('bad', p.value.length > 0 && p.value.length < +p.dataset.min); } };
  upd(); f.addEventListener('input', upd); f.addEventListener('change', upd);
  f.addEventListener('submit', e => { e.preventDefault(); if (bt.disabled) return; const n = f.dataset.next; if (n) show(n); }); });
document.querySelectorAll('.pw .eye').forEach(b => b.addEventListener('click', e => { e.preventDefault(); const i = b.parentElement.querySelector('input'); i.type = i.type === 'password' ? 'text' : 'password'; b.textContent = i.type === 'password' ? '표시' : '숨김'; }));
const cs = document.querySelector('.cases');
function show(k){ document.querySelectorAll('.vw').forEach(v => v.classList.toggle('on', v.dataset.c === k)); cs.querySelectorAll('[data-c]').forEach(x => x.classList.toggle('on', x.dataset.c === k)); location.hash = k; scrollTo(0, 0); }
cs.querySelectorAll('[data-c]').forEach(s => s.onclick = () => show(s.dataset.c));
document.querySelectorAll('.nav .me').forEach(m => m.addEventListener('click', e => { e.stopPropagation(); m.classList.toggle('open'); }));
addEventListener('click', () => document.querySelectorAll('.nav .me.open').forEach(m => m.classList.remove('open')));
document.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); show(a.dataset.go); }));
document.querySelectorAll('.star').forEach(b => b.addEventListener('click', e => { e.preventDefault(); const on = b.classList.toggle('on'); b.lastChild.textContent = on ? '저장됨' : '회사 저장'; const n = b.closest('.vw').querySelector('.savedn'); if (n) n.classList.toggle('on', on); }));
if (location.hash.length > 1 && cs.querySelector(`[data-c="${location.hash.slice(1)}"]`)) show(location.hash.slice(1));
"""


def nav(state="guest", here=None):
    """nav — 비로그인 '로그인' / 로그인됨 you@ + 메뉴(저장한 회사 ★ 목록 · 검토함 · 설정 · 로그아웃). 모든 페이지의 '이메일 구독' CTA 가 이걸로 바뀐다."""
    links = [("추천", "reco"), ("검토함", "saved"), ("개선 기록", "log")]
    ls = "".join(f'<b>{t}</b>' if k == here else f'<span>{t}</span>' for t, k in links)
    if state == "guest":
        tail = '<a class="cta" href="#" data-go="1">로그인</a>'
    else:
        cos = "".join(f'<a class="co" href="#">{esc(c)}</a>' for c in SAVED)
        tail = (f'<span class="me">{EMAIL.split("@")[0]}@…<div class="menu"><a href="#">{EMAIL}<small>로그인됨</small></a><div class="sep"></div>'
                f'<span class="k">저장한 회사 {len(SAVED)}</span>{cos}<div class="sep"></div>'
                f'<a href="#">검토함<small>검토한 공고 3건</small></a><a href="#">설정<small>비밀번호 변경 · 알림 수신 · 탈퇴</small></a><div class="sep"></div><a class="dim" href="#" data-go="7">로그아웃</a></div></span>')
    return f'<div class="nav"><a class="brand" href="#">{TILE}조달핏</a><div class="links">{ls}{tail}</div></div>'


def pw_field(label="비밀번호", min_=8, hint=True, forgot=False, placeholder="8자 이상"):
    top = f'<div class="row2"><span class="k">{label}</span><a href="#" data-go="6">비밀번호 찾기</a></div>' if forgot else f'<span class="k">{label}</span>'
    return (f'<div class="fld pw"><label>{top}<input type="password" placeholder="{placeholder}" autocomplete="{"current-password" if forgot else "new-password"}" data-min="{min_}"></label><button class="eye" type="button">표시</button>'
            + (f'<div class="hint" data-min="{min_}">8자 이상</div>' if hint else '') + '</div>')


def consent():
    return ('<div class="cs"><label><input type="checkbox" class="must"><span><b>[필수]</b> <a href="#">이용약관</a> 동의</span></label>'
            '<label><input type="checkbox" class="must"><span><b>[필수]</b> 개인정보 수집·이용 동의 — 이메일 주소 · 로그인·검토함·저장한 회사 보관 · 탈퇴 시 삭제. <a href="#">처리방침</a></span></label>'
            '<label class="opt"><input type="checkbox"><span><span class="k">[선택]</span>알림 메일 수신 동의 — 준비 중, 시작 시 안내</span></label></div>')


def gain():
    return ('<div class="gain"><span class="k">로그인하면</span><ul><li><b>결과 전부</b><span>상위 5건 뒤의 나머지 공고</span></li>'
            '<li><b>검토함</b><span>검토 표시한 공고 보관</span></li><li><b>저장한 회사</b><span>여러 회사 저장, 바로 결과</span></li></ul></div>')


def frame(title, lead, inner):
    return f'{nav("guest")}<div class="narrow"><h1>{title}</h1>' + (f'<p class="lead">{lead}</p>' if lead else '') + f'<div class="pane">{inner}</div></div>'


def scene_login():
    inner = (f'<form class="f" data-next="5" novalidate><div class="fld"><label><span class="k">이메일</span><input type="email" placeholder="{EMAIL}" autocomplete="email" inputmode="email"></label></div>'
             f'{pw_field(min_=1, forgot=True, hint=False, placeholder="비밀번호")}<button class="bt dark" type="submit">로그인</button></form>'
             f'<div class="alt"><span></span><a href="#" data-go="2">회원가입</a></div>{gain()}')
    return frame("로그인", "", inner)


def scene_signup():
    inner = (f'<form class="f" data-next="3" novalidate><div class="fld"><label><span class="k">이메일</span><input type="email" placeholder="{EMAIL}" autocomplete="email" inputmode="email"></label>'
             f'<div class="hint">확인 메일 발송</div></div>{pw_field()}{consent()}<button class="bt dark" type="submit">가입</button></form>'
             f'<div class="alt"><span></span><a href="#" data-go="1">로그인</a></div>')
    return frame("회원가입", "", inner)


def scene_sent(kind):
    if kind == "signup":
        title, h, p_, back, mail = "회원가입", "확인 메일을 보냈습니다", "메일의 링크를 열면 가입이 완료됩니다.", "2", "4"
    else:
        title, h, p_, back, mail = "비밀번호 재설정", "재설정 링크를 보냈습니다", "메일의 링크를 열면 새 비밀번호를 정합니다.", "6", "6b"
    inner = (f'<div class="sent"><h2>{h}</h2><p>{p_}</p><ul class="steps"><li><span class="k">받는 곳</span><span><b class="em">{EMAIL}</b></span></li>'
             f'<li><span class="k">유효</span><span>{TTL}분 · 1회</span></li>'
             f'<li><span class="k">안 오면</span><span>스팸함 확인 · 보낸 주소 <b>noreply@jodalfit.co.kr</b></span></li></ul>'
             f'<div class="acts"><a class="wait">다시 보내기 — 47초 뒤</a><a href="#" data-go="{back}">다른 이메일</a><a href="#" data-go="{mail}">받은 메일 보기 →</a></div></div>')
    return frame(title, "", inner)


def scene_mail(kind):
    if kind == "confirm":
        subj, h, p_, btn, link, go, what = f"조달핏 이메일 확인 ({TTL}분 유효)", "이메일 확인", "아래 버튼을 누르면 가입이 완료됩니다.", "이메일 확인", "https://jodalfit.co.kr/auth/confirm?token_hash=7f3a…&type=signup&next=%2Frecommendations", "5", "가입"
    else:
        subj, h, p_, btn, link, go, what = f"조달핏 비밀번호 재설정 ({TTL}분 유효)", "비밀번호 재설정", "아래 버튼을 누르면 새 비밀번호를 정하는 화면이 열립니다.", "비밀번호 재설정", "https://jodalfit.co.kr/auth/confirm?token_hash=9c1d…&type=recovery&next=%2Fsettings%2Fpassword", "6c", "비밀번호 재설정"
    return (f'<div class="mail"><div class="hdr"><span>보낸 사람</span><span><b>조달핏</b> &lt;noreply@jodalfit.co.kr&gt;</span><span>받는 사람</span><span>{EMAIL}</span><span>제목</span><span><b>{subj}</b></span></div>'
            f'<div class="body"><div class="brand">{TILE}조달핏</div><h2>{h}</h2><p>{p_}</p><a class="btn" href="#" data-go="{go}">{btn}</a>'
            f'<p>유효 {TODAY.month}.{TODAY.day:02d} 15:02까지 · 1회. 버튼이 동작하지 않으면 아래 주소를 브라우저에 입력합니다.</p>'
            f'<div class="raw"><code>{link}</code></div>'
            f'<div class="ft">{EMAIL} 의 {what} 요청으로 발송된 메일입니다. 요청한 적이 없으면 무시하십시오.<br>조달핏 · jodalfit.co.kr · 개인정보처리방침</div></div></div>')


def scene_in(d, prof_stub):
    """가입 완료 = 로그인됨. 결과 페이지 조각: nav 이메일, 안내 한 줄(처음 한 번), 머리에 ☆ 회사 저장 — 누르면 nav 메뉴의 저장한 회사로."""
    res = d["results"]; co = d["company"]
    trs = [trow(i, r, prof_stub, False) for i, r in enumerate(res[:3], 1)]
    return (f'{nav("in", "reco")}<div class="piece"><div class="head"><h1>{esc(co["corp_nm"])}<small>124-XX-X731</small><button class="star" type="button">회사 저장</button><a class="sw-co" href="#">다른 회사</a></h1>'
            f'<div class="meta"><span>경상남도 창원시</span><span>등록업종 15</span><span>공급물품 없음</span><span>기준일 {TODAY.isoformat()}</span></div></div>'
            f'<div class="res"><div class="cols"><div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span></div>'
            f'<div class="okline"><span class="em">{EMAIL}</span> 가입 완료<span class="x2">전체 {len(res)}건 공개</span></div>'
            f'<div class="savedn">저장됨 — <a href="#">검토함 › 저장한 회사</a></div>'
            f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>{"".join(trs)}</div>'
            f'<div class="tail">… 이하 {len(res) - 3}건 — 흐림·게이트 없음. 안내 줄은 가입 직후 한 번만. ☆ 는 회사 페이지·결과 페이지 머리의 같은 자리.</div></div></div></div></div>')


def scene_reset():
    inner = (f'<form class="f" data-next="6a" novalidate><p class="notice">가입한 이메일로 재설정 링크를 보냅니다.</p>'
             f'<div class="fld"><label><span class="k">이메일</span><input type="email" value="{EMAIL}" autocomplete="email"></label></div><button class="bt dark" type="submit">재설정 링크 받기</button></form>'
             f'<div class="alt"><span></span><a href="#" data-go="1">로그인</a></div>')
    return frame("비밀번호 재설정", "", inner)


def scene_newpw():
    inner = (f'<form class="f" data-next="5" novalidate><div class="fld"><label><span class="k">계정</span><input type="email" value="{EMAIL}" disabled></label></div>'
             f'{pw_field("새 비밀번호")}{pw_field("새 비밀번호 확인", hint=False, placeholder="한 번 더")}<button class="bt dark" type="submit">변경</button>'
             f'<div class="note">변경 시 다른 기기 로그인 해제.</div></form>')
    return frame("새 비밀번호", "", inner)


def scene_out():
    inner = ('<div class="sent"><p>검토함·저장한 회사는 계정에 보관됩니다.</p>'
             '<div class="acts"><a href="#" data-go="1">로그인</a><a href="#">추천</a></div></div>')
    return frame("로그아웃되었습니다", "", inner)


def gate_auth(n):
    return (f'<div class="gateline"><div><b>나머지 {n - 5}건은 로그인 후 공개</b><span class="dim" style="display:block;margin-top:4px">상위 5건은 로그인 없이 공개</span></div>'
            f'<span class="sp"></span><span class="in"><a class="bt" href="#" data-go="1">로그인</a><a class="bt dark" href="#" data-go="2">회원가입</a></span></div>')


def page(d):
    prof_stub = dict(industries=([], []), products=([], []), rgn=None, names=set(), terms=set(), codes=set())
    res = d["results"]
    trs = [trow(i, r, prof_stub, False) for i, r in enumerate(res[:5], 1)]
    gate_piece = (f'{nav("guest", "reco")}<div class="piece"><div class="res"><div class="cols"><div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span></div>'
                  f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>{"".join(trs)}{gate_auth(len(res))}'
                  f'<div class="fade">{trow(6, res[5], prof_stub)}{trow(7, res[6], prof_stub)}</div></div>'
                  f'<div class="tail">결과·회사 페이지 표 안 게이트. 옛 "이메일 등록" 한 칸은 폐기 — 로그인 / 회원가입 두 버튼, 둘 다 끝나면 이 페이지로 돌아온다(next). 가입은 확인 메일을 거치므로 메일의 링크가 이 페이지를 연다.</div></div></div></div></div>')
    scenes = [("1", "1 로그인", scene_login()), ("2", "2 회원가입", scene_signup()), ("3", "3 확인 메일 보냄", scene_sent("signup")), ("4", "4 메일", scene_mail("confirm")),
              ("5", "5 가입 완료", scene_in(d, prof_stub)), ("6", "6 재설정", scene_reset()), ("6a", "6a 보냄", scene_sent("reset")), ("6b", "6b 메일", scene_mail("reset")), ("6c", "6c 새 비밀번호", scene_newpw()),
              ("g", "게이트", gate_piece), ("7", "7 로그아웃", scene_out())]
    vws = "".join(f'<div class="vw {"on" if k == "1" else ""}" data-c="{k}">{h}</div>' for k, _, h in scenes)
    pills = "".join(f'<span data-c="{k}" class="{"on" if k == "1" else ""}">{l}</span>' for k, l, _ in scenes)
    foot = (f'<div class="foot">로그인·회원가입 흐름 최종 시안 — 이메일 + 비밀번호, 가입은 확인 메일 1회, 재설정은 메일 링크. 회사 연결 대신 <b>저장한 회사(☆, 여러 곳)</b>. '
            f'nav 는 모든 페이지에서 "이메일 구독" → <b>로그인</b> / 로그인됨 you@…(메뉴: 저장한 회사·검토함·설정·로그아웃). 동의는 이용약관(필수)·개인정보(필수)·알림 수신(선택). 이름·연락처·사업자번호는 받지 않는다. 공고는 {TODAY.isoformat()} 실제 추천 결과(data/sample.json).</div>')
    body = f'<div class="wrap">{vws}{foot}</div><div class="cases">{pills}</div>'
    return (f'<!doctype html><html lang="ko" class="v-panel"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 로그인</title>{FONT}'
            f'<style>{CSS}</style></head><body class="done">{body}<script>{JS}</script></body></html>')


BANNED = ["이메일 구독", "매직링크", "맞아요", "예요", "에요", "해드려요", "하세요", "아침 7시", "낼 수 있", "회사 연결"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in p.read_text(encoding="utf-8")
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(600)
        txt = pg.evaluate("[...document.querySelectorAll('.vw')].map(v => v.innerText).join('\\n')")
        bad = [w for w in BANNED if w in txt]; assert not bad, bad
        dis = lambda: pg.evaluate("document.querySelector('.vw.on .bt.dark').disabled")
        # 1 로그인 — 이메일·비밀번호 둘 다 있어야 켜짐
        s = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { cta: v.querySelector('.nav .cta').textContent, dis: v.querySelector('.bt.dark').disabled,
            pw: v.querySelectorAll('input[type=password]').length, forgot: !!v.querySelector('[data-go="6"]'), signup: !!v.querySelector('[data-go="2"]'), bg: cs(document.body).backgroundColor } }""")
        assert s["cta"] == "로그인" and s["dis"] and s["pw"] == 1 and s["forgot"] and s["signup"] and s["bg"] == "rgb(250, 249, 247)", s
        pg.screenshot(path=str(out / "_shot_login_1.png"), full_page=True)
        pg.fill('.vw.on input[type=email]', EMAIL); assert dis(); pg.fill('.vw.on input[type=password]', "x"); assert not dis()
        pg.click('.vw.on .pw .eye'); assert pg.evaluate("document.querySelector('.vw.on .pw input').type") == "text"
        # 2 회원가입 — 이메일 + 8자 비밀번호 + 약관·개인정보 둘 다 체크해야 켜짐 → 3
        pg.click('.cases [data-c="2"]'); pg.wait_for_timeout(150)
        pg.fill('.vw.on input[type=email]', EMAIL); pg.fill('.vw.on input[type=password]', "short"); assert dis()
        assert pg.evaluate("document.querySelector('.vw.on .hint[data-min]').classList.contains('bad')")
        pg.fill('.vw.on input[type=password]', "longenough1"); assert dis()   # 동의 전
        musts = pg.locator('.vw.on input.must'); assert musts.count() == 2; musts.nth(0).check(); assert dis(); musts.nth(1).check(); assert not dis()
        pg.screenshot(path=str(out / "_shot_login_2.png"), full_page=True)
        pg.click('.vw.on .bt.dark'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "3"
        assert pg.evaluate("getComputedStyle(document.querySelector('.vw.on .sent b.em')).borderBottomColor") == "rgb(249, 115, 22)"
        pg.screenshot(path=str(out / "_shot_login_3.png"), full_page=True)
        pg.click('.vw.on [data-go="4"]'); pg.wait_for_timeout(200)
        m = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { btn: cs(v.querySelector('.mail .btn')).backgroundColor, raw: v.querySelector('.mail .raw code').textContent.includes('type=signup'), subj: v.querySelector('.hdr').innerText.includes('이메일 확인') } }""")
        assert m["btn"] == "rgb(20, 20, 20)" and m["raw"] and m["subj"], m
        pg.screenshot(path=str(out / "_shot_login_4.png"), full_page=True)
        pg.click('.vw.on .mail .btn'); pg.wait_for_timeout(300)   # 이메일 확인 → 5
        i = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { c: v.dataset.c, me: v.querySelector('.nav .me') && v.querySelector('.nav .me').textContent.includes('you@'),
            cta: v.querySelectorAll('.nav .cta').length, ok: cs(v.querySelector('.okline')).display, gate: v.querySelectorAll('.gateline').length, fade: v.querySelectorAll('.fade').length, star: v.querySelector('.star').textContent, saved: cs(v.querySelector('.savedn')).display } }""")
        assert i["c"] == "5" and i["me"] and i["cta"] == 0 and i["ok"] == "block" and i["gate"] == 0 and i["fade"] == 0 and i["star"] == "회사 저장" and i["saved"] == "none", i
        pg.click('.vw.on .star'); pg.wait_for_timeout(400)   # 테두리 전환 .15s 가 끝난 뒤 읽는다
        st = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { t: v.querySelector('.star').textContent, bd: cs(v.querySelector('.star')).borderColor, n: cs(v.querySelector('.savedn')).display } }""")
        assert st["t"] == "저장됨" and st["bd"] == "rgb(249, 115, 22)" and st["n"] == "block", st
        pg.click('.vw.on .nav .me'); pg.wait_for_timeout(150)
        mn = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { open: getComputedStyle(v.querySelector('.nav .me .menu')).display, cos: v.querySelectorAll('.menu a.co').length } }""")
        assert mn["open"] == "block" and mn["cos"] == 2, mn
        pg.screenshot(path=str(out / "_shot_login_5.png"), full_page=True)
        pg.click('.vw.on .menu [data-go="7"]'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "7"
        pg.screenshot(path=str(out / "_shot_login_7.png"), full_page=False)
        # 6 재설정 — 이메일 채워짐 → 6a → 6b 메일(type=recovery) → 6c 새 비밀번호(둘이 같아야 켜짐)
        pg.click('.cases [data-c="6"]'); pg.wait_for_timeout(150); assert pg.evaluate("document.querySelector('.vw.on input[type=email]').value") == EMAIL and not dis()
        pg.screenshot(path=str(out / "_shot_login_6.png"), full_page=False)
        pg.click('.vw.on .bt.dark'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "6a"
        pg.click('.vw.on [data-go="6b"]'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on .mail .raw code').textContent.includes('type=recovery')")
        pg.click('.vw.on .mail .btn'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "6c"
        pws = pg.locator('.vw.on input[type=password]'); pws.nth(0).fill("newpassword1"); pws.nth(1).fill("newpassword2"); assert dis(); pws.nth(1).fill("newpassword1"); assert not dis()
        pg.screenshot(path=str(out / "_shot_login_6c.png"), full_page=False)
        pg.click('.cases [data-c="g"]'); pg.wait_for_timeout(200)
        g = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { btns: v.querySelectorAll('.gateline .in .bt').length, tr: v.querySelectorAll('.sheet > .tr').length, fade: v.querySelectorAll('.fade .tr').length, email_in: v.querySelectorAll('.gateline input').length } }""")
        assert g["btns"] == 2 and g["tr"] == 5 and g["fade"] == 2 and g["email_in"] == 0, g
        pg.screenshot(path=str(out / "_shot_login_gate.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri() + "#2"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390")
        pg.screenshot(path=str(out / "_shot_login_390.png"), full_page=True)
        b.close()
    print("ok 1 login(pw+forgot+signup) · 2 signup(8자·약관·개인정보 게이트) → 3 → 4 mail(signup) → 5 logged-in + ☆ saved + menu 2 companies · 6→6a→6b(recovery)→6c match · gate 2 buttons · 7 logout · 390 ok · banned 0")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(d))
    print("written", sys.argv[2])

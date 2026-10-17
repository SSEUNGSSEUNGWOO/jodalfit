"""로그인 흐름 최종 시안(`prototypes/login-final.html`) — 이메일 매직링크, 비밀번호 없음. 결정(2026-10-17 승우님): nav 라벨은 '로그인', 흐름 전체.

로그인 = 이메일 하나. 매직링크(Supabase Auth)만 발송하고 아침 메일은 보류(roadmap Phase 4) — 그래서 동의는 **개인정보 수집·이용(필수)** 하나만 받고,
광고성 수신 동의는 **선택**(알림 메일 시작 시 안내)으로 분리한다. 로그인하면 결과 전부 · 검토함 보관 · 회사 기억.

장면(알약): 1 /login 페이지 → 2 링크 보냄 → 3 메일 본문 → 4 링크 열림 = 로그인됨(nav·게이트·검토 버튼이 바뀐 결과 페이지 조각) → 5 만료·사용된 링크 → 6 nav 메뉴·로그아웃.
   + 2b 표 안 게이트에서 바로 보낸 상태(결과·회사 페이지의 '이메일 등록'이 같은 링크를 보낸다).

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_login.py ../docs/design/data/sample.json ../docs/design/prototypes/login-final.html
검증: gen_login.py --check ../docs/design/prototypes/login-final.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_flow import ORANGE, TILE  # noqa: E402
from gen_split import SPLIT_CSS, trow  # noqa: E402
from gen_results_final import CSS as FINAL_CSS  # noqa: E402

EMAIL = "you@company.co.kr"
TTL = 15   # 링크 유효 분 — Supabase Auth 기본 1시간을 줄인다(메일함에 오래 남는 로그인 링크는 위험)

CSS = FINAL_CSS + r"""
html, body { background:#faf9f7 }
.wrap { padding-bottom:140px }
/* nav — 로그인 상태 둘. 비로그인 '로그인' / 로그인됨 이메일 앞부분 + 검토함 */
.nav .cta { border-bottom:1px solid #141414; color:#141414 } .nav .me { position:relative; color:#141414; font-weight:600; cursor:pointer; border-bottom:1px solid #141414 }
.nav .me .menu { display:none; position:absolute; right:0; top:28px; background:#fff; border:1px solid #e6e4df; border-radius:10px; padding:6px; min-width:200px; font-weight:450; z-index:5; box-shadow:0 8px 24px rgba(20,20,20,.06) }
.nav .me.open .menu { display:block } .menu a { display:block; padding:9px 12px; border-radius:6px; color:#141414; font-size:13.5px } .menu a:hover { background:#f6f5f2 } .menu a.dim { color:#737370 } .menu .sep { height:1px; background:#ececea; margin:6px 4px }
.menu a small { display:block; color:#737370; font-size:12px; margin-top:1px }
/* 좁은 판 — 입구와 같은 폭 */
.narrow { max-width:520px; margin:48px auto 0 } .narrow h1 { margin:0 0 6px; font-size:28px; letter-spacing:-0.03em; font-weight:650 } .narrow .lead { font-size:14.5px; color:#55554f; line-height:1.65; margin:0 0 22px }
.pane { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:26px 28px 28px }
.f label { display:block } .f .k { display:block; margin-bottom:6px }
.f input[type=email] { width:100%; height:46px; border:1px solid #e3e1dc; border-radius:8px; padding:0 14px; font:inherit; font-size:16px; color:#141414; background:#fff; outline:none; transition:border-color .15s, box-shadow .15s }
.f input:focus { border-color:#f97316; box-shadow:0 0 0 4px rgba(249,115,22,.14) } .f input::placeholder { color:#9b9a95 }
.f .cs { margin:14px 0 18px; display:flex; flex-direction:column; gap:8px } .f .cs label { display:flex; gap:8px; align-items:flex-start; font-size:13px; line-height:1.55; color:#333; cursor:pointer }
.f .cs input { margin:3px 0 0; accent-color:#141414 } .f .cs a { border-bottom:1px solid #d8d6d0 } .f .cs .opt { color:#55554f } .f .cs .opt .k { display:inline; margin:0 6px 0 0; color:#737370 }
.f .bt.dark { width:100%; height:46px; justify-content:center; font-size:15px; cursor:pointer } .f .bt.dark[disabled] { background:#e3e1dc; border-color:#e3e1dc; color:#8f8f8b; cursor:default }
.f .note { margin-top:14px; font-size:12.5px; color:#6b6b67; line-height:1.6 }
.gain { margin-top:22px; border-top:1px solid #ececea; padding-top:16px } .gain .k { display:block; margin-bottom:8px }
.gain ul { margin:0; padding:0; list-style:none } .gain li { font-size:14px; line-height:1.6; padding:5px 0; border-bottom:1px solid #f1f0ec; display:grid; grid-template-columns:96px 1fr; gap:12px } .gain li b { font-weight:600 }
/* 보냄 — 상태 한 줄은 먹 괘선 아래, 주황은 이메일 밑줄에만 */
.sent b.em { border-bottom:2px solid #f97316; font-weight:600 } .sent h2 { margin:0 0 8px; font-size:20px; font-weight:650; letter-spacing:-0.02em } .sent p { margin:0; font-size:14.5px; line-height:1.65; color:#333 }
.sent .steps { margin:18px 0 0; padding:0; list-style:none } .sent .steps li { display:grid; grid-template-columns:72px 1fr; gap:12px; padding:8px 0; border-top:1px solid #ececea; font-size:14px; line-height:1.6 } .sent .steps li .k { padding-top:3px }
.sent .acts { display:flex; gap:16px; align-items:center; margin-top:18px; font-size:13.5px } .sent .acts a { color:#141414; border-bottom:1px solid #d8d6d0 } .sent .acts .wait { color:#737370; border:0 }
/* 메일 본문 — 받은편지함 프레임 안. 버튼은 먹(주황 면 금지) */
.mail { max-width:640px; margin:48px auto 0 } .mail .hdr { font-size:13px; color:#55554f; border:1px solid #e6e4df; border-bottom:0; border-radius:14px 14px 0 0; background:#fff; padding:14px 22px; display:grid; grid-template-columns:56px 1fr; gap:4px 10px }
.mail .hdr b { color:#141414; font-weight:600 } .mail .body { border:1px solid #e6e4df; border-radius:0 0 14px 14px; background:#fff; padding:30px 34px 30px }
.mail .brand { font-weight:800; font-size:15px; letter-spacing:-0.035em; display:flex; align-items:center; gap:8px; margin-bottom:22px }
.mail h2 { margin:0 0 10px; font-size:20px; font-weight:650; letter-spacing:-0.02em } .mail p { margin:0 0 10px; font-size:14.5px; line-height:1.7; color:#333 }
.mail .btn { display:inline-flex; align-items:center; height:44px; padding:0 22px; border-radius:8px; background:#141414; color:#fff; font-weight:600; font-size:15px; margin:10px 0 18px }
.mail .raw { font-size:12.5px; color:#6b6b67; word-break:break-all; line-height:1.6 } .mail .raw code { font-family:ui-monospace,Consolas,monospace; font-size:12px }
.mail .ft { margin-top:22px; padding-top:14px; border-top:1px solid #ececea; font-size:12px; color:#737370; line-height:1.6 }
/* 로그인됨 — 결과 페이지 조각: 머리 + 상단 3행, 게이트 자리에 안내 한 줄, 검토 버튼 */
.piece .head { padding-top:26px } .piece .res .cols { grid-template-columns:1fr } .piece .mh { margin-top:0 }
.piece .okline { display:block; border-bottom:1px solid #ececea } .piece .okline .em { font-weight:600 } .piece .okline .x2 { color:#55554f; margin-left:10px }
.piece .tail { padding:14px 0 0; font-size:13px; color:#6b6b67 }
/* 만료 — 같은 좁은 판, 제목만 다르고 이메일은 채워져 있다 */
.exp .why { font-size:13.5px; color:#55554f; margin:0 0 18px; line-height:1.6; border-left:2px solid #f97316; padding-left:10px }
/* 장면 알약 */
.cases { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; align-items:center; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px; white-space:nowrap; z-index:9 }
.cases span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .cases span.on { background:#141414; color:#fff } .cases i { width:1px; height:18px; background:#e6e4df; margin:0 4px }
.vw { display:none } .vw.on { display:block }
@media screen and (max-width:720px){
  .narrow { margin-top:20px } .pane { padding:20px 16px 22px; border-radius:12px } .narrow h1 { font-size:22px } .gain li { grid-template-columns:1fr; gap:2px }
  .mail { margin-top:20px } .mail .body { padding:22px 18px } .mail .hdr { grid-template-columns:1fr; gap:0 }
  .sent .steps li { grid-template-columns:1fr; gap:0 }
  .cases { font-size:11.5px; padding:2px; white-space:normal; flex-wrap:wrap; justify-content:center; width:calc(100% - 24px); border-radius:16px } .cases span { padding:5px 8px } .cases i { display:none }
  .nav .me .menu { right:-8px }
}
"""

JS = r"""
document.querySelectorAll('.sheet .tr').forEach(t => t.addEventListener('click', () => t.nextElementSibling.classList.toggle('on')));
document.querySelectorAll('form.f').forEach(f => { const em = f.querySelector('input[type=email]'), must = f.querySelector('input.must'), bt = f.querySelector('.bt.dark');
  const upd = () => { bt.disabled = !(em.validity.valid && em.value && (!must || must.checked)); }; upd(); f.addEventListener('input', upd); f.addEventListener('change', upd);
  f.addEventListener('submit', e => { e.preventDefault(); if (bt.disabled) return; const n = f.dataset.next; if (n) show(n); }); });
const cs = document.querySelector('.cases');
function show(k){ document.querySelectorAll('.vw').forEach(v => v.classList.toggle('on', v.dataset.c === k)); cs.querySelectorAll('[data-c]').forEach(x => x.classList.toggle('on', x.dataset.c === k)); location.hash = k; }
cs.querySelectorAll('[data-c]').forEach(s => s.onclick = () => show(s.dataset.c));
document.querySelectorAll('.nav .me').forEach(m => m.addEventListener('click', e => { e.stopPropagation(); m.classList.toggle('open'); }));
addEventListener('click', () => document.querySelectorAll('.nav .me.open').forEach(m => m.classList.remove('open')));
document.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); show(a.dataset.go); }));
if (location.hash.length > 1 && cs.querySelector(`[data-c="${location.hash.slice(1)}"]`)) show(location.hash.slice(1));
"""


def nav(state="guest", here=None):
    """nav — 비로그인 '로그인' / 로그인됨 you@ + 메뉴(검토함·알림 설정·로그아웃). 모든 페이지의 '이메일 구독' CTA 가 이걸로 바뀐다."""
    links = [("추천", "reco"), ("검토함", "saved"), ("개선 기록", "log")]
    ls = "".join(f'<b>{t}</b>' if k == here else f'<span>{t}</span>' for t, k in links)
    if state == "guest":
        tail = '<a class="cta" href="#" data-go="1">로그인</a>'
    else:
        tail = (f'<span class="me">{EMAIL.split("@")[0]}@…<div class="menu"><a href="#">{EMAIL}<small>로그인됨 · 회사 한종산업개발 기억</small></a><div class="sep"></div>'
                f'<a href="#">검토함<small>검토한 공고 3건</small></a><a href="#">알림 설정<small>알림 메일 준비 중 — 수신 동의만 받는 중</small></a><div class="sep"></div><a class="dim" href="#" data-go="6">로그아웃</a></div></span>')
    return f'<div class="nav"><a class="brand" href="#">{TILE}조달핏</a><div class="links">{ls}{tail}</div></div>'


def consent(opt=True):
    return ('<div class="cs"><label><input type="checkbox" class="must"><span><b>[필수]</b> 개인정보 수집·이용 동의 — 이메일 주소를 로그인과 검토함 보관에만 사용하고, 탈퇴 시 삭제합니다. <a href="#">처리방침</a></span></label>'
            + ('<label class="opt"><input type="checkbox"><span><span class="k">[선택]</span>알림 메일 수신 동의 — 새로 남은 공고 알림은 준비 중이며, 시작할 때 다시 안내합니다. 언제든 거부 가능</span></label>' if opt else "") + '</div>')


def scene_login():
    return (f'{nav("guest")}<div class="narrow"><h1>로그인</h1><p class="lead">비밀번호가 없습니다. 이메일로 받은 링크를 열면 로그인됩니다.</p>'
            f'<div class="pane"><form class="f" data-next="2" novalidate><label><span class="k">이메일</span><input type="email" placeholder="{EMAIL}" autocomplete="email" inputmode="email"></label>'
            f'{consent()}<button class="bt dark" type="submit">로그인 링크 받기</button>'
            f'<div class="note">링크는 {TTL}분 동안 한 번만 유효합니다. 처음이면 이 이메일로 계정이 만들어집니다 — 별도 가입 절차 없음.</div></form>'
            f'<div class="gain"><span class="k">로그인하면</span><ul><li><b>결과 전부</b><span>상위 5건 뒤의 나머지 공고와 추천 근거</span></li>'
            f'<li><b>검토함</b><span>검토 표시한 공고 보관, 마감 순 정리</span></li><li><b>회사 기억</b><span>다음 방문에 회사 입력 없이 바로 결과</span></li></ul></div></div></div>')


def scene_sent(gate=False):
    steps = (f'<ul class="steps"><li><span class="k">받는 곳</span><span><b class="em">{EMAIL}</b></span></li><li><span class="k">유효</span><span>{TTL}분 · 한 번만. 지나면 이 페이지에서 다시 받습니다</span></li>'
             f'<li><span class="k">안 오면</span><span>스팸함과 프로모션함 확인. 보낸 주소 <b>login@jodalfit.co.kr</b></span></li></ul>'
             f'<div class="acts"><a class="wait">다시 보내기 — 47초 뒤</a><a href="#" data-go="1">다른 이메일로</a><a href="#" data-go="3">받은 메일 보기 →</a></div>')
    if not gate:
        return (f'{nav("guest")}<div class="narrow"><h1>로그인</h1><p class="lead">비밀번호가 없습니다. 이메일로 받은 링크를 열면 로그인됩니다.</p>'
                f'<div class="pane sent"><h2>로그인 링크를 보냈습니다</h2><p>메일의 <b>로그인</b> 버튼을 누르면 이 창으로 돌아옵니다. 다른 기기에서 열어도 됩니다.</p>{steps}</div></div>')
    # 2b — 표 안 게이트에서 보낸 상태: 게이트 자리가 그대로 보냄 상태가 된다(페이지 이동 없음)
    return ""


def gate_sent():
    return (f'<div class="gateline sent"><div><b>로그인 링크를 <b class="em">{EMAIL}</b>로 보냈습니다</b><span class="dim" style="display:block;margin-top:4px">메일의 링크를 열면 이 페이지의 나머지 7건이 열립니다 · {TTL}분 유효 · 한 번만</span></div>'
            f'<span class="sp"></span><span class="in"><a class="wait" style="font-size:13px;color:#737370">다시 보내기 — 47초 뒤</a></span></div>')


def scene_mail():
    link = "https://jodalfit.co.kr/auth/confirm?token_hash=pkce_7f3a…&type=magiclink&next=%2Frecommendations"
    return (f'<div class="mail"><div class="hdr"><span>보낸 사람</span><span><b>조달핏</b> &lt;login@jodalfit.co.kr&gt;</span><span>받는 사람</span><span>{EMAIL}</span><span>제목</span><span><b>조달핏 로그인 링크 ({TTL}분 유효)</b></span></div>'
            f'<div class="body"><div class="brand">{TILE}조달핏</div><h2>로그인 링크</h2><p>아래 버튼을 누르면 조달핏에 로그인됩니다. 요청한 기기가 아니어도 됩니다.</p>'
            f'<a class="btn" href="#" data-go="4">로그인</a>'
            f'<p>링크는 {TODAY.month}.{TODAY.day:02d} 14:17까지({TTL}분) 한 번만 유효합니다. 버튼이 동작하지 않으면 아래 주소를 브라우저에 붙여 넣습니다.</p>'
            f'<div class="raw"><code>{link}</code></div>'
            f'<div class="ft">이 메일은 {EMAIL} 로 로그인을 요청해 발송되었습니다. 요청한 적이 없으면 무시하십시오 — 링크를 열지 않는 한 아무 일도 일어나지 않습니다. 로그인 외 목적의 메일은 보내지 않습니다.<br>조달핏 · jodalfit.co.kr · 개인정보처리방침</div></div></div>')


def scene_in(d, prof_stub):
    """링크 열림 = 로그인됨. 결과 페이지 조각: nav 바뀜, 게이트 자리에 확인 한 줄(이번 한 번), 흐림 없음, 검토 버튼은 보관으로 이어진다."""
    res = d["results"]; co = d["company"]
    trs = [trow(i, r, prof_stub, i == 1) for i, r in enumerate(res[:3], 1)]
    return (f'{nav("in", "reco")}<div class="piece"><div class="head"><h1>{esc(co["corp_nm"])}<small>124-XX-X731</small><a class="sw-co" href="#">다른 회사</a></h1>'
            f'<div class="meta"><span>경상남도 창원시</span><span>등록업종 15</span><span>공급물품 없음</span><span>기준일 {TODAY.isoformat()}</span></div></div>'
            f'<div class="res"><div class="cols"><div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span></div>'
            f'<div class="okline"><span class="em">{EMAIL}</span>로 로그인되었습니다<span class="x2">전체 {len(res)}건 공개 · 검토한 공고는 검토함에 보관 · 이 회사를 기억합니다</span></div>'
            f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>{"".join(trs)}</div>'
            f'<div class="tail">… 이하 {len(res) - 3}건 — 흐림·게이트 없음. 이 안내 줄은 로그인 직후 한 번만 보이고 다음 방문부터는 표만.</div></div></div></div></div>')


def scene_expired():
    return (f'{nav("guest")}<div class="narrow exp"><h1>로그인</h1><p class="lead">비밀번호가 없습니다. 이메일로 받은 링크를 열면 로그인됩니다.</p>'
            f'<div class="pane"><p class="why"><b>링크가 만료되었거나 이미 사용되었습니다.</b> 링크는 {TTL}분 동안 한 번만 유효합니다. 같은 이메일로 새 링크를 받습니다.</p>'
            f'<form class="f" data-next="2" novalidate><label><span class="k">이메일</span><input type="email" value="{EMAIL}" autocomplete="email"></label>'
            f'{consent(opt=False).replace("<input type=\"checkbox\" class=\"must\">", "<input type=\"checkbox\" class=\"must\" checked>")}'
            f'<button class="bt dark" type="submit">새 링크 받기</button><div class="note">동의는 처음 로그인 때 받은 것이 유지됩니다 — 확인만 합니다.</div></form></div></div>')


def scene_out():
    return (f'{nav("guest")}<div class="narrow"><h1>로그아웃되었습니다</h1><p class="lead">검토함과 회사 기억은 계정에 남아 있습니다. 다시 로그인하면 그대로 보입니다.</p>'
            f'<div class="pane sent"><p>이 브라우저에는 회사 이름도 남기지 않았습니다. 공용 PC 라면 여기서 끝입니다.</p>'
            f'<div class="acts"><a href="#" data-go="1">다시 로그인</a><a href="#">추천으로</a></div></div></div>')


def page(d):
    prof_stub = dict(industries=([], []), products=([], []), rgn=None, names=set(), terms=set(), codes=set())
    # 2b: 게이트에서 보냄 — 결과 조각의 게이트 자리만
    res = d["results"]
    trs = [trow(i, r, prof_stub, False) for i, r in enumerate(res[:5], 1)]
    gate_piece = (f'{nav("guest", "reco")}<div class="piece"><div class="res"><div class="cols"><div class="main"><div class="mh"><span class="k"><b>검토할 공고 {len(res)}건</b>적합 순</span></div>'
                  f'<div class="sheet"><div class="th"><span>#</span><span>공고 · 발주기관 · 근거</span><span class="r">마감</span><span class="r">추정가</span></div>{"".join(trs)}{gate_sent()}'
                  f'<div class="fade">{trow(6, res[5], prof_stub)}{trow(7, res[6], prof_stub)}</div></div>'
                  f'<div class="tail">표 안 게이트의 "이메일 등록"도 같은 로그인 링크를 보낸다 — 페이지를 떠나지 않고 게이트 자리가 보냄 상태로 바뀐다. 처음이면 동의 체크 한 줄이 게이트 안에 같이 선다(여기선 생략). 메일의 링크를 열면 이 탭이 장면 4 로 바뀐다.</div></div></div></div></div>')
    scenes = [("1", "1 로그인", scene_login()), ("2", "2 링크 보냄", scene_sent()), ("2b", "2b 게이트에서", gate_piece), ("3", "3 메일", scene_mail()),
              ("4", "4 로그인됨", scene_in(d, prof_stub)), ("5", "5 만료", scene_expired()), ("6", "6 로그아웃", scene_out())]
    vws = "".join(f'<div class="vw {"on" if k == "1" else ""}" data-c="{k}">{h}</div>' for k, _, h in scenes)
    pills = "".join(f'<span data-c="{k}" class="{"on" if k == "1" else ""}">{l}</span>' for k, l, _ in scenes)
    foot = (f'<div class="foot">로그인 흐름 최종 시안 — 이메일 매직링크(Supabase Auth), 비밀번호 없음, 링크 {TTL}분·1회. nav 는 모든 페이지에서 "이메일 구독" → <b>로그인</b> / 로그인됨 you@…(메뉴: 검토함·알림 설정·로그아웃). '
            f'동의는 개인정보(필수) 하나, 알림 메일 수신은 선택 — 아침 메일은 보류(roadmap Phase 4)라 약속하지 않는다. 표 안 게이트의 "이메일 등록"은 같은 링크를 보낸다. 공고 3건은 {TODAY.isoformat()} 실제 추천 결과(data/sample.json).</div>')
    body = f'<div class="wrap">{vws}{foot}</div><div class="cases">{pills}</div>'
    return (f'<!doctype html><html lang="ko" class="v-panel"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조달핏 로그인</title>{FONT}'
            f'<style>{CSS}</style></head><body class="done">{body}<script>{JS}</script></body></html>')


BANNED = ["이메일 구독", "회원가입", "비밀번호를", "맞아요", "예요", "에요", "해드려요", "하세요", "아침 7시", "낼 수 있"]


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
        # 1 — 이메일 + 필수 동의 전엔 버튼 꺼짐, 둘 다 채우면 켜짐 → 제출하면 2
        s = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { cta: v.querySelector('.nav .cta').textContent, dis: v.querySelector('.bt.dark').disabled,
            opt: v.querySelectorAll('.cs label').length, bg: cs(document.body).backgroundColor, w: v.querySelector('.narrow').getBoundingClientRect().width } }""")
        assert s["cta"] == "로그인" and s["dis"] and s["opt"] == 2 and s["bg"] == "rgb(250, 249, 247)" and 500 <= s["w"] <= 520, s
        pg.screenshot(path=str(out / "_shot_login_1.png"), full_page=True)
        pg.fill('.vw.on input[type=email]', EMAIL); assert pg.evaluate("document.querySelector('.vw.on .bt.dark').disabled")   # 동의 전
        pg.check('.vw.on input.must'); assert not pg.evaluate("document.querySelector('.vw.on .bt.dark').disabled")
        pg.click('.vw.on .bt.dark'); pg.wait_for_timeout(200)
        assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "2"
        em = pg.evaluate("getComputedStyle(document.querySelector('.vw.on .sent b.em')).borderBottomColor"); assert em == "rgb(249, 115, 22)", em
        pg.screenshot(path=str(out / "_shot_login_2.png"), full_page=True)
        pg.click('.cases [data-c="2b"]'); pg.wait_for_timeout(200)
        g = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { gate: !!v.querySelector('.gateline.sent'), tr: v.querySelectorAll('.sheet > .tr').length, fade: v.querySelectorAll('.fade .tr').length } }""")
        assert g["gate"] and g["tr"] == 5 and g["fade"] == 2, g
        pg.screenshot(path=str(out / "_shot_login_2b.png"), full_page=True)
        pg.click('.cases [data-c="3"]'); pg.wait_for_timeout(200)
        m = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { btn: cs(v.querySelector('.mail .btn')).backgroundColor, raw: !!v.querySelector('.mail .raw code'), subj: v.querySelector('.hdr').innerText.includes('로그인 링크') } }""")
        assert m["btn"] == "rgb(20, 20, 20)" and m["raw"] and m["subj"], m
        pg.screenshot(path=str(out / "_shot_login_3.png"), full_page=True)
        pg.click('.vw.on .mail .btn'); pg.wait_for_timeout(300)   # 메일의 로그인 → 4
        i = pg.evaluate("""() => { const v = document.querySelector('.vw.on'), cs = e => getComputedStyle(e); return { c: v.dataset.c, me: v.querySelector('.nav .me') && v.querySelector('.nav .me').textContent.includes('you@'),
            cta: v.querySelectorAll('.nav .cta').length, ok: cs(v.querySelector('.okline')).display, gate: v.querySelectorAll('.gateline').length, fade: v.querySelectorAll('.fade').length, tr: v.querySelectorAll('.sheet .tr').length } }""")
        assert i["c"] == "4" and i["me"] and i["cta"] == 0 and i["ok"] == "block" and i["gate"] == 0 and i["fade"] == 0 and i["tr"] == 3, i
        pg.click('.vw.on .nav .me'); pg.wait_for_timeout(150)
        assert pg.evaluate("getComputedStyle(document.querySelector('.vw.on .nav .me .menu')).display") == "block"
        pg.screenshot(path=str(out / "_shot_login_4.png"), full_page=True)
        pg.click('.vw.on .menu [data-go="6"]'); pg.wait_for_timeout(200); assert pg.evaluate("document.querySelector('.vw.on').dataset.c") == "6"
        pg.screenshot(path=str(out / "_shot_login_6.png"), full_page=False)
        pg.click('.cases [data-c="5"]'); pg.wait_for_timeout(200)
        x = pg.evaluate("""() => { const v = document.querySelector('.vw.on'); return { val: v.querySelector('input[type=email]').value, dis: v.querySelector('.bt.dark').disabled, rule: getComputedStyle(v.querySelector('.why')).borderLeftColor } }""")
        assert x["val"] == EMAIL and not x["dis"] and x["rule"] == "rgb(249, 115, 22)", x
        pg.screenshot(path=str(out / "_shot_login_5.png"), full_page=False)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390")
        pg.screenshot(path=str(out / "_shot_login_390.png"), full_page=True)
        b.close()
    print("ok scenes 1→2 (consent gate), 2b gate-sent, 3 mail (black button, raw link), 4 logged-in (nav me, no gate/fade), 5 expired prefilled, 6 logout; 390 no overflow; banned 0")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(page(d))
    print("written", sys.argv[2])

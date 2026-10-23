"""공고 상세 최종 시안(`prototypes/final/notice-final.html`) — notice-rail(10-15 선택안)을 결과 페이지 최종 시안과 같은 문법으로.

같은 문법 = 주황 #f97316(선으로만) · 로고 lockup · 공문 톤 · 바닥 #faf9f7 위에 머리, 본문+레일은 흰 판 하나(14px) · 먹 괘선은 머리 아래 하나 ·
글자 단계 12 / 13.5 / 14 / 16 · 한글 라벨 자간·uppercase 없음 · 전환 곡선 (.3,.7,.2,1) · 참가 자격 충족(✓ 먹 600) > 제한 없음(회색 무표식) ·
지역은 기초자치단체까지, 판정은 운영 코드(app.recommender.qualifications.region_allows)와 같은 규칙.
본문 블록(과업·조건·단계·기관·정정)과 레일 구성은 gen_notice.l3 그대로 쓴다 — 판만 바꾼다.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_notice_final.py ../docs/design/prototypes/final/notice-final.html
검증: gen_notice_final.py --check ../docs/design/prototypes/final/notice-final.html → 금지어·인주 0, 판 배경, 레일 sticky, 캡처 4장(A 로그인·B 비로그인·C 로그인·390).
"""
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import gen_notice as GN  # noqa: E402
from gen_notice import CSS as N_CSS, L3_CSS, JS, LAYOUTS, NOTICES, COMPANY, esc, ro, TODAY  # noqa: E402
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_flow import ORANGE, nav  # noqa: E402
from gen_split import rgn_base  # noqa: E402
from app.recommender.qualifications import region_allows  # noqa: E402

FINAL_CSS = r"""
.brand { font-weight:800; font-size:16px; letter-spacing:-0.035em; gap:8px } .brand svg { display:block }
.k { font-size:12px; letter-spacing:0; text-transform:none; color:#6b6b67 }
/* 바닥과 판 — 머리는 바닥 위, 본문+레일은 흰 판 하나. 먹 괘선은 머리 아래 하나 */
html, body { background:#faf9f7 }
.head { border-bottom:1px solid #141414; padding-bottom:20px }
.cols { background:#fff; border:1px solid #e6e4df; border-radius:14px; padding:28px 32px 32px; margin-top:22px !important; gap:48px }
.rail { top:16px; border-top:0; padding-top:0 }
.sec { border-top-color:#e6e4df } .qual { border-top-color:#e6e4df } table.aw th { border-bottom-color:#e6e4df }
.sw { background:#fff; color:#55554f; border:1px solid #e6e4df; box-shadow:none } .sw .on { background:#141414; color:#fff } .sw .sep { background:#e6e4df }
/* 글자 — 결과 페이지와 같은 단계 */
h1.t { font-size:32px } .sec > h2 { font-size:19px } .sec > .lead { font-size:13.5px }
.qr .qv { font-size:14.5px } .qr .qb { font-size:13px } .qr .qk { font-size:13px }
.rail .rn { font-size:14px; padding:10px 0 } .rail .rqr { font-size:13.5px } .rail .rdoc { font-size:12.5px } .rail .rsub { font-size:13px }
ul.reqs li { font-size:14px } .meta { font-size:14px }
/* 참가 자격 — 충족(먹 600 + ✓) > 제한 없음(회색, 표식 없음) */
.qr.s-none .qk::before { content:"·"; color:#b8b6b0; position:absolute; left:0; font-weight:700 } .qr.s-none .qv, .qr.s-none .qb { color:#737370 }
.qr.s-ok .qv { font-weight:600 }
.rail .rqr.s-none { border-left-color:#e6e4df; color:#737370 } .rail .rqr.s-ok span:last-child { font-weight:600; color:#141414 }
.rail .rv.none { color:#55554f; font-weight:500 }
/* 주황은 선 — 마감 당김 알림의 면(#fdf3f0)을 걷고 괘선만 */
.rail .ramd { background:transparent; padding-left:12px }
/* 검토 버튼은 주황 헤어라인(결과 페이지와 같은 것) */
.bt.rv { border-color:#f97316 } .bt, .rmore, .lcm, .att a, .src a, .qf a { transition:border-color .15s ease, background .15s ease, color .15s ease }
.reveal { transition:opacity .5s ease var(--d,0s), transform .55s cubic-bezier(.3,.7,.2,1) var(--d,0s) }
@media screen and (max-width:980px) { .cols { padding:16px 16px 20px; border-radius:12px; gap:26px } h1.t { font-size:24px } }
"""


def qual(d, prof, login=True):
    """gen_notice.qual 과 같은 모양(상태, 항목, 내용, 근거, 레일 짧은 판정, 레일 짧은 원문) — 지역 판정만 운영 규칙(region_allows)으로,
    '제한 없음'은 s-ok 가 아니라 s-none(충족과 시그널 크기가 다르다 — 승우님 2026-10-16), 본사 표기는 기초자치단체까지."""
    n = d["n"]
    mine = prof["industries"][0] + prof["industries"][1]
    allowed = [a.strip() for a in (n["bidprc_psbl_indstryty_nm"] or "").split(",") if a.strip()]
    rows = []
    if not allowed:
        rows.append(("s-none", "허용 업종", "제한 없음", "공고 업종제한 N", "제한 없음", "제한 없음"))
    else:
        hit = [a for a in allowed if any(m.split("(")[0] in a or a.split("(")[0] in m for m in mine)]
        txt = ", ".join(esc(a) for a in allowed[:3]) + (f' <span class="mute">외 {len(allowed) - 3}</span>' if len(allowed) > 3 else "")
        rows.append(("s-ok" if hit else "s-warn", "허용 업종", txt,
                     f'등록업종 {len(mine)}개 중 {esc(hit[0])} 보유' if hit else f"등록업종 {len(mine)}개 중 일치 없음",
                     f'{esc(hit[0])} 보유' if hit else f"등록업종 {len(mine)}개에 없음", f"{len(allowed)}개 업종으로 제한"))
    rgn = (n["prtcpt_psbl_rgn_nm"] or "").strip()
    base = rgn_base(prof["rgn"])
    if not rgn:
        rows.append(("s-none", "지역 제한", "제한 없음", "공고 지역제한 N", "제한 없음", "제한 없음"))
    else:
        parts = [p.strip() for p in rgn.split(",") if p.strip()]
        ok = bool(prof["rgn"]) and any(region_allows(p, prof["rgn"]) for p in parts)
        rows.append(("s-ok" if ok else "s-warn", "지역 제한",
                     ", ".join(esc(p) for p in parts[:2]) + (f' <span class="mute">외 {len(parts) - 2}</span>' if len(parts) > 2 else ""),
                     f'본사 {esc(base)}', f'본사 {esc(base)} ' + ("포함" if ok else "제외"),
                     esc(parts[0]) + (f" 외 {len(parts) - 1}곳{ro('곳')} 제한" if len(parts) > 1 else f"{ro(parts[0])} 제한")))
    return rows


GN.qual = qual   # l3 / qual_block 은 모듈 전역을 호출 시점에 찾는다


def rail_head(rows):
    """레일 판정 한 줄 — 충족·제한 없음·불충족을 가른다(옛 코드는 제한 없음도 '충족'으로 셌다)."""
    bad = [r for r in rows if r[0] == "s-warn"]; ok = [r for r in rows if r[0] == "s-ok"]; none = [r for r in rows if r[0] == "s-none"]
    if bad:
        return (f"공고 제한 {len(rows)}건 모두 불충족" if len(bad) == len(rows) else f"공고 제한 {len(rows)}건 중 {len(bad)}건 불충족"), "no"
    if not ok:
        return "공고에 업종·지역 제한 없음", "none"
    return f"공고 제한 {len(ok)}건 충족" + (f" · {len(none)}건은 제한 없음" if none else ""), "yes"


def l3(d, prof, login):
    html = GN.l3(d, prof, login)
    if login:   # gen_notice.l3 의 머리 한 줄을 셋으로 가른 것으로 교체
        head, cls = rail_head(qual(d, prof, login))
        import re
        html = re.sub(r'<div class="rv[^"]*">[^<]*</div>', f'<div class="rv {cls}">{head}</div>', html, count=1)
    return html.replace('<a class="bt" href="#">검토</a>', '<a class="bt rv" href="#">검토</a>')


def page(data, prof):
    css = (SHEET_CSS + N_CSS + L3_CSS).replace("#e8431b", ORANGE) + FINAL_CSS
    vws = "".join(f'<div class="vw" data-n="{key}" data-s="{state}">{l3(data[key], prof, state == "login")}</div>'
                  for key in ("full", "thin", "amend") for state in ("guest", "login"))
    nbtn = "".join(f'<span data-n="{k}">{lab}</span>' for k, lab in (("full", "A 조건 많음·계약까지"), ("thin", "B 빈약"), ("amend", "C 정정 3차")))
    sw = (f'<div class="sw"><div class="g">{nbtn}</div><span class="sep"></span>'
          f'<div class="g"><span data-s="guest">비로그인</span><span data-s="login">회사 확인됨</span></div></div>')
    foot = (f'<div class="foot">공고 상세 최종 시안 — notice-rail 구성에 결과 페이지 문법(주황·로고·바닥+판·먹 괘선 하나·글자 단계·충족 &gt; 제한 없음·지역 기초자치단체). '
            f'공고 3건·기관 통계·개찰·계약은 {TODAY.isoformat()} 기준 실제 DB 행. 회사 확인됨 상태의 회사는 용산건설(주)(전남 보성군, 등록업종 11).</div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 공고 상세</title>{FONT}<style>{css}</style></head>'
            f'<body><div class="wrap2">{nav().replace("<b>추천</b>", "<span>추천</span>")}{vws}{foot}</div>{sw}<script>{JS}</script></body></html>')   # 상세는 추천 탭이 아니다


BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일로 전부 보기"]


def check(path):
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    assert "#e8431b" not in p.read_text(encoding="utf-8")   # 인주 0
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
        bad = [w for w in BANNED if w in pg.evaluate("document.body.innerText")]; assert not bad, bad
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e), v = document.querySelector('.vw.on'); return { bg: cs(document.body).backgroundColor,
            panel: cs(v.querySelector('.cols')).backgroundColor, r: cs(v.querySelector('.cols')).borderRadius, sticky: cs(v.querySelector('.rail')).position,
            rule: cs(v.querySelector('.head')).borderBottomColor, sec: cs(v.querySelector('.sec:not(:first-child)') || v.querySelector('.sec')).borderTopColor,
            brand: !!document.querySelector('.brand svg'), cta: document.querySelector('.nav .cta').textContent } }""")
        assert s["bg"] == "rgb(250, 249, 247)" and s["panel"] == "rgb(255, 255, 255)" and s["r"] == "14px" and s["sticky"] == "sticky", s
        assert s["rule"] == "rgb(20, 20, 20)" and s["brand"] and s["cta"] == "이메일 구독", s
        shots = []
        for n, st, name in [("full", "login", "a_login"), ("thin", "guest", "b_guest"), ("amend", "login", "c_login")]:
            pg.click(f'.sw [data-n="{n}"]'); pg.click(f'.sw [data-s="{st}"]'); pg.wait_for_timeout(300)
            pg.screenshot(path=str(out / f"_shot_nfinal_{name}.png"), full_page=True); shots.append(name)
        q = pg.evaluate("""() => ({ none: document.querySelectorAll('.vw[data-s="login"] .qr.s-none, .vw[data-s="login"] .rqr.s-none').length,
            ok: document.querySelectorAll('.vw[data-s="login"] .qr.s-ok').length, warn: document.querySelectorAll('.vw[data-s="login"] .qr.s-warn').length,
            rv: [...document.querySelectorAll('.vw[data-s="login"] .rv')].map(e => e.className + '|' + e.textContent) })""")
        assert q["none"] > 0 and q["warn"] > 0, q   # 세 공고 안에 제한 없음과 불충족이 둘 다 있어야 구분이 보인다
        pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(300)
        assert not pg.evaluate("document.documentElement.scrollWidth > 390")
        pg.screenshot(path=str(out / "_shot_nfinal_390.png"), full_page=True)
        b.close()
    print("ok panel/sticky/rule/brand; rv =", q["rv"], "; shots", shots + ["390"])


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    from jobs.evaluate_recommender import connect, fetch_company_profile
    conn = connect()
    prof = fetch_company_profile(conn, COMPANY.replace("-", ""))
    data = {key: GN.fetch(conn, no, od) for no, od, key, _ in NOTICES}
    open(sys.argv[1], "w", encoding="utf-8", newline="\n").write(page(data, prof))
    print("written", sys.argv[1])

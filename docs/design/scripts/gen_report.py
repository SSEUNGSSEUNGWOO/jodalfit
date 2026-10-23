"""추천 공고 보고서 — A4 세로 한 장(`prototypes/final/report.html`). 결과 페이지의 '인쇄 / PDF 저장' 뷰이자 이메일 게이트가 보내는 첨부,
나중엔 아침 메일 본문. 입찰 담당자가 상사에게 그대로 건네는 문서.

화면과 같은 말을 한다 — 근거·자격은 gen_flow.why_lines/qual_lines(공문 톤, flow.html 이 쓰는 것), 기준 띠는 gen_results_v6.crit 그대로.
주황 #f97316 은 마지막 12 · D-day ≤ 7 · 로고 타일뿐. 먹/회색 + 헤어라인. 버튼 없음(화면 모드의 '인쇄 / PDF 저장' 하나만, 인쇄에선 숨김).

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_report.py ../docs/design/data/sample.json ../docs/design/data/funnel.json ../docs/design/prototypes/final/report.html
검증: 같은 환경에서 gen_report.py --check ../docs/design/prototypes/final/report.html
      → 800px 화면 캡처 `_shot_report_800.png`, A4 PDF `_report.pdf`(1장이어야 통과), 인쇄 매체에서 주황 유지 확인.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results import TODAY, esc, won, dleft  # noqa: E402
from gen_results_v3 import FONT  # noqa: E402
from gen_results_v6 import crit  # noqa: E402
from gen_flow import TILE, why_lines, qual_lines  # noqa: E402

ORANGE = "#f97316"
# 네 칸은 앞 칸의 부분집합이어야 한다. "등록업종 허용 공고"는 파이프라인 단계가 아니었다 —
# 후보는 그 집합이 아니라 전체에서 유사도 순으로 뽑는다(2026-10-23: 최종 20건 중 8건이 업종 불일치).
# frontend Scene.tsx 의 FUNNEL_LABELS 와 같은 말이어야 한다.
LABELS = ["지금 입찰 가능한 공고", "비슷한 순서로 추린 공고", "참가 자격 통과 공고", "검토할 공고"]
REPORT_ROWS = 12  # A4 한 장 상한 — frontend report/page.tsx 의 limit 과 같아야 한다

CSS = r"""
* { box-sizing:border-box }
html { background:#faf9f7 }
body { margin:0; color:#141414; font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif; font-size:10px; line-height:1.3; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; -webkit-print-color-adjust:exact; print-color-adjust:exact }
a { color:inherit; text-decoration:none } .dim { color:#737370 } .mute { color:#8f8f8b } .acc { color:#f97316 }
.k { font-size:9.5px; color:#737370; font-weight:600; letter-spacing:.02em }
/* 화면 모드 — 종이 위에 A4 한 장 */
.nav { width:210mm; margin:0 auto; display:flex; justify-content:space-between; align-items:center; padding:18px 0 12px; font-size:13px; color:#55554f }
.nav .print { background:none; border:0; padding:0 0 2px; font:inherit; font-weight:600; color:#141414; border-bottom:2px solid #f97316; cursor:pointer }
.page { width:210mm; min-height:297mm; margin:0 auto 60px; background:#fff; border:1px solid #e6e4df; padding:16mm; display:flex; flex-direction:column }
/* 머리 */
.hd { display:flex; justify-content:space-between; align-items:flex-end; padding-bottom:8px; border-bottom:1px solid #141414 }
.brand { display:flex; align-items:center; gap:6px; font-weight:800; font-size:14px; letter-spacing:-0.035em } .brand svg { display:block }
.hd .r { text-align:right } .hd .r b { font-weight:650; font-size:11.5px } .hd .r .co { margin-top:2px; color:#55554f }
/* 띠 1 — 걸러낸 경로 */
.fun { display:flex; align-items:flex-start; gap:12px; padding:8px 0 7px; border-bottom:1px solid #e6e4df }
.fun .n { font-size:17px; font-weight:650; letter-spacing:-0.02em; line-height:1.2 } .fun .l { font-size:9.5px; color:#737370; margin-top:1px }
.fun i { font-style:normal; color:#b8b6b0; font-size:15px; line-height:1.35 }
/* 띠 2 — 판정 기준: gen_results_v6.crit 마크업을 한 줄씩으로 */
.sec { padding:4px 0 1px } .sec .k { display:block }
.crit { border-bottom:1px solid #e6e4df; padding-bottom:5px }
.crit > div { display:grid; grid-template-columns:150px 1fr; gap:0 10px; align-items:baseline }
.crit .k { padding-top:1px } .crit .txt { color:#333 } .crit .txt b { font-weight:600 }
.crit .act { display:block; margin-top:2px } .crit .act .bt { display:none } .crit .act .mute { font-size:9.5px }
/* 본문 — 12 행 */
.row { display:grid; grid-template-columns:20px 1fr; gap:0 6px; padding:3px 0 4px; border-top:1px solid #e6e4df; break-inside:avoid }
.row:first-of-type { border-top:0 }
.row .no { font-size:9.5px; color:#8f8f8b; padding-top:2px }
.row .t { display:flex; justify-content:space-between; align-items:baseline; gap:12px } .row .t b { font-weight:650; font-size:10.5px; letter-spacing:-0.01em }
.row .t span { white-space:nowrap; color:#55554f } .row .t span .d { font-weight:650; color:#141414 } .row .t span .d.hot { color:#f97316 }
.row .m { color:#55554f } .row .m .u { color:#8f8f8b }
.row .q, .row .w { display:grid; grid-template-columns:44px 1fr; gap:0 6px; color:#333 } .row .q b, .row .w b { font-weight:650 }
/* 꼬리 */
.ft { margin-top:auto; padding-top:6px; border-top:1px solid #141414; display:flex; justify-content:space-between; gap:20px; font-size:9.5px; color:#737370; line-height:1.45 } .ft b { color:#141414; font-weight:650 } .ft .pn { white-space:nowrap }
@page { size:A4; margin:16mm }
@media print {
  html, body { background:#fff }
  .nav { display:none }
  .page { width:auto; min-height:264mm; margin:0; border:0; padding:0 }
}
@media screen and (max-width:820px) {  /* screen 한정 — 인쇄 폭 178mm(673px)에 걸리면 안 된다 */ .nav, .page { width:auto; margin-left:10px; margin-right:10px } .page { padding:24px 16px; min-height:0 } .row .t { flex-direction:column; align-items:flex-start; gap:0 } }
"""


def qual_line(r, prof):
    """참가 자격 한 줄 — 화면의 판정 그대로. ✓ 는 먹, 어긋난 것은 '!'. 규모는 기준 띠가 '미입력'을 말하므로 라벨만."""
    out = []
    for c, t in qual_lines(r, prof):
        if c == "todo": out.append("규모 미입력")
        else: out.append(t.replace(" — ", " ") + {"ok": " ✓", "warn": " !"}.get(c, ""))   # 제한 없음(none)은 표식 없음 — 충족만 ✓
    return " · ".join(out)


def row(i, r, prof):
    org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or ""
    n, dd = dleft(r["bid_clse_date"])
    url = r["bid_ntce_url"].replace("https://www.", "")
    why = " · ".join(why_lines(r, org)[:2])
    return (f'<div class="row"><span class="no">{i:02d}</span><div>'
            f'<div class="t"><b>{esc(r["bid_ntce_nm"])}</b><span>마감 <span class="d {"hot" if n <= 7 else ""}">D-{n}</span> ({dd.month}.{dd.day:02d}) · 추정가 {won(r.get("presmpt_prce"))}</span></div>'
            f'<div class="m">{esc(org)} · <a class="u" href="{esc(r["bid_ntce_url"])}">{esc(url)}</a></div>'
            f'<div class="q"><b>참가 자격</b><span>{qual_line(r, prof)}</span></div>'
            f'<div class="w"><b>추천 근거</b><span>{why}</span></div></div></div>')


def page(d, prof, f):
    # 화면은 20건이지만 보고서는 12건 — A4 한 장이 상한이고(행 20개는 두 장) 상사에게 건네는 요약이라
    # 역할이 다르다. 운영도 같다(report/page.tsx 가 limit 12 로 따로 요청한다). 2026-10-23.
    res, co = d["results"][:REPORT_ROWS], d["company"]
    n_ind = len(prof["industries"][0] + prof["industries"][1])
    tile = TILE.replace('width="22" height="22"', 'width="20" height="20"')
    vals = [f'{f["total"]:,}', str(f["candidate"]), str(f["qualified"]), f'<span class="acc">{len(res)}</span>']
    fun = "".join((f'<div><div class="n">{v}</div><div class="l">{l}</div></div>' + ("<i>→</i>" if k < 3 else ""))
                  for k, (v, l) in enumerate(zip(vals, LABELS)))
    body = (f'<div class="nav"><a href="#">← 결과로 돌아가기</a><button class="print" type="button" onclick="window.print()">인쇄 / PDF 저장</button></div>'
            f'<div class="page">'
            f'<div class="hd"><div class="brand">{tile}조달핏</div><div class="r"><b>추천 공고 보고서 · 기준일 {TODAY.isoformat()}</b>'
            f'<div class="co">{esc(co["corp_nm"])} · {esc(co["rgn_nm"])} · 등록업종 {n_ind} · 공급물품 없음</div></div></div>'
            f'<div class="fun">{fun}</div>'
            f'<div class="sec"><span class="k">판정 기준</span></div>{crit(co, prof)}'
            f'<div class="sec"><span class="k">검토할 공고 {len(res)}건 · 적합 순</span></div>'
            f'{"".join(row(i, r, prof) for i, r in enumerate(res, 1))}'
            f'<div class="ft"><div><b>조달핏</b> · jodalfit.co.kr · 이 보고서는 낙찰 예측이 아니라 검토 대상 선별입니다 · '
            f'자격 판정은 나라장터 업체정보와 공고 제한 필드 기준이며 서류로 증빙되는 조건은 판정하지 않습니다</div><div class="pn">1 / 1</div></div>'
            f'</div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>조달핏 추천 공고 보고서 — {esc(co["corp_nm"])} · {TODAY.isoformat()}</title>{FONT}<style>{CSS}</style></head><body>{body}</body></html>')


def check(path):
    """Playwright: 제목·행 수, 800px 캡처, 인쇄 매체에서 nav 숨김·주황 유지, A4 PDF 가 1장인지."""
    from playwright.sync_api import sync_playwright
    p = Path(path).resolve(); out = p.parent
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 860, "height": 1200})
        pg.goto(p.as_uri()); pg.wait_for_load_state("networkidle")
        s = pg.evaluate("""() => ({ title: document.title, rows: document.querySelectorAll('.row').length, btn: getComputedStyle(document.querySelector('.nav .print')).display,
            pageH: document.querySelector('.page').getBoundingClientRect().height })""")
        assert s["title"].startswith("조달핏 추천 공고 보고서") and s["rows"] == REPORT_ROWS and s["btn"] != "none", s
        pg.screenshot(path=str(out / "_shot_report_800.png"), full_page=True)
        pg.emulate_media(media="print"); pg.set_viewport_size({"width": 673, "height": 1000})  # A4 내용 폭 178mm 에서 줄바꿈을 잰다
        pr = pg.evaluate("""() => { const cs = e => getComputedStyle(e); return { nav: cs(document.querySelector('.nav')).display, acc: cs(document.querySelector('.fun .acc')).color,
            hot: [...document.querySelectorAll('.hot')].map(e => cs(e).color), pca: cs(document.body).printColorAdjust || cs(document.body).webkitPrintColorAdjust,
            pageH: document.querySelector('.page').scrollHeight, wraps: [...document.querySelectorAll('.row .m, .row .q span, .row .w span, .crit .txt')].filter(e => e.getBoundingClientRect().height > 16).length } }""")
        assert pr["nav"] == "none" and pr["acc"] == "rgb(249, 115, 22)" and all(c == "rgb(249, 115, 22)" for c in pr["hot"]) and pr["pca"] == "exact", pr
        pdf = out / "_report.pdf"; pg.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    from pypdf import PdfReader
    rd = PdfReader(str(pdf)); pages = len(rd.pages)
    ink = b"".join(pg_.get_contents().get_data() for pg_ in rd.pages)
    orange = bool(re.search(rb"0?\.97\d* 0?\.45\d* 0?\.08\d* (rg|RG)", ink))  # Skia 는 .9765 .451 .0863 rg
    print(f"title={s['title']!r} rows={s['rows']} screen page height={s['pageH']:.0f}px print page height={pr['pageH']}px (A4 내용 영역 265mm ≈ 1001) wraps={pr['wraps']} hot={len(pr['hot'])} pdf pages={pages} orange in pdf={orange}")
    assert pages == 1, f"PDF {pages}장 — 근거 1줄로 줄일 것"
    assert orange, "PDF 에 주황이 없다"


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2]); sys.exit()
    from jobs.evaluate_recommender import connect, fetch_company_profile
    src, fsrc, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(src, encoding="utf-8")); f = json.load(open(fsrc))
    prof = fetch_company_profile(connect(), "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, f))
    print("written", out)

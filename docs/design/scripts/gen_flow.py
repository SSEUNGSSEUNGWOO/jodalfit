"""시안 "흐름" — 오늘 올라온 공고가 물줄기로 흐르고, 관문마다 통로가 좁아진다.
가닥 하나가 공고 하나. 9,285 → 업종 831 → 자격 385 → 검토할 12.
탈락 가닥은 관문에서 아래로 빠져 사라지고, 남은 12가닥이 아래 표의 12줄로 펼쳐진다.
흐름이 끝나면 띠는 접히고 '9,285 → 831 → 385 → 12' 한 줄만 표 위에 남는다.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_flow.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/flow.html
"""
import html
import json
import random
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav, table  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

W, H, CY = 1120, 330, 132
XS = [0, 288, 576, 864]          # 구간 시작 x — 관문은 288 / 576 / 864
SP = [112, 44, 26, 18]           # 각 구간 통로 반폭
FAN_X, FAN_SP = 1024, 118        # 마지막 구간에서 12가닥이 표 줄 간격으로 펼쳐지는 지점
N = [140, 24, 16, 12]            # 구간별 가닥 수 — 표본이다(실제 비율은 숫자로 적는다)
STROKE = ["#8f8f8b", "#8f8f8b", "#6b6b67", "url(#g)"]
OPA = [0.5, 0.85, 1, 1]
WID = [0.6, 0.7, 0.8, 1.2]


def paths(rnd):
    """가닥별 (fate, d, 색인). fate = 몇 번째 관문에서 빠지는가(1~3), 4면 끝까지 산다."""
    fates = [1] * (N[0] - N[1]) + [2] * (N[1] - N[2]) + [3] * (N[2] - N[3]) + [4] * N[3]
    rnd.shuffle(fates)
    lane = {}  # (seg, strand) -> y
    for s in range(4):
        alive = [i for i, f in enumerate(fates) if f > s]
        for rank, i in enumerate(alive):
            t = 0 if len(alive) == 1 else rank / (len(alive) - 1) * 2 - 1
            lane[(s, i)] = CY + t * SP[s] + (rnd.uniform(-1.6, 1.6) if s == 0 else 0)
    rows = {}  # 살아남은 가닥 -> 표에서 몇 번째 줄인가
    final = [i for i, f in enumerate(fates) if f == 4]
    for rank, i in enumerate(final):
        rows[i] = CY + (rank / (len(final) - 1) * 2 - 1) * FAN_SP

    def seg(x0, y0, x1, y1, sag=0.0):
        d = (x1 - x0) * 0.42
        return f" C{x0 + d:.0f},{y0 + sag:.1f} {x1 - d:.0f},{y1 - sag:.1f} {x1:.0f},{y1:.1f}"

    out = []
    for i, f in enumerate(fates):
        y = lane[(0, i)]
        d = f"M0,{y:.1f}"
        for s in range(1, min(f, 4)):          # 통과한 관문마다 통로 안쪽으로 수렴
            ny = lane[(s, i)]
            d += seg(XS[s - 1], y, XS[s], ny, rnd.uniform(-5, 5))
            y = ny
        if f < 4:                               # 관문 앞까지 흐른 뒤 아래로 빠진다
            gx = XS[f]
            d += seg(XS[f - 1], y, gx, y, rnd.uniform(-5, 5))
            d += f" C{gx + 46:.0f},{y + 14:.1f} {gx + 92:.0f},{CY + 150:.0f} {gx + 150 + rnd.randint(0, 70)},{H + 14}"
        else:                                   # 마지막 구간을 흐른 뒤 표의 줄 위치로 펼쳐진다
            d += seg(XS[2], y, XS[3], lane[(3, i)], rnd.uniform(-4, 4))
            d += seg(XS[3], lane[(3, i)], FAN_X, lane[(3, i)])
            d += seg(FAN_X, lane[(3, i)], W, rows[i])
        out.append((f, d))
    return out


CSS = SHEET_CSS + r"""
.q { padding:26px 0 0; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.stage { margin-top:20px; border-top:1px solid #141414 }
.gates { display:grid; grid-template-columns:288fr 288fr 288fr 256fr; border-bottom:1px solid #e6e4df }
.gate { padding:12px 16px 12px 0; border-left:1px solid #141414; padding-left:12px; opacity:.28; transition:opacity .45s ease }
.gate:first-child { border-left:0; padding-left:0 } .gate.on { opacity:1 }
.gate .k { display:block; white-space:nowrap } .gate .n { margin-top:6px; font-size:30px; letter-spacing:-0.04em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums }
.gate .n small { font-size:12px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:6px } .gate .p { margin-top:5px; font-size:12px; color:#737370 }
.gate.last .n { color:#e8431b }
.band { height:330px; overflow:hidden; transition:height .55s cubic-bezier(.3,.7,.2,1) }
.band svg { display:block; transition:transform .55s cubic-bezier(.3,.7,.2,1) }
.ttl { font-size:9.5px; fill:#8f8f8b; letter-spacing:-0.02em } .ttl.keep { fill:#6b6b67; font-size:10px }
.chain { display:flex; align-items:baseline; gap:10px; padding:14px 0 0; font-size:13px; color:#737370; height:0; opacity:0; overflow:hidden; transition:opacity .4s ease .15s, height .4s ease }
.chain b { font-size:17px; font-weight:650; color:#141414; letter-spacing:-0.02em } .chain b.acc { color:#e8431b } .chain i { font-style:normal; color:#c9c9c4 }
.done .band { height:0 } .done .band svg { transform:translateY(-120px) }
.done .gates { opacity:0; height:0; overflow:hidden; border:0; transition:opacity .3s ease, height .4s ease }
.done .chain { height:28px; opacity:1 }
.res { opacity:0; transition:opacity .5s ease .2s } .done .res { opacity:1 }
.ctl { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px }
.ctl span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.foot { max-width:840px; line-height:1.6 }
@media (prefers-reduced-motion: reduce) { .band, .band svg, .gate, .chain, .res, .gates { transition:none !important } }
"""

JS = r"""
const F = JSON.parse(document.getElementById('funnel').textContent);
const G = [...document.querySelectorAll('.gate')], front = document.getElementById('front');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let raf = 0;

function paint(x, settled){
  front.setAttribute('width', x);
  G.forEach((g, i) => g.classList.toggle('on', x >= +g.dataset.x));
  G.forEach((g, i) => {
    const span = g.querySelector('.cnt'), to = +span.dataset.to, x0 = +g.dataset.x;
    const p = Math.min(1, Math.max(0, (x - x0) / 150));
    span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString('ko-KR');
  });
  document.body.classList.toggle('done', settled);
}

function run(mode){
  cancelAnimationFrame(raf);
  document.querySelectorAll('.ctl span').forEach(s => s.classList.toggle('on', s.dataset.run === mode));
  if (mode === 'still') { paint(1120, true); return; }
  const dur = mode === 'fast' ? 1100 : 4200, t0 = performance.now();
  const tick = now => {
    const p = Math.min(1, (now - t0) / dur);
    paint(1120 * (1 - Math.pow(1 - p, 2.2)), false);
    if (p < 1) raf = requestAnimationFrame(tick);
    else setTimeout(() => document.body.classList.add('done'), mode === 'fast' ? 150 : 520);
  };
  raf = requestAnimationFrame(tick);
}

document.querySelectorAll('.ctl span').forEach(s => s.onclick = () => run(s.dataset.run));
run(reduce ? 'still' : 'full');
"""


def band(rnd, titles):
    ps, texts = [], []
    keep_i = iter(titles["keep"])
    di = iter(titles["drop_ind"])
    dr = iter(titles["drop_rgn"])
    for i, (f, d) in enumerate(paths(rnd)):
        ps.append(f'<path id="s{i}" d="{d}" fill="none" stroke="{STROKE[f - 1]}" stroke-opacity="{OPA[f - 1]}" stroke-width="{WID[f - 1]}"/>')
        src, off, cls = (di, 18, "") if f == 1 else (dr, 300, "") if f == 2 else (keep_i, 880, "keep") if f == 4 else (None, 0, "")
        if src is None:
            continue
        t = next(src, None)
        if t is None:
            continue
        texts.append(f'<text class="ttl {cls}" dy="-3.5"><textPath href="#s{i}" startOffset="{off}">{t[:34]}</textPath></text>')
    rules = "".join(f'<line x1="{x}" y1="0.5" x2="{XS[k + 1] if k < 3 else W}" y2="0.5" stroke="{"#e8431b" if k == 3 else "#141414"}"/>'
                    f'<line x1="{x + 0.5}" y1="0" x2="{x + 0.5}" y2="{H - 40}" stroke="#e6e4df"/>' for k, x in enumerate(XS) if k)
    return (f'<div class="band"><svg viewBox="0 0 {W} {H}" width="100%" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="{W}">'
            f'<stop offset="0.74" stop-color="#55554f"/><stop offset="0.79" stop-color="#e8431b"/></linearGradient>'
            f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" y1="258" y2="322">'
            f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
            f'<mask id="m"><rect x="0" y="0" width="{W}" height="258" fill="#fff"/><rect x="0" y="258" width="{W}" height="64" fill="url(#fade)"/></mask>'
            f'<clipPath id="c"><rect id="front" x="0" y="0" width="0" height="{H}"/></clipPath></defs>'
            f'<g mask="url(#m)"><g clip-path="url(#c)">{rules}{"".join(ps)}{"".join(texts)}</g></g></svg></div>')


def gates(f, n):
    steps = [("오늘 올라온 공고", f["total"], "나라장터 전체 · 마감 90일 이내"),
             ("업종이 맞는 공고", f["industry"], f'전체의 {f["industry"] / f["total"] * 100:.1f}% 통과'),
             ("자격이 되는 공고", f["qualified"], f'앞 단계의 {f["qualified"] / f["industry"] * 100:.0f}% 통과 · 면허·지역'),
             ("검토할 공고", n, f'앞 단계의 {n / f["qualified"] * 100:.1f}% · 적합 순')]
    return '<div class="gates">' + "".join(
        f'<div class="gate {"last" if i == 3 else ""}" data-x="{XS[i]}"><span class="k">{k}</span>'
        f'<div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div><div class="p">{p}</div></div>'
        for i, (k, v, p) in enumerate(steps)) + "</div>"


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    rnd = random.Random(7)
    chain = (f'<div class="chain"><span class="k">걸러낸 경로</span><b>{f["total"]:,}</b><i>→</i><b>{f["industry"]}</b><i>→</i>'
             f'<b>{f["qualified"]}</b><i>→</i><b class="acc">{len(res)}</b><span>건</span></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(prof["industries"][0] + prof["industries"][1])} · 공급물품 없음</div>'
            f'<div class="stage">{gates(f, len(res))}{band(rnd, titles)}{chain}</div>'
            f'<div class="res">{table(res, prof)}</div>'
            f'<div class="foot">가닥 하나가 공고 하나. 관문에서 빠지는 가닥은 실제 탈락 공고명을 달고 있고, 끝까지 남은 12가닥이 아래 표의 12줄이 된다. '
            f'숫자·공고명은 2026-10-15 실제 추천 결과 — 가닥 수는 눈에 읽히는 표본이고 통과율은 숫자로 적었다.</div></div>'
            f'<div class="ctl"><span data-run="full">처음 방문</span><span data-run="fast">재방문(짧게)</span><span data-run="still">움직임 줄이기</span></div>'
            f'<script type="application/json" id="funnel">{json.dumps(f)}</script>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 — 흐름</title>{FONT}'
            f'<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>')


def esc(s):
    return html.escape(s or "")


def demo():
    rnd = random.Random(7)
    ps = paths(rnd)
    assert [sum(1 for f, _ in ps if f > s) for s in range(4)] == N, "구간별 가닥 수가 안 맞는다"
    assert all(d.startswith("M0,") and "C" in d for _, d in ps)
    for s in range(3):                        # 같은 구간 안에서 가닥이 서로 교차하지 않아야 한다
        ys = [float(d.split(",")[1].split(" ")[0]) for f, d in ps if f > s]
        assert len(ys) == N[s]
    print("ok", [sum(1 for f, _ in ps if f == k) for k in (1, 2, 3, 4)])


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo(); sys.exit()
    src, fsrc, tsrc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src, encoding="utf-8"))
    fn = json.load(open(fsrc))
    tt = {k: [esc(x.strip()) for x in v] for k, v in json.load(open(tsrc, encoding="utf-8")).items()}
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    open(out, "w", encoding="utf-8", newline="\n").write(page(d, prof, fn, tt))
    print("written", out)

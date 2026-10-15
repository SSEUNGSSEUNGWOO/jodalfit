"""시안 "흐름" — 지금 입찰 가능한 공고가 띠로 흐르고, 관문마다 띠가 좁아진다.
띠의 반높이가 남은 건수(로그 눈금)다. 9,285 → 업종 831 → 자격 385 → 검토할 12.
관문에서 빠진 양은 짧은 쐐기로 아래로 빠져 60px 안에 사라지고, 마지막 12가닥이 아래 표의 12줄로 펼쳐진다.
흐름이 끝나면 띠는 접히고 '9,285 → 831 → 385 → 12' 한 줄만 표 위에 남는다.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_flow.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/flow.html
"""
import html
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav, table  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

W, H, CY = 1120, 300, 146
XS = [0, 288, 576, 864]      # 구간 시작 x — 관문은 288 / 576 / 864
TAPER = 34                   # 관문을 지난 직후 이 거리 안에서 띠가 좁아진다
FAN_X, FAN_SP = 936, 112     # 마지막 구간에서 12가닥이 표 줄 위치로 펼쳐지는 지점
HMIN, HMAX = 9, 84           # 띠 반높이 — 로그 눈금의 양 끝
DROP = 54                    # 탈락 쐐기가 아래로 빠지는 거리 (짧고 단호하게)


def half(counts):
    """반높이 = 로그 눈금. 9,285과 12를 한 화면에 같이 읽히게 하려면 선형으로는 안 된다."""
    lo, hi = math.log(counts[-1]), math.log(counts[0])
    return [HMIN + (HMAX - HMIN) * (math.log(c) - lo) / (hi - lo) for c in counts]


def edge(hh, sign):
    """위(-1)/아래(+1) 가장자리 — 관문까지 평평하게 가다 TAPER 안에서만 꺾인다. 딱딱한 모서리."""
    d, y = [], CY + sign * hh[0]
    for k in (1, 2, 3):
        ny = CY + sign * hh[k]
        d.append(f"L{XS[k]},{y:.1f} C{XS[k] + 15},{y:.1f} {XS[k] + 19},{ny:.1f} {XS[k] + TAPER},{ny:.1f}")
        y = ny
    d.append(f"L{FAN_X},{y:.1f}")
    return " ".join(d)


def edge_rev(hh, sign):
    """같은 가장자리를 FAN_X → 0 역방향으로 (띠를 하나의 닫힌 도형으로 만들기 위해)."""
    d, y = [], CY + sign * hh[3]
    for k in (3, 2, 1):
        ny = CY + sign * hh[k - 1]
        d.append(f"L{XS[k] + TAPER},{y:.1f} C{XS[k] + 19},{y:.1f} {XS[k] + 15},{ny:.1f} {XS[k]},{ny:.1f}")
        y = ny
    d.append(f"L0,{y:.1f}")
    return " ".join(d)


def strands(hh, n):
    """띠 안을 흐르는 가닥 몇 개 — 양을 나타내는 건 띠고, 이건 결이다. 마지막엔 표의 n줄로 펼쳐진다."""
    out = []
    for i in range(n):
        t = i / (n - 1) * 2 - 1
        y = CY + t * (hh[0] - 4)
        d = f"M0,{y:.1f}"
        for k in (1, 2, 3):
            ny = CY + t * max(hh[k] - 2, 1.5)
            d += f" L{XS[k]},{y:.1f} C{XS[k] + 15},{y:.1f} {XS[k] + 19},{ny:.1f} {XS[k] + TAPER},{ny:.1f}"
            y = ny
        row = CY + t * FAN_SP
        d += f" L{FAN_X},{y:.1f} C{FAN_X + 70},{y:.1f} {W - 70},{row:.1f} {W},{row:.1f}"
        out.append(d)
    return out


def wedge(hh, k):
    """관문 k에서 빠진 양 — 짧게 아래로 빠지고 DROP 안에서 사라진다. (도형, 그라디언트)."""
    gx, yb, ym = XS[k], CY + hh[k - 1], CY + hh[k]
    return (f'<path d="M{gx},{yb:.1f} C{gx + 22},{yb + 12:.1f} {gx + 42},{yb + 32:.1f} {gx + 58},{yb + DROP:.1f} '
            f'L{gx + 42},{yb + DROP:.1f} C{gx + 32},{yb + 26:.1f} {gx + TAPER + 8},{ym + 8:.1f} {gx + TAPER},{ym:.1f} Z" '
            f'fill="url(#w{k})"/>',
            f'<linearGradient id="w{k}" gradientUnits="userSpaceOnUse" x1="0" y1="{yb:.1f}" x2="0" y2="{yb + DROP:.1f}">'
            f'<stop offset="0" stop-color="#141414" stop-opacity=".26"/><stop offset=".55" stop-color="#141414" stop-opacity=".07"/>'
            f'<stop offset="1" stop-color="#141414" stop-opacity="0"/></linearGradient>')


CSS = SHEET_CSS + r"""
.q { padding:26px 0 0; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.stage { margin-top:20px; border-top:1px solid #141414 }
.band { position:relative; height:300px; overflow:hidden; transition:height .55s cubic-bezier(.3,.7,.2,1) }
.band svg { display:block; transition:transform .55s cubic-bezier(.3,.7,.2,1) }
.lab { position:absolute; opacity:0; transition:opacity .4s ease } .lab.on { opacity:1 }
.lab .k { display:block; font-size:12px; color:#55554f; white-space:nowrap; line-height:1.3 }
.lab .n { margin-top:5px; font-size:26px; letter-spacing:-0.04em; font-weight:650; line-height:1; font-variant-numeric:tabular-nums; color:#141414 }
.lab .n small { font-size:11.5px; color:#6b6b67; font-weight:450; letter-spacing:0; margin-left:5px }
.lab.last .n { color:#e8431b }
.ttl { position:absolute; font-size:11.5px; line-height:1; color:#6b6b67; letter-spacing:-0.015em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
       opacity:0; transition:opacity .35s ease } .ttl.on { opacity:1 }
.chain { display:flex; align-items:baseline; gap:10px; font-size:13px; color:#737370; height:0; opacity:0; overflow:hidden; transition:opacity .4s ease .15s, height .4s ease }
.chain b { font-size:17px; font-weight:650; color:#141414; letter-spacing:-0.02em; font-variant-numeric:tabular-nums } .chain b.acc { color:#e8431b } .chain i { font-style:normal; color:#c9c9c4 }
.done .band { height:0 } .done .band svg { transform:translateY(-120px) }
.done .chain { height:48px; opacity:1; padding-top:16px }
.res { opacity:0; max-height:0; overflow:hidden; transition:opacity .5s ease .2s } .done .res { opacity:1; max-height:none }
.ctl { position:fixed; left:50%; bottom:20px; transform:translateX(-50%); display:flex; gap:2px; background:#fff; border:1px solid #e6e4df; border-radius:999px; padding:3px; font-size:12.5px }
.ctl span { padding:6px 14px; border-radius:999px; color:#55554f; cursor:pointer } .ctl span.on { background:#141414; color:#fff }
.foot { max-width:880px; line-height:1.6 }
@media (prefers-reduced-motion: reduce) { .band, .band svg, .lab, .ttl, .chain, .res { transition:none !important } }
"""

JS = r"""
const L = [...document.querySelectorAll('.lab')], T = [...document.querySelectorAll('.ttl')];
const front = document.getElementById('front');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let raf = 0;

function paint(x, settled){
  front.setAttribute('width', x);
  T.forEach(t => t.classList.toggle('on', x >= +t.dataset.x));
  L.forEach(g => {
    g.classList.toggle('on', x >= +g.dataset.x);
    const span = g.querySelector('.cnt'), to = +span.dataset.to;
    const p = Math.min(1, Math.max(0, (x - g.dataset.x) / 150));
    span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString('ko-KR');
  });
  document.body.classList.toggle('done', settled);
}

function run(mode){
  cancelAnimationFrame(raf);
  document.querySelectorAll('.ctl span').forEach(s => s.classList.toggle('on', s.dataset.run === mode));
  if (mode === 'still') { paint(1120, true); return; }
  const dur = mode === 'fast' ? 1100 : 3600, t0 = performance.now();
  const tick = now => {
    const p = Math.min(1, (now - t0) / dur);
    paint(1120 * (1 - Math.pow(1 - p, 2.2)), false);
    if (p < 1) raf = requestAnimationFrame(tick);
    else setTimeout(() => document.body.classList.add('done'), mode === 'fast' ? 150 : 480);
  };
  raf = requestAnimationFrame(tick);
}

document.querySelectorAll('.ctl span').forEach(s => s.onclick = () => run(s.dataset.run));
run(reduce ? 'still' : 'full');
"""

# (구간, 왼쪽 x, 기준선 y, 최대폭) — 1구간 6개, 2구간 3개. 각자 자기 줄을 쓰고 관문선을 넘지 않는다.
SPOTS = ([("drop_ind", 16, 72), ("drop_ind", 16, 98), ("drop_ind", 16, 124), ("drop_ind", 16, 150), ("drop_ind", 16, 176), ("drop_ind", 16, 202)]
         + [("drop_rgn", 304, 108), ("drop_rgn", 304, 146), ("drop_rgn", 304, 184)])


def band(f, n, titles):
    hh = half([f["total"], f["industry"], f["qualified"], n])
    fill = (f'<path d="M0,{CY - hh[0]:.1f} {edge(hh, -1)} L{FAN_X},{CY + hh[3]:.1f} {edge_rev(hh, 1)} Z" fill="#141414" fill-opacity=".11"/>')
    acc = (f'<path d="M{XS[3]},{CY - hh[2]:.1f} C{XS[3] + 15},{CY - hh[2]:.1f} {XS[3] + 19},{CY - hh[3]:.1f} {XS[3] + TAPER},{CY - hh[3]:.1f} '
           f'L{FAN_X},{CY - hh[3]:.1f} L{FAN_X},{CY + hh[3]:.1f} L{XS[3] + TAPER},{CY + hh[3]:.1f} '
           f'C{XS[3] + 19},{CY + hh[3]:.1f} {XS[3] + 15},{CY + hh[2]:.1f} {XS[3]},{CY + hh[2]:.1f} Z" fill="#e8431b" fill-opacity=".14"/>')
    rims = "".join(f'<path d="M0,{CY + s * hh[0]:.1f} {edge(hh, s)}" fill="none" stroke="#141414" stroke-opacity=".5" stroke-width="1"/>' for s in (-1, 1))
    # 가닥은 띠 안에서는 결(연한 먹), 마지막 구간부터는 셀 수 있게 인주로 굵어진다 — 12개를 눈으로 세는 지점
    hair = "".join(f'<path d="{d}" fill="none" stroke="url(#g)" stroke-width=".9"/>' for d in strands(hh, n))
    grad = (f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="{W}">'
            f'<stop offset="0" stop-color="#141414" stop-opacity=".3"/><stop offset="{(XS[3] - 20) / W:.3f}" stop-color="#141414" stop-opacity=".3"/>'
            f'<stop offset="{(XS[3] + 30) / W:.3f}" stop-color="#e8431b" stop-opacity=".85"/><stop offset="1" stop-color="#e8431b" stop-opacity=".85"/></linearGradient>')
    gates = "".join(f'<line x1="{x + .5}" y1="0" x2="{x + .5}" y2="{H}" stroke="#e6e4df"/>' for x in XS[1:])
    wd = [wedge(hh, k) for k in (1, 2, 3)]
    svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" preserveAspectRatio="none" aria-hidden="true">'
           f'<defs><clipPath id="c"><rect id="front" x="0" y="0" width="0" height="{H}"/></clipPath>'
           f'{grad}{"".join(g for _, g in wd)}</defs>'
           f'{gates}<g clip-path="url(#c)">{fill}{acc}{"".join(p for p, _ in wd)}{rims}{hair}</g></svg>')

    # 글자는 전진선이 제 폭을 다 지나간 뒤에만 나타난다 — 잉크보다 앞서 나가면 계측이 아니다
    tx = "".join(f'<div class="ttl" data-x="{x + XS[1] - 32}" style="left:{x / W * 100:.3f}%;top:{y}px;max-width:{(XS[1] - 32) / W * 100:.3f}%">{titles[src][k]}</div>'
                 for k, (src, x, y) in enumerate(SPOTS))
    return f'<div class="band">{svg}{labels(f, n, hh)}{tx}</div>'


def labels(f, n, hh):
    steps = [("지금 입찰 가능한 공고 · 마감 90일 이내", f["total"]),
             (f'업종이 맞는 공고 · 전체의 {f["industry"] / f["total"] * 100:.1f}%', f["industry"]),
             (f'자격이 되는 공고 · 면허·지역 {f["qualified"] / f["industry"] * 100:.0f}% 통과', f["qualified"]),
             (f'검토할 공고 · 앞 단계의 {n / f["qualified"] * 100:.1f}%', n)]
    return "".join(
        f'<div class="lab {"last" if i == 3 else ""}" data-x="{XS[i]}" style="left:{(XS[i] + (0 if i == 0 else 12)) / W * 100:.3f}%;top:{max(10, CY - hh[i] - 52):.0f}px">'
        f'<span class="k">{k}</span><div class="n"><span class="cnt" data-to="{v}">0</span><small>건</small></div></div>'
        for i, (k, v) in enumerate(steps))


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    chain = (f'<div class="chain"><span class="k">걸러낸 경로</span><b>{f["total"]:,}</b><i>→</i><b>{f["industry"]}</b><i>→</i>'
             f'<b>{f["qualified"]}</b><i>→</i><b class="acc">{len(res)}</b><span>건</span></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(prof["industries"][0] + prof["industries"][1])} · 공급물품 없음</div>'
            f'<div class="stage">{band(f, len(res), titles)}{chain}</div>'
            f'<div class="res">{table(res, prof)}</div>'
            f'<div class="foot">띠의 두께가 남은 건수다 — 9,285건과 12건을 한 화면에 같이 읽히게 하려고 <b>로그 눈금</b>으로 그렸다(두께가 절반이면 건수는 약 1/100). '
            f'안에 흐르는 가는 선 {len(res)}개는 결이지 개수가 아니고, 그중 끝까지 남은 선이 아래 표의 {len(res)}줄이 된다. '
            f'관문에서 빠지는 양은 아래로 짧게 빠지며 그 자리에 실제 탈락 공고명을 남긴다. 숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>'
            f'<div class="ctl"><span data-run="full">처음 방문</span><span data-run="fast">재방문(짧게)</span><span data-run="still">움직임 줄이기</span></div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조달핏 — 흐름</title>{FONT}'
            f'<style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>')


def esc(s):
    return html.escape(s or "")


def demo():
    f = {"total": 9285, "industry": 831, "qualified": 385}
    hh = half([f["total"], f["industry"], f["qualified"], 12])
    assert hh[0] == HMAX and abs(hh[3] - HMIN) < 1e-9, hh
    assert hh[0] > hh[1] > hh[2] > hh[3], hh          # 단조 감소
    assert hh[1] > (hh[0] + hh[3]) / 2, hh            # 로그라서 831이 선형 중간보다 위에 있어야
    assert CY + hh[0] + DROP <= H, "쐐기가 캔버스를 벗어난다"
    for i, h in enumerate(hh):
        assert max(10, CY - h - 52) + 46 < CY - h, f"{i}구간 라벨이 띠를 침범한다"
    ss = strands(hh, 12)
    ys = sorted(float(d.rsplit(",", 1)[-1]) for d in ss)
    assert all(d.startswith("M0,") for d in ss) and all(f"L{FAN_X}," in d for d in ss)
    assert len(set(ys)) == 12 and round(ys[-1] - ys[0]) == 2 * FAN_SP, ys
    # 제목은 자기 줄을 쓰고(겹침 없음) 관문선을 넘지 않으며 띠 안에 들어온다
    for s, (_, x, y) in enumerate(SPOTS):
        seg = 0 if x < XS[1] else 1
        assert CY - hh[seg] + 6 < y < CY + hh[seg] - 6, (x, y)
        assert x + (XS[1] - 32) <= XS[seg + 1], (x, y)
    for a in range(len(SPOTS)):
        for b in range(a + 1, len(SPOTS)):
            assert SPOTS[a][1] != SPOTS[b][1] or abs(SPOTS[a][2] - SPOTS[b][2]) >= 24, (a, b)
    print("ok half=", [round(v, 1) for v in hh], "fan", round(ys[0]), round(ys[-1]))


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

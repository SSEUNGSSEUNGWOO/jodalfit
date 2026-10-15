"""시안 "흐름" — 지금 입찰 가능한 공고가 띠로 흐르고, 관문(체) 세 개를 지나며 통로가 좁아진다.
띠의 반높이가 남은 건수(로그 눈금)다. 9,285 → 업종 831 → 자격 385 → 검토할 12.
관문은 통로만 뚫린 세로 벽이다. 통로에 안 맞는 양은 떨어지는 게 아니라 벽 앞에서 눌려 사라진다
— 그 공고들이 나쁜 게 아니라 '이 회사'에 해당되지 않을 뿐이라서, 아래로 버리는 그림을 쓰지 않는다.
통로를 지난 흐름은 다시 가운데로 모여 다음 관문까지 간다. 마지막 12가닥이 아래 표의 12줄로 펼쳐진다.
흐름이 끝나면 띠는 접히고 '9,285 → 831 → 385 → 12' 한 줄만 표 위에 남는다.
사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run python ../docs/design/scripts/gen_flow.py <sample.json> <funnel.json> <scene_titles.json> ../docs/design/prototypes/flow.html
"""
import html
import json
import math
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from gen_results_v3 import FONT, SHEET_CSS  # noqa: E402
from gen_results_v4 import nav, table  # noqa: E402
from jobs.evaluate_recommender import connect, fetch_company_profile  # noqa: E402

W, H, CY = 1120, 252, 142
XS = [0, 288, 576, 864]      # 구간 시작 x — 관문(벽)은 288 / 576 / 864 에 같은 간격으로 선다
FAN_X, FAN_SP = 936, 100     # 마지막 구간에서 12가닥이 표 줄 위치로 펼쳐지는 지점
HMIN, HMAX = 9, 78           # 띠 반높이 — 로그 눈금의 양 끝
PRESS = 44                   # 벽에 막힌 양이 눌렸다 흩어지는 거리 (벽 앞 44px)
CONV = 44                    # 가닥이 통로 폭으로 모이는 거리 (벽 앞 44px)


def half(counts):
    """반높이 = 로그 눈금. 9,285과 12를 한 화면에 같이 읽히게 하려면 선형으로는 안 된다."""
    lo, hi = math.log(counts[-1]), math.log(counts[0])
    return [HMIN + (HMAX - HMIN) * (math.log(c) - lo) / (hi - lo) for c in counts]


def stops(x0, x1, a, pressed, tail):
    """벽 앞에서만 변하는 가로 그라디언트 — PRESS 전까지는 그대로, 벽에 눌려 짙어졌다 벽면에서 흩어진다.
    벽면에서 0이 아니라 tail 로 끝낸다: 잉크가 벽에 닿아야 '막혔다'로 읽힌다(벽 앞에서 끊기면 그냥 사라진 것)."""
    wd = x1 - x0
    return (f'<linearGradient gradientUnits="userSpaceOnUse" x1="{x0}" x2="{x1}">'
            f'<stop offset="0" stop-color="#141414" stop-opacity="{a}"/>'
            f'<stop offset="{(wd - PRESS) / wd:.3f}" stop-color="#141414" stop-opacity="{a}"/>'
            f'<stop offset="{(wd - 6) / wd:.3f}" stop-color="#141414" stop-opacity="{pressed}"/>'
            f'<stop offset="1" stop-color="#141414" stop-opacity="{tail}"/></linearGradient>')


def strands(hh, n):
    """띠 안을 흐르는 가닥 몇 개 — 양을 나타내는 건 띠고, 이건 결이다. 벽 앞에서 통로 폭으로 모인다."""
    out = []
    for i in range(n):
        t = i / (n - 1) * 2 - 1
        y = CY + t * (hh[0] - 5)
        d = f"M0,{y:.1f}"
        for k in (1, 2, 3):
            ny = CY + t * max(hh[k] - 2, 1.5)
            g = XS[k]
            d += f" L{g - CONV},{y:.1f} C{g - 20},{y:.1f} {g - 16},{ny:.1f} {g},{ny:.1f}"
            y = ny
        row = CY + t * FAN_SP
        d += f" L{FAN_X},{y:.1f} C{FAN_X + 70},{y:.1f} {W - 70},{row:.1f} {W},{row:.1f}"
        out.append(d)
    return out


def sieve(hh):
    """구간 = 평평한 네모(계단식). 관문 = 통로만 뚫린 세로 벽. 막힌 양은 벽 앞에서 눌려 사라진다."""
    defs, body, walls = [], [], []
    for s in (0, 1, 2):
        g, x0 = XS[s + 1], XS[s]
        defs.append(stops(x0, g, ".11", ".27", ".08").replace("<linearGradient", f'<linearGradient id="p{s}"', 1))
        defs.append(stops(x0, g, ".5", ".88", ".12").replace("<linearGradient", f'<linearGradient id="e{s}"', 1))
        # 통로를 지날 속심 — 벽까지 그대로 간다
        body.append(f'<rect x="{x0}" y="{CY - hh[s + 1]:.1f}" width="{g - x0}" height="{2 * hh[s + 1]:.1f}" fill="#141414" fill-opacity=".11"/>')
        for sg in (-1, 1):
            y = CY - hh[s] if sg < 0 else CY + hh[s + 1]
            body.append(f'<rect x="{x0}" y="{y:.1f}" width="{g - x0}" height="{hh[s] - hh[s + 1]:.1f}" fill="url(#p{s})"/>')
            body.append(f'<line x1="{x0}" y1="{CY + sg * hh[s]:.1f}" x2="{g}" y2="{CY + sg * hh[s]:.1f}" stroke="url(#e{s})" stroke-width="1"/>')
            # 벽: 통로(±hh[s+1]) 바깥만 막혀 있다. 통로 쪽 끝에 짧은 입술을 달아 '뚫린 구멍'을 분명히 한다
            walls.append(f'<line x1="{g}" y1="{CY + sg * hh[s]:.1f}" x2="{g}" y2="{CY + sg * hh[s + 1]:.1f}" stroke="#141414" stroke-width="2.5"/>'
                         f'<line x1="{g - 7}" y1="{CY + sg * hh[s + 1]:.1f}" x2="{g + 7}" y2="{CY + sg * hh[s + 1]:.1f}" stroke="#141414" stroke-width="1.5"/>')
    # 마지막 구간 — 통과한 12건, 유일한 인주
    body.append(f'<rect x="{XS[3]}" y="{CY - hh[3]:.1f}" width="{FAN_X - XS[3]}" height="{2 * hh[3]:.1f}" fill="#e8431b" fill-opacity=".16"/>')
    for sg in (-1, 1):
        body.append(f'<line x1="{XS[3]}" y1="{CY + sg * hh[3]:.1f}" x2="{FAN_X}" y2="{CY + sg * hh[3]:.1f}" stroke="#141414" stroke-opacity=".5" stroke-width="1"/>')
    return "".join(defs), "".join(body), "".join(walls)


CSS = SHEET_CSS + r"""
.q { padding:26px 0 0; font-size:13.5px; color:#55554f } .q b { color:#141414; font-size:16px; font-weight:650; margin-right:10px }
.stage { margin-top:20px; border-top:1px solid #141414 }
.band { position:relative; height:252px; overflow:hidden; transition:height .55s cubic-bezier(.3,.7,.2,1) }
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
/* 적합은 숫자 없이 막대만 (docs/design/README.md 표현·요소 결정 2026-10-15) */
.tr .fit i { margin-right:0 }
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

# (출처, 왼쪽 x, 기준선 y) — 1구간 6개, 2구간 3개. 각자 자기 줄을 쓰고 벽을 넘지 않는다.
SPOTS = ([("drop_ind", 16, 72), ("drop_ind", 16, 98), ("drop_ind", 16, 124), ("drop_ind", 16, 150), ("drop_ind", 16, 176), ("drop_ind", 16, 200)]
         + [("drop_rgn", 304, 104), ("drop_rgn", 304, 136), ("drop_rgn", 304, 168)])


def band(f, n, titles):
    hh = half([f["total"], f["industry"], f["qualified"], n])
    defs, body, walls = sieve(hh)
    # 가닥은 띠 안에서는 결(연한 먹), 마지막 구간부터는 셀 수 있게 인주로 굵어진다 — 12개를 눈으로 세는 지점
    hair = "".join(f'<path d="{d}" fill="none" stroke="url(#g)" stroke-width=".9"/>' for d in strands(hh, n))
    grad = (f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="{W}">'
            f'<stop offset="0" stop-color="#141414" stop-opacity=".3"/><stop offset="{(XS[3] - 20) / W:.3f}" stop-color="#141414" stop-opacity=".3"/>'
            f'<stop offset="{(XS[3] + 30) / W:.3f}" stop-color="#e8431b" stop-opacity=".85"/><stop offset="1" stop-color="#e8431b" stop-opacity=".85"/></linearGradient>')
    # 벽에서 라벨까지 올라가는 연한 기둥 — 이 숫자를 만든 게 저 벽임을 눈으로 잇는다
    posts = "".join(f'<line x1="{x + .5}" y1="0" x2="{x + .5}" y2="{H}" stroke="#d8d6d0"/>' for x in XS[1:])
    svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" preserveAspectRatio="none" aria-hidden="true">'
           f'<defs><clipPath id="c"><rect id="front" x="0" y="0" width="0" height="{H}"/></clipPath>{grad}{defs}</defs>'
           f'{posts}<g clip-path="url(#c)">{body}{hair}{walls}</g></svg>')

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


def sheet(res, prof):
    """gen_results_v4.table() 결과를 이 시안의 표현 결정에 맞게 깎는다.
    (gen_results_v3/v4 는 다른 작업자가 쓰는 중이라 건드리지 않고 문자열에서 뺀다 — README 2026-10-15)
    적합 점수 숫자는 빼고 막대만, '안 맞아요' 는 없애고 '검토 인장' 은 '검토' 로."""
    h = re.sub(r'(<i><b style="width:\d+%"></b></i>)\d+(</span>)', r"\1\2", table(res, prof))
    h = h.replace('<a class="bt" href="#">검토 인장</a><a class="bt txt" href="#"><u>안 맞아요</u></a>',
                  '<a class="bt" href="#">검토</a>')
    assert "안 맞아요" not in h and "검토 인장" not in h, "표 버튼 치환 실패 — gen_results_v4 마크업이 바뀌었다"
    assert not re.search(r"</b></i>\d", h), "적합 숫자가 남았다"
    return h


def page(d, prof, f, titles):
    res, co = d["results"], d["company"]
    chain = (f'<div class="chain"><span class="k">걸러낸 경로</span><b>{f["total"]:,}</b><i>→</i><b>{f["industry"]}</b><i>→</i>'
             f'<b>{f["qualified"]}</b><i>→</i><b class="acc">{len(res)}</b><span>건</span></div>')
    body = (f'<div class="wrap">{nav()}'
            f'<div class="q"><b>{esc(co["corp_nm"])}</b>{esc(co["rgn_nm"])} · 등록업종 {len(prof["industries"][0] + prof["industries"][1])} · 공급물품 없음</div>'
            f'<div class="stage">{band(f, len(res), titles)}{chain}</div>'
            f'<div class="res">{sheet(res, prof)}</div>'
            f'<div class="foot">띠의 두께가 남은 건수다 — 9,285건과 12건을 한 화면에 같이 읽히게 하려고 <b>로그 눈금</b>으로 그렸다(두께가 절반이면 건수는 약 1/100). '
            f'세로 벽 세 개가 관문이고, 뚫린 통로 높이가 통과한 건수다. 통로에 안 맞는 양은 <b>벽 앞에서 눌려 사라진다</b> — '
            f'떨어뜨리는 게 아니라 이 회사에 해당되지 않을 뿐이고, 같은 공고가 다른 회사에서는 통과한다. '
            f'안에 흐르는 가는 선 {len(res)}개는 결이지 개수가 아니고, 그중 끝까지 남은 선이 아래 표의 {len(res)}줄이 된다. 숫자·공고명은 2026-10-15 실제 추천 결과.</div></div>'
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
    # 아래로 새는 것이 없다 — 띠도 부채도 캔버스 안에 들어온다
    assert CY + hh[0] <= H and CY + FAN_SP <= H and CY - FAN_SP >= 0, (CY, hh[0], H)
    defs, body, walls = sieve(hh)
    assert walls.count("<line") == 12, "관문마다 위·아래 벽 2 + 통로 입술 2 = 12개"
    for k in (1, 2, 3):                               # 통로 높이 = 통과한 건수의 띠 높이
        assert f'x1="{XS[k]}" y1="{CY - hh[k - 1]:.1f}" x2="{XS[k]}" y2="{CY - hh[k]:.1f}"' in walls, k
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

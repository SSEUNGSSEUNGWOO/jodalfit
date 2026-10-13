"""Attio 워크플로우 캔버스 문법으로 추천 파이프라인."""
import sys
out = sys.argv[1]
F = 'font-family="Pretendard Variable,Pretendard,sans-serif"'
INK, SUB, MUTE, BLUE, GRAY = "#141414", "#5c5c58", "#9a9a96", "#b9b9b4", "#d6d6d2"
W, H = 1240, 600

def icon(kind, x, y, bg, fg):
    # 24x24 아이콘 타일 (간단 기하)
    s = f'<rect x="{x}" y="{y}" width="34" height="34" rx="8" fill="{bg}"/>'
    cx, cy = x+17, y+17
    if kind == "search":  s += f'<circle cx="{cx-2}" cy="{cy-2}" r="6" fill="none" stroke="{fg}" stroke-width="1.8"/><line x1="{cx+3}" y1="{cy+3}" x2="{cx+8}" y2="{cy+8}" stroke="{fg}" stroke-width="2" stroke-linecap="round"/>'
    if kind == "db":      s += f'<ellipse cx="{cx}" cy="{cy-6}" rx="8" ry="3" fill="none" stroke="{fg}" stroke-width="1.8"/><path d="M{cx-8},{cy-6} v12 a8,3 0 0 0 16,0 v-12" fill="none" stroke="{fg}" stroke-width="1.8"/><path d="M{cx-8},{cy} a8,3 0 0 0 16,0" fill="none" stroke="{fg}" stroke-width="1.8"/>'
    if kind == "vec":     s += "".join(f'<circle cx="{cx+dx}" cy="{cy+dy}" r="2.2" fill="{fg}"/>' for dx,dy in ((-7,-6),(5,-7),(-3,2),(7,4),(-8,7),(2,8))) + f'<line x1="{cx-7}" y1="{cy-6}" x2="{cx-3}" y2="{cy+2}" stroke="{fg}" stroke-width="1.2"/><line x1="{cx-3}" y1="{cy+2}" x2="{cx+7}" y2="{cy+4}" stroke="{fg}" stroke-width="1.2"/>'
    if kind == "list":    s += "".join(f'<rect x="{cx-9}" y="{cy-8+i*6}" width="18" height="2.6" rx="1.3" fill="{fg}"/>' for i in range(3))
    if kind == "match":   s += f'<circle cx="{cx-4}" cy="{cy}" r="6.5" fill="none" stroke="{fg}" stroke-width="1.8"/><circle cx="{cx+4}" cy="{cy}" r="6.5" fill="none" stroke="{fg}" stroke-width="1.8"/>'
    if kind == "branch":  s += f'<circle cx="{cx-6}" cy="{cy}" r="2.6" fill="{fg}"/><circle cx="{cx+6}" cy="{cy-6}" r="2.6" fill="{fg}"/><circle cx="{cx+6}" cy="{cy+6}" r="2.6" fill="{fg}"/><path d="M{cx-4},{cy} C{cx},{cy} {cx},{cy-6} {cx+4},{cy-6} M{cx-4},{cy} C{cx},{cy} {cx},{cy+6} {cx+4},{cy+6}" fill="none" stroke="{fg}" stroke-width="1.6"/>'
    if kind == "sort":    s += "".join(f'<rect x="{cx-9}" y="{cy-8+i*6}" width="{18-i*5}" height="2.6" rx="1.3" fill="{fg}"/>' for i in range(3))
    if kind == "check":   s += f'<path d="M{cx-7},{cy} l5,5 l9,-10" fill="none" stroke="{fg}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    if kind == "x":       s += f'<path d="M{cx-6},{cy-6} l12,12 M{cx+6},{cy-6} l-12,12" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>'
    return s

def node(x, y, w, title, sub, kind, bg, fg, status=None, trigger=False, h=76, muted=False, ports=("in","out")):
    s = f'<g class="nd"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#fff" stroke="{"#e6e6e2" if not muted else "#ececea"}" stroke-width="1"/>'
    s += f'<rect x="{x+1}" y="{y+1}" width="{w-2}" height="{h-2}" rx="15" fill="none" stroke="#fff" stroke-width="1" opacity=".6"/>'
    s += icon(kind, x+16, y+21, bg, fg)
    s += f'<text x="{x+64}" y="{y+34}" font-size="15.5" font-weight="600" letter-spacing="-0.01em" fill="{INK if not muted else MUTE}" {F}>{title}</text>'
    s += f'<text x="{x+64}" y="{y+54}" font-size="12" fill="{MUTE}" {F}>{sub}</text>'
    if status:
        s += f'<text x="{x+w-14}" y="{y+22}" font-size="11" fill="{MUTE}" text-anchor="end" {F}>{status}</text>'
    return s + "</g>"

def conn(points, color=BLUE, arrow=True, r=10):
    # 직교 꺾임 + 둥근 모서리
    d = f"M{points[0][0]},{points[0][1]}"
    for i in range(1, len(points)-1):
        (x0,y0),(x1,y1),(x2,y2) = points[i-1], points[i], points[i+1]
        dx1, dy1 = (x1-x0), (y1-y0); dx2, dy2 = (x2-x1), (y2-y1)
        sx = (dx1/abs(dx1)) if dx1 else 0; sy = (dy1/abs(dy1)) if dy1 else 0
        tx = (dx2/abs(dx2)) if dx2 else 0; ty = (dy2/abs(dy2)) if dy2 else 0
        d += f" L{x1 - sx*r},{y1 - sy*r} Q{x1},{y1} {x1 + tx*r},{y1 + ty*r}"
    d += f" L{points[-1][0]},{points[-1][1]}"
    mk = f' marker-end="url(#arr{"b" if color==BLUE else "g"})"' if arrow else ""
    return f'<path class="cn" pathLength="1" d="{d}" fill="none" stroke="{color}" stroke-width="1.2"{mk}/>'

g = [f'''<svg viewBox="0 0 {W} {H}" width="100%" style="display:block"><defs>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="#e4e4e0"/></pattern>
<marker id="arrb" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1 L8,5 L0,9" fill="none" stroke="{BLUE}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
<marker id="arrg" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1 L8,5 L0,9" fill="none" stroke="{GRAY}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
</defs><rect width="{W}" height="{H}" fill="#fafaf8"/><rect width="{W}" height="{H}" fill="url(#dots)"/>''']

# 좌표
NW = 290; NH = 76
r1y, r2y, r3y = 60, 260, 460
n1 = (60, r1y); n2 = (460, r1y); n3 = (860, r1y)
n4 = (60, r2y); n5 = (460, r2y); n6 = (860, r2y)
n7 = (460, r3y)
# 연결선 먼저 (카드 뒤로)
g.append(conn([(n1[0]+NW, r1y+NH/2), (n2[0], r1y+NH/2)]))
g.append(conn([(n2[0]+NW, r1y+NH/2), (n3[0], r1y+NH/2)]))
g.append(conn([(n3[0]+NW, r1y+NH/2), (n3[0]+NW+40, r1y+NH/2), (n3[0]+NW+40, r1y+NH+60), (20, r1y+NH+60), (20, r2y+NH/2), (n4[0], r2y+NH/2)]))
g.append(conn([(n4[0]+NW, r2y+NH/2), (n5[0], r2y+NH/2)]))
# 분기: 통과 → 점수·정렬(오른쪽), 미충족 → 제외(아래)
g.append(conn([(n5[0]+NW, r2y+NH/2), (n6[0], r2y+NH/2)]))
g.append(conn([(n5[0]+NW/2, r2y+NH), (n5[0]+NW/2, r3y)], color=GRAY))
# 점수·정렬 → 결과 (아래로)
g.append(conn([(n6[0]+NW/2, r2y+NH), (n6[0]+NW/2, r3y)]))

# 노드
g.append(node(*n1, NW, "회사명 입력", "케이브레인컴퍼니", "search", "#e8efff", "#2f6bf6", status="시작"))
g.append(node(*n2, NW, "회사 데이터", "등록업종 · 공급물품 · 수주 이력", "db", "#fdeaf3", "#c83a7a", status="나라장터"))
g.append(node(*n3, NW, "회사 벡터", "업종 65 · 수주 30 · 관심 5", "vec", "#eaf7ee", "#1a8a4a"))
g.append(node(*n4, NW, "오늘 공고", "매일 05:00 · 같은 공간에 임베딩", "list", "#fff3e3", "#b8600e", status="10,278건"))
g.append(node(*n5, NW, "매칭 · 자격", "가까운 100건 · 면허·지역 판정", "branch", "#efe9fb", "#6b3fd6", status="100건"))
g.append(f'<text x="{n5[0]+NW+12}" y="{r2y+NH/2-8}" font-size="11" fill="{MUTE}" {F}>통과 88</text>')
g.append(f'<text x="{n5[0]+NW/2+10}" y="{r2y+NH+40}" font-size="11" fill="{MUTE}" {F}>미충족 12</text>')
g.append(node(*n6, NW, "점수 · 정렬", "기관 · 지역 · 예산 · 마감 · 다양성", "sort", "#e8efff", "#2f6bf6"))
g.append(node(n6[0], r3y, NW, "결과 30건", "행마다 왜 남았나", "check", "#eaf7ee", "#1a8a4a"))
g.append(node(n5[0], r3y, NW, "제외 12건", "면허 9 · 지역 3", "x", "#f1f1ef", "#8a8a86", muted=True))
g.append("</svg>")
canvas = "".join(g)

html = f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>.cv *{{font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif;box-sizing:border-box}} .cv .box{{border:1px solid #d8d7d2;border-radius:6px;overflow:hidden}} .cv h2{{margin:0 0 4px;font-size:20px}} .cv p{{margin:0 0 16px;font-size:13px;color:#555;line-height:1.6;max-width:900px}}</style>
<div class="cv"><h2>추천 파이프라인 — 미니멀</h2><p>점 격자 캔버스, 아이콘 타일 + 제목 + 설명의 카드, 둥근 모서리로 꺾이는 파란 연결선, 상태 칩, 첫 노드의 Trigger 탭, 자격 판정의 분기(통과 / 미충족). 숫자는 실제 값(가중치·오늘 공고 수·점수 항목).</p>
<div class="box">{canvas}</div>
<p style="margin-top:14px">메인 "02 근거" 섹션에 이 캔버스를 넣으면 "어떻게 추천하는지"가 그림 하나로 설명됩니다. 실제 구현에선 노드가 순서대로 켜지고(상태 칩이 하나씩 ✓로), 회사명을 바꾸면 숫자가 갱신됩니다.</p></div>'''
open(out, "w", encoding="utf-8").write(html); print("written", len(html))

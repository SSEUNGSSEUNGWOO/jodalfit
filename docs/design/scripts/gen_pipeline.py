"""추천 파이프라인 다이어그램 — 한 줄, 교차 없음. 실제 코드의 가중치·점수 항목 그대로."""
import sys
out = sys.argv[1]
INK, SUB, MUTE, RULE, HOT, PAPER = "#141414", "#5c5c58", "#9a9a96", "#e6e4df", "#e8431b", "#faf9f6"
F = 'font-family="Pretendard Variable,Pretendard,sans-serif"'

steps = [
 ("01", "입력", "회사명 또는 사업자번호", ["회사명 유사 검색으로 식별", "못 찾으면 키워드 모드로"]),
 ("02", "회사 데이터", "나라장터 공개 API", ["등록업종 (메인)", "공급물품 (메인)", "과거 수주 이력 (보조)"]),
 ("03", "회사 벡터", "텍스트 임베딩 1536차원", ["수주 0건: 업종 100%", "1~5건: 업종 65 · 수주 30 · 관심 5", "6건+: 업종 50 · 수주 45 · 관심 5"]),
 ("04", "오늘 공고", "매일 05:00 수집·임베딩", ["진행 중 10,278건", "공고명·기관·마감·추정가·제한", "같은 1536차원 공간"]),
 ("05", "매칭", "코사인 유사도 → 후보 100", ["pgvector 근접 검색", "면허·지역 제한 미충족 제외"]),
 ("06", "점수·정렬", "규칙 점수 + 다양성", ["유사도 ×100, 업종·물품 일치", "재출현 기관 +50, 지역 +30", "예산대 ±20, 마감 임박 −30", "비슷한 공고 중복 억제 (MMR)"]),
 ("07", "결과", "남은 30건 + 왜 남았나", ["행마다 점수 근거 배지", "회사 벡터와의 유사도 표시"]),
]
W = 1120; gap = 18; cols = 4; bw = (W - gap*(cols-1)) / cols; BH = 196; RG = 34; H = BH*2 + RG
g = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#b5b5b0"/></marker></defs>']
for k, (no, title, sub, items) in enumerate(steps):
    r, cidx = divmod(k, cols); x = cidx * (bw + gap); y = r * (BH + RG); hot = k in (2, 5)
    g.append(f'<rect x="{x:.0f}" y="{y}" width="{bw:.0f}" height="{BH}" rx="10" fill="{PAPER if not hot else "#fff"}" stroke="{HOT if hot else RULE}" stroke-width="{1.2 if hot else 1}"/>')
    g.append(f'<text x="{x+16:.0f}" y="{y+26}" font-size="10.5" font-weight="700" letter-spacing=".08em" fill="{HOT if hot else MUTE}" {F}>{no}</text>')
    g.append(f'<text x="{x+16:.0f}" y="{y+50}" font-size="15px" font-weight="700" fill="{INK}" {F}>{title}</text>')
    g.append(f'<text x="{x+16:.0f}" y="{y+69}" font-size="12" fill="{SUB}" {F}>{sub}</text>')
    g.append(f'<line x1="{x+16:.0f}" y1="{y+82}" x2="{x+bw-16:.0f}" y2="{y+82}" stroke="{RULE}"/>')
    for j, it in enumerate(items):
        g.append(f'<text x="{x+16:.0f}" y="{y+106+j*21}" font-size="12" fill="{INK}" {F}>{it}</text>')
    if cidx < cols-1 and k < len(steps)-1:
        g.append(f'<line x1="{x+bw+2:.0f}" y1="{y+BH/2:.0f}" x2="{x+bw+gap-2:.0f}" y2="{y+BH/2:.0f}" stroke="#b5b5b0" stroke-width="1.2" marker-end="url(#a)"/>')
    if cidx == cols-1 and k < len(steps)-1:  # 줄바꿈 화살표: 오른쪽 끝 → 아래 왼쪽
        g.append(f'<path d="M{x+bw/2:.0f},{y+BH+2} L{x+bw/2:.0f},{y+BH+RG/2} L{bw/2:.0f},{y+BH+RG/2} L{bw/2:.0f},{y+BH+RG-2}" fill="none" stroke="#b5b5b0" stroke-width="1.2" marker-end="url(#a)"/>')
g.append("</svg>")
pipe = "".join(g)

# 아래: 데이터 출처 한 줄
src = [("나라장터 입찰공고 API", "공고·사전규격·발주계획 · 매일 05:00 / 12:30"), ("나라장터 업체정보 API", "등록업종·공급물품·면허·지역 · 일 4,500회 한도"), ("계약·낙찰 API", "수주 이력·낙찰가·참가업체 · 180일 백필"), ("OpenAI text-embedding-3-small", "1536차원 · 회사·공고 동일 공간")]
sw = (W - 18*3)/4; s2 = [f'<svg viewBox="0 0 {W} 70" width="100%" style="display:block">']
for k, (a, b) in enumerate(src):
    x = k*(sw+18)
    s2.append(f'<rect x="{x:.0f}" y="0" width="{sw:.0f}" height="70" rx="10" fill="#fff" stroke="{RULE}"/><text x="{x+14:.0f}" y="28" font-size="13" font-weight="650" fill="{INK}" {F}>{a}</text><text x="{x+14:.0f}" y="48" font-size="11.5" fill="{SUB}" {F}>{b}</text>')
s2.append("</svg>"); src_svg = "".join(s2)

html = f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>.pp *{{font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif;box-sizing:border-box}} .pp .box{{background:#fff;border:1px solid #d8d7d2;padding:26px 24px 22px}} .pp h2{{margin:0 0 4px;font-size:20px}} .pp p{{margin:0 0 20px;font-size:13px;color:#555;line-height:1.6;max-width:900px}} .pp h3{{margin:26px 0 10px;font-size:13px;color:#9a9a96;font-weight:600;letter-spacing:.06em}}</style>
<div class="pp"><div class="box">
<h2>추천은 이렇게 만들어집니다</h2>
<p>입력 → 회사 데이터 → 회사 벡터 → 오늘 공고 → 매칭 → 점수·정렬 → 결과. 숫자(가중치·점수)는 전부 지금 코드에 있는 값입니다. 인주 테두리 두 칸(회사 벡터, 점수·정렬)이 조달핏만의 부분입니다.</p>
{pipe}
<h3>데이터 출처</h3>{src_svg}
</div></div>'''
open(out, "w", encoding="utf-8").write(html); print("written", len(html))

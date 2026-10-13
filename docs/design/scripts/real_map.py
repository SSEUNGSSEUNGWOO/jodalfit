"""실제 임베딩으로 공고 지도. 활성 공고 전부 + 회사 벡터 + 코사인 TOP 38."""
import os, re, sys, json, math, collections
import numpy as np, psycopg, umap
from sklearn.cluster import KMeans

OUT = sys.argv[1]
OLD = [l.split("=",1)[1].strip() for l in open("C:/Dev/personal/jodalfit/backend/.env", encoding="utf-8") if l.startswith("DATABASE_URL=")][0]
conn = psycopg.connect(OLD, connect_timeout=20, options="-c statement_timeout=300000")
conn.execute("set client_encoding to 'UTF8'")

rows = conn.execute("""
  select bid_ntce_no, bid_ntce_nm, coalesce(bsns_div_nm,''), ntce_instt_nm, bid_clse_date::text, presmpt_prce, embedding::text
  from bid_notices where bid_clse_date >= current_date and embedding is not null""").fetchall()
print("notices", len(rows))
X = np.array([json.loads(r[6]) for r in rows], dtype=np.float32)
X /= np.linalg.norm(X, axis=1, keepdims=True)

comp = conn.execute("""select bizrno_norm, corp_nm, embedding::text, contract_count from companies
  where corp_nm ilike %s and embedding is not null limit 1""", ("%케이브레인컴퍼니%",)).fetchone()
if not comp:
    comp = conn.execute("""select bizrno_norm, corp_nm, embedding::text, contract_count from companies
      where embedding is not null and contract_count between 5 and 30 order by random() limit 1""").fetchone()
print("company", comp[0], comp[1], comp[3])
c = np.array(json.loads(comp[2]), dtype=np.float32); c /= np.linalg.norm(c)
sims = X @ c
top = np.argsort(-sims)[:38]

red = umap.UMAP(n_neighbors=25, min_dist=0.08, metric="cosine", random_state=7)
Y = red.fit_transform(X)
cy = red.transform(c[None, :])[0]
print("umap done")

# 군집 라벨: KMeans 14 + 제목 빈출 단어
k = 14
km = KMeans(n_clusters=k, n_init=4, random_state=7).fit(Y)
STOP = set("및 외 등 년 월 구매 용역 사업 공사 제작 설치 운영 관리 위탁 구입 납품 공급 2026년 2027년 제 차 건 1 2 3 the of".split())
labels = []
for ci in range(k):
    idx = np.where(km.labels_ == ci)[0]
    words = collections.Counter()
    for i in idx:
        for w in re.split(r"[\s()\[\]·,/]+", rows[i][1]):
            w = re.sub(r"^\d+[년월차호]?$", "", w)
            if len(w) >= 2 and w not in STOP: words[w] += 1
    top2 = [w for w, _ in words.most_common(2)]
    labels.append((Y[idx, 0].mean(), Y[idx, 1].mean(), " · ".join(top2), len(idx)))

# 정규화 → SVG
W, H, pad = 1120, 640, 40
mn, mx = Y.min(0), Y.max(0)
def P(p): return pad + (p[0]-mn[0])/(mx[0]-mn[0])*(W-2*pad), pad + (p[1]-mn[1])/(mx[1]-mn[1])*(H-2*pad)
INK, HOT, MUTE, SUB = "#141414", "#e8431b", "#8a8a86", "#5c5c58"
FONT = 'font-family="Pretendard Variable,Pretendard,sans-serif"'
s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block;overflow:visible"><defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter></defs>']
topset = set(top.tolist())
for i, p in enumerate(Y):
    if i in topset: continue
    x, y = P(p); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="{INK}" opacity=".16"/>')
for lx, ly, lab, n in labels:
    x, y = P((lx, ly)); s.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="11.5" font-weight="600" letter-spacing=".02em" fill="{SUB}" text-anchor="middle" {FONT}>{lab}</text><text x="{x:.0f}" y="{y+13:.0f}" font-size="10" fill="{MUTE}" text-anchor="middle" {FONT}>{n:,}</text>')
for i in top:
    x, y = P(Y[i]); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{HOT}" opacity=".3" filter="url(#bl)"/><circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{HOT}"/>')
x, y = P(cy)
s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{INK}"/><circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="none" stroke="{INK}" stroke-width=".9" opacity=".6"/><text x="{x+22:.0f}" y="{y+4:.0f}" font-size="13" font-weight="700" fill="{INK}" {FONT}>{comp[1]}</text>')
s.append("</svg>")
svg = "".join(s)

def fmt(p):
    if p is None: return "—"
    p = float(p); return f"{p/1e8:.1f}억" if p >= 1e8 else f"{p/1e4:,.0f}만"
rowhtml = "".join(f'<div style="display:grid;grid-template-columns:28px 1fr 150px 90px 60px;gap:0 14px;padding:9px 0;border-bottom:1px solid #e8e6e1;font-size:13px"><span style="color:{MUTE};font-size:11.5px">{k+1:02d}</span><span style="font-weight:600;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{rows[i][1]}</span><span style="color:{SUB};font-size:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{rows[i][3]}</span><span style="text-align:right">{fmt(rows[i][5])}</span><span style="text-align:right;color:{HOT};font-weight:600">{sims[i]:.2f}</span></div>' for k, i in enumerate(top[:12]))

html = f'''<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>.rm *{{box-sizing:border-box;font-family:"Pretendard Variable",Pretendard,system-ui,sans-serif}}</style>
<div class="rm">
<h2>실제 데이터 — 활성 공고 {len(rows):,}건의 지도</h2>
<p class="subtitle">가짜 점이 아닙니다. 오늘 진행 중인 공고 {len(rows):,}건의 임베딩을 UMAP으로 2D 투영했고, 군집 라벨은 각 군집 공고명의 빈출 단어 2개를 자동으로 뽑은 것입니다. 검정 점이 <b>{comp[1]}</b>(수주 {comp[3]}건)의 벡터 위치, 인주 점이 코사인 유사도 상위 38건입니다.</p>
<div style="background:#fbfaf7;border:1px solid #d8d7d2;padding:28px 24px 10px">{svg}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:26px">
 <div><h3 style="margin:0 0 8px">상위 12건 (유사도)</h3>{rowhtml}</div>
 <div><h3 style="margin:0 0 8px">읽는 법</h3>
  <p style="font-size:13.5px;line-height:1.7;color:{SUB}">군집은 데이터가 스스로 만든 것입니다. 급식 식재료, SW 유지보수, 하수도 공사가 각자 모여 있고, 라벨은 손으로 붙인 게 아니라 공고명에서 나왔습니다.<br><br>인주 점이 한 군데에 뭉치면 "한 분야 회사", 두세 군데로 갈라지면 "다부서 회사"입니다. 이 그림 하나가 추천 근거 설명을 대신합니다.<br><br>세련됨은 여기서 점 크기·농도·여백·라벨 타이포로 만듭니다. 장식이 아니라 실제 구조라서, 매일 다시 그려도 거짓이 되지 않습니다.</p></div></div>
</div>'''
open(OUT, "w", encoding="utf-8").write(html)
print("written", OUT)

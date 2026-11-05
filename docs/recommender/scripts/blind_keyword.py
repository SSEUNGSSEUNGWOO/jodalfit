"""키워드 모드 블라인드 비교 — 실사용자 질의 40개를 두 임베딩 공간으로 돌려 좌우 무작위 페이지를 만든다.

1) collect: 공간 하나로 recommend() 를 돌려 JSON 저장 (EMBED_SPACE 환경변수로 공간 선택, 두 번 실행)
   cd backend && EMBED_SPACE=kure   uv run python ../docs/recommender/scripts/blind_keyword.py collect data/emb_rematch/blind-kure.json
   cd backend && EMBED_SPACE=gemini uv run python ../docs/recommender/scripts/blind_keyword.py collect data/emb_rematch/blind-gemini.json
2) page: 두 JSON → HTML(좌우 무작위) + 정답 키
   uv run python ../docs/recommender/scripts/blind_keyword.py page data/emb_rematch/blind-kure.json data/emb_rematch/blind-gemini.json data/emb_rematch/blind.html

질의는 search_logs 의 실사용자(source='user') 키워드 질의 최근 90일에서 seed 고정으로 40개. 의미 유사 판("그 밖에")만 비교한다 —
제목 일치 판은 임베딩과 무관해 양쪽이 같다.
"""

from __future__ import annotations

import html
import json
import os
import random
import sys

N = 40
SEED = 7


def collect(out: str) -> None:
    import psycopg
    from dotenv import load_dotenv

    load_dotenv(".env")
    from app.services.recommend import recommend

    with psycopg.connect(os.environ["DATABASE_URL"]) as c:
        rows = c.execute(
            """select query, count(*) from search_logs
                where source = 'user' and mode in ('keywords', 'auto') and created_at >= now() - interval '90 days'
                  and length(query) between 2 and 40 and query !~ '^[0-9-]+$'
                group by query order by count(*) desc, query limit 300"""
        ).fetchall()
    qs = [q for q, _ in rows]
    random.Random(SEED).shuffle(qs)
    qs = qs[:N]
    space = os.environ.get("EMBED_SPACE")
    items = []
    for i, q in enumerate(qs, 1):
        r = recommend(q, limit=20, candidate_pool=200, mode="keywords", algorithm="v2")
        items.append({"q": q, "results": [{"no": x.get("bid_ntce_no"), "title": x.get("bid_ntce_nm"), "div": x.get("bsns_div_nm"),
                                            "instt": x.get("dmnd_instt_nm") or x.get("ntce_instt_nm"), "close": str(x.get("bid_clse_date") or "")}
                                           for x in (r.get("results") or [])[:20]],
                      "title_matches": len(r.get("title_matches") or [])})
        print(f"  {i:2d}/{len(qs)} {q} → {len(items[-1]['results'])}", flush=True)
    json.dump({"space": space, "items": items}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {out} ({space})")


def page(a_path: str, b_path: str, out: str) -> None:
    A, B = json.load(open(a_path, encoding="utf-8")), json.load(open(b_path, encoding="utf-8"))
    rng = random.Random(SEED + 1)
    key = []
    blocks = []
    for i, (ia, ib) in enumerate(zip(A["items"], B["items"]), 1):
        assert ia["q"] == ib["q"]
        flip = rng.random() < 0.5
        left, right = (ib, ia) if flip else (ia, ib)
        key.append({"n": i, "q": ia["q"], "left": B["space"] if flip else A["space"], "right": A["space"] if flip else B["space"]})

        def col(it: dict) -> str:
            rows = "".join(
                f"<li><span class='t'>{html.escape(x['title'] or '')}</span><span class='m'>{html.escape(x['div'] or '')} · {html.escape(x['instt'] or '')} · 마감 {html.escape(x['close'])}</span></li>"
                for x in it["results"]
            ) or "<li class='empty'>결과 없음</li>"
            return f"<ol>{rows}</ol>"

        blocks.append(
            f"<section id='q{i}'><h2>{i}. {html.escape(ia['q'])}</h2>"
            f"<p class='s'>제목 일치 {ia['title_matches']}건은 양쪽 같아 뺐습니다. 아래는 의미 유사 20건.</p>"
            f"<div class='pair'><div><h3>왼쪽</h3>{col(left)}</div><div><h3>오른쪽</h3>{col(right)}</div></div>"
            f"<div class='vote'><label><input type='radio' name='v{i}' value='L'> 왼쪽이 낫다</label>"
            f"<label><input type='radio' name='v{i}' value='R'> 오른쪽이 낫다</label>"
            f"<label><input type='radio' name='v{i}' value='T'> 비슷하다</label></div></section>"
        )
    doc = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>키워드 블라인드 비교</title>
<style>body{{font-family:Pretendard,'Malgun Gothic',sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;line-height:1.5;color:#1f1d1a}}
h2{{font-size:18px;margin:32px 0 4px}} h3{{font-size:13px;color:#6b655c;margin:0 0 6px}} .s{{font-size:12px;color:#6b655c;margin:0 0 8px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} ol{{margin:0;padding-left:20px;font-size:13px}} li{{margin:0 0 6px}}
.t{{display:block}} .m{{display:block;font-size:11px;color:#6b655c}} .empty{{color:#6b655c;list-style:none}}
.vote{{margin:10px 0 0;display:flex;gap:16px;font-size:13px}} .vote label{{border:1px solid #d9d3ca;border-radius:4px;padding:4px 10px;cursor:pointer}}
#sum{{position:sticky;top:0;background:#fff;border-bottom:2px solid #f97316;padding:8px 0;font-size:13px}}
textarea{{width:100%;height:80px;font-family:monospace;font-size:12px}}</style></head><body>
<div id='sum'>투표: <span id='cnt'>0</span>/{len(blocks)} · 끝나면 아래 "결과 복사" 칸의 글을 저에게 주시면 됩니다.</div>
<p>질의마다 왼쪽·오른쪽 중 "입찰 검토 대상으로 더 쓸모 있는 쪽"을 고르십시오. 어느 쪽이 어느 모델인지는 질의마다 무작위입니다.</p>
{''.join(blocks)}
<h2>결과 복사</h2><textarea id='out' readonly></textarea>
<script>
const n={len(blocks)};function upd(){{const v=[];let c=0;for(let i=1;i<=n;i++){{const r=document.querySelector(`input[name=v${{i}}]:checked`);v.push(r?r.value:'-');if(r)c++;}}
document.getElementById('cnt').textContent=c;document.getElementById('out').value=v.join('');}}
document.querySelectorAll('input[type=radio]').forEach(r=>r.addEventListener('change',upd));upd();
</script></body></html>"""
    open(out, "w", encoding="utf-8").write(doc)
    json.dump(key, open(out.replace(".html", "-key.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {out} (+ key)")


def score(key_path: str, votes: str) -> None:
    """votes = 'LRT-…' 40글자. 공간별 승·패·무."""
    key = json.load(open(key_path, encoding="utf-8"))
    tally: dict[str, int] = {}
    for k, v in zip(key, votes):
        if v == "L":
            tally[k["left"]] = tally.get(k["left"], 0) + 1
        elif v == "R":
            tally[k["right"]] = tally.get(k["right"], 0) + 1
        elif v == "T":
            tally["tie"] = tally.get("tie", 0) + 1
    print(tally)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "collect":
        collect(sys.argv[2])
    elif cmd == "page":
        page(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "score":
        score(sys.argv[2], sys.argv[3])

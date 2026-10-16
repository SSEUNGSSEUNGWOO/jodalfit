"""결과 페이지 시안의 원천 데이터 — `data/` 에 커밋한다(임시 파일에 두었다가 사라진 2026-10-16 사고 재발 방지).

  sample.json       recommend('한종산업개발', 12, pool 100, company, v2) 응답. 200자 넘는 값(raw·임베딩 등)은 뺀다.
  funnel.json       지금 입찰 가능(마감 90일 이내) / 등록업종 허용 / 자격 통과 / 결과 — 네 칸.
  scene_titles.json 머리 장면 캔버스 위 공고명: 업종에서 막힌 6건, 지역·면허에서 막힌 3건.

사용: cd backend && KURE_BACKEND=torch PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_data.py ../docs/design/data
"""
import json
import random
import sys
from pathlib import Path

from app.recommender.qualifications import check_qualifications
from app.services.recommend import recommend
from jobs.evaluate_recommender import connect, fetch_company_profile, fetch_limits

COMPANY, LIMIT, POOL, MAXLEN = "한종산업개발", 12, 100, 200
KEEP = {"bidprc_psbl_indstryty_nm"}  # 허용업종 목록은 길어도 시안이 읽는다


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not (isinstance(v, str) and len(v) > MAXLEN and k not in KEEP)}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def funnel(conn, prof, n_res):
    rows = conn.execute("""select bid_ntce_no, bid_ntce_ord, bid_ntce_nm, bidprc_psbl_indstryty_nm, prtcpt_psbl_rgn_nm
                           from bid_notices where bid_clse_date between current_date and current_date + 90""").fetchall()
    names = prof["names"]
    ind = [r for r in rows if any(n in (r[3] or "") for n in names)]
    lim = fetch_limits(conn, [(r[0], r[1]) for r in ind])
    q = {r[0]: check_qualifications(names, prof["rgn"], *(lambda s: (s["licenses"], s["regions"]))(lim.get((r[0], r[1])) or {"licenses": [], "regions": []}))
         for r in ind}
    f = dict(total=len(rows), industry=len(ind), qualified=sum(1 for v in q.values() if v["passed"]), result=n_res)
    rnd = random.Random(7)
    drop_ind = rnd.sample([r[2] for r in rows if r not in ind and r[2]], 6)
    drop_rgn = rnd.sample([r[2] for r in ind if not q[r[0]]["passed"] and any("지역" in x for x in q[r[0]]["failures"])], 3)
    return f, dict(drop_ind=drop_ind, drop_rgn=drop_rgn)


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
    d = strip(json.loads(json.dumps(recommend(COMPANY, limit=LIMIT, candidate_pool=POOL, mode="company", algorithm="v2"), default=str)))
    conn = connect()
    prof = fetch_company_profile(conn, "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit()))
    f, titles = funnel(conn, prof, len(d["results"]))
    for name, obj in (("sample.json", d), ("funnel.json", f), ("scene_titles.json", titles)):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f, titles)

"""결과 페이지 시안의 원천 데이터 — `data/` 에 커밋한다(임시 파일에 두었다가 사라진 2026-10-16 사고 재발 방지).

  sample.json       recommend('한종산업개발', 12, pool 100, company, v2) 응답. 200자 넘는 값(raw·임베딩 등)은 뺀다.
  funnel.json       지금 입찰 가능 / 비슷한 순서로 추린 후보 / 자격 통과 / 결과 — 네 칸.
                    **운영 파이프라인을 그대로 재생해서 얻는다**(progress 이벤트). 예전에는 여기서
                    "전체 → 등록업종 허용 → 그 안에서 자격 통과"를 직접 세었는데, 운영은 그렇게 돌지
                    않는다 — 유사도로 후보를 추린 뒤 그 안에서 자격을 본다. 2026-10-23 확인: 최종
                    20건 중 8건이 등록업종 허용 목록 밖이었다. 시안 숫자가 낡은 게 아니라 애초에
                    다른 파이프라인의 숫자였다.
  scene_titles.json 머리 장면 캔버스 위 공고명 (폐기된 flow/scene 시안 전용).

사용: cd backend && KURE_BACKEND=torch PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python ../docs/design/scripts/gen_data.py ../docs/design/data
"""
import json
import random
import sys
from datetime import date
from pathlib import Path

from app.core import progress
from app.services.recommend import recommend
from jobs.evaluate_recommender import connect, fetch_company_profile

# 운영 결과 페이지와 같은 조건 — 시안 숫자가 화면과 달라지면 안 된다(ResultsView.tsx 의 RESULT_LIMIT·candidate_pool).
COMPANY, LIMIT, POOL, MAXLEN = "한종산업개발", 20, 200, 200
KEEP = {"bidprc_psbl_indstryty_nm"}  # 허용업종 목록은 길어도 시안이 읽는다


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not (isinstance(v, str) and len(v) > MAXLEN and k not in KEEP)}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def funnel(conn, prof, events, n_res):
    """운영이 실제로 센 수를 쓴다 — events 는 recommend() 를 돌리며 모은 progress 이벤트다.

    total     지금 입찰 가능(마감 90일 이내 · 벡터 있음 · 참가자격 등록 안 지남) — 0057 funnel_counts
    candidate 비슷한 순서로 추린 후보 (stage=search)
    qualified 그중 면허·지역 통과 (stage=qualify)
    result    화면에 나가는 건수
    네 칸이 앞 칸의 부분집합이라 깔때기로 그려도 거짓이 아니다.
    """
    by = {}
    for e in events:
        if e["type"] == "funnel":
            by["total"] = e.get("total")
        elif e["type"] == "stage" and e.get("stage") == "search":
            by["candidate"] = e.get("candidates")
        elif e["type"] == "stage" and e.get("stage") == "qualify":
            by["candidate"] = e.get("candidates", by.get("candidate"))
            by["qualified"] = e.get("passed")
    if by.get("total") is None:  # 0057 미적용 환경 — 같은 정의로 직접 센다
        by["total"] = conn.execute("""select count(*) from bid_notices
                                       where bid_clse_date between current_date and current_date + 90
                                         and embedding_k is not null
                                         and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > now())""").fetchone()[0]
    f = dict(total=by["total"], candidate=by.get("candidate"), qualified=by.get("qualified"), result=n_res)
    assert all(v is not None for v in f.values()), f
    assert f["total"] >= f["candidate"] >= f["qualified"] >= f["result"], f  # 포함 관계가 깨지면 깔때기가 거짓이다

    # 탈락 예시 공고명 — 폐기된 flow/scene 시안 전용이다. 파이프라인 밖에서는 어느 점이 어느 관문에서
    # 떨어졌는지 알 수 없으므로(후보 풀 id 를 돌려주지 않는다) '추린 200 밖' 과 '업종 불일치'로만 나눈다.
    rows = conn.execute("""select bid_ntce_nm, bidprc_psbl_indstryty_nm from bid_notices
                            where bid_clse_date between current_date and current_date + 90
                              and embedding_k is not null and bid_ntce_nm is not null
                              and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > now())""").fetchall()
    names = prof["names"]
    rnd = random.Random(7)
    off = [r[0] for r in rows if not any(n in (r[1] or "") for n in names)]
    on = [r[0] for r in rows if any(n in (r[1] or "") for n in names)]
    return f, dict(drop_ind=rnd.sample(off, min(6, len(off))), drop_rgn=rnd.sample(on, min(3, len(on))))


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
    events: list[dict] = []
    tok = progress.set_callback(events.append)  # 운영이 머리 장면에 쏘는 그 이벤트를 그대로 받는다
    try:
        raw = recommend(COMPANY, limit=LIMIT, candidate_pool=POOL, mode="company", algorithm="v2")
    finally:
        progress.reset(tok)
    d = strip(json.loads(json.dumps(raw, default=str)))
    conn = connect()
    biz = "".join(ch for ch in d["company"]["bizrno"] if ch.isdigit())
    prof = fetch_company_profile(conn, biz, date.today())
    f, titles = funnel(conn, prof, events, len(d["results"]))
    for name, obj in (("sample.json", d), ("funnel.json", f), ("scene_titles.json", titles)):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f, titles)

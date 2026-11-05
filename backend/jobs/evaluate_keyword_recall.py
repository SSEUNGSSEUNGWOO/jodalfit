"""키워드 모드 채점표 — 사전규격·발주계획이 나중에 어느 공고로 전환됐는지(bid_ntce_no_list)를 정답으로 쓴다.

회사 모드 채점표(evaluate_recommender)는 낙찰 기록이 정답이라 키워드 질의를 못 쟀다(2026-11-05 Codex 검토 지적).
사전규격 47,952건·발주계획 5,786건이 "이 사업은 이 공고가 됐다" 연결을 갖고 있어, 사업명을 질의로 넣고
전환된 공고가 의미 유사 20건 안에 드는지 세면 사람이 치는 짧은 질의와 같은 꼴의 정답지가 된다.

- 시점 t: 활성 공고 집합은 evaluate_recommender.fetch_active_notices(운영 RPC 조건과 동일, 벡터 열은 --space).
- 질의 둘: full = 사업명 그대로 / short = 연도·괄호·기관 꼬리를 떼고 끝 3낱말(사용자가 치는 "전산장비 유지보수 용역" 꼴).
- 의미 유사 채널만 잰다(제목 일치 판은 임베딩과 무관). 질의 임베딩은 운영과 같은 "관심 영역: {expand_keywords(q)}", kind="query".
- 지표: hit@5·hit@20·MRR(정답 공고가 여럿이면 가장 앞 순위).

실행: cd backend && uv run python -m jobs.evaluate_keyword_recall --as-of 2026-08-01 --space kure --n 500 --seed 7
결과: backend/data/recommender_eval/kw-<space>-<date>/metrics.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from app.recommender.keyword_expand import expand_keywords
from app.services.embedding import emb_col, embed_texts
from jobs import evaluate_recommender as er

_YEAR = re.compile(r"^\d{4}년?(도|학년도)?$|^\d{4}~\d{4}$|^\(.*\)$|^\[.*\]$")


def short_query(name: str) -> str:
    """'대구동부고 2027학년도 교복(동복, 하복) 학교주관구매' → '교복 학교주관구매' 꼴. 괄호 안·연도·앞쪽 기관명을 떼고 끝 3낱말."""
    s = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", name)
    toks = [t for t in re.split(r"[\s,/·]+", s) if t and not _YEAR.match(t)]
    return " ".join(toks[-3:]) if len(toks) > 3 else " ".join(toks)


def fetch_queries(conn, t: date, active_keys: set[str], n: int, seed: int) -> list[dict]:
    """t 이전 등록 + 전환 공고가 t 활성 집합에 있는 사전규격·발주계획. 공고번호는 앞 13자리(발주계획은 차수 3자리가 붙는다)."""
    rows = conn.execute(
        """select 'pre_spec' as src, bf_spec_rgst_no, prdct_clsfc_no_nm, bid_ntce_no_list from pre_specs
            where coalesce(bid_ntce_no_list,'') <> '' and rgst_dt < %s and rgst_dt >= %s - interval '120 days'
           union all
           select 'order_plan', order_plan_unty_no, biz_nm, bid_ntce_no_list from order_plans
            where coalesce(bid_ntce_no_list,'') <> ''""",
        (t, t),
    ).fetchall()
    out = []
    for src, key, name, lst in rows:
        if not name or len(name.strip()) < 4:
            continue
        nos = {x.strip()[:13] for x in lst.split(",") if x.strip()}
        answers = nos & active_keys
        if answers:
            out.append({"src": src, "key": key, "name": name.strip(), "answers": sorted(answers)})
    random.Random(seed).shuffle(out)
    return out[:n]


def rank_hits(sims: np.ndarray, nos: list[str], answers: set[str], k: int) -> int | None:
    """정답 공고가 처음 나오는 순위(1부터, 같은 공고번호의 차수는 하나로 센다). 없으면 None."""
    order = np.argsort(-sims)
    seen: set[str] = set()
    rank = 0
    for i in order:
        no = nos[i]
        if no in seen:
            continue
        seen.add(no)
        rank += 1
        if no in answers:
            return rank
        if rank >= k:
            return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--space", choices=["openai", "kure", "gemini"], required=True)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--no-prefix", action="store_true", help='운영의 "관심 영역: " 접두어·약어 풀이 없이 질의 원문만 임베딩 (접두어가 모델마다 득실이 다른지 확인용)')
    ap.add_argument("--expand-only", action="store_true", help='약어 풀이(expand_keywords)는 하되 "관심 영역: " 접두어만 뺀다')
    args = ap.parse_args()
    t = date.fromisoformat(args.as_of)
    horizon = t + timedelta(days=er.HORIZON_DAYS)
    er.EMB_SPACE, er.EMB_COL = args.space, emb_col(args.space)
    conn = er.connect()
    notices, X = er.fetch_active_notices(conn, t, horizon)
    nos = [r["bid_ntce_no"] for r in notices]
    queries = fetch_queries(conn, t, set(nos), args.n, args.seed)
    if not queries:
        raise SystemExit("질의 0건")
    print(f"[kw] t={t} space={args.space} active={len(notices):,} queries={len(queries)} "
          f"(pre_spec {sum(q['src']=='pre_spec' for q in queries)} / order_plan {sum(q['src']=='order_plan' for q in queries)})", flush=True)

    results = {}
    for variant in ("full", "short"):
        texts = [q["name"] if variant == "full" else short_query(q["name"]) for q in queries]
        prompts = texts if args.no_prefix else [expand_keywords(x) for x in texts] if args.expand_only else [f"관심 영역: {expand_keywords(x)}" for x in texts]
        Q = np.zeros((len(prompts), X.shape[1]), dtype=np.float32)
        for s in range(0, len(prompts), 100):
            Q[s : s + 100] = np.array(embed_texts(prompts[s : s + 100], space=args.space, kind="query"), dtype=np.float32)
        Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
        S = Q @ X.T
        ranks = [rank_hits(S[i], nos, set(q["answers"]), 20) for i, q in enumerate(queries)]
        n = len(ranks)
        results[variant] = {
            "n": n,
            "hit5": sum(1 for r in ranks if r is not None and r <= 5) / n,
            "hit20": sum(1 for r in ranks if r is not None) / n,
            "mrr20": sum(1 / r for r in ranks if r is not None) / n,
            "by_src": {src: {"n": sum(1 for q in queries if q["src"] == src),
                             "hit20": (sum(1 for q, r in zip(queries, ranks) if q["src"] == src and r is not None)
                                       / max(1, sum(1 for q in queries if q["src"] == src)))}
                       for src in ("pre_spec", "order_plan")},
            "examples": [{"q": texts[i], "rank": ranks[i], "answer_title": next((r["bid_ntce_nm"] for r in notices if r["bid_ntce_no"] in q["answers"]), None)}
                         for i, q in list(enumerate(queries))[:8]],
        }
        print(f"  {variant:5s} hit@5 {results[variant]['hit5']:.3f}  hit@20 {results[variant]['hit20']:.3f}  MRR {results[variant]['mrr20']:.3f}", flush=True)

    run_id = args.run_id or f"kw-{args.space}{'-noprefix' if args.no_prefix else '-expandonly' if args.expand_only else ''}-{t.strftime('%Y%m%d')}"
    out_dir = Path(__file__).resolve().parents[1] / "data" / "recommender_eval" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps({"as_of": t.isoformat(), "space": args.space, "active": len(notices),
                                                        "n": len(queries), "seed": args.seed, **results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[kw] → {out_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()

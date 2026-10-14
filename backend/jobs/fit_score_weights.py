"""점수표 재보정 도구 — 채점표의 features.csv 로 특징 lift 와 회사 내 로지스틱 계수를 구하고, 점수표 후보를 held-out 비교한다.

사용:
  uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --dump-features --run-id feat-0801
  uv run python -m jobs.fit_score_weights data/recommender_eval/feat-0801 data/recommender_eval/feat-0901 [...]
    → 첫 run 으로 적합, 나머지 run 에서 held-out 평가. 지표는 자격 통과 풀 안에서의 recall@30/@5·MRR(회사 macro).

원리: 특징을 회사 안에서 중심화(회사 평균 빼기)한 뒤 로지스틱 회귀 → 회사 간 유사도 수준 차이에 휘둘리지 않는
'같은 회사 안에서 어느 후보가 낙찰 공고인가' 계수. 계수를 유사도 1%p = 1점 기준으로 환산해 5점 단위 점수표로 만든다.
2026-10-14 재보정 근거: docs/recommender/exp-2026-10-14-score.md
"""
from __future__ import annotations

import collections
import csv
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BIN = ["institution", "instt_closed", "instt_open", "region", "budget", "budget_mismatch", "deadline_urgent", "deadline_ok",
       "industry_name_match", "has_allowed"]
NAMES = ["sim"] + BIN + ["ind_tokens"]

# 운영 점수표 (score.py 와 같아야 한다). 비교 기준.
CURRENT = dict(institution=40, instt_closed=-10, instt_open=0, region=30, budget=5, budget_mismatch=-5, deadline_urgent=-30,
               deadline_ok=0, industry_name_match=0, has_allowed=0, ind_tokens=10)


def load(run: str) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{run}/features.csv", encoding="utf-8")):
        by[r["biz"]].append(r)
    return by


def _on(r: dict, k: str) -> float:
    return 1.0 if float(r.get(k, 0) or 0) != 0 else 0.0


def feats(r: dict) -> list[float]:
    return [float(r["sim"]) * 100] + [_on(r, k) for k in BIN] + [min(float(r.get("industry_tokens", 0) or 0) / 10, 3)]


def metrics(by: dict, scorer) -> dict:
    per = []
    for rows in by.values():
        pos = {r["bid_ntce_no"] for r in rows if r["is_pos"] == "1"}
        if not pos:
            continue
        order = np.argsort(-np.asarray(scorer(rows)), kind="stable")
        seen: set[str] = set(); uniq: list[str] = []
        for i in order:
            n = rows[i]["bid_ntce_no"]
            if n not in seen:
                seen.add(n); uniq.append(n)
        per.append({"tier": rows[0]["tier"], "r30": len(set(uniq[:30]) & pos) / len(pos), "r5": len(set(uniq[:5]) & pos) / len(pos),
                    "mrr": next((1 / (i + 1) for i, n in enumerate(uniq) if n in pos), 0.0)})
    out: dict = {"n": len(per)}
    for grp in ("all", "cold", "small", "rich"):
        sel = [p for p in per if grp == "all" or p["tier"] == grp]
        out[grp] = {m: (sum(p[m] for p in sel) / len(sel) if sel else float("nan")) for m in ("r30", "r5", "mrr")}
    return out


def points_scorer(table: dict):
    def f(rows):
        return [100 * float(r["sim"]) + sum(table[k] * _on(r, k) for k in BIN)
                + table["ind_tokens"] * min(float(r.get("industry_tokens", 0) or 0) / 10, 3) for r in rows]
    return f


def lift(by: dict) -> None:
    tot: collections.Counter = collections.Counter(); pos: collections.Counter = collections.Counter()
    for rows in by.values():
        for r in rows:
            for k in BIN + ["industry_tokens"]:
                on = float(r.get(k, 0) or 0) != 0
                tot[(k, on)] += 1; pos[(k, on)] += r["is_pos"] == "1"
    print(f"{'feature':20}{'n_on':>7}{'P(pos|on)':>11}{'P(pos|off)':>11}{'lift':>7}")
    for k in BIN + ["industry_tokens"]:
        p_on = pos[(k, True)] / max(tot[(k, True)], 1); p_off = pos[(k, False)] / max(tot[(k, False)], 1)
        print(f"{k:20}{tot[(k, True)]:7}{p_on:11.4f}{p_off:11.4f}{(p_on / p_off if p_off else float('nan')):7.2f}")


def fit(by: dict, l2: float = 1.0, iters: int = 4000, lr: float = 0.05) -> dict[str, float]:
    """회사 내 중심화 로지스틱(고정효과 근사). 반환: 특징별 점수(sim 1%p = 1점 기준)."""
    X, y, w_s = [], [], []
    for rows in by.values():
        npos = sum(r["is_pos"] == "1" for r in rows)
        if not npos or npos == len(rows):
            continue
        F = np.asarray([feats(r) for r in rows]); F = F - F.mean(0)
        for r, f in zip(rows, F):
            X.append(f); y.append(float(r["is_pos"]))
            w_s.append(1.0 if r["is_pos"] == "1" else npos / max(len(rows) - npos, 1))  # 회사별 양·음성 균형
    Xa, ya, wa = np.asarray(X), np.asarray(y), np.asarray(w_s)
    sd = Xa.std(0) + 1e-9; Z = Xa / sd
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z @ w)))
        w -= lr * ((wa * (p - ya)) @ Z / wa.sum() + l2 * w / len(ya))
    raw = w / sd
    return {n: float(v) for n, v in zip(NAMES, raw / raw[0])}


def show(label: str, m: dict) -> None:
    g = lambda grp, k: m[grp][k]  # noqa: E731
    print(f"{label:28} n={m['n']:3} | all r30 {g('all','r30'):.3f} r5 {g('all','r5'):.3f} mrr {g('all','mrr'):.3f}"
          f" | cold r30 {g('cold','r30'):.3f} r5 {g('cold','r5'):.3f} | small r30 {g('small','r30'):.3f} r5 {g('small','r5'):.3f}"
          f" | rich r30 {g('rich','r30'):.3f} r5 {g('rich','r5'):.3f}")


def main() -> None:
    runs = sys.argv[1:]
    if len(runs) < 2:
        sys.exit(__doc__)
    data = {r: load(r) for r in runs}
    print(f"== lift ({runs[0]})"); lift(data[runs[0]])
    pts = fit(data[runs[0]])
    fitted = {k: (int(5 * round(v / 5)) if k != "sim" else 1.0) for k, v in pts.items()}
    print(f"\n== fitted table ({runs[0]}; sim 1%p = 1점, 5점 단위)")
    for k in NAMES[1:]:
        print(f"  {k:20} raw {pts[k]:+7.1f} -> {fitted[k]:+4d}   (current {CURRENT[k]:+d})")
    print()
    for r in runs:
        tag = "fit" if r == runs[0] else "held-out"
        show(f"current  {r[-9:]} ({tag})", metrics(data[r], points_scorer(CURRENT)))
        show(f"fitted   {r[-9:]} ({tag})", metrics(data[r], points_scorer(fitted)))


if __name__ == "__main__":
    main()

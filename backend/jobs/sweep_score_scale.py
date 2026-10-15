"""보너스 배율 한 개를 특징 파일 위에서 훑는다 — 평가를 다시 돌리지 않고.

점수 = 유사도×100 + k × (보너스 합). 항목 간 상대 비율은 2026-10-14 재보정 값을 그대로 두고
k 하나만 움직인다. 파라미터가 하나라 과적합할 자유도가 거의 없다.

왜 배율이냐: 임베딩 모델을 바꾸면 유사도가 퍼진 정도가 달라진다. 점수표는 '유사도 1%p = 1점'
으로 환산해 만든 것이므로, 폭이 줄면 같은 보너스가 상대적으로 더 세진다. KURE 는 회사 안
1위~30위 폭이 OpenAI 의 0.636 배다(2026-10-15 실측).

주의: 지표는 fit_score_weights 와 같이 '자격 통과 풀 안에서의' recall 이라 하네스 숫자와
denominator 가 다르다. 안끼리 비교하는 용도이고, 고른 k 는 하네스로 한 번 확인해야 한다.

실행:
    cd backend
    uv run python -m jobs.sweep_score_scale data/recommender_eval/<run1> data/recommender_eval/<run2> ...
"""

from __future__ import annotations

import sys

from jobs.fit_score_weights import CURRENT, load, metrics, points_scorer

SCALES = [round(0.05 * i, 2) for i in range(0, 31)]  # 0.00 ~ 1.50


def scaled(k: float) -> dict:
    return {name: pts * k for name, pts in CURRENT.items()}


def main() -> None:
    runs = sys.argv[1:]
    if not runs:
        sys.exit(__doc__)
    data = [(r.rstrip("/\\").split("/")[-1].split("\\")[-1], load(r)) for r in runs]

    print("배율별 지표 (자격 통과 풀 기준, 시점별)\n")
    header = "  k   " + "".join(f"| {nm[:12]:^26} " for nm, _ in data) + "|  평균 r30  평균 mrr"
    print(header)
    print("      " + "".join("|   r30     r5    mrr      " for _ in data) + "|")
    best = None
    for k in SCALES:
        sc = points_scorer(scaled(k))
        cells, r30s, mrrs = "", [], []
        for _, by in data:
            m = metrics(by, sc)
            a = m["all"]
            cells += f"| {a['r30']:.3f}  {a['r5']:.3f}  {a['mrr']:.3f}   "
            r30s.append(a["r30"])
            mrrs.append(a["mrr"])
        avg30, avgmrr = sum(r30s) / len(r30s), sum(mrrs) / len(mrrs)
        mark = ""
        if best is None or avg30 + avgmrr > best[1]:
            best, mark = (k, avg30 + avgmrr), " <"
        print(f" {k:4.2f} {cells}|  {avg30:.4f}   {avgmrr:.4f}{mark}")

    k = best[0]
    print(f"\n평균 r30+mrr 최대: k = {k:.2f}")
    print("\n군별 (k=1.00 현재 → 위 최적):")
    for nm, by in data:
        cur, new = metrics(by, points_scorer(scaled(1.0))), metrics(by, points_scorer(scaled(k)))
        for g in ("all", "cold", "small", "rich"):
            c, n = cur[g], new[g]
            flag = "" if n["r30"] >= c["r30"] - 1e-9 else "  ↓"
            print(f"  {nm:16} {g:5} r30 {c['r30']:.3f} → {n['r30']:.3f}   mrr {c['mrr']:.3f} → {n['mrr']:.3f}{flag}")

    print(f"\n운영 점수표로 옮기려면 각 항목에 {k:.2f} 를 곱한다:")
    for name, pts in CURRENT.items():
        if pts:
            print(f"  {name:20} {pts:+4} → {round(pts * k / 5) * 5:+4}")


if __name__ == "__main__":
    main()

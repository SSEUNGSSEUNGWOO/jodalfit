"""추천 평가 순수 함수. DB·네트워크 없음. `uv run python -m app.recommender.evaluation` 으로 self-check."""
from __future__ import annotations

from collections import defaultdict

Key = str | tuple[str, str]  # (bid_ntce_no, bid_ntce_ord) — 잡은 bare bid_ntce_no 문자열도 넘긴다

STAGES = ("dense", "dedup", "qualified", "scored", "final")


def recall_at_k(ranked: list[Key], positives: set[Key], k: int) -> float:
    """정답 중 상위 k 안에 든 비율. 정답 0개면 0.0 (호출부에서 제외)."""
    if not positives:
        return 0.0
    hit = len(set(ranked[:k]) & positives)
    return hit / len(positives)


def mrr(ranked: list[Key], positives: set[Key]) -> float:
    """첫 정답의 역순위. 정답이 없으면 0.0."""
    for i, key in enumerate(ranked, 1):
        if key in positives:
            return 1.0 / i
    return 0.0


def company_tier(n_history: float) -> str:
    """t 이전 수주(계약+참가 유효건수) 수로 군 분류. 운영 dynamic_weights 경계와 동일. 참가는 0.4 가중이라 float."""
    if n_history == 0:
        return "cold"
    if n_history <= 5:
        return "small"
    return "rich"


def strip_leaked_history(history: list[dict], positives: set[Key]) -> list[dict]:
    """t 이후 정답 공고와 같은 공고번호는 이력에서 전부 제거 (차수 무관)."""
    banned = {no for no, _ in positives}
    return [h for h in history if h["bid_ntce_no"] not in banned]


def stage_lost(stage_ranks: dict[str, list[Key]], positive: Key, pool: int, limit: int) -> str:
    """정답 1건이 어느 단계에서 사라졌는지. STAGES 순서로 처음 탈락한 단계 이름, 끝까지 살았으면 'kept'.
    scored = 점수 순위가 limit 밖, final = scored top-limit 안이었지만 MMR 에 밀려남."""
    if positive in stage_ranks["final"][:limit]:
        return "kept"
    cut = {"dense": pool * 2, "dedup": pool, "qualified": pool, "scored": limit, "final": limit}
    for st in STAGES:
        if positive not in stage_ranks[st][: cut[st]]:
            return st
    return "kept"


def aggregate(per_company: list[dict]) -> dict:
    """per_company: {tier, bsns_div, r_dense, r_qual, r_scored30, r_final30, mrr, n_pos}.
    r_final5·r_final20 은 있으면 같이 집계한다 (운영 화면 조건 — 5건 공개 / 20건 표시).
    macro(회사 평균)와 군별 평균, micro(정답 가중)를 돌려준다."""
    out: dict = {"n_companies": len(per_company)}
    ALL_METRICS = ("r_dense", "r_qual", "r_scored30", "r_final30", "r_final5", "r_final20", "mrr")
    metrics = tuple(m for m in ALL_METRICS if per_company and m in per_company[0])

    def mean(rows: list[dict], m: str) -> float:
        return sum(r[m] for r in rows) / len(rows) if rows else 0.0

    out["macro"] = {m: round(mean(per_company, m), 4) for m in metrics}
    tot = sum(r["n_pos"] for r in per_company) or 1
    out["micro"] = {m: round(sum(r[m] * r["n_pos"] for r in per_company) / tot, 4) for m in metrics}
    by_tier: dict[str, list[dict]] = defaultdict(list)
    by_div: dict[str, list[dict]] = defaultdict(list)
    for r in per_company:
        by_tier[r["tier"]].append(r)
        by_div[r["bsns_div"]].append(r)
    out["by_tier"] = {t: {"n": len(rows), **{m: round(mean(rows, m), 4) for m in metrics}} for t, rows in sorted(by_tier.items())}
    out["by_div"] = {d: {"n": len(rows), **{m: round(mean(rows, m), 4) for m in metrics}} for d, rows in sorted(by_div.items())}
    return out


def _self_check() -> None:
    a, b, c = ("A", "000"), ("B", "000"), ("C", "001")
    assert recall_at_k([a, b, c], {a, c}, 2) == 0.5
    assert recall_at_k([a, b, c], {a, c}, 3) == 1.0
    assert recall_at_k([], {a}, 5) == 0.0
    assert mrr([b, a], {a}) == 0.5 and mrr([b], {a}) == 0.0
    assert (company_tier(0), company_tier(5), company_tier(6)) == ("cold", "small", "rich")
    hist = [{"bid_ntce_no": "A"}, {"bid_ntce_no": "Z"}]
    assert strip_leaked_history(hist, {("A", "002")}) == [{"bid_ntce_no": "Z"}]
    ranks = {"dense": [a, b], "dedup": [a, b], "qualified": [b], "scored": [b], "final": [b]}
    assert stage_lost(ranks, a, pool=10, limit=5) == "qualified"
    assert stage_lost(ranks, b, pool=10, limit=5) == "kept"
    assert recall_at_k([a], set(), 1) == 0.0
    assert stage_lost({**ranks, "final": [a, b]}, b, pool=10, limit=1) == "final"
    assert stage_lost({"dense": [b] * 25 + [a], "dedup": [a], "qualified": [a], "scored": [a], "final": []}, a, pool=10, limit=5) == "dense"
    d = ("D", "000")
    ranks2 = {"dense": [a, b, c, d], "dedup": [a, b, c, d], "qualified": [a, b, c, d], "scored": [a, b, c, d], "final": [a, b, c]}
    assert stage_lost(ranks2, d, pool=10, limit=3) == "scored"  # scored 순위(4위) > limit(3)
    assert stage_lost(ranks2, d, pool=10, limit=4) == "final"   # scored top-4 안이지만 final 에 없음(MMR 에 밀림)
    assert company_tier(0.4) == "small"
    agg = aggregate([
        {"tier": "cold", "bsns_div": "용역", "r_dense": 1.0, "r_qual": 1.0, "r_scored30": 0.5, "r_final30": 0.5, "mrr": 0.5, "n_pos": 2},
        {"tier": "rich", "bsns_div": "용역", "r_dense": 0.0, "r_qual": 0.0, "r_scored30": 0.0, "r_final30": 0.0, "mrr": 0.0, "n_pos": 1},
    ])
    assert agg["macro"]["r_dense"] == 0.5 and agg["by_tier"]["cold"]["n"] == 1
    assert agg["micro"]["r_dense"] == round(2 / 3, 4)  # aggregate 는 4자리 반올림
    print("evaluation self-check ok")


if __name__ == "__main__":
    _self_check()

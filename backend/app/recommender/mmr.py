"""MMR (Maximal Marginal Relevance) — top N 다양성 보장.

매 pick마다 (λ × 정규화점수 − (1−λ) × 이미 뽑힌 것과의 최대 유사도)를
최대화. 임베딩 없는 후보는 유사도 0으로 취급(뽑힐 수 있음).
"""

from __future__ import annotations

import numpy as np


def _norm(v: list[float]) -> np.ndarray:
    a = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(a))
    return a / n if n > 0 else a


def mmr_diversify(
    candidates: list[dict],
    embeddings: dict[tuple[str, str], list[float]],
    k: int = 5,
    lambda_: float = 0.7,
) -> list[dict]:
    """candidates(raw score 내림차순 가정)에서 다양성 고려해 k개 선별.

    반환: 선별된 k개 + 남은 후보(점수순). 전체 길이는 입력과 동일.
    """
    if len(candidates) <= k:
        return candidates

    scores = [c["score_raw"] for c in candidates]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1.0
    norm_scores = [(s - lo) / span for s in scores]

    embs: list[np.ndarray | None] = []
    for c in candidates:
        e = embeddings.get((c["bid_ntce_no"], c["bid_ntce_ord"]))
        embs.append(_norm(e) if e else None)

    remaining = list(range(len(candidates)))
    picked: list[int] = []
    while len(picked) < k and remaining:
        best_i, best_val = remaining[0], -np.inf
        for i in remaining:
            max_sim = 0.0
            if embs[i] is not None:
                for j in picked:
                    if embs[j] is not None:
                        max_sim = max(max_sim, float(embs[i] @ embs[j]))
            val = lambda_ * norm_scores[i] - (1 - lambda_) * max_sim
            if val > best_val:
                best_i, best_val = i, val
        picked.append(best_i)
        remaining.remove(best_i)

    return [candidates[i] for i in picked] + [candidates[i] for i in remaining]

# 추천 평가 하네스(채점표) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 과거 낙찰을 정답으로 삼아 "그 시점 t에 추천했다면 정답이 후보 200 / 최종 30 안에 들었는가"를 회사 군별로 재는 CLI와 보고서를 만든다. 이후 모든 추천 변경의 전후 비교 기준.

**Architecture:** 순수 지표 함수(`app/recommender/evaluation.py`)와 데이터 추출·재생(`jobs/evaluate_recommender.py`)을 분리한다. 재생은 운영 코드(`score_notice`, `check_qualifications`, `mmr_diversify`, `build_industry_text`, `dynamic_weights`)를 **그대로 import**해 쓰고, DB 접근은 psycopg 읽기 전용(`DATABASE_URL`)으로 한다. 회사 벡터·거래기관·금액 중간값·기관 통계는 t 이전 데이터로 다시 합성해 정답 누수를 막는다. dense 검색은 활성 공고 임베딩을 numpy로 한 번 올려 정확 코사인(운영 RPC와 같은 결과)으로 한다.

**Tech Stack:** Python 3.12 / uv, psycopg 3, numpy. 테스트 프레임워크 없음(CLAUDE.md) → 순수 함수 모듈에 `python -m` self-check(assert)를 둔다.

**운영과 일부러 다르게 두는 것 (manifest에 기록):** 회사 업종·물품은 같은 사업자번호(norm)의 모든 행을 합친다(운영은 한 행만 읽는 버그, Codex P1). 업종·지역은 현재 값(과거 이력 없음) — "현재 등록정보 참고 평가"임을 보고서에 명시.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `backend/app/recommender/evaluation.py` (신규) | 순수 함수: recall@k, MRR, 회사 tier 분류, 누수 필터, 단계별 손실 집계. DB 없음. `__main__` self-check |
| `backend/jobs/evaluate_recommender.py` (신규) | CLI. 시점 t 고정 → 정답·회사 표본·활성 공고 추출 → t 기준 회사 벡터 재합성 → 운영 파이프라인 재생 → 지표·보고서 저장 |
| `backend/data/recommender_eval/<run_id>/` | `manifest.json`, `metrics.json`, `report.md`, `failures.csv` (gitignored `data/`) |
| `docs/recommender/evaluation.md` (신규) | 평가 규칙·누수 제한·실행법·첫 baseline 결과 |

---

### Task 1: 순수 지표 모듈 + self-check

**Files:**
- Create: `backend/app/recommender/evaluation.py`

- [ ] **Step 1: 모듈 작성 (self-check 포함)**

```python
"""추천 평가 순수 함수. DB·네트워크 없음. `uv run python -m app.recommender.evaluation` 으로 self-check."""
from __future__ import annotations

from collections import defaultdict

Key = tuple[str, str]  # (bid_ntce_no, bid_ntce_ord)

STAGES = ("dense", "dedup", "qualified", "scored", "final")


def recall_at_k(ranked: list[Key], positives: set[Key], k: int) -> float:
    """정답 중 상위 k 안에 든 비율. 정답 0개면 0.0 (호출부에서 제외)."""
    if not positives:
        return 0.0
    hit = sum(1 for key in ranked[:k] if key in positives)
    return hit / len(positives)


def mrr(ranked: list[Key], positives: set[Key]) -> float:
    for i, key in enumerate(ranked, 1):
        if key in positives:
            return 1.0 / i
    return 0.0


def company_tier(n_history: int) -> str:
    """t 이전 수주(계약+참가 유효건수) 수로 군 분류. 운영 dynamic_weights 경계와 동일."""
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
    """정답 1건이 어느 단계에서 사라졌는지. STAGES 순서로 처음 탈락한 단계 이름, 끝까지 살았으면 'kept'."""
    cut = {"dense": pool * 2, "dedup": pool, "qualified": pool, "scored": limit, "final": limit}  # scored=점수 순위 limit 밖, final=MMR 에 밀림
    for st in STAGES:
        if positive not in stage_ranks.get(st, [])[: cut[st]]:
            return st
    return "kept"


def aggregate(per_company: list[dict]) -> dict:
    """per_company: {tier, bsns_div, r_dense, r_qual, r_scored30, r_final30, mrr, n_pos}.
    macro(회사 평균)와 군별 평균, micro(정답 가중)를 돌려준다."""
    out: dict = {"n_companies": len(per_company)}
    metrics = ("r_dense", "r_qual", "r_scored30", "r_final30", "mrr")

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
    agg = aggregate([
        {"tier": "cold", "bsns_div": "용역", "r_dense": 1.0, "r_qual": 1.0, "r_scored30": 0.5, "r_final30": 0.5, "mrr": 0.5, "n_pos": 2},
        {"tier": "rich", "bsns_div": "용역", "r_dense": 0.0, "r_qual": 0.0, "r_scored30": 0.0, "r_final30": 0.0, "mrr": 0.0, "n_pos": 1},
    ])
    assert agg["macro"]["r_dense"] == 0.5 and agg["by_tier"]["cold"]["n"] == 1
    assert agg["micro"]["r_dense"] == round(2 / 3, 4)  # aggregate 는 4자리 반올림
    print("evaluation self-check ok")


if __name__ == "__main__":
    _self_check()
```

- [ ] **Step 2: self-check 실행**

Run: `cd backend && uv run python -m app.recommender.evaluation`
Expected: `evaluation self-check ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/recommender/evaluation.py
git commit -m "feat(recommender): 평가 순수 함수 모듈 (recall/mrr/tier/누수 필터/단계 손실)"
```

---

### Task 2: CLI 골격 + 데이터 추출 (정답·회사 표본·활성 공고)

**Files:**
- Create: `backend/jobs/evaluate_recommender.py`

- [ ] **Step 1: 골격 + 추출 함수 작성**

```python
"""추천 평가 하네스 — 시점 t 에 추천했다면 이후 낙찰 공고가 들었는가.

사용: cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 300 [--pool 200 --limit 30 --seed 7]
읽기 전용. 결과: data/recommender_eval/<run_id>/
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv

from app.recommender.evaluation import (
    STAGES, aggregate, company_tier, mrr, recall_at_k, stage_lost, strip_leaked_history,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
HORIZON_DAYS = 90          # recommend.py MAX_CLSE_HORIZON_DAYS 와 동일
HALF_LIFE = 365.0          # compute_company_vectors 와 동일
PARTICIPATION_WEIGHT = 0.4


def connect() -> psycopg.Connection:
    if not DATABASE_URL:
        sys.exit("DATABASE_URL 이 .env 에 없습니다")
    conn = psycopg.connect(DATABASE_URL, connect_timeout=20, options="-c statement_timeout=600000")
    conn.execute("set client_encoding to 'UTF8'")
    return conn


def fetch_positives(conn, t: date, horizon: date) -> dict[str, set[tuple[str, str]]]:
    """t 에 활성(게시 < t ≤ 마감 ≤ t+horizon)이었고 나중에 낙찰한 (회사norm → {(no, ord)})."""
    rows = conn.execute(
        """select a.bizrno_norm, a.bid_ntce_no, a.bid_ntce_ord
           from award_results a join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where a.is_winner and a.bizrno_norm is not null and b.embedding is not null
             and b.bid_ntce_date < %s and b.bid_clse_date >= %s and b.bid_clse_date <= %s""",
        (t, t, horizon),
    ).fetchall()
    out: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for biz, no, od in rows:
        out[biz].add((no, od))
    return out


def fetch_history_count(conn, bizs: list[str], t: date) -> dict[str, float]:
    """t 이전 유효 이력 수 = 계약(<t) 1.0 + 참가(개찰 < t) 0.4. tier 분류용."""
    cnt: dict[str, float] = defaultdict(float)
    for biz, n in conn.execute(
        "select rprsnt_corp_bizrno_norm, count(*) from contracts where rprsnt_corp_bizrno_norm = any(%s) and cntrct_cncls_date < %s group by 1",
        (bizs, t),
    ):
        cnt[biz] += n
    for biz, n in conn.execute(
        """select a.bizrno_norm, count(*) from award_results a join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where a.bizrno_norm = any(%s) and not a.is_winner and b.openg_date < %s group by 1""",
        (bizs, t),
    ):
        cnt[biz] += PARTICIPATION_WEIGHT * n
    return cnt


def sample_companies(conn, positives: dict, t: date, n: int, seed: int) -> list[dict]:
    """업종 재료가 있는 회사 중 tier 별로 고르게 표본. 반환: [{biz, tier, n_hist}]"""
    bizs = list(positives)
    have_ind = {r[0] for r in conn.execute(
        """select co.bizrno_norm from companies co where co.bizrno_norm = any(%s)
           and exists (select 1 from company_industries i where i.bizrno = co.bizrno)""", (bizs,))}
    hist = fetch_history_count(conn, [b for b in bizs if b in have_ind], t)
    by_tier: dict[str, list[str]] = defaultdict(list)
    for b in bizs:
        if b in have_ind:
            by_tier[company_tier(hist.get(b, 0.0))].append(b)  # float 유효건수 (참가 0.4) 그대로
    rng = random.Random(seed)
    per = max(1, n // 3)
    out: list[dict] = []
    for tier in ("cold", "small", "rich"):
        pool = by_tier[tier]
        rng.shuffle(pool)
        out += [{"biz": b, "tier": tier, "n_hist": hist.get(b, 0)} for b in pool[:per]]
    return out


def fetch_active_notices(conn, t: date, horizon: date) -> tuple[list[dict], np.ndarray]:
    """t 에 활성이고 임베딩 있는 공고 전부(운영 RPC 조건과 동일) + 임베딩 행렬(정규화)."""
    rows = conn.execute(
        """select bid_ntce_no, bid_ntce_ord, bid_ntce_nm, bsns_div_nm, bid_clse_date, presmpt_prce,
                  ntce_instt_nm, dmnd_instt_nm, bidprc_psbl_indstryty_nm, prtcpt_psbl_rgn_nm, embedding::text
           from bid_notices where embedding is not null and bid_ntce_date < %s and bid_clse_date >= %s and bid_clse_date <= %s""",
        (t, t, horizon),
    ).fetchall()
    notices = [dict(bid_ntce_no=r[0], bid_ntce_ord=r[1], bid_ntce_nm=r[2], bsns_div_nm=r[3],
                    bid_clse_date=r[4], presmpt_prce=r[5], ntce_instt_nm=r[6], dmnd_instt_nm=r[7],
                    bidprc_psbl_indstryty_nm=r[8], prtcpt_psbl_rgn_nm=r[9]) for r in rows]
    X = np.array([json.loads(r[10]) for r in rows], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return notices, X


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True, help="평가 시점 t (YYYY-MM-DD)")
    ap.add_argument("--companies", type=int, default=300)
    ap.add_argument("--pool", type=int, default=200, help="운영 candidate_pool")
    ap.add_argument("--limit", type=int, default=30, help="최종 결과 수")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    t = date.fromisoformat(args.as_of)
    horizon = t + timedelta(days=HORIZON_DAYS)
    conn = connect()
    positives = fetch_positives(conn, t, horizon)
    sample = sample_companies(conn, positives, t, args.companies, args.seed)
    notices, X = fetch_active_notices(conn, t, horizon)
    print(f"t={t} positives: {sum(len(v) for v in positives.values()):,} notices / {len(positives):,} companies; "
          f"sample={len(sample)} ({', '.join(f'{k}={sum(1 for s in sample if s['tier']==k)}' for k in ('cold','small','rich'))}); active={len(notices):,}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 추출만 실행해 규모 확인**

Run: `cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 300`
Expected: `t=2026-08-01 positives: N notices / M companies; sample=300 (cold=100, small=100, rich=100); active=~9,000` (숫자는 실제값. active 가 0이면 날짜 오류)

- [ ] **Step 3: Commit**

```bash
git add backend/jobs/evaluate_recommender.py
git commit -m "feat(jobs): 추천 평가 하네스 골격 — 시점 t 정답·회사 표본·활성 공고 추출"
```

---

### Task 3: t 기준 회사 프로필 재합성 (벡터·업종·거래기관·금액·기관통계) — 누수 차단

**Files:**
- Modify: `backend/jobs/evaluate_recommender.py` (Task 2 의 `main()` 위에 추가)

- [ ] **Step 1: 재합성 함수 추가**

`from jobs.compute_company_vectors import build_industry_text, dynamic_weights` 를 상단 import 에 추가하고(이 모듈은 import 시 DB 연결 없음 — Task 3 Step 2 에서 확인), `from app.services.openai_client import embed_texts` 를 추가한다. 그다음 함수들:

```python
def fetch_company_profile(conn, biz: str) -> dict:
    """같은 norm 의 모든 회사 행을 합친 업종·물품(대표/나머지), 지역, 업종 이름 set, 토큰 set."""
    from app.recommender.score import _tokenize  # 운영과 같은 토큰화
    rows = conn.execute("select bizrno, rgn_nm from companies where bizrno_norm = %s", (biz,)).fetchall()
    pks = [r[0] for r in rows]
    rgn = next((r[1] for r in rows if r[1]), None)
    rep_i, rest_i, rep_p, rest_p = [], [], [], []
    names: set[str] = set(); terms: set[str] = set()
    for nm, rep in conn.execute("select indstryty_nm, rprsnt_indstryty_yn from company_industries where bizrno = any(%s) order by indstryty_nm", (pks,)):
        if not nm or nm in rep_i or nm in rest_i: continue
        (rep_i if rep == "Y" else rest_i).append(nm)
        names.add(nm); base = nm.split("(")[0].strip()
        if base and base != nm: names.add(base)
        terms |= _tokenize(nm)
    for nm, rep in conn.execute("select dtl_prdct_clsfc_nm, rprsnt_prdct_yn from company_supply_products where bizrno = any(%s) order by dtl_prdct_clsfc_nm", (pks,)):
        if not nm or nm in rep_p or nm in rest_p: continue
        (rep_p if rep == "Y" else rest_p).append(nm)
        terms |= _tokenize(nm)
    return {"rgn": rgn, "industries": (rep_i, rest_i), "products": (rep_p, rest_p), "names": names, "terms": terms}


def fetch_history_before(conn, biz: str, t: date) -> tuple[list[dict], set[str], float | None]:
    """t 이전 이력: [{bid_ntce_no, bid_ntce_ord, w, when}] (계약 1.0 / 참가 0.4),
    거래기관 set, 계약금액 중간값(운영 _fetch_company_history 와 같은 '위쪽 중앙값')."""
    hist: list[dict] = []; instts: set[str] = set(); amts: list[float] = []
    for no, od, d, instt, amt in conn.execute(
        "select bid_ntce_no, bid_ntce_ord, cntrct_cncls_date, dmnd_instt_nm, cntrct_amt from contracts where rprsnt_corp_bizrno_norm = %s and cntrct_cncls_date < %s",
        (biz, t)):
        if no: hist.append({"bid_ntce_no": no, "bid_ntce_ord": od, "w": 1.0, "when": d})
        if instt and instt.strip(): instts.add(instt.strip())
        if amt and amt > 0: amts.append(float(amt))
    for no, od, d in conn.execute(
        """select a.bid_ntce_no, a.bid_ntce_ord, b.openg_date from award_results a join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where a.bizrno_norm = %s and not a.is_winner and b.openg_date < %s""", (biz, t)):
        hist.append({"bid_ntce_no": no, "bid_ntce_ord": od, "w": PARTICIPATION_WEIGHT, "when": d})
    median = sorted(amts)[len(amts) // 2] if amts else None
    return hist, instts, median


def company_vector_at(conn, prof: dict, hist: list[dict], t: date, cache: dict, eff_count: float) -> np.ndarray | None:
    """운영 compute_company_vectors 와 같은 합성: 업종 텍스트 임베딩 + 시간가중 수주 평균, dynamic_weights.
    eff_count 는 표본의 n_hist(계약 1.0 + 참가 0.4, t 이전)와 같은 값 — tier 라벨과 가중치의 단일 출처."""
    text = build_industry_text({}, prof["industries"], prof["products"])
    if not text:
        return None
    if text not in cache:
        cache[text] = np.array(embed_texts([text])[0], dtype=np.float32)
    ind = cache[text]; ind = ind / (np.linalg.norm(ind) + 1e-9)
    keys = [(h["bid_ntce_no"], h["bid_ntce_ord"]) for h in hist]
    emb: dict[tuple[str, str], np.ndarray] = {}
    if keys:
        for no, od, e in conn.execute(
            "select bid_ntce_no, bid_ntce_ord, embedding::text from bid_notices where (bid_ntce_no, bid_ntce_ord) in (select unnest(%s::text[]), unnest(%s::text[])) and embedding is not null",
            ([k[0] for k in keys], [k[1] for k in keys])):
            emb[(no, od)] = np.array(json.loads(e), dtype=np.float32)
    acc = np.zeros_like(ind); tw = 0.0
    for h in hist:
        v = emb.get((h["bid_ntce_no"], h["bid_ntce_ord"]))
        if v is None: continue
        days = max((t - h["when"]).days, 0) if h["when"] else 0
        w = h["w"] * (0.5 ** (days / HALF_LIFE))
        acc += w * v; tw += w
    wts = dynamic_weights(eff_count, has_interest=False)
    vec = wts["industry"] * ind
    if tw > 0:
        vec = vec + wts["suju"] * (acc / tw)   # 운영과 동일: 수주 평균은 정규화하지 않음 (Codex P2 지적, 그대로 재현)
    return vec / (np.linalg.norm(vec) + 1e-9)


def fetch_instt_stats_before(conn, t: date) -> dict[str, dict]:
    """0038 MV 와 같은 식(total, distinct_winners)을 t 이전 계약으로 계산. 전체 기관 한 번."""
    return {instt: {"total": tot, "distinct_winners": dw} for instt, tot, dw in conn.execute(
        """select dmnd_instt_nm, count(*)::int, count(distinct rprsnt_corp_bizrno_norm)::int from contracts
           where dmnd_instt_nm is not null and cntrct_cncls_date < %s group by 1 having count(*) >= 10""", (t,))}
```

- [ ] **Step 2: import 부작용·합성 1건 검증**

Run:
```bash
cd backend && uv run python -c "import jobs.compute_company_vectors as m; print('import ok, no DB side effect')"
uv run python - <<'EOF'
from datetime import date
from jobs.evaluate_recommender import connect, fetch_company_profile, fetch_history_before, company_vector_at, fetch_positives, strip_leaked_history
from datetime import timedelta
c = connect(); t = date(2026, 8, 1)
pos = fetch_positives(c, t, t + timedelta(days=90)); biz = next(iter(pos))
prof = fetch_company_profile(c, biz); hist, instts, med = fetch_history_before(c, biz, t)
clean = strip_leaked_history(hist, pos[biz])
v = company_vector_at(c, prof, clean, t, {}, sum(h["w"] for h in clean))  # 검증용 근사치. 본 실행(Task 5)은 표본의 n_hist(계약 행 수 기반, 운영 suju_count 와 동일)를 넘긴다 — 계약의 64%가 bid_ntce_no='' 라 둘은 다르다
assert v is not None and abs(float((v*v).sum()) - 1) < 1e-4, "단위 벡터 아님"
assert all(h["when"] is None or h["when"] < t for h in clean), "t 이후 이력 누수"
assert not ({h["bid_ntce_no"] for h in clean} & {no for no, _ in pos[biz]}), "정답 공고가 이력에 남음"
print("profile ok", biz, "hist", len(hist), "->", len(clean), "instts", len(instts), "median", med)
EOF
```
Expected: `import ok, no DB side effect` 그리고 `profile ok <biz> hist N -> M instts K median X` (assert 통과)

- [ ] **Step 3: Commit**

```bash
git add backend/jobs/evaluate_recommender.py
git commit -m "feat(jobs): 평가 하네스 — t 기준 회사 프로필·벡터·기관통계 재합성(누수 차단)"
```

---

### Task 4: 운영 파이프라인 재생 (dense → dedup → 자격 → 점수 → MMR) + 단계별 순위 기록

**Files:**
- Modify: `backend/jobs/evaluate_recommender.py`

- [ ] **Step 1: 재생 함수 추가**

상단 import 에 `from app.recommender.score import score_notice`, `from app.recommender.qualifications import check_qualifications`, `from app.recommender.mmr import mmr_diversify`, `from app.recommender.pipeline import MMR_POOL` 추가. 그다음:

```python
def fetch_limits(conn, keys: list[tuple[str, str]]) -> dict[tuple[str, str], dict]:
    """운영 _fetch_eligibility 와 같은 두 테이블."""
    out: dict[tuple[str, str], dict] = {}
    nos = list({k[0] for k in keys})
    for no, od, nm, grp in conn.execute("select bid_ntce_no, bid_ntce_ord, lcns_lmt_nm, lmt_grp_no from bid_license_limits where bid_ntce_no = any(%s)", (nos,)):
        out.setdefault((no, od), {"licenses": [], "regions": []})["licenses"].append({"lcns_lmt_nm": nm, "lmt_grp_no": grp})
    for no, od, rg in conn.execute("select bid_ntce_no, bid_ntce_ord, prtcpt_psbl_rgn_nm from bid_rgn_limits where bid_ntce_no = any(%s)", (nos,)):
        out.setdefault((no, od), {"licenses": [], "regions": []})["regions"].append({"prtcpt_psbl_rgn_nm": rg})
    return out


def replay(conn, notices: list[dict], X: np.ndarray, vec: np.ndarray, prof: dict, instts: set[str],
           median: float | None, instt_stats: dict, t: date, pool: int, limit: int) -> dict[str, list[tuple[str, str]]]:
    """운영 _search_with_embedding + rank_v2 를 그대로 재생. 단계별 (no, ord) 순위 리스트 반환."""
    sims = X @ vec
    order = np.argsort(-sims)[: pool * 2]
    dense = [(notices[i]["bid_ntce_no"], notices[i]["bid_ntce_ord"]) for i in order]
    # dedup: 공고번호 첫 등장 + 내용 지문 (운영과 동일)
    seen: set[str] = set(); seen_c: set[tuple] = set(); cand: list[dict] = []
    for i in order:
        r = dict(notices[i]); r["similarity"] = float(sims[i])
        n = r["bid_ntce_no"]
        if n in seen: continue
        ck = ((r.get("bid_ntce_nm") or "").strip(), (r.get("ntce_instt_nm") or r.get("dmnd_instt_nm") or "").strip(), r.get("bid_clse_date"), r.get("presmpt_prce"))
        if ck[0] and ck in seen_c: continue
        seen.add(n); seen_c.add(ck); cand.append(r)
        if len(cand) >= pool: break
    dedup = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in cand]
    lim = fetch_limits(conn, dedup)
    passed: list[dict] = []
    for r in cand:
        slot = lim.get((r["bid_ntce_no"], r["bid_ntce_ord"])) or {"licenses": [], "regions": []}
        q = check_qualifications(prof["names"], prof["rgn"], slot["licenses"], slot["regions"])
        if q["passed"]:
            r["qualification"] = q; passed.append(r)
    qualified = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in passed]
    for r in passed:
        raw, bd = score_notice(r, company_rgn=prof["rgn"], company_terms=prof["terms"], company_institutions=instts,
                               company_amt_median=median, today=t, peer_instt_counts={}, instt_stats=instt_stats)
        r["score_raw"] = round(raw, 1)  # 운영 pipeline.py 와 동일 (정렬·MMR 입력)
    passed.sort(key=lambda r: r["score_raw"], reverse=True)
    scored = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in passed]
    top = passed[:MMR_POOL]
    idx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): i for i, n in enumerate(notices)}
    embs = {(r["bid_ntce_no"], r["bid_ntce_ord"]): X[idx[(r["bid_ntce_no"], r["bid_ntce_ord"])]].tolist() for r in top}
    final_rows = mmr_diversify(top, embs, k=5) + passed[MMR_POOL:]
    final = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in final_rows[:limit]]
    return {"dense": dense, "dedup": dedup, "qualified": qualified, "scored": scored, "final": final}
```

- [ ] **Step 2: 회사 1곳 재생 검증**

Run:
```bash
cd backend && uv run python - <<'EOF'
from datetime import date, timedelta
from jobs.evaluate_recommender import *
c = connect(); t = date(2026, 8, 1); h = t + timedelta(days=90)
pos = fetch_positives(c, t, h); biz = next(iter(pos))
notices, X = fetch_active_notices(c, t, h)
prof = fetch_company_profile(c, biz); hist, instts, med = fetch_history_before(c, biz, t)
clean = strip_leaked_history(hist, pos[biz])
vec = company_vector_at(c, prof, clean, t, {}, sum(h["w"] for h in clean))
st = replay(c, notices, X, vec, prof, instts, med, fetch_instt_stats_before(c, t), t, 200, 30)
print({k: len(v) for k, v in st.items()})
assert len(st["dense"]) == 400 and len(st["dedup"]) <= 200 and len(st["final"]) <= 30
assert len(st["qualified"]) <= len(st["dedup"]) and set(st["final"]) <= set(st["qualified"])
print("replay ok; positives in final:", sum(1 for k in st["final"] if k in pos[biz]), "/", len(pos[biz]))
EOF
```
Expected: `{'dense': 400, 'dedup': ≤200, 'qualified': ≤dedup, 'scored': =qualified, 'final': ≤30}` 와 `replay ok; ...`

- [ ] **Step 3: Commit**

```bash
git add backend/jobs/evaluate_recommender.py
git commit -m "feat(jobs): 평가 하네스 — 운영 파이프라인 재생(dense→dedup→자격→점수→MMR) 단계별 순위"
```

---

### Task 5: 전체 실행 루프 + 지표·보고서 저장

**Files:**
- Modify: `backend/jobs/evaluate_recommender.py` (`main()` 교체)

- [ ] **Step 1: main() 을 아래로 교체**

```python
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True); ap.add_argument("--companies", type=int, default=300)
    ap.add_argument("--pool", type=int, default=200); ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    t = date.fromisoformat(args.as_of); horizon = t + timedelta(days=HORIZON_DAYS)
    run_id = args.run_id or f"{t.isoformat()}_{datetime.now():%m%d%H%M}"
    out_dir = Path("data/recommender_eval") / run_id; out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect()
    positives = fetch_positives(conn, t, horizon)
    sample = sample_companies(conn, positives, t, args.companies, args.seed)
    notices, X = fetch_active_notices(conn, t, horizon)
    instt_stats = fetch_instt_stats_before(conn, t)
    nidx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): n for n in notices}
    print(f"t={t} active={len(notices):,} sample={len(sample)} positives(total)={sum(len(positives[s['biz']]) for s in sample):,}")
    cache: dict = {}; per: list[dict] = []; failures: list[dict] = []; skipped = 0
    for i, s in enumerate(sample, 1):
        biz = s["biz"]; pos = {k for k in positives[biz] if k in nidx}
        if not pos:
            skipped += 1; continue
        prof = fetch_company_profile(conn, biz)
        hist, instts, med = fetch_history_before(conn, biz, t)
        clean = strip_leaked_history(hist, pos)
        vec = company_vector_at(conn, prof, clean, t, cache, s["n_hist"])  # tier 라벨과 같은 유효건수
        if vec is None:
            skipped += 1; continue
        st = replay(conn, notices, X, vec, prof, instts, med, instt_stats, t, args.pool, args.limit)
        # dedup 이 공고번호 단위로 차수를 접으므로(운영과 동일) 정답·순위 비교도 공고번호 단위로 한다
        # (활성 공고의 9%가 다른 차수와 공존, 정답의 4%가 그 영향 — 그대로 두면 가짜 'dedup 손실'이 생긴다)
        pos_nos = {no for no, _ in pos}
        st_nos = {k: [no for no, _ in v] for k, v in st.items()}
        div = nidx[next(iter(pos))]["bsns_div_nm"] or "?"
        per.append({"biz": biz, "tier": s["tier"], "bsns_div": div, "n_pos": len(pos_nos),
                    "r_dense": recall_at_k(st_nos["dedup"], pos_nos, args.pool), "r_qual": recall_at_k(st_nos["qualified"], pos_nos, args.pool),
                    "r_scored30": recall_at_k(st_nos["scored"], pos_nos, args.limit), "r_final30": recall_at_k(st_nos["final"], pos_nos, args.limit),
                    "mrr": mrr(st_nos["final"], pos_nos)})
        title_by_no = {no: nidx[(no, od)]["bid_ntce_nm"] for no, od in pos}
        for p in pos_nos:
            lost = stage_lost(st_nos, p, args.pool, args.limit)
            if lost != "kept":
                rank_dense = next((r for r, k in enumerate(st_nos["dense"], 1) if k == p), None)
                failures.append({"biz": biz, "tier": s["tier"], "bid_ntce_no": p, "title": title_by_no[p], "lost_at": lost, "dense_rank": rank_dense})
        if i % 25 == 0: print(f"  {i}/{len(sample)}")
    if not per:
        sys.exit("평가된 회사가 0곳 — 날짜/표본 조건을 확인하세요 (보고서 미생성)")
    agg = aggregate(per)
    lost_counts = defaultdict(int)
    for f in failures: lost_counts[f["lost_at"]] += 1
    agg["lost_at"] = dict(lost_counts); agg["skipped"] = skipped
    manifest = {"as_of": t.isoformat(), "horizon_days": HORIZON_DAYS, "pool": args.pool, "limit": args.limit, "seed": args.seed,
                "companies_requested": args.companies, "companies_evaluated": len(per), "active_notices": len(notices),
                "notes": ["업종·물품·지역은 현재 값(과거 이력 없음) → '현재 등록정보 참고 평가'",
                          "회사 업종·물품은 같은 사업자번호(norm)의 모든 행 합침 (운영은 한 행 — Codex P1)",
                          "peer_instt_counts 비활성(운영과 동일), 기관통계는 t 이전 2년 계약으로 재계산",
                          "정답=낙찰(award_results.is_winner). 미낙찰은 음성 아님",
                          "참가 이력의 시점은 openg_date(개찰일) 기준 — 운영 잡은 raw bidprcDt 를 쓰지만 t 시점 '알 수 있었던' 기준으로는 개찰일이 맞다",
                          "정답·순위 비교는 공고번호 단위(차수 무시) — 운영 dedup 과 같은 단위",
                          "게시일 = t 인 공고는 제외(bid_ntce_date < t) — 보수적, 시점당 수십 건"]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "failures.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["biz", "tier", "bid_ntce_no", "title", "lost_at", "dense_rank"]); w.writeheader(); w.writerows(failures)
    m, lines = agg["macro"], []
    lines += [f"# 추천 평가 baseline — t={t} (run {run_id})", "",
              f"회사 {len(per)} (skip {skipped}) · 활성 공고 {len(notices):,} · pool {args.pool} · limit {args.limit}", "",
              "| 지표 | macro | micro |", "|---|---|---|"]
    lines += [f"| {k} | {m[k]:.3f} | {agg['micro'][k]:.3f} |" for k in ("r_dense", "r_qual", "r_scored30", "r_final30", "mrr")]
    lines += ["", "## 군별 (macro)", "", "| 군 | n | dense@pool | qual@pool | scored@30 | final@30 | mrr |", "|---|---|---|---|---|---|---|"]
    for grp in ("by_tier", "by_div"):
        for k, v in agg[grp].items():
            lines.append(f"| {k} | {v['n']} | {v['r_dense']:.3f} | {v['r_qual']:.3f} | {v['r_scored30']:.3f} | {v['r_final30']:.3f} | {v['mrr']:.3f} |")
    lines += ["", "## 정답이 사라진 단계", "", "| 단계 | 건수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(lost_counts.items(), key=lambda x: -x[1])]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines)); print(f"\nsaved: {out_dir}")
```

- [ ] **Step 2: 소규모 실행으로 end-to-end 확인**

Run: `cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 30 --run-id smoke`
Expected: 진행 로그 후 report 표가 출력되고 `data/recommender_eval/smoke/` 에 4개 파일 생성. `r_dense ≥ r_qual ≥ r_scored30 ≥ 0` 순서가 지켜짐(아니면 단계 버그).

- [ ] **Step 3: Commit**

```bash
git add backend/jobs/evaluate_recommender.py
git commit -m "feat(jobs): 평가 하네스 — 전체 루프·군별 지표·손실 단계·보고서 저장"
```

---

### Task 6: baseline 실행 + 문서

**Files:**
- Create: `docs/recommender/evaluation.md`
- Create: `docs/recommender/baseline-2026-08-01.md` (report.md 복사)

- [ ] **Step 1: baseline 두 시점 실행 (백그라운드, 각 10~20분)**

Run:
```bash
cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 300 --run-id base-0801
uv run python -m jobs.evaluate_recommender --as-of 2026-09-01 --companies 300 --run-id base-0901
```
Expected: 두 report.md. 두 시점의 macro 지표 차이가 ±0.05 안이면 표본이 안정적. 크게 다르면 `--companies 600` 으로 재실행.

- [ ] **Step 2: 문서 작성**

`docs/recommender/evaluation.md`:
```markdown
# 추천 평가 하네스 (채점표)

실행: `cd backend && uv run python -m jobs.evaluate_recommender --as-of YYYY-MM-DD --companies 300`
결과: `backend/data/recommender_eval/<run_id>/` (manifest / metrics.json / report.md / failures.csv)

## 규칙
- 정답 = `award_results.is_winner` 인 공고 중, t 에 활성(게시 < t ≤ 마감 ≤ t+90일)이었던 것. 미낙찰·미참가는 음성이 아님.
- 회사 벡터·거래기관·금액 중간값·기관 통계는 **t 이전 데이터로 재합성**. 정답 공고와 같은 공고번호는 이력에서 제거.
- 후보 집합 = t 에 활성이고 임베딩 있는 공고 전부 (운영 RPC 조건과 동일). dense 는 정확 코사인.
- 파이프라인은 운영 함수(`score_notice`, `check_qualifications`, `mmr_diversify`) 를 그대로 import.
- 지표: dense@pool(dedup 후), qual@pool(자격 후), scored@30(MMR 전), final@30, MRR. 회사 macro 평균 + 정답 가중 micro. 군: cold/small/rich(t 이전 이력), 업무구분.
- 한계: 업종·물품·지역은 현재 값. 낙찰 라벨은 기존 거래처 편향. "낙찰 확률"이 아니라 "검토할 공고를 놓치지 않는가"를 잰다.
- 운영과 알려진 차이: 회사 업종·물품은 같은 사업자번호의 모든 행 합침(운영은 한 행). 참가 이력 시점은 개찰일 기준. 게시일 = t 공고 제외. 정답·순위 비교는 공고번호 단위(차수 무시).

## 변경 비교 방법
같은 `--as-of --seed --companies` 로 전후 실행 → `metrics.json` 의 macro·군별 차이를 본다. 한 군이 떨어지면 전체 평균이 올라도 채택하지 않는다.

## Baseline
`baseline-2026-08-01.md` 참조.
```

- [ ] **Step 3: 보고서 복사·커밋·push**

```bash
cp backend/data/recommender_eval/base-0801/report.md docs/recommender/baseline-2026-08-01.md
git add docs/recommender/evaluation.md docs/recommender/baseline-2026-08-01.md
git commit -m "docs(recommender): 평가 하네스 규칙 + 2026-08-01 baseline"
git push origin main
```

- [ ] **Step 4: 결과 해석 보고 (승우님께)**
어느 군에서 어느 단계(dense / qualified / scored / final)에 정답을 가장 많이 잃는지 한 문단으로. 이것이 2~5단계 중 다음 작업을 정한다.

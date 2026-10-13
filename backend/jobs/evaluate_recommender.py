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
    conn = psycopg.connect(DATABASE_URL, connect_timeout=20, autocommit=True)
    conn.execute("set client_encoding to 'UTF8'")
    conn.execute("set statement_timeout = 600000")
    conn.execute("set default_transaction_read_only = on")
    return conn


def fetch_positives(conn, t: date, horizon: date) -> dict[str, set[tuple[str, str]]]:
    """t 에 활성(게시 < t ≤ 마감 ≤ t+horizon)이었고 나중에 낙찰한 (회사norm → {(no, ord)})."""
    rows = conn.execute(
        """select a.bizrno_norm, a.bid_ntce_no, a.bid_ntce_ord
           from award_results a join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where a.is_winner and a.bizrno_norm <> '' and b.embedding is not null
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
    bizs = sorted(positives)
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
        out += [{"biz": b, "tier": tier, "n_hist": hist.get(b, 0.0)} for b in pool[:per]]
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

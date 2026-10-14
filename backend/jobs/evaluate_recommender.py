"""추천 평가 하네스 — 시점 t 에 추천했다면 이후 낙찰 공고가 들었는가.

사용: cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 300 [--pool 200 --limit 30 --seed 7]
읽기 전용. 결과: data/recommender_eval/<run_id>/
baseline 보존: 산출물은 gitignore 대상 — 기준점은 docs/recommender/ 에 report.md 를 복사해 둔다.
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
    aggregate, company_tier, mrr, recall_at_k, stage_lost, strip_leaked_history,
)
from app.services.openai_client import embed_texts
from jobs.compute_company_vectors import build_industry_text, dynamic_weights
from app.recommender.mmr import mmr_diversify
from app.recommender.pipeline import MMR_POOL
from app.recommender.qualifications import check_qualifications
from app.recommender.score import score_notice

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    if conn.execute("show transaction_read_only").fetchone()[0] != "on":
        sys.exit("읽기 전용 세션이 적용되지 않았습니다 — DATABASE_URL 이 트랜잭션 풀러(:6543)인지 확인")
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
           from bid_notices where embedding is not null and bid_ntce_date < %s and bid_clse_date >= %s and bid_clse_date <= %s
           order by bid_ntce_no, bid_ntce_ord""",
        (t, t, horizon),
    ).fetchall()
    if not rows:
        sys.exit(f"t={t} 활성 공고 0건 — --as-of 날짜를 확인하세요")
    notices = [dict(bid_ntce_no=r[0], bid_ntce_ord=r[1], bid_ntce_nm=r[2], bsns_div_nm=r[3],
                    bid_clse_date=r[4], presmpt_prce=r[5], ntce_instt_nm=r[6], dmnd_instt_nm=r[7],
                    bidprc_psbl_indstryty_nm=r[8], prtcpt_psbl_rgn_nm=r[9]) for r in rows]
    X = np.array([json.loads(r[10]) for r in rows], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return notices, X


def fetch_company_profile(conn, biz: str) -> dict:
    """같은 norm 의 모든 회사 행을 합친 업종·물품(대표/나머지), 지역, 업종 이름 set, 토큰 set."""
    from app.recommender.score import _tokenize  # 운영과 같은 토큰화
    rows = conn.execute("select bizrno, rgn_nm from companies where bizrno_norm = %s order by bizrno", (biz,)).fetchall()
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
           where dmnd_instt_nm is not null and cntrct_cncls_date < %s and cntrct_cncls_date >= %s - interval '2 years'
           group by 1 having count(*) >= 10""", (t, t))}


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
    order = np.argsort(-sims, kind="stable")[: pool * 2]
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
        r["score_raw"] = round(raw, 1)
    passed.sort(key=lambda r: r["score_raw"], reverse=True)
    scored = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in passed]
    top = passed[:MMR_POOL]
    idx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): i for i, n in enumerate(notices)}
    embs = {(r["bid_ntce_no"], r["bid_ntce_ord"]): X[idx[(r["bid_ntce_no"], r["bid_ntce_ord"])]].tolist() for r in top}
    final_rows = mmr_diversify(top, embs, k=5) + passed[MMR_POOL:]
    final = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in final_rows[:limit]]
    return {"dense": dense, "dedup": dedup, "qualified": qualified, "scored": scored, "final": final}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True); ap.add_argument("--companies", type=int, default=300)
    ap.add_argument("--pool", type=int, default=200); ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    t = date.fromisoformat(args.as_of); horizon = t + timedelta(days=HORIZON_DAYS)
    run_id = args.run_id or f"{t.isoformat()}_{datetime.now():%m%d%H%M}"
    out_dir = Path(__file__).resolve().parents[1] / "data" / "recommender_eval" / run_id; out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect()
    positives = fetch_positives(conn, t, horizon)
    sample = sample_companies(conn, positives, t, args.companies, args.seed)
    notices, X = fetch_active_notices(conn, t, horizon)
    instt_stats = fetch_instt_stats_before(conn, t)
    nidx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): n for n in notices}
    print(f"t={t} active={len(notices):,} sample={len(sample)} positives(total)={sum(len(positives[s['biz']]) for s in sample):,}")
    cache: dict = {}; per: list[dict] = []; failures: list[dict] = []; skipped = 0; positives_dropped = 0
    for i, s in enumerate(sample, 1):
        biz = s["biz"]; pos = {k for k in positives[biz] if k in nidx}
        positives_dropped += len(positives[biz]) - len(pos)
        if not pos:
            skipped += 1; continue
        prof = fetch_company_profile(conn, biz)
        hist, instts, med = fetch_history_before(conn, biz, t)
        clean = strip_leaked_history(hist, positives[biz])
        vec = company_vector_at(conn, prof, clean, t, cache, s["n_hist"])  # tier 라벨과 같은 유효건수
        if vec is None:
            skipped += 1; continue
        st = replay(conn, notices, X, vec, prof, instts, med, instt_stats, t, args.pool, args.limit)
        # dedup 이 공고번호 단위로 차수를 접으므로(운영과 동일) 정답·순위 비교도 공고번호 단위로 한다
        # (활성 공고의 9%가 다른 차수와 공존, 정답의 4%가 그 영향 — 그대로 두면 가짜 'dedup 손실'이 생긴다)
        pos_nos = {no for no, _ in pos}
        st_nos = {k: [no for no, _ in v] for k, v in st.items()}
        div = nidx[min(pos)]["bsns_div_nm"] or "?"
        per.append({"biz": biz, "tier": s["tier"], "bsns_div": div, "n_pos": len(pos_nos),
                    "r_dense": recall_at_k(st_nos["dedup"], pos_nos, args.pool), "r_qual": recall_at_k(st_nos["qualified"], pos_nos, args.pool),
                    "r_scored30": recall_at_k(st_nos["scored"], pos_nos, args.limit), "r_final30": recall_at_k(st_nos["final"], pos_nos, args.limit),
                    "mrr": mrr(st_nos["final"], pos_nos)})
        title_by_no = {no: nidx[(no, od)]["bid_ntce_nm"] for no, od in sorted(pos)}
        for p in sorted(pos_nos):
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
    agg["positives_dropped"] = positives_dropped
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
    lines += ["", "## 정답이 사라진 단계", "",
              "- dense: dense 상위 pool×2 밖 · dedup: 후보 풀 pool 컷(지문 중복 제거 포함) · qualified: 자격 하드 제외 · scored: 점수 순위 limit 밖 · final: MMR 에 밀림",
              "", "| 단계 | 건수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(lost_counts.items(), key=lambda x: -x[1])]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines)); print(f"\nsaved: {out_dir}")


if __name__ == "__main__":
    main()

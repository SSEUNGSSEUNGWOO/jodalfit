"""추천 평가 하네스 — 시점 t 에 추천했다면 이후 낙찰 공고가 들었는가.

사용: cd backend && uv run python -m jobs.evaluate_recommender --as-of 2026-08-01 --companies 300 [--pool 200 --limit 30 --seed 7]
읽기 전용. 결과: data/recommender_eval/<run_id>/
baseline 보존: 산출물은 gitignore 대상 — 기준점은 docs/recommender/ 에 report.md 를 복사해 둔다.
"""
from __future__ import annotations

import argparse
from itertools import zip_longest
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

from app.core.config import get_settings
from app.recommender.evaluation import (
    aggregate, company_tier, mrr, recall_at_k, stage_lost, strip_leaked_history,
)
from app.services.embedding import embed_texts
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


def fetch_positives(conn, t: date, horizon: date, positives: str = "winner") -> dict[str, set[tuple[str, str]]]:
    """t 에 활성(게시 < t, t+2 ≤ 마감 ≤ t+horizon)이었고 나중에 낙찰(winner) 또는 입찰 참가(participant, 낙찰 포함)한 (회사norm → {(no, ord)}).
    participant 는 정답이 ~10배(8/1: 4,074 → 43,472 쌍, 회사 3.6천 → 19천)라 측정이 안정되고 '검토할 만한 공고' 라는 제품 목적에 더 가깝다."""
    win = "a.is_winner and" if positives == "winner" else ""
    rows = conn.execute(
        f"""select a.bizrno_norm, a.bid_ntce_no, a.bid_ntce_ord
           from award_results a join bid_notices b using (bid_ntce_no, bid_ntce_ord)
           where {win} a.bizrno_norm <> '' and b.{EMB_COL} is not null
             and b.bid_ntce_date < %s and b.bid_clse_date >= %s and b.bid_clse_date <= %s  -- 마감 2일 이상 남은 것만: 1일 내 마감은 t 에 '발견'할 수 없는 공고(운영 마감 임박 -30 과 같은 기준)""",
        (t, t + timedelta(days=2), horizon),
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


EMB_SPACE = "openai"  # --space: openai(embedding, 1536) | kure(embedding_k, 1024)
EMB_COL = "embedding"
EMB_STORE: dict | None = None  # --embeddings: {"n": {(no, ord): vec}, "t": {industry_text: vec}} — 다른 임베딩 모델 실험용


def load_emb_store(path: str) -> dict:
    """embed_local.py 가 만든 npz → 스토어. 공고 키 'no|ord', 업종 텍스트 원문 그대로."""
    z = np.load(path, allow_pickle=True)
    n = {tuple(k.split("|", 1)): v for k, v in zip(z["keys"].tolist(), z["N"])}
    t = {str(k): v for k, v in zip(z["texts"].tolist(), z["I"])}
    return {"n": n, "t": t, "dim": int(z["N"].shape[1])}


def fetch_active_notices(conn, t: date, horizon: date) -> tuple[list[dict], np.ndarray]:
    """t 에 활성이고 임베딩 있는 공고 전부(운영 RPC 조건과 동일) + 임베딩 행렬(정규화).
    입찰참가자격 등록 마감(bid_qlfct_rgst_dt)이 t 이전이면 제외 — 운영 RPC(0049)의 now() 조건을 t 로 옮긴 것."""
    rows = conn.execute(
        f"""select bid_ntce_no, bid_ntce_ord, bid_ntce_nm, bsns_div_nm, bid_clse_date, presmpt_prce,
                  ntce_instt_nm, dmnd_instt_nm, bidprc_psbl_indstryty_nm, prtcpt_psbl_rgn_nm, {EMB_COL}::text, prdct_clsfc_nos
           from bid_notices where {EMB_COL} is not null and bid_ntce_date < %s and bid_clse_date >= %s and bid_clse_date <= %s
             and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > %s)
           order by bid_ntce_no, bid_ntce_ord""",
        (t, t, horizon, t),
    ).fetchall()
    if not rows:
        sys.exit(f"t={t} 활성 공고 0건 — --as-of 날짜를 확인하세요")
    notices = [dict(bid_ntce_no=r[0], bid_ntce_ord=r[1], bid_ntce_nm=r[2], bsns_div_nm=r[3],
                    bid_clse_date=r[4], presmpt_prce=r[5], ntce_instt_nm=r[6], dmnd_instt_nm=r[7],
                    bidprc_psbl_indstryty_nm=r[8], prtcpt_psbl_rgn_nm=r[9], prdct_clsfc_nos=set(r[11] or ())) for r in rows]
    if EMB_STORE is not None:  # 로컬 모델 임베딩으로 대체 — 빠진 공고가 있으면 실험 자체가 무효라 fail-loud
        missing = [(r[0], r[1]) for r in rows if (r[0], r[1]) not in EMB_STORE["n"]]
        if missing:
            sys.exit(f"--embeddings 에 활성 공고 {len(missing)}건 없음 (예: {missing[0]})")
        X = np.array([EMB_STORE["n"][(r[0], r[1])] for r in rows], dtype=np.float32)
    else:
        X = np.array([json.loads(r[10]) for r in rows], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    return notices, X


def fetch_company_profile(conn, biz: str, t: date) -> dict:
    """같은 norm 의 모든 회사 행을 합친 업종·물품(대표/나머지), 지역, 업종 이름 set, 토큰 set.

    t 시점 기준으로 거른다 — 낙찰 뒤에 추가된 등록정보가 과거 평가를 낙관적으로 만든다(코덱스 지적).
    2026-10-23 실측: 8/1 표본 3,557곳 중 t 이후 업종 추가 0.6%, 물품 추가 4.3% 라 영향은 작지만
    지표를 믿으려면 시점이 맞아야 한다. 등록일에 0227년·4004년 같은 쓰레기 값이 섞여 있어
    상식 범위를 벗어난 값은 '모름'으로 보고 남긴다 — 버리면 프로필이 통째로 비어버린다."""
    from app.recommender.score import _tokenize  # 운영과 같은 토큰화
    rows = conn.execute("select bizrno, rgn_nm from companies where bizrno_norm = %s order by bizrno", (biz,)).fetchall()
    pks = [r[0] for r in rows]
    rgn = next((r[1] for r in rows if r[1]), None)
    rep_i, rest_i, rep_p, rest_p = [], [], [], []
    names: set[str] = set(); terms: set[str] = set()
    for nm, rep in conn.execute(
        """select indstryty_nm, rprsnt_indstryty_yn from company_industries
            where bizrno = any(%s)
              and (rgst_dt is null or rgst_dt not between '1900-01-01' and '2100-01-01' or rgst_dt <= %s)
              and (valid_to_dt is null or valid_to_dt not between '1900-01-01' and '2100-01-01' or valid_to_dt >= %s)
            order by indstryty_nm""", (pks, t, t)):
        if not nm or nm in rep_i or nm in rest_i: continue
        (rep_i if rep == "Y" else rest_i).append(nm)
        names.add(nm); base = nm.split("(")[0].strip()
        if base and base != nm: names.add(base)
        terms |= _tokenize(nm)
    codes: set[str] = set()
    for nm, rep, code in conn.execute(
        """select dtl_prdct_clsfc_nm, rprsnt_prdct_yn, dtl_prdct_clsfc_no from company_supply_products
            where bizrno = any(%s)
              and (rgst_dt is null or rgst_dt not between '1900-01-01' and '2100-01-01' or rgst_dt <= %s)
            order by dtl_prdct_clsfc_nm""", (pks, t)):
        if code: codes.add(code)
        if not nm or nm in rep_p or nm in rest_p: continue
        (rep_p if rep == "Y" else rest_p).append(nm)
        terms |= _tokenize(nm)
    return {"rgn": rgn, "industries": (rep_i, rest_i), "products": (rep_p, rest_p), "names": names, "terms": terms, "codes": codes}


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
        if EMB_STORE is not None:
            if text not in EMB_STORE["t"]:
                sys.exit("--embeddings 에 업종 텍스트 없음: " + text[:60])
            cache[text] = np.array(EMB_STORE["t"][text], dtype=np.float32)
        else:
            cache[text] = np.array(embed_texts([text], space=EMB_SPACE)[0], dtype=np.float32)
    ind = cache[text]; ind = ind / (np.linalg.norm(ind) + 1e-9)
    keys = [(h["bid_ntce_no"], h["bid_ntce_ord"]) for h in hist]
    emb: dict[tuple[str, str], np.ndarray] = {}
    if keys and EMB_STORE is not None:
        emb = {k: EMB_STORE["n"][k] for k in keys if k in EMB_STORE["n"]}
    elif keys:
        for no, od, e in conn.execute(
            f"select bid_ntce_no, bid_ntce_ord, {EMB_COL}::text from bid_notices where (bid_ntce_no, bid_ntce_ord) in (select unnest(%s::text[]), unnest(%s::text[])) and {EMB_COL} is not null",
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
           median: float | None, instt_stats: dict, t: date, pool: int, limit: int,
           retrieval: str = "dense", features_out: list[dict] | None = None,
           ablate: set[str] | None = None) -> dict[str, list[tuple[str, str]]]:
    """운영 _search_with_embedding + rank_v2 를 그대로 재생. 단계별 (no, ord) 순위 리스트 반환.
    retrieval: dense(운영) / prefilter(등록업종이 허용업종에 든 공고 안에서만 dense) / soft(prefilter + 허용업종 없는 공고 유지)
    / hybrid(dense 와 prefilter 교대 합침) / hybrid+prd(hybrid + 물품분류 코드 채널, 0048)."""
    sims = X @ vec
    order = np.argsort(-sims, kind="stable")
    if retrieval != "dense" and prof["names"]:
        mask = np.array([any(n in (r["bidprc_psbl_indstryty_nm"] or "") for n in prof["names"]) for r in notices])
        if retrieval == "soft":  # 허용업종이 없는 공고는 버리지 않는다
            mask |= np.array([not (r["bidprc_psbl_indstryty_nm"] or "").strip() for r in notices])
        ind = [i for i in order if mask[i]][: min(pool * 2, CHANNEL_MAX_ROWS)]
        if retrieval in ("prefilter", "soft"):
            order = ind
        else:  # hybrid: 채널들을 번갈아(동률 RRF 와 같은 효과). 운영 _interleave 와 같은 채널 순서여야 한다.
            def rr(*chs):
                out: list[int] = []; seen_i: set[int] = set()
                for group in zip_longest(*chs):  # 한쪽이 짧아도 다른 쪽은 끝까지
                    for i in group:
                        if i is not None and i not in seen_i: seen_i.add(i); out.append(i)
                return out
            channels = [ind, list(order[: min(pool * 2, CHANNEL_MAX_ROWS)])]
            if retrieval == "hybrid+prd" and prof.get("codes"):
                # 물품 채널(0048): 세 채널을 나란히(각 1/3). 업종 채널과 한 자리를 나누는 중첩 방식은 업종 몫이 1/4 로 줄어
                # 9/1 에서 rich −0.06·공사 −0.04 로 전부 나빠졌다(2026-10-15 prd2-0901, 7/1·8/1 은 네트워크 단절로 미완). 평면은 공사 −0.01, 물품 +0.04~0.07, 전체 3/3 상승.
                pmask = np.array([bool(r["prdct_clsfc_nos"] & prof["codes"]) for r in notices])
                channels.insert(0, [i for i in order if pmask[i]][: min(pool * 2, CHANNEL_MAX_ROWS)])
            order = rr(*channels)
    order = order[: pool * 2]
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
    qual_fail: dict[tuple[str, str], list] = {}
    for r in cand:
        slot = lim.get((r["bid_ntce_no"], r["bid_ntce_ord"])) or {"licenses": [], "regions": []}
        q = check_qualifications(prof["names"], prof["rgn"], slot["licenses"], slot["regions"])
        if q["passed"]:
            r["qualification"] = q; passed.append(r)
        else:
            # 탈락 사유를 보고서까지 들고 간다 — 면허/지역 구분이 없어 "9월에 자격 손실이 큰 이유"를
            # 짚을 수 없었다(코덱스 지적). failures 는 check_qualifications 가 주는 사람이 읽는 문구다.
            qual_fail[(r["bid_ntce_no"], r["bid_ntce_ord"])] = q.get("failures") or []
    qualified = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in passed]
    for r in passed:
        raw, bd = score_notice(r, company_rgn=prof["rgn"], company_terms=prof["terms"], company_institutions=instts,
                               company_amt_median=median, today=t, peer_instt_counts={}, instt_stats=instt_stats)
        # ablate 된 보너스는 합에서 뺀다 — breakdown 은 그대로 둬서 features.csv 로 기여도를 볼 수 있게.
        if ablate:
            raw = sum(b["points"] for b in bd if b["key"] not in ablate)
        r["score_raw"] = round(raw, 1)
        if features_out is not None:  # 점수 재보정용 특징 덤프 (운영 경로와 무관)
            allowed = r.get("bidprc_psbl_indstryty_nm") or ""
            row = {"bid_ntce_no": r["bid_ntce_no"], "bid_ntce_ord": r["bid_ntce_ord"], "bsns_div": r.get("bsns_div_nm") or "?",
                   "sim": round(float(r["similarity"]), 4), "score_raw": r["score_raw"],
                   "has_allowed": int(bool(allowed.strip())), "industry_name_match": int(any(n in allowed for n in prof["names"])),
                   "instt_known": int(bool(instts)), "n_names": len(prof["names"])}
            for b in bd:
                # 토큰 일치는 점수가 아니라 개수로 — 점수표 배율을 바꿔도 특징이 안 변하게(2026-10-15, matched 는 5개 캡).
                row[b["key"]] = min(len(b.get("matched") or []), 3) if b["key"] == "industry_tokens" else b["points"]
            features_out.append(row)
    passed.sort(key=lambda r: r["score_raw"], reverse=True)
    scored = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in passed]
    top = passed[:MMR_POOL]
    idx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): i for i, n in enumerate(notices)}
    embs = {(r["bid_ntce_no"], r["bid_ntce_ord"]): X[idx[(r["bid_ntce_no"], r["bid_ntce_ord"])]].tolist() for r in top}
    final_rows = mmr_diversify(top, embs, k=5) + passed[MMR_POOL:]
    final = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in final_rows[:limit]]
    return {"dense": dense, "dedup": dedup, "qualified": qualified, "scored": scored, "final": final,
            "qual_fail": qual_fail}


# 결과를 몇 건 보여줄지 정하려고 같은 랭킹에서 여러 K 로 잰다 — 표시 수 결정용이고 기존 지표(final@30)와 무관하다.
# --limit 보다 큰 K 는 limit 에서 잘린 목록을 재므로 의미가 없다(항상 --limit 30 이상으로 돌릴 것).
K_CURVE = (3, 5, 8, 12, 16, 20, 25, 30)

# Supabase REST 는 한 요청에 1,000행만 돌려준다 — 운영은 채널마다 match_count=pool*2 를
# 요청하지만 실제로 받는 건 min(pool*2, 1000) 이다. 2026-10-23 실측: pool 2000/3000 을
# 요청해도 후보가 890~1,331 에서 포화했고 dense 채널 원본이 정확히 1,000 에서 멈췄다.
# 하네스는 전수 코사인을 정렬하므로 이 천장이 없어 pool>=500 에서 운영보다 낙관적이었다.
CHANNEL_MAX_ROWS = 1000

# 점수 분해(ablation)용 — score_notice 가 내는 보너스 key 전부. 'vector'(유사도)는 기준선이라 뺄 수 없다.
# 코덱스 리뷰 2번: scored 단계가 최대 손실이라는 사실만으로 가중치가 틀렸다고 단정할 수 없다.
# 유사도 단독 기준선을 만들고 보너스를 하나씩 켜서 정답의 순위 이동을 봐야 한다.
BONUS_KEYS = ("institution", "peer_institution", "instt_closed", "region",
              "budget", "budget_mismatch", "industry_tokens", "deadline_urgent")


def resolve_ablate(spec: str) -> set[str]:
    """--ablate 문자열을 뺄 key 집합으로. 'bonuses' = 유사도 외 전부(= 유사도 단독 기준선)."""
    keys: set[str] = set()
    for tok in (x.strip() for x in spec.split(",")):
        if not tok:
            continue
        if tok == "bonuses":
            keys |= set(BONUS_KEYS)
        elif tok in BONUS_KEYS:
            keys.add(tok)
        else:
            sys.exit(f"--ablate 에 모르는 key: {tok} (가능: bonuses, {', '.join(BONUS_KEYS)})")
    return keys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True); ap.add_argument("--companies", type=int, default=300)
    ap.add_argument("--pool", type=int, default=200); ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--run-id", default=None)
    ap.add_argument("--retrieval", choices=["dense", "prefilter", "soft", "hybrid", "hybrid+prd"], default=get_settings().reco_retrieval,
                     help="기본값은 운영 설정 RECO_RETRIEVAL")
    ap.add_argument("--dump-features", action="store_true", help="자격 통과 후보별 점수 특징 + 정답 여부를 features.csv 로 저장(점수 재보정용)")
    ap.add_argument("--ablate", default="", metavar="KEYS",
                    help="점수에서 뺄 보너스 key(쉼표). 'bonuses' 는 유사도 외 전부 = 유사도 단독 기준선. "
                         f"가능: bonuses, {','.join(BONUS_KEYS)}")
    ap.add_argument("--positives", choices=["winner", "participant"], default="winner", help="정답: 낙찰만 / 입찰 참가(낙찰 포함)")
    ap.add_argument("--space", choices=["openai", "kure"], default=get_settings().embed_space, help="벡터 공간: openai(embedding) / kure(embedding_k, 0045 적용 후)")
    ap.add_argument("--embeddings", default=None, help="로컬 모델 임베딩 npz (embed_local.py) — 공고·업종 벡터를 DB/OpenAI 대신 이걸로 (모델 비교 실험)")
    args = ap.parse_args()
    ablate = resolve_ablate(args.ablate)
    global EMB_STORE, EMB_SPACE, EMB_COL
    EMB_SPACE = args.space; EMB_COL = "embedding_k" if args.space == "kure" else "embedding"
    t = date.fromisoformat(args.as_of); horizon = t + timedelta(days=HORIZON_DAYS)
    run_id = args.run_id or f"{t.isoformat()}_{datetime.now():%m%d%H%M}"
    out_dir = Path(__file__).resolve().parents[1] / "data" / "recommender_eval" / run_id; out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect()
    positives = fetch_positives(conn, t, horizon, args.positives)
    sample = sample_companies(conn, positives, t, args.companies, args.seed)
    if args.embeddings:
        EMB_STORE = load_emb_store(args.embeddings)
        print(f"embeddings: {args.embeddings} (dim {EMB_STORE['dim']}, notices {len(EMB_STORE['n']):,})")
    notices, X = fetch_active_notices(conn, t, horizon)
    instt_stats = fetch_instt_stats_before(conn, t)
    nidx = {(n["bid_ntce_no"], n["bid_ntce_ord"]): n for n in notices}
    print(f"t={t} active={len(notices):,} sample={len(sample)} positives(total)={sum(len(positives[s['biz']]) for s in sample):,}")
    cache: dict = {}; per: list[dict] = []; failures: list[dict] = []; skipped = 0; all_feats: list[dict] = []; positives_dropped = 0
    for i, s in enumerate(sample, 1):
        biz = s["biz"]; pos = {k for k in positives[biz] if k in nidx}
        positives_dropped += len(positives[biz]) - len(pos)
        if not pos:
            skipped += 1; continue
        prof = fetch_company_profile(conn, biz, t)
        hist, instts, med = fetch_history_before(conn, biz, t)
        clean = strip_leaked_history(hist, positives[biz])
        vec = company_vector_at(conn, prof, clean, t, cache, s["n_hist"])  # tier 라벨과 같은 유효건수
        if vec is None:
            skipped += 1; continue
        feats: list[dict] | None = [] if args.dump_features else None
        st = replay(conn, notices, X, vec, prof, instts, med, instt_stats, t, args.pool, args.limit, args.retrieval, feats, ablate)
        # dedup 이 공고번호 단위로 차수를 접으므로(운영과 동일) 정답·순위 비교도 공고번호 단위로 한다
        # (활성 공고의 9%가 다른 차수와 공존, 정답의 4%가 그 영향 — 그대로 두면 가짜 'dedup 손실'이 생긴다)
        pos_nos = {no for no, _ in pos}
        qual_fail = st.pop("qual_fail", {})  # 단계별 순위가 아니라 사유 맵 — st_nos 변환에서 제외한다
        st_nos = {k: [no for no, _ in v] for k, v in st.items()}
        if feats is not None:
            for f in feats:
                f.update(biz=biz, tier=s["tier"], is_pos=int(f["bid_ntce_no"] in pos_nos))
                all_feats.append(f)
        div = nidx[min(pos)]["bsns_div_nm"] or "?"
        per.append({"biz": biz, "tier": s["tier"], "bsns_div": div, "n_pos": len(pos_nos),
                    "r_dense": recall_at_k(st_nos["dedup"], pos_nos, args.pool), "r_qual": recall_at_k(st_nos["qualified"], pos_nos, args.pool),
                    "r_scored30": recall_at_k(st_nos["scored"], pos_nos, args.limit), "r_final30": recall_at_k(st_nos["final"], pos_nos, args.limit),
                    # 운영 화면 조건 — 비로그인 공개 5건 / 로그인 표시 20건. final@30 은 파이프라인 상한이라 체감과 다르다.
                    "r_final5": recall_at_k(st_nos["final"], pos_nos, 5), "r_final20": recall_at_k(st_nos["final"], pos_nos, 20),
                    "mrr": mrr(st_nos["final"], pos_nos),
                    "k_curve": [recall_at_k(st_nos["final"], pos_nos, k) for k in K_CURVE]})
        title_by_no = {no: nidx[(no, od)]["bid_ntce_nm"] for no, od in sorted(pos)}
        for p in sorted(pos_nos):
            lost = stage_lost(st_nos, p, args.pool, args.limit)
            if lost != "kept":
                rank_dense = next((r for r, k in enumerate(st_nos["dense"], 1) if k == p), None)
                # 자격에서 떨어진 정답은 사유를 같이 남긴다 — 같은 공고번호의 아무 차수나 매칭(차수는 사유가 같다).
                why = next((v for (no, _), v in qual_fail.items() if no == p), None)
                failures.append({"biz": biz, "tier": s["tier"], "bid_ntce_no": p, "title": title_by_no[p], "lost_at": lost,
                                 "dense_rank": rank_dense, "qual_failures": why})
        if i % 25 == 0: print(f"  {i}/{len(sample)}")
    if not per:
        sys.exit("평가된 회사가 0곳 — 날짜/표본 조건을 확인하세요 (보고서 미생성)")
    agg = aggregate(per)
    agg["k_curve"] = {str(k): round(sum(p["k_curve"][i] for p in per) / len(per), 4) for i, k in enumerate(K_CURVE)}
    lost_counts = defaultdict(int)
    for f in failures: lost_counts[f["lost_at"]] += 1
    agg["lost_at"] = dict(lost_counts); agg["skipped"] = skipped
    agg["positives_dropped"] = positives_dropped
    manifest = {"as_of": t.isoformat(), "positives": args.positives, "space": args.space, "embeddings": args.embeddings, "horizon_days": HORIZON_DAYS, "pool": args.pool, "limit": args.limit, "seed": args.seed,
                "retrieval": args.retrieval, "ablate": sorted(ablate), "channel_max_rows": CHANNEL_MAX_ROWS,
                "companies_requested": args.companies, "companies_evaluated": len(per), "active_notices": len(notices),
                "notes": ["업종·물품·지역은 현재 값(과거 이력 없음) → '현재 등록정보 참고 평가'",
                          "회사 업종·물품은 같은 사업자번호(norm)의 모든 행 합침 (운영은 한 행 — Codex P1)",
                          "peer_instt_counts 비활성(운영과 동일), 기관통계는 t 이전 2년 계약으로 재계산",
                          "정답=낙찰(award_results.is_winner) 또는 --positives participant 면 입찰 참가(낙찰 포함). 미참가는 음성 아님",
                          "참가 이력의 시점은 openg_date(개찰일) 기준 — 운영 잡은 raw bidprcDt 를 쓰지만 t 시점 '알 수 있었던' 기준으로는 개찰일이 맞다",
                          "정답·순위 비교는 공고번호 단위(차수 무시) — 운영 dedup 과 같은 단위",
                          "게시일 = t 인 공고는 제외(bid_ntce_date < t) — 보수적, 시점당 수십 건"]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "failures.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["biz", "tier", "bid_ntce_no", "title", "lost_at", "dense_rank", "qual_failures"]); w.writeheader(); w.writerows(failures)
    m, lines = agg["macro"], []
    lines += [f"# 추천 평가 baseline — t={t} (run {run_id})", "",
              f"회사 {len(per)} (skip {skipped}) · 활성 공고 {len(notices):,} · pool {args.pool} · limit {args.limit} · retrieval {args.retrieval}"
              + (f" · ablate {','.join(sorted(ablate))}" if ablate else ""), "",
              "| 지표 | macro | micro |", "|---|---|---|"]
    lines += [f"| {k} | {m[k]:.3f} | {agg['micro'][k]:.3f} |" for k in m]
    # 군별 표는 운영 화면 조건(@5·@20)을 같이 싣는다 — final@30 은 파이프라인 상한이라 체감과 다르다.
    lines += ["", "## 군별 (macro)", "", "| 군 | n | dense@pool | qual@pool | final@5 | final@20 | final@30 | mrr |",
              "|---|---|---|---|---|---|---|---|"]
    for grp in ("by_tier", "by_div"):
        for k, v in agg[grp].items():
            lines.append(f"| {k} | {v['n']} | {v['r_dense']:.3f} | {v['r_qual']:.3f} | "
                         f"{v.get('r_final5', 0):.3f} | {v.get('r_final20', 0):.3f} | {v['r_final30']:.3f} | {v['mrr']:.3f} |")
    lines += ["", "## 정답이 사라진 단계", "",
              "- dense: dense 상위 pool×2 밖 · dedup: 후보 풀 pool 컷(지문 중복 제거 포함) · qualified: 자격 하드 제외 · scored: 점수 순위 limit 밖 · final: MMR 에 밀림",
              "", "| 단계 | 건수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(lost_counts.items(), key=lambda x: -x[1])]
    lines += ["", "## K 곡선 — 결과를 몇 건 보여줄까 (macro, 같은 랭킹)", "", "| K | final@K | 직전 K 대비 |", "|---|---|---|"]
    prev = 0.0
    for k in K_CURVE:
        v = agg["k_curve"][str(k)]
        lines.append(f"| {k} | {v:.3f} | +{v - prev:.3f} |")
        prev = v
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if all_feats:
        cols = sorted({k for f in all_feats for k in f}, key=lambda k: (k not in ("biz", "tier", "bid_ntce_no", "bid_ntce_ord", "is_pos"), k))
        with (out_dir / "features.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, restval=0); w.writeheader(); w.writerows(all_feats)
        lines.append(f"features.csv: {len(all_feats):,} rows")
    print("\n".join(lines)); print(f"\nsaved: {out_dir}")


if __name__ == "__main__":
    main()

"""v2 랭킹 오케스트레이션 — recommend.py의 후보 검색 뒤에서 분기되어 호출된다.

v1(rerank 소프트 감점)과의 차이:
  1. 자격 미충족 공고는 하드 제외 (감점 아님)
  2. 가중치 합산 점수 + 라벨 breakdown (score_breakdown)
  3. top 5는 MMR로 다양성 보장

순환 import 주의: recommend.py → (함수 내 lazy import) → 이 모듈 → recommend.py 헬퍼.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from app.core.progress import emit
from app.core.timing import submit_timed, timed
from app.recommender.cancellation import cancel_ords, drop_cancelled
from app.recommender.collaborative import fetch_institution_stats
from app.recommender.mmr import mmr_diversify
from app.recommender.qualifications import check_qualifications, unverified_penalty
from app.recommender.score import score_notice

MMR_POOL = 40  # MMR·임베딩 fetch 대상 상위 후보 수
SCORE_DISPLAY_DIVISOR = 200.0  # raw(대략 0~240) → 프론트 0~1 표시 스케일


def rank_v2(
    client,
    candidates: list[dict],
    *,
    company_rgn: str | None,
    company_terms: set[str],
    company_institutions: set[str],
    company_amt_median: float | None,
    company_industry_names: set[str],
    limit: int,
    company_embedding_str: str | None = None,
    company_bizrno_norm: str | None = None,
    embeddings_out: dict | None = None,
) -> list[dict]:
    from app.services.recommend import _fetch_eligibility, _fetch_notice_status, _fetch_result_embeddings

    bid_keys = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in candidates]
    bid_nos = sorted({k[0] for k in bid_keys if k[0]})
    # 자격 데이터와 공고 상태는 서로 독립 — 같이 보내 왕복 한 번 값으로 끝낸다
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_elig = submit_timed(ex, "eligibility", _fetch_eligibility, client, bid_keys)
        f_status = submit_timed(ex, "notice_status", _fetch_notice_status, client, bid_nos)
        elig = f_elig.result()
        try:
            cmap = cancel_ords(f_status.result())
        except Exception as e:  # 상태 조회 실패 — 취소 제외 없이 나머지는 그대로
            print(f"[rank_v2] notice status skipped: {e}")
            cmap = {}
    n_before = len(candidates)
    candidates = drop_cancelled(candidates, cmap)   # 취소공고와 그 원공고 — cancellation.py

    passed: list[dict] = []
    for r in candidates:
        slot = elig.get((r["bid_ntce_no"], r["bid_ntce_ord"])) or {
            "licenses": [],
            "regions": [],
        }
        q = check_qualifications(
            company_industry_names, company_rgn, slot["licenses"], slot["regions"],
            license_text=r.get("bidprc_psbl_indstryty_nm"),
        )
        if not q["passed"]:
            continue
        r["qualification"] = q
        passed.append(r)
    emit("stage", stage="qualify", candidates=n_before, passed=len(passed), cancelled=n_before - len(candidates))

    # peer 탐색(match_companies RPC)은 껐다. 그 RPC 가 타는 companies_embedding_idx
    # (HNSW 489MB)가 shared_buffers 256MB 의 두 배여서 캐시에 못 올라가고, DB 전체를
    # 디스크 I/O 기아로 만들고 있었다 — 55행 인덱스 스캔 1.2초, 회사 페이지 19초
    # (2026-09-21 측정). 인덱스를 걷어내면서 호출도 같이 끈다. 인덱스 없이 호출만 두면
    # 14만 행 seq scan 이라 매 요청이 statement timeout 까지 기다린 뒤 degrade 한다.
    # 되살리려면 인덱스 재생성(비싸다)부터. 기관 반복 발주 통계는 별개 RPC 라 그대로 쓴다.
    peer_instt_counts: dict[str, int] = {}
    instt_stats: dict[str, dict] = {}
    try:
        cand_instts = {
            (r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "").strip()
            for r in passed
        }
        with timed("instt_stats"):
            instt_stats = fetch_institution_stats(client, cand_instts)
    except Exception as e:
        # 0015 RPC 미적용 등 — 협업 시그널 없이 v2 나머지는 그대로 동작
        print(f"[rank_v2] collaborative signals skipped: {e}")

    today = date.today()
    for r in passed:
        raw, breakdown = score_notice(
            r,
            company_rgn=company_rgn,
            company_terms=company_terms,
            company_institutions=company_institutions,
            company_amt_median=company_amt_median,
            today=today,
            peer_instt_counts=peer_instt_counts,
            instt_stats=instt_stats,
        )
        pen = unverified_penalty(r["qualification"])   # 면허 확인불가(회사 업종 미상)만 감점
        if r["qualification"]["unverified"]:
            breakdown.append(
                {"key": "qual_unverified", "label": "자격 확인불가", "points": -pen}
            )
        r["score_raw"] = round(raw - pen, 1)
        r["score_breakdown"] = breakdown
        r["base_similarity"] = r.get("similarity", 0)
        # 기존 UI(scorePercent)가 0~1 기대 → 표시용 정규화
        r["score"] = max(0.01, min(raw / SCORE_DISPLAY_DIVISOR, 0.99))

    passed.sort(key=lambda r: r["score_raw"], reverse=True)
    pool = passed[:MMR_POOL]
    with timed("mmr_embeddings"):
        embeddings = _fetch_result_embeddings(client, pool)
    if embeddings_out is not None:
        # 호출부(viz)가 같은 공고 벡터를 다시 읽지 않도록 넘겨준다
        embeddings_out.update(embeddings)
    diversified = mmr_diversify(pool, embeddings, k=5) + passed[MMR_POOL:]
    out = diversified[:limit]
    emit("stage", stage="rank", results=len(out))
    return out

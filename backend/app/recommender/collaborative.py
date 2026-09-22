"""Phase 2 협업 시그널 — 유사 회사들의 낙찰 행동 + 기관 개방성.

LLM이 텍스트만 볼 때 우리는 "이 회사와 비슷한 회사들이 실제로 어디서
수주하는가"를 본다 (moat 시그널). RPC: 0015_collaborative_rpc.sql.
"""

from __future__ import annotations

from datetime import date, timedelta

PEER_COUNT = 20
PEER_MONTHS = 3
STATS_YEARS = 2


def fetch_peer_institutions(
    client,
    embedding_str: str,
    exclude_bizrno_norm: str | None,
    k: int = PEER_COUNT,
    months: int = PEER_MONTHS,
) -> dict[str, int]:
    """유사 회사 top-k가 최근 낙찰받은 기관별 건수."""
    peers = (
        client.rpc(
            "match_companies",
            {
                "query_embedding": embedding_str,
                "match_count": k,
                "exclude_bizrno_norm": exclude_bizrno_norm,
            },
        )
        .execute()
        .data
        or []
    )
    norms = [p["bizrno_norm"] for p in peers if p.get("bizrno_norm")]
    if not norms:
        return {}

    since = (date.today() - timedelta(days=months * 30)).isoformat()
    rows = (
        client.table("contracts")
        .select("dmnd_instt_nm")
        .in_("rprsnt_corp_bizrno_norm", norms)
        .gte("cntrct_cncls_date", since)
        .execute()
        .data
        or []
    )
    counts: dict[str, int] = {}
    for r in rows:
        instt = (r.get("dmnd_instt_nm") or "").strip()
        if instt:
            counts[instt] = counts.get(instt, 0) + 1
    return counts


def fetch_institution_stats(
    client, institutions: set[str], years: int = STATS_YEARS
) -> dict[str, dict]:
    """기관별 {total, distinct_winners} — 반복거래율 계산 재료.

    0038 의 미리 계산된 MV 를 먼저 본다. 매 요청 contracts 를 다시 집계하던 원래 RPC 는
    추천 전체의 57~71%(4~6초)를 먹었다(2026-09-22 Server-Timing 실측). MV 창은 2년 고정이라
    years 가 기본값일 때만 쓰고, 0038 미적용·빈 MV 면 원래 RPC 로 degrade 한다.
    """
    instts = sorted(i for i in institutions if i)
    if not instts:
        return {}
    if years == STATS_YEARS:
        try:
            rows = (
                client.rpc("institution_repeat_stats_cached", {"p_instts": instts})
                .execute()
                .data
                or []
            )
            # 빈 결과는 "그 기관들은 2년 내 계약이 없다"는 정상 답이다 — 느린 RPC 로 되묻지 않는다.
            # 채우기 전 MV 는 비어서 오는 게 아니라 "not been populated" 에러라 아래로 간다.
            return {r["dmnd_instt_nm"]: r for r in rows}
        except Exception:
            pass
    since = (date.today() - timedelta(days=years * 365)).isoformat()
    rows = (
        client.rpc(
            "institution_repeat_stats",
            {"p_instts": instts, "p_since": since},
        )
        .execute()
        .data
        or []
    )
    return {r["dmnd_instt_nm"]: r for r in rows}

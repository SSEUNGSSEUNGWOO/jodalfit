"""Supabase 수집 — 사람 행동·제품 건강(RPC marketing_daily_stats, 0033) + 색인 표본 URL(sitemap_urls MV)."""

from __future__ import annotations

import time
from datetime import date

from postgrest.exceptions import APIError

from app.services.supabase_client import get_admin_client


def daily_stats(day: date) -> dict:
    """평소 3초. DB 가 인덱스 빌드 등으로 바쁘면 8초 timeout(57014)에 걸리므로 한 번 더 시도."""
    sb = get_admin_client()
    for attempt in range(2):
        try:
            return sb.rpc("marketing_daily_stats", {"p_date": day.isoformat()}).execute().data
        except APIError as e:
            if e.code != "57014" or attempt == 1:
                raise
            time.sleep(5)


def sample_urls(domain: str, cfg: dict) -> list[str]:
    """sitemap_urls 에서 seq 가 배수인 URL — 매일 같은 표본이라 색인 비율 추세가 된다.
    seq 목록을 직접 지정해 (kind, seq) 유니크 인덱스로 조회한다 (범위 조회는 PostgREST 1,000행 상한에 잘림)."""
    sb = get_admin_client()
    out: list[str] = []
    for kind, every in (("company", cfg["company_every"]), ("notice", cfg["notice_every"])):
        seqs = [i * every for i in range(cfg["max_per_kind"])]
        rows = (
            sb.table("sitemap_urls").select("seq,path").eq("kind", kind).in_("seq", seqs)
            .order("seq").execute().data or []
        )
        out.extend(f"https://{domain}{r['path']}" for r in rows)
    return out

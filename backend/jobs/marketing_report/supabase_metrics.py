"""Supabase 수집 — 사람 행동·제품 건강(RPC marketing_daily_stats, 0033) + 색인 표본 URL(sitemap_urls MV)."""

from __future__ import annotations

from datetime import date

from app.services.supabase_client import get_admin_client


def daily_stats(day: date) -> dict:
    sb = get_admin_client()
    return sb.rpc("marketing_daily_stats", {"p_date": day.isoformat()}).execute().data


def sample_urls(domain: str, cfg: dict) -> list[str]:
    """sitemap_urls 에서 seq 가 배수인 URL — 매일 같은 표본이라 색인 비율 추세가 된다."""
    sb = get_admin_client()
    out: list[str] = []
    for kind, every in (("company", cfg["company_every"]), ("notice", cfg["notice_every"])):
        rows = (
            sb.table("sitemap_urls").select("seq,path").eq("kind", kind)
            .order("seq").limit(every * cfg["max_per_kind"]).execute().data or []
        )
        picked = [r["path"] for r in rows if r["seq"] % every == 0][: cfg["max_per_kind"]]
        out.extend(f"https://{domain}{p}" for p in picked)
    return out

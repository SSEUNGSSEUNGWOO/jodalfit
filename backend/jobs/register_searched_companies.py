"""검색됐는데 없던 회사 등록 — 실사용자가 사업자번호로 찾았는데 companies 에 없던 회사를 조달청에서 받아 온다.

2026-09-18: 실사용 "회사를 찾을 수 없음" 사업자번호 8개 중 5개가 조달청엔 조달업체로 등록돼 있었다.
계약·입찰 참가 이력이 없어 수집한 적이 없었을 뿐이라, 등록업종만 받아 오면 업종 벡터(콜드스타트)로 바로 추천이 된다.

백엔드(Railway)는 해외 IP 라 나라장터 API 가 막혀 있어서, 요청 시점이 아니라 이 PC의 매시 수집(hourly-sync.ps1)에서 돈다.
화면은 사업자번호를 못 찾으면 "1시간 안에 준비"라고 안내한다 (BoardView FallbackBoard).

흐름 (회사 하나당 API 3회: 기본정보·등록업종·공급물품):
  1) search_logs(source='user', 최근 N일) 에서 "회사를 찾을 수 없습니다" + 10자리 사업자번호 입력
  2) companies 에 없고, company_lookup_attempts 에 7일 내 not_found 가 없는 번호
  3) 기본정보 → companies upsert / 없으면 not_found 기록
  4) 등록업종·공급물품 → upsert
  5) 회사 벡터 (compute_company_vectors.process_chunk 재사용) → 다음 검색부터 추천

실행:
    cd backend
    uv run python -m jobs.register_searched_companies            # 최근 30일
    uv run python -m jobs.register_searched_companies --days 90 --limit 50
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta, timezone

from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start, upsert_embeddings_with_retry
from jobs.backfill_companies_basic import fetch_basic
from jobs.compute_company_vectors import process_chunk
from jobs.ingest_companies_userinfo import map_item
from jobs.ingest_company_details import fetch_industries, fetch_supply, map_industry, map_supply

JOB_NAME = "register_searched_companies"
RETRY_NOT_FOUND_DAYS = 7


def _bizrno_input(q: str | None) -> str | None:
    """'123-45-67890' / '1234567890' 같은 사업자번호 입력만. 회사명·공고명은 키워드 검색으로 넘어간다."""
    q = (q or "").strip()
    digits = re.sub(r"\D", "", q)
    return digits if len(digits) == 10 and re.fullmatch(r"[\d\-\s]+", q) else None


def find_candidates(client, days: int) -> list[str]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (
        client.table("search_logs").select("query")
        .eq("source", "user").eq("mode", "company")
        .like("error_msg", "회사를 찾을 수 없%")
        .gte("created_at", since).limit(1000).execute().data or []
    )
    wanted = sorted({b for b in (_bizrno_input(r["query"]) for r in rows) if b})
    if not wanted:
        return []
    known = {r["bizrno_norm"] for r in client.table("companies").select("bizrno_norm").in_("bizrno_norm", wanted).execute().data or []}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETRY_NOT_FOUND_DAYS)).isoformat()
    recent_miss = {
        r["bizrno_norm"] for r in client.table("company_lookup_attempts").select("bizrno_norm")
        .in_("bizrno_norm", wanted).eq("result", "not_found").gte("checked_at", cutoff).execute().data or []
    }
    return [b for b in wanted if b not in known and b not in recent_miss]


def register(client, norm: str) -> dict:
    item = fetch_basic(norm)
    if item is None:
        return {"bizrno_norm": norm, "result": "not_found"}
    row = map_item(item)
    upsert_rows("companies", [row], on_conflict="bizrno")
    biz = row["bizrno"]
    inds = [r for r in (map_industry(it, biz) for it in fetch_industries(norm)) if r]
    sups = [r for r in (map_supply(it, biz) for it in fetch_supply(norm)) if r]
    if inds:
        upsert_rows("company_industries", inds, on_conflict="bizrno,indstryty_cd", ignore_duplicates=True)
    if sups:
        upsert_rows("company_supply_products", sups, on_conflict="bizrno,dtl_prdct_clsfc_no", ignore_duplicates=True)
    updates, _ = process_chunk(client, [norm])
    if updates:
        upsert_embeddings_with_retry(client, "update_company_embeddings", updates)
    return {"bizrno_norm": norm, "result": "registered", "corp_nm": row.get("corp_nm"),
            "n_industries": len(inds), "n_supplies": len(sups), "vector_built": bool(updates)}


def run(days: int = 30, limit: int = 100) -> None:
    run_id = log_ingest_start(JOB_NAME, {"days": days, "limit": limit})
    client = get_admin_client()
    registered = not_found = errors = 0
    try:
        targets = find_candidates(client, days)[:limit]
        print(f"[{JOB_NAME}] 대상 {len(targets)}개")
        for norm in targets:
            try:
                rec = register(client, norm)
            except Exception as e:  # httpx 오류 메시지엔 ServiceKey 가 든 URL 이 섞이므로 종류만 남긴다
                rec = {"bizrno_norm": norm, "result": "error", "detail": type(e).__name__}
            rec["checked_at"] = datetime.now(timezone.utc).isoformat()
            upsert_rows("company_lookup_attempts", [rec], on_conflict="bizrno_norm")
            registered += rec["result"] == "registered"
            not_found += rec["result"] == "not_found"
            errors += rec["result"] == "error"
            print(f"  {norm}: {rec['result']} {rec.get('corp_nm') or ''} "
                  f"업종 {rec.get('n_industries', '-')} 물품 {rec.get('n_supplies', '-')} 벡터 {rec.get('vector_built', '-')}")
        log_ingest_finish(run_id, "success", rows_inserted=registered, rows_failed=errors)
        print(f"[{JOB_NAME}] done. registered={registered} not_found={not_found} errors={errors}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=registered, rows_failed=errors, error_msg=str(e))
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="최근 며칠의 검색을 볼지")
    ap.add_argument("--limit", type=int, default=100, help="한 번에 조회할 최대 회사 수 (회사당 API 3회)")
    args = ap.parse_args()
    run(args.days, args.limit)

"""회사별 등록업종 + 공급물품 풍부화 (UsrInfoService02).

핵심 데이터 — v0.2 알고리즘 전환의 메인 시그널.
"이 회사가 뭐하는 회사인가" = 등록업종 + 공급물품

소스:
- getPrcrmntCorpIndstrytyInfo02 (필수: bizno, inqryDiv=1)
- getPrcrmntCorpSplyPrdctInfo02 (필수: bizno)

전략:
- contracts에 등장한 active 회사만 대상
- 우선순위: ① 유저가 검색한 회사 (search_logs, 최근 검색 순)
           ② 최근 계약 체결 회사 (cntrct_cncls_date desc)
           ③ 나머지 active 회사
- 이미 enriched된 회사는 skip
- 회사당 2개 API 호출
- 일일 한도 각 10k → 한 잡 실행에 4500 회사 처리 (안전 마진)
- active 회사 전부 풍부화에 ~4일 분산

실행:
    cd backend
    uv run python -m jobs.ingest_company_details --limit 4500
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start, to_timestamptz, to_yn

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
BASE = "https://apis.data.go.kr/1230000/ao/UsrInfoService02"
JOB_NAME = "ingest_company_details"


def fetch_industries(bizrno_norm: str) -> list[dict[str, Any]]:
    params = {
        "ServiceKey": API_KEY,
        "type": "json",
        "pageNo": "1",
        "numOfRows": "50",
        "bizno": bizrno_norm,
        "inqryDiv": "1",
    }
    try:
        resp = httpx.get(
            f"{BASE}/getPrcrmntCorpIndstrytyInfo02", params=params, timeout=15.0
        )
        data = resp.json()
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        return items if isinstance(items, list) else []
    except Exception:
        return []


def fetch_supply(bizrno_norm: str) -> list[dict[str, Any]]:
    params = {
        "ServiceKey": API_KEY,
        "type": "json",
        "pageNo": "1",
        "numOfRows": "100",
        "bizno": bizrno_norm,
    }
    try:
        resp = httpx.get(
            f"{BASE}/getPrcrmntCorpSplyPrdctInfo02", params=params, timeout=15.0
        )
        data = resp.json()
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        return items if isinstance(items, list) else []
    except Exception:
        return []


def fetch_priority_ranks(client) -> dict[str, tuple[int, int]]:
    """bizrno_norm → (tier, rank) 우선순위 맵.

    tier 0 = 유저가 검색한 회사 (최근 검색 순)
    tier 1 = 최근 계약 체결 회사 (계약일 desc, 상위 ~10k행)
    맵에 없으면 tier 2 (나머지 active).
    """
    ranks: dict[str, tuple[int, int]] = {}

    # tier 1: 최근 계약 체결 순 (상위 10k행 — 대략 최근 1~2주 분량이면 충분)
    print("  ↳ 최근 계약 회사 순위 수집 중...")
    offset = 0
    idx = 0
    while offset < 10000:
        r = (
            client.table("contracts")
            .select("rprsnt_corp_bizrno_norm")
            .not_.is_("rprsnt_corp_bizrno_norm", "null")
            .order("cntrct_cncls_date", desc=True)
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            v = row.get("rprsnt_corp_bizrno_norm")
            if v and v not in ranks:
                ranks[v] = (1, idx)
                idx += 1
        if len(r) < 1000:
            break
        offset += 1000

    # tier 0: 유저가 검색한 회사 (최근 검색 순) — tier 1보다 우선하므로 덮어씀
    print("  ↳ 검색된 회사 순위 수집 중...")
    offset = 0
    idx = 0
    while offset < 10000:
        r = (
            client.table("search_logs")
            .select("matched_bizrno")
            .not_.is_("matched_bizrno", "null")
            .order("created_at", desc=True)
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            norm = "".join(ch for ch in (row.get("matched_bizrno") or "") if ch.isdigit())
            if norm and ranks.get(norm, (9, 0))[0] > 0:
                ranks[norm] = (0, idx)
                idx += 1
        if len(r) < 1000:
            break
        offset += 1000

    searched = sum(1 for t, _ in ranks.values() if t == 0)
    print(f"  ↳ priority: 검색된 회사 {searched:,} / 최근 수주 {len(ranks) - searched:,}")
    return ranks


def fetch_candidate_companies(client, limit: int) -> list[dict]:
    """active 회사 중 아직 업종 풍부화 안 된 회사를 우선순위 순으로 가져옴."""
    # 1. active bizrno_norm set (contracts에서)
    print("  ↳ active bizrnos 수집 중...")
    active = set()
    offset = 0
    while True:
        r = (
            client.table("contracts")
            .select("rprsnt_corp_bizrno_norm")
            .not_.is_("rprsnt_corp_bizrno_norm", "null")
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            v = row.get("rprsnt_corp_bizrno_norm")
            if v:
                active.add(v)
        if len(r) < 1000:
            break
        offset += 1000
    print(f"  ↳ active = {len(active):,}")

    # 2. 이미 풍부화된 bizrno set (company_industries에 row 있는 회사)
    print("  ↳ 이미 풍부화된 회사 수집 중...")
    enriched = set()
    offset = 0
    while True:
        r = (
            client.table("company_industries")
            .select("bizrno")
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            v = row.get("bizrno")
            if v:
                enriched.add(v)
        if len(r) < 1000:
            break
        offset += 1000
    print(f"  ↳ enriched = {len(enriched):,}")

    # 3. 우선순위 맵 (검색된 회사 / 최근 수주 회사)
    ranks = fetch_priority_ranks(client)

    # 4. companies 전체 순회 — bizrno_norm in active AND bizrno not in enriched
    #    (우선순위 정렬을 위해 limit에서 멈추지 않고 전부 모은 뒤 sort)
    print("  ↳ candidates 추출 중...")
    candidates: list[dict] = []
    offset = 0
    while True:
        r = (
            client.table("companies")
            .select("bizrno,bizrno_norm,corp_nm")
            .not_.is_("bizrno_norm", "null")
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            if (
                row["bizrno_norm"] in active
                and row["bizrno"] not in enriched
            ):
                candidates.append(row)
        if len(r) < 1000:
            break
        offset += 1000

    fallback = (2, 0)
    candidates.sort(key=lambda row: ranks.get(row["bizrno_norm"], fallback))
    picked = candidates[:limit]
    tier_counts = [0, 0, 0]
    for row in picked:
        tier_counts[ranks.get(row["bizrno_norm"], fallback)[0]] += 1
    print(
        f"  ↳ 선정 {len(picked):,} / 후보 {len(candidates):,}"
        f"  (검색됨 {tier_counts[0]:,} / 최근수주 {tier_counts[1]:,} / 기타 {tier_counts[2]:,})"
    )
    return picked


def map_industry(it: dict, bizrno: str) -> dict | None:
    cd = it.get("indstrytyCd")
    if not cd:
        return None
    return {
        "bizrno": bizrno,
        "indstryty_cd": cd,
        "indstryty_nm": it.get("indstrytyNm"),
        "rgst_dt": to_timestamptz(it.get("rgstDt")),
        "valid_to_dt": to_timestamptz(it.get("vldPrdExprtDt")),
        "indstryty_sttus_nm": it.get("indstrytyStatsNm") or None,
        "rprsnt_indstryty_yn": to_yn(it.get("rprsntIndstrytyYn")),
        "raw": it,
    }


def map_supply(it: dict, bizrno: str) -> dict | None:
    no = it.get("dtilPrdctClsfcNo")
    if not no:
        return None
    return {
        "bizrno": bizrno,
        "dtl_prdct_clsfc_no": no,
        "dtl_prdct_clsfc_nm": it.get("dtilPrdctClsfcNoNm"),
        "rgst_dt": to_timestamptz(it.get("rgstDt")),
        "rprsnt_prdct_yn": to_yn(it.get("rprsntPrdctClsfcNoNmYn")),
        "raw": it,
    }


def run(limit: int = 4500, batch: int = 100) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    client = get_admin_client()

    print(f"[{JOB_NAME}] fetching candidates...")
    candidates = fetch_candidate_companies(client, limit)
    print(f"[{JOB_NAME}] target = {len(candidates):,} companies")

    total_ind = 0
    total_sup = 0
    processed = 0
    failed = 0

    ind_batch: list[dict] = []
    sup_batch: list[dict] = []

    try:
        for i, corp in enumerate(candidates):
            try:
                ind_items = fetch_industries(corp["bizrno_norm"])
                sup_items = fetch_supply(corp["bizrno_norm"])
            except Exception:
                failed += 1
                continue

            for it in ind_items:
                row = map_industry(it, corp["bizrno"])
                if row:
                    ind_batch.append(row)
            for it in sup_items:
                row = map_supply(it, corp["bizrno"])
                if row:
                    sup_batch.append(row)

            processed += 1

            # 배치 단위 flush
            if len(ind_batch) >= batch:
                upsert_rows(
                    "company_industries",
                    ind_batch,
                    on_conflict="bizrno,indstryty_cd",
                    ignore_duplicates=True,
                )
                total_ind += len(ind_batch)
                ind_batch.clear()
            if len(sup_batch) >= batch:
                upsert_rows(
                    "company_supply_products",
                    sup_batch,
                    on_conflict="bizrno,dtl_prdct_clsfc_no",
                    ignore_duplicates=True,
                )
                total_sup += len(sup_batch)
                sup_batch.clear()

            if processed % 100 == 0:
                print(
                    f"  [{processed}/{len(candidates)}]  ind={total_ind + len(ind_batch)}  sup={total_sup + len(sup_batch)}  failed={failed}"
                )

        # 마지막 잔여분 flush
        if ind_batch:
            upsert_rows(
                "company_industries",
                ind_batch,
                on_conflict="bizrno,indstryty_cd",
                ignore_duplicates=True,
            )
            total_ind += len(ind_batch)
        if sup_batch:
            upsert_rows(
                "company_supply_products",
                sup_batch,
                on_conflict="bizrno,dtl_prdct_clsfc_no",
                ignore_duplicates=True,
            )
            total_sup += len(sup_batch)

        log_ingest_finish(
            run_id,
            "success",
            rows_inserted=total_ind + total_sup,
            rows_failed=failed,
        )
        print(
            f"[{JOB_NAME}] done. {processed:,} companies / {total_ind:,} industries / {total_sup:,} supplies / {failed} failed"
        )
    except Exception as e:
        log_ingest_finish(
            run_id, "failed", rows_inserted=total_ind + total_sup, error_msg=str(e)
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=4500)
    parser.add_argument("--batch", type=int, default=100)
    args = parser.parse_args()
    run(args.limit, args.batch)

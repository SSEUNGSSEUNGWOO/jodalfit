"""데이터 신선도 점검 — 각 테이블의 적재 시점 / 최신 데이터 시점."""

from app.services.supabase_client import get_admin_client


def main():
    c = get_admin_client()

    print("=== bid_notices (입찰공고) ===")
    newest = c.table("bid_notices").select("bid_ntce_date,created_at").order("bid_ntce_date", desc=True).limit(1).execute().data
    oldest = c.table("bid_notices").select("bid_ntce_date,created_at").order("bid_ntce_date").limit(1).execute().data
    cnt = c.table("bid_notices").select("*", count="exact").limit(0).execute().count
    print(f"  총 {cnt:,}건")
    if newest: print(f"  최신 공고일: {newest[0]['bid_ntce_date']}  (DB 적재 {newest[0]['created_at'][:10]})")
    if oldest: print(f"  가장 오래된 공고일: {oldest[0]['bid_ntce_date']}")

    print("\n=== contracts (계약) ===")
    newest = c.table("contracts").select("cntrct_cncls_date,created_at").order("cntrct_cncls_date", desc=True).limit(1).execute().data
    oldest = c.table("contracts").select("cntrct_cncls_date,created_at").order("cntrct_cncls_date").limit(1).execute().data
    cnt = c.table("contracts").select("*", count="exact").limit(0).execute().count
    print(f"  총 {cnt:,}건")
    if newest: print(f"  최신 계약일: {newest[0]['cntrct_cncls_date']}  (DB 적재 {newest[0]['created_at'][:10]})")
    if oldest: print(f"  가장 오래된 계약일: {oldest[0]['cntrct_cncls_date']}")

    print("\n=== companies (회사 마스터) ===")
    cnt = c.table("companies").select("*", count="exact").limit(0).execute().count
    with_vec = c.table("companies").select("*", count="exact").not_.is_("embedded_at", "null").limit(0).execute().count
    print(f"  총 {cnt:,}건 / 벡터 보유 {with_vec:,}건")

    print("\n=== pre_specs / pre_spec_opinions / order_plans ===")
    for t in ["pre_specs", "pre_spec_opinions", "order_plans"]:
        cnt = c.table(t).select("*", count="exact").limit(0).execute().count
        print(f"  {t}: {cnt:,}건")

    print("\n=== ingest_runs (수집 잡 실행 기록) ===")
    runs = c.table("ingest_runs").select("job_name,started_at,status,rows_inserted").order("started_at", desc=True).limit(8).execute().data
    for r in runs:
        print(f"  {r['started_at'][:19]}  {r['job_name']:<35} {r['status']:<10} rows={r.get('rows_inserted')}")


if __name__ == "__main__":
    main()

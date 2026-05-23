"""Supabase 연결 + 스키마 적용 여부 검증.

실행:
    cd backend
    uv run python -m jobs.verify_setup
"""

from app.services.supabase_client import get_admin_client


TABLES = [
    "bid_notices",
    "contracts",
    "pre_specs",
    "pre_spec_opinions",
    "order_plans",
    "companies",
    "company_industries",
    "company_supply_products",
    "industries_baselaw",
    "award_results",
    "subscribers",
    "ingest_runs",
]


def main() -> None:
    client = get_admin_client()
    print("Supabase admin client 연결 OK")
    print()
    print(f"{'table':<30} {'rows':>8}")
    print("-" * 40)
    for t in TABLES:
        try:
            res = client.table(t).select("*", count="exact").limit(0).execute()
            print(f"{t:<30} {res.count:>8}")
        except Exception as e:
            print(f"{t:<30} ERROR: {e}")


if __name__ == "__main__":
    main()

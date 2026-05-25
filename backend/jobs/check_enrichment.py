"""풍부화 진행 상태 점검."""

from app.services.supabase_client import get_admin_client


def main():
    c = get_admin_client()

    ind = c.table("company_industries").select("*", count="exact").limit(0).execute().count
    sup = c.table("company_supply_products").select("*", count="exact").limit(0).execute().count

    # active 회사 풀
    active = set()
    offset = 0
    while True:
        r = (
            c.table("contracts")
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

    # enriched 회사 (industries 보유)
    enriched_pks = set()
    offset = 0
    while True:
        r = (
            c.table("company_industries")
            .select("bizrno")
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            if row.get("bizrno"):
                enriched_pks.add(row["bizrno"])
        if len(r) < 1000:
            break
        offset += 1000

    cnt = c.table("companies").select("*", count="exact").limit(0).execute().count

    print("=== 풍부화 진행 상태 ===")
    print(f"전체 companies:           {cnt:,}")
    print(f"active 회사 (contracts):  {len(active):,}")
    print(f"enriched 회사 (industries 보유): {len(enriched_pks):,}")
    print(f"  → enriched / active:    {len(enriched_pks)/len(active)*100:.1f}%")
    print(f"company_industries 행:    {ind:,}")
    print(f"company_supply_products 행: {sup:,}")


if __name__ == "__main__":
    main()

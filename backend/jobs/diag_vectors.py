"""회사 벡터 매칭 안 되는 원인 진단."""

from app.services.supabase_client import get_admin_client


def main():
    c = get_admin_client()

    print("=== 1. contracts.rprsnt_corp_bizrno_norm 분포 ===")
    sample = (
        c.table("contracts")
        .select("rprsnt_corp_bizrno,rprsnt_corp_bizrno_norm,rprsnt_corp_nm")
        .not_.is_("rprsnt_corp_bizrno_norm", "null")
        .limit(10)
        .execute()
        .data
    )
    for r in sample:
        bz = r.get("rprsnt_corp_bizrno_norm") or ""
        print(
            f"  raw={r['rprsnt_corp_bizrno']!r:20} norm={bz!r:14} len={len(bz)} corp={r['rprsnt_corp_nm']}"
        )

    print("\n=== 2. companies stub: bizrno 형식 sample ===")
    sample2 = (
        c.table("companies")
        .select("bizrno,bizrno_norm,corp_nm")
        .limit(10)
        .execute()
        .data
    )
    for r in sample2:
        bz = r.get("bizrno_norm") or ""
        print(
            f"  bizrno={r['bizrno']!r:20} norm={bz!r:14} len={len(bz)} corp={r['corp_nm']}"
        )

    print("\n=== 3. 같은 bizrno_norm로 양쪽 매칭 테스트 ===")
    # contracts에서 하나 뽑아서 companies 매칭 시도
    t = sample[0]
    target = t["rprsnt_corp_bizrno_norm"]
    matched = (
        c.table("companies")
        .select("bizrno,corp_nm")
        .eq("bizrno_norm", target)
        .execute()
        .data
    )
    print(f"  contracts bizrno_norm={target!r}")
    print(f"  matched companies: {matched}")

    print("\n=== 4. 회사 풀 통계 ===")
    only_contracts = (
        c.table("companies")
        .select("*", count="exact")
        .like("bizrno", "%-%")
        .limit(0)
        .execute()
        .count
    )
    no_dash = (
        c.table("companies")
        .select("*", count="exact")
        .not_.like("bizrno", "%-%")
        .limit(0)
        .execute()
        .count
    )
    print(f"  companies with dashes: {only_contracts}")
    print(f"  companies without dashes: {no_dash}")


if __name__ == "__main__":
    main()

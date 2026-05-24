"""벡터가 있는 회사 sample을 JSON으로 저장."""

import json
from pathlib import Path

from app.services.supabase_client import get_admin_client


def main():
    c = get_admin_client()
    r = (
        c.table("companies")
        .select("bizrno,bizrno_norm,corp_nm,rgn_nm,corp_bsns_div_nm,ceo_nm")
        .not_.is_("embedded_at", "null")
        .limit(20)
        .execute()
        .data
    )
    out = Path(__file__).resolve().parent.parent.parent / "data" / "sample_companies.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(r)} companies to {out}")


if __name__ == "__main__":
    main()

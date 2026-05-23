"""계약 수집 잡 (회사 수주 시그널 ⭐).

소스: PubDataOpnStdService/getDataSetOpnStdCntrctInfo
조회조건: 계약체결일자 (inqryDiv=1 + inqryBgnDt/EndDt)

부수효과: companies 테이블에 새 사업자번호 등록 + contract_count 증가.

실행:
    cd backend
    uv run python -m jobs.ingest_contracts --days-back 1
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta

from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import (
    DATE_FMT,
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_date,
    to_int,
)

URL = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdCntrctInfo"
JOB_NAME = "ingest_contracts"


def map_item(it: dict) -> dict:
    return {
        "cntrct_no": it.get("cntrctNo"),
        "cntrct_ord": it.get("cntrctOrd") or "01",
        "unty_cntrct_no": it.get("untyCntrctNo"),
        "bid_ntce_no": it.get("bidNtceNo"),
        "bid_ntce_ord": it.get("bidNtceOrd"),
        "cntrct_nm": it.get("cntrctNm"),
        "bsns_div_nm": it.get("bsnsDivNm"),
        "cntrct_cncls_mthd_nm": it.get("cntrctCnclsMthdNm"),
        "cntrct_cncls_date": to_date(it.get("cntrctCnclsDate")),
        "cntrct_amt": to_int(it.get("cntrctAmt")),
        "ttal_cntrct_amt": to_int(it.get("ttalCntrctAmt")),
        "rsrvtn_prce": to_int(it.get("rsrvtnPrce")),
        "rprsnt_corp_bizrno": (it.get("rprsntCorpBizrno") or "").strip() or None,
        "rprsnt_corp_nm": it.get("rprsntCorpNm"),
        "rprsnt_corp_ceo_nm": it.get("rprsntCorpCeoNm"),
        "cntrct_instt_cd": it.get("cntrctInsttCd"),
        "cntrct_instt_nm": it.get("cntrctInsttNm"),
        "dmnd_instt_cd": it.get("dmndInsttCd"),
        "dmnd_instt_nm": it.get("dmndInsttNm"),
        "openg_date": to_date(it.get("opengDate")),
        "data_bss_date": to_date(it.get("dataBssDate")),
        "raw": it,
    }


def upsert_companies_from_contracts(rows: list[dict]) -> int:
    """계약에서 발견된 새 사업자번호를 companies 마스터에 stub upsert."""
    by_biz: dict[str, dict] = {}
    for r in rows:
        biz = r.get("rprsnt_corp_bizrno")
        if not biz or not r.get("rprsnt_corp_nm"):
            continue
        if biz not in by_biz:
            by_biz[biz] = {
                "bizrno": biz,
                "corp_nm": r["rprsnt_corp_nm"],
                "ceo_nm": r.get("rprsnt_corp_ceo_nm"),
            }
    if not by_biz:
        return 0
    # ON CONFLICT DO NOTHING - corp_nm/ceo_nm은 사용자정보 API가 권위 있는 소스이므로 overwrite 안 함
    client = get_admin_client()
    client.table("companies").upsert(
        list(by_biz.values()), on_conflict="bizrno", ignore_duplicates=True
    ).execute()
    return len(by_biz)


def run(days_back: int = 1, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(
        JOB_NAME,
        {"days_back": days_back, "begin": extra["inqryBgnDt"], "end": extra["inqryEndDt"]},
    )
    print(f"[{JOB_NAME}] range {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    total = 0
    new_companies = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["cntrct_no"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("contracts", batch, on_conflict="cntrct_no,cntrct_ord")
                new_companies += upsert_companies_from_contracts(batch)
                total += len(batch)
                print(f"  upserted {total} contracts ({new_companies} new companies)...")
                batch.clear()
        if batch:
            upsert_rows("contracts", batch, on_conflict="cntrct_no,cntrct_ord")
            new_companies += upsert_companies_from_contracts(batch)
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {total} contracts, {new_companies} new companies")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

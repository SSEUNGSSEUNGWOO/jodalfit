"""사전규격 수집 잡 (SW 사업만).

소스: HrcspSsstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch
필터: swBizObjYn=Y (SW사업 대상만)

실행:
    cd backend
    uv run python -m jobs.ingest_pre_specs --days-back 1
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.services.supabase_client import upsert_rows
from jobs._common import (
    DATE_FMT,
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_int,
    to_timestamptz,
    to_yn,
)

URL = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch"
JOB_NAME = "ingest_pre_specs"


def map_item(it: dict) -> dict:
    return {
        "bf_spec_rgst_no": it.get("bfSpecRgstNo"),
        "bid_ntce_no_list": it.get("bidNtceNoList") or None,
        "prdct_clsfc_no_nm": it.get("prdctClsfcNoNm"),
        "bsns_div_nm": it.get("bsnsDivNm"),
        "sw_biz_obj_yn": to_yn(it.get("swBizObjYn")),
        "asign_bdgt_amt": to_int(it.get("asignBdgtAmt")),
        "rcpt_dt": to_timestamptz(it.get("rcptDt")),
        "rgst_dt": to_timestamptz(it.get("rgstDt")),
        "chg_dt": to_timestamptz(it.get("chgDt")),
        "opnin_rgst_clse_dt": to_timestamptz(it.get("opninRgstClseDt")),
        "dlvr_daynum": to_int(it.get("dlvrDaynum")),
        "order_instt_nm": it.get("orderInsttNm"),
        "rl_dminstt_nm": it.get("rlDminsttNm"),
        "prdct_dtl_list": it.get("prdctDtlList"),
        "spec_doc_file_url_1": it.get("specDocFileUrl1") or None,
        "spec_doc_file_url_2": it.get("specDocFileUrl2") or None,
        "spec_doc_file_url_3": it.get("specDocFileUrl3") or None,
        "spec_doc_file_url_4": it.get("specDocFileUrl4") or None,
        "spec_doc_file_url_5": it.get("specDocFileUrl5") or None,
        "ref_no": it.get("refNo"),
        "raw": it,
    }


def run(days_back: int = 1, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
        "swBizObjYn": "Y",
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back, **extra} | {"ServiceKey": "***"})
    print(f"[{JOB_NAME}] SW사업 only, {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    total = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["bf_spec_rgst_no"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("pre_specs", batch, on_conflict="bf_spec_rgst_no")
                total += len(batch)
                batch.clear()
        if batch:
            upsert_rows("pre_specs", batch, on_conflict="bf_spec_rgst_no")
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {total} rows upserted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

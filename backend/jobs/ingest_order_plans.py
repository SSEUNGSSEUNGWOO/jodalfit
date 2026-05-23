"""발주계획 수집 잡 (선행지표).

소스: OrderPlanSttusService/getOrderPlanSttusListServcPPSSrch
조회조건: orderPlanBgnYearMonth + orderPlanEndYearMonth (YYYYMM 형식)

실행:
    cd backend
    uv run python -m jobs.ingest_order_plans --months-back 6
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.services.supabase_client import upsert_rows
from jobs._common import (
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_decimal,
    to_int,
    to_timestamptz,
)

URL = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusListServcPPSSrch"
JOB_NAME = "ingest_order_plans"


def map_item(it: dict) -> dict:
    return {
        "order_plan_unty_no": it.get("orderPlanUntyNo"),
        "biz_nm": it.get("bizNm"),
        "bsns_div_nm": it.get("bsnsDivNm"),
        "bsns_ty_cd": it.get("bsnsTyCd"),
        "bsns_ty_nm": it.get("bsnsTyNm"),
        "order_year": it.get("orderYear"),
        "order_mnth": it.get("orderMnth"),
        "cntrct_mthd_nm": it.get("cntrctMthdNm"),
        "prcrmnt_methd": it.get("prcrmntMethd"),
        "order_instt_cd": it.get("orderInsttCd"),
        "order_instt_nm": it.get("orderInsttNm"),
        "totlmng_instt_nm": it.get("totlmngInsttNm"),
        "jrsdctn_div_nm": it.get("jrsdctnDivNm"),
        "sum_order_amt": to_int(it.get("sumOrderAmt")),
        "sum_order_dol_amt": to_decimal(it.get("sumOrderDolAmt")),
        "bid_ntce_no_list": it.get("bidNtceNoList") or None,
        "prdct_clsfc_no_nm": it.get("prdctClsfcNoNm") or None,
        "usg_cntnts": it.get("usgCntnts") or None,
        "spec_cntnts": it.get("specCntnts") or None,
        "ntice_dt": to_timestamptz(it.get("nticeDt")),
        "chg_dt": to_timestamptz(it.get("chgDt")),
        "raw": it,
    }


def run(months_back: int = 6, batch_size: int = 500) -> None:
    end = datetime.now()
    # 발주계획은 미래 일정도 포함되므로 시작은 과거, 끝은 미래까지
    begin_yymm = (end - timedelta(days=months_back * 30)).strftime("%Y%m")
    end_yymm = (end + timedelta(days=180)).strftime("%Y%m")
    extra = {
        "orderPlanBgnYearMonth": begin_yymm,
        "orderPlanEndYearMonth": end_yymm,
    }
    run_id = log_ingest_start(JOB_NAME, {"months_back": months_back, **extra})
    print(f"[{JOB_NAME}] {begin_yymm} ~ {end_yymm}")

    total = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["order_plan_unty_no"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("order_plans", batch, on_conflict="order_plan_unty_no")
                total += len(batch)
                batch.clear()
        if batch:
            upsert_rows("order_plans", batch, on_conflict="order_plan_unty_no")
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {total} rows upserted")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--months-back", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.months_back, args.batch_size)

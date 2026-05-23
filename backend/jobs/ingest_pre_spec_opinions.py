"""사전규격 의견 수집 잡 ⭐ (회사 관심 신호 - 콜드스타트 해결).

소스: HrcspSsstndrdInfoService/getPublicPrcureThngOpinionInfoServc
주의: 의견에는 사업자번호가 없고 'mkngCorpNm'(회사명)만 있어서
companies 매핑은 추후 fuzzy 매칭 잡에서 처리.

실행:
    cd backend
    uv run python -m jobs.ingest_pre_spec_opinions --days-back 1
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
    to_timestamptz,
)

URL = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngOpinionInfoServc"
JOB_NAME = "ingest_pre_spec_opinions"


def map_item(it: dict) -> dict:
    return {
        "bf_spec_rgst_no": it.get("bfSpecRgstNo"),
        "opnin_no": str(it.get("opninNo") or "0"),
        "ref_no": it.get("refNo"),
        "opnin_titl": it.get("opninTitl"),
        "opnin_cntnts": it.get("opninCntnts"),
        "mkng_corp_nm": (it.get("mkngCorpNm") or "").strip() or None,
        "mkr_nm": (it.get("mkrNm") or "").strip() or None,
        "mkr_email": (it.get("mkrEmail") or "").strip() or None,
        "mkr_tel": (it.get("mkrTel") or "").strip() or None,
        "inpt_dt": to_timestamptz(it.get("inptDt")),
        "rply_no": it.get("rplyNo"),
        "spec_doc_opnin_file_url_1": it.get("specDocOpninFileUrl1") or None,
        "raw": it,
    }


def run(days_back: int = 1, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back})
    print(f"[{JOB_NAME}] range {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    total = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["bf_spec_rgst_no"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("pre_spec_opinions", batch, on_conflict="bf_spec_rgst_no,opnin_no")
                total += len(batch)
                batch.clear()
        if batch:
            upsert_rows("pre_spec_opinions", batch, on_conflict="bf_spec_rgst_no,opnin_no")
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

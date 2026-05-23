"""회사 마스터 풍부화 (UsrInfoService02 - 기본정보).

소스: UsrInfoService02/getPrcrmntCorpBasicInfo02
조회조건: 변경일시 범위 (inqryDiv=1 + inqryBgnDt/EndDt)
모드: 변경된 회사만 누적 → 매일 잡으로 운영

부수효과: companies 테이블에 기본정보 upsert (overwrite — 권위 있는 소스).

실행:
    cd backend
    uv run python -m jobs.ingest_companies_userinfo --days-back 3
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta

from app.services.supabase_client import upsert_rows
from jobs._common import (
    DATE_FMT,
    iter_all_items,
    log_ingest_finish,
    log_ingest_start,
    to_date,
    to_int,
    to_timestamptz,
    to_yn,
)

URL = "https://apis.data.go.kr/1230000/ao/UsrInfoService02/getPrcrmntCorpBasicInfo02"
JOB_NAME = "ingest_companies_userinfo"


def normalize_bizrno(v: str | None) -> str | None:
    if not v:
        return None
    s = re.sub(r"\D", "", v)
    return s or None


def map_item(it: dict) -> dict:
    # API 응답 → companies 스키마 매핑. bizno → bizrno (정규화)
    return {
        "bizrno": normalize_bizrno(it.get("bizno")),
        "corp_nm": it.get("corpNm"),
        "english_nm": it.get("engCorpNm") or None,
        "ceo_nm": it.get("ceoNm"),
        "opng_dt": to_date(it.get("opbizDt")),
        "rgn_cd": it.get("rgnCd"),
        "rgn_nm": it.get("rgnNm"),
        "zip_no": it.get("zip"),
        "addr": it.get("adrs"),
        "dtl_addr": it.get("dtlAdrs"),
        "tel_no": it.get("telNo"),
        "fax_no": it.get("faxNo"),
        "hmpg_addr": it.get("hmpgAdrs"),
        "mnfctr_div_cd": it.get("mnfctDivCd"),
        "mnfctr_div_nm": it.get("mnfctDivNm"),
        "emp_count": to_int(it.get("emplyeNum")),
        "corp_bsns_div_cd": it.get("corpBsnsDivCd"),
        "corp_bsns_div_nm": it.get("corpBsnsDivNm"),
        "hd_off_div_nm": it.get("hdoffceDivNm"),
        "unq_no_crtfct_yn": to_yn(it.get("esntlNoCertRgstYn")),
        "rgst_dt": to_timestamptz(it.get("rgstDt")),
        "raw": it,
    }


def run(days_back: int = 3, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    extra = {
        "inqryDiv": "1",
        "inqryBgnDt": begin.strftime(DATE_FMT),
        "inqryEndDt": end.strftime(DATE_FMT),
    }
    run_id = log_ingest_start(JOB_NAME, {"days_back": days_back, **{k: v for k, v in extra.items()}})
    print(f"[{JOB_NAME}] 변경일 {extra['inqryBgnDt']} ~ {extra['inqryEndDt']}")

    total = 0
    batch: list[dict] = []
    try:
        for it in iter_all_items(URL, extra):
            row = map_item(it)
            if not row["bizrno"] or not row["corp_nm"]:
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                upsert_rows("companies", batch, on_conflict="bizrno")
                total += len(batch)
                print(f"  upserted {total}...")
                batch.clear()
        if batch:
            upsert_rows("companies", batch, on_conflict="bizrno")
            total += len(batch)
        log_ingest_finish(run_id, "success", rows_inserted=total)
        print(f"[{JOB_NAME}] done. {total} companies upserted/updated")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    run(args.days_back, args.batch_size)

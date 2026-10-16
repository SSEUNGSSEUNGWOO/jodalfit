"""사전규격 수집 잡 — 물품·용역·공사·외자 전부.

소스: HrcspSsstndrdInfoService/getPublicPrcureThngInfo{Thng,Servc,Cnstwk,Frgcpt}PPSSrch
(업무구분별 엔드포인트가 따로다. 2026-10-16 까지는 용역(Servc)+swBizObjYn=Y 만 받아 2,521건이었고,
bid_notices.bf_spec_rgst_no(0047)가 채워진 물품 공고 3.8만 건과 한 건도 안 이어졌다.)
조회 범위 30일 초과 시 API 가 거부하므로 30일 창으로 나눠 받는다.

실행:
    cd backend
    uv run python -m jobs.ingest_pre_specs --days-back 1
    uv run python -m jobs.ingest_pre_specs --days-back 170   # 백필 (30일씩 6창)
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

BASE = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService"
URLS = {
    "물품": f"{BASE}/getPublicPrcureThngInfoThngPPSSrch",
    "용역": f"{BASE}/getPublicPrcureThngInfoServcPPSSrch",
    "공사": f"{BASE}/getPublicPrcureThngInfoCnstwkPPSSrch",
    "외자": f"{BASE}/getPublicPrcureThngInfoFrgcptPPSSrch",
}
JOB_NAME = "ingest_pre_specs"
WINDOW_DAYS = 30  # 나라장터 조회 범위 상한


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


def windows(begin: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """[begin, end] 를 WINDOW_DAYS 이하 구간으로 나눈다 (경계는 1분 겹치지 않게)."""
    out = []
    cur = begin
    while cur < end:
        nxt = min(cur + timedelta(days=WINDOW_DAYS), end)
        out.append((cur, nxt))
        cur = nxt + timedelta(minutes=1)
    return out


def run(days_back: int = 1, batch_size: int = 500) -> None:
    end = datetime.now()
    begin = end - timedelta(days=days_back)
    run_id = log_ingest_start(
        JOB_NAME,
        {"days_back": days_back, "inqryBgnDt": begin.strftime(DATE_FMT), "inqryEndDt": end.strftime(DATE_FMT)},
    )
    print(f"[{JOB_NAME}] {begin:%Y%m%d%H%M} ~ {end:%Y%m%d%H%M}, {len(URLS)} 업무구분 × {len(windows(begin, end))} 창")

    total = 0
    batch: list[dict] = []
    try:
        for div, url in URLS.items():
            n_div = 0
            for w_begin, w_end in windows(begin, end):
                extra = {
                    "inqryDiv": "1",
                    "inqryBgnDt": w_begin.strftime(DATE_FMT),
                    "inqryEndDt": w_end.strftime(DATE_FMT),
                }
                for it in iter_all_items(url, extra):
                    row = map_item(it)
                    if not row["bf_spec_rgst_no"]:
                        continue
                    batch.append(row)
                    n_div += 1
                    if len(batch) >= batch_size:
                        upsert_rows("pre_specs", batch, on_conflict="bf_spec_rgst_no")
                        total += len(batch)
                        batch.clear()
            print(f"  {div}: {n_div} rows")
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

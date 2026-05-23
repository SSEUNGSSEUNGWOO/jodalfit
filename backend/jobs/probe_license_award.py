"""BidPublicInfoService 면허제한 + ScsbidInfoService 개찰결과 endpoint probe.

확인:
- getBidPblancListInfoLicenseLimit: 필수파라미터, 응답 필드
- getOpengResultListInfoOpengCompt: 동일

실행:
    cd backend
    uv run python -m jobs.probe_license_award
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
BID_BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
SCSBID_BASE = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"

OUT = Path(__file__).resolve().parent.parent.parent / "data" / "api_probe"
OUT.mkdir(parents=True, exist_ok=True)

DATE_FMT = "%Y%m%d%H%M"
END = datetime.now()
BEGIN = END - timedelta(days=3)


def fetch_and_dump(label: str, url: str, params: dict):
    full = {"ServiceKey": API_KEY, "type": "json", "pageNo": "1", "numOfRows": "3"} | params
    try:
        r = httpx.get(url, params=full, timeout=30.0)
        data = r.json() if r.text.lstrip().startswith("{") else {"_raw": r.text[:500]}
    except Exception as e:
        data = {"_err": str(e)}

    (OUT / f"la_{label}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n=== {label} ===")
    print(f"url: {url}")
    print(f"params: { {k: v for k, v in params.items()} }")

    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        print(f"[ERROR] code={err.get('resultCode')} msg={err.get('resultMsg')}")
        return
    if "_raw" in data:
        print(data["_raw"][:400])
        return

    body = data.get("response", {}).get("body", {})
    header = data.get("response", {}).get("header", {})
    print(f"resultCode={header.get('resultCode')} totalCount={body.get('totalCount')}")
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            print(f"필드 {len(first)}개")
            for k, v in sorted(first.items()):
                print(f"  {k}: {repr(v)[:80]}")


def main():
    # 1. 면허제한: 등록일시 + (옵션) 입찰공고번호
    fetch_and_dump(
        "license_limit_dates",
        f"{BID_BASE}/getBidPblancListInfoLicenseLimit",
        {"inqryDiv": "1", "inqryBgnDt": BEGIN.strftime(DATE_FMT), "inqryEndDt": END.strftime(DATE_FMT)},
    )

    # 2. 참가가능지역
    fetch_and_dump(
        "rgn_limit_dates",
        f"{BID_BASE}/getBidPblancListInfoPrtcptPsblRgn",
        {"inqryDiv": "1", "inqryBgnDt": BEGIN.strftime(DATE_FMT), "inqryEndDt": END.strftime(DATE_FMT)},
    )

    # 3. 개찰완료 (입찰공고번호 필수)
    fetch_and_dump(
        "opengresult_dates",
        f"{SCSBID_BASE}/getOpengResultListInfoOpengCompt",
        {"inqryDiv": "1", "inqryBgnDt": BEGIN.strftime(DATE_FMT), "inqryEndDt": END.strftime(DATE_FMT)},
    )

    # 4. 낙찰자목록 - 용역
    fetch_and_dump(
        "scsbid_servc_dates",
        f"{SCSBID_BASE}/getScsbidListSttusServc",
        {"inqryDiv": "1", "inqryBgnDt": BEGIN.strftime(DATE_FMT), "inqryEndDt": END.strftime(DATE_FMT)},
    )


if __name__ == "__main__":
    main()

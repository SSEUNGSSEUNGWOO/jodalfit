"""개찰결과(참가업체) endpoint probe — ingest_bid_participants 설계용.

확인:
- getOpengResultListInfoOpengCompt를 bidNtceNo 지정(inqryDiv=2)으로 호출 시
  참가업체 전체(순위·사업자번호·투찰금액)가 나오는지
- 공고번호는 award_results에서 최근 낙찰 건을 샘플링

실행:
    cd backend
    uv run python -m jobs.probe_participants
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.supabase_client import get_admin_client  # noqa: E402

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
SCSBID_BASE = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"

OUT = Path(__file__).resolve().parent.parent.parent / "data" / "api_probe"
OUT.mkdir(parents=True, exist_ok=True)


def fetch_and_dump(label: str, url: str, params: dict):
    full = {"ServiceKey": API_KEY, "type": "json", "pageNo": "1", "numOfRows": "20"} | params
    try:
        r = httpx.get(url, params=full, timeout=30.0)
        data = r.json() if r.text.lstrip().startswith("{") else {"_raw": r.text[:500]}
    except Exception as e:
        data = {"_err": str(e)}

    (OUT / f"pp_{label}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n=== {label} ===")
    print(f"params: {params}")

    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        print(f"[ERROR] code={err.get('resultCode')} msg={err.get('resultMsg')}")
        return
    if "_raw" in data:
        print(data["_raw"][:400])
        return
    if "_err" in data:
        print(f"[EXC] {data['_err']}")
        return

    body = data.get("response", {}).get("body", {})
    header = data.get("response", {}).get("header", {})
    print(f"resultCode={header.get('resultCode')} totalCount={body.get('totalCount')}")
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if not isinstance(items, list):
        items = [items]
    for i, it in enumerate(items[:12]):
        if not isinstance(it, dict):
            continue
        if i == 0:
            print(f"필드 {len(it)}개: {sorted(it.keys())}")
        summary = {
            k: it.get(k)
            for k in ("opengRank", "prcbdrBizno", "prcbdrNm", "bidprcAmt", "bidprcrt", "rmrk")
            if k in it
        }
        print(f"  [{i}] {summary if summary else it}")


def main():
    client = get_admin_client()
    rows = (
        client.table("award_results")
        .select("bid_ntce_no,bid_ntce_ord,bsns_div_nm")
        .order("created_at", desc=True)
        .limit(3)
        .execute()
        .data
    )
    if not rows:
        raise SystemExit("award_results가 비어 있습니다.")

    for r in rows:
        print(f"\n##### 샘플 공고 {r['bid_ntce_no']}-{r['bid_ntce_ord']} ({r.get('bsns_div_nm')})")
        fetch_and_dump(
            f"compt_{r['bid_ntce_no']}",
            f"{SCSBID_BASE}/getOpengResultListInfoOpengCompt",
            {"inqryDiv": "2", "bidNtceNo": r["bid_ntce_no"]},
        )


if __name__ == "__main__":
    main()

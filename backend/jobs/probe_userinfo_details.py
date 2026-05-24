"""UsrInfoService02 업종/공급물품 endpoint probe.

active 회사 1개로 호출 → 응답 필드 + 정확한 파라미터명 확인
"""

import json
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
BASE = "https://apis.data.go.kr/1230000/ao/UsrInfoService02"
OUT = Path(__file__).resolve().parent.parent.parent / "data" / "api_probe"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(op: str, params: dict, label: str):
    url = f"{BASE}/{op}"
    full = {"ServiceKey": API_KEY, "type": "json", "pageNo": "1", "numOfRows": "10"} | params
    try:
        r = httpx.get(url, params=full, timeout=20.0)
        data = r.json() if r.text.lstrip().startswith("{") else {"_raw": r.text[:400]}
    except Exception as e:
        data = {"_err": str(e)}

    (OUT / f"usr_{label}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n=== {label} ===  ({op})")
    print(f"params: { {k:v for k,v in params.items()} }")

    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        print(f"[ERROR] code={err.get('resultCode')} msg={err.get('resultMsg')}")
        return
    body = data.get("response", {}).get("body", {})
    header = data.get("response", {}).get("header", {})
    print(f"resultCode={header.get('resultCode')} total={body.get('totalCount')}")
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            print(f"필드 {len(first)}개: {sorted(first.keys())}")
            print("샘플:")
            for k in sorted(first.keys()):
                print(f"  {k}: {repr(first[k])[:60]}")


def main():
    # 실제 active 회사의 사업자번호 — contracts에 등장한 회사 중 하나
    # 예: 5088127915 (퓨처자료실) — 이전 probe에서 확인
    sample = "5088127915"

    # 등록업종 — 추가 필수값 시도
    fetch(
        "getPrcrmntCorpIndstrytyInfo02",
        {"bizno": sample, "inqryDiv": "1"},
        "indstry_inqry1",
    )
    fetch(
        "getPrcrmntCorpIndstrytyInfo02",
        {"bizno": sample, "inqryDiv": "1", "inqryBgnDt": "200001010000", "inqryEndDt": "202605250000"},
        "indstry_dates",
    )
    fetch(
        "getPrcrmntCorpIndstrytyInfo02",
        {"corpBizrnoNo": sample},
        "indstry_corpBizrnoNo",
    )
    fetch(
        "getPrcrmntCorpIndstrytyInfo02",
        {"bsnsRegNo": sample},
        "indstry_bsnsRegNo",
    )


if __name__ == "__main__":
    main()

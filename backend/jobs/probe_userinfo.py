"""UsrInfoService02 호출 패턴 확인용 probe.

확인할 것:
1. 빈 조건 + 페이지네이션으로 전체 목록 가능한가?
2. 사업자번호 검색이 필수인가?
3. 응답 필드 구조

실행:
    cd backend
    uv run python -m jobs.probe_userinfo
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

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
BASE = "https://apis.data.go.kr/1230000/ao/UsrInfoService02"

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "api_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def probe(op: str, params: dict, label: str):
    url = f"{BASE}/{op}"
    full = {"ServiceKey": API_KEY, "type": "json", "pageNo": "1", "numOfRows": "3"} | params
    try:
        r = httpx.get(url, params=full, timeout=30.0)
        data = r.json() if r.text.lstrip().startswith("{") else {"_raw": r.text[:300]}
    except Exception as e:
        data = {"_err": str(e)}

    print(f"\n=== {label} ===")
    print(f"op: {op}")
    print(f"params: { {k:v for k,v in params.items()} }")
    (OUT_DIR / f"usrinfo_{label}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        print(f"[ERROR] code={err.get('resultCode')} msg={err.get('resultMsg')}")
        return
    if "_raw" in data:
        print(data["_raw"][:300])
        return

    body = data.get("response", {}).get("body", {})
    header = data.get("response", {}).get("header", {})
    print(f"resultCode={header.get('resultCode')} resultMsg={header.get('resultMsg')}")
    print(f"totalCount={body.get('totalCount')}")
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, list) and items and isinstance(items[0], dict):
        print(f"필드 {len(items[0])}개: {sorted(items[0].keys())}")
        print("첫 row 일부:")
        for k, v in list(items[0].items())[:8]:
            print(f"  {k}: {repr(v)[:80]}")


def main():
    # 테스트할 사업자번호: 우리 companies 테이블에 있는 것 하나 사용 (이전 적재에서 확인된 값)
    # 예시로 자주 사용되는 사업자번호 형식 시도
    sample_bizrno = "1234567890"  # fallback - 빈조건 호출이 먼저

    # 1. 빈 조건 (전체 페이지네이션 가능한지)
    probe("getPrcrmntCorpBasicInfo02", {}, "basic_empty")

    # 2. 사업자번호 입력
    probe("getPrcrmntCorpBasicInfo02", {"bizrno": sample_bizrno}, "basic_bizrno")

    # 3. inqryDiv + 날짜 (변경 추적용일 가능성)
    probe(
        "getPrcrmntCorpBasicInfo02",
        {"inqryDiv": "1", "inqryBgnDt": "202605200000", "inqryEndDt": "202605232359"},
        "basic_inqry_dates",
    )

    # 4. 업종/공급물품도 빈 조건 시도
    probe("getPrcrmntCorpIndstrytyInfo02", {}, "indstryty_empty")
    probe("getPrcrmntCorpSplyPrdctInfo02", {}, "supply_empty")

    # 5. 부정당 제재
    probe("getUnptRsttCorpInfo02", {}, "rstrct_empty")
    probe(
        "getUnptRsttCorpInfo02",
        {"inqryDiv": "1", "inqryBgnDt": "202601010000", "inqryEndDt": "202605232359"},
        "rstrct_dates",
    )


if __name__ == "__main__":
    main()

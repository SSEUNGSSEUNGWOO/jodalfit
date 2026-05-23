"""나라장터 OpenAPI 최종 검증 probe.

공식 명세 기반 확정 endpoint + 파라미터로 4개 핵심 API 검증.

실행:
    cd backend
    uv run python -m jobs.probe_api
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.getenv("NARAJANGTEO_API_KEY")
if not API_KEY:
    raise SystemExit("NARAJANGTEO_API_KEY가 .env에 설정되지 않았습니다.")

PUB_STD = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
HRCSP = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService"
ORDER_PLAN = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService"

END = datetime.now()
BEGIN_WEEK = END - timedelta(days=7)
DATE_FMT = "%Y%m%d%H%M"

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "api_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str, params: dict[str, str]) -> dict[str, Any]:
    resp = httpx.get(url, params=params, timeout=30.0)
    text = resp.text
    if text.lstrip().startswith("{"):
        try:
            return resp.json()
        except Exception:
            pass
    return {"_raw_text": text[:1500], "_status": resp.status_code, "_ctype": resp.headers.get("content-type")}


def summarize(label: str, url: str, params: dict[str, str], data: dict[str, Any], filename: str) -> None:
    out_path = OUT_DIR / filename
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {label} ===")
    print(f"url: {url}")
    print(f"params: { {k:v for k,v in params.items() if k != 'ServiceKey'} }")

    if "nkoneps.com.response.ResponseError" in data:
        err = data["nkoneps.com.response.ResponseError"].get("header", {})
        print(f"[ERROR] resultCode={err.get('resultCode')} resultMsg={err.get('resultMsg')}")
        return
    if "_raw_text" in data:
        print(f"[NON-JSON] {data.get('_status')} {data.get('_ctype')}")
        print(data["_raw_text"][:300])
        return

    body = data.get("response", {}).get("body", {})
    header = data.get("response", {}).get("header", {})
    rc = header.get("resultCode")
    print(f"resultCode: {rc} / resultMsg: {header.get('resultMsg')}")
    if rc not in (None, "00", "0"):
        return

    total = body.get("totalCount")
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    print(f"totalCount: {total} / items returned: {len(items) if isinstance(items, list) else 'N/A'}")

    if isinstance(items, list) and items and isinstance(items[0], dict):
        first = items[0]
        print(f"필드 {len(first)}개")
        # 키 텍스트로 보이는 필드만 일부 출력
        for k in sorted(first.keys()):
            v = first[k]
            v_repr = repr(v)
            if len(v_repr) > 80:
                v_repr = v_repr[:80] + "..."
            print(f"  {k}: {v_repr}")


def try_probe(label: str, url: str, params: dict[str, str], filename: str) -> None:
    try:
        data = fetch(url, params)
        summarize(label, url, params, data, filename)
    except Exception as e:
        print(f"\n=== {label} ===\n[EXC] {type(e).__name__}: {e}")


def main() -> None:
    print(f"조회 기간: {BEGIN_WEEK.strftime(DATE_FMT)} ~ {END.strftime(DATE_FMT)}")

    base = {"ServiceKey": API_KEY, "type": "json", "pageNo": "1", "numOfRows": "3"}

    # ==== 1. 낙찰 (확정 파라미터: opengBgnDt + opengEndDt + bsnsDivNm) ====
    for div in ["용역", "물품"]:
        params = base | {
            "inqryDiv": "1",
            "opengBgnDt": BEGIN_WEEK.strftime(DATE_FMT),
            "opengEndDt": END.strftime(DATE_FMT),
            "bsnsDivNm": div,
        }
        try_probe(
            f"낙찰-{div} (확정 파라미터)",
            f"{PUB_STD}/getDataSetOpnStdScsbidInfo",
            params,
            f"scsbid_{div}_final.json",
        )

    # ==== 2. 사전규격 용역 PPSSrch + SW사업대상여부=Y ====
    params = base | {
        "inqryDiv": "1",
        "inqryBgnDt": BEGIN_WEEK.strftime(DATE_FMT),
        "inqryEndDt": END.strftime(DATE_FMT),
        "swBizObjYn": "Y",
    }
    try_probe(
        "사전규격 용역 PPSSrch (SW사업만)",
        f"{HRCSP}/getPublicPrcureThngInfoServcPPSSrch",
        params,
        "prestd_servc_ppssrch_sw.json",
    )

    # ==== 3. 사전규격 의견 용역 ====
    params = base | {
        "inqryDiv": "1",
        "inqryBgnDt": BEGIN_WEEK.strftime(DATE_FMT),
        "inqryEndDt": END.strftime(DATE_FMT),
    }
    try_probe(
        "사전규격 의견 용역 (회사 관심 신호)",
        f"{HRCSP}/getPublicPrcureThngOpinionInfoServc",
        params,
        "prestd_opinion_servc.json",
    )

    # ==== 4. 발주계획 용역 PPSSrch (확정 파라미터: 발주시작년월) ====
    today = END.strftime("%Y%m")
    six_month_ago = (END - timedelta(days=180)).strftime("%Y%m")
    params = base | {
        "orderPlanBgnYearMonth": six_month_ago,
        "orderPlanEndYearMonth": today,
    }
    try_probe(
        "발주계획 용역 PPSSrch (발주월 범위)",
        f"{ORDER_PLAN}/getOrderPlanSttusListServcPPSSrch",
        params,
        "order_servc_ppssrch.json",
    )


if __name__ == "__main__":
    main()

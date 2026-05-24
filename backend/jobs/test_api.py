"""POST /recommendations end-to-end 테스트.

실행 전제:
- uvicorn 별도 터미널에서 http://localhost:8000 동작
또는 같은 프로세스에서 in-process 호출도 가능 (USE_INPROCESS=True).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

# 한글 콘솔 출력
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = os.getenv("JODALFIT_API_BASE", "http://localhost:8000")

QUERIES = [
    "주식회사 지피",
    "세이프월드 주식회사",
    "(주)두신건설",
    "1408173625",  # 사업자번호 직접
    "존재하지않는회사명XYZ",  # 실패 케이스
]


def call(query: str, with_explanation: bool = False) -> dict:
    """추천 API 호출."""
    payload = {
        "query": query,
        "limit": 5,
        "with_explanation": with_explanation,
    }
    try:
        resp = httpx.post(
            f"{API_BASE}/recommendations", json=payload, timeout=60.0
        )
    except httpx.HTTPError as e:
        return {"_error": f"connection: {e}"}
    if resp.status_code != 200:
        return {"_status": resp.status_code, "_body": resp.text[:400]}
    return resp.json()


def main():
    out_dir = Path(__file__).resolve().parent.parent.parent / "data" / "api_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for i, q in enumerate(QUERIES):
        # 첫 2개는 with_explanation=True로 LLM 호출까지 검증
        with_exp = i < 2
        print(f"\n[{i+1}/{len(QUERIES)}] query={q!r} with_explanation={with_exp}")
        result = call(q, with_explanation=with_exp)

        # 저장
        slug = q.replace("/", "_").replace(" ", "_")[:40]
        out_path = out_dir / f"{i+1}_{slug}.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 요약
        if "_error" in result:
            print(f"  ❌ ERROR: {result['_error']}")
            summary.append((q, "ERROR", result["_error"]))
        elif "_status" in result:
            print(f"  ❌ HTTP {result['_status']}: {result['_body'][:200]}")
            summary.append((q, f"HTTP {result['_status']}", ""))
        else:
            comp = result.get("company")
            results = result.get("results", [])
            err = result.get("error")
            if comp:
                print(f"  ✅ 회사 식별: {comp['corp_nm']} ({comp['bizrno']})")
                print(f"     추천 공고 {len(results)}건")
                for j, r in enumerate(results[:3]):
                    expl = (r.get("explanation") or "")[:80]
                    print(
                        f"     #{j+1} score={r.get('score', 0):.3f}  {r.get('bid_ntce_nm', '')[:50]}"
                    )
                    if expl:
                        print(f"        설명: {expl}...")
                summary.append((q, "OK", f"{comp['corp_nm']}, {len(results)} 추천"))
            else:
                print(f"  ⚠️ 회사 식별 실패: {err}")
                summary.append((q, "NO_COMPANY", err or ""))

    print("\n" + "=" * 60)
    print("최종 요약")
    print("=" * 60)
    for q, status, note in summary:
        print(f"  {status:12} {q:30}  {note}")

    print(f"\n저장: {out_dir}")


if __name__ == "__main__":
    main()

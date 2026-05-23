"""Phase 2 사전 점검.

확인할 것:
1. OpenAI 키 동작 (임베딩 1건 호출)
2. 0002 마이그레이션 적용 (bizrno_norm generated column)
3. 0003 마이그레이션 적용 (find_companies / match_bid_notices RPC)
"""

from __future__ import annotations

from app.services.openai_client import embed_texts
from app.services.supabase_client import get_admin_client


def main() -> None:
    print("=== Phase 2 사전 점검 ===\n")

    # 1. OpenAI 임베딩 동작
    try:
        v = embed_texts(["테스트 임베딩 확인"])
        print(f"[1] OpenAI 임베딩: OK (dim={len(v[0])})")
    except Exception as e:
        print(f"[1] OpenAI 임베딩: FAIL — {e}")

    client = get_admin_client()

    # 2. bizrno_norm generated column
    try:
        r = client.table("companies").select("bizrno,bizrno_norm").limit(1).execute()
        has_norm = bool(r.data) and "bizrno_norm" in r.data[0]
        print(f"[2] 0002 bizrno_norm 컬럼: {'OK' if has_norm else 'MISSING — 0002 SQL 미적용'}")
    except Exception as e:
        print(f"[2] 0002 bizrno_norm 컬럼: FAIL — {e}")

    # 3. RPC 함수
    try:
        r = client.rpc("find_companies", {"query_name": "테스트", "max_count": 1}).execute()
        print(f"[3] 0003 find_companies RPC: OK (rows={len(r.data or [])})")
    except Exception as e:
        print(f"[3] 0003 find_companies RPC: FAIL — {e}")

    try:
        sample_vec = "[" + ",".join(["0.0"] * 1536) + "]"
        r = client.rpc(
            "match_bid_notices",
            {"query_embedding": sample_vec, "match_count": 1},
        ).execute()
        print(f"[3] 0003 match_bid_notices RPC: OK (rows={len(r.data or [])})")
    except Exception as e:
        print(f"[3] 0003 match_bid_notices RPC: FAIL — {e}")


if __name__ == "__main__":
    main()

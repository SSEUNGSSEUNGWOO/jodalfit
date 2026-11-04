"""Supabase 클라이언트 wrapper.

- service role 키 기반 admin 클라이언트 (백엔드 잡/관리자 작업용)
- anon 키 클라이언트는 frontend에서만 사용 (RLS 적용)
"""

from __future__ import annotations

from functools import lru_cache

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import get_settings


@lru_cache
def get_admin_client() -> Client:
    """Service role 키 기반 admin 클라이언트. 잡/관리자 작업 전용.

    HTTP/1.1 로 고정한다(postgrest-py 기본은 http2=True). 이 클라이언트 하나를 추천 경로의 스레드 풀이 함께 쓰는데,
    HTTP/2 는 연결 하나에 요청을 다중화해서 스레드가 겹치면 hpack 상태가 깨진다 — 운영 2026-11-02~04 이틀간
    POST /recommendations 500 191건이 전부 "Server disconnected"·"ConnectionTerminated error_code:9"·
    "IndexError: pop from an empty deque"(hpack) 였고, 그 연결이 멎으면 진행 중인 요청 전부가 같이 멎었다가
    한꺼번에 풀렸다(최장 7분). 로컬 재현: 스레드 12개 × 15회 — HTTP/2 는 180건 중 23건 실패, HTTP/1.1 은 0건.
    HTTP/1.1 은 요청마다 풀의 연결 하나를 혼자 쓴다. 타임아웃 120초는 라이브러리 기본값 그대로.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY가 .env에 설정되지 않았습니다."
        )
    http = httpx.Client(http2=False, timeout=httpx.Timeout(120), follow_redirects=True)
    return create_client(
        settings.supabase_url, settings.supabase_service_role_key, options=SyncClientOptions(httpx_client=http)
    )


def upsert_rows(
    table: str,
    rows: list[dict],
    on_conflict: str | None = None,
    ignore_duplicates: bool = False,
) -> dict:
    """배치 upsert helper.

    - ignore_duplicates=True: INSERT ... ON CONFLICT DO NOTHING (UPDATE 안 함, 빠름)
    - ignore_duplicates=False(기본): ON CONFLICT DO UPDATE (느림. HNSW 인덱스 있는 테이블은 timeout 위험)
    """
    if not rows:
        return {"inserted": 0}
    client = get_admin_client()
    query = client.table(table)
    if on_conflict:
        result = query.upsert(
            rows, on_conflict=on_conflict, ignore_duplicates=ignore_duplicates
        ).execute()
    else:
        result = query.upsert(rows, ignore_duplicates=ignore_duplicates).execute()
    return {"inserted": len(result.data or [])}

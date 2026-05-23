"""Supabase 클라이언트 wrapper.

- service role 키 기반 admin 클라이언트 (백엔드 잡/관리자 작업용)
- anon 키 클라이언트는 frontend에서만 사용 (RLS 적용)
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_admin_client() -> Client:
    """Service role 키 기반 admin 클라이언트. 잡/관리자 작업 전용."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY가 .env에 설정되지 않았습니다."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def upsert_rows(table: str, rows: list[dict], on_conflict: str | None = None) -> dict:
    """배치 upsert helper. 빈 리스트는 noop."""
    if not rows:
        return {"inserted": 0}
    client = get_admin_client()
    query = client.table(table)
    if on_conflict:
        result = query.upsert(rows, on_conflict=on_conflict).execute()
    else:
        result = query.upsert(rows).execute()
    return {"inserted": len(result.data or [])}

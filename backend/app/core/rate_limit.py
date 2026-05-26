"""IP 기반 rate limiting — OpenAI 토큰 남용 방지.

Railway는 proxy 뒤라 x-forwarded-for 첫 IP가 진짜 클라이언트.
in-memory storage라 단일 instance에서만 동작. 다중 instance 확장 시 Redis 필요.
"""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request


def _key(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=_key)

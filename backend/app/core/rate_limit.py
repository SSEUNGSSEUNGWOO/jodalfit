"""IP 기반 rate limiting — OpenAI 토큰 남용 방지.

Railway는 proxy 뒤라 x-forwarded-for 첫 IP가 진짜 클라이언트.
in-memory storage라 단일 instance에서만 동작. 다중 instance 확장 시 Redis 필요.
"""

from __future__ import annotations

from contextvars import ContextVar

from slowapi import Limiter
from starlette.requests import Request

from app.core.traffic_source import INTERNAL, classify_source


def _key(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=_key)

# 내부 SSR(X-Internal-Token 일치)은 IP 제한에서 뺀다. 회사 페이지 SSR 은 Vercel 의 IP 몇 개에서 나가므로 크롤러가 회사
# 페이지를 몰아서 긁으면 그 IP 가 분당 15회를 넘겨 429 — 2026-11-04 두 시간에 500건 넘게 추천 없는 페이지가 렌더링됐다.
# slowapi 0.1.9 의 exempt_when 은 request 를 못 받으므로, 비동기 의존성이 요청 컨텍스트에 표시를 남기고 exempt_when 이 읽는다
# (동기 엔드포인트는 anyio 워커 스레드가 컨텍스트를 복사해 간다). 동기 의존성에서 set 하면 그 스레드에만 남아 안 된다.
_internal: ContextVar[bool] = ContextVar("rate_limit_internal", default=False)


async def mark_internal(request: Request) -> None:
    """엔드포인트 dependencies 에 넣는다. 반드시 async — 요청 태스크의 컨텍스트에 남아야 한다."""
    _internal.set(classify_source(request) == INTERNAL)


def internal_exempt() -> bool:
    return _internal.get()

"""봇/스크래퍼 차단 dependency.

전략:
- 시크릿 헤더(X-Internal-Token) 일치 → 모든 검사 면제 (Next.js SSR self-call)
- 외부 호출 → 전역 cap + UA 블랙리스트 + referer 화이트리스트 검사

INTERNAL_API_TOKEN이 설정되지 않으면 전체 가드 no-op (개발 편의).
프로덕션에서는 반드시 설정.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from app.core.config import get_settings

# 자동화 도구 UA. Next.js SSR("node")은 토큰으로 통과하므로 여기 포함 안전.
_UA_BLOCKLIST = (
    "python-requests",
    "aiohttp",
    "httpx",
    "curl/",
    "wget/",
    "go-http-client",
    "okhttp",
    "java/",
    "scrapy",
    "node",
)

# 전역 cap — 분산 IP 봇 우회 차단용. in-process(단일 instance 가정).
_GLOBAL_WINDOW_SEC = 60
_GLOBAL_MAX_PER_MIN = 300
_global_hits: deque[float] = deque()
_global_lock = Lock()


def _check_global_cap() -> None:
    now = time.time()
    with _global_lock:
        while _global_hits and now - _global_hits[0] > _GLOBAL_WINDOW_SEC:
            _global_hits.popleft()
        if len(_global_hits) >= _GLOBAL_MAX_PER_MIN:
            raise HTTPException(
                status_code=429, detail="전체 트래픽 한도 초과. 잠시 후 다시 시도해주세요."
            )
        _global_hits.append(now)


def _referer_host(referer: str | None) -> str | None:
    if not referer:
        return None
    try:
        return urlparse(referer).hostname
    except Exception:
        return None


def guard_external_traffic(request: Request) -> None:
    settings = get_settings()

    # 토큰 미설정 = 가드 비활성 (개발 편의)
    expected = settings.internal_api_token
    if not expected:
        return

    # 내부 호출 우회 (Next.js SSR self-call)
    if request.headers.get("x-internal-token") == expected:
        return

    _check_global_cap()

    ua = (request.headers.get("user-agent") or "").lower()
    for needle in _UA_BLOCKLIST:
        if needle in ua:
            raise HTTPException(status_code=403, detail="허용되지 않는 클라이언트")

    allowed = settings.allowed_referer_hosts
    if allowed:
        host = _referer_host(request.headers.get("referer"))
        if not host or host not in allowed:
            raise HTTPException(status_code=403, detail="허용되지 않은 출처")

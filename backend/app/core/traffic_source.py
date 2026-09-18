"""요청 출처 분류 — 로그 지표에서 내부 SSR 호출과 실사용자를 갈라내기 위한 것.

search_logs·notice_events가 한 테이블에 섞여 있으면 "검색 8만 건" 같은 숫자가
사실은 회사·공고 SEO 페이지를 서버가 렌더링한 횟수가 된다. 2026-09-18 확인:
최근 1,000건 중 982건이 내부 SSR(`node`)이었다.

판정은 추측이 아니라 신호 기반이다:
- `X-Internal-Token` 일치 → internal (Next.js SSR self-call, bot_guard와 같은 신호)
- UA가 자동화 도구 → bot
- 그 외 → user
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings

INTERNAL = "internal"
BOT = "bot"
USER = "user"

# 자동화 도구 UA. bot_guard._UA_BLOCKLIST와 같은 이유로 "node"를 포함한다 —
# 정상 SSR은 토큰으로 internal 판정이 먼저 끝나므로, 여기 걸리는 "node"는 토큰 없는 외부 호출이다.
_BOT_UA = (
    "node",
    "bot",
    "spider",
    "crawl",
    "slurp",
    "yeti",
    "facebookexternalhit",
    "bingpreview",
    "headless",
    "python-requests",
    "httpx",
    "aiohttp",
    "curl/",
    "wget/",
    "go-http-client",
    "okhttp",
    "java/",
    "scrapy",
    "axios",
    "node-fetch",
    "undici",
    "lighthouse",
    "uptime",
)


def classify(user_agent: str | None, internal_token: str | None, expected_token: str | None) -> str:
    """순수 함수 — 테스트 가능하게 헤더 값만 받는다."""
    if expected_token and internal_token == expected_token:
        return INTERNAL
    ua = (user_agent or "").lower()
    if not ua:
        return BOT  # UA 없는 요청은 브라우저가 아니다
    if any(n in ua for n in _BOT_UA):
        return BOT
    return USER


def classify_source(request: Request) -> str:
    return classify(
        request.headers.get("user-agent"),
        request.headers.get("x-internal-token"),
        get_settings().internal_api_token,
    )


def _demo() -> None:
    """uv run python -m app.core.traffic_source"""
    T = "secret-token"
    CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128"

    # 내부 SSR: 토큰이 UA보다 우선한다 (SSR UA가 "node"여도 internal)
    assert classify("node", T, T) == INTERNAL
    assert classify(CHROME, T, T) == INTERNAL
    # 토큰 불일치·미설정이면 UA로 판정
    assert classify("node", "wrong", T) == BOT
    assert classify("node", None, T) == BOT
    assert classify("node", T, None) == BOT, "서버에 토큰 미설정이면 internal로 속일 수 없어야 한다"
    # 봇
    assert classify("Googlebot/2.1", None, T) == BOT
    assert classify("Mozilla/5.0 (compatible; Yeti/1.1)", None, T) == BOT
    assert classify("python-requests/2.31", None, T) == BOT
    assert classify(None, None, T) == BOT
    assert classify("", None, T) == BOT
    # 실사용자
    assert classify(CHROME, None, T) == USER
    assert classify("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1", None, T) == USER
    print("traffic_source: ok")


if __name__ == "__main__":
    _demo()

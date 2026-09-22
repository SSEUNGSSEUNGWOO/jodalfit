"""요청 1회 안의 구간별 소요 시간 수집 — Server-Timing 헤더로 내보낸다.

로컬에서 프로파일링하면 한국↔DB 왕복 지연이 결과를 지배해 프로덕션 병목이 가려진다
(2026-09-22, 가설을 네 번 갈아탔다). 그래서 백엔드가 실제로 도는 곳에서 잰다.

API 레이어가 start() 로 수집을 켜고, 서비스 코드는 `with timed("이름"):` 으로 구간을
감싼다. 수집이 꺼져 있으면(잡·CLI 등) timed 는 아무것도 하지 않는다.
recommend.py ↔ recommender/ 순환 import 를 피하려고 별도 모듈로 둔다.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar

_timings: ContextVar[dict[str, float] | None] = ContextVar("timings", default=None)


def start() -> dict[str, float]:
    d: dict[str, float] = {}
    _timings.set(d)
    return d


@contextmanager
def timed(name: str):
    t = time.perf_counter()
    try:
        yield
    finally:
        d = _timings.get()
        if d is not None:
            # 같은 이름이 여러 번 불리면 합산한다 (예: 재시도)
            d[name] = d.get(name, 0.0) + (time.perf_counter() - t) * 1000


def server_timing_header(d: dict[str, float]) -> str:
    return ", ".join(f"{k};dur={v:.0f}" for k, v in d.items())
